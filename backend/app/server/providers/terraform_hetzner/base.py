import random
import string
import subprocess
import logging
import os

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
    ServerTypeBase,
):
    server_variant: str = ''
    location: str = ''
    instance_type = 'cx21'
    image_name: str = ''

    def create_instance(
            self, server_name, server_type, server_image, server_location, server_labels, server_password, server_variant
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
