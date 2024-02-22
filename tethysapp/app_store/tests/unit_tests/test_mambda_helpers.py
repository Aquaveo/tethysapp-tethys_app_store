from unittest.mock import MagicMock, call
from tethysapp.app_store.mamba_helpers import send_uninstall_messages, mamba_install, mamba_uninstall, mamba_download


def test_mamba_uninstall(mocker, tmp_path):
    mamba_helpers_file = tmp_path / "mamba_helpers.py"
    mamba_helpers_file.mkdir()
    mocker.patch('tethysapp.app_store.mamba_helpers.__file__', str(mamba_helpers_file))
    mock_sp = mocker.patch('tethysapp.app_store.mamba_helpers.subprocess')
    mock_sm = mocker.patch('tethysapp.app_store.mamba_helpers.send_uninstall_messages')
    mock_sp.Popen().stdout.readline.side_effect = [
        "Running Mamba remove", "Transaction starting", "Transaction finished", "Mamba Remove Complete"]
    app_name = "test_app"
    mock_channel = MagicMock()

    mamba_uninstall(app_name, mock_channel)

    script_path = str(tmp_path / "scripts" / "mamba_uninstall.sh")
    mock_sp.Popen.assert_called_with([script_path, app_name], stdout=mock_sp.PIPE, stderr=mock_sp.STDOUT)
    mock_sm.assert_has_calls([
        call("Running uninstall script", mock_channel),
        call("Starting mamba uninstall", mock_channel),
        call("Mamba uninstall complete", mock_channel)
    ])


def test_mamba_uninstall2(mocker, tmp_path):
    mamba_helpers_file = tmp_path / "mamba_helpers.py"
    mamba_helpers_file.mkdir()
    mocker.patch('tethysapp.app_store.mamba_helpers.__file__', str(mamba_helpers_file))
    mock_sp = mocker.patch('tethysapp.app_store.mamba_helpers.subprocess')
    mock_sm = mocker.patch('tethysapp.app_store.mamba_helpers.send_uninstall_messages')
    mock_sp.Popen().stdout.readline.side_effect = [""]
    app_name = "test_app"
    mock_channel = MagicMock()

    mamba_uninstall(app_name, mock_channel)

    script_path = str(tmp_path / "scripts" / "mamba_uninstall.sh")
    mock_sp.Popen.assert_called_with([script_path, app_name], stdout=mock_sp.PIPE, stderr=mock_sp.STDOUT)
    mock_sm.assert_not_called()


def test_send_uninstall_messages(mocker):
    mock_sn = mocker.patch('tethysapp.app_store.mamba_helpers.send_notification')
    mock_channel = MagicMock()

    message = "uninstall message"
    send_uninstall_messages(message, mock_channel)

    expected_json = {"target": "uninstallNotices", "message": message}
    mock_sn.assert_called_with(expected_json, mock_channel)


def test_mamba_download_success(resource, mocker):
    app_channel = "test_channel"
    app_label = "dev"
    app_version = ""
    app_resource = resource("test_app", app_channel, app_label)
    mock_channel = MagicMock()
    mock_ws = mocker.patch('tethysapp.app_store.mamba_helpers.send_notification')
    mock_sp = mocker.patch('tethysapp.app_store.mamba_helpers.subprocess')
    mock_time = mocker.patch('tethysapp.app_store.mamba_helpers.time')
    mock_time.time.side_effect = [10, 20]
    mock_sp.Popen().stdout.readline.side_effect = ["Mamba Download Complete"]

    successful_install = mamba_download(app_resource, app_channel, app_label, app_version, mock_channel)

    mock_ws.assert_has_calls([
        call("Mamba install may take a couple minutes to complete depending on how complicated the "
             "environment is. Please wait....", mock_channel),
        call("Mamba download completed in 10.00 seconds.", mock_channel)
    ])
    assert successful_install


