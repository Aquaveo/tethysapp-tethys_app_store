from conda.exceptions import PackagesNotFoundError
from unittest.mock import MagicMock, call
from tethys_apps.exceptions import TethysAppSettingNotAssigned
from tethysapp.app_store.uninstall_handlers import uninstall_app


def test_uninstall_app_tethysapp(mocker, caplog):
    mock_sn = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.send_uninstall_messages"
    )
    mock_subprocess = mocker.patch("tethysapp.app_store.uninstall_handlers.subprocess")
    mock_subprocess.Popen().stdout.readline.side_effect = [
        "Running Mamba remove\n",
        "Transaction starting\n",
        "Transaction finished\n",
        "Mamba Remove Complete\n",
    ]
    mocker.patch(
        "tethysapp.app_store.uninstall_handlers.get_manage_path",
        return_value="manage_path",
    )
    mock_setting = MagicMock()
    mock_setting.__str__.side_effect = ["setting1"]
    mock_setting.persistent_store_database_exists.side_effect = [True]
    mock_app = MagicMock(persistent_store_database_settings=[mock_setting])
    mocker.patch(
        "tethysapp.app_store.uninstall_handlers.TethysApp.objects.filter",
        side_effect=[[mock_app]],
    )
    mock_mamba_uninstall = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.mamba_uninstall"
    )
    mock_channel = MagicMock()
    mock_workspace = MagicMock()

    uninstall_data = {"name": "test_app", "app_type": "tethysapp"}
    uninstall_app(uninstall_data, mock_channel, mock_workspace)

    mock_subprocess.call.assert_called_with(
        ["python", "manage_path", "tethys_app_uninstall", "test_app", "-f"]
    )
    mock_mamba_uninstall.assert_called_with("test_app", mock_channel)
    mock_sn.assert_has_calls(
        [
            call("Starting Uninstall. Please wait...", mock_channel),
            call(
                "Tethys App Uninstalled. Running Conda/GitHub Cleanup...", mock_channel
            ),
            call("Uninstall completed. Restarting server...", mock_channel),
        ]
    )
    assert "Dropping Database for persistent store setting: setting1" in caplog.messages


def test_uninstall_app_proxyapp(mocker):
    mock_sn = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.send_uninstall_messages"
    )
    mock_delete_proxy_app = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.delete_proxy_app"
    )
    mock_mamba_uninstall = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.mamba_uninstall"
    )
    mock_channel = MagicMock()
    mock_workspace = MagicMock()

    uninstall_data = {"name": "test_app", "app_type": "proxyapp"}
    uninstall_app(uninstall_data, mock_channel, mock_workspace)

    expected_uninstall_data = uninstall_data
    expected_uninstall_data["app_name"] = expected_uninstall_data["name"].replace(
        "proxyapp_", ""
    )
    mock_delete_proxy_app.assert_called_with(expected_uninstall_data, mock_channel)
    mock_mamba_uninstall.assert_called_with("test_app", mock_channel)
    mock_sn.assert_has_calls(
        [
            call("Starting Uninstall. Please wait...", mock_channel),
            call("Uninstalling Proxy App", mock_channel),
            call("Uninstall completed. Restarting server...", mock_channel),
        ]
    )


