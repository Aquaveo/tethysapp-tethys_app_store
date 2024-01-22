import pytest
from unittest.mock import MagicMock
import shutil
from pathlib import Path
import json
from tethys_apps.base import TethysAppBase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


class TestApp(TethysAppBase):
    name = 'Test App'
    init_ran = False
    package = 'test_app'

    def __init__(self):
        self.init_ran = True

    def custom_settings(self):
        mock_setting = MagicMock()
        mock_setting.name = "mock_setting"
        return [mock_setting]


@pytest.fixture()
def tethysapp():
    return TestApp


@pytest.fixture()
def app_store_dir():
    app_store_dir = Path(__file__).parent.parent

    return app_store_dir


@pytest.fixture()
def app_files_dir(app_store_dir):
    app_files_dir = app_store_dir / "application_files"

    return app_files_dir


@pytest.fixture()
def test_files_dir():
    current_dir = Path(__file__).parent
    app_files_dir = current_dir / "files"

    return app_files_dir


@pytest.fixture
def store():
    def _store(id, default=True, active=True, conda_labels=None):
        if not conda_labels:
            conda_labels = ['main']

        return {
            'default': default,
            'conda_labels': conda_labels,
            'github_token': f'fake_token_{id}',
            'conda_channel': f'conda_channel_{id}',
            'github_organization': f'org_{id}',
            'conda_style': 'blue',
            'active': active
        }
    return _store


@pytest.fixture
def all_active_stores(store):
    return {
        "active_default": store("active_default"),
        "active_not_default": store("active_not_default", default=False)
    }


@pytest.fixture
def mix_active_inactive_stores(store):
    return {
        "active_default": store("active_default"),
        "inactive_not_default": store("inactive_not_default", default=False, active=False)
    }


@pytest.fixture
def all_inactive_stores(store):
    return {
        "inactive_default": store("inactive_default", active=False),
        "inactive_not_default": store("inactive_not_default", default=False, active=False)
    }


@pytest.fixture
def fresh_resource():
    def _fresh_resource(app_name, conda_channel, conda_label):
        return {
            'name': app_name,
            'installed': {conda_channel: {conda_label: False}},
            'versions': {conda_channel: {conda_label: ["1.0"]}},
            'versionURLs': {conda_channel: {conda_label: ["versionURL"]}},
            'channels_and_labels': {conda_channel: {conda_label: []}},
            'timestamp': {conda_channel: {conda_label: "timestamp"}},
            'compatibility': {conda_channel: {conda_label: {}}},
            'license': {conda_channel: {conda_label: None}},
            'licenses': {conda_channel: {conda_label: []}}
        }
    return _fresh_resource


@pytest.fixture
def resource():
    def _resource(app_name, conda_channel, conda_label):
        return {
            'name': app_name,
            'installed': {conda_channel: {conda_label: False}},
            'installedVersion': {conda_channel: {conda_label: "1.0"}},
            'latestVersion': {conda_channel: {conda_label: "1.0"}},
            'versions': {conda_channel: {conda_label: ["1.0"]}},
            'versionURLs': {conda_channel: {conda_label: ["versionURL"]}},
            'channels_and_labels': {conda_channel: {conda_label: []}},
            'timestamp': {conda_channel: {conda_label: "timestamp"}},
            'compatibility': {conda_channel: {conda_label: {}}},
            'license': {conda_channel: {conda_label: None}},
            'licenses': {conda_channel: {conda_label: []}},
            'author': {conda_channel: {conda_label: 'author'}},
            'description': {conda_channel: {conda_label: 'description'}},
            'author_email': {conda_channel: {conda_label: 'author_email'}},
            'keywords': {conda_channel: {conda_label: 'keywords'}},
            'dev_url': {conda_channel: {conda_label: 'url'}}
        }
    return _resource


@pytest.fixture()
def store_with_resources(resource, store):
    def _store_with_resources(store_name, conda_labels, available_apps_label=None, available_apps_name="",
                              installed_apps_label=None, installed_apps_name="", incompatible_apps_label=None,
                              incompatible_apps_name=""):
        active_store = store(store_name, conda_labels=conda_labels)
        available_app = {}
        installed_app = {}
        incompatible_app = {}

        if available_apps_label:
            if available_apps_name:
                app_name = available_apps_name
            else:
                app_name = f"{store_name}_available_app_{available_apps_label}"
            available_app = {app_name: resource(app_name, active_store['conda_channel'], available_apps_label)}

        if installed_apps_label:
            if installed_apps_name:
                app_name = installed_apps_name
            else:
                app_name = f"{store_name}_installed_app_{installed_apps_label}"
            installed_app = {app_name: resource(app_name, active_store['conda_channel'], installed_apps_label)}

        if incompatible_apps_label:
            if incompatible_apps_name:
                app_name = incompatible_apps_name
            else:
                app_name = f"{store_name}_incompatible_app_{incompatible_apps_label}"
            incompatible_app = {app_name: resource(app_name, active_store['conda_channel'], incompatible_apps_label)}

        resources = {
            'availableApps': available_app,
            'installedApps': installed_app,
            'incompatibleApps': incompatible_app
        }

        return (active_store, resources)

    return _store_with_resources


