from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from typing import TYPE_CHECKING
from django.template import Context, Template

from icecream import ic   # type: ignore[import]

from django.utils import timezone
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.messages import (
    constants as message_constants,
)   # type: ignore[import]

from user_messages import api   # type: ignore[import]

import celery   # type: ignore[import]
from celery import shared_task   # type: ignore[import]
from celery.utils.log import get_task_logger   # type: ignore[import]

from server.server_registration import (
    ExecutionMessage,
    ServerCreatedInfo,
    ServerDeletedInfo,
    ServerInfo,
    ServerPasswordResetInfo,
    ServerTypeBase,
    StartServerMixin,
    ResetPasswordMixin,
    RestartServerMixin,
    StopServerMixin,
)

if TYPE_CHECKING:
    from server.models import ProvisionedServerInstance


logger = get_task_logger(__name__)


class ErrorCatcher(celery.Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            f'{exc} ({task_id}) with args: {args} and kwargs: {kwargs} failed with error: {einfo}.'
        )

        from server.models import ExecutionMessages

        execution = ExecutionMessages(
            job_id=task_id,
            task_name=self.name,
            admin_message=f'{exc} ({task_id}) with args: {args} and kwargs: {kwargs} failed with an error (see trace).',
            admin_trace=str(einfo),
        )
        try:
            if 'instance_id' in kwargs:
                server_instance = _get_server_obj(kwargs.get('instance_id'))
                execution.instance = server_instance
                user_message = f'Server {server_instance} failed. Please retry later or inform the administrator of this site.'

                execution.user_message = user_message
                api.add_message(
                    user=server_instance.user,
                    level=message_constants.ERROR,
                    message=user_message,
                )
        except Exception as e:
            logger.error(e)
        execution.save()


def add_message_content_to_server_instance(
    task_name: str,
    job_id: str,
    message: ServerInfo
    | ServerDeletedInfo
    | ServerCreatedInfo
    | ServerPasswordResetInfo,
    server_instance: ProvisionedServerInstance,
):
    from server.models import ExecutionMessages

    attrs = server_instance.updateable_server_fields
    for attr_name in attrs:
        if (
            hasattr(message, attr_name)
            and getattr(message, attr_name) is not None
        ):
            ic(attr_name, getattr(message, attr_name))
            # FIXME: ugly: server_state is a special case. Make it less special ;-)
            if attr_name != 'server_state':
                value = getattr(message, attr_name)
            else:
                try:
                    value = getattr(message, attr_name).value
                except AttributeError:
                    logger.error(
                        f'{attr_name} was not as on the message {message} object as expected.'
                    )
                    value = getattr(message, attr_name)
            setattr(server_instance, attr_name, value)

    execution = ExecutionMessages(
        instance=server_instance,
        job_id=job_id,
        task_name=task_name,
        user=server_instance.user,
    )

    if hasattr(message, 'message') and message.message is not None:
        execution.user_message = message.message.user_message
        execution.user_trace = message.message.user_error_trace
        execution.admin_message = message.message.admin_message
        execution.admin_trace = message.message.admin_error_trace

    execution.save()
    server_instance.save()


def get_server_class(
    server_instance,
) -> ServerTypeBase | StartServerMixin | ResetPasswordMixin | RestartServerMixin | StopServerMixin:
    server_class = server_instance.server_type.get_server_type_implementation()
    return server_class


def reschedule_if_max_parallel_reached(celery_task, server_instance):
    if server_instance is None or server_instance.server_type is None:
        return

    max_paralell_executions = (
        server_instance.server_type.max_paralell_executions
    )

    if max_paralell_executions is None or max_paralell_executions == 0:
        return
    else:
        from server.models import ProvisionedServerInstance

        # TODO: This isn't very exact, so it might be plus minus an instance
        # at the same time
        currently_running = ProvisionedServerInstance.objects.filter(
            server_id__isnull=True
        ).count()
        # to make this better, the states of celery might be needed:
        # from celery.states import READY_STATES, UNREADY_STATES
        try:
            if currently_running >= max_paralell_executions:
                raise BufferError(
                    f'job limit exeeded: running: {currently_running}, max: {max_paralell_executions}. Retrying in 1 minute.'
                )
        except BufferError as exc:
            # Retry in 1 minute.
            # stops the execution here
            # https://docs.celeryq.dev/en/stable/reference/celery.app.task.html#celery.app.task.Task.retry
            celery_task.retry(countdown=60, exc=exc)
            raise


