import pytest
import json
from unittest.mock import MagicMock, call
from django.urls import reverse
from django.http import JsonResponse
from pathlib import Path
import shutil
from tethysapp.app_store.git_install_handlers import get_log_file, get_status_file


@pytest.mark.django_db
def test_get_status_no_token(mock_admin_api_get_request, mocker, tmp_path):
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    url = reverse('app_store:git_get_status')
    data = {}

    api_response = mock_admin_api_get_request(auth_header=False, url=url, data=data)

    assert api_response.status_code == 401
    json_response = json.loads(api_response.content)
    assert json_response['detail'] == 'Authentication credentials were not provided.'


@pytest.mark.django_db
def test_get_status_no_permission(mock_admin_api_get_request, mocker, tmp_path):
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethysapp.app_store.git_install_handlers.has_permission', side_effect=[False])
    url = reverse('app_store:git_get_status')
    data = {}

    api_response = mock_admin_api_get_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 401
    json_response = json.loads(api_response.content)
    assert json_response['message'] == 'Missing required permissions'


@pytest.mark.django_db
def test_get_status_called(mock_admin_api_get_request, mocker, tmp_path):
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethysapp.app_store.git_install_handlers.has_permission', side_effect=[True])
    mock_get_status_main = mocker.patch('tethysapp.app_store.git_install_handlers.get_status_main',
                                        side_effect=[JsonResponse({})])
    url = reverse('app_store:git_get_status')
    data = {}

    mock_admin_api_get_request(auth_header=True, url=url, data=data)

    mock_get_status_main.assert_called()


@pytest.mark.django_db
def test_get_status_override_no_custom_key_set(mock_admin_api_get_request, mocker, tmp_path):
    mocker.patch('tethysapp.app_store.git_install_handlers.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethysapp.app_store.git_install_handlers.get_override_key', return_value=None)
    url = reverse('app_store:git_get_status_override')
    data = {}

    api_response = mock_admin_api_get_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 500
    json_response = json.loads(api_response.content)
    assert json_response['message'] == 'API not usable. No override key has been set'


@pytest.mark.django_db
def test_get_status_override_no_custom_key_provided(mock_admin_api_get_request, mocker, tmp_path):
    mocker.patch('tethysapp.app_store.git_install_handlers.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethysapp.app_store.git_install_handlers.get_override_key', side_effect=["override_key"])
    url = reverse('app_store:git_get_status_override')
    data = {}

    api_response = mock_admin_api_get_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 401
    json_response = json.loads(api_response.content)
    assert json_response['message'] == 'Invalid override key provided'


@pytest.mark.django_db
def test_get_status_override_called(mock_admin_api_get_request, mocker, tmp_path):
    mocker.patch('tethysapp.app_store.git_install_handlers.get_app_workspace', return_value=str(tmp_path))
    override_key = "override_key"
    mocker.patch('tethysapp.app_store.git_install_handlers.get_override_key', side_effect=[override_key])
    mock_get_status_main = mocker.patch('tethysapp.app_store.git_install_handlers.get_status_main',
                                        side_effect=[JsonResponse({})])
    url = reverse('app_store:git_get_status_override')
    data = {'custom_key': override_key}

    mock_admin_api_get_request(auth_header=True, url=url, data=data)

    mock_get_status_main.assert_called()


@pytest.mark.django_db
def test_get_logs_no_token(mock_admin_api_get_request, mocker, tmp_path):
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    url = reverse('app_store:git_get_logs')
    data = {}

    api_response = mock_admin_api_get_request(auth_header=False, url=url, data=data)

    assert api_response.status_code == 401
    json_response = json.loads(api_response.content)
    assert json_response['detail'] == 'Authentication credentials were not provided.'


@pytest.mark.django_db
def test_get_logs_no_permission(mock_admin_api_get_request, mocker, tmp_path):
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethysapp.app_store.git_install_handlers.has_permission', side_effect=[False])
    url = reverse('app_store:git_get_logs')
    data = {}

    api_response = mock_admin_api_get_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 401
    json_response = json.loads(api_response.content)
    assert json_response['message'] == 'Missing required permissions'


