import pytest
import json
from unittest.mock import MagicMock
from django.urls import reverse


@pytest.mark.django_db
def test_scaffold_command_no_token(mock_admin_api_post_request, mocker, tmp_path):
    mocker.patch(
        "tethys_apps.base.workspace.get_app_workspace", return_value=str(tmp_path)
    )
    url = reverse("app_store:scaffold_app")
    data = {}

    api_response = mock_admin_api_post_request(auth_header=False, url=url, data=data)

    assert api_response.status_code == 401
    json_response = json.loads(api_response.content)
    assert json_response["detail"] == "Authentication credentials were not provided."


@pytest.mark.django_db
def test_scaffold_command_no_permission(mock_admin_api_post_request, mocker, tmp_path):
    mocker.patch(
        "tethys_apps.base.workspace.get_app_workspace", return_value=str(tmp_path)
    )
    mocker.patch(
        "tethysapp.app_store.scaffold_handler.has_permission", side_effect=[False]
    )
    url = reverse("app_store:scaffold_app")
    data = {}

    api_response = mock_admin_api_post_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 401
    json_response = json.loads(api_response.content)
    assert json_response["message"] == "Missing required permissions"


@pytest.mark.django_db
def test_scaffold_command(mock_admin_api_post_request, mocker, tmp_path):
    mock_workspace = MagicMock(path=str(tmp_path))
    mocker.patch(
        "tethys_apps.base.workspace.get_app_workspace", return_value=mock_workspace
    )
    mocker.patch("tethysapp.app_store.scaffold_handler.install_app")
    mocker.patch(
        "tethysapp.app_store.scaffold_handler.has_permission", side_effect=[True]
    )
    url = reverse("app_store:scaffold_app")
    data = {
        "name": "new-Name",
        "proper_name": " my First APP",
        "description": "Description",
        "tags": "",
        "author_name": "",
        "author_email": "",
        "license_name": "",
        "overwrite": True,
    }

    api_response = mock_admin_api_post_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 200
    json_response = json.loads(api_response.content)
    assert json_response["status"] == "true"
    assert json_response["message"] == "App scaffold Succeeded."
    assert (tmp_path / "install_status" / "scaffoldRunning").is_file()
    app_name = data["name"].replace("-", "_").lower()
    assert (tmp_path / "develop" / f"tethysapp-{app_name}" / "install.yml").is_file()
    assert (tmp_path / "develop" / f"tethysapp-{app_name}" / "setup.py").is_file()
    assert (
        tmp_path / "develop" / f"tethysapp-{app_name}" / "tethysapp" / app_name
    ).is_dir()
    app_py = (
        tmp_path
        / "develop"
        / f"tethysapp-{app_name}"
        / "tethysapp"
        / app_name
        / "app.py"
    )
    assert app_py.is_file()


@pytest.mark.django_db
def test_scaffold_command_template_error(mock_admin_api_post_request, mocker, tmp_path):
    mock_workspace = MagicMock(path=str(tmp_path))
    mocker.patch(
        "tethys_apps.base.workspace.get_app_workspace", return_value=mock_workspace
    )
    mocker.patch("tethysapp.app_store.scaffold_handler.install_app")
    mocker.patch("tethysapp.app_store.scaffold_handler.APP_PATH", "nonexistent_path")
    mocker.patch(
        "tethysapp.app_store.scaffold_handler.has_permission", side_effect=[True]
    )
    url = reverse("app_store:scaffold_app")
    data = {
        "name": "newName",
        "proper_name": " my First APP",
        "description": "Description",
        "tags": "",
        "author_name": "",
        "author_email": "",
        "license_name": "",
        "overwrite": True,
    }

    api_response = mock_admin_api_post_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 500
    json_response = json.loads(api_response.content)
    assert json_response["status"] == "false"
    assert json_response["message"] == 'Error: "default" is not a valid template.'


@pytest.mark.django_db
def test_scaffold_command_bad_project_name(
    mock_admin_api_post_request, mocker, tmp_path
):
    mock_workspace = MagicMock(path=str(tmp_path))
    mocker.patch(
        "tethys_apps.base.workspace.get_app_workspace", return_value=mock_workspace
    )
    mocker.patch("tethysapp.app_store.scaffold_handler.install_app")
    mocker.patch(
        "tethysapp.app_store.scaffold_handler.has_permission", side_effect=[True]
    )
    url = reverse("app_store:scaffold_app")
    data = {
        "name": "new/Name",
        "proper_name": " my First APP",
        "description": "Description",
        "tags": "",
        "author_name": "",
        "author_email": "",
        "license_name": "",
        "overwrite": True,
    }

    api_response = mock_admin_api_post_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 400
    json_response = json.loads(api_response.content)
    assert json_response["status"] == "false"
    project_name = data["name"].lower()
    assert (
        json_response["message"]
        == f'Error: Invalid characters in project name "{project_name}". Only letters, numbers, and underscores.'
    )  # noqa: E501


