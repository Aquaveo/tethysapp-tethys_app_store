import pytest
import shutil
import os
import filecmp
from unittest import mock
from unittest.mock import call
from github.GithubException import UnknownObjectException
from tethysapp.app_store.submission_handlers import (update_anaconda_dependencies, get_github_repo,
                                                     initialize_local_repo_for_active_stores, initialize_local_repo,
                                                     generate_label_strings, create_tethysapp_warehouse_release,
                                                     generate_current_version, reset_folder, copy_files_for_recipe,
                                                     create_upload_command, get_keywords_and_email,
                                                     create_template_data_for_install, fix_setup, remove_init_file,
                                                     apply_main_yml_template, get_head_and_tag_names,
                                                     create_current_tag_version, check_if_organization_in_remote,
                                                     push_to_warehouse_release_remote_branch,
                                                     create_head_current_version, create_tags_for_current_version,
                                                     get_workflow_job_url, process_branch)


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

    # Rerun to test functionality for existing file
    files_changed = False
    files_changed = copy_files_for_recipe(src, dest, files_changed)

    assert not files_changed
    assert dest.is_file()


def test_create_upload_command(tmp_path, app_files_dir):
    labels_string = "main --label dev"
    create_upload_command(labels_string, app_files_dir, tmp_path)

    upload_command_file = tmp_path / "upload_command.txt"
    assert "anaconda upload --force --label main --label dev noarch/*.tar.bz2" == upload_command_file.read_text()

    # Rerun to test functionality for existing file
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


def test_create_template_data_for_install(complex_tethysapp):
    install_data = {'github_dir': complex_tethysapp, "dev_url": "https://github.com/notrealorg/fakeapp"}
    setup_py_data = {
        'name': 'release_package', 'version': '0.0.1', 'description': 'example',
        'long_description': 'This is just an example for testing', 'keywords': 'example,test',
        'author': 'Tester', 'author_email': 'tester@email.com', 'url': '', 'license': 'BSD-3'
    }
    template_data = create_template_data_for_install(install_data, setup_py_data)

    expected_template_data = {
        'metadataObj': "{'name': 'release_package', 'version': '0.0.1', 'description': 'example', "
        "'long_description': 'This is just an example for testing', 'keywords': 'example,test', "
        "'author': 'Tester', 'author_email': 'tester@email.com', 'url': '', 'license': 'BSD-3', "
        "'tethys_version': '>=4.0', 'dev_url': 'https://github.com/notrealorg/fakeapp'}"
    }
    assert template_data == expected_template_data


def test_fix_setup(test_files_dir, tmp_path):
    bad_setup = test_files_dir / "bad_setup.py"
    good_setup = test_files_dir / "setup.py"
    tmp_setup = tmp_path / "setup2.py"
    shutil.copyfile(bad_setup, tmp_setup)

    app_package = fix_setup(tmp_setup)

    assert app_package == "test_app"
    assert filecmp.cmp(tmp_setup, good_setup, shallow=False)


def test_remove_init_file(tethysapp_base_with_application_files):
    install_data = {"github_dir": tethysapp_base_with_application_files}

    remove_init_file(install_data)

    init_file = tethysapp_base_with_application_files / "__init__.py"
    init_file.is_file()


def test_apply_main_yml_template(app_files_dir, tmp_path, mocker):
    rel_package = "test_app"
    install_data = {"email": "test@email.com"}
    mock_apply_template = mocker.patch('tethysapp.app_store.submission_handlers.apply_template')
    apply_main_yml_template(app_files_dir, tmp_path, rel_package, install_data)

    source = os.path.join(app_files_dir, 'main_template.yaml')
    template_data = {
        'subject': "Tethys App Store: Build complete for " + rel_package,
        'email': install_data['email'],
        'buildMsg': """
        Your Tethys App has been successfully built and is now available on the Tethys App Store.
        This is an auto-generated email and this email is not monitored for replies.
        Please send any queries to gromero@aquaveo.com
        """
    }
    destination = os.path.join(tmp_path, 'main.yaml')
    mock_apply_template.assert_called_with(source, template_data, destination)


