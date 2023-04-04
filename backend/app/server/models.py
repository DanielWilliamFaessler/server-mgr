from __future__ import annotations
from typing import TYPE_CHECKING, Type, TypeAlias
from datetime import timedelta
from uuid import uuid4
import logging

from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.core.mail import send_mail, mail_admins
from django.conf import settings
from django.db import models
from django.urls import reverse_lazy
from django.utils import timezone

from celery.states import ALL_STATES  # type: ignore[import]

from django_extensions.db.models import TimeStampedModel  # type: ignore[import]

from server.server_registration import (
    ServerState,
    ServerTypeBase,
    ResetPasswordMixin,
    RestartServerMixin,
    ServerTypeFactory,
    StartServerMixin,
    StopServerMixin,
)

from server import tasks


User = get_user_model()
logger = logging.Logger(__name__)

UNKNOWN = 'UNKNOWN'
REMOVED = 'REMOVED'
CELERY_STATES = frozenset(
    [
        UNKNOWN,
    ]
    + list(ALL_STATES)
    + [
        REMOVED,
    ]
)
# TODO: set celery job state when job is done, ie. using a callback
CELERY_STATE_CHOICES = [(state, state) for state in CELERY_STATES]


class ServerType(models.Model):
    name = models.CharField(max_length=200, null=False)
    description = models.TextField(
        null=False, help_text='Message at creation time for the user'
    )
    max_paralell_executions = models.IntegerField(
        blank=True,
        default=0,
        help_text='If set, only as many jobs for one action (creation, deletionetc) are allowed. They are retried until the limit is OK again. 0 for unlimited.',
    )
    remove_after_minutes = models.IntegerField(
        default=4 * 60, help_text='default is 4h.'
    )
    user_message = models.TextField(null=True, blank=True)
    notify_before_destroy = models.BooleanField(
        null=False,
        default=False,
        help_text='Default settings for notify user before deletion of server',
    )
    allowed_groups = models.ManyToManyField(
        Group,
        blank=True,
        default=None,
        help_text='None for allowed for everyone. Select groups to limit access to the template.',
    )
    prolong_by_days = models.IntegerField(
        null=True,
        blank=True,
        default=None,
        help_text='if set, allow prolonging by this amount of days is allowed. 365 days is a year.',
    )
    server_type_reference = models.CharField(
        null=False,
        max_length=200,
        unique=True,
    )
    # todo: pass these along during creation
    template_params = models.JSONField(
        null=True,
        blank=True,
        help_text='if allowed by the template, this will be passed along when creating the server.',
    )

    @classmethod
    def get_user_choosable_option(cls, user):
        return cls.objects.filter(
            models.Q(allowed_groups=None)
            | models.Q(allowed_groups__in=user.groups.all())
        )

    def __str__(self):
        return self.name

    def has_group_permission(self, user):
        server_groups = set([g.id for g in self.allowed_groups.all()])

        if len(server_groups) == 0:
            return True

        user_groups = set([g.id for g in user.groups.all()])

        if (
            len(server_groups)
            and len(server_groups.intersection(user_groups)) > 0
        ):
            return True
        return False

    def get_server_type_implementation(
        self,
    ) -> ServerTypeBase | StartServerMixin | ResetPasswordMixin | RestartServerMixin | StopServerMixin:
        return ServerTypeFactory.create_server_type(self.server_type_reference)


