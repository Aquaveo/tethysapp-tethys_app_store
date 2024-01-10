from unittest.mock import call, MagicMock
import json
import pytest
import shutil
import sys
from tethysapp.app_store.resource_helpers import (create_pre_multiple_stores_labels_obj, get_resources_single_store,
                                                  get_new_stores_reformated_by_labels, get_stores_reformated_by_channel,
                                                  get_app_channel_for_stores, merge_channels_of_apps, fetch_resources,
                                                  get_stores_reformatted, clear_conda_channel_cache, process_resources,
                                                  merge_labels_single_store, get_app_label_obj_for_store,
                                                  merge_labels_for_app_in_store, get_resource, check_if_app_installed,
                                                  add_keys_to_app_metadata, get_app_instance_from_path)


def test_clear_conda_channel_cache(mocker, store):
    store_name = 'active_default'
    conda_labels = ['main', 'dev']
    active_store = store(store_name, conda_labels=conda_labels)
    mocker.patch('tethysapp.app_store.resource_helpers.get_conda_stores', return_value=[active_store])
    mock_cache = mocker.patch('tethysapp.app_store.resource_helpers.cache')

    clear_conda_channel_cache({}, None)

    mock_calls = [call(f'{active_store["conda_channel"]}_{conda_label}_app_resources') for conda_label in conda_labels]
    mock_cache.delete.assert_has_calls(mock_calls)


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
                'versions': {store1['conda_channel']: {'main': ["1.0"]}, store2['conda_channel']: {'dev': ["1.0"]}},
                'versionURLs': {store1['conda_channel']: {'main': ["versionURL"]},
                                store2['conda_channel']: {'dev': ["versionURL"]}},
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
                'dev_url': {store1['conda_channel']: {'main': 'url'}, store2['conda_channel']: {'dev': 'url'}}
            }
        },
        'installedApps': {
            installed_app_name: {
                'name': installed_app_name,
                'installed': {store1['conda_channel']: {'main': False}, store2['conda_channel']: {'main': False}},
                'installedVersion': {store1['conda_channel']: {'main': "1.0"},
                                     store2['conda_channel']: {'main': "1.0"}},
                'latestVersion': {store1['conda_channel']: {'main': "1.0"}, store2['conda_channel']: {'main': "1.0"}},
                'versions': {store1['conda_channel']: {'main': ["1.0"]}, store2['conda_channel']: {'main': ["1.0"]}},
                'versionURLs': {store1['conda_channel']: {'main': ["versionURL"]},
                                store2['conda_channel']: {'main': ["versionURL"]}},
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
                'dev_url': {store1['conda_channel']: {'main': 'url'}, store2['conda_channel']: {'main': 'url'}}
            }
        },
        'incompatibleApps': {
            incompatible_app_name: {
                'name': incompatible_app_name,
                'installed': {store1['conda_channel']: {'dev': False}},
                'installedVersion': {store1['conda_channel']: {'dev': "1.0"}},
                'latestVersion': {store1['conda_channel']: {'dev': "1.0"}},
                'versions': {store1['conda_channel']: {'dev': ["1.0"]}},
                'versionURLs': {store1['conda_channel']: {'dev': ["versionURL"]}},
                'channels_and_labels': {store1['conda_channel']: {'dev': []}},
                'timestamp': {store1['conda_channel']: {'dev': "timestamp"}},
                'compatibility': {store1['conda_channel']: {'dev': {}}},
                'license': {store1['conda_channel']: {'dev': None}},
                'licenses': {store1['conda_channel']: {'dev': []}},
                'author': {store1['conda_channel']: {'dev': 'author'}},
                'description': {store1['conda_channel']: {'dev': 'description'}},
                'author_email': {store1['conda_channel']: {'dev': 'author_email'}},
                'keywords': {store1['conda_channel']: {'dev': 'keywords'}},
                'dev_url': {store1['conda_channel']: {'dev': 'url'}}
            }
        }
    }

    assert merged_channels_app == expected_object_stores


