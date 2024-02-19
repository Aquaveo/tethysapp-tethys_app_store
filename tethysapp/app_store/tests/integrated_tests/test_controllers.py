from tethysapp.app_store.controllers import (home, get_available_stores, get_merged_resources)
from tethysapp.app_store.helpers import html_label_styles
from unittest.mock import call, MagicMock
import json


def test_home_stores(mocker, tmp_path, store, mock_admin_get_request, resource, proxy_app_install_data):
    request = mock_admin_get_request('/apps/app-store')
    active_store = store('active_default')
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethys_apps.utilities.get_active_app')
    mocker.patch('tethysapp.app_store.controllers.get_conda_stores', return_value=[active_store])
    object_stores = {
        'availableApps': [resource("test_app", active_store['conda_channel'], active_store['conda_labels'][0])],
        'installedApps': [],
        'incompatibleApps': []
    }
    mocker.patch('tethysapp.app_store.controllers.get_stores_reformatted', return_value=object_stores)
    mocker.patch('tethysapp.app_store.controllers.list_proxy_apps', return_value=[proxy_app_install_data])
    mock_render = mocker.patch('tethysapp.app_store.controllers.render')
    mocker.patch('tethysapp.app_store.controllers.tethys_version', "4.0.0")

    home(request)

    expected_styles = {'conda_channel_active_default': {'channel_style': 'blue', 'label_styles': {'main': 'indigo'}}}
    expected_stores = [{
        'default': True, 'conda_labels': [{'label_name': 'main', 'label_style': 'indigo', 'active': True}],
        'github_token': 'fake_token_active_default', 'conda_channel': 'conda_channel_active_default',
        'github_organization': 'org_active_default', 'active': True, 'channel_style': 'blue'
    }]
    expected_context = {
        'storesData': expected_stores,
        'show_stores': True,
        'list_styles': html_label_styles,
        'labels_style_dict': expected_styles,
        'availableApps': object_stores['availableApps'],
        'installedApps': object_stores['installedApps'],
        'proxyApps': [proxy_app_install_data],
        'incompatibleApps': object_stores['incompatibleApps'],
        'tethysVersion': "4.0.0"
    }
    mock_render.assert_has_calls([
        call(request, 'app_store/home.html', expected_context)
    ])


def test_home_no_stores(mocker, tmp_path, mock_admin_get_request):
    request = mock_admin_get_request('/apps/app-store')
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethys_apps.utilities.get_active_app')
    mocker.patch('tethysapp.app_store.controllers.get_conda_stores', return_value=[])
    mocker.patch('tethysapp.app_store.controllers.list_proxy_apps', return_value=[])
    object_stores = {
        'availableApps': [],
        'installedApps': [],
        'incompatibleApps': []
    }
    mocker.patch('tethysapp.app_store.controllers.get_stores_reformatted', return_value=object_stores)
    mock_render = mocker.patch('tethysapp.app_store.controllers.render')
    mocker.patch('tethysapp.app_store.controllers.tethys_version', "4.0.0")

    home(request)

    expected_context = {
        'storesData': [],
        'show_stores': False,
        'list_styles': html_label_styles,
        'labels_style_dict': {},
        'availableApps': [],
        'installedApps': [],
        'incompatibleApps': [],
        'proxyApps': [],
        'tethysVersion': "4.0.0"
    }
    mock_render.assert_has_calls([
        call(request, 'app_store/home.html', expected_context)
    ])


def test_home_no_access(mocker, mock_no_permission_get_request):
    mock_messages = MagicMock()
    request = mock_no_permission_get_request('/apps/app-store')
    request._messages = mock_messages
    mocker.patch('tethys_apps.utilities.get_active_app')
    mock_render = mocker.patch('tethysapp.app_store.controllers.render')

    home(request)

    mock_render.assert_not_called()
    mock_messages.add.assert_called_with(30, "We're sorry, but the operation you requested cannot be found.", '')


def test_get_available_stores(mocker, tmp_path, store, mock_admin_get_request):
    request = mock_admin_get_request('/app-store/get_available_stores')
    active_store = store('active_default')
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethys_apps.utilities.get_active_app')
    mocker.patch('tethysapp.app_store.controllers.get_conda_stores', return_value=[active_store])

    stores = get_available_stores(request)
    expected_stores = {"stores": [active_store]}
    assert json.loads(stores.content) == expected_stores


def test_get_available_stores_no_access(mocker, mock_no_permission_get_request):
    mock_messages = MagicMock()
    request = mock_no_permission_get_request('/app-store/get_available_stores')
    request._messages = mock_messages
    mocker.patch('tethys_apps.utilities.get_active_app')

    get_available_stores(request)

    mock_messages.add.assert_called_with(30, "We're sorry, but the operation you requested cannot be found.", '')


def test_get_merged_resources(store, resource, mocker, mock_admin_get_request, tmp_path):
    request = mock_admin_get_request('/app-store/get_merged_resources')
    active_store = store('active_default', conda_labels=['main', 'dev'])
    mocker.patch('tethys_apps.base.workspace.get_app_workspace', return_value=str(tmp_path))
    mocker.patch('tethys_apps.utilities.get_active_app')
    request.active_store = active_store
    app_resource_main = resource("test_app", active_store['conda_channel'], active_store['conda_labels'][0])
    app_resource2_main = resource("test_app2", active_store['conda_channel'], active_store['conda_labels'][0])
    app_resource2_dev = resource("test_app2", active_store['conda_channel'], active_store['conda_labels'][1])
    mocker.patch('tethysapp.app_store.controllers.tethys_version', "4.0.0")

    list_stores = {
        'availableApps': [app_resource_main],
        'installedApps': [app_resource_main],
        'incompatibleApps': [app_resource2_main, app_resource2_dev]
    }
    mocker.patch('tethysapp.app_store.controllers.get_stores_reformatted', return_value=list_stores)

    object_stores = get_merged_resources(request)

    expected_list_stores = {
        'availableApps': [app_resource_main],
        'installedApps': [app_resource_main],
        'incompatibleApps': [app_resource2_main, app_resource2_dev],
        'tethysVersion': "4.0.0"
    }
    assert json.loads(object_stores.content) == expected_list_stores
