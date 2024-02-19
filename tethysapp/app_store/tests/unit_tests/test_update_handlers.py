from unittest.mock import MagicMock, call
import yaml
from tethysapp.app_store.update_handlers import update_app, send_update_msg, conda_update


def test_send_update_msg(mocker):
    mock_sn = mocker.patch('tethysapp.app_store.update_handlers.send_notification')
    mock_channel = MagicMock()

    message = "update message"
    send_update_msg(message, mock_channel)

    expected_json = {"target": "update-notices", "message": message}
    mock_sn.assert_called_with(expected_json, mock_channel)


def test_conda_update(mocker, app_store_dir):
    mocker.patch('tethysapp.app_store.update_handlers.time.time', side_effect=[10, 20])
    mock_send_update_msg = mocker.patch('tethysapp.app_store.update_handlers.send_update_msg')
    mock_subprocess = mocker.patch('tethysapp.app_store.update_handlers.subprocess')
    mock_subprocess.Popen().stdout.readline.side_effect = ["Collecting package metadata: done".encode('utf-8'),
                                                           "Solving environment: done".encode('utf-8'),
                                                           "Verifying transaction: done".encode('utf-8'),
                                                           "All requested packages already installed.".encode('utf-8'),
                                                           "Found conflicts!: conflicting requests".encode('utf-8'),
                                                           "Mamba Update Complete".encode('utf-8')]
    mock_channel = MagicMock()
    app_name = "test_app"
    app_version = "1.0.0"
    conda_channel = "conda_channel"
    conda_label = "conda_label"

    conda_update(app_name, app_version, conda_channel, conda_label, mock_channel)

    update_script = str(app_store_dir / "scripts" / "mamba_update.sh")
    mock_subprocess.Popen.assert_called_with(
        [update_script, f'{app_name}={app_version}', f'{conda_channel}/label/{conda_label}'],
        stdout=mock_subprocess.PIPE, stderr=mock_subprocess.STDOUT)
    mock_send_update_msg.assert_has_calls([
        call("Updating the Conda environment may take a couple minutes to complete depending on how "
             "complicated the environment is. Please wait....", mock_channel),
        call("Package Metadata Collection: Done", mock_channel),
        call("Solving Environment: Done", mock_channel),
        call("Verifying Transaction: Done", mock_channel),
        call("Application package is already installed in this conda environment.", mock_channel),
        call("Mamba install found conflicts. Please try running the following command in your terminal's conda "
             f"environment to attempt a manual installation :  mamba install -c {conda_channel} {app_name}",
             mock_channel),
        call("Conda update completed in 10.00 seconds.", mock_channel)
    ])


def test_conda_update_2(mocker, app_store_dir):
    mocker.patch('tethysapp.app_store.update_handlers.time.time', side_effect=[10, 20])
    mock_send_update_msg = mocker.patch('tethysapp.app_store.update_handlers.send_update_msg')
    mock_subprocess = mocker.patch('tethysapp.app_store.update_handlers.subprocess')
    mock_subprocess.Popen().stdout.readline.return_value = ""
    mock_channel = MagicMock()
    app_name = "test_app"
    app_version = "1.0.0"
    conda_channel = "conda_channel"
    conda_label = "conda_label"

    conda_update(app_name, app_version, conda_channel, conda_label, mock_channel)

    update_script = str(app_store_dir / "scripts" / "mamba_update.sh")
    mock_subprocess.Popen.assert_called_with(
        [update_script, f'{app_name}={app_version}', f'{conda_channel}/label/{conda_label}'],
        stdout=mock_subprocess.PIPE, stderr=mock_subprocess.STDOUT)
    mock_send_update_msg.assert_has_calls([
        call("Updating the Conda environment may take a couple minutes to complete depending on how "
             "complicated the environment is. Please wait....", mock_channel),
        call("Conda update completed in 10.00 seconds.", mock_channel)
    ])


def test_update_app(mocker):
    mock_restart = mocker.patch('tethysapp.app_store.update_handlers.restart_server')
    mock_conda_update = mocker.patch('tethysapp.app_store.update_handlers.conda_update')
    mock_channel = MagicMock()
    mock_workspace = MagicMock()
    data = {
        "name": "test_app",
        "app_type": "tethysapp",
        "version": "1.0.0",
        "channel": "conda_channel",
        "label": "conda_label"
    }

    update_app(data, mock_channel, mock_workspace)

    expected_data = {"restart_type": "update", "name": data["name"]}
    mock_conda_update.assert_called_with(data["name"], data["version"], data["channel"], data["label"], mock_channel)
    mock_restart.assert_called_with(data=expected_data, channel_layer=mock_channel, app_workspace=mock_workspace)


def test_update_app_proxyapp(mocker, proxyapp_site_package, test_files_dir):
    mock_send_update_msg = mocker.patch('tethysapp.app_store.update_handlers.send_update_msg')
    mock_restart = mocker.patch('tethysapp.app_store.update_handlers.restart_server')
    mock_conda_update = mocker.patch('tethysapp.app_store.update_handlers.conda_update')
    mock_delete_proxy_app = mocker.patch('tethysapp.app_store.update_handlers.delete_proxy_app')
    mock_create_proxy_app = mocker.patch('tethysapp.app_store.update_handlers.create_proxy_app')
    subprocess_location = str(proxyapp_site_package / "subprocess")

    mocker.patch('tethysapp.app_store.begin_install.subprocess.__file__', subprocess_location)
    mock_channel = MagicMock()
    mock_workspace = MagicMock()
    data = {
        "name": "proxyapp_test_app",
        "app_type": "proxyapp",
        "version": "1.0.0",
        "channel": "conda_channel",
        "label": "conda_label"
    }

    update_app(data, mock_channel, mock_workspace)

    expected_data = {"restart_type": "update", "name": data["name"]}
    mock_conda_update.assert_called_with(data["name"], data["version"], data["channel"], data["label"], mock_channel)
    mock_restart.assert_called_with(data=expected_data, channel_layer=mock_channel, app_workspace=mock_workspace)
    expected_data = data
    expected_data['app_name'] = expected_data['name'].replace("proxyapp_", "")
    mock_delete_proxy_app.assert_called_with(expected_data, mock_channel)
    expected_proxy_app_data = yaml.safe_load((test_files_dir / "proxyapp.yaml").read_text())
    mock_create_proxy_app.assert_called_with(expected_proxy_app_data, mock_channel)
    mock_send_update_msg.assert_called_with("Proxy app has been updated.", mock_channel)


def test_update_app_exception(mocker, caplog):
    mock_restart = mocker.patch('tethysapp.app_store.update_handlers.restart_server')
    mock_send_update_msg = mocker.patch('tethysapp.app_store.update_handlers.send_update_msg')
    mocker.patch('tethysapp.app_store.update_handlers.conda_update', side_effect=[Exception("Conda failed")])
    mock_channel = MagicMock()
    mock_workspace = MagicMock()
    data = {
        "name": "test_app",
        "version": "1.0.0",
        "channel": "conda_channel",
        "label": "conda_label"
    }

    update_app(data, mock_channel, mock_workspace)

    assert "Conda failed" in caplog.messages
    mock_send_update_msg.assert_called_with("Application update failed. Check logs for more details.", mock_channel)
    mock_restart.assert_not_called()
