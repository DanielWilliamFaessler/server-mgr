from django.utils import timezone

import pytest

from server.server_registration import (
    ExecutionMessage,
    ServerInfo,
    ServerState,
)
from server.tasks import add_message_content_to_server_instance


@pytest.fixture
def dummy_task_name():
    return 'dummy-task'


@pytest.mark.django_db
def test_add_message_content_to_server_instance(
    dummy_task_name,
    dummy_active_server_type,
    dummy_server_info,
    dummy_provisioned_server_instance,
):
    instance = dummy_provisioned_server_instance

    assert instance.server_id == dummy_server_info.server_id
    assert instance.server_type == dummy_active_server_type

    # there should be no change, when the info is the same
    add_message_content_to_server_instance(
        dummy_task_name,
        'dummy-test-run-id',
        dummy_server_info,
        dummy_provisioned_server_instance,
    )
    assert instance.server_id == dummy_server_info.server_id
    assert instance.server_type == dummy_active_server_type

    # there should change, when the info is altered
    new_info = ServerInfo(
        server_address='1.2.3.4',
        created=timezone.now(),
        labels=['new-label'],
        usage='Another Info about the usage for test-dummy',
        server_name='new-name',
        message=ExecutionMessage(user_message='new-message'),
        server_password='new-password',
        server_user='new-username',
        server_id='asdadadsadasdasd',
        server_state=ServerState.STOPPED,
    )
    add_message_content_to_server_instance(
        dummy_task_name,
        'another-dummy-run-id',
        new_info,
        dummy_provisioned_server_instance,
    )
    assert instance.server_id == new_info.server_id
    assert instance.server_address == new_info.server_address
    assert instance.server_name == new_info.server_name
    assert instance.server_password == new_info.server_password
    assert instance.server_user == new_info.server_user
    assert instance.server_state == new_info.server_state.value

    #  but hopefuly the unchangeable info is still unchanged
    assert instance.created < new_info.created
    user_messages = instance.user_messages()
    assert user_messages.count() == 1
    assert user_messages[0].user_message == new_info.message.user_message
