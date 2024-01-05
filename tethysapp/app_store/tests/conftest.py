import pytest
import shutil
from pathlib import Path


@pytest.fixture()
def app_files_dir():
    current_dir = Path(__file__).parent.parent
    app_files_dir = current_dir / "application_files"

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
def resource():
    def _resource(app_name, conda_channel, conda_label):
        return {
            'name': app_name,
            'installed': {conda_channel: {conda_label: False}},
            'installedVersion': {conda_channel: {conda_label: "1.0"}},
            'latestVersion': {conda_channel: {conda_label: "1.0"}},
            'versions': {conda_channel: {conda_label: []}},
            'versionURLs': {conda_channel: {conda_label: []}},
            'channels_and_labels': {conda_channel: {conda_label: []}},
            'timestamp': {conda_channel: {conda_label: "timestamp"}},
            'compatibility': {conda_channel: {conda_label: {}}},
            'license': {conda_channel: {conda_label: None}},
            'licenses': {conda_channel: {conda_label: []}}
        }
    return _resource


@pytest.fixture()
def tethysapp_base(tmp_path):
    tethysapp_base_dir = tmp_path / "tethysapp-test_app"
    tethysapp_base_dir.mkdir()

    tethysapp_dir = tethysapp_base_dir / "tethysapp"
    tethysapp_dir.mkdir()

    app_dir = tethysapp_dir / "test_app"
    app_dir.mkdir()

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
def mock_admin_request(rf, admin_user):
    def _mock_admin_request(url):
        request = rf.get(url)
        request.user = admin_user
        return request

    return _mock_admin_request
