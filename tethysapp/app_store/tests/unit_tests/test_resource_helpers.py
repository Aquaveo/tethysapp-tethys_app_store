from tethysapp.app_store.resource_helpers import (create_pre_multiple_stores_labels_obj, get_resources_single_store,
                                                  get_new_stores_reformated_by_labels, get_stores_reformated_by_channel,
                                                  get_app_channel_for_stores, merge_channels_of_apps)


def test_create_pre_multiple_stores_labels_obj(tmp_path, mocker, store, resource):
    active_store = store('active_default', conda_labels=['main', 'dev'])
    mocker.patch('tethysapp.app_store.resource_helpers.get_conda_stores', return_value=[active_store])
    app_resource_main = resource("test_app", active_store['conda_channel'], active_store['conda_labels'][0])
    app_resource2_main = resource("test_app2", active_store['conda_channel'], active_store['conda_labels'][0])
    app_resource_dev = resource("test_app", active_store['conda_channel'], active_store['conda_labels'][1])
    main_resources = {
        'availableApps': {"test_app": app_resource_main},
        'installedApps': {"test_app": app_resource_main},
        'incompatibleApps': {"test_app2": app_resource2_main},
        'tethysVersion': "4.0.0",
    }
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


def test_get_resources_single_store_compatible_and_installed(tmp_path, mocker, resource):
    require_refresh = False
    conda_channel = 'test_channel'
    conda_label = 'main'
    cache_key = 'test_cache_key'

    app_resource = resource("test_app", conda_channel, conda_label)
    app_resource['versions'][conda_channel][conda_label] = ["1.0"]
    app_resource['compatibility'][conda_channel][conda_label] = {'1.0': '>=4.0.0'}
    app_resource["installed"][conda_channel][conda_label] = True

    app_resource2 = resource("test_app2", conda_channel, conda_label)
    app_resource2['versions'][conda_channel][conda_label] = ["1.0"]
    app_resource2['compatibility'][conda_channel][conda_label] = {'1.0': '<4.0.0'}

    mocker.patch('tethysapp.app_store.resource_helpers.fetch_resources', return_value=[app_resource, app_resource2])
    mocker.patch('tethysapp.app_store.resource_helpers.tethys_version', "4.0.0")

    resources = get_resources_single_store(tmp_path, require_refresh, conda_channel, conda_label, cache_key)

    expected_resources = {
        'availableApps': {"test_app": app_resource},
        'installedApps': {"test_app": app_resource},
        'incompatibleApps': {"test_app2": app_resource2},
        'tethysVersion': "4.0.0",
    }

    assert expected_resources == resources


def test_get_new_stores_reformated_by_labels(store_with_resources):
    store1, main_resources1 = store_with_resources("store1", ['main'], available_apps_label="main",
                                                   installed_apps_label="main")
    store1, dev_resources1 = store_with_resources("store1", ['dev'], incompatible_apps_label="dev")
    store2, main_resources2 = store_with_resources("store1", ['main'], available_apps_label="main",
                                                   installed_apps_label="main")
    store2, dev_resources2 = store_with_resources("store1", ['dev'], incompatible_apps_label="dev")

    object_stores = {
        store1['conda_channel']: {
            "main": main_resources1,
            "dev": dev_resources1
        },
        store2['conda_channel']: {
            "main": main_resources2,
            "dev": dev_resources2
        }
    }

    reformatted_object_stores = get_new_stores_reformated_by_labels(object_stores)

    expected_object_stores = {
        store1['conda_channel']: {
            'availableApps': main_resources1['availableApps'],
            'installedApps': main_resources1['installedApps'],
            'incompatibleApps': dev_resources1['incompatibleApps']
        },
        store2['conda_channel']: {
            'availableApps': main_resources2['availableApps'],
            'installedApps': main_resources2['installedApps'],
            'incompatibleApps': dev_resources2['incompatibleApps']
        }
    }

    assert reformatted_object_stores == expected_object_stores


