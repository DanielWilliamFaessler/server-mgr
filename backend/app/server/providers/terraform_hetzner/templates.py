from server.providers.terraform_hetzner.base import ServerTypeTerraform
from server.server_registration import ServerTypeFactory


@ServerTypeFactory.register(name_id='hetzner-superset')
class SupersetHetznerTemplate(ServerTypeTerraform):
    server_variant = 'superset'
    location = 'nbg1'
    instance_type = 'cx21'
    image_name = 'superset'


@ServerTypeFactory.register(name_id='hetzner-linux-server')
class LinuxInstanceHetznerTemplate(ServerTypeTerraform):
    server_variant = 'linux'
    location = 'nbg1'
    instance_type = 'cx11'
    image_name = 'ubuntu-22.04'
