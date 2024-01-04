import pytest
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
