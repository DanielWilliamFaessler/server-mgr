from server.providers.hetzner.base import ServerTypeHetzner
from server.server_registration import ServerTypeFactory


@ServerTypeFactory.register(name_id='hetzner-superset')
class SupersetHetznerTemplate(ServerTypeHetzner):
    server_variant = 'superset'
    location = 'nbg1'
    instance_type = 'cx21'
    image_name = 'superset'


@ServerTypeFactory.register(name_id='hetzner-linux-server')
class LinuxInstanceHetznerTemplate(ServerTypeHetzner):
    server_variant = 'superset'
    location = 'nbg1'
    instance_type = 'cx21'
    image_name = 'superset'