def test_get_stores_reformated_by_channel(store_with_resources):
    store1, store1_resources = store_with_resources("store_name1", ['main', 'dev'], available_apps_label="main",
                                                    installed_apps_label="main", incompatible_apps_label="dev")
    store2, store2_resources = store_with_resources("store_name2", ['main'], available_apps_label="main",
                                                    installed_apps_label="main")

    object_stores = {store1['conda_channel']: store1_resources, store2['conda_channel']: store2_resources}

    reformatted_object_stores = get_stores_reformated_by_channel(object_stores)

    expected_object_stores = {
        'availableApps': {**store1_resources['availableApps'], **store2_resources['availableApps']},
        'installedApps': {**store1_resources['installedApps'], **store2_resources['installedApps']},
        'incompatibleApps': {**store1_resources['incompatibleApps'], **store2_resources['incompatibleApps']}
    }

    assert reformatted_object_stores == expected_object_stores


def test_get_app_channel_for_stores(store_with_resources):
    available_app_name = "available_app_name"
    installed_app_name = "installed_app_name"
    incompatible_app_name = "incompatible_app_name"
    store1, store1_resources = store_with_resources("store_name1", ['main', 'dev'],
                                                    available_apps_label="main", available_apps_name=available_app_name,
                                                    installed_apps_label="main", installed_apps_name=installed_app_name,
                                                    incompatible_apps_label="dev",
                                                    incompatible_apps_name=incompatible_app_name)
    store2, store2_resources = store_with_resources("store_name2", ['main'],
                                                    available_apps_label="main", available_apps_name=available_app_name,
                                                    installed_apps_label="main", installed_apps_name=installed_app_name)

    object_stores = {store1['conda_channel']: store1_resources, store2['conda_channel']: store2_resources}

    app_channel_obj = get_app_channel_for_stores(object_stores)

    expected_app_channel_obj = {
        'availableApps': {available_app_name: [store1['conda_channel'], store2['conda_channel']]},
        'installedApps': {installed_app_name: [store1['conda_channel'], store2['conda_channel']]},
        'incompatibleApps': {incompatible_app_name: [store1['conda_channel']]}
    }

    assert app_channel_obj == expected_app_channel_obj


