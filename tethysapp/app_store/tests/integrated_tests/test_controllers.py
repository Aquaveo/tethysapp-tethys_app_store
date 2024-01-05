from tethysapp.app_store.controllers import (home, get_available_stores)
from unittest.mock import call, MagicMock
import json


def test_home_stores(mocker, tmp_path, store, mock_admin_request):
    request = mock_admin_request('/apps/app-store')
    active_store = store('active_default')
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethys_apps.utilities.get_active_app')
    mocker.patch('tethysapp.app_store.controllers.get_conda_stores', return_value=[active_store])
    mock_render = mocker.patch('tethysapp.app_store.controllers.render')

    home(request)

    expected_context = {
        'storesData': [active_store],
        'show_stores': True
    }
    mock_render.assert_has_calls([
        call(request, 'app_store/home.html', expected_context)
    ])


def test_home_no_stores(mocker, tmp_path, mock_admin_request):
    request = mock_admin_request('/apps/app-store')
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethys_apps.utilities.get_active_app')
    mocker.patch('tethysapp.app_store.controllers.get_conda_stores', return_value=[])
    mock_render = mocker.patch('tethysapp.app_store.controllers.render')

    home(request)

    expected_context = {
        'storesData': [],
        'show_stores': False
    }
    mock_render.assert_has_calls([
        call(request, 'app_store/home.html', expected_context)
    ])


def test_home_no_access(mocker, mock_no_permission_request):
    mock_messages = MagicMock()
    request = mock_no_permission_request('/apps/app-store')
    request._messages = mock_messages
    mocker.patch('tethys_apps.utilities.get_active_app')
    mock_render = mocker.patch('tethysapp.app_store.controllers.render')

    home(request)

    mock_render.assert_not_called()
    mock_messages.add.assert_called_with(30, "We're sorry, but the operation you requested cannot be found.", '')


def test_get_available_stores(mocker, tmp_path, store, mock_admin_request):
    request = mock_admin_request('/app-store/get_available_stores')
    active_store = store('active_default')
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethys_apps.utilities.get_active_app')
    mocker.patch('tethysapp.app_store.controllers.get_conda_stores', return_value=[active_store])

    stores = get_available_stores(request)
    expected_stores = {"stores": [active_store]}
    assert json.loads(stores.content) == expected_stores


def test_get_available_stores_no_access(mocker, mock_no_permission_request):
    mock_messages = MagicMock()
    request = mock_no_permission_request('/app-store/get_available_stores')
    request._messages = mock_messages
    mocker.patch('tethys_apps.utilities.get_active_app')

    get_available_stores(request)

    mock_messages.add.assert_called_with(30, "We're sorry, but the operation you requested cannot be found.", '')


# def test_home_stores(mocker, tmp_path, store, mock_admin_request):
#     request = mock_admin_request('/apps/app-store', {'active_store': 'test_channel'})
#     active_store = store('active_default')
#     mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
#     mocker.patch('tethys_apps.utilities.get_active_app')
#     mocker.patch('tethysapp.app_store.controllers.get_stores_reformatted')
#     mock_render = mocker.patch('tethysapp.app_store.controllers.render')

#     get_merged_resources(request)

#     expected_context = {
#         'storesData': [active_store],
#         'show_stores': True
#     }
#     mock_render.assert_has_calls([
#         call(request, 'app_store/home.html', expected_context)
#     ])
