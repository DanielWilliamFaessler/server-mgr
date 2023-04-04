from dataclasses import asdict
import random
import string
import os
import logging
from time import sleep

from django.utils import timezone

HCLOUD_TOKEN = os.environ.get('HCLOUD_TOKEN')

if not HCLOUD_TOKEN:
    raise ValueError('HCLOUD_TOKEN missing from environment.')

from hcloud import Client, APIException   # type: ignore[import]
from hcloud.servers.domain import (  # type: ignore[import]
    Server as HetznerServer,
)
from hcloud.server_types.domain import (  # type: ignore[import]
    ServerType as HetznerServerType,
)
from server.server_registration import (
    ResetPasswordMixin,
    RestartServerMixin,
    ServerPasswordResetInfo,
    ServerState,
    StopServerMixin,
    StartServerMixin,
    ServerCreatedInfo,
    ServerDeletedInfo,
    ServerInfo,
    ServerTypeBase,
    StopServerMixin,
)  # type: ignore[import]

logger = logging.getLogger(__name__)

hetzner_status_to_server_state = {
    'running': ServerState.RUNNING,
    'initializing': ServerState.CREATING,
    'starting': ServerState.CREATING,
    'stopping': ServerState.STOPPED,
    'off': ServerState.STOPPED,
    'deleting': ServerState.RUNNING,
    'migrating': ServerState.STOPPED,
    'rebuilding': ServerState.STOPPED,
    'unknown': ServerState.UNKNOWN,
}


def _get_server_infos_from_hetzner_server(server: HetznerServer):
    return ServerInfo(
        server_id=server.id,
        server_name=server.name,
        server_state=hetzner_status_to_server_state[server.status],
        created=server.created,
        server_address=server.public_net.primary_ipv4.ip,
        labels=server.labels,
    )


def _create_random_string(
    size=6, choice_pool=string.ascii_letters + string.digits
):
    return ''.join(random.choice(choice_pool) for _ in range(size))


def _create_random_name():
    return _create_random_string(choice_pool=string.ascii_letters)


def create_hetzner_server(
    server_variant,
    username,
    instance_type,
    image_name,
    location,
    description: str,
) -> ServerCreatedInfo:
    client = Client(token=f'{HCLOUD_TOKEN}')
    name = f'{server_variant}-{_create_random_name()}-{_create_random_name()}'
    server_type = HetznerServerType(name=instance_type)
    # snapshot only have descriptions and labels
    # image = Image(name='superset', type='snapshot')
    image = [
        i
        for i in client.images.get_all(type='snapshot')
        if i.description == image_name
    ][0]
    location = client.locations.get_by_name(location)
    created_date = (
        str(timezone.now().isoformat('-', 'minutes'))
        .replace(':', '-')
        .replace('+', '-')
    )
    labels = {
        'usage': server_variant,
        'created-on': created_date,
        'username': username,
    }
    response = client.servers.create(
        name=name,
        server_type=server_type,
        image=image,
        location=location,
        labels=labels,
    )
    server = response.server
    info = asdict(_get_server_infos_from_hetzner_server(server))
    # remove keys that are set again in ServerCreatedInfo
    info.pop('description', None)
    info.pop('server_user', None)
    info.pop('server_password', None)
    return ServerCreatedInfo(
        **info,
        description=description,
        server_user='root',
        server_password=response.root_password,
    )


def _get_server(server_id):
    client = Client(token=f'{HCLOUD_TOKEN}')
    server = client.servers.get_by_id(server_id)
    return server


def status(server_id) -> ServerInfo:
    server = _get_server(server_id)
    return _get_server_infos_from_hetzner_server(server)


def reboot(server_id) -> ServerInfo:
    server = _get_server(server_id)
    server.reboot()
    # wait for server to be up again
    sleep(30)
    return _get_server_infos_from_hetzner_server(server)


def stop(server_id) -> ServerInfo:
    server = _get_server(server_id)
    server.power_off()
    # wait for server to be done
    sleep(30)
    return _get_server_infos_from_hetzner_server(server)


def start(server_id) -> ServerInfo:
    server = _get_server(server_id)
    server.power_on()
    # wait for server to be one again
    sleep(30)
    return _get_server_infos_from_hetzner_server(server)


def reset_pw(server_id) -> ServerPasswordResetInfo:
    server = _get_server(server_id)
    response = server.reset_password()
    return ServerPasswordResetInfo(
        server_id=server_id,
        server_password=response.root_password,
        server_user='root',
    )


def destroy(server_id) -> ServerDeletedInfo:
    server = _get_server(server_id)
    server.delete()
    # wait for server to be done
    sleep(30)
    # server is deleted!
    return ServerDeletedInfo(
        deleted=True,
        server_id=server_id,
    )


class ServerTypeHetzner(
    RestartServerMixin,
    ResetPasswordMixin,
    StopServerMixin,
    StartServerMixin,
    ServerTypeBase,
):
    server_variant: str = ''
    location: str = ''
    instance_type = 'cx21'
    image_name: str = ''

    def create_instance(
        self, model_instance_id, *args, **kwargs
    ) -> ServerCreatedInfo:
        from server.models import ProvisionedServerInstance

        server_instance = ProvisionedServerInstance.objects.get(
            id=model_instance_id
        )
        username = server_instance.user.username
        return create_hetzner_server(
            server_variant=self.server_variant,
            instance_type=self.instance_type,
            username=username,
            image_name=self.image_name,
            location=self.location,
            description=server_instance.server_type.description or '',
        )

    def get_server_info(
        self, model_instance_id: str, *args, **kwargs
    ) -> ServerInfo:
        instance = self.get_server_instance(model_instance_id)
        return status(instance.server_id)

    def reset_password(
        self, model_instance_id, *args, **kwargs
    ) -> ServerPasswordResetInfo:
        instance = self.get_server_instance(model_instance_id)
        return reset_pw(instance.server_id)

    def start_server(self, model_instance_id, *args, **kwargs) -> ServerInfo:
        instance = self.get_server_instance(model_instance_id)
        return start(instance.server_id)

    def restart_server(self, model_instance_id, *args, **kwargs) -> ServerInfo:
        instance = self.get_server_instance(model_instance_id)
        return reboot(instance.server_id)

    def stop_server(self, model_instance_id, *args, **kwargs) -> ServerInfo:
        instance = self.get_server_instance(model_instance_id)
        return stop(instance.server_id)

    def delete_server(
        self, model_instance_id, *args, **kwargs
    ) -> ServerDeletedInfo:
        instance = self.get_server_instance(model_instance_id)
        deleted = False
        # try once again before bailing out
        try:
            destroy(instance.server_id)
            deleted = True
        except APIException:
            try:
                destroy(instance.server_id)
                deleted = True
            except APIException:
                logger.exception(
                    f'Could not delete hetzner server with id {instance.server_id} but continuing anyway.'
                )

        return ServerDeletedInfo(server_id=model_instance_id, deleted=deleted)
