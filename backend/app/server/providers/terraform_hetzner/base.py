from time import sleep
import random
import string
import subprocess
import logging
import json
from typing import Optional
from datetime import datetime
import os

from django.utils import timezone

from hcloud import APIException   # type: ignore[import]

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
    ServerTypeBase
)

logger = logging.getLogger(__name__)

terraform_status_to_server_state = {
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


def _get_server_info():
    try:
        result = subprocess.run(
            ['terraform', 'output', '-json'],
            capture_output=True,
            text=True,
            check=True,
        )
        output_json = json.loads(result.stdout.strip())

        server_id = output_json.get('server_id', {}).get('value', '')
        server_name = output_json.get('server_name', {}).get('value', '')
        server_state = terraform_status_to_server_state.get(
            output_json.get('server_state', {}).get('value', 'unknown')
        )
        server_address = output_json.get('server_address', {}).get('value', '')
        labels = output_json.get('server_labels', {}).get('value', {})

        return ServerInfo(
            server_id=server_id,
            server_name=server_name,
            server_state=server_state,
            created=datetime.now(),
            server_address=server_address,
            labels=labels,
        )
    except subprocess.CalledProcessError as e:
        logger.exception(f'Error: {e}')
        return None

HCLOUD_TOKEN: str = os.environ.get('HCLOUD_TOKEN')
if not HCLOUD_TOKEN:
    raise ValueError('HCLOUD_TOKEN missing from environment.')

terraform_directory: str = '/terraform_workspace'
_location = "nbg1"
_instance_type = "cx11"
_image_name = "ubuntu-22.04"

def _create_random_string(
    size=8, choice_pool=string.ascii_letters + string.digits
):
    return ''.join(random.choice(choice_pool) for _ in range(size))

def _create_random_name():
    return _create_random_string(choice_pool=string.ascii_letters)

def _change_directory():
    if not os.path.isdir(terraform_directory):
        logger.exception(f"Directory '{terraform_directory}' does not exist.")
    else:
        os.chdir(terraform_directory)

def apply_configuration(
    server_name,
    server_password,
    hcloud_token,
    server_type: Optional[str] = None,
    server_image: Optional[str] = None,
    server_location: Optional[str] = None,
    server_labels: Optional[str] = None,
    server_action: Optional[str] = None,
    server_password_reset: Optional[str] = None,
    destroy: Optional[str] = None,
):
    # Select Terraform workspace
    subprocess.run(['terraform', 'workspace', 'select', 'default'])

    # Apply Terraform configuration with variable inputs
    terraform_apply_args = [
        'terraform',
        'apply',
        '-auto-approve',
        '-var',
        f'hcloud_token={hcloud_token}',
        '-var',
        f'server_name={server_name}',
        '-var',
        f'server_password={server_password}',
    ]
    if server_type:
        terraform_apply_args.extend(['-var', f'server_type={server_type}'])
    if server_image:
        terraform_apply_args.extend(['-var', f'server_image={server_image}'])
    if server_location:
        terraform_apply_args.extend(
            ['-var', f'server_location={server_location}']
        )
    if server_labels:
        terraform_apply_args.extend(['-var', f'server_labels={server_labels}'])
    if server_action:
        terraform_apply_args.extend(['-var', f'server_action={server_action}'])
    if server_password_reset:
        terraform_apply_args.extend(['-var', 'server_password_reset=true'])
    if destroy:
        terraform_apply_args.extend(['-destroy'])

    subprocess.run(terraform_apply_args)


def create_terraform_server(
    server_variant: str,
    username: str,
    description: str,
) -> ServerCreatedInfo:
    server_name: str = (
        f'{server_variant}-{_create_random_name()}-{_create_random_name()}'
    )
    server_password = _create_random_string()
    created_date = (
        str(timezone.now().isoformat('-', 'minutes'))
        .replace(':', '-')
        .replace('+', '-')
    )
    labels = {
        'usage': f'{server_variant}',
        'created-on': f'{created_date}',
        'username': f'{username}',
    }
    labels_json = json.dumps(labels)

    _change_directory()
    subprocess.run(['terraform', 'init'])

    apply_configuration(
        server_name,
        server_password,
        HCLOUD_TOKEN,
        _instance_type,
        _image_name,
        _location,
        labels_json,
    )
    info = _get_server_info()
    if info:
        return ServerCreatedInfo(
            server_id=info.server_id,
            server_name=info.server_name,
            server_state=info.server_state,
            created=info.created,
            server_address=info.server_address,
            labels=info.labels,
            description=description,
            server_user='root',
            server_password=server_password,
        )


def status() -> ServerInfo:
    return _get_server_info()


def reboot(
    server_name,
    server_password,
    labels,
) -> ServerInfo:
    _change_directory()
    apply_configuration(
        server_name,
        server_password,
        HCLOUD_TOKEN,
        _instance_type,
        _image_name,
        _location,
        labels,
        server_action='reboot',
    )
    # wait for server to be up again
    sleep(30)
    return _get_server_info()


def stop(
    server_name,
    server_password,
    labels,
) -> ServerInfo:
    info = _get_server_info()
    _change_directory()
    apply_configuration(
        server_name,
        server_password,
        HCLOUD_TOKEN,
        _instance_type,
        _image_name,
        _location,
        labels,
        server_action='poweroff',
    )
    # wait for server to be up again
    sleep(30)
    return _get_server_info()


def start(
    server_name,
    server_password,
    labels,
) -> ServerInfo:
    _change_directory()
    info = _get_server_info()
    apply_configuration(
        server_name,
        server_password,
        HCLOUD_TOKEN,
        _instance_type,
        _image_name,
        _location,
        labels,
        server_action='poweron',
    )
    # wait for server to be up again
    sleep(30)
    return _get_server_info()


def reset_pw(
    server_name,
    server_password,
    labels,
) -> ServerPasswordResetInfo:
    _change_directory()
    info = _get_server_info()
    apply_configuration(
        server_name,
        server_password,
        HCLOUD_TOKEN,
        _instance_type,
        _image_name,
        _location,
        labels,
        server_action=None,
        server_password_reset=True,
    )
    # wait for server to be up again
    sleep(30)
    return _get_server_info()


def destroy(
    server_id,
    server_name,
    server_password,
    labels
) -> ServerDeletedInfo:
    _change_directory()
    apply_configuration(
        server_name,
        server_password,
        HCLOUD_TOKEN,
        _instance_type,
        _image_name,
        _location,
        labels,
        server_action=None,
        destroy="destroy"
    )
    sleep(30)
    return ServerDeletedInfo(deleted=True,server_id=server_id, )
    


class ServerTypeTerraform(
    RestartServerMixin,
    ResetPasswordMixin,
    StopServerMixin,
    StartServerMixin,
    ServerTypeBase,
):
    server_variant: str = 'Linux'
    location: str =_location
    instance_type = _instance_type
    image_name: str = _image_name

    def create_instance(
        self, model_instance_id, *args, **kwargs
    ) -> ServerCreatedInfo:
        from server.models import ProvisionedServerInstance

        server_instance = ProvisionedServerInstance.objects.get(
            id=model_instance_id
        )
        username = server_instance.user.username
        return create_terraform_server(
            server_variant=self.server_variant,
            username=username,
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
        info = _get_server_info()
        return reset_pw(
            instance.server_name,
            instance.server_password,
            info.labels,
        )

    def start_server(self, model_instance_id, *args, **kwargs) -> ServerInfo:
        instance = self.get_server_instance(model_instance_id)
        info = _get_server_info()
        return start(
            instance.server_name,
            instance.server_password,
            info.labels,
        )

    def restart_server(self, model_instance_id, *args, **kwargs) -> ServerInfo:
        instance = self.get_server_instance(model_instance_id)
        info = _get_server_info()
        return reboot(
            instance.server_name,
            instance.server_password,
            info.labels,
        )

    def stop_server(self, model_instance_id, *args, **kwargs) -> ServerInfo:
        instance = self.get_server_instance(model_instance_id)
        info = _get_server_info()
        return stop(
            instance.server_name,
            instance.server_password,
            info.labels,
        )

    def delete_server(
        self, model_instance_id, *args, **kwargs
    ) -> ServerDeletedInfo:
        instance = self.get_server_instance(model_instance_id)
        info = _get_server_info()
        deleted = False
        # try once again before bailing out
        try:
            destroy(
                instance.server_id,
                instance.server_name,
                instance.server_password,
                info.labels
            )
            deleted = True
        except APIException:
            try:
                destroy(
                    instance.server_id,
                    instance.server_name,
                    instance.server_password,
                    info.labels
                )
                deleted = True
            except APIException:
                logger.exception(
                    f'Could not delete hetzner server with id {instance.server_id} but continuing anyway.'
                )

        return ServerDeletedInfo(server_id=model_instance_id, deleted=deleted)
