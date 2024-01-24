import json
import os
import yaml
import pytest
from rest_framework.exceptions import ValidationError
from unittest.mock import MagicMock, call
from django.http import Http404
from tethysapp.app_store.git_install_handlers import (clear_github_cache_list, update_status_file, run_pending_installs,
                                                      CACHE_KEY, install_worker, install_packages, write_logs,
                                                      continue_install, get_log_file, get_status_file, get_status_main,
                                                      get_logs_main, resume_pending_installs)


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
    workspace_app = str(git_status_workspace / "apps" / "github_installed" / "test_app")
    mock_continue.assert_called_with(workspace_app, mock_logger, str(git_status_file), install_options, "test_app",
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


def test_install_packages(mocker, git_status_workspace):
    mock_conda = mocker.patch('tethysapp.app_store.git_install_handlers.conda_run',
                              return_value=["successful", "", 0])
    conda_config = {'channels': 'conda-forge', 'packages': ['numpy', 'requests']}
    mock_logger = MagicMock()
    status_file_path = git_status_workspace / 'install_status' / 'github' / "abc123.json"

    install_packages(conda_config, mock_logger, str(status_file_path))

    mock_conda.assert_called_with("install", "-c", conda_config['channels'], '--freeze-installed', 'numpy', 'requests',
                                  use_exception_handler=False)
    git_status = json.loads(status_file_path.read_text())
    assert git_status['status']['conda']
    assert call("Running conda installation tasks...") in mock_logger.info.mock_calls
    assert call("successful") in mock_logger.info.mock_calls


def test_install_packages_failed(mocker, git_status_workspace):
    mock_datetime = mocker.patch('tethysapp.app_store.git_install_handlers.datetime')
    mock_datetime.now().strftime.return_value = "2024-01-02T00:00:00:0000"
    mock_conda = mocker.patch('tethysapp.app_store.git_install_handlers.conda_run',
                              return_value=["failed", "", 1])
    conda_config = {'channels': 'conda-forge', 'packages': ['numpy', 'requests']}
    mock_logger = MagicMock()
    status_file_path = git_status_workspace / 'install_status' / 'github' / "abc123.json"

    install_packages(conda_config, mock_logger, str(status_file_path))

    mock_conda.assert_called_with("install", "-c", conda_config['channels'], '--freeze-installed', 'numpy', 'requests',
                                  use_exception_handler=False)
    err_msg = "Warning: Packages installation ran into an error. Please try again or a manual install"
    git_status = json.loads(status_file_path.read_text())
    assert not git_status['status']['conda']
    assert git_status['errorDateTime'] == "2024-01-02T00:00:00:0000"
    assert git_status["errorMessage"] == err_msg
    assert call("Running conda installation tasks...") in mock_logger.info.mock_calls
    assert call(err_msg) in mock_logger.error.mock_calls


def test_write_logs():
    mock_logger = MagicMock()
    mock_output = MagicMock()
    mock_output.readline.side_effect = [b"Simulating output", b"Final output"]
    subHeading = "Testing : "

    write_logs(mock_logger, mock_output, subHeading)

    assert call(subHeading + "Simulating output") in mock_logger.info.mock_calls
    assert call(subHeading + "Final output") in mock_logger.info.mock_calls


def test_continue_install(git_status_workspace, mocker):
    mock_popen = mocker.patch('tethysapp.app_store.git_install_handlers.Popen')
    mock_popen().wait.return_value = 0
    mock_popen().communicate.return_value = ["processed"]
    mock_pipe = mocker.patch('tethysapp.app_store.git_install_handlers.PIPE')
    mock_stdout = mocker.patch('tethysapp.app_store.git_install_handlers.STDOUT')
    mock_stdout.side_effect = [b"Simulating output", b"Final output"]
    mock_restart_server = mocker.patch('tethysapp.app_store.git_install_handlers.restart_server')
    mock_clear_github_cache_list = mocker.patch('tethysapp.app_store.git_install_handlers.clear_github_cache_list')
    mocker.patch('tethysapp.app_store.git_install_handlers.write_logs')
    mock_logger = MagicMock()
    status_file_path = git_status_workspace / 'install_status' / 'github' / "abc123.json"
    install_options = {
        'version': 1.0, 'name': 'test_app', 'post': ['post_script.sh'], 'tethys_version': '>=4.0',
        'requirements': {'skip': False, 'conda': {'channels': 'conda-forge', 'packages': ['numpy']},
                         'pip': ['requests']}
    }
    app_name = install_options['name']
    workspace_app = str(git_status_workspace / "apps" / "github_installed" / "test_app")

    continue_install(workspace_app, mock_logger, str(status_file_path), install_options, app_name,
                     str(git_status_workspace))

    git_status = json.loads(status_file_path.read_text())
    assert git_status['status']['dbSync']
    assert git_status['status']['post']
    assert git_status['status']['setupPy']
    assert call(['tethys', 'db', 'sync'], stdout=mock_pipe, stderr=mock_stdout) in mock_popen.mock_calls
    assert call("Running post installation tasks...") in mock_logger.info.mock_calls
    assert call("Post Script Result: processed") in mock_logger.info.mock_calls
    assert call("Install completed") in mock_logger.info.mock_calls
    mock_clear_github_cache_list.assert_called()
    mock_restart_server.assert_called_with({"restart_type": "github_install", "name": app_name},
                                           channel_layer=None, app_workspace=str(git_status_workspace))


def test_continue_install_fail_db_sync(git_status_workspace, mocker):
    mock_datetime = mocker.patch('tethysapp.app_store.git_install_handlers.datetime')
    mock_datetime.now().strftime.return_value = "2024-01-02T00:00:00:0000"
    mock_popen = mocker.patch('tethysapp.app_store.git_install_handlers.Popen')
    mock_popen().wait.return_value = 1
    mock_popen().communicate.return_value = ["processed"]
    mock_pipe = mocker.patch('tethysapp.app_store.git_install_handlers.PIPE')
    mock_stdout = mocker.patch('tethysapp.app_store.git_install_handlers.STDOUT')
    mock_stdout.side_effect = [b"Simulating output", b"Final output"]
    mock_restart_server = mocker.patch('tethysapp.app_store.git_install_handlers.restart_server')
    mock_clear_github_cache_list = mocker.patch('tethysapp.app_store.git_install_handlers.clear_github_cache_list')
    mocker.patch('tethysapp.app_store.git_install_handlers.write_logs')
    mock_logger = MagicMock()
    status_file_path = git_status_workspace / 'install_status' / 'github' / "abc123.json"
    install_options = {
        'version': 1.0, 'name': 'test_app', 'post': ['post_script.sh'], 'tethys_version': '>=4.0',
        'requirements': {'skip': False, 'conda': {'channels': 'conda-forge', 'packages': ['numpy']},
                         'pip': ['requests']}
    }
    app_name = install_options['name']
    workspace_app = str(git_status_workspace / "apps" / "github_installed" / "test_app")

    continue_install(workspace_app, mock_logger, str(status_file_path), install_options, app_name,
                     str(git_status_workspace))

    err_msg = "Error while running DBSync. Please check logs"
    git_status = json.loads(status_file_path.read_text())
    assert not git_status['status']['dbSync']
    assert git_status['errorDateTime'] == "2024-01-02T00:00:00:0000"
    assert git_status["errorMessage"] == err_msg
    assert git_status['status']['post']
    assert git_status['status']['setupPy']
    assert call(['tethys', 'db', 'sync'], stdout=mock_pipe, stderr=mock_stdout) in mock_popen.mock_calls
    assert call("Running post installation tasks...") in mock_logger.info.mock_calls
    assert call("Post Script Result: processed") in mock_logger.info.mock_calls
    assert call("Install completed") in mock_logger.info.mock_calls
    mock_clear_github_cache_list.assert_called()
    mock_restart_server.assert_called_with({"restart_type": "github_install", "name": app_name},
                                           channel_layer=None, app_workspace=str(git_status_workspace))


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
    mock_continue.assert_called_with(workspace_app, mock_logger, str(status_file_path), install_options, "test_app",
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
    mock_continue.assert_called_with(workspace_app, mock_logger, str(status_file_path), install_options, "test_app",
                                     str(git_status_workspace))
    assert call("Installing dependencies...") in mock_logger.info.mock_calls
    assert call("Running pip installation tasks...") not in mock_logger.info.mock_calls
    assert call("PIP Install exited with: 0") not in mock_logger.info.mock_calls
    assert call("Running application install....") in mock_logger.info.mock_calls
    assert call("Python Application install exited with: 0") in mock_logger.info.mock_calls


def test_get_log_file(git_status_workspace):
    log_file = get_log_file("abc123", str(git_status_workspace))

    assert log_file == str(git_status_workspace / 'logs' / 'github_install' / "abc123.log")


def test_get_status_file(git_status_workspace):
    status_file = get_status_file("abc123", str(git_status_workspace))

    assert status_file == str(git_status_workspace / 'install_status' / 'github' / "abc123.json")


def test_get_status_main(git_status_workspace, mock_admin_get_request):
    mock_workspace = MagicMock(path=str(git_status_workspace))
    request = mock_admin_get_request("logs", {"install_id": "abc123"})

    status = get_status_main(request, mock_workspace)

    status_file_path = git_status_workspace / 'install_status' / 'github' / "abc123.json"
    git_status = json.loads(status_file_path.read_text())
    assert git_status == json.loads(status.content)


def test_get_status_main_no_id(git_status_workspace, mock_admin_get_request):
    mock_workspace = MagicMock(path=str(git_status_workspace))
    request = mock_admin_get_request("logs", {})

    with pytest.raises(ValidationError) as e:
        get_status_main(request, mock_workspace)

    assert e.value.args[0] == {"install_id": "Missing Value"}


def test_get_status_missing_id(git_status_workspace, mock_admin_get_request):
    mock_workspace = MagicMock(path=str(git_status_workspace))
    request = mock_admin_get_request("logs", {"install_id": "foobar"})

    with pytest.raises(Http404) as e:
        get_status_main(request, mock_workspace)

    assert e.value.args[0] == 'No Install with id foobar exists'


def test_get_logs_main(git_status_workspace, mock_admin_get_request):
    mock_workspace = MagicMock(path=str(git_status_workspace))
    request = mock_admin_get_request("logs", {"install_id": "abc123"})
    log_path = git_status_workspace / 'logs' / 'github_install' / "abc123.log"
    with open(log_path, "w") as log_file:
        log_file.write("This is a log")

    status = get_logs_main(request, mock_workspace)

    log_path = git_status_workspace / 'logs' / 'github_install' / "abc123.log"
    assert status.content.decode() == log_path.read_text()


def test_get_logs_main_no_id(git_status_workspace, mock_admin_get_request):
    mock_workspace = MagicMock(path=str(git_status_workspace))
    request = mock_admin_get_request("logs", {})

    with pytest.raises(ValidationError) as e:
        get_logs_main(request, mock_workspace)

    assert e.value.args[0] == {"install_id": "Missing Value"}


def test_get_logs_main_missing_id(git_status_workspace, mock_admin_get_request):
    mock_workspace = MagicMock(path=str(git_status_workspace))
    request = mock_admin_get_request("logs", {"install_id": "foobar"})

    with pytest.raises(Http404) as e:
        get_logs_main(request, mock_workspace)

    assert e.value.args[0] == 'No Install with id foobar exists'


def test_resume_pending_installs(mocker):
    mock_threading = mocker.patch('tethysapp.app_store.git_install_handlers.threading')

    resume_pending_installs()

    mock_threading.Thread.assert_called_with(target=run_pending_installs, name="ResumeGitInstalls")
    mock_threading.Thread().setDaemon.assert_called_with(True)
    mock_threading.Thread().start.assert_called()