@shared_task(bind=True, base=ErrorCatcher, name='remove-due-servers')
def run_cleanup(self):
    from server.models import ProvisionedServerInstance
    from server.tasks import delete_server

    now = timezone.now()
    for ps in ProvisionedServerInstance.objects.filter(removal_at__lte=now):
        delete_server.delay(instance_id=ps.id)

    # TODO: Delete obsolete servers after a certain time when they do not start
    # For example: After 25 Minutes the server is being deleted.
    # This should take care to stop/cancelling still waiting/proceeding job
    # so they don't break.
    # possible way to start with implementation (missing the job cancelling):
    # timeout = timedelta(minutes=25)
    # for s in ProvisionedServerInstance.objects.filter(server_id__isnull=True).filter(timeout):
    #     if not s.server_id:
    #         s.delete()
    #         continue
    logger.info(f'cleanup done {now}')


@shared_task(bind=True, base=ErrorCatcher, name='send-soon-due-mails')
def run_info_mail_send(self):
    """
    renewal is only available 12 weeks before the deadline.
    """
    from server.models import ProvisionedServerInstance

    in_12_weeks = timezone.now() + timedelta(weeks=12)
    unsent_servers = (
        ProvisionedServerInstance.objects.filter(notify_before_destroy=True)
        .filter(info_mail_sent=False)
        .filter(removal_at__lte=in_12_weeks)
    )

    if len(unsent_servers) > 0:
        try:
            site = Site.objects.get(pk=settings.SITE_ID)
        except:
            site = Site.objects.all()[0]
        url = site.domain
        if not url.startswith('http'):
            url = f'https://{url}'
        for s in unsent_servers:
            try:
                s.send_deletion_notification_mail(url)
            except Exception as e:
                logger.error(
                    f'sending email failed, continuing anyway. Error: {e}'
                )


def _get_server_obj(instance_id: int):
    from server.models import ProvisionedServerInstance

    return ProvisionedServerInstance.objects.get(pk=instance_id)


@shared_task(
    bind=True,
    base=ErrorCatcher,
)
def create_server(self, *, instance_id: int):
    server_instance = _get_server_obj(instance_id)
    reschedule_if_max_parallel_reached(self, server_instance)

    api.add_message(
        user=server_instance.user,
        level=message_constants.INFO,
        message=f'Server {server_instance} is being created.',
    )
    server_class = get_server_class(server_instance)
    if not isinstance(server_class, ServerTypeBase):
        raise ValueError(
            '{server_class} is not a ServerTypeBase and canot create a server'
        )
    result = server_class.create_instance(model_instance_id=server_instance.id)
    
    t = Template(server_instance.server_type.user_message)
    result.message = ExecutionMessage(t.render(context=Context(dict(server=result))))

    add_message_content_to_server_instance(
        self.name, self.request.id, result, server_instance
    )

    api.add_message(
        user=server_instance.user,
        level=message_constants.SUCCESS,
        message=f'Server {server_instance} is ready.',
    )
    return asdict(result)


@shared_task(
    bind=True,
    base=ErrorCatcher,
)
def start_server(self, *, instance_id: int):
    server_instance = _get_server_obj(instance_id)
    reschedule_if_max_parallel_reached(self, server_instance)

    server_class = get_server_class(server_instance)
    if not isinstance(server_class, StartServerMixin):
        raise ValueError(
            '{server_class} has no StartServerMixin and canot start a server'
        )

    result = server_class.start_server(model_instance_id=server_instance.id)

    add_message_content_to_server_instance(
        self.name, self.request.id, result, server_instance
    )

    api.add_message(
        user=server_instance.user,
        level=message_constants.SUCCESS,
        message=f'Server {server_instance} started.',
    )

    return asdict(result)