def test_merge_channels_of_apps_missing_app(store_with_resources):
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
        'availableApps': {},
        'installedApps': {installed_app_name: [store1['conda_channel'], store2['conda_channel']]},
        'incompatibleApps': {incompatible_app_name: [store1['conda_channel']]}
    }

    merged_channels_app = merge_channels_of_apps(app_channel_obj, object_stores)

    expected_object_stores = {
        'availableApps': {
            available_app_name: {}
        },
        'installedApps': {
            installed_app_name: {
                'name': installed_app_name,
                'installed': {store1['conda_channel']: {'main': False}, store2['conda_channel']: {'main': False}},
                'installedVersion': {store1['conda_channel']: {'main': "1.0"},
                                     store2['conda_channel']: {'main': "1.0"}},
                'latestVersion': {store1['conda_channel']: {'main': "1.0"}, store2['conda_channel']: {'main': "1.0"}},
                'versions': {store1['conda_channel']: {'main': ["1.0"]}, store2['conda_channel']: {'main': ["1.0"]}},
                'versionURLs': {store1['conda_channel']: {'main': ["versionURL"]},
                                store2['conda_channel']: {'main': ["versionURL"]}},
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
                'dev_url': {store1['conda_channel']: {'main': 'url'}, store2['conda_channel']: {'main': 'url'}}
            }
        },
        'incompatibleApps': {
            incompatible_app_name: {
                'name': incompatible_app_name,
                'installed': {store1['conda_channel']: {'dev': False}},
                'installedVersion': {store1['conda_channel']: {'dev': "1.0"}},
                'latestVersion': {store1['conda_channel']: {'dev': "1.0"}},
                'versions': {store1['conda_channel']: {'dev': ["1.0"]}},
                'versionURLs': {store1['conda_channel']: {'dev': ["versionURL"]}},
                'channels_and_labels': {store1['conda_channel']: {'dev': []}},
                'timestamp': {store1['conda_channel']: {'dev': "timestamp"}},
                'compatibility': {store1['conda_channel']: {'dev': {}}},
                'license': {store1['conda_channel']: {'dev': None}},
                'licenses': {store1['conda_channel']: {'dev': []}},
                'author': {store1['conda_channel']: {'dev': 'author'}},
                'description': {store1['conda_channel']: {'dev': 'description'}},
                'author_email': {store1['conda_channel']: {'dev': 'author_email'}},
                'keywords': {store1['conda_channel']: {'dev': 'keywords'}},
                'dev_url': {store1['conda_channel']: {'dev': 'url'}}
            }
        }
    }

    assert merged_channels_app == expected_object_stores


def test_reduce_level_obj(store, resource, mocker):
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
    object_stores = {
        active_store['conda_channel']: {
            "main": main_resources,
            "dev": dev_resources
        }
    }
    mocker.patch('tethysapp.app_store.resource_helpers.create_pre_multiple_stores_labels_obj',
                 return_value=object_stores)

    list_stores = get_stores_reformatted(object_stores)

    expected_list_stores = {
        'availableApps': [app_resource_main],
        'installedApps': [app_resource_main],
        'incompatibleApps': [app_resource2_main, app_resource_dev]
    }

    assert list_stores == expected_list_stores


def test_merge_labels_single_store(store, resource):
    active_store = store('active_default', conda_labels=['main', 'dev'])
    app_resource_main = resource("test_app", active_store['conda_channel'], active_store['conda_labels'][0])
    app_resource2_main = resource("test_app2", active_store['conda_channel'], active_store['conda_labels'][0])
    app_resource_dev = resource("test_app2", active_store['conda_channel'], active_store['conda_labels'][1])
    main_resources = {
        'availableApps': {"test_app": app_resource_main},
        'installedApps': {"test_app": app_resource_main},
        'incompatibleApps': {"test_app2": app_resource2_main},
        'tethysVersion': "4.0.0",
    }
    dev_resources = {
        'availableApps': {},
        'installedApps': {},
        'incompatibleApps': {"test_app2": app_resource_dev},
        'tethysVersion': "4.0.0",
    }
    conda_channel = active_store['conda_channel']
    object_stores = {
        conda_channel: {
            "main": main_resources,
            "dev": dev_resources
        }
    }

    ref_object_stores = merge_labels_single_store(object_stores[conda_channel], conda_channel, 'availableApps')
    expected_object_stores = main_resources['availableApps']
    assert ref_object_stores == expected_object_stores

    ref_object_stores = merge_labels_single_store(object_stores[conda_channel], conda_channel, 'installedApps')
    expected_object_stores = main_resources['installedApps']
    assert ref_object_stores == expected_object_stores

    ref_object_stores = merge_labels_single_store(object_stores[conda_channel], conda_channel, 'incompatibleApps')
    expected_object_stores = expected_object_stores = {'test_app2': {
        'name': "test_app2",
        'installed': {active_store['conda_channel']: {'main': False, 'dev': False}},
        'installedVersion': {active_store['conda_channel']: {'main': "1.0", 'dev': "1.0"}},
        'latestVersion': {active_store['conda_channel']: {'main': "1.0", 'dev': "1.0"}},
        'versions': {active_store['conda_channel']: {'main': ["1.0"], 'dev': ["1.0"]}},
        'versionURLs': {active_store['conda_channel']: {'main': ["versionURL"], 'dev': ["versionURL"]}},
        'channels_and_labels': {active_store['conda_channel']: {'main': [], 'dev': []}},
        'timestamp': {active_store['conda_channel']: {'main': "timestamp", 'dev': "timestamp"}},
        'compatibility': {active_store['conda_channel']: {'main': {}, 'dev': {}}},
        'license': {active_store['conda_channel']: {'main': None, 'dev': None}},
        'licenses': {active_store['conda_channel']: {'main': [], 'dev': []}},
        'author': {active_store['conda_channel']: {'main': 'author', 'dev': 'author'}},
        'description': {active_store['conda_channel']: {'main': 'description', 'dev': 'description'}},
        'author_email': {active_store['conda_channel']: {'main': 'author_email', 'dev': 'author_email'}},
        'keywords': {active_store['conda_channel']: {'main': 'keywords', 'dev': 'keywords'}},
        'dev_url': {active_store['conda_channel']: {'main': 'url', 'dev': 'url'}}
    }}
    assert ref_object_stores == expected_object_stores