class ProvisionedServerInstance(TimeStampedModel, models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    usage = models.TextField(null=False, default='', blank=True)
    server_type = models.ForeignKey(
        'server.ServerType',
        on_delete=models.CASCADE,
        null=False,
    )
    user_message = models.TextField(null=True, blank=True)
    removal_at = models.DateTimeField(null=False, blank=False)

    # these fields are being added later
    server_id = models.CharField(null=False, blank=False, max_length=255)
    server_name = models.CharField(
        null=False, blank=False, max_length=255, default=''
    )
    server_address = models.URLField(null=True, blank=True)
    server_user = models.TextField(null=True, blank=True)
    # this needs to be plain text, to be able to display again
    server_password = models.TextField(null=True, blank=True)
    notify_before_destroy = models.BooleanField(
        null=False, blank=False, default=False
    )
    info_mail_sent = models.BooleanField(
        null=False, blank=False, default=False
    )
    extending_lifetime_secret = models.UUIDField(
        null=True, blank=True, editable=False, default=None
    )
    server_state = models.IntegerField(
        choices=ServerState.as_choices(),
        default=int(ServerState.UNKNOWN.value),
    )
    server_bears_mark_of_deletion = models.BooleanField(
        null=False,
        blank=False,
        default=False,
    )

    # fields that can be updated through the providers
    # all fields can be manipulated in the admin, no restrictions
    updateable_server_fields = [
        'usage',
        'user_message',
        'server_id',
        'server_name',
        'server_address',
        'server_user',
        'server_password',
        'server_state',
    ]

    def __str__(self) -> str:
        name = f'{self.user.username}: {self.server_type}'
        return name

    def save(self, *args, **kwargs):
        if self._state.adding:
            if not self._has_creation_perms(self.server_type):
                raise PermissionError(
                    'You lack the permissions to create a server or there is already one.'
                )
            self.usage = self.server_type.description
            self.notify_before_destroy = self.server_type.notify_before_destroy
            # extra stuff, like template
            remove_after_minutes = self.server_type.remove_after_minutes
            self.removal_at = timezone.now() + timedelta(
                minutes=remove_after_minutes
            )
            super().save(*args, **kwargs)
            tasks.create_server.delay(instance_id=self.id)
        else:
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not self._has_destroy_perms(self.user):
            raise PermissionError(
                'You lack the permissions to create a server or there is already one.'
            )
        if not kwargs.pop('really_delete', False):
            self.server_bears_mark_of_deletion = True
            self.save()
            tasks.delete_server.delay(instance_id=self.id)
        else:
            super().delete(*args, **kwargs)

    def send_deletion_notification_mail(
        self, site
    ) -> 'ProvisionedServerInstance':
        if not self.server_type.prolong_by_days:
            return self

        self.extending_lifetime_secret = uuid4()
        subject = f'Your server will be deleted on {self.removal_at}. Prolong it now.'
        msg = f"""
Your server {self} is scheduled to be removed on {self.removal_at}.
If you want to keep if, use this link to extend its lifetime by {self.server_type.prolong_by_days} days:
{site}{reverse_lazy('server-prolong', kwargs=dict(pk=self.id, secret=self.extending_lifetime_secret))}.
"""

        email = self.user.email
        try:
            send_mail(
                subject,
                msg,
                from_email=settings.EMAIL_DEFAULT_FROM,
                recipient_list=[email],
                fail_silently=False,
            )
        except:
            logging.error(
                f'unable to send prolonging email. Original Mail to {email}: {msg}'
            )

            mail_admins(
                subject=f'unable to send prolonging email.',
                message=f'{msg}',
            )

        self.info_mail_sent = True
        self.save()
        logger.info('mail sent')
        return self

    def _has_destroy_perms(self, user: TypeAlias[User]):
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return self.user == user

    def _has_change_perms(self, user: TypeAlias[User]):
        return self._has_destroy_perms(user)

    @classmethod
    def _user_has_instance_already(
        cls, server_type: ServerType, user: TypeAlias[User]
    ):
        has_already_an_instance = (
            ProvisionedServerInstance.objects.filter(
                server_bears_mark_of_deletion=False
            )
            .filter(server_type=server_type)
            .filter(user=user)
            .count()
            > 0
        )
        return has_already_an_instance

    def _has_creation_perms(self, server_type: ServerType):
        if self.user.is_superuser:
            return True

        if not self.user.is_authenticated:
            return False

        has_already_an_instance = self._user_has_instance_already(
            server_type, self.user
        )
        if has_already_an_instance:
            return False

        if not server_type.has_group_permission(self.user):
            return False
        return True

    def get_server_class(
        self,
    ) -> ServerTypeBase | StartServerMixin | ResetPasswordMixin | RestartServerMixin | StopServerMixin:
        return self.server_type.get_server_type_implementation()

    @property
    def availables_actions(self):
        server_class = self.get_server_class()
        create_action = isinstance(server_class, ServerTypeBase)
        server_info_action = isinstance(server_class, ServerTypeBase)
        delete_server_action = isinstance(server_class, ServerTypeBase)
        restart_action = isinstance(server_class, RestartServerMixin)
        start_action = isinstance(server_class, StartServerMixin)
        stop_action = isinstance(server_class, StopServerMixin)
        pw_reset_action = isinstance(server_class, ResetPasswordMixin)

        return {
            'is_crateable': create_action,
            'can_show_server_info': server_info_action,
            'is_deletable': delete_server_action,
            'is_restartable': restart_action,
            'is_startable': start_action,
            'is_stoppable': stop_action,
            'is_pw_resetable': pw_reset_action,
        }

    def get_absolute_url(self):
        return reverse_lazy('server:server-list')

    def execution_messages(self):
        return ExecutionMessages.objects.filter(instance=self).order_by(
            '-created'
        )

    def user_messages(self):
        return self.execution_messages().filter(user_message__isnull=False)

    def user_traces(self):
        return self.execution_messages().filter(user_trace__isnull=False)

    def admin_messages(self):
        return self.execution_messages().filter(admin_message__isnull=False)

    def admin_traces(self):
        return self.execution_messages().filter(admin_trace__isnull=False)


class ExecutionMessages(TimeStampedModel, models.Model):
    instance = models.ForeignKey(
        'ProvisionedServerInstance',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    job_id = models.CharField(max_length=255, null=False, blank=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    task_name = models.CharField(max_length=255, null=False, blank=False)
    user_message = models.TextField(null=True, blank=True)
    user_trace = models.TextField(null=True, blank=True)
    admin_message = models.TextField(null=True, blank=True)
    admin_trace = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        info = f'{self.task_name} ({self.created}) '
        if self.user_message:
            info += f'{self.user_message[0:10]}'
        elif self.admin_message:
            info += f'{self.admin_message[0:10]}'
        return f'{info} ({self.instance})'

    class Meta:
        ordering = ['-created']