def test_mamba_download_success2(resource, mocker):
    app_channel = "test_channel"
    app_label = "dev"
    app_version = ""
    app_resource = resource("test_app", app_channel, app_label)
    mock_channel = MagicMock()
    mock_ws = mocker.patch('tethysapp.app_store.mamba_helpers.send_notification')
    mock_sp = mocker.patch('tethysapp.app_store.mamba_helpers.subprocess')
    mock_time = mocker.patch('tethysapp.app_store.mamba_helpers.time')
    mock_time.time.side_effect = [10, 20]
    mock_sp.Popen().stdout.readline.side_effect = [""]

    successful_install = mamba_download(app_resource, app_channel, app_label, app_version, mock_channel)

    mock_ws.assert_has_calls([
        call("Mamba install may take a couple minutes to complete depending on how complicated the "
             "environment is. Please wait....", mock_channel),
        call("Mamba download completed in 10.00 seconds.", mock_channel)
    ])
    assert successful_install


def test_mamba_download_failure(resource, mocker):
    app_channel = "test_channel"
    app_label = "dev"
    app_version = ""
    app_resource = resource("test_app", app_channel, app_label)
    mock_channel = MagicMock()
    mock_ws = mocker.patch('tethysapp.app_store.mamba_helpers.send_notification')
    mock_sp = mocker.patch('tethysapp.app_store.mamba_helpers.subprocess')
    mock_time = mocker.patch('tethysapp.app_store.mamba_helpers.time')
    mock_time.time.side_effect = [10, 20]
    mock_sp.Popen().stdout.readline.side_effect = ["All requested packages already installed",
                                                   "Mamba Download Complete"]

    successful_install = mamba_download(app_resource, app_channel, app_label, app_version, mock_channel)

    mock_ws.assert_has_calls([
        call("Application is already installed in this conda environment.", mock_channel),
        call("Mamba download completed in 10.00 seconds.", mock_channel)
    ])
    assert not successful_install


def test_mamba_install_success(resource, mocker):
    app_channel = "test_channel"
    app_label = "dev"
    app_version = ""
    app_resource = resource("test_app", app_channel, app_label)
    mock_channel = MagicMock()
    mock_ws = mocker.patch('tethysapp.app_store.mamba_helpers.send_notification')
    mock_sp = mocker.patch('tethysapp.app_store.mamba_helpers.subprocess')
    mock_time = mocker.patch('tethysapp.app_store.mamba_helpers.time')
    mock_time.time.side_effect = [10, 20]
    mock_sp.Popen().stdout.readline.side_effect = [
        "Running Mamba Install", "Collecting package metadata: done", "Solving environment: done",
        "Verifying transaction: done", "All requested packages already installed.", "Mamba Install Success",
        "Install Complete"]

    successful_install = mamba_install(app_resource, app_channel, app_label, app_version, mock_channel)

    mock_ws.assert_has_calls([
        call("Mamba install may take a couple minutes to complete depending on how complicated the "
             "environment is. Please wait....", mock_channel),
        call("Package Metadata Collection: Done", mock_channel),
        call("Solving Environment: Done", mock_channel),
        call("Verifying Transaction: Done", mock_channel),
        call("Application package is already installed in this conda environment.", mock_channel),
        call("Mamba install completed in 10.00 seconds.", mock_channel)
    ])
    assert successful_install


def test_mamba_install_mamba_failure_conda_success(resource, mocker):
    app_channel = "test_channel"
    app_label = "dev"
    app_version = ""
    app_resource = resource("test_app", app_channel, app_label)
    mock_channel = MagicMock()
    mock_ws = mocker.patch('tethysapp.app_store.mamba_helpers.send_notification')
    mock_sp = mocker.patch('tethysapp.app_store.mamba_helpers.subprocess')
    mock_time = mocker.patch('tethysapp.app_store.mamba_helpers.time')
    mock_time.time.side_effect = [10, 20]
    mock_sp.Popen().stdout.readline.side_effect = [
        "Running Mamba Install", "critical libmamba Could not solve for environment specs",
        "Mamba failed. Trying conda now.", "Conda Install Success", "Install Complete"]

    successful_install = mamba_install(app_resource, app_channel, app_label, app_version, mock_channel)

    mock_ws.assert_has_calls([
        call("Mamba install may take a couple minutes to complete depending on how complicated the "
             "environment is. Please wait....", mock_channel),
        call("Failed to resolve environment specs when installing.", mock_channel),
        call("Install failed using mamba. Trying now with conda.", mock_channel),
        call("Install succeeded with conda.", mock_channel),
        call("Mamba install completed in 10.00 seconds.", mock_channel)
    ])
    assert successful_install