def test_merge_channels_of_apps(store_with_resources):
    available_app_name = "available_app_name"
    installed_app_name = "installed_app_name"
    incompatible_app_name = "incompatible_app_name"
    store1, store1_resources = store_with_resources("store_name1", ['main', 'dev'],
                                                    available_apps_label="main", available_apps_name=available_app_name,
                                                    installed_apps_label="main", installed_apps_name=installed_app_name,
                                                    incompatible_apps_label="dev",
                                                    incompatible_apps_name=incompatible_app_name)
    store2, store2_resources = store_with_resources("store_name2", ['main'],
                                                    available_apps_label="dev", available_apps_name=available_app_name,
                                                    installed_apps_label="main", installed_apps_name=installed_app_name)

    object_stores = {store1['conda_channel']: store1_resources, store2['conda_channel']: store2_resources}

    app_channel_obj = {
        'availableApps': {available_app_name: [store1['conda_channel'], store2['conda_channel']]},
        'installedApps': {installed_app_name: [store1['conda_channel'], store2['conda_channel']]},
        'incompatibleApps': {incompatible_app_name: [store1['conda_channel']]}
    }

    merged_channels_app = merge_channels_of_apps(app_channel_obj, object_stores)

    expected_object_stores = {
        'availableApps': {
            available_app_name: {
                'name': available_app_name,
                'installed': {store1['conda_channel']: {'main': False}, store2['conda_channel']: {'dev': False}},
                'installedVersion': {store1['conda_channel']: {'main': "1.0"},
                                     store2['conda_channel']: {'dev': "1.0"}},
                'latestVersion': {store1['conda_channel']: {'main': "1.0"}, store2['conda_channel']: {'dev': "1.0"}},
                'versions': {store1['conda_channel']: {'main': []}, store2['conda_channel']: {'dev': []}},
                'versionURLs': {store1['conda_channel']: {'main': []}, store2['conda_channel']: {'dev': []}},
                'channels_and_labels': {store1['conda_channel']: {'main': []}, store2['conda_channel']: {'dev': []}},
                'timestamp': {store1['conda_channel']: {'main': "timestamp"},
                              store2['conda_channel']: {'dev': "timestamp"}},
                'compatibility': {store1['conda_channel']: {'main': {}}, store2['conda_channel']: {'dev': {}}},
                'license': {store1['conda_channel']: {'main': None}, store2['conda_channel']: {'dev': None}},
                'licenses': {store1['conda_channel']: {'main': []}, store2['conda_channel']: {'dev': []}},
                'author': {store1['conda_channel']: {'main': 'author'}, store2['conda_channel']: {'dev': 'author'}},
                'description': {store1['conda_channel']: {'main': 'description'},
                                store2['conda_channel']: {'dev': 'description'}},
                'author_email': {store1['conda_channel']: {'main': 'author_email'},
                                 store2['conda_channel']: {'dev': 'author_email'}},
                'keywords': {store1['conda_channel']: {'main': 'keywords'},
                             store2['conda_channel']: {'dev': 'keywords'}},
                'dev_url': {store1['conda_channel']: {'main': 'dev_url'}, store2['conda_channel']: {'dev': 'dev_url'}}
            }
        },
        'installedApps': {
            installed_app_name: {
                'name': installed_app_name,
                'installed': {store1['conda_channel']: {'main': False}, store2['conda_channel']: {'main': False}},
                'installedVersion': {store1['conda_channel']: {'main': "1.0"},
                                     store2['conda_channel']: {'main': "1.0"}},
                'latestVersion': {store1['conda_channel']: {'main': "1.0"}, store2['conda_channel']: {'main': "1.0"}},
                'versions': {store1['conda_channel']: {'main': []}, store2['conda_channel']: {'main': []}},
                'versionURLs': {store1['conda_channel']: {'main': []}, store2['conda_channel']: {'main': []}},
                'channels_and_labels': {store1['conda_channel']: {'main': []}, store2['conda_channel']: {'main': []}},
                'timestamp': {store1['conda_channel']: {'main': "timestamp"},
                              store2['conda_channel']: {'main': "timestamp"}},
                'compatibility': {store1['conda_channel']: {'main': {}}, store2['conda_channel']: {'main': {}}},
                'license': {store1['conda_channel']: {'main': None}, store2['conda_channel']: {'main': None}},
                'licenses': {store1['conda_channel']: {'main': []}, store2['conda_channel']: {'main': []}},
                'author': {store1['conda_channel']: {'main': 'author'}, store2['conda_channel']: {'main': 'author'}},
                'description': {store1['conda_channel']: {'main': 'description'},
                                store2['conda_channel']: {'main': 'description'}},
                'author_email': {store1['conda_channel']: {'main': 'author_email'},
                                 store2['conda_channel']: {'main': 'author_email'}},
                'keywords': {store1['conda_channel']: {'main': 'keywords'},
                             store2['conda_channel']: {'main': 'keywords'}},
                'dev_url': {store1['conda_channel']: {'main': 'dev_url'}, store2['conda_channel']: {'main': 'dev_url'}}
            }
        },
        'incompatibleApps': {
            incompatible_app_name: {
                'name': incompatible_app_name,
                'installed': {store1['conda_channel']: {'dev': False}},
                'installedVersion': {store1['conda_channel']: {'dev': "1.0"}},
                'latestVersion': {store1['conda_channel']: {'dev': "1.0"}},
                'versions': {store1['conda_channel']: {'dev': []}},
                'versionURLs': {store1['conda_channel']: {'dev': []}},
                'channels_and_labels': {store1['conda_channel']: {'dev': []}},
                'timestamp': {store1['conda_channel']: {'dev': "timestamp"}},
                'compatibility': {store1['conda_channel']: {'dev': {}}},
                'license': {store1['conda_channel']: {'dev': None}},
                'licenses': {store1['conda_channel']: {'dev': []}},
                'author': {store1['conda_channel']: {'dev': 'author'}},
                'description': {store1['conda_channel']: {'dev': 'description'}},
                'author_email': {store1['conda_channel']: {'dev': 'author_email'}},
                'keywords': {store1['conda_channel']: {'dev': 'keywords'}},
                'dev_url': {store1['conda_channel']: {'dev': 'dev_url'}}
            }
        }
    }

    assert merged_channels_app == expected_object_stores
