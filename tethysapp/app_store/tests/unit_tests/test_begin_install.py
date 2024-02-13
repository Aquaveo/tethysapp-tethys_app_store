from unittest.mock import call, MagicMock
from tethysapp.app_store.begin_install import (handle_property_not_present, process_post_install_scripts,
                                               detect_app_dependencies, begin_install)


def test_handle_property_not_present():
    handle_property_not_present("")


def test_process_post_install_scripts(tmp_path):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()

    process_post_install_scripts(tmp_path)


def test_detect_app_dependencies_pip_no_settings(mocker, tethysapp_base_with_application_files):
    app_name = "test_app"
    channel_layer = MagicMock()
    mock_ws = MagicMock()
    mocker.patch('tethysapp.app_store.begin_install.call')
    mocker.patch('tethysapp.app_store.begin_install.cache')
    mocker.patch('tethysapp.app_store.begin_install.importlib')
    mock_subprocess = mocker.patch('tethysapp.app_store.begin_install.subprocess')
    mock_subprocess.Popen().stdout.readline.side_effect = ["still_running", "PIP Install Complete"]
    mock_tethysapp = mocker.patch('tethysapp.app_store.begin_install.tethysapp')
    mock_app = MagicMock()
    mock_app.custom_settings.return_value = []
    mocker.patch('tethysapp.app_store.begin_install.get_app_instance_from_path', return_value=mock_app)

    mock_tethysapp.__path__ = [str(tethysapp_base_with_application_files / "tethysapp")]

    detect_app_dependencies(app_name, channel_layer, mock_ws)

    expected_data_json = {
        "data": [],
        "returnMethod": "set_custom_settings",
        "jsHelperFunction": "processCustomSettings",
        "app_py_path": str(tethysapp_base_with_application_files / "tethysapp")
    }
    mock_ws.assert_has_calls([
        call("Running PIP install....", channel_layer),
        call("PIP install completed", channel_layer),
        call(expected_data_json, channel_layer)
    ])
    assert mock_subprocess.Popen().stdout.readline.call_count == 2


def test_detect_app_dependencies_pip_settings(mocker, tethysapp_base_with_application_files):
    app_name = "test_app"
    channel_layer = MagicMock()
    mock_ws = MagicMock()
    mocker.patch('tethysapp.app_store.begin_install.call')
    mocker.patch('tethysapp.app_store.begin_install.cache')
    mocker.patch('tethysapp.app_store.begin_install.importlib')
    mock_subprocess = mocker.patch('tethysapp.app_store.begin_install.subprocess')
    mock_subprocess.Popen().stdout.readline.side_effect = [""]
    mock_tethysapp = mocker.patch('tethysapp.app_store.begin_install.tethysapp')
    mock_app = MagicMock()
    mock_setting = MagicMock(default="some_value", description="description", required=True)
    mock_setting.name = "name"
    mock_app.custom_settings.return_value = [mock_setting]
    mocker.patch('tethysapp.app_store.begin_install.get_app_instance_from_path', return_value=mock_app)

    mock_tethysapp.__path__ = [str(tethysapp_base_with_application_files / "tethysapp")]

    detect_app_dependencies(app_name, channel_layer, mock_ws)

    expected_data_json = {
        "data": [{"name": "name", "description": "description", "required": True, "default": "some_value"}],
        "returnMethod": "set_custom_settings",
        "jsHelperFunction": "processCustomSettings",
        "app_py_path": str(tethysapp_base_with_application_files / "tethysapp")
    }
    mock_ws.assert_has_calls([
        call("Running PIP install....", channel_layer),
        call("PIP install completed", channel_layer),
        call("Processing App's Custom Settings....", channel_layer),
        call(expected_data_json, channel_layer)
    ])
    assert mock_subprocess.Popen().stdout.readline.call_count == 1


def test_detect_app_dependencies_pip_settings_workspace_default(mocker, tethysapp_base_with_application_files,
                                                                tmp_path):
    app_name = "test_app"
    channel_layer = MagicMock()
    mock_ws = MagicMock()
    mocker.patch('tethysapp.app_store.begin_install.call')
    mocker.patch('tethysapp.app_store.begin_install.cache')
    mocker.patch('tethysapp.app_store.begin_install.importlib')
    mock_subprocess = mocker.patch('tethysapp.app_store.begin_install.subprocess')
    mock_subprocess.Popen().stdout.readline.side_effect = [""]
    mock_tethysapp = mocker.patch('tethysapp.app_store.begin_install.tethysapp')
    mock_app = MagicMock()
    mock_workspace = MagicMock(path=str(tmp_path))
    mocker.patch('tethysapp.app_store.begin_install.isinstance', return_value=True)
    mock_setting = MagicMock(default=mock_workspace, description="description", required=True)
    mock_setting.name = "name"
    mock_app.custom_settings.return_value = [mock_setting]
    mocker.patch('tethysapp.app_store.begin_install.get_app_instance_from_path', return_value=mock_app)

    mock_tethysapp.__path__ = [str(tethysapp_base_with_application_files / "tethysapp")]

    detect_app_dependencies(app_name, channel_layer, mock_ws)

    expected_data_json = {
        "data": [{"name": "name", "description": "description", "required": True, "default": str(tmp_path)}],
        "returnMethod": "set_custom_settings",
        "jsHelperFunction": "processCustomSettings",
        "app_py_path": str(tethysapp_base_with_application_files / "tethysapp")
    }
    mock_ws.assert_has_calls([
        call("Running PIP install....", channel_layer),
        call("PIP install completed", channel_layer),
        call("Processing App's Custom Settings....", channel_layer),
        call(expected_data_json, channel_layer)
    ])
    assert mock_subprocess.Popen().stdout.readline.call_count == 1


