from conda.exceptions import PackagesNotFoundError
from unittest.mock import MagicMock, call
from tethys_apps.exceptions import TethysAppSettingNotAssigned
from tethysapp.app_store.uninstall_handlers import (send_uninstall_messages, uninstall_app)


def test_send_uninstall_messages(mocker):
    mock_sn = mocker.patch('tethysapp.app_store.uninstall_handlers.send_notification')
    mock_channel = MagicMock()

    message = "uninstall message"
    send_uninstall_messages(message, mock_channel)

    expected_json = {"target": "uninstallNotices", "message": message}
    mock_sn.assert_called_with(expected_json, mock_channel)


def test_uninstall_app(mocker, caplog, app_store_dir):
    mock_sn = mocker.patch('tethysapp.app_store.uninstall_handlers.send_uninstall_messages')
    mock_subprocess = mocker.patch('tethysapp.app_store.uninstall_handlers.subprocess')
    mock_subprocess.Popen().stdout.readline.side_effect = ["Running Mamba remove\n",
                                                           "Transaction starting\n",
                                                           "Transaction finished\n",
                                                           "Mamba Remove Complete\n"]
    mocker.patch('tethysapp.app_store.uninstall_handlers.get_manage_path', return_value="manage_path")
    mock_setting = MagicMock()
    mock_setting.__str__.side_effect = ["setting1"]
    mock_setting.persistent_store_database_exists.side_effect = [True]
    mock_app = MagicMock(persistent_store_database_settings=[mock_setting])
    mocker.patch('tethysapp.app_store.uninstall_handlers.TethysApp.objects.filter', side_effect=[[mock_app]])
    mock_channel = MagicMock()
    mock_workspace = MagicMock()

    uninstall_data = {'name': 'test_app'}
    uninstall_app(uninstall_data, mock_channel, mock_workspace)

    mock_subprocess.call.assert_called_with(['python', "manage_path", 'tethys_app_uninstall', "test_app", "-f"])
    uninstall_script = str(app_store_dir / "scripts" / "mamba_uninstall.sh")
    mock_subprocess.Popen.assert_called_with([uninstall_script, "test_app"],
                                             stdout=mock_subprocess.PIPE, stderr=mock_subprocess.STDOUT)
    mock_sn.assert_has_calls([
        call('Starting Uninstall. Please wait...', mock_channel),
        call('Tethys App Uninstalled. Running Conda/GitHub Cleanup...', mock_channel),
        call("Running uninstall script", mock_channel),
        call("Starting mamba uninstall", mock_channel),
        call("Mamba uninstall complete", mock_channel),
        call('Uninstall completed. Restarting server...', mock_channel)
    ])
    assert "Dropping Database for persistent store setting: setting1" in caplog.messages


def test_uninstall_app_no_persistent_stores(mocker, caplog, app_store_dir):
    mock_sn = mocker.patch('tethysapp.app_store.uninstall_handlers.send_uninstall_messages')
    mock_subprocess = mocker.patch('tethysapp.app_store.uninstall_handlers.subprocess')
    mock_subprocess.Popen().stdout.readline.side_effect = ["Running Mamba remove\n",
                                                           "Transaction starting\n",
                                                           "Transaction finished\n",
                                                           "Mamba Remove Complete\n"]
    mock_subprocess.call.side_effect = [KeyboardInterrupt]
    mocker.patch('tethysapp.app_store.uninstall_handlers.get_manage_path', return_value="manage_path")
    mock_app = MagicMock(persistent_store_database_settings=[])
    mocker.patch('tethysapp.app_store.uninstall_handlers.TethysApp.objects.filter', side_effect=[[mock_app]])
    mock_channel = MagicMock()
    mock_workspace = MagicMock()

    uninstall_data = {'name': 'test_app'}
    uninstall_app(uninstall_data, mock_channel, mock_workspace)

    mock_subprocess.call.assert_called_with(['python', "manage_path", 'tethys_app_uninstall', "test_app", "-f"])
    uninstall_script = str(app_store_dir / "scripts" / "mamba_uninstall.sh")
    mock_subprocess.Popen.assert_called_with([uninstall_script, "test_app"],
                                             stdout=mock_subprocess.PIPE, stderr=mock_subprocess.STDOUT)
    mock_sn.assert_has_calls([
        call('Starting Uninstall. Please wait...', mock_channel),
        call('Tethys App Uninstalled. Running Conda/GitHub Cleanup...', mock_channel),
        call("Running uninstall script", mock_channel),
        call("Starting mamba uninstall", mock_channel),
        call("Mamba uninstall complete", mock_channel),
        call('Uninstall completed. Restarting server...', mock_channel)
    ])
    assert "No Persistent store services found for: test_app" in caplog.messages


