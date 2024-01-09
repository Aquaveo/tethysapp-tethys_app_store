import pytest
from unittest.mock import MagicMock
from tethysapp.app_store.helpers import (parse_setup_py, get_conda_stores, check_all_present, run_process,
                                         send_notification, apply_template)


@pytest.mark.parametrize(
    "substrings, expected_outcome", [
        (["This", "testing"], True),
        (["This", "not present"], False)])
def test_check_all_present(substrings, expected_outcome):
    string = "This is a testing string"
    present = check_all_present(string, substrings)

    assert present is expected_outcome


def test_run_process(mocker, caplog):

    mock_run_results = MagicMock(stdout="standard output", returncode=10, stderr="standard error")
    mock_run = mocker.patch('tethysapp.app_store.helpers.run', return_value=mock_run_results)

    args = ["executable", "arg1", "arg2"]
    run_process(args)

    mock_run.assert_called_with(args, capture_output=True)
    assert "standard output" in caplog.messages
    assert "standard error" in caplog.messages


def test_send_notification(mocker):
    channel_layer = MagicMock(group_send="some_function")
    mock_async_to_sync = mocker.patch('tethysapp.app_store.helpers.async_to_sync')
    msg = "testing functionality"

    send_notification(msg, channel_layer)

    expected_args = ["notifications", {"type": "install_notifications", "message": msg}]
    assert mock_async_to_sync.some_function.called_once_with(expected_args)


def test_apply_template(app_files_dir, tmp_path):
    upload_template = app_files_dir / "upload_command.txt"
    data = {"label_string": "main"}
    output_location = tmp_path / "upload_command.txt"

    apply_template(upload_template, data, output_location)

    assert output_location.read_text() == "anaconda upload --force --label main noarch/*.tar.bz2"


def test_parse_setup_py(test_files_dir):
    setup_py = test_files_dir / "setup.py"

    parsed_data = parse_setup_py(setup_py)

    expected_data = {
        'name': 'release_package', 'version': '0.0.1', 'description': 'example',
        'long_description': 'This is just an example for testing', 'keywords': 'example,test',
        'author': 'Tester', 'author_email': 'tester@email.com', 'url': '', 'license': 'BSD-3'
    }
    assert parsed_data == expected_data


def test_get_conda_stores(mocker, store):
    mock_app = mocker.patch('tethysapp.app_store.helpers.app')
    encryption_key = 'fake_encryption_key'
    active_store = store('active_default')
    inactive_store = store("inactive_not_default", default=False, active=False)
    mock_app.get_custom_setting.side_effect = [{'stores': [active_store, inactive_store]}, encryption_key]
    mocker.patch('tethysapp.app_store.helpers.decrypt', return_value='decrypted_token')

    stores = get_conda_stores()

    active_store['github_token'] = 'decrypted_token'
    inactive_store['github_token'] = 'decrypted_token'
    expected_stores = [active_store, inactive_store]
    assert stores == expected_stores


def test_get_conda_stores_active(mocker, store):
    mock_app = mocker.patch('tethysapp.app_store.helpers.app')
    encryption_key = 'fake_encryption_key'
    active_store = store('active_default')
    inactive_store = store("inactive_not_default", default=False, active=False)
    mock_app.get_custom_setting.side_effect = [{'stores': [active_store, inactive_store]}, encryption_key]
    mocker.patch('tethysapp.app_store.helpers.decrypt', return_value='decrypted_token')

    stores = get_conda_stores(active_only=True)

    active_store['github_token'] = 'decrypted_token'
    expected_stores = [active_store]
    assert stores == expected_stores


def test_get_conda_stores_specific_str(mocker, store):
    mock_app = mocker.patch('tethysapp.app_store.helpers.app')
    encryption_key = 'fake_encryption_key'
    active_store = store('active_default')
    inactive_store = store("inactive_not_default", default=False, active=False)
    mock_app.get_custom_setting.side_effect = [{'stores': [active_store, inactive_store]}, encryption_key]
    mocker.patch('tethysapp.app_store.helpers.decrypt', return_value='decrypted_token')

    stores = get_conda_stores(channel_names="conda_channel_inactive_not_default")

    inactive_store['github_token'] = 'decrypted_token'
    expected_stores = [inactive_store]
    assert stores == expected_stores


def test_get_conda_stores_specific_list(mocker, store):
    mock_app = mocker.patch('tethysapp.app_store.helpers.app')
    encryption_key = 'fake_encryption_key'
    active_store = store('active_default')
    inactive_store = store("inactive_not_default", default=False, active=False)
    mock_app.get_custom_setting.side_effect = [{'stores': [active_store, inactive_store]}, encryption_key]
    mocker.patch('tethysapp.app_store.helpers.decrypt', return_value='decrypted_token')

    stores = get_conda_stores(channel_names=["conda_channel_inactive_not_default", "conda_channel_active_default"])

    active_store['github_token'] = 'decrypted_token'
    inactive_store['github_token'] = 'decrypted_token'
    expected_stores = [active_store, inactive_store]
    assert stores == expected_stores