@pytest.mark.django_db
def test_get_logs_called(mock_admin_api_get_request, mocker, tmp_path):
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethysapp.app_store.git_install_handlers.has_permission', side_effect=[True])
    mock_get_logs_main = mocker.patch('tethysapp.app_store.git_install_handlers.get_logs_main',
                                      side_effect=[JsonResponse({})])
    url = reverse('app_store:git_get_logs')
    data = {}

    mock_admin_api_get_request(auth_header=True, url=url, data=data)

    mock_get_logs_main.assert_called()


@pytest.mark.django_db
def test_get_logs_override_no_custom_key_set(mock_admin_api_get_request, mocker, tmp_path):
    mocker.patch('tethysapp.app_store.git_install_handlers.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethysapp.app_store.git_install_handlers.get_override_key', return_value=None)
    url = reverse('app_store:git_get_logs_override')
    data = {}

    api_response = mock_admin_api_get_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 500
    json_response = json.loads(api_response.content)
    assert json_response['message'] == 'API not usable. No override key has been set'


@pytest.mark.django_db
def test_get_logs_override_no_custom_key_provided(mock_admin_api_get_request, mocker, tmp_path):
    mocker.patch('tethysapp.app_store.git_install_handlers.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethysapp.app_store.git_install_handlers.get_override_key', side_effect=["override_key"])
    url = reverse('app_store:git_get_logs_override')
    data = {}

    api_response = mock_admin_api_get_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 401
    json_response = json.loads(api_response.content)
    assert json_response['message'] == 'Invalid override key provided'


@pytest.mark.django_db
def test_get_logs_override_called(mock_admin_api_get_request, mocker, tmp_path):
    mocker.patch('tethysapp.app_store.git_install_handlers.get_app_workspace', return_value=str(tmp_path))
    override_key = "override_key"
    mocker.patch('tethysapp.app_store.git_install_handlers.get_override_key', side_effect=[override_key])
    mock_get_logs_main = mocker.patch('tethysapp.app_store.git_install_handlers.get_logs_main',
                                      side_effect=[JsonResponse({})])
    url = reverse('app_store:git_get_logs_override')
    data = {'custom_key': override_key}

    mock_admin_api_get_request(auth_header=True, url=url, data=data)

    mock_get_logs_main.assert_called()


@pytest.mark.django_db
def test_install_git_no_token(mock_admin_api_post_request, mocker, tmp_path):
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    url = reverse('app_store:install_git')
    data = {}

    api_response = mock_admin_api_post_request(auth_header=False, url=url, data=data)

    assert api_response.status_code == 401
    json_response = json.loads(api_response.content)
    assert json_response['detail'] == 'Authentication credentials were not provided.'


@pytest.mark.django_db
def test_install_git_no_permission(mock_admin_api_post_request, mocker, tmp_path):
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethysapp.app_store.git_install_handlers.has_permission', side_effect=[False])
    url = reverse('app_store:install_git')
    data = {}

    api_response = mock_admin_api_post_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 401
    json_response = json.loads(api_response.content)
    assert json_response['message'] == 'Missing required permissions'


