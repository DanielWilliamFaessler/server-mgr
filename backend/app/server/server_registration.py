from __future__ import annotations
from typing import TYPE_CHECKING, Callable
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import IntEnum
import random
import string

from logging import Logger

if TYPE_CHECKING:
    from server.models import ProvisionedServerInstance

logger = Logger(__name__)


class ServerState(IntEnum):
    ERROR = -1
    CREATING = 10
    RUNNING = 20
    STOPPED = 30
    UNKNOWN = 1000

    @classmethod
    def as_choices(cls):
        return tuple((i.value, i.name) for i in cls)


@dataclass
class ExecutionMessage:
    # Message exposed to the user
    user_message: str | None = None
    # only set this if you want to expose the error trace to the user
    user_error_trace: str | None = None
    # message only visible by admins
    admin_message: str | None = None
    # error trace only visible by admins
    admin_error_trace: str | None = None


@dataclass
class ServerInfo:
    server_id: str
    server_name: str
    server_state: ServerState
    created: datetime
    server_address: str
    labels: dict
    usage: str | None = None
    message: ExecutionMessage | None = field(default=None, init=True)
    server_user: str | None = field(default=None, init=True)
    server_password: str | None = field(default=None, init=True)


@dataclass
class ServerPasswordResetInfo:
    server_id: str
    server_user: str
    server_password: str


@dataclass(kw_only=True)
class ServerCreatedInfo(ServerInfo):
    description: str


@dataclass
class ServerDeletedInfo:
    server_id: str
    deleted: bool
    message: ExecutionMessage | None = field(default=None, init=True)


class ServerTypeBase(metaclass=ABCMeta):
    """Base class for a ServerType"""

    def __init__(self, **kwargs):
        # set maximum parallel runners. None means as many as workers are available.
        self.parallel_runners_limit = None
        self.auto_delete_after = timedelta(days=1)

    def get_server_instance(
        self, model_instance_id
    ) -> ProvisionedServerInstance:
        from server.models import ProvisionedServerInstance

        return ProvisionedServerInstance.objects.get(id=model_instance_id)

    @abstractmethod
    def create_instance(
        self, model_instance_id, *args, **kwargs
    ) -> ServerCreatedInfo:
        ...

    @abstractmethod
    def get_server_info(
        self, model_instance_id, *args, **kwargs
    ) -> ServerInfo:
        ...

    @abstractmethod
    def delete_server(
        self, model_instance_id, *args, **kwargs
    ) -> ServerDeletedInfo:
        ...

    def prolong_server(
        self, model_instance_id, *args, **kwargs
    ) -> ServerInfo | None:
        """This method can be overridden, default is to do nothing"""
        return None

    @classmethod
    def _create_random_string(
        cls, size=6, choice_pool=string.ascii_letters + string.digits
    ):
        return ''.join(random.choice(choice_pool) for _ in range(size))

    @classmethod
    def _create_random_name(cls):
        return cls._create_random_string(choice_pool=string.ascii_letters)


class StartServerMixin(metaclass=ABCMeta):
    """Mixin class for starting a server"""

    @abstractmethod
    def start_server(self, model_instance_id, *args, **kwargs) -> ServerInfo:
        ...


class RestartServerMixin(metaclass=ABCMeta):
    """Mixin class for restarting a server"""

    @abstractmethod
    def restart_server(self, model_instance_id, *args, **kwargs) -> ServerInfo:
        ...


class ResetPasswordMixin(metaclass=ABCMeta):
    """Mixin class for resetting a server password"""

    @abstractmethod
    def reset_password(
        self, model_instance_id, *args, **kwargs
    ) -> ServerPasswordResetInfo:
        ...


class StopServerMixin(metaclass=ABCMeta):
    """Mixin class for stopping a server"""

    @abstractmethod
    def stop_server(self, model_instance_id, *args, **kwargs) -> ServerInfo:
        ...


class ServerTypeFactory:
    """The factory class for creating ServerTypes"""

    registry: dict[str, Callable] = {}

    @classmethod
    def register(cls, name_id: str) -> Callable:
        """Class method to register ServerType class to the internal registry.
        Args:
            name_id (str): The unique name (id) of the server type.
        Returns:
            The Server Type class itself.
        """

        def inner_wrapper(wrapped_class: Callable) -> Callable:
            if name_id in cls.registry:
                logger.warning(
                    f'Server Type {name_id} already exists. It will be replaced.'
                )
            cls.registry[name_id] = wrapped_class
            return wrapped_class

        return inner_wrapper

    @classmethod
    def remove(cls, name: str) -> None:
        """Remove a ServerType from the internal registry.
        Args:
            name (str): The name of the server type.
        """
        if name in cls.registry:
            del cls.registry[name]

    @classmethod
    def create_server_type(
        cls, name: str, **kwargs
    ) -> ServerTypeBase | StartServerMixin | ResetPasswordMixin | RestartServerMixin | StopServerMixin:
        if name not in cls.registry:
            logger.error(
                'ServerType {name} does not exist in the registry', name
            )
            raise ValueError(
                f'ServerType {name} does not exist in the registry'
            )

        server_type_class = cls.registry[name]
        server_type = server_type_class(**kwargs)
        return server_type