def test_uninstall_app_no_persistent_stores(mocker, caplog):
    mock_sn = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.send_uninstall_messages"
    )
    mock_subprocess = mocker.patch("tethysapp.app_store.uninstall_handlers.subprocess")
    mock_subprocess.Popen().stdout.readline.side_effect = [
        "Running Mamba remove\n",
        "Transaction starting\n",
        "Transaction finished\n",
        "Mamba Remove Complete\n",
    ]
    mock_subprocess.call.side_effect = [KeyboardInterrupt]
    mocker.patch(
        "tethysapp.app_store.uninstall_handlers.get_manage_path",
        return_value="manage_path",
    )
    mock_app = MagicMock(persistent_store_database_settings=[])
    mocker.patch(
        "tethysapp.app_store.uninstall_handlers.TethysApp.objects.filter",
        side_effect=[[mock_app]],
    )
    mock_mamba_uninstall = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.mamba_uninstall"
    )
    mock_channel = MagicMock()
    mock_workspace = MagicMock()

    uninstall_data = {"name": "test_app", "app_type": "tethysapp"}
    uninstall_app(uninstall_data, mock_channel, mock_workspace)

    mock_subprocess.call.assert_called_with(
        ["python", "manage_path", "tethys_app_uninstall", "test_app", "-f"]
    )
    mock_mamba_uninstall.assert_called_with("test_app", mock_channel)
    mock_sn.assert_has_calls(
        [
            call("Starting Uninstall. Please wait...", mock_channel),
            call(
                "Tethys App Uninstalled. Running Conda/GitHub Cleanup...", mock_channel
            ),
            call("Uninstall completed. Restarting server...", mock_channel),
        ]
    )
    assert "No Persistent store services found for: test_app" in caplog.messages


def test_uninstall_app_no_target_app(mocker, caplog):
    mock_sn = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.send_uninstall_messages"
    )
    mock_subprocess = mocker.patch("tethysapp.app_store.uninstall_handlers.subprocess")
    mock_subprocess.Popen().stdout.readline.side_effect = [
        "Running Mamba remove\n",
        "Transaction starting\n",
        "Transaction finished\n",
        "Mamba Remove Complete\n",
    ]
    mocker.patch(
        "tethysapp.app_store.uninstall_handlers.get_manage_path",
        return_value="manage_path",
    )
    mocker.patch(
        "tethysapp.app_store.uninstall_handlers.TethysApp.objects.filter",
        side_effect=[[]],
    )
    mock_mamba_uninstall = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.mamba_uninstall"
    )
    mock_channel = MagicMock()
    mock_workspace = MagicMock()

    uninstall_data = {"name": "test_app", "app_type": "tethysapp"}
    uninstall_app(uninstall_data, mock_channel, mock_workspace)

    mock_subprocess.call.assert_called_with(
        ["python", "manage_path", "tethys_app_uninstall", "test_app", "-f"]
    )
    mock_mamba_uninstall.assert_called_with("test_app", mock_channel)
    mock_sn.assert_has_calls(
        [
            call("Starting Uninstall. Please wait...", mock_channel),
            call(
                "Tethys App Uninstalled. Running Conda/GitHub Cleanup...", mock_channel
            ),
            call("Uninstall completed. Restarting server...", mock_channel),
        ]
    )
    assert (
        "Couldn't find the target application for removal of databases. Continuing clean up"
        in caplog.messages
    )


def test_uninstall_app_bad_setting(mocker, caplog):
    mock_sn = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.send_uninstall_messages"
    )
    mock_subprocess = mocker.patch("tethysapp.app_store.uninstall_handlers.subprocess")
    mock_subprocess.Popen().stdout.readline.side_effect = [
        "Running Mamba remove\n",
        "Transaction starting\n",
        "Transaction finished\n",
        "Mamba Remove Complete\n",
    ]
    mocker.patch(
        "tethysapp.app_store.uninstall_handlers.get_manage_path",
        return_value="manage_path",
    )
    mock_setting = MagicMock()
    mock_setting.__str__.side_effect = ["setting1"]
    mock_setting.persistent_store_database_exists.side_effect = [
        Exception("bad_setting")
    ]
    mock_app = MagicMock(persistent_store_database_settings=[mock_setting])
    mocker.patch(
        "tethysapp.app_store.uninstall_handlers.TethysApp.objects.filter",
        side_effect=[[mock_app]],
    )
    mock_mamba_uninstall = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.mamba_uninstall"
    )
    mock_channel = MagicMock()
    mock_workspace = MagicMock()

    uninstall_data = {"name": "test_app", "app_type": "tethysapp"}
    uninstall_app(uninstall_data, mock_channel, mock_workspace)

    mock_subprocess.call.assert_called_with(
        ["python", "manage_path", "tethys_app_uninstall", "test_app", "-f"]
    )
    mock_mamba_uninstall.assert_called_with("test_app", mock_channel)
    mock_sn.assert_has_calls(
        [
            call("Starting Uninstall. Please wait...", mock_channel),
            call(
                "Tethys App Uninstalled. Running Conda/GitHub Cleanup...", mock_channel
            ),
            call("Uninstall completed. Restarting server...", mock_channel),
        ]
    )
    assert "bad_setting" in caplog.messages
    assert (
        "Couldn't connect to database for removal. Continuing clean up"
        in caplog.messages
    )