@pytest.mark.django_db
def test_install_git_already_exists(mock_admin_api_post_request, app_store_workspace, mocker, caplog):
    mock_workspace = MagicMock(path=str(app_store_workspace))
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=mock_workspace)
    mocker.patch('tethysapp.app_store.git_install_handlers.has_permission', side_effect=[True])
    mock_git = mocker.patch('tethysapp.app_store.git_install_handlers.git')
    mock_threading = mocker.patch('tethysapp.app_store.git_install_handlers.threading')
    mock_install_worker = mocker.patch('tethysapp.app_store.git_install_handlers.install_worker')
    mock_git_install_logger = mocker.patch('tethysapp.app_store.git_install_handlers.git_install_logger')
    url = reverse('app_store:install_git')
    data = {"url": "https://github.com/test_app.git", "branch": "master", "develop": True}
    shutil.rmtree(app_store_workspace / "install_status" / "github")
    shutil.rmtree(app_store_workspace / "logs" / "github_install")

    api_response = mock_admin_api_post_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 200
    json_response = json.loads(api_response.content)
    install_id = json_response['install_id']
    log_file = get_log_file(install_id, str(app_store_workspace))
    status_file = get_status_file(install_id, str(app_store_workspace))
    app_location = str(app_store_workspace / "apps" / "github_installed" / "test_app")

    assert Path(log_file).is_file()
    assert Path(status_file).is_file
    assert call(f"Starting GitHub Install. Installation ID: {install_id}") in mock_git_install_logger.info.mock_calls
    assert call(f"Input URL: {data['url']}") in mock_git_install_logger.info.mock_calls
    assert call("Assumed App Name: test_app") in mock_git_install_logger.info.mock_calls
    assert call(f"Application Install Path: {app_location}") in mock_git_install_logger.info.mock_calls
    assert call("Git Repo exists locally. Doing a pull to get the latest") in mock_git_install_logger.info.mock_calls
    mock_git.cmd.Git.assert_called_with(app_location)
    mock_git.cmd.Git().pull.assert_called()
    mock_threading.Thread.assert_called_with(target=mock_install_worker, name="InstallApps",
                                             args=(app_location, status_file, mock_git_install_logger, True,
                                                   mock_workspace))


@pytest.mark.django_db
def test_install_git_dne(mock_admin_api_post_request, app_store_workspace, mocker):
    mock_workspace = MagicMock(path=str(app_store_workspace))
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=mock_workspace)
    mocker.patch('tethysapp.app_store.git_install_handlers.has_permission', side_effect=[True])
    mock_git = mocker.patch('tethysapp.app_store.git_install_handlers.git')
    mock_threading = mocker.patch('tethysapp.app_store.git_install_handlers.threading')
    mock_install_worker = mocker.patch('tethysapp.app_store.git_install_handlers.install_worker')
    mock_git_install_logger = mocker.patch('tethysapp.app_store.git_install_handlers.git_install_logger')
    url = reverse('app_store:install_git')
    data = {"url": "https://github.com/test_app.git", "branch": "master", "develop": True}

    workspace_app = app_store_workspace / "apps" / "github_installed" / "test_app"
    shutil.rmtree(workspace_app)

    api_response = mock_admin_api_post_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 200
    json_response = json.loads(api_response.content)
    install_id = json_response['install_id']
    log_file = get_log_file(install_id, str(app_store_workspace))
    status_file = get_status_file(install_id, str(app_store_workspace))
    app_location = str(app_store_workspace / "apps" / "github_installed" / "test_app")

    assert Path(log_file).is_file()
    assert Path(status_file).is_file
    assert call(f"Starting GitHub Install. Installation ID: {install_id}") in mock_git_install_logger.info.mock_calls
    assert call(f"Input URL: {data['url']}") in mock_git_install_logger.info.mock_calls
    assert call("Assumed App Name: test_app") in mock_git_install_logger.info.mock_calls
    assert call(f"Application Install Path: {app_location}") in mock_git_install_logger.info.mock_calls
    assert call("App folder Directory does not exist. Creating one.") in mock_git_install_logger.info.mock_calls
    mock_git.Repo.init.assert_called_with(app_location)
    mock_git.Repo.init().create_remote.assert_called_with('origin', data['url'])
    mock_git.Repo.init().create_remote().fetch.assert_called()
    mock_git.Repo.init().git.checkout.assert_called_with(data['branch'], "-f")
    mock_threading.Thread.assert_called_with(target=mock_install_worker, name="InstallApps",
                                             args=(app_location, status_file, mock_git_install_logger, True,
                                                   mock_workspace))


