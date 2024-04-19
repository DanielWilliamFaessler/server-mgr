import random
import string
import subprocess
import logging
from typing import Optional
import os

from django.utils import timezone

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
        result = subprocess.run(['terraform', 'output'], capture_output=True, text=True, check=True)
        output_lines = result.stdout.strip().split('\n')
        output = {}
        for line in output_lines:
            parts = line.split(' = ')
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip().strip('"')
                output[key] = value
        return ServerInfo(
            output
        )
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return None


HCLOUD_TOKEN: str = os.environ.get('HCLOUD_TOKEN')

terraform_directory: str = "/terraform_workspace"

if not HCLOUD_TOKEN:
    raise ValueError('HCLOUD_TOKEN missing from environment.')


def _create_random_string(
    size=8, choice_pool=string.ascii_letters + string.digits
):
    return ''.join(random.choice(choice_pool) for _ in range(size))


def _create_random_name():
    return _create_random_string(choice_pool=string.ascii_letters)


def apply_configuration(server_name, server_password, hcloud_token, server_type: Optional[str] = None, server_image: Optional[str] = None, server_location: Optional[str] = None, server_labels: Optional[str] = None, server_action: Optional[str] = None):
    # Select Terraform workspace
    subprocess.run(["terraform", "workspace", "select", "default"])

    # Apply Terraform configuration with variable inputs
    terraform_apply_args = ["terraform", "apply", "-auto-approve",
                            "-var", f"hcloud_token={hcloud_token}",
                            "-var", f"server_name={server_name}",
                            "-var", f"server_password={server_password}"]
    if server_type:
        terraform_apply_args.extend(["-var", f"server_type={server_type}"])
    if server_image:
        terraform_apply_args.extend(["-var", f"server_image={server_image}"])
    if server_location:
        terraform_apply_args.extend(["-var", f"server_location={server_location}"])
    if server_labels:
        terraform_apply_args.extend(["-var", f"server_labels={server_labels}"])
    if server_action:
        terraform_apply_args.extend(["-var", f"server_action={server_action}"])

    subprocess.run(terraform_apply_args)


server_address = "128.140.110.213"
server_id = "45964980"
server_labels = "{}"
server_name = "testingStuff"
server_state = "off"
def create_terraform_server(
    server_variant,
    username,
    instance_type,
    image_name,
    location,
    description: str,
) -> ServerCreatedInfo:
    server_name: str = f'{server_variant}-{_create_random_name()}-{_create_random_name()}'
    server_password: str = _create_random_string
    server_type: str = instance_type
    server_image: str = image_name
    server_location: str = location
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


    if not os.path.isdir(terraform_directory):
        print(f"Directory '{terraform_directory}' does not exist.")
        exit(1)

    os.chdir(terraform_directory)
    subprocess.run(["terraform","init"])

    apply_configuration(server_name, server_password, HCLOUD_TOKEN, server_type, server_image, server_location, labels, server_action=None)
    return ServerCreatedInfo(
        **info,
        description=description,
        server_user='root',
        server_password=response.root_password,
    )


class ServerTypeTerraform(
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
        return create_terraform_server(
            server_variant=self.server_variant,
            instance_type=self.instance_type,
            username=username,
            image_name=self.image_name,
            location=self.location,
            description=server_instance.server_type.description or '',
        )
        # Write Terraform variables to a .tfvars file
        with open("terraform.tfvars", "w") as tfvars_file:
            tfvars_file.write(f"hcloud_token = \"{self.hcloud_token}\"\n")
            tfvars_file.write(f"server_name = \"{server_name}\"\n")
            tfvars_file.write(f"server_type = \"{server_type}\"\n")
            tfvars_file.write(f"server_image = \"{server_image}\"\n")
            tfvars_file.write(f"server_location = \"{server_location}\"\n")
            tfvars_file.write(f"server_labels = {json.dumps(server_labels)}\n")
            tfvars_file.write(f"server_password = \"{server_password}\"\n")

        # Run Terraform commands
        subprocess.run(["terraform", "init"])
        subprocess.run(["terraform", "apply", "-auto-approve"])

        # Parse Terraform output to retrieve server information
        with open("terraform.tfstate", "r") as tfstate_file:
            tfstate_data = json.load(tfstate_file)
            server_id = tfstate_data["resources"][0]["instances"][0]["attributes"]["id"]
            server_address = tfstate_data["resources"][0]["instances"][0]["attributes"]["ipv4_address"]

        return {
            "server_id": server_id,
            "server_address": server_address,
            "server_variant": server_variant
        }
