from dataclasses import dataclass
import random
import string
import os
from datetime import datetime
from django.utils import timezone

HCLOUD_TOKEN = os.environ.get('HCLOUD_TOKEN')

if not HCLOUD_TOKEN:
    raise ValueError('HCLOUD_TOKEN missing from environment.')

from hcloud import Client
from hcloud.server_types.domain import ServerType


@dataclass
class ServerInfo:
    id: str
    name: str
    status: str
    created: datetime
    address: str
    labels: dict
    username: str = None
    password: str = None


def _get_server_infos(server):
    return ServerInfo(
        id=server.id,
        name=server.name,
        status=server.status,
        created=server.created,
        address=server.public_net.primary_ipv4.ip,
        labels=server.labels,
    )


def _create_random_string(
    size=6, choice_pool=string.ascii_letters + string.digits
):
    return ''.join(random.choice(choice_pool) for _ in range(size))


def _create_random_name():
    return _create_random_string(choice_pool=string.ascii_letters)


def create_hetzner_server(server_variant, labels: dict) -> ServerInfo:
    client = Client(token=f'{HCLOUD_TOKEN}')
    name = f'{server_variant.type_id}-{_create_random_name()}-{_create_random_name()}'
    server_type = ServerType(name=server_variant.instance_type)
    # snapshot only have descriptions and labels
    # image = Image(name='superset', type='snapshot')
    image = [
        i
        for i in client.images.get_all(type='snapshot')
        if i.description == server_variant.image_name
    ][0]
    location = client.locations.get_by_name(server_variant.location)
    created_date = (
        str(timezone.now().isoformat('-', 'minutes'))
        .replace(':', '-')
        .replace('+', '-')
    )
    if labels is None:
        labels = {}
    labels = {
        **labels,
        'usage': server_variant.type_id,
        'created-on': created_date,
    }
    response = client.servers.create(
        name=name,
        server_type=server_type,
        image=image,
        location=location,
        labels=labels,
    )
    server = response.server
    server_info = _get_server_infos(server)
    server_info.username = 'root'
    server_info.password = response.root_password
    return server_info


def _get_server(server_id):
    client = Client(token=f'{HCLOUD_TOKEN}')
    server = client.servers.get_by_id(server_id)
    return server


def status(server_id):
    server = _get_server(server_id)
    return _get_server_infos(server)


def reboot(server_id):
    server = _get_server(server_id)
    server.reboot()
    return _get_server_infos(server)


def reset_pw(server_id):
    server = _get_server(server_id)
    response = server.reset_password()
    return response.root_password


def destroy(server_id):
    server = _get_server(server_id)
    server.delete()
    # server is deleted!
    return None