def test_get_app_label_obj_for_store(store, resource):
    active_store = store('active_default', conda_labels=['main', 'dev'])
    app_resource_main = resource("test_app", active_store['conda_channel'], active_store['conda_labels'][0])
    app_resource2_main = resource("test_app2", active_store['conda_channel'], active_store['conda_labels'][0])
    app_resource_dev = resource("test_app2", active_store['conda_channel'], active_store['conda_labels'][1])
    main_resources = {
        'availableApps': {"test_app": app_resource_main},
        'installedApps': {"test_app": app_resource_main},
        'incompatibleApps': {"test_app2": app_resource2_main},
        'tethysVersion': "4.0.0",
    }
    dev_resources = {
        'availableApps': {},
        'installedApps': {},
        'incompatibleApps': {"test_app2": app_resource_dev},
        'tethysVersion': "4.0.0",
    }
    conda_channel = active_store['conda_channel']
    object_stores = {
        conda_channel: {
            "main": main_resources,
            "dev": dev_resources
        }
    }

    apps_labels = get_app_label_obj_for_store(object_stores[conda_channel], 'availableApps')
    assert apps_labels == {'test_app': ['main']}

    apps_labels = get_app_label_obj_for_store(object_stores[conda_channel], 'installedApps')
    assert apps_labels == {'test_app': ['main']}

    apps_labels = get_app_label_obj_for_store(object_stores[conda_channel], 'incompatibleApps')
    assert apps_labels == {'test_app2': ['main', 'dev']}


def test_merge_labels_for_app_in_store(store, resource):
    active_store = store('active_default', conda_labels=['main', 'dev'])
    app_resource_main = resource("test_app", active_store['conda_channel'], active_store['conda_labels'][0])
    app_resource2_main = resource("test_app2", active_store['conda_channel'], active_store['conda_labels'][0])
    app_resource_dev = resource("test_app2", active_store['conda_channel'], active_store['conda_labels'][1])
    main_resources = {
        'availableApps': {"test_app": app_resource_main},
        'installedApps': {"test_app": app_resource_main},
        'incompatibleApps': {"test_app2": app_resource2_main},
        'tethysVersion': "4.0.0",
    }
    dev_resources = {
        'availableApps': {},
        'installedApps': {},
        'incompatibleApps': {"test_app2": app_resource_dev},
        'tethysVersion': "4.0.0",
    }
    conda_channel = active_store['conda_channel']
    object_stores = {
        conda_channel: {
            "main": main_resources,
            "dev": dev_resources
        }
    }
    app_labels = {'test_app2': ['main', 'dev']}

    merged_label_store = merge_labels_for_app_in_store(app_labels, object_stores[conda_channel], conda_channel,
                                                       'incompatibleApps')

    expected_object_stores = {'test_app2': {
        'name': "test_app2",
        'installed': {active_store['conda_channel']: {'main': False, 'dev': False}},
        'installedVersion': {active_store['conda_channel']: {'main': "1.0", 'dev': "1.0"}},
        'latestVersion': {active_store['conda_channel']: {'main': "1.0", 'dev': "1.0"}},
        'versions': {active_store['conda_channel']: {'main': ["1.0"], 'dev': ["1.0"]}},
        'versionURLs': {active_store['conda_channel']: {'main': ["versionURL"], 'dev': ["versionURL"]}},
        'channels_and_labels': {active_store['conda_channel']: {'main': [], 'dev': []}},
        'timestamp': {active_store['conda_channel']: {'main': "timestamp", 'dev': "timestamp"}},
        'compatibility': {active_store['conda_channel']: {'main': {}, 'dev': {}}},
        'license': {active_store['conda_channel']: {'main': None, 'dev': None}},
        'licenses': {active_store['conda_channel']: {'main': [], 'dev': []}},
        'author': {active_store['conda_channel']: {'main': 'author', 'dev': 'author'}},
        'description': {active_store['conda_channel']: {'main': 'description', 'dev': 'description'}},
        'author_email': {active_store['conda_channel']: {'main': 'author_email', 'dev': 'author_email'}},
        'keywords': {active_store['conda_channel']: {'main': 'keywords', 'dev': 'keywords'}},
        'dev_url': {active_store['conda_channel']: {'main': 'url', 'dev': 'url'}}
    }}

    assert merged_label_store == expected_object_stores


