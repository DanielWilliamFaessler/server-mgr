import random
import string
import subprocess
import logging
import os
from server_registration import *

from server_registration import (
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

def _get_server_infos_from_terraform_server(server):
    return ServerInfo(
        server_id=str(server.id),
        server_name=server.name or "",
        server_state=terraform_status_to_server_state[server.status or "unknown"],
        created=server.created,
        server_address="", #I have to figure this one out later
        labels=server.labels or dict(),
    )

HCLOUD_TOKEN: str = os.environ.get('HCLOUD_TOKEN')

if not HCLOUD_TOKEN:
    raise ValueError('HCLOUD_TOKEN missing from environment.')

def _create_random_string(
    size=8, choice_pool=string.ascii_letters + string.digits
):
    return ''.join(random.choice(choice_pool) for _ in range(size))

def _create_random_name():
    return _create_random_string(choice_pool=string.ascii_letters)

def apply_configuration(server_name, server_password, hcloud_token):
    # Select Terraform workspace
    subprocess.run(["terraform", "workspace", "select", "default"])

    # Apply Terraform configuration with variable inputs
    subprocess.run(["terraform", "apply", "-auto-approve",
                    "-var", f"hcloud_token={HCLOUD_TOKEN}",
                    "-var", f"server_name={server_name}",
                    "-var", f"server_password={server_password}"]),

def create_hetzner_server():
    terraform_directory: str = "/terraform_workspace"
    server_name: str = _create_random_name()
    server_password: str = _create_random_string

    if not os.path.isdir(terraform_directory):
        print(f"Directory '{terraform_directory}' does not exist.")
        exit(1)

    os.chdir(terraform_directory)

    subprocess.run(["terraform","init"])

    apply_configuration(server_name, server_password, HCLOUD_TOKEN)

create_hetzner_server()

class ServerTypeTerraform(
    RestartServerMixin,
    ResetPasswordMixin,
    StopServerMixin,
    StartServerMixin,
    ServerTypeBase,):
    server_variant: str = ''
    location: str = ''
    instance_type = 'cx21'
    image_name: str = ''