def test_detect_app_dependencies_no_pip_no_settings(mocker, tethysapp_base_with_application_files):
    test_install_pip = tethysapp_base_with_application_files / "tethysapp" / "test_app" / "scripts" / "install_pip.sh"
    test_install_pip.unlink()
    app_name = "test_app"
    channel_layer = MagicMock()
    mock_ws = MagicMock()
    mocker.patch('tethysapp.app_store.begin_install.call')
    mocker.patch('tethysapp.app_store.begin_install.cache')
    mocker.patch('tethysapp.app_store.begin_install.importlib')
    mock_subprocess = mocker.patch('tethysapp.app_store.begin_install.subprocess')
    mock_tethysapp = mocker.patch('tethysapp.app_store.begin_install.tethysapp')
    mock_app = MagicMock()
    mock_app.custom_settings.return_value = []
    mocker.patch('tethysapp.app_store.begin_install.get_app_instance_from_path', return_value=mock_app)

    mock_tethysapp.__path__ = [str(tethysapp_base_with_application_files / "tethysapp")]

    detect_app_dependencies(app_name, channel_layer, mock_ws)

    expected_data_json = {
        "data": [],
        "returnMethod": "set_custom_settings",
        "jsHelperFunction": "processCustomSettings",
        "app_py_path": str(tethysapp_base_with_application_files / "tethysapp")
    }
    mock_ws.assert_called_once_with(expected_data_json, channel_layer)
    assert mock_subprocess.Popen().stdout.readline.call_count == 0


def test_detect_app_dependencies_no_app_path(mocker, caplog):
    app_name = "test_app"
    channel_layer = MagicMock()
    mock_ws = MagicMock()
    mocker.patch('tethysapp.app_store.begin_install.call')
    mocker.patch('tethysapp.app_store.begin_install.cache')
    mocker.patch('tethysapp.app_store.begin_install.importlib')
    mock_tethysapp = mocker.patch('tethysapp.app_store.begin_install.tethysapp')

    mock_tethysapp.__path__ = []

    detect_app_dependencies(app_name, channel_layer, mock_ws)

    mock_ws.assert_not_called()
    assert "Can't find the installed app location." in caplog.messages


def test_begin_install(resource, mocker):
    mock_channel = MagicMock()
    mock_workspace = MagicMock()
    app_name = "test_app"
    app_channel = "test_channel"
    app_label = "main"
    app_resource = resource(app_name, app_channel, app_label)
    app_version = app_resource['latestVersion'][app_channel][app_label]
    install_data = {
        "name": app_name,
        "label": app_label,
        "channel": app_channel,
        "version": app_version
    }

    mock_ws = mocker.patch('tethysapp.app_store.begin_install.send_notification')
    mocker.patch('tethysapp.app_store.begin_install.get_resource', return_value=app_resource)
    mocker.patch('tethysapp.app_store.begin_install.mamba_install', return_value=True)
    mocker.patch('tethysapp.app_store.begin_install.detect_app_dependencies')

    begin_install(install_data, mock_channel, mock_workspace)

    mock_ws.assert_has_calls([
        call(f"Starting installation of app: {app_name} from store {app_channel} with label {app_label}", mock_channel),
        call(f"Installing Version: {app_version}", mock_channel),
    ])


def test_begin_install_no_resource(mocker):
    mock_channel = MagicMock()
    mock_workspace = MagicMock()
    app_name = "test_app"
    app_channel = "test_channel"
    app_label = "main"
    install_data = {
        "name": app_name,
        "label": app_label,
        "channel": app_channel,
        "version": "1.0"
    }

    mock_ws = mocker.patch('tethysapp.app_store.begin_install.send_notification')
    mocker.patch('tethysapp.app_store.begin_install.get_resource', return_value=None)

    begin_install(install_data, mock_channel, mock_workspace)

    mock_ws.assert_has_calls([
        call(f"Failed to get the {install_data['name']} resource", mock_channel)
    ])


def test_begin_install_failed_install(resource, mocker):
    mock_channel = MagicMock()
    mock_workspace = MagicMock()
    app_name = "test_app"
    app_channel = "test_channel"
    app_label = "main"
    app_resource = resource(app_name, app_channel, app_label)
    app_version = app_resource['latestVersion'][app_channel][app_label]
    install_data = {
        "name": app_name,
        "label": app_label,
        "channel": app_channel,
        "version": app_version
    }

    mock_ws = mocker.patch('tethysapp.app_store.begin_install.send_notification')
    mocker.patch('tethysapp.app_store.begin_install.get_resource', return_value=app_resource)
    mocker.patch('tethysapp.app_store.begin_install.mamba_install', return_value=False)

    begin_install(install_data, mock_channel, mock_workspace)

    mock_ws.assert_has_calls([
        call(f"Starting installation of app: {app_name} from store {app_channel} with label {app_label}", mock_channel),
        call(f"Installing Version: {app_version}", mock_channel),
        call("Application installation failed. Check logs for more details.", mock_channel)
    ])