@shared_task(
    bind=True,
    base=ErrorCatcher,
)
def stop_server(self, *, instance_id: int):
    server_instance = _get_server_obj(instance_id)
    reschedule_if_max_parallel_reached(self, server_instance)

    server_class = get_server_class(server_instance)

    if not isinstance(server_class, StopServerMixin):
        raise ValueError(
            '{server_class} has no StopServerMixin and canot stop a server'
        )

    result = server_class.stop_server(model_instance_id=server_instance.id)
    add_message_content_to_server_instance(
        self.name, self.request.id, result, server_instance
    )

    api.add_message(
        user=server_instance.user,
        level=message_constants.SUCCESS,
        message=f'Server {server_instance} stopped.',
    )
    return asdict(result)


@shared_task(
    bind=True,
    base=ErrorCatcher,
)
def reboot_server(self, *, instance_id: int):
    server_instance = _get_server_obj(instance_id)
    reschedule_if_max_parallel_reached(self, server_instance)

    server_class = get_server_class(server_instance)
    if not isinstance(server_class, RestartServerMixin):
        raise ValueError(
            '{server_class} has no RestartServerMixin and canot restart a server'
        )
    result = server_class.restart_server(model_instance_id=server_instance.id)
    add_message_content_to_server_instance(
        self.name, self.request.id, result, server_instance
    )

    api.add_message(
        user=server_instance.user,
        level=message_constants.SUCCESS,
        message=f'Server {server_instance} is rebooted.',
    )
    return asdict(result)


@shared_task(
    bind=True,
    base=ErrorCatcher,
)
def pw_reset_server(self, *, instance_id: int):
    server_instance = _get_server_obj(instance_id)
    reschedule_if_max_parallel_reached(self, server_instance)

    server_class = get_server_class(server_instance)
    if not isinstance(server_class, ResetPasswordMixin):
        raise ValueError(
            '{server_class} has no ResetPasswordMixin and canot reset the password'
        )

    result = server_class.reset_password(model_instance_id=server_instance.id)
    add_message_content_to_server_instance(
        self.name, self.request.id, result, server_instance
    )

    api.add_message(
        user=server_instance.user,
        level=message_constants.SUCCESS,
        message=f'The Password for {server_instance} has been reset.',
    )
    return asdict(result)


@shared_task(
    bind=True,
    base=ErrorCatcher,
)
def prolong_server(self, *, instance_id: int):
    server_instance = _get_server_obj(instance_id)
    reschedule_if_max_parallel_reached(self, server_instance)

    if server_instance.server_type.prolong_by_days:
        server_instance.removal_at += timedelta(
            days=server_instance.server_type.prolong_by_days
        )

        server_class = get_server_class(server_instance)
        if not isinstance(server_class, ServerTypeBase):
            raise ValueError(
                '{server_class} is no ServerTypeBase and canot prolong'
            )

        result = server_class.prolong_server(
            model_instance_id=server_instance.id
        )
        if result is not None:
            add_message_content_to_server_instance(
                self.name, self.request.id, result, server_instance
            )

        api.add_message(
            user=server_instance.user,
            level=message_constants.SUCCESS,
            message=f'The server {server_instance} has been prolonged.',
        )
        if result is None:
            result = server_class.get_server_info(
                model_instance_id=server_instance.id
            )
    else:
        api.add_message(
            user=server_instance.user,
            level=message_constants.ERROR,
            message=f'The server {server_instance} cannot be prolonged.',
        )
        raise ValueError(
            f'The server {server_instance} has not prolonging option enabled.'
        )

    return asdict(result)


@shared_task(
    bind=True,
    base=ErrorCatcher,
)
def delete_server(self, *, instance_id: int):
    server_instance = _get_server_obj(instance_id)
    reschedule_if_max_parallel_reached(self, server_instance)
    user = server_instance.user
    server_id = server_instance.server_id
    deletion_info = ServerDeletedInfo(server_id=server_id, deleted=False)
    if server_instance.server_id:
        server_class = server_instance.get_server_class()
        if not isinstance(server_class, ServerTypeBase):
            raise ValueError(
                '{server_class} is no ServerTypeBase and cannot delete a server'
            )
        deletion_info = server_class.delete_server(server_instance.id)
    server_instance.delete(really_delete=True)
    deletion_info.deleted = True
    api.add_message(
        user=user,
        level=message_constants.INFO,
        message=f'Server {server_id} has been deleted.',
    )
    add_message_content_to_server_instance(
        self.name, self.request.id, deletion_info, server_instance
    )
    return asdict(deletion_info)