def test_get_head_and_tag_names():
    tag1 = mock.MagicMock(ref="tag1")
    tag2 = mock.MagicMock(ref="tag2")
    mock_repo = mock.MagicMock()
    mock_repo.get_git_refs.return_value = [tag1, tag2]

    heads = get_head_and_tag_names(mock_repo)

    assert heads == ["tag1", "tag2"]


def test_create_current_tag_version(mocker):
    current_version = "1.0"
    head_names_list = [f"v{current_version}_0_2024_1_1", f"v{current_version}_1_2024_1_1"]
    mock_time = mocker.patch('tethysapp.app_store.submission_handlers.time')
    mock_time.strftime.return_value = "2024_1_1"

    tag = create_current_tag_version(current_version, head_names_list)

    expected_tag = f"v{current_version}_2_2024_1_1"
    assert tag == expected_tag


def test_check_if_organization_in_remote_exists():
    mock_remote = mock.MagicMock()
    github_organization = "test_org"
    mock_repo = mock.MagicMock(remotes={github_organization: mock_remote})
    remote_url = "https://github.com/notrealorg/fakeapp"

    tethysapp_remote = check_if_organization_in_remote(mock_repo, github_organization, remote_url)

    assert mock_remote == tethysapp_remote
    mock_remote.set_url.assert_called_with(remote_url)
    mock_repo.create_remote.assert_not_called()


def test_check_if_organization_in_remote_dne():
    mock_remote = mock.MagicMock()
    github_organization = "test_org"
    mock_repo = mock.MagicMock(remotes={})
    mock_repo.create_remote.side_effect = [mock_remote]
    remote_url = "https://github.com/notrealorg/fakeapp"

    tethysapp_remote = check_if_organization_in_remote(mock_repo, github_organization, remote_url)

    assert mock_remote == tethysapp_remote
    mock_remote.set_url.assert_not_called()
    mock_repo.create_remote.assert_called_with(github_organization, remote_url)


def test_push_to_warehouse_release_remote_branch():
    mock_repo = mock.MagicMock()
    mock_remote = mock.MagicMock()
    file_changed = True
    current_tag_name = "test_tag"

    push_to_warehouse_release_remote_branch(mock_repo, mock_remote, current_tag_name, file_changed)

    mock_repo.git.add.assert_called_with(A=True)
    mock_repo.git.commit.assert_called_with(m=f"tag version {current_tag_name}")
    mock_remote.push.assert_called_with('tethysapp_warehouse_release', force=True)


def test_create_head_current_version():
    mock_repo = mock.MagicMock()
    mock_branch = mock.MagicMock()
    current_tag_name = "v1.0_2_2024_1_1"
    head_names_list = ["v1.0_0_2024_1_1", "v1.0_1_2024_1_1"]
    mock_remote = mock.MagicMock()
    mock_repo.create_head.side_effect = [mock_branch]

    create_head_current_version(mock_repo, current_tag_name, head_names_list, mock_remote)

    mock_repo.git.checkout.assert_called_with(current_tag_name)
    mock_remote.push.assert_called_with(mock_branch)


def test_create_head_current_version_new_tag():
    mock_repo = mock.MagicMock()
    current_tag_name = "v1.0_1_2024_1_1"
    head_names_list = ["v1.0_0_2024_1_1", "v1.0_1_2024_1_1"]
    mock_remote = mock.MagicMock()

    create_head_current_version(mock_repo, current_tag_name, head_names_list, mock_remote)

    mock_repo.git.checkout.assert_called_with(current_tag_name)
    mock_remote.push.assert_called_with(current_tag_name)


def test_create_tags_for_current_version_dne():
    current_tag_name = "v1.0_2_2024_1_1"
    head_names_list = ["v1.0_0_2024_1_1", "v1.0_1_2024_1_1"]
    mock_repo = mock.MagicMock(heads={"tethysapp_warehouse_release": "ref"})
    mock_remote = mock.MagicMock()
    mock_tag = mock.MagicMock()
    mock_repo.create_tag.side_effect = [mock_tag]

    create_tags_for_current_version(mock_repo, current_tag_name, head_names_list, mock_remote)

    mock_repo.create_tag.assert_called_with(
        f"{current_tag_name}_release",
        ref="ref",
        message=f'This is a tag-object pointing to tethysapp_warehouse_release branch with release version {current_tag_name}')  # noqa: E501
    mock_remote.push.assert_called_with(mock_tag)