@pytest.fixture()
def tethysapp_base(tmp_path):
    tethysapp_base_dir = tmp_path / "tethysapp-test_app"
    tethysapp_dir = tethysapp_base_dir / "tethysapp"
    app_dir = tethysapp_dir / "test_app"

    app_dir.mkdir(parents=True)

    return tethysapp_base_dir


@pytest.fixture()
def tethysapp_base_with_application_files(tethysapp_base, app_files_dir, test_files_dir):

    conda_recipes_dir = tethysapp_base / "conda.recipes"
    conda_recipes_dir.mkdir()

    meta_template = app_files_dir / "meta_template.yaml"
    tethysapp_meta_template = conda_recipes_dir / "meta.yaml"
    shutil.copy(meta_template, tethysapp_meta_template)

    getChannels = app_files_dir / "getChannels.py"
    tethysapp_getChannels = tethysapp_base / "getChannels.py"
    shutil.copy(getChannels, tethysapp_getChannels)

    setup_helper = app_files_dir / "setup_helper.py"
    tethysapp_setup_helper = tethysapp_base / "setup_helper.py"
    shutil.copy(setup_helper, tethysapp_setup_helper)

    setup_helper = test_files_dir / "setup.py"
    tethysapp_setup_helper = tethysapp_base / "setup.py"
    shutil.copy(setup_helper, tethysapp_setup_helper)

    setup_helper = test_files_dir / "install_pip.sh"
    tethysapp_scripts = tethysapp_base / "tethysapp" / "test_app" / "scripts"
    tethysapp_scripts.mkdir(parents=True)
    tethysapp_setup_helper = tethysapp_scripts / "install_pip.sh"
    shutil.copy(setup_helper, tethysapp_setup_helper)

    setup_helper = app_files_dir / "__init__.py"
    tethysapp_setup_helper = tethysapp_base / "__init__.py"
    shutil.copy(setup_helper, tethysapp_setup_helper)

    return tethysapp_base


@pytest.fixture()
def basic_tethysapp(tethysapp_base_with_application_files, test_files_dir):
    test_install_yaml = test_files_dir / "basic_install.yml"
    tethysapp_install_yaml = tethysapp_base_with_application_files / "install.yml"
    shutil.copy(test_install_yaml, tethysapp_install_yaml)

    return tethysapp_base_with_application_files


@pytest.fixture()
def complex_tethysapp(tethysapp_base_with_application_files, test_files_dir):
    test_install_yaml = test_files_dir / "complex_install.yml"
    tethysapp_install_yaml = tethysapp_base_with_application_files / "install.yml"
    shutil.copy(test_install_yaml, tethysapp_install_yaml)

    return tethysapp_base_with_application_files


@pytest.fixture()
def basic_meta_yaml(test_files_dir):
    basic_meta_yaml = test_files_dir / "basic_meta.yaml"

    return basic_meta_yaml


@pytest.fixture()
def complex_meta_yaml(test_files_dir):
    complex_meta_yaml = test_files_dir / "complex_meta.yaml"

    return complex_meta_yaml


@pytest.fixture()
def install_pip_bash(test_files_dir):
    install_pip_bash = test_files_dir / "install_pip.sh"

    return install_pip_bash


@pytest.fixture()
def mock_admin_get_request(rf, admin_user):
    def _mock_admin_get_request(url):
        request = rf.get(url)
        request.user = admin_user
        return request

    return _mock_admin_get_request


@pytest.fixture()
def mock_admin_api_request(rf, admin_user, get_or_create_token):
    def _mock_admin_api_request(url, data=None, auth_header=False):
        client = APIClient()

        if auth_header:
            token = get_or_create_token(user=admin_user)
            client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        else:
            client.credentials()

        response = client.post(url, data, format='json')
        return response

    return _mock_admin_api_request


@pytest.fixture()
def mock_no_permission_get_request(rf, django_user_model):
    def _mock_no_permission_get_request(url):
        request = rf.get(url)
        new_user = django_user_model.objects.create(username="someone", password="something")
        request.user = new_user
        return request

    return _mock_no_permission_get_request


@pytest.fixture
def get_or_create_token():
    def _get_or_create_token(user):
        token, _ = Token.objects.get_or_create(user=user)
        return token

    return _get_or_create_token


@pytest.fixture
def git_status_workspace(tmp_path, complex_tethysapp):
    workspace = tmp_path / "workspaces"
    workspace_apps = workspace / "apps" / "github_installed"
    workspace_apps.mkdir(parents=True)

    test_app_git = workspace_apps / "test_app"
    shutil.copytree(complex_tethysapp, test_app_git)

    workspace_logs = workspace / "logs" / "github_install"
    workspace_logs.mkdir(parents=True)
    install_status_dir = workspace / 'install_status' / 'github'
    install_status_dir.mkdir(parents=True)
    statusfile_data = {
        'installID': "abc123",
        'githubURL': 'githubURL',
        'workspacePath': str(test_app_git),
        'installComplete': False,
        'status': {
            "installStarted": True,
            "conda": "Pending",
            "pip": "Pending",
            "setupPy": "Pending",
            "dbSync": "Pending",
            "post": "Pending"
        },
        'installStartTime': '2024-01-01T00:00:00.0000'
    }
    statusfile_json = install_status_dir / "abc123.json"
    with open(statusfile_json, 'w') as outfile:
        json.dump(statusfile_data, outfile)
    statusfile_log = workspace_logs / "abc123.log"
    statusfile_log.touch()

    return workspace
