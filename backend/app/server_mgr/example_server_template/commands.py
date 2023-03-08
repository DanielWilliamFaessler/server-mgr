"""
Every function may return a valid json (string),
or a dataclass (which is the convereted to a json).
Alternatively, in case of an exception, the error (and stacktrace, if possible)
will be saved in the backend for further analysis and the end-user will receive
a generic error message (and that he may try again later).

The json has the following signature, whereby nullable values (default null)
can also be ommited, which has the same effect.
"""
import json
from dataclasses import dataclass
from server_mgr.server_template_executor import run


@dataclass
class ServerInfoResponse:
    # the id of the server. In all cases except creation, this is a mere echo.
    # in case of creation, this might be changed (even though a unique name is passed
    # which can be used)
    server_id: str
    server_ip: str
    # admin login username
    server_username: str
    # admin login password
    server_password: str
    # status of the server. Should be reachable when true.
    server_is_running: bool = False
    # extra informations from "tf show -json"
    server_extra_infos: dict = None
    # did the operation succeed. If not, or an exception is thrown,
    # the use gets an error message. Details should be included in the user_message
    # for the user.
    success: bool = False
    # extra infos for the user. Sould be template specific. Variables from
    # server_* can be used here, ie. {{ server_ip }}.
    user_message: str = None
    # private message for admins only, most likely only for debugging/errors.
    admin_message: str = None


@dataclass
class ServerDeleteResponse:
    server_id: str
    server_is_running: bool = False
    success: bool = False
    user_message: str = None
    admin_message: str = None


def create(server_id) -> ServerInfoResponse:
    run_resp = run('')
    result = json.loads(run_resp.result)
    return ServerInfoResponse(**result)


def get_infos(server_id) -> ServerInfoResponse:
    run_resp = run('')
    result = json.loads(run_resp.result)
    return ServerInfoResponse(**result)


def start(server_id) -> ServerInfoResponse:
    run_resp = run('')
    result = json.loads(run_resp.result)
    return ServerInfoResponse(**result)


def stop(server_id) -> ServerInfoResponse:
    run_resp = run('')
    result = json.loads(run_resp.result)
    return ServerInfoResponse(**result)


def reboot(server_id) -> ServerInfoResponse:
    run_resp = run('')
    result = json.loads(run_resp.result)
    return ServerInfoResponse(**result)


def create_new_password(server_id) -> ServerInfoResponse:
    run_resp = run('')
    result = json.loads(run_resp.result)
    return ServerInfoResponse(**result)


def delete(server_id) -> ServerDeleteResponse:
    run_resp = run('')
    result = json.loads(run_resp.result)
    return ServerDeleteResponse(**result)
