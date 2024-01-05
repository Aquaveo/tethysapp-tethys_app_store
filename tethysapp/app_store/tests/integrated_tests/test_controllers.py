from tethysapp.app_store.controllers import (home)
from unittest.mock import call


def test_home_stores(mocker, tmp_path, store, mock_admin_request):
    request = mock_admin_request('/apps/app-store')
    encryption_key = 'fake_encryption_key'
    active_store = store('active_default')
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethys_apps.utilities.get_active_app')
    mock_app = mocker.patch('tethysapp.app_store.controllers.app')
    mock_app.get_custom_setting.side_effect = [{'stores': [active_store]}, encryption_key]
    mock_decrypt = mocker.patch('tethysapp.app_store.controllers.decrypt', side_effect='decrypted_token')
    mock_render = mocker.patch('tethysapp.app_store.controllers.render')

    home(request)

    mock_decrypt.assert_has_calls([
        call('fake_token_active_default', encryption_key)
    ])
    active_store['github_token'] = 'decrypted_token'
    expected_context = {
        'storesData': [active_store],
        'show_stores': True
    }
    mock_render.assert_has_calls([
        call(request, 'app_store/home.html', expected_context)
    ])


def test_home_no_stores(mocker, tmp_path, mock_admin_request):
    request = mock_admin_request('/apps/app-store')
    encryption_key = 'fake_encryption_key'
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethys_apps.utilities.get_active_app')
    mock_app = mocker.patch('tethysapp.app_store.controllers.app')
    mock_app.get_custom_setting.side_effect = [{'stores': []}, encryption_key]
    mock_decrypt = mocker.patch('tethysapp.app_store.controllers.decrypt', side_effect='decrypted_token')
    mock_render = mocker.patch('tethysapp.app_store.controllers.render')

    home(request)

    mock_decrypt.assert_not_called()
    expected_context = {
        'storesData': [],
        'show_stores': False
    }
    mock_render.assert_has_calls([
        call(request, 'app_store/home.html', expected_context)
    ])
