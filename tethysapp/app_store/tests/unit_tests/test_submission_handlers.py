import pytest
import filecmp
from unittest import mock
from github.GithubException import UnknownObjectException
from tethysapp.app_store.submission_handlers import (update_anaconda_dependencies, get_github_repo,
                                                     initialize_local_repo_for_active_stores, initialize_local_repo,
                                                     generate_label_strings, create_tethysapp_warehouse_release,
                                                     generate_current_version, reset_folder, copy_files_for_recipe,
                                                     create_upload_command, get_keywords_and_email)


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


@pytest.mark.parametrize(
    "stores, expected_call_count", [
        (pytest.lazy_fixture("all_active_stores"), 2),
        (pytest.lazy_fixture("mix_active_inactive_stores"), 1),
        (pytest.lazy_fixture("all_inactive_stores"), 0)])
def test_initialize_local_repo_for_active_stores(stores, expected_call_count, mocker):
    install_data = {
        "url": "https://github.com/notrealorg/fakeapp",
        "stores": stores
    }

    channel_layer = mock.MagicMock()
    app_workspace = "fake_path"
    mock_initialize_local_repo = mocker.patch('tethysapp.app_store.submission_handlers.initialize_local_repo')

    initialize_local_repo_for_active_stores(install_data, channel_layer, app_workspace)

    assert mock_initialize_local_repo.call_count == expected_call_count


def test_initialize_local_repo_fresh(store, tmp_path, mocker):
    github_url = "https://github.com/notrealorg/fakeapp"
    active_store = store("active_default")
    channel_layer = mock.MagicMock()
    app_workspace = mock.MagicMock(path=tmp_path)

    mock_repo = mock.MagicMock()
    mock_branch1 = mock.MagicMock()
    mock_branch1.name = 'origin/commit1'
    mock_branch2 = mock.MagicMock()
    mock_branch2.name = 'origin/commit2'
    mock_git = mocker.patch('git.Repo.init', side_effect=[mock_repo])
    mock_ws = mocker.patch('tethysapp.app_store.submission_handlers.send_notification')

    mock_repo.remote().refs = [mock_branch1, mock_branch2]
    initialize_local_repo(github_url, active_store, channel_layer, app_workspace)

    expected_github_dur = tmp_path / "gitsubmission" / active_store['conda_channel']
    expected_app_github_dur = expected_github_dur / "fakeapp"
    assert expected_github_dur.is_dir()

    mock_git.create_remote.called_with(['origin', github_url])
    mock_git.create_remote().fetch.called_once()

    expected_data_json = {
        "data": {
            "branches": ["commit1", "commit2"],
            "github_dir": expected_app_github_dur,
            "conda_channel": active_store['conda_channel'],
            "github_token": active_store['github_token'],
            "conda_labels": active_store['conda_labels'],
            "github_organization": active_store['github_organization']
        },
        "jsHelperFunction": "showBranches",
        "helper": "addModalHelper"
    }

    mock_ws.called_with([expected_data_json, channel_layer])


def test_initialize_local_repo_already_exists(store, tmp_path, mocker):
    github_url = "https://github.com/notrealorg/fakeapp"
    active_store = store("active_default")
    channel_layer = mock.MagicMock()
    app_workspace = mock.MagicMock(path=tmp_path)
    expected_github_dur = tmp_path / "gitsubmission" / active_store['conda_channel']
    expected_app_github_dur = expected_github_dur / "fakeapp"
    expected_app_github_dur.mkdir(parents=True)

    mock_repo = mock.MagicMock()
    mock_branch1 = mock.MagicMock()
    mock_branch1.name = 'origin/commit1'
    mock_branch2 = mock.MagicMock()
    mock_branch2.name = 'origin/commit2'
    mock_git = mocker.patch('git.Repo.init', side_effect=[mock_repo])
    mock_ws = mocker.patch('tethysapp.app_store.submission_handlers.send_notification')

    mock_repo.remote().refs = [mock_branch1, mock_branch2]
    initialize_local_repo(github_url, active_store, channel_layer, app_workspace)

    assert expected_github_dur.is_dir()

    mock_git.create_remote.called_with(['origin', github_url])
    mock_git.create_remote().fetch.called_once()

    expected_data_json = {
        "data": {
            "branches": ["commit1", "commit2"],
            "github_dir": expected_app_github_dur,
            "conda_channel": active_store['conda_channel'],
            "github_token": active_store['github_token'],
            "conda_labels": active_store['conda_labels'],
            "github_organization": active_store['github_organization']
        },
        "jsHelperFunction": "showBranches",
        "helper": "addModalHelper"
    }

    mock_ws.called_with([expected_data_json, channel_layer])