def test_fetch_resources(tmp_path, mocker, resource):
    conda_search_rep = json.dumps({
        "test_app": [{
            "arch": None,
            "build": "py_0",
            "build_number": 0,
            "channel": "https://conda.anaconda.org/test_channel/noarch",
            "constrains": [],
            "depends": [
                "pandas"
            ],
            "fn": "test_app-1.9-py_0.tar.bz2",
            "license": "{'name': 'test_app', 'version': '1.9', 'description': 'description', "
                       "'long_description': 'long_description', 'author': 'author', 'author_email': 'author_email', "
                       "'url': 'url', 'license': 'BSD 3-Clause Clear', 'tethys_version': '>=4.0.0'}",
            "md5": "ab2eb7cc691f4fd984a2216401fabfa1",
            "name": "test_app",
            "noarch": "python",
            "package_type": "noarch_python",
            "platform": None,
            "sha256": "f38c3e39fe3442dc4a72b1acf7415a5e90443139c6684042a5ddf328d06a9354",
            "size": 1907887,
            "subdir": "noarch",
            "timestamp": 1663012608139,
            "url": "https://conda.anaconda.org/test_channel/noarch/test_app-1.9-py_0.tar.bz2",
            "version": "1.9"
        }]
    })
    app_installation = {'isInstalled': False}
    app_resource = resource("test_app", 'conda_channel', 'dev')
    mock_conda = mocker.patch('tethysapp.app_store.resource_helpers.conda_run',
                              return_value=[conda_search_rep, None, 0])
    mocker.patch('tethysapp.app_store.resource_helpers.check_if_app_installed', return_value=app_installation)
    mocker.patch('tethysapp.app_store.resource_helpers.process_resources', return_value=app_resource)
    mock_cache = mocker.patch('tethysapp.app_store.resource_helpers.cache')
    mock_cache.get.side_effect = [None]

    fetched_resource = fetch_resources(tmp_path, "test_channel", conda_label="dev")

    mock_conda.assert_called_with("search", ["-c", "test_channel/label/dev", "--override-channels", "-i", "--json"])
    mock_cache.set.assert_called_with("test_channel", app_resource)
    assert fetched_resource == app_resource


def test_fetch_resources_already_installed_no_license(tmp_path, mocker, resource):
    conda_search_rep = json.dumps({
        "test_app": [{
            "arch": None,
            "build": "py_0",
            "build_number": 0,
            "channel": "https://conda.anaconda.org/test_channel/noarch",
            "constrains": [],
            "depends": [
                "pandas"
            ],
            "fn": "test_app-1.9-py_0.tar.bz2",
            "license": "BSD",
            "md5": "ab2eb7cc691f4fd984a2216401fabfa1",
            "name": "test_app",
            "noarch": "python",
            "package_type": "noarch_python",
            "platform": None,
            "sha256": "f38c3e39fe3442dc4a72b1acf7415a5e90443139c6684042a5ddf328d06a9354",
            "size": 1907887,
            "subdir": "noarch",
            "timestamp": 1663012608139,
            "url": "https://conda.anaconda.org/test_channel/noarch/test_app-1.9-py_0.tar.bz2",
            "version": "1.9"
        }]
    })
    app_installation = {'isInstalled': True, 'channel': 'test_channel', 'version': "1"}
    app_resource = resource("test_app", 'conda_channel', 'main')
    mock_conda = mocker.patch('tethysapp.app_store.resource_helpers.conda_run',
                              return_value=[conda_search_rep, None, 0])
    mocker.patch('tethysapp.app_store.resource_helpers.check_if_app_installed', return_value=app_installation)
    mocker.patch('tethysapp.app_store.resource_helpers.process_resources', return_value=app_resource)
    mock_cache = mocker.patch('tethysapp.app_store.resource_helpers.cache')
    mock_cache.get.side_effect = [None]

    fetched_resource = fetch_resources(tmp_path, "test_channel", conda_label="main")

    mock_conda.assert_called_with("search", ["-c", "test_channel", "--override-channels", "-i", "--json"])
    mock_cache.set.assert_called_with("test_channel", app_resource)
    assert fetched_resource == app_resource


def test_fetch_resources_no_resources(tmp_path, mocker, caplog):
    conda_search_rep = json.dumps({"error": "The following packages are not available from current channels"})
    mock_conda = mocker.patch('tethysapp.app_store.resource_helpers.conda_run',
                              return_value=[conda_search_rep, None, 0])
    mock_cache = mocker.patch('tethysapp.app_store.resource_helpers.cache')
    mock_cache.get.side_effect = [None]

    fetched_resource = fetch_resources(tmp_path, "test_channel", conda_label="dev")

    mock_conda.assert_called_with("search", ["-c", "test_channel/label/dev", "--override-channels", "-i", "--json"])
    assert 'no packages found with the label dev in channel test_channel' in caplog.messages
    assert fetched_resource == []