@pytest.mark.django_db
def test_install_git_dne_branch_error(mock_admin_api_post_request, app_store_workspace, mocker):
    mock_workspace = MagicMock(path=str(app_store_workspace))
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=mock_workspace)
    mocker.patch('tethysapp.app_store.git_install_handlers.has_permission', side_effect=[True])
    mock_git = mocker.patch('tethysapp.app_store.git_install_handlers.git')
    exception_error = "bad branch"
    mock_git.Repo.init().git.checkout.side_effect = [Exception(exception_error), True]
    mock_threading = mocker.patch('tethysapp.app_store.git_install_handlers.threading')
    mock_install_worker = mocker.patch('tethysapp.app_store.git_install_handlers.install_worker')
    mock_git_install_logger = mocker.patch('tethysapp.app_store.git_install_handlers.git_install_logger')
    url = reverse('app_store:install_git')
    data = {"url": "https://github.com/test_app.git", "branch": "master", "develop": True}

    workspace_app = app_store_workspace / "apps" / "github_installed" / "test_app"
    shutil.rmtree(workspace_app)

    api_response = mock_admin_api_post_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 200
    json_response = json.loads(api_response.content)
    install_id = json_response['install_id']
    log_file = get_log_file(install_id, str(app_store_workspace))
    status_file = get_status_file(install_id, str(app_store_workspace))
    app_location = str(app_store_workspace / "apps" / "github_installed" / "test_app")

    assert Path(log_file).is_file()
    assert Path(status_file).is_file
    assert call(f"Starting GitHub Install. Installation ID: {install_id}") in mock_git_install_logger.info.mock_calls
    assert call(f"Input URL: {data['url']}") in mock_git_install_logger.info.mock_calls
    assert call("Assumed App Name: test_app") in mock_git_install_logger.info.mock_calls
    assert call(f"Application Install Path: {app_location}") in mock_git_install_logger.info.mock_calls
    assert call("App folder Directory does not exist. Creating one.") in mock_git_install_logger.info.mock_calls
    assert call(exception_error) in mock_git_install_logger.info.mock_calls
    assert call(f"Couldn't check out {data['branch']} branch. Attempting to checkout main") in mock_git_install_logger.info.mock_calls  # noqa: E501
    mock_git.Repo.init.assert_called_with(app_location)
    mock_git.Repo.init().create_remote.assert_called_with('origin', data['url'])
    mock_git.Repo.init().create_remote().fetch.assert_called()
    mock_git.Repo.init().git.checkout.assert_has_calls([
        call(data['branch'], "-f"),
        call("main", "-f")
    ])
    mock_threading.Thread.assert_called_with(target=mock_install_worker, name="InstallApps",
                                             args=(app_location, status_file, mock_git_install_logger, True,
                                                   mock_workspace))


@pytest.mark.django_db
def test_run_git_install_override_no_custom_key_set(mock_admin_api_post_request, mocker, tmp_path):
    mocker.patch('tethysapp.app_store.git_install_handlers.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethysapp.app_store.git_install_handlers.get_override_key', return_value=None)
    url = reverse('app_store:install_git_override')
    data = {}

    api_response = mock_admin_api_post_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 500
    json_response = json.loads(api_response.content)
    assert json_response['message'] == 'API not usable. No override key has been set'


@pytest.mark.django_db
def test_run_git_install_override_no_custom_key_provided(mock_admin_api_post_request, mocker, tmp_path):
    mocker.patch('tethysapp.app_store.git_install_handlers.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethysapp.app_store.git_install_handlers.get_override_key', side_effect=["override_key"])
    url = reverse('app_store:install_git_override')
    data = {}

    api_response = mock_admin_api_post_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 401
    json_response = json.loads(api_response.content)
    assert json_response['message'] == 'Invalid override key provided'


@pytest.mark.django_db
def test_run_git_install_override_called(mock_admin_api_post_request, mocker, tmp_path):
    mocker.patch('tethysapp.app_store.git_install_handlers.get_app_workspace', return_value=str(tmp_path))
    override_key = "override_key"
    mocker.patch('tethysapp.app_store.git_install_handlers.get_override_key', side_effect=[override_key])
    mock_run_git_install_main = mocker.patch('tethysapp.app_store.git_install_handlers.run_git_install_main',
                                             side_effect=[JsonResponse({})])
    url = reverse('app_store:install_git_override')
    data = {'custom_key': override_key}

    mock_admin_api_post_request(auth_header=True, url=url, data=data)

    mock_run_git_install_main.assert_called()
