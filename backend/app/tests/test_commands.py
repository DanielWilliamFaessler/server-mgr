# import pytest
# import json
#
# import server_mgr.server_template_executor
# from server_mgr.example_server_template.commands import (
#     ServerDeleteResponse,
#     ServerInfoResponse,
#     create,
#     get_infos,
#     reboot,
#     start,
#     stop,
#     create_new_password,
#     delete,
# )
# from server_mgr.server_template_executor import run, ShellExecutionResult
#
#
# def test_run_failed_command_has_reason():
#     res = run('exit 1')
#     assert res.success == False
#     assert res.reason == "Command 'exit 1' returned non-zero exit status 1."
#     assert res.result == ''
#     # error is empty in this case, since no output has been created
#     assert res.error == ''
#
#
# def test_run_failed_command_has_error_output():
#     res = run('ls -lah /nonexistend-place')
#     assert res.success == False
#     assert (
#         res.reason
#         == "Command 'ls -lah /nonexistend-place' returned non-zero exit status 2."
#     )
#     assert res.result == ''
#     # error is empty in this case, since no output has been created
#     assert (
#         res.error.strip('\n')
#         == "ls: cannot access '/nonexistend-place': No such file or directory"
#     )
#
#
# def test_run_succeeded_command_contains_expected_results():
#     res = run('echo "I did run successfully"')
#     assert res.success == True
#     assert res.reason is None
#     assert res.result.strip('\n') == 'I did run successfully'
#     # error is empty in this case, since no output has been created
#     assert res.error == ''
#
#
# @pytest.fixture
# def server_id():
#     return '<username>-special-id-special-id'
#
#
# @pytest.fixture
# def started_info(server_id):
#     return {
#         'server_id': server_id,
#         'server_ip': '123.23.23.12',
#         'server_username': 'root',
#         'server_password': 'insecure-root-password-that-should-not-be-used',
#         'server_extra_infos': {},
#         'server_is_running': True,
#         'success': True,
#         'user_message': 'successfully created. Please use ssh://root@{{ server_id }} to login',
#         'admin_message': '',
#     }
#
#
# @pytest.fixture
# def stopped_info(server_id):
#     return {
#         'server_id': server_id,
#         'server_ip': '123.23.23.12',
#         'server_username': 'root',
#         'server_password': 'insecure-root-password-that-should-not-be-used',
#         'server_extra_infos': {},
#         'server_is_running': False,
#         'success': True,
#         'user_message': 'successfully created. Please use ssh://root@{{ server_id }} to login',
#         'admin_message': '',
#     }
#
#
# @pytest.fixture
# def pwchange_info(server_id):
#     return {
#         'server_id': server_id,
#         'server_ip': '123.23.23.12',
#         'server_username': 'root',
#         'server_password': 'another-insecure-root-password-that-should-not-be-used',
#         'server_extra_infos': {},
#         'server_is_running': True,
#         'success': True,
#         'user_message': 'successfully created. Please use ssh://root@{{ server_id }} to login',
#         'admin_message': '',
#     }
#
#
# @pytest.fixture
# def deleted_info(server_id):
#     return {
#         'server_id': server_id,
#         'server_is_running': False,
#         'success': True,
#         'user_message': 'Server has been deleted.',
#         'admin_message': '',
#     }
#
#
# def test_sunny_workflow(
#     monkeypatch,
#     started_info,
#     stopped_info,
#     pwchange_info,
#     deleted_info,
#     server_id,
# ):
#     assert started_info['server_id'] == server_id
#     assert stopped_info['server_id'] == server_id
#     assert pwchange_info['server_id'] == server_id
#     assert deleted_info['server_id'] == server_id
#
#     with monkeypatch.context() as m:
#         m.setattr(
#             'server_mgr.example_server_template.commands.run',
#             lambda *args, **kwargs: ShellExecutionResult(
#                 result=json.dumps(started_info)
#             ),
#         )
#
#         server_info_create = create(server_id)
#         assert server_info_create.success == True
#
#         assert server_info_create.server_id == server_id
#         server_info = get_infos(server_id)
#         assert server_info.success == True
#         assert server_info.server_is_running == True
#         assert server_info_create.server_id == server_info.server_id
#         assert server_info_create.server_ip == server_info.server_ip
#         assert (
#             server_info_create.server_username == server_info.server_username
#         )
#         assert (
#             server_info_create.server_password == server_info.server_password
#         )
#
#         server_info = get_infos(server_id)
#         server_id = server_info.server_id
#
#         server_info = reboot(server_id)
#         assert server_info.success == True
#         assert server_info.server_is_running == True
#         assert server_info_create.server_id == server_info.server_id
#         assert server_info_create.server_ip == server_info.server_ip
#         assert (
#             server_info_create.server_username == server_info.server_username
#         )
#         assert (
#             server_info_create.server_password == server_info.server_password
#         )
#
#     with monkeypatch.context() as m:
#         m.setattr(
#             'server_mgr.example_server_template.commands.run',
#             lambda *args, **kwargs: ShellExecutionResult(
#                 result=json.dumps(stopped_info)
#             ),
#         )
#
#         server_info = stop(server_id)
#         assert server_info.success == True
#         assert server_info.server_is_running == False
#         assert server_info_create.server_id == server_info.server_id
#         assert server_info_create.server_ip == server_info.server_ip
#         assert (
#             server_info_create.server_username == server_info.server_username
#         )
#         assert (
#             server_info_create.server_password == server_info.server_password
#         )
#
#     with monkeypatch.context() as m:
#         m.setattr(
#             'server_mgr.example_server_template.commands.run',
#             lambda *args, **kwargs: ShellExecutionResult(
#                 result=json.dumps(started_info)
#             ),
#         )
#
#         server_info = start(server_id)
#         assert server_info.success == True
#         assert server_info.server_is_running == True
#         assert server_info_create.server_id == server_info.server_id
#         # ip can be changed when the tool supports deep sleep/archiving and unarchiving.
#         assert server_info.server_ip is not None
#         assert (
#             server_info_create.server_username == server_info.server_username
#         )
#         assert (
#             server_info_create.server_password == server_info.server_password
#         )
#
#         # doing a start even when running should be OK.
#         server_info = start(server_id)
#         assert server_info.success == True
#         assert server_info.server_is_running == True
#         assert server_info_create.server_id == server_info.server_id
#         # ip can be changed when the tool supports deep sleep/archiving and unarchiving.
#         assert server_info.server_ip is not None
#         assert (
#             server_info_create.server_username == server_info.server_username
#         )
#         assert (
#             server_info_create.server_password == server_info.server_password
#         )
#
#     with monkeypatch.context() as m:
#         m.setattr(
#             'server_mgr.example_server_template.commands.run',
#             lambda *args, **kwargs: ShellExecutionResult(
#                 result=json.dumps(pwchange_info)
#             ),
#         )
#         server_info = create_new_password(server_id)
#         assert server_info.success == True
#         assert server_info.server_is_running == True
#         assert server_info_create.server_id == server_info.server_id
#         # ip can be changed when the tool supports deep sleep/archiving and unarchiving.
#         assert server_info.server_ip is not None
#         assert (
#             server_info_create.server_username == server_info.server_username
#         )
#         assert (
#             server_info_create.server_password != server_info.server_password
#         )
#
#     with monkeypatch.context() as m:
#         m.setattr(
#             'server_mgr.example_server_template.commands.run',
#             lambda *args, **kwargs: ShellExecutionResult(
#                 result=json.dumps(deleted_info)
#             ),
#         )
#         server_info = delete(server_id)
#         assert server_info.success == True
#         assert server_info.server_is_running == False
#
