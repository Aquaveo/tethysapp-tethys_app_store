import filecmp
import pytest
from unittest import mock
from github.GithubException import UnknownObjectException
from tethysapp.app_store.submission_handlers import (update_anaconda_dependencies, get_github_repo, 
                                                     pull_git_repo_all)


def test_update_anaconda_dependencies_no_pip(basic_tethysapp, app_files_dir, basic_meta_yaml):
    
    recipe_path = basic_tethysapp / "conda.recipes"
    
    update_anaconda_dependencies(basic_tethysapp, recipe_path, app_files_dir)
    
    test_app_meta_yaml = recipe_path / "meta.yaml"
    assert filecmp.cmp(test_app_meta_yaml, basic_meta_yaml, shallow=False)
    
    test_install_pip = basic_tethysapp / "tethysapp" / "test_app" / "scripts" / "install_pip.sh"
    assert not test_install_pip.is_file()


def test_update_anaconda_dependencies_with_pip(complex_tethysapp, app_files_dir, complex_meta_yaml, install_pip_bash):
    
    recipe_path = complex_tethysapp / "conda.recipes"
    
    update_anaconda_dependencies(complex_tethysapp, recipe_path, app_files_dir)
    
    test_app_meta_yaml = recipe_path / "meta.yaml"
    assert filecmp.cmp(test_app_meta_yaml, complex_meta_yaml, shallow=False)
    
    test_install_pip = complex_tethysapp / "tethysapp" / "test_app" / "scripts" / "install_pip.sh"
    assert filecmp.cmp(test_install_pip, install_pip_bash, shallow=False)


def test_repo_exists(mocker, caplog):
    organization_login = "test_org"
    repo_name = "test_app"
    mock_organization = mocker.patch('github.Organization.Organization')
    mock_organization.login = organization_login
    mock_repository = mock.MagicMock(full_name="github-org/test_app")
    mock_organization.get_repo.return_value = mock_repository
    
    tethysapp_repo = get_github_repo(repo_name, mock_organization)
    assert tethysapp_repo == mock_repository

    mock_organization.get_repo.assert_called_once()
    mock_organization.create_repo.assert_not_called()
    
    logger_message = f"{organization_login}/{repo_name} Exists. Will have to delete"
    assert logger_message in caplog.messages


def test_repo_does_not_exist(mocker, caplog):
    organization_login = "test_org"
    repo_name = "test_app"
    error_status = 404
    error_message = "Not Found"
    
    mock_organization = mocker.patch('github.Organization.Organization')
    mock_organization.login = organization_login
    mock_organization.get_repo.side_effect = UnknownObjectException(error_status, message=error_message)
    mock_repository = mock.MagicMock(full_name="github-org/test_app")
    mock_organization.create_repo.return_value = mock_repository
    
    tethysapp_repo = get_github_repo(repo_name, mock_organization)
    assert tethysapp_repo == mock_repository

    mock_organization.get_repo.assert_called_once()
    mock_organization.create_repo.assert_called_once()
    
    logger_message = f"Received a {error_status} error when checking {organization_login}/{repo_name}. " \
                     f"Error: {error_message}"
    assert logger_message in caplog.messages
    
    logger_message = f"Creating a new repository at {organization_login}/{repo_name}"
    assert logger_message in caplog.messages