def test_mamba_install_mamba_failure_conda_failure(resource, mocker):
    app_channel = "test_channel"
    app_label = "dev"
    app_version = ""
    app_resource = resource("test_app", app_channel, app_label)
    mock_channel = MagicMock()
    mock_ws = mocker.patch('tethysapp.app_store.mamba_helpers.send_notification')
    mock_sp = mocker.patch('tethysapp.app_store.mamba_helpers.subprocess')
    mock_time = mocker.patch('tethysapp.app_store.mamba_helpers.time')
    mock_time.time.side_effect = [10, 20]
    mock_sp.Popen().stdout.readline.side_effect = [
        "Running Mamba Install", "critical libmamba Could not solve for environment specs",
        "Mamba failed. Trying conda now.", "Install Complete"]

    successful_install = mamba_install(app_resource, app_channel, app_label, app_version, mock_channel)

    mock_ws.assert_has_calls([
        call("Mamba install may take a couple minutes to complete depending on how complicated the "
             "environment is. Please wait....", mock_channel),
        call("Failed to resolve environment specs when installing.", mock_channel),
        call("Install failed using mamba. Trying now with conda.", mock_channel),
        call("Mamba install completed in 10.00 seconds.", mock_channel)
    ])
    assert not successful_install


def test_mamba_install_output_failure2(resource, mocker):
    app_name = "test_app"
    app_channel = "test_channel"
    app_label = "dev"
    app_resource = resource(app_name, app_channel, app_label)
    app_version = app_resource['latestVersion'][app_channel][app_label]
    mock_channel = MagicMock()
    mock_ws = mocker.patch('tethysapp.app_store.mamba_helpers.send_notification')
    mock_sp = mocker.patch('tethysapp.app_store.mamba_helpers.subprocess')
    mock_time = mocker.patch('tethysapp.app_store.mamba_helpers.time')
    mock_time.time.side_effect = [10, 20]
    mock_sp.Popen().stdout.readline.side_effect = [
        "Running Mamba Install", "Found conflicts!", "Install Complete"]

    successful_install = mamba_install(app_resource, app_channel, app_label, app_version, mock_channel)

    mock_ws.assert_has_calls([
        call("Mamba install may take a couple minutes to complete depending on how complicated the "
             "environment is. Please wait....", mock_channel),
        call("Mamba install found conflicts. Please try running the following command in your terminal's "
             f"conda environment to attempt a manual installation : mamba install -c {app_channel}/label/{app_label} "
             f"{app_name}={app_version}",
             mock_channel),
        call("Mamba install completed in 10.00 seconds.", mock_channel)
    ])
    assert not successful_install


def test_mamba_install_output_failure3(resource, mocker):
    app_name = "test_app"
    app_channel = "test_channel"
    app_label = "main"
    app_resource = resource(app_name, app_channel, app_label)
    app_version = app_resource['latestVersion'][app_channel][app_label]
    mock_channel = MagicMock()
    mock_ws = mocker.patch('tethysapp.app_store.mamba_helpers.send_notification')
    mock_sp = mocker.patch('tethysapp.app_store.mamba_helpers.subprocess')
    mock_time = mocker.patch('tethysapp.app_store.mamba_helpers.time')
    mock_time.time.side_effect = [10, 20]
    mock_sp.Popen().stdout.readline.side_effect = [
        "Running Mamba Install", "Found conflicts!", ""]

    successful_install = mamba_install(app_resource, app_channel, app_label, app_version, mock_channel)

    mock_ws.assert_has_calls([
        call("Mamba install may take a couple minutes to complete depending on how complicated the "
             "environment is. Please wait....", mock_channel),
        call("Mamba install found conflicts. Please try running the following command in your terminal's "
             f"conda environment to attempt a manual installation : mamba install -c {app_channel} "
             f"{app_name}={app_version}",
             mock_channel),
        call("Mamba install completed in 10.00 seconds.", mock_channel)
    ])
    assert not successful_install
