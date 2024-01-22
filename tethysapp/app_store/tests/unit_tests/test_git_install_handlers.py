import json
import os
import yaml
from unittest.mock import MagicMock, call
from tethysapp.app_store.git_install_handlers import (clear_github_cache_list, update_status_file, run_pending_installs,
                                                      CACHE_KEY, install_worker)


def test_clear_github_cache_list(mocker):
    mock_cache = mocker.patch('tethysapp.app_store.git_install_handlers.cache')

    clear_github_cache_list()

    mock_cache.delete.assert_called_with(CACHE_KEY)


def test_run_pending_installs_dne(tmp_path, mocker, caplog):
    mock_workspace = MagicMock(path=tmp_path)
    mocker.patch('tethysapp.app_store.git_install_handlers.get_app_workspace', return_value=mock_workspace)
    mocker.patch('tethysapp.app_store.git_install_handlers.time')

    run_pending_installs()

    assert "Checking for Pending Installs" in caplog.messages


def test_run_pending_installs(git_status_workspace, mocker, caplog):
    mock_workspace = MagicMock(path=str(git_status_workspace))
    mocker.patch('tethysapp.app_store.git_install_handlers.time')
    mock_logger = mocker.patch('tethysapp.app_store.git_install_handlers.git_install_logger')
    mock_continue = mocker.patch('tethysapp.app_store.git_install_handlers.continue_install')
    mocker.patch('tethysapp.app_store.git_install_handlers.get_app_workspace', return_value=mock_workspace)
    git_status_file = git_status_workspace / 'install_status' / 'github' / "abc123.json"

    update_status_file(git_status_file, "Running", "setupPy")

    run_pending_installs()

    assert "Checking for Pending Installs" in caplog.messages
    install_options = {
        'version': 1.0, 'name': 'test_app', 'post': None, 'tethys_version': '>=4.0',
        'requirements': {'skip': False, 'conda': {'channels': 'conda-forge', 'packages': ['numpy']},
                         'pip': ['requests']}
    }
    mock_continue.assert_called_with(mock_logger, str(git_status_file), install_options, "test_app",
                                     mock_workspace)


def test_update_status_file_install(git_status_workspace, mocker):
    mock_datetime = mocker.patch('tethysapp.app_store.git_install_handlers.datetime')
    mock_datetime.now().strftime.return_value = "2024-01-02T00:00:00:0000"
    git_status_file = git_status_workspace / 'install_status' / 'github' / "abc123.json"

    update_status_file(git_status_file, True, "conda")
    update_status_file(git_status_file, True, "pip")
    update_status_file(git_status_file, True, "setupPy")
    update_status_file(git_status_file, True, "dbSync")
    update_status_file(git_status_file, True, "post")

    git_status = json.loads(git_status_file.read_text())
    assert git_status['status']['pip']
    assert git_status['installCompletedTime'] == "2024-01-02T00:00:00:0000"
    assert git_status["installComplete"]


def test_update_status_file_error(git_status_workspace, mocker):
    mock_datetime = mocker.patch('tethysapp.app_store.git_install_handlers.datetime')
    mock_datetime.now().strftime.return_value = "2024-01-02T00:00:00:0000"
    git_status_file = git_status_workspace / 'install_status' / 'github' / "abc123.json"

    update_status_file(git_status_file, False, "conda", "conda failed")

    git_status = json.loads(git_status_file.read_text())
    assert not git_status['status']['conda']
    assert git_status['errorDateTime'] == "2024-01-02T00:00:00:0000"
    assert git_status["errorMessage"] == "conda failed"


