from dataclasses import asdict
from datetime import datetime
from typing import Generator, Iterator
from unittest.mock import patch
import pytest

from server.models import ProvisionedServerInstance, ServerType

from server.server_registration import (
    ServerState,
    ServerTypeFactory,
    ServerTypeBase,
    ServerCreatedInfo,
    ServerInfo,
    ServerPasswordResetInfo,
    ServerDeletedInfo,
    ExecutionMessage,
    ServerState,
    RestartServerMixin,
    ResetPasswordMixin,
    StopServerMixin,
    StartServerMixin,
)


@pytest.fixture
def dummy_server_created_info():
    return ServerCreatedInfo(
        server_id='dummy-id',
        server_name='name',
        server_state=ServerState.RUNNING,
        created=datetime.now(),
        server_address='0.0.0.0',
        labels=['labels'],
        description='A user facing description',
    )


@pytest.fixture
def dummy_server_info():
    return ServerInfo(
        server_id='dummy-id',
        server_name='name',
        server_state=ServerState.RUNNING,
        created=datetime.now(),
        server_address='0.0.0.0',
        labels=['labels'],
    )


@pytest.fixture
def dummy_server_deletion_info():
    return ServerDeletedInfo(
        server_id='dummy-id',
        deleted=True,
        message=ExecutionMessage(user_message='Server has been deleted!'),
    )


@pytest.fixture
def dummy_server_type(
    dummy_server_created_info, dummy_server_info, dummy_server_deletion_info
) -> Iterator[str]:
    server_type_name = 'test_dummy_server'

    @ServerTypeFactory.register(server_type_name)
    class DummyServerType(ServerTypeBase):
        def create_instance(self, model_instance_id, *args, **kwargs) -> ServerCreatedInfo:
            return dummy_server_created_info

        def get_server_info(self, model_instance_id, *args, **kwargs) -> ServerInfo:
            return dummy_server_info

        def delete_server(self, model_instance_id, *args, **kwargs) -> ServerDeletedInfo:
            return dummy_server_deletion_info

    yield server_type_name
    ServerTypeFactory.remove(server_type_name)


@pytest.fixture
def extended_dummy_server_type(
    dummy_server_created_info, dummy_server_info, dummy_server_deletion_info
) -> Iterator[str]:
    server_type_name = 'extended_test_dummy_server'

    @ServerTypeFactory.register(server_type_name)
    class ExtendedDummyServerType(
        ServerTypeBase,
        RestartServerMixin,
        StartServerMixin,
        ResetPasswordMixin,
        StopServerMixin,
    ):
        def create_instance(self, model_instance_id, *args, **kwargs) -> ServerCreatedInfo:
            return dummy_server_created_info

        def get_server_info(self, model_instance_id, *args, **kwargs) -> ServerInfo:
            return dummy_server_info

        def reset_password(self, model_instance_id, *args, **kwargs) -> ServerPasswordResetInfo:
            reset_info = dict(
                server_id=dummy_server_info.server_id,
                server_user='new-username',
                server_password='new-password',
            )
            return ServerPasswordResetInfo(**reset_info)

        def start_server(self, model_instance_id, *args, **kwargs) -> ServerInfo:
            kwargs = asdict(dummy_server_info)
            kwargs.update(dict(server_state=ServerState.RUNNING))
            return ServerInfo(**kwargs)

        def restart_server(self, model_instance_id, *args, **kwargs) -> ServerInfo:
            return dummy_server_info

        def stop_server(self, model_instance_id, *args, **kwargs) -> ServerInfo:
            kwargs = asdict(dummy_server_info)
            kwargs.update(dict(server_state=ServerState.STOPPED))
            return ServerInfo(**kwargs)

        def delete_server(self, model_instance_id, *args, **kwargs) -> ServerDeletedInfo:
            return dummy_server_deletion_info

    yield server_type_name
    ServerTypeFactory.remove(server_type_name)


@pytest.fixture
def dummy_active_server_type(dummy_server_type, django_user_model):
    server_type = ServerType(
        name='dummy-active-server-type',
        description='A dummy server type',
        server_type_reference=dummy_server_type,
    )
    server_type.save()
    return server_type


@pytest.fixture
@patch('server.models.tasks.create_server.delay')
def dummy_provisioned_server_instance(
    create_server_mock,
    dummy_active_server_type,
    django_user_model,
    dummy_server_info,
):
    user = django_user_model.objects.create(
        username='example', password='password'
    )
    server_instance = ProvisionedServerInstance.objects.create(
        server_type=dummy_active_server_type,
        user=user,
        server_id=dummy_server_info.server_id,
    )
    create_server_mock.assert_called_with(instance_id=server_instance.id)
    return server_instance
