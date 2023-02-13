from dataclasses import dataclass
import random
import string
import os
from datetime import datetime

HCLOUD_TOKEN = os.environ.get('HCLOUD_TOKEN')

if not HCLOUD_TOKEN:
    raise ValueError('HCLOUD_TOKEN missing from environment.')

from hcloud import Client
from hcloud.server_types.domain import ServerType
from hcloud.images.domain import Image


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
        address=server.public_net.primary_ipv4,
        labels=server.labels,
    )


def _create_random_string(
    size=6, choice_pool=string.ascii_letters + string.digits
):
    return ''.join(random.choice(choice_pool) for _ in range(size))


def _create_random_name():
    return _create_random_string(choice_pool=string.ascii_letters)


def create_superset_server(username) -> ServerInfo:
    name = f'superset-{_create_random_name()}-{_create_random_name()}'
    server_type = ServerType(name='cpx21')
    image = Image(name='ubuntu-22.04')
    client = Client(token=f'{HCLOUD_TOKEN}')
    location = client.locations.get_by_name('nbg1')
    created_date = str(datetime.now().isoformat('-', 'minutes'))

    response = client.servers.create(
        name=name,
        server_type=server_type,
        image=image,
        location=location,
        labels={
            'usage': 'superset',
            'username': username,
            'created-on': created_date,
        },
    )
    server = response.server
    server_info = _get_server_infos(server)
    server_info.username = 'root'
    server_info.password = response.root_password
    return server_info


def get_server(server_id):
    client = Client(token=f'{HCLOUD_TOKEN}')
    response = client.servers.get_by_id(server_id)
    return response.server, response


def status(server_id):
    server, _ = get_server(server_id)
    return _get_server_infos(server)


def reboot(server_id):
    server, _ = get_server(server_id)
    server.reboot()
    return _get_server_infos(server)


def reset_pw(server_id):
    server, _ = get_server(server_id)
    response = server.reset_password()
    return response.root_password


def destroy(server_id):
    server, _ = get_server(server_id)
    server.delete()
    # server is deleted!
    return None