def test_uninstall_app_setting_not_assigned(mocker):
    mock_sn = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.send_uninstall_messages"
    )
    mock_subprocess = mocker.patch("tethysapp.app_store.uninstall_handlers.subprocess")
    mock_subprocess.Popen().stdout.readline.side_effect = [
        "Running Mamba remove\n",
        "Transaction starting\n",
        "Transaction finished\n",
        "",
    ]
    mocker.patch(
        "tethysapp.app_store.uninstall_handlers.get_manage_path",
        return_value="manage_path",
    )
    mock_setting = MagicMock()
    mock_setting.__str__.side_effect = ["setting1"]
    mock_setting.persistent_store_database_exists.side_effect = [
        TethysAppSettingNotAssigned
    ]
    mock_app = MagicMock(persistent_store_database_settings=[mock_setting])
    mocker.patch(
        "tethysapp.app_store.uninstall_handlers.TethysApp.objects.filter",
        side_effect=[[mock_app]],
    )
    mock_mamba_uninstall = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.mamba_uninstall"
    )
    mock_channel = MagicMock()
    mock_workspace = MagicMock()

    uninstall_data = {"name": "test_app", "app_type": "tethysapp"}
    uninstall_app(uninstall_data, mock_channel, mock_workspace)

    mock_subprocess.call.assert_called_with(
        ["python", "manage_path", "tethys_app_uninstall", "test_app", "-f"]
    )
    mock_mamba_uninstall.assert_called_with("test_app", mock_channel)
    mock_sn.assert_has_calls(
        [
            call("Starting Uninstall. Please wait...", mock_channel),
            call(
                "Tethys App Uninstalled. Running Conda/GitHub Cleanup...", mock_channel
            ),
            call("Uninstall completed. Restarting server...", mock_channel),
        ]
    )


def test_uninstall_app_proxyapp_PackagesNotFoundError(mocker):
    mock_sn = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.send_uninstall_messages"
    )
    mock_delete_proxy_app = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.delete_proxy_app"
    )
    mock_mamba_uninstall = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.mamba_uninstall"
    )
    mock_shutil = mocker.patch("tethysapp.app_store.uninstall_handlers.shutil")
    mock_clear_github_cache_list = mocker.patch(
        "tethysapp.app_store.uninstall_handlers.clear_github_cache_list"
    )
    mock_mamba_uninstall.side_effect = [PackagesNotFoundError("test_app")]
    git_app = {"name": "test_app", "path": "app_path"}
    mocker.patch(
        "tethysapp.app_store.uninstall_handlers.get_github_install_metadata",
        side_effect=[[git_app]],
    )
    mock_channel = MagicMock()
    mock_workspace = MagicMock()

    uninstall_data = {"name": "test_app", "app_type": "proxyapp"}

    uninstall_app(uninstall_data, mock_channel, mock_workspace)

    expected_uninstall_data = uninstall_data
    expected_uninstall_data["app_name"] = expected_uninstall_data["name"].replace(
        "proxyapp_", ""
    )
    mock_delete_proxy_app.assert_called_with(expected_uninstall_data, mock_channel)
    mock_mamba_uninstall.assert_called_with("test_app", mock_channel)
    mock_sn.assert_has_calls(
        [
            call("Starting Uninstall. Please wait...", mock_channel),
            call("Uninstalling Proxy App", mock_channel),
            call("Uninstall completed. Restarting server...", mock_channel),
        ]
    )
    mock_shutil.rmtree.assert_called_with("app_path")
    mock_clear_github_cache_list.assert_called()
