from unittest.mock import call
import json
import pytest
from tethysapp.app_store.resource_helpers import (create_pre_multiple_stores_labels_obj, get_resources_single_store,
                                                  get_new_stores_reformated_by_labels, get_stores_reformated_by_channel,
                                                  get_app_channel_for_stores, merge_channels_of_apps, fetch_resources,
                                                  get_stores_reformatted, clear_conda_channel_cache,
                                                  merge_labels_single_store, get_app_label_obj_for_store,
                                                  merge_labels_for_app_in_store, )


def test_clear_conda_channel_cache(mocker, store):
    store_name = 'active_default'
    conda_labels = ['main', 'dev']
    active_store = store(store_name, conda_labels=conda_labels)
    mocker.patch('tethysapp.app_store.resource_helpers.get_conda_stores', return_value=[active_store])
    mock_cache = mocker.patch('tethysapp.app_store.resource_helpers.cache')

    clear_conda_channel_cache()

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
        'versions': {active_store['conda_channel']: {'main': [], 'dev': []}},
        'versionURLs': {active_store['conda_channel']: {'main': [], 'dev': []}},
        'channels_and_labels': {active_store['conda_channel']: {'main': [], 'dev': []}},
        'timestamp': {active_store['conda_channel']: {'main': "timestamp", 'dev': "timestamp"}},
        'compatibility': {active_store['conda_channel']: {'main': {}, 'dev': {}}},
        'license': {active_store['conda_channel']: {'main': None, 'dev': None}},
        'licenses': {active_store['conda_channel']: {'main': [], 'dev': []}},
        'author': {active_store['conda_channel']: {'main': 'author', 'dev': 'author'}},
        'description': {active_store['conda_channel']: {'main': 'description', 'dev': 'description'}},
        'author_email': {active_store['conda_channel']: {'main': 'author_email', 'dev': 'author_email'}},
        'keywords': {active_store['conda_channel']: {'main': 'keywords', 'dev': 'keywords'}},
        'dev_url': {active_store['conda_channel']: {'main': 'dev_url', 'dev': 'dev_url'}}
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
        'versions': {active_store['conda_channel']: {'main': [], 'dev': []}},
        'versionURLs': {active_store['conda_channel']: {'main': [], 'dev': []}},
        'channels_and_labels': {active_store['conda_channel']: {'main': [], 'dev': []}},
        'timestamp': {active_store['conda_channel']: {'main': "timestamp", 'dev': "timestamp"}},
        'compatibility': {active_store['conda_channel']: {'main': {}, 'dev': {}}},
        'license': {active_store['conda_channel']: {'main': None, 'dev': None}},
        'licenses': {active_store['conda_channel']: {'main': [], 'dev': []}},
        'author': {active_store['conda_channel']: {'main': 'author', 'dev': 'author'}},
        'description': {active_store['conda_channel']: {'main': 'description', 'dev': 'description'}},
        'author_email': {active_store['conda_channel']: {'main': 'author_email', 'dev': 'author_email'}},
        'keywords': {active_store['conda_channel']: {'main': 'keywords', 'dev': 'keywords'}},
        'dev_url': {active_store['conda_channel']: {'main': 'dev_url', 'dev': 'dev_url'}}
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
            "license": None,
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


def test_fetch_resources_no_resources(tmp_path, mocker, resource, caplog):
    conda_search_rep = json.dumps({"error": "The following packages are not available from current channels"})
    mock_conda = mocker.patch('tethysapp.app_store.resource_helpers.conda_run',
                              return_value=[conda_search_rep, None, 0])
    mock_cache = mocker.patch('tethysapp.app_store.resource_helpers.cache')
    mock_cache.get.side_effect = [None]

    fetched_resource = fetch_resources(tmp_path, "test_channel", conda_label="dev")

    mock_conda.assert_called_with("search", ["-c", "test_channel/label/dev", "--override-channels", "-i", "--json"])
    assert 'no packages found with the label dev in channel test_channel/label/dev' in caplog.messages
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