def test_fetch_resources_non_zero_code(tmp_path, mocker):
    conda_search_rep = json.dumps({})
    mocker.patch('tethysapp.app_store.resource_helpers.conda_run', return_value=[conda_search_rep, None, 9])

    with pytest.raises(Exception) as e_info:
        fetch_resources(tmp_path, "test_channel")
        assert e_info.message == "ERROR: Couldn't search packages in the conda_channel channel"


def test_fetch_resources_cached(tmp_path, mocker, resource, caplog):
    app_resource = resource("test_app", 'conda_channel', 'main')
    mock_cache = mocker.patch('tethysapp.app_store.resource_helpers.cache')
    mock_cache.get.return_value = app_resource

    fetched_resource = fetch_resources(tmp_path, "test_channel")

    assert "Found in cache" in caplog.messages
    assert fetched_resource == app_resource


def test_process_resources_with_license_installed_update_available(fresh_resource, resource, tmp_path, mocker):
    mock_workspace = MagicMock(path=tmp_path)
    conda_channel = "test_channel"
    conda_label = "main"
    app_resources = fresh_resource("test_app", conda_channel, conda_label)
    app_resources['license'][conda_channel][conda_label] = json.dumps({
        'name': 'test_app', 'version': '1.9', 'description': 'description', 'long_description': 'long_description',
        'author': 'author', 'author_email': 'author_email', 'url': 'url', 'license': 'BSD 3-Clause Clear',
        'tethys_version': '>=4.0.0'})
    app_resources['installed'] = {conda_channel: {conda_label: True}}
    app_resources['installedVersion'] = {conda_channel: {conda_label: "0.9"}}
    mocker.patch('tethysapp.app_store.resource_helpers.tethys_version', "4.0.0")

    processed_resources = process_resources([app_resources], mock_workspace, conda_channel, conda_label)[0]
    processed_resources['keywords'][conda_channel][conda_label] = 'keywords'

    expected_resource = resource("test_app", conda_channel, conda_label)
    expected_resource['license'][conda_channel][conda_label] = json.dumps({
        'name': 'test_app', 'version': '1.9', 'description': 'description', 'long_description': 'long_description',
        'author': 'author', 'author_email': 'author_email', 'url': 'url', 'license': 'BSD 3-Clause Clear',
        'tethys_version': '>=4.0.0'})
    expected_resource['updateAvailable'] = {conda_channel: {conda_label: True}}
    expected_resource['installed'] = {conda_channel: {conda_label: True}}
    expected_resource['installedVersion'] = {conda_channel: {conda_label: "0.9"}}

    assert processed_resources == expected_resource


def test_process_resources_with_license_installed(fresh_resource, resource, tmp_path, mocker):
    mock_workspace = MagicMock(path=tmp_path)
    conda_channel = "test_channel"
    conda_label = "main"
    app_resources = fresh_resource("test_app", conda_channel, conda_label)
    app_resources['license'][conda_channel][conda_label] = json.dumps({
        'name': 'test_app', 'version': '1.9', 'description': 'description', 'long_description': 'long_description',
        'author': 'author', 'author_email': 'author_email', 'url': 'url', 'license': 'BSD 3-Clause Clear',
        'tethys_version': '>=4.0.0'})
    app_resources['installed'] = {conda_channel: {conda_label: True}}
    app_resources['installedVersion'] = {conda_channel: {conda_label: "1.0"}}
    mocker.patch('tethysapp.app_store.resource_helpers.tethys_version', "3.9.0")

    processed_resources = process_resources([app_resources], mock_workspace, conda_channel, conda_label)[0]
    processed_resources['keywords'][conda_channel][conda_label] = 'keywords'

    expected_resource = resource("test_app", conda_channel, conda_label)
    expected_resource['license'][conda_channel][conda_label] = json.dumps({
        'name': 'test_app', 'version': '1.9', 'description': 'description', 'long_description': 'long_description',
        'author': 'author', 'author_email': 'author_email', 'url': 'url', 'license': 'BSD 3-Clause Clear',
        'tethys_version': '>=4.0.0'})
    expected_resource['updateAvailable'] = {conda_channel: {conda_label: False}}
    expected_resource['installed'] = {conda_channel: {conda_label: True}}
    expected_resource['latestVersion'] = {conda_channel: {conda_label: "1.0*"}}

    assert processed_resources == expected_resource