@pytest.mark.django_db
def test_scaffold_command_bad_proper_name(
    mock_admin_api_post_request, mocker, tmp_path
):
    mock_workspace = MagicMock(path=str(tmp_path))
    mocker.patch(
        "tethys_apps.base.workspace.get_app_workspace", return_value=mock_workspace
    )
    mocker.patch("tethysapp.app_store.scaffold_handler.install_app")
    mocker.patch(
        "tethysapp.app_store.scaffold_handler.has_permission", side_effect=[True]
    )
    url = reverse("app_store:scaffold_app")
    data = {
        "name": "newName",
        "proper_name": " my First/APP",
        "description": "Description",
        "tags": "",
        "author_name": "",
        "author_email": "",
        "license_name": "",
        "overwrite": True,
    }

    api_response = mock_admin_api_post_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 400
    json_response = json.loads(api_response.content)
    assert json_response["status"] == "false"
    assert (
        json_response["message"]
        == "Error: Proper name can only contain letters and numbers and spaces."
    )


@pytest.mark.django_db
def test_scaffold_command_unable_to_overwrite(
    mock_admin_api_post_request, mocker, tmp_path
):
    mock_workspace = MagicMock(path=str(tmp_path))
    mocker.patch(
        "tethys_apps.base.workspace.get_app_workspace", return_value=mock_workspace
    )
    mocker.patch("tethysapp.app_store.scaffold_handler.install_app")
    mocker.patch(
        "tethysapp.app_store.scaffold_handler.shutil.rmtree", side_effect=[OSError]
    )
    mocker.patch(
        "tethysapp.app_store.scaffold_handler.has_permission", side_effect=[True]
    )
    url = reverse("app_store:scaffold_app")
    data = {
        "name": "new-Name",
        "proper_name": " my First APP",
        "description": "Description",
        "tags": "",
        "author_name": "",
        "author_email": "",
        "license_name": "",
        "overwrite": True,
    }
    app_name = data["name"].replace("-", "_").lower()
    project_root = tmp_path / "develop" / f"tethysapp-{app_name}"
    project_root.mkdir(parents=True)

    api_response = mock_admin_api_post_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 500
    json_response = json.loads(api_response.content)
    assert json_response["status"] == "false"
    assert (
        json_response["message"]
        == f"Error: Unable to overwrite {str(project_root)}. Please remove the directory and try again."
    )  # noqa: E501
    assert (tmp_path / "install_status" / "scaffoldRunning").is_file()


@pytest.mark.django_db
def test_scaffold_command_overwrite_false(
    mock_admin_api_post_request, mocker, tmp_path
):
    mock_workspace = MagicMock(path=str(tmp_path))
    mocker.patch(
        "tethys_apps.base.workspace.get_app_workspace", return_value=mock_workspace
    )
    mocker.patch("tethysapp.app_store.scaffold_handler.install_app")
    mocker.patch(
        "tethysapp.app_store.scaffold_handler.shutil.rmtree", side_effect=[OSError]
    )
    mocker.patch(
        "tethysapp.app_store.scaffold_handler.has_permission", side_effect=[True]
    )
    url = reverse("app_store:scaffold_app")
    data = {
        "name": "new-Name",
        "proper_name": " my First APP",
        "description": "Description",
        "tags": "",
        "author_name": "",
        "author_email": "",
        "license_name": "",
        "overwrite": False,
    }
    app_name = data["name"].replace("-", "_").lower()
    project_root = tmp_path / "develop" / f"tethysapp-{app_name}"
    project_root.mkdir(parents=True)

    api_response = mock_admin_api_post_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 500
    json_response = json.loads(api_response.content)
    assert json_response["status"] == "false"
    assert (
        json_response["message"]
        == f"Error: App directory exists {project_root} and Overwrite was not permitted. "
        "Please remove the directory and try again."
    )
    assert (tmp_path / "install_status" / "scaffoldRunning").is_file()


@pytest.mark.django_db
def test_scaffold_command_install_failed(mock_admin_api_post_request, mocker, tmp_path):
    mock_workspace = MagicMock(path=str(tmp_path))
    mocker.patch(
        "tethys_apps.base.workspace.get_app_workspace", return_value=mock_workspace
    )
    mocker.patch(
        "tethysapp.app_store.scaffold_handler.install_app", side_effect=[Exception]
    )
    mocker.patch(
        "tethysapp.app_store.scaffold_handler.has_permission", side_effect=[True]
    )
    url = reverse("app_store:scaffold_app")
    data = {
        "name": "new-Name",
        "proper_name": " my First APP",
        "description": "Description",
        "tags": "",
        "author_name": "",
        "author_email": "",
        "license_name": "",
        "overwrite": True,
    }

    api_response = mock_admin_api_post_request(auth_header=True, url=url, data=data)

    assert api_response.status_code == 500
    json_response = json.loads(api_response.content)
    assert json_response["status"] == "false"
    assert json_response["message"] == "App scaffold failed. Check logs."
    assert (tmp_path / "install_status" / "scaffoldRunning").is_file()
    app_name = data["name"].replace("-", "_").lower()
    assert (tmp_path / "develop" / f"tethysapp-{app_name}" / "install.yml").is_file()
    assert (tmp_path / "develop" / f"tethysapp-{app_name}" / "setup.py").is_file()
    assert (
        tmp_path / "develop" / f"tethysapp-{app_name}" / "tethysapp" / app_name
    ).is_dir()
    app_py = (
        tmp_path
        / "develop"
        / f"tethysapp-{app_name}"
        / "tethysapp"
        / app_name
        / "app.py"
    )
    assert app_py.is_file()
