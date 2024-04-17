import random
import string
import subprocess
import os

HCLOUD_TOKEN: str = os.environ.get('HCLOUD_TOKEN')

if not HCLOUD_TOKEN:
    raise ValueError('HCLOUD_TOKEN missing from environment.')

def _create_random_password(
    size=8, choice_pool=string.ascii_letters + string.digits
):
    return ''.join(random.choice(choice_pool) for _ in range(size))

def _create_random_name():
    return _create_random_string(choice_pool=string.ascii_letters)

subprocess.run(["terraform","init"])

# Select Terraform workspace
subprocess.run(["terraform", "workspace", "select", "default"])

# Apply Terraform configuration with variable inputs
subprocess.run(["terraform", "apply", "-auto-approve",
                "-var", f"hcloud_token={hcloud_token}",
                "-var", f"server_name={_create_random_name}",
                "-var", f"server_password={_create_random_password}"]),