def test_process_resources_with_license_installed_without_version(fresh_resource, resource, tmp_path, mocker):
    mock_workspace = MagicMock(path=tmp_path)
    conda_channel = "test_channel"
    conda_label = "main"
    app_resources = fresh_resource("test_app", conda_channel, conda_label)
    app_resources['license'][conda_channel][conda_label] = json.dumps({
        'name': 'test_app', 'version': '1.9', 'description': 'description', 'long_description': 'long_description',
        'author': 'author', 'author_email': 'author_email', 'url': 'url', 'license': 'BSD 3-Clause Clear',
        'tethys_version': '>=4.0.0'})
    app_resources['installed'] = {conda_channel: {conda_label: True}}
    mocker.patch('tethysapp.app_store.resource_helpers.tethys_version', "4.0.0")

    processed_resources = process_resources([app_resources], mock_workspace, conda_channel, conda_label)[0]
    processed_resources['keywords'][conda_channel][conda_label] = 'keywords'

    expected_resource = resource("test_app", conda_channel, conda_label)
    expected_resource['license'][conda_channel][conda_label] = json.dumps({
        'name': 'test_app', 'version': '1.9', 'description': 'description', 'long_description': 'long_description',
        'author': 'author', 'author_email': 'author_email', 'url': 'url', 'license': 'BSD 3-Clause Clear',
        'tethys_version': '>=4.0.0'})
    expected_resource['updateAvailable'] = {conda_channel: {conda_label: False}}
    expected_resource['installed'] = {conda_channel: {conda_label: True}}
    del expected_resource['installedVersion']

    assert processed_resources == expected_resource


def test_process_resources_with_license_not_installed(fresh_resource, resource, tmp_path, mocker):
    mock_workspace = MagicMock(path=tmp_path)
    conda_channel = "test_channel"
    conda_label = "main"
    app_resources = fresh_resource("test_app", conda_channel, conda_label)
    app_resources['license'][conda_channel][conda_label] = json.dumps({
        'name': 'test_app', 'version': '1.9', 'description': 'description', 'long_description': 'long_description',
        'author': 'author', 'author_email': 'author_email', 'url': 'url', 'license': 'BSD 3-Clause Clear',
        'tethys_version': '>=4.0.0'})
    mocker.patch('tethysapp.app_store.resource_helpers.tethys_version', "4.0.0")

    processed_resources = process_resources([app_resources], mock_workspace, conda_channel, conda_label)[0]
    processed_resources['keywords'][conda_channel][conda_label] = 'keywords'

    expected_resource = resource("test_app", conda_channel, conda_label)
    expected_resource['license'][conda_channel][conda_label] = json.dumps({
        'name': 'test_app', 'version': '1.9', 'description': 'description', 'long_description': 'long_description',
        'author': 'author', 'author_email': 'author_email', 'url': 'url', 'license': 'BSD 3-Clause Clear',
        'tethys_version': '>=4.0.0'})
    del expected_resource['installedVersion']

    assert processed_resources == expected_resource


def test_process_resources_with_license_not_installed_no_license_url(fresh_resource, resource, tmp_path, mocker):
    mock_workspace = MagicMock(path=tmp_path)
    conda_channel = "test_channel"
    conda_label = "main"
    app_resources = fresh_resource("test_app", conda_channel, conda_label)
    app_resources['license'][conda_channel][conda_label] = json.dumps({
        'name': 'test_app', 'version': '1.9', 'description': 'description', 'long_description': 'long_description',
        'author': 'author', 'author_email': 'author_email', 'license': 'BSD 3-Clause Clear',
        'tethys_version': '>=4.0.0'})
    mocker.patch('tethysapp.app_store.resource_helpers.tethys_version', "4.0.0")

    processed_resources = process_resources([app_resources], mock_workspace, conda_channel, conda_label)[0]
    processed_resources['keywords'][conda_channel][conda_label] = 'keywords'

    expected_resource = resource("test_app", conda_channel, conda_label)
    expected_resource['license'][conda_channel][conda_label] = json.dumps({
        'name': 'test_app', 'version': '1.9', 'description': 'description', 'long_description': 'long_description',
        'author': 'author', 'author_email': 'author_email', 'license': 'BSD 3-Clause Clear',
        'tethys_version': '>=4.0.0'})
    expected_resource['dev_url'][conda_channel][conda_label] = ''
    del expected_resource['installedVersion']

    assert processed_resources == expected_resource


def test_process_resources_no_license_no_meta_yaml_not_installed(fresh_resource, tmp_path, mocker, caplog):
    mock_workspace = MagicMock(path=tmp_path)
    conda_channel = "test_channel"
    conda_label = "main"
    app_resources = fresh_resource("test_app", conda_channel, conda_label)
    mocker.patch('tethysapp.app_store.resource_helpers.tethys_version', "4.0.0")
    mock_urllib = mocker.patch('tethysapp.app_store.resource_helpers.urllib')
    mock_shutil = mocker.patch('tethysapp.app_store.resource_helpers.shutil')

    processed_resources = process_resources([app_resources], mock_workspace, conda_channel, conda_label)[0]

    expected_resource = fresh_resource("test_app", conda_channel, conda_label)
    expected_resource['latestVersion'] = {conda_channel: {conda_label: "1.0*"}}
    filepath = tmp_path / "apps" / conda_channel / conda_label / "test_app"
    filepath.mkdir(parents=True)
    expected_resource['filepath'] = {conda_channel: {conda_label: str(filepath)}}

    assert processed_resources == expected_resource
    download_path = tmp_path / "apps" / conda_channel / conda_label / "versionURL"
    mock_urllib.request.urlretrieve.assert_called_with("versionURL", str(download_path))
    mock_shutil.unpack_archive.assert_called_with(str(download_path), str(filepath))
    assert "License field metadata not found. Downloading: versionURL" in caplog.messages
    assert "No yaml file available to retrieve metadata" in caplog.messages