def test_uninstall_app_no_target_app(mocker, caplog, app_store_dir):
    mock_sn = mocker.patch('tethysapp.app_store.uninstall_handlers.send_uninstall_messages')
    mock_subprocess = mocker.patch('tethysapp.app_store.uninstall_handlers.subprocess')
    mock_subprocess.Popen().stdout.readline.side_effect = ["Running Mamba remove\n",
                                                           "Transaction starting\n",
                                                           "Transaction finished\n",
                                                           "Mamba Remove Complete\n"]
    mocker.patch('tethysapp.app_store.uninstall_handlers.get_manage_path', return_value="manage_path")
    mocker.patch('tethysapp.app_store.uninstall_handlers.TethysApp.objects.filter', side_effect=[[]])
    mock_channel = MagicMock()
    mock_workspace = MagicMock()

    uninstall_data = {'name': 'test_app'}
    uninstall_app(uninstall_data, mock_channel, mock_workspace)

    mock_subprocess.call.assert_called_with(['python', "manage_path", 'tethys_app_uninstall', "test_app", "-f"])
    uninstall_script = str(app_store_dir / "scripts" / "mamba_uninstall.sh")
    mock_subprocess.Popen.assert_called_with([uninstall_script, "test_app"],
                                             stdout=mock_subprocess.PIPE, stderr=mock_subprocess.STDOUT)
    mock_sn.assert_has_calls([
        call('Starting Uninstall. Please wait...', mock_channel),
        call('Tethys App Uninstalled. Running Conda/GitHub Cleanup...', mock_channel),
        call("Running uninstall script", mock_channel),
        call("Starting mamba uninstall", mock_channel),
        call("Mamba uninstall complete", mock_channel),
        call('Uninstall completed. Restarting server...', mock_channel)
    ])
    assert "Couldn't find the target application for removal of databases. Continuing clean up" in caplog.messages


def test_uninstall_app_bad_setting(mocker, caplog, app_store_dir):
    mock_sn = mocker.patch('tethysapp.app_store.uninstall_handlers.send_uninstall_messages')
    mock_subprocess = mocker.patch('tethysapp.app_store.uninstall_handlers.subprocess')
    mock_subprocess.Popen().stdout.readline.side_effect = ["Running Mamba remove\n",
                                                           "Transaction starting\n",
                                                           "Transaction finished\n",
                                                           "Mamba Remove Complete\n"]
    mocker.patch('tethysapp.app_store.uninstall_handlers.get_manage_path', return_value="manage_path")
    mock_setting = MagicMock()
    mock_setting.__str__.side_effect = ["setting1"]
    mock_setting.persistent_store_database_exists.side_effect = [Exception("bad_setting")]
    mock_app = MagicMock(persistent_store_database_settings=[mock_setting])
    mocker.patch('tethysapp.app_store.uninstall_handlers.TethysApp.objects.filter', side_effect=[[mock_app]])
    mock_channel = MagicMock()
    mock_workspace = MagicMock()

    uninstall_data = {'name': 'test_app'}
    uninstall_app(uninstall_data, mock_channel, mock_workspace)

    mock_subprocess.call.assert_called_with(['python', "manage_path", 'tethys_app_uninstall', "test_app", "-f"])
    uninstall_script = str(app_store_dir / "scripts" / "mamba_uninstall.sh")
    mock_subprocess.Popen.assert_called_with([uninstall_script, "test_app"],
                                             stdout=mock_subprocess.PIPE, stderr=mock_subprocess.STDOUT)
    mock_sn.assert_has_calls([
        call('Starting Uninstall. Please wait...', mock_channel),
        call('Tethys App Uninstalled. Running Conda/GitHub Cleanup...', mock_channel),
        call("Running uninstall script", mock_channel),
        call("Starting mamba uninstall", mock_channel),
        call("Mamba uninstall complete", mock_channel),
        call('Uninstall completed. Restarting server...', mock_channel)
    ])
    assert "bad_setting" in caplog.messages
    assert "Couldn't connect to database for removal. Continuing clean up" in caplog.messages