@pytest.mark.parametrize(
    "conda_labels, expected_label_string", [
        (["dev", "main"], "dev --label main"),
        (["main"], "main")])
def test_generate_label_strings(conda_labels, expected_label_string):
    label_string = generate_label_strings(conda_labels)

    assert label_string == expected_label_string


def test_create_tethysapp_warehouse_release_app_store_branch_not_exists():
    mock_repo = mock.MagicMock(heads=['main'])
    branch = "test_branch"
    create_tethysapp_warehouse_release(mock_repo, branch)

    mock_repo.create_head.assert_called_with('tethysapp_warehouse_release')
    mock_repo.git.checkout.assert_not_called()
    mock_repo.git.merge.assert_not_called()


def test_create_tethysapp_warehouse_release_app_store_branch_exists():
    mock_repo = mock.MagicMock(heads=['tethysapp_warehouse_release'])
    branch = "test_branch"
    create_tethysapp_warehouse_release(mock_repo, branch)

    mock_repo.create_head.assert_not_called()
    mock_repo.git.checkout.assert_called_with('tethysapp_warehouse_release')
    mock_repo.git.merge.assert_called_with(branch)


def test_generate_current_version():
    mock_repo = mock.MagicMock(heads=['tethysapp_warehouse_release'])
    branch = "test_branch"
    create_tethysapp_warehouse_release(mock_repo, branch)

    mock_repo.create_head.assert_not_called()
    mock_repo.git.checkout.assert_called_with('tethysapp_warehouse_release')
    mock_repo.git.merge.assert_called_with(branch)


def test_generate_current_version():
    setup_py_data = {
        "version": "1.0" 
    }
    version = generate_current_version(setup_py_data)
    
    assert version == setup_py_data['version']


def test_reset_folder(tmp_path):
    test_path = tmp_path / "test_dir"
    test_path.mkdir()
    test2_path = test_path / "test2_dir"
    test2_path.mkdir()
    
    reset_folder(test_path)
    
    assert not test2_path.is_dir()


def test_copy_files_for_recipe(tmp_path, app_files_dir):
    file = "main_template.yaml"
    files_changed = False
    src = app_files_dir / file
    dest = tmp_path / file
    
    files_changed = copy_files_for_recipe(src, dest, files_changed)
    
    assert files_changed
    assert dest.is_file()
    
    # Rerun to test functionality for exising file
    files_changed = False
    files_changed = copy_files_for_recipe(src, dest, files_changed)
    
    assert not files_changed
    assert dest.is_file()


def test_create_upload_command(tmp_path, app_files_dir):
    labels_string = "main --label dev"
    create_upload_command(labels_string, app_files_dir, tmp_path)
    
    upload_command_file = tmp_path / "upload_command.txt"
    assert "anaconda upload --force --label main --label dev noarch/*.tar.bz2" == upload_command_file.read_text()
    
    # Rerun to test functionality for exising file
    labels_string = "main"
    create_upload_command(labels_string, app_files_dir, tmp_path)
    
    upload_command_file = tmp_path / "upload_command.txt"
    assert "anaconda upload --force --label main noarch/*.tar.bz2" == upload_command_file.read_text()

@pytest.mark.parametrize(
    "setup_py_data, expected_keywords, expected_email", [
        ({"keywords": "example, test", "author_email": "tester@email.com"}, ["example", "test"], "tester@email.com"),
        ({"keywords": "example", "author_email": "tester@email.com"}, ["example"], "tester@email.com"),
        ({"keywords": "", "author_email": ""}, [], ""),
        ({}, [], "")])
def test_get_keywords_and_email(setup_py_data, expected_keywords, expected_email):
    
    keywords, email = get_keywords_and_email(setup_py_data)
    
    assert keywords == expected_keywords
    assert email == expected_email