def test_create_tags_for_current_version_exists():
    current_tag_name = "v1.0_1_2024_1_1"
    head_names_list = ["v1.0_0_2024_1_1", "v1.0_1_2024_1_1_release"]
    mock_repo = mock.MagicMock(heads={"tethysapp_warehouse_release": "ref"})
    mock_remote = mock.MagicMock()
    mock_tag = mock.MagicMock()
    mock_repo.create_tag.side_effect = [mock_tag]

    create_tags_for_current_version(mock_repo, current_tag_name, head_names_list, mock_remote)

    mock_repo.git.tag.assert_called_with('-d', f"{current_tag_name}_release")
    mock_repo.create_tag.assert_called_with(
        f"{current_tag_name}_release",
        ref="ref",
        message=f'This is a tag-object pointing to tethysapp_warehouse_release branch with release version {current_tag_name}')  # noqa: E501
    mock_remote.push.assert_has_calls([call(refspec=f":{current_tag_name}_release"), call(mock_tag)])


def test_get_workflow_job_url(mocker):
    current_tag_name = "v1.0_1_2024_1_1"
    hex = "abc123"
    mocker.patch('tethysapp.app_store.submission_handlers.time')

    mock_repo = mock.MagicMock()
    mock_repo.head.object.hexsha = hex
    mock_remote_repo = mock.MagicMock()
    mock_job = mock.MagicMock(head_sha=hex, html_url="job_url")
    mock_workflow = mock.MagicMock(display_title="tag version v1.0_1_2024_1_1")
    mock_workflow.jobs.return_value = [mock_job]
    mock_remote_repo.get_workflow_runs.return_value = [mock_workflow]

    job_url = get_workflow_job_url(mock_repo, mock_remote_repo, current_tag_name)

    assert job_url == "job_url"


def test_get_workflow_job_url_not_found(mocker):
    current_tag_name = "v1.0_1_2024_1_1"
    hex = "abc123"
    mocker.patch('tethysapp.app_store.submission_handlers.time')

    mock_repo = mock.MagicMock()
    mock_repo.head.object.hexsha = hex
    mock_remote_repo = mock.MagicMock()
    mock_job = mock.MagicMock(head_sha="123abc", html_url="job_url")
    mock_workflow = mock.MagicMock(display_title="tag version v1.0_1_2024_1_1")
    mock_workflow.jobs.return_value = [mock_job]
    mock_remote_repo.get_workflow_runs.return_value = [mock_workflow]

    job_url = get_workflow_job_url(mock_repo, mock_remote_repo, current_tag_name)

    assert job_url is None


def test_process_branch(mix_active_inactive_stores, mocker, basic_tethysapp):
    dev_url = "https://github.com/notrealorg/fakeapp"
    install_data = {
        "github_organization": "fake_org",
        "github_token": "fake_token",
        "github_dir": str(basic_tethysapp),
        "stores": mix_active_inactive_stores,
        "dev_url": dev_url,
        "email": "test@email.com",
        "conda_labels": ["main", "dev"],
        "conda_channel": "test_channel",
        "branch": "test_branch"
    }
    mock_channel = mock.MagicMock()
    mock_github = mocker.patch('tethysapp.app_store.submission_handlers.github')
    mock_github.Github().get_organization().get_repo().git_url.replace.return_value = dev_url
    mocker.patch('tethysapp.app_store.submission_handlers.git')
    mocker.patch('tethysapp.app_store.submission_handlers.get_workflow_job_url', return_value="job_url")
    mock_send_notification = mocker.patch('tethysapp.app_store.submission_handlers.send_notification')

    process_branch(install_data, mock_channel)

    expected_data_json = {
        "data": {
            "githubURL": dev_url,
            "job_url": "job_url",
            "conda_channel": "test_channel"
        },
        "jsHelperFunction": "addComplete",
        "helper": "addModalHelper"
    }
    mock_send_notification.assert_called_with(expected_data_json, mock_channel)