def test_process_resources_no_license_no_meta_yaml_not_installed_output_exists(fresh_resource, tmp_path,
                                                                               mocker, caplog):
    mock_workspace = MagicMock(path=tmp_path)
    conda_channel = "test_channel"
    conda_label = "main"
    app_resources = fresh_resource("test_app", conda_channel, conda_label)
    mocker.patch('tethysapp.app_store.resource_helpers.tethys_version', "4.0.0")
    mock_urllib = mocker.patch('tethysapp.app_store.resource_helpers.urllib')
    mock_shutil = mocker.patch('tethysapp.app_store.resource_helpers.shutil')
    filepath = tmp_path / "apps" / conda_channel / conda_label / "test_app"
    filepath.mkdir(parents=True)

    processed_resources = process_resources([app_resources], mock_workspace, conda_channel, conda_label)[0]

    expected_resource = fresh_resource("test_app", conda_channel, conda_label)
    expected_resource['latestVersion'] = {conda_channel: {conda_label: "1.0*"}}
    expected_resource['filepath'] = {conda_channel: {conda_label: str(filepath)}}

    assert processed_resources == expected_resource
    download_path = tmp_path / "apps" / conda_channel / conda_label / "versionURL"
    mock_urllib.request.urlretrieve.assert_called_with("versionURL", str(download_path))
    mock_shutil.unpack_archive.assert_called_with(str(download_path), str(filepath))
    assert "License field metadata not found. Downloading: versionURL" in caplog.messages
    assert "No yaml file available to retrieve metadata" in caplog.messages


def test_process_resources_no_license_not_installed(fresh_resource, resource, tmp_path, mocker, caplog, test_files_dir):
    mock_workspace = MagicMock(path=tmp_path)
    conda_channel = "test_channel"
    conda_label = "main"
    app_resources = fresh_resource("test_app", conda_channel, conda_label)
    mocker.patch('tethysapp.app_store.resource_helpers.tethys_version', "4.0.0")
    mock_urllib = mocker.patch('tethysapp.app_store.resource_helpers.urllib')
    mock_shutil = mocker.patch('tethysapp.app_store.resource_helpers.shutil')
    filepath = tmp_path / "apps" / conda_channel / conda_label / "test_app"
    filepath.mkdir(parents=True)
    recipes = filepath / "info" / "recipe"
    recipes.mkdir(parents=True)
    test_meta_yaml = test_files_dir / "recipe_meta.yaml"
    recipes_meta_yaml = recipes / "meta.yaml"
    shutil.copyfile(test_meta_yaml, recipes_meta_yaml)

    processed_resources = process_resources([app_resources], mock_workspace, conda_channel, conda_label)[0]

    expected_resource = resource("test_app", conda_channel, conda_label)
    expected_resource['dev_url'] = {conda_channel: {conda_label: ""}}
    expected_resource['latestVersion'] = {conda_channel: {conda_label: "1.0*"}}
    expected_resource['filepath'] = {conda_channel: {conda_label: str(filepath)}}
    del expected_resource['installedVersion']

    assert processed_resources == expected_resource
    download_path = tmp_path / "apps" / conda_channel / conda_label / "versionURL"
    mock_urllib.request.urlretrieve.assert_called_with("versionURL", str(download_path))
    mock_shutil.unpack_archive.assert_called_with(str(download_path), str(filepath))
    assert "License field metadata not found. Downloading: versionURL" in caplog.messages


def test_process_resources_no_license_yaml_exception(fresh_resource, tmp_path, mocker, caplog,
                                                     test_files_dir):
    mock_workspace = MagicMock(path=tmp_path)
    conda_channel = "test_channel"
    conda_label = "main"
    app_resources = fresh_resource("test_app", conda_channel, conda_label)
    mocker.patch('tethysapp.app_store.resource_helpers.tethys_version', "4.0.0")
    mock_urllib = mocker.patch('tethysapp.app_store.resource_helpers.urllib')
    mock_shutil = mocker.patch('tethysapp.app_store.resource_helpers.shutil')
    filepath = tmp_path / "apps" / conda_channel / conda_label / "test_app"
    filepath.mkdir(parents=True)
    recipes = filepath / "info" / "recipe"
    recipes.mkdir(parents=True)
    test_meta_yaml = test_files_dir / "basic_meta.yaml"
    recipes_meta_yaml = recipes / "meta.yaml"
    shutil.copyfile(test_meta_yaml, recipes_meta_yaml)

    processed_resources = process_resources([app_resources], mock_workspace, conda_channel, conda_label)[0]

    expected_resource = fresh_resource("test_app", conda_channel, conda_label)
    expected_resource['latestVersion'] = {conda_channel: {conda_label: "1.0*"}}
    expected_resource['filepath'] = {conda_channel: {conda_label: str(filepath)}}

    assert processed_resources == expected_resource
    download_path = tmp_path / "apps" / conda_channel / conda_label / "versionURL"
    mock_urllib.request.urlretrieve.assert_called_with("versionURL", str(download_path))
    mock_shutil.unpack_archive.assert_called_with(str(download_path), str(filepath))
    assert "License field metadata not found. Downloading: versionURL" in caplog.messages
    assert "Error happened while downloading package for metadata" in caplog.messages