def test_install_worker(git_status_workspace, mocker):
    mock_logger = MagicMock()
    workspace_app = str(git_status_workspace / "apps" / "github_installed" / "test_app")
    status_file_path = git_status_workspace / 'install_status' / 'github' / "abc123.json"
    mocker.patch('tethysapp.app_store.git_install_handlers.write_logs')
    mock_popen = mocker.patch('tethysapp.app_store.git_install_handlers.Popen')
    mock_popen().wait.return_value = 0
    mock_pipe = mocker.patch('tethysapp.app_store.git_install_handlers.PIPE')
    mock_stdout = mocker.patch('tethysapp.app_store.git_install_handlers.STDOUT')
    mock_install_packages = mocker.patch('tethysapp.app_store.git_install_handlers.install_packages')
    mock_continue = mocker.patch('tethysapp.app_store.git_install_handlers.continue_install')

    install_worker(workspace_app, str(status_file_path), mock_logger, True, str(git_status_workspace))

    conda_config = {'channels': 'conda-forge', 'packages': ['numpy']}
    mock_install_packages.assert_called_with(conda_config, mock_logger, str(status_file_path))
    git_status = json.loads(status_file_path.read_text())
    assert call(['pip', 'install', 'requests'], stdout=mock_pipe, stderr=mock_stdout) in mock_popen.mock_calls
    assert call(['python', 'setup.py', 'develop'], cwd=workspace_app, stdout=mock_pipe, stderr=mock_stdout) in mock_popen.mock_calls  # noqa: E501
    assert git_status['status']['pip']
    assert git_status['status']['conda']
    assert git_status['status']['setupPy'] == "Running"
    install_options = {
        'version': 1.0, 'name': 'test_app', 'post': None, 'tethys_version': '>=4.0',
        'requirements': {'skip': False, 'conda': {'channels': 'conda-forge', 'packages': ['numpy']},
                         'pip': ['requests']}
    }
    mock_continue.assert_called_with(mock_logger, str(status_file_path), install_options, "test_app",
                                     str(git_status_workspace))
    assert call("Installing dependencies...") in mock_logger.info.mock_calls
    assert call("Running pip installation tasks...") in mock_logger.info.mock_calls
    assert call("PIP Install exited with: 0") in mock_logger.info.mock_calls
    assert call("Running application install....") in mock_logger.info.mock_calls
    assert call("Python Application install exited with: 0") in mock_logger.info.mock_calls


def test_install_worker_skip_package(git_status_workspace, mocker):
    mock_logger = MagicMock()
    workspace_app = str(git_status_workspace / "apps" / "github_installed" / "test_app")
    status_file_path = git_status_workspace / 'install_status' / 'github' / "abc123.json"
    mocker.patch('tethysapp.app_store.git_install_handlers.write_logs')
    mock_popen = mocker.patch('tethysapp.app_store.git_install_handlers.Popen')
    mock_popen().wait.return_value = 0
    mock_pipe = mocker.patch('tethysapp.app_store.git_install_handlers.PIPE')
    mock_stdout = mocker.patch('tethysapp.app_store.git_install_handlers.STDOUT')
    mock_install_packages = mocker.patch('tethysapp.app_store.git_install_handlers.install_packages')
    mock_continue = mocker.patch('tethysapp.app_store.git_install_handlers.continue_install')

    install_yml = os.path.join(workspace_app, 'install.yml')
    with open(install_yml, "r") as yaml_file:
        data = yaml.load(yaml_file, Loader=yaml.FullLoader)
    data['requirements']['skip'] = True
    with open(install_yml, "w") as yaml_file:
        yaml_file.write(yaml.dump(data, default_flow_style=False))

    install_worker(workspace_app, str(status_file_path), mock_logger, False, str(git_status_workspace))

    mock_install_packages.assert_not_called()
    git_status = json.loads(status_file_path.read_text())
    assert call(['pip', 'install', 'requests'], stdout=mock_pipe, stderr=mock_stdout) not in mock_popen.mock_calls
    assert call(['python', 'setup.py', 'install'], cwd=workspace_app, stdout=mock_pipe, stderr=mock_stdout) in mock_popen.mock_calls  # noqa: E501
    assert git_status['status']['pip']
    assert git_status['status']['conda']
    assert git_status['status']['setupPy'] == "Running"
    install_options = {
        'version': 1.0, 'name': 'test_app', 'post': None, 'tethys_version': '>=4.0',
        'requirements': {'skip': True, 'conda': {'channels': 'conda-forge', 'packages': ['numpy']}, 'pip': ['requests']}
    }
    mock_continue.assert_called_with(mock_logger, str(status_file_path), install_options, "test_app",
                                     str(git_status_workspace))
    assert call("Installing dependencies...") in mock_logger.info.mock_calls
    assert call("Running pip installation tasks...") not in mock_logger.info.mock_calls
    assert call("PIP Install exited with: 0") not in mock_logger.info.mock_calls
    assert call("Running application install....") in mock_logger.info.mock_calls
    assert call("Python Application install exited with: 0") in mock_logger.info.mock_calls
