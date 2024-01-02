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
            id: {
                'default': default,
                'conda_labels': conda_labels,
                'github_token': f'fake_token_{id}',
                'conda_channel': f'conda_channel_{id}',
                'github_organization': f'org_{id}',
                'conda_style': 'blue',
                'active': active
            }
        }
    return _store


@pytest.fixture
def active_default_store(store):
    return store("active_default")


@pytest.fixture
def active_not_default_store(store):
    return store("active_not_default", default=False)


@pytest.fixture
def inactive_default_store(store):
    return store("inactive_default", active=False)


@pytest.fixture
def inactive_not_default_store(store):
    return store("inactive_not_default", default=False, active=False)