def test_uninstall_app_setting_not_assigned(mocker, caplog, app_store_dir):
    mock_sn = mocker.patch('tethysapp.app_store.uninstall_handlers.send_uninstall_messages')
    mock_subprocess = mocker.patch('tethysapp.app_store.uninstall_handlers.subprocess')
    mock_subprocess.Popen().stdout.readline.side_effect = ["Running Mamba remove\n",
                                                           "Transaction starting\n",
                                                           "Transaction finished\n",
                                                           ""]
    mocker.patch('tethysapp.app_store.uninstall_handlers.get_manage_path', return_value="manage_path")
    mock_setting = MagicMock()
    mock_setting.__str__.side_effect = ["setting1"]
    mock_setting.persistent_store_database_exists.side_effect = [TethysAppSettingNotAssigned]
    mock_app = MagicMock(persistent_store_database_settings=[mock_setting])
    mocker.patch('tethysapp.app_store.uninstall_handlers.TethysApp.objects.filter', side_effect=[[mock_app]])
    mock_channel = MagicMock()
    mock_workspace = MagicMock()

    uninstall_data = {'name': 'test_app'}
    uninstall_app(uninstall_data, mock_channel, mock_workspace)

    mock_subprocess.call.assert_called_with(['python', "manage_path", 'tethys_app_uninstall', "test_app", "-f"])
    uninstall_script = str(app_store_dir / "scripts" / "mamba_uninstall.sh")
    mock_subprocess.Popen.assert_called_with([uninstall_script, "test_app"],
                                             stdout=mock_subprocess.PIPE, stderr=mock_subprocess.STDOUT)
    mock_sn.assert_has_calls([
        call('Starting Uninstall. Please wait...', mock_channel),
        call('Tethys App Uninstalled. Running Conda/GitHub Cleanup...', mock_channel),
        call("Running uninstall script", mock_channel),
        call("Starting mamba uninstall", mock_channel),
        call("Mamba uninstall complete", mock_channel),
        call('Uninstall completed. Restarting server...', mock_channel)
    ])


def test_uninstall_app_PackagesNotFoundError(mocker, caplog, app_store_dir):
    mock_sn = mocker.patch('tethysapp.app_store.uninstall_handlers.send_uninstall_messages')
    mock_subprocess = mocker.patch('tethysapp.app_store.uninstall_handlers.subprocess')
    mock_subprocess.Popen.side_effect = [PackagesNotFoundError("test_app")]
    mocker.patch('tethysapp.app_store.uninstall_handlers.get_manage_path', return_value="manage_path")
    mock_app = MagicMock(persistent_store_database_settings=[])
    mocker.patch('tethysapp.app_store.uninstall_handlers.TethysApp.objects.filter', side_effect=[[mock_app]])
    git_app = {"name": "test_app", "path": "app_path"}
    mocker.patch('tethysapp.app_store.uninstall_handlers.get_github_install_metadata', side_effect=[[git_app]])
    mocker.patch('tethysapp.app_store.uninstall_handlers.shutil')
    mocker.patch('tethysapp.app_store.uninstall_handlers.clear_github_cache_list')
    mock_channel = MagicMock()
    mock_workspace = MagicMock()

    uninstall_data = {'name': 'test_app'}
    uninstall_app(uninstall_data, mock_channel, mock_workspace)

    mock_subprocess.call.assert_called_with(['python', "manage_path", 'tethys_app_uninstall', "test_app", "-f"])
    uninstall_script = str(app_store_dir / "scripts" / "mamba_uninstall.sh")
    mock_subprocess.Popen.assert_called_with([uninstall_script, "test_app"],
                                             stdout=mock_subprocess.PIPE, stderr=mock_subprocess.STDOUT)
    mock_sn.assert_has_calls([
        call('Starting Uninstall. Please wait...', mock_channel),
        call('Tethys App Uninstalled. Running Conda/GitHub Cleanup...', mock_channel),
        call('Uninstall completed. Restarting server...', mock_channel)
    ])
    assert "No Persistent store services found for: test_app" in caplog.messages
