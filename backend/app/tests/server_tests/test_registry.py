from server.server_registration import ServerState, ServerTypeFactory


def test_registry_simple(dummy_server_type, dummy_server_created_info):
    assert dummy_server_type is not None

    server = ServerTypeFactory.create_server_type(dummy_server_type)
    server_info = server.create_instance(model_instance_id=dummy_server_created_info.server_id)

    assert server_info is not None
    assert dummy_server_type in ServerTypeFactory.registry

    server_info = server.get_server_info(model_instance_id=dummy_server_created_info.server_id)
    assert server_info.server_state == ServerState.RUNNING

    deletion_info = server.delete_server(model_instance_id=dummy_server_created_info.server_id)
    assert deletion_info.deleted == True


def test_registry_optional_methods(
    extended_dummy_server_type, dummy_server_created_info
):
    assert extended_dummy_server_type is not None

    server = ServerTypeFactory.create_server_type(extended_dummy_server_type)
    server_info = server.create_instance(model_instance_id=dummy_server_created_info.server_id)

    assert server_info is not None
    assert extended_dummy_server_type in ServerTypeFactory.registry

    server_info = server.get_server_info(model_instance_id=dummy_server_created_info.server_id)
    assert server_info.server_state == ServerState.RUNNING

    server_pw_reset_info = server.reset_password(
        model_instance_id=dummy_server_created_info.server_id
    )
    assert (
        server_pw_reset_info.server_id == dummy_server_created_info.server_id
    )
    assert server_pw_reset_info.server_user == 'new-username'
    assert server_pw_reset_info.server_password == 'new-password'

    server_info = server.stop_server(model_instance_id=dummy_server_created_info.server_id)
    assert server_info.server_state == ServerState.STOPPED
    assert server_info.server_user is None
    assert server_info.server_password is None

    server_info = server.start_server(model_instance_id=dummy_server_created_info.server_id)
    assert server_info.server_state == ServerState.RUNNING

    server_info = server.restart_server(model_instance_id=dummy_server_created_info.server_id)
    assert server_info.server_state == ServerState.RUNNING

    deletion_info = server.delete_server(model_instance_id=dummy_server_created_info.server_id)
    assert deletion_info.deleted == True
