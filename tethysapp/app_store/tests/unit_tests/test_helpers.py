from tethysapp.app_store.helpers import (parse_setup_py, get_conda_stores)


def test_parse_setup_py(test_files_dir):
    setup_py = test_files_dir / "setup.py"

    parsed_data = parse_setup_py(setup_py)

    expected_data = {
        'name': 'release_package', 'version': '0.0.1', 'description': 'example',
        'long_description': 'This is just an example for testing', 'keywords': 'example,test',
        'author': 'Tester', 'author_email': 'tester@email.com', 'url': '', 'license': 'BSD-3'
    }
    assert parsed_data == expected_data


def test_get_conda_stores(mocker, store):
    mock_app = mocker.patch('tethysapp.app_store.helpers.app')
    encryption_key = 'fake_encryption_key'
    active_store = store('active_default')
    inactive_store = store("inactive_not_default", default=False, active=False)
    mock_app.get_custom_setting.side_effect = [{'stores': [active_store, inactive_store]}, encryption_key]
    mocker.patch('tethysapp.app_store.helpers.decrypt', return_value='decrypted_token')

    stores = get_conda_stores()

    active_store['github_token'] = 'decrypted_token'
    inactive_store['github_token'] = 'decrypted_token'
    expected_stores = [active_store, inactive_store]
    assert stores == expected_stores


def test_get_conda_stores_active(mocker, store):
    mock_app = mocker.patch('tethysapp.app_store.helpers.app')
    encryption_key = 'fake_encryption_key'
    active_store = store('active_default')
    inactive_store = store("inactive_not_default", default=False, active=False)
    mock_app.get_custom_setting.side_effect = [{'stores': [active_store, inactive_store]}, encryption_key]
    mocker.patch('tethysapp.app_store.helpers.decrypt', return_value='decrypted_token')

    stores = get_conda_stores(active_only=True)

    active_store['github_token'] = 'decrypted_token'
    expected_stores = [active_store]
    assert stores == expected_stores


def test_get_conda_stores_specific_str(mocker, store):
    mock_app = mocker.patch('tethysapp.app_store.helpers.app')
    encryption_key = 'fake_encryption_key'
    active_store = store('active_default')
    inactive_store = store("inactive_not_default", default=False, active=False)
    mock_app.get_custom_setting.side_effect = [{'stores': [active_store, inactive_store]}, encryption_key]
    mocker.patch('tethysapp.app_store.helpers.decrypt', return_value='decrypted_token')

    stores = get_conda_stores(channel_names="conda_channel_inactive_not_default")

    inactive_store['github_token'] = 'decrypted_token'
    expected_stores = [inactive_store]
    assert stores == expected_stores


def test_get_conda_stores_specific_list(mocker, store):
    mock_app = mocker.patch('tethysapp.app_store.helpers.app')
    encryption_key = 'fake_encryption_key'
    active_store = store('active_default')
    inactive_store = store("inactive_not_default", default=False, active=False)
    mock_app.get_custom_setting.side_effect = [{'stores': [active_store, inactive_store]}, encryption_key]
    mocker.patch('tethysapp.app_store.helpers.decrypt', return_value='decrypted_token')

    stores = get_conda_stores(channel_names=["conda_channel_inactive_not_default", "conda_channel_active_default"])

    active_store['github_token'] = 'decrypted_token'
    inactive_store['github_token'] = 'decrypted_token'
    expected_stores = [active_store, inactive_store]
    assert stores == expected_stores
