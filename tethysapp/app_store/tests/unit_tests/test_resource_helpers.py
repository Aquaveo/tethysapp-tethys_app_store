from tethysapp.app_store.resource_helpers import (create_pre_multiple_stores_labels_obj, get_resources_single_store)


def test_create_pre_multiple_stores_labels_obj(tmp_path, mocker, store, resource):
    active_store = store('active_default', conda_labels=['main', 'dev'])
    mocker.patch('tethysapp.app_store.resource_helpers.get_conda_stores', return_value=[active_store])
    app_resource_main = resource("test_app", active_store['conda_channel'], active_store['conda_labels'][0])
    main_resources = {
        'availableApps': {"test_app": app_resource_main},
        'installedApps': {"test_app": app_resource_main},
        'incompatibleApps': {},
        'tethysVersion': "4.0.0",
    }
    app_resource_dev = resource("test_app", active_store['conda_channel'], active_store['conda_labels'][1])
    dev_resources = {
        'availableApps': {},
        'installedApps': {},
        'incompatibleApps': {"test_app": app_resource_dev},
        'tethysVersion': "4.0.0",
    }
    mocker.patch('tethysapp.app_store.resource_helpers.get_resources_single_store',
                 side_effect=[main_resources, dev_resources])

    object_stores = create_pre_multiple_stores_labels_obj(tmp_path)

    expected_object_stores = {
        active_store['conda_channel']: {
            "main": main_resources,
            "dev": dev_resources
        }
    }

    assert object_stores == expected_object_stores


def test_get_resources_single_store_incompatible(tmp_path, mocker, resource):
    require_refresh = False
    conda_channel = 'test_channel'
    conda_label = 'main'
    cache_key = 'test_cache_key'
    app_resource = resource("test_app", conda_channel, conda_label)
    app_resource['versions'][conda_channel][conda_label] = ["1.0"]
    app_resource['compatibility'][conda_channel][conda_label] = {'1.0': '<4.0.0'}

    mocker.patch('tethysapp.app_store.resource_helpers.fetch_resources', return_value=[app_resource])
    mocker.patch('tethysapp.app_store.resource_helpers.tethys_version', "4.0.0")

    resources = get_resources_single_store(tmp_path, require_refresh, conda_channel, conda_label, cache_key)

    expected_resources = {
        'availableApps': {},
        'installedApps': {},
        'incompatibleApps': {"test_app": app_resource},
        'tethysVersion': "4.0.0",
    }
    assert expected_resources == resources


def test_get_resources_single_store_compatible_and_installed(tmp_path, mocker, resource):
    require_refresh = False
    conda_channel = 'test_channel'
    conda_label = 'main'
    cache_key = 'test_cache_key'
    app_resource = resource("test_app", conda_channel, conda_label)
    app_resource['versions'][conda_channel][conda_label] = ["1.0"]
    app_resource['compatibility'][conda_channel][conda_label] = {'1.0': '>=4.0.0'}
    app_resource["installed"][conda_channel][conda_label] = True

    mocker.patch('tethysapp.app_store.resource_helpers.fetch_resources', return_value=[app_resource])
    mocker.patch('tethysapp.app_store.resource_helpers.tethys_version', "4.0.0")

    resources = get_resources_single_store(tmp_path, require_refresh, conda_channel, conda_label, cache_key)

    expected_resources = {
        'availableApps': {"test_app": app_resource},
        'installedApps': {"test_app": app_resource},
        'incompatibleApps': {},
        'tethysVersion': "4.0.0",
    }

    assert expected_resources == resources