def test_get_resource(resource, tmp_path, mocker):
    conda_channel = "test_channel"
    conda_label = "main"
    app_resource = resource("test_app", conda_channel, conda_label)
    mocker.patch('tethysapp.app_store.resource_helpers.fetch_resources', return_value=[app_resource])

    resource_response = get_resource("test_app", conda_channel, conda_label, tmp_path)

    assert resource_response == app_resource


def test_get_resource_none(tmp_path, mocker):
    conda_channel = "test_channel"
    conda_label = "main"
    mocker.patch('tethysapp.app_store.resource_helpers.fetch_resources', return_value=[])

    resource_response = get_resource("test_app", conda_channel, conda_label, tmp_path)

    assert resource_response is None


def test_check_if_app_installed_installed(mocker):
    conda_run_resp = json.dumps([{"channel": "conda_channel", 'version': '1.0'}])
    mocker.patch('tethysapp.app_store.resource_helpers.conda_run', return_value=[conda_run_resp, "", 0])

    response = check_if_app_installed("test_app")

    expected_response = {
        'isInstalled': True,
        'channel': "conda_channel",
        'version': '1.0'
    }
    assert response == expected_response


def test_check_if_app_installed_not_installed(mocker):
    conda_run_resp = json.dumps([{}])
    mocker.patch('tethysapp.app_store.resource_helpers.conda_run', return_value=[conda_run_resp, "", 10])

    response = check_if_app_installed("test_app")

    expected_response = {
        'isInstalled': False
    }
    assert response == expected_response


def test_add_keys_to_app_metadata():
    conda_channel = "conda_channel"
    conda_label = "conda_label"
    additional_data = {
        "author": "author",
        "description": "description"
    }
    app = {
        "name": "test_app",
        "version": {conda_channel: {conda_label: "1.0"}}
    }
    additional_keys = ["author"]
    new_dict = add_keys_to_app_metadata(additional_data, app, additional_keys, conda_channel, conda_label)

    expected_new_dict = {
        "name": "test_app",
        "version": {conda_channel: {conda_label: "1.0"}},
        "author": {conda_channel: {conda_label: "author"}}
    }
    assert new_dict == expected_new_dict


def test_add_keys_to_app_metadata_no_additional_data():
    conda_channel = "conda_channel"
    conda_label = "conda_label"
    additional_data = {}
    app = {
        "name": "test_app",
        "version": {conda_channel: {conda_label: "1.0"}}
    }
    additional_keys = ["author"]
    new_dict = add_keys_to_app_metadata(additional_data, app, additional_keys, conda_channel, conda_label)

    expected_new_dict = {
        "name": "test_app",
        "version": {conda_channel: {conda_label: "1.0"}}
    }
    assert new_dict == expected_new_dict


def test_get_app_instance_from_path(mocker, tmp_path, tethysapp):
    app_name = "test_app"
    mock_module = MagicMock(test_app=tethysapp)
    sys.modules[f'tethysapp.{app_name}.app'] = mock_module
    mocker.patch('tethysapp.app_store.resource_helpers.pkgutil.iter_modules', return_value=[["", app_name, True]])
    mocker.patch('tethysapp.app_store.resource_helpers.inspect.getmembers', return_value=[["test_app", tethysapp]])

    get_app_instance_from_path(tmp_path)
    app_instance = get_app_instance_from_path(tmp_path)

    assert app_instance.init_ran


def test_get_app_instance_from_path_typeerror(mocker, tmp_path, tethysapp):
    app_name = "test_app"
    mock_module = MagicMock()
    mock_module.test_app = "Not a Class"
    sys.modules[f'tethysapp.{app_name}.app'] = mock_module
    mocker.patch('tethysapp.app_store.resource_helpers.pkgutil.iter_modules', return_value=[["", app_name, True]])
    mocker.patch('tethysapp.app_store.resource_helpers.inspect.getmembers', return_value=[["test_app", tethysapp]])

    app_instance = get_app_instance_from_path(tmp_path)

    assert app_instance is None
