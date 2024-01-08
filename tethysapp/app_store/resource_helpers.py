from django.core.cache import cache

import ast
import re
import semver
from tethys_portal import __version__ as tethys_version
import copy

import os
import json
import urllib
import shutil
from pkg_resources import parse_version
import yaml
from .helpers import check_if_app_installed, add_if_exists_keys, logger, get_conda_stores
from conda.cli.python_api import run_command as conda_run, Commands


def clear_conda_channel_cache():
    """Clears Django cache for all the conda stores
    """
    available_stores_data_dict = get_conda_stores()
    for store in available_stores_data_dict:
        store_name = store['conda_channel']
        for conda_label in store['conda_labels']:
            cache_key = f'{store_name}_{conda_label}_app_resources'
            cache.delete(cache_key)


def create_pre_multiple_stores_labels_obj(app_workspace, refresh=False, conda_channels='all'):
    """Creates a dictionary of resources based on conda channels and conda labels

    Args:
        app_workspace (str): Path pointing to the app workspace within the app store
        refresh (bool, optional): Indicates whether resources should be refreshed or use a cache. Defaults to False.
        conda_channels (str/list, optional): Name of the conda channel to use for app discovery. Defaults to 'all'.

    Returns:
        dict: A reformatted app resource dictionary based solely on the conda channel See the example below.

        {
            'conda_channel1': {
                'conda_label1': {
                    'availableApps': {'app1_name': <app1_metadata_dict>},
                    'installedApps': {'app1_name': <app1_metadata_dict>},
                    'incompatibleApps': {}
                },
                'conda_label2': {
                    'availableApps': {'app2_name': <app2_metadata_dict>},
                    'installedApps': {},
                    'incompatibleApps': {'app3_name': <app3_metadata_dict>}
                }
            }
        }
    """
    available_stores_data_dict = get_conda_stores(channel_names=conda_channels)
    object_stores = {}
    for store in available_stores_data_dict:
        conda_channel = store['conda_channel']
        object_stores[conda_channel] = {}
        for conda_label in store['conda_labels']:
            cache_key = f'{conda_channel}_{conda_label}_app_resources'
            object_stores[conda_channel][conda_label] = get_resources_single_store(app_workspace, refresh,
                                                                                   conda_channel, conda_label,
                                                                                   cache_key=cache_key)

    return object_stores


def get_new_stores_reformated_by_labels(object_stores):
    """Merge all app resources in a given conda channel into channel based dictionaries of availableApps, installedApps,
    and incompatibleApps.

    Args:
        object_stores (dict): A dictionary of app resources based on conda channel and then conda label

    Returns:
        dict: A reformatted app resource dictionary based solely on the conda channel See the example below.

        {
            'conda_channel1': {
                'availableApps': {'app1_name': <app1_metadata_dict>, 'app2_name': <app2_metadata_dict>},
                'installedApps': {'app1_name': <app1_metadata_dict>},
                'incompatibleApps': {'app3_name': <app3_metadata_dict>}
            },
            'conda_channel2': {
                'availableApps': {'app4_name': <app1_metadata_dict>,
                'installedApps': {},
                'incompatibleApps': {'app5_name': <app3_metadata_dict>}
            }
        }
    """
    new_store_reformatted = {}
    for conda_channel in object_stores:
        new_store_reformatted[conda_channel] = {}
        list_labels_store = list(object_stores[conda_channel].keys())
        list_type_apps = list(object_stores[conda_channel][list_labels_store[0]].keys())
        for type_app in list_type_apps:
            if type_app != 'tethysVersion':
                new_store_reformatted[conda_channel][type_app] = merge_labels_single_store(
                    object_stores[conda_channel], conda_channel, type_app)

    return new_store_reformatted


def get_stores_reformatted(app_workspace, refresh=False, conda_channels='all'):
    """Retrieve a dictionary of app resources and metadata from the conda channels. Reformat the dictionary to
        provide a list of available apps, installed apps, and incompatible apps

    Args:
        app_workspace (str): Path pointing to the app workspace within the app store
        refresh (bool, optional): Indicates whether resources should be refreshed or use a cache. Defaults to False.
        conda_channels (str/list, optional): Name of the conda channel to use for app discovery. Defaults to 'all'.

    Returns:
        dict: list of available apps, installed apps, and incompatible apps across all specified channels
    """
    object_stores_raw = create_pre_multiple_stores_labels_obj(app_workspace, refresh, conda_channels)
    object_stores_formatted_by_label = get_new_stores_reformated_by_labels(object_stores_raw)
    object_stores_formatted_by_channel = get_stores_reformated_by_channel(object_stores_formatted_by_label)

    list_stores_formatted_by_channel = {
        'availableApps': [metadata for _, metadata in object_stores_formatted_by_channel['availableApps'].items()],
        'installedApps': [metadata for _, metadata in object_stores_formatted_by_channel['installedApps'].items()],
        'incompatibleApps': [metadata for _, metadata in object_stores_formatted_by_channel['incompatibleApps'].items()]
    }
    return list_stores_formatted_by_channel


def get_stores_reformated_by_channel(stores):
    """Reformats a dictionary of conda channel based resources into a status based dictionary

    Args:
        stores (dict): Dictionary of apps based on conda channels

    Returns:
        dict: Dictionary of apps based on status, i.e. availableApps, installedApps, and incompatibleApps. See the
        example below.

        {
            'availableApps': {'app1_name': <app1_metadata_dict>, 'app2_name': <app2_metadata_dict>},
            'installedApps': {'app1_name': <app1_metadata_dict>},
            'incompatibleApps': {'app3_name': <app3_metadata_dict>}
        }
    """
    app_channel_obj = get_app_channel_for_stores(stores)
    merged_channels_app = merge_channels_of_apps(app_channel_obj, stores)
    return merged_channels_app


def merge_channels_of_apps(app_channel_obj, stores):
    """Merge resource information for apps that have the same name across conda channels

    Args:
        app_channel_obj (dict): Dictionary with information about apps and in what conda channels they can be found.
            See get_app_channel_for_stores return information
        stores (dict): Dictionary of app information based on conda channels

    Returns:
        dict: Dictionary of merged apps across multiple channels based on status, i.e. availableApps, installedApps, and
        incompatibleApps. See the example below.

        {
            'availableApps': {'app1_name': <app1_metadata_dict>, 'app2_name': <app2_metadata_dict>},
            'installedApps': {'app1_name': <app1_metadata_dict>},
            'incompatibleApps': {'app3_name': <app3_metadata_dict>}
        }

        app1_metadata_dict would contain information about the app across multiple channels. See the example resource
        metadata below.

        {
            'name': 'app_name,
            'installed': {'conda_channel1_name': {'main': False}, 'conda_channel2_name': {'dev': False}},
            'installedVersion': {'conda_channel1_name': {'main': "1.0"}, 'conda_channel2_name': {'dev': "1.0"}},
            'latestVersion': {'conda_channel1_name': {'main': "1.0"}, 'conda_channel2_name': {'dev': "1.0"}},
            'versions': {'conda_channel1_name': {'main': []}, 'conda_channel2_name': {'dev': []}},
            'versionURLs': {'conda_channel1_name': {'main': []}, 'conda_channel2_name': {'dev': []}},
            'channels_and_labels': {'conda_channel1_name': {'main': []}, 'conda_channel2_name': {'dev': []}},
            'timestamp': {'conda_channel1_name': {'main': "timestamp"}, 'conda_channel2_name': {'dev': "timestamp"}},
            'compatibility': {'conda_channel1_name': {'main': {}}, 'conda_channel2_name': {'dev': {}}},
            'license': {'conda_channel1_name': {'main': None}, 'conda_channel2_name': {'dev': None}},
            'licenses': {'conda_channel1_name': {'main': []}, 'conda_channel2_name': {'dev': []}},
            'author': {'conda_channel1_name': {'main': 'author'}, 'conda_channel2_name': {'dev': 'author'}},
            'description': {'conda_channel1_name': {'main': 'description'},
                            'conda_channel2_name': {'dev': 'description'}},
            'author_email': {'conda_channel1_name': {'main': 'author_email'},
                            'conda_channel2_name': {'dev': 'author_email'}},
            'keywords': {'conda_channel1_name': {'main': 'keywords'}, 'conda_channel2_name': {'dev': 'keywords'}},
            'dev_url': {'conda_channel1_name': {'main': 'dev_url'}, 'conda_channel2_name': {'dev': 'dev_url'}}
        }
    """
    merged_channels_app = {}
    for channel in stores:
        for type_app in stores[channel]:
            if type_app not in merged_channels_app:
                merged_channels_app[type_app] = {}
            for app in stores[channel][type_app]:
                if app not in merged_channels_app[type_app]:
                    merged_channels_app[type_app][app] = {}
                if app not in app_channel_obj[type_app]:
                    continue
                for key in stores[channel][type_app][app]:
                    if key != 'name':
                        if key not in merged_channels_app[type_app][app]:
                            merged_channels_app[type_app][app][key] = {}
                        if channel in app_channel_obj[type_app][app]:
                            merged_channels_app[type_app][app][key][channel] = stores[channel][type_app][app][key][channel]  # noqa: E501
                    else:
                        merged_channels_app[type_app][app][key] = stores[channel][type_app][app][key]

    return merged_channels_app


def get_app_channel_for_stores(stores):
    """Parses a dictionary of resources based on conda channels and provides a summary of apps shared across channels

    Args:
        stores (dict): Dictionary of apps based on conda channels

    Returns:
        dict: Summary of apps and channels based on status, i.e. availableApps, installedApps, and incompatibleApps.
        See the example below

        {
            'availableApps': {'app1_name': ['conda_channel1', 'conda_channel2'], 'app2_name': ['conda_channel1']},
            'installedApps': {'app1_name': ['conda_channel1']},
            'incompatibleApps': {'app3_name': ['conda_channel1', 'conda_channel2']}
        }
    """
    app_channel_obj = {}
    for channel in stores:
        for type_apps in stores[channel]:
            if type_apps not in app_channel_obj:
                app_channel_obj[type_apps] = {}
            for app in stores[channel][type_apps]:
                if app not in app_channel_obj[type_apps]:
                    app_channel_obj[type_apps][app] = []
                    app_channel_obj[type_apps][app].append(channel)
                else:
                    if channel not in app_channel_obj[type_apps][app]:
                        app_channel_obj[type_apps][app].append(channel)
    return app_channel_obj


def get_app_label_obj_for_store(store, type_apps):
    """Parse the app resources to get a dictionary of all apps and any labels that the app uses

    Args:
        store (dict): Apps that are found from the conda channel
        type_apps (str): availableApps, installedApps, or incompatibleApps

    Returns:
        dict: Dictionary containing all the apps and any labels that the app can be found in. See the example below

        {
            'app_name': ['main'],
            'app2_name': ['main', 'dev']
        }
    """
    apps_label = {}
    labels = list(store.keys())
    for label in labels:
        apps = list(store[label][type_apps].keys())
        for app in apps:
            if app in apps_label:
                apps_label[app].append(label)
            else:
                apps_label[app] = []
                apps_label[app].append(label)

    return apps_label


def merge_labels_for_app_in_store(apps_label, store, conda_channel, type_apps):
    """Merge labels in the app resource metadata

    Args:
        apps_label (dict): Dictionary containing all the apps and any labels that the app can be found in
        store (dict): Apps that are found from the conda channel
        conda_channel (str): Name of the conda channel to use for app discovery
        type_apps (str): availableApps, installedApps, or incompatibleApps

    Returns:
        dict: Merged app resource information for each label in the conda channel
    """
    new_store_label_obj = {}
    for app in apps_label:
        if app not in new_store_label_obj:
            new_store_label_obj[app] = {}
        for label in store:
            if label not in apps_label[app]:
                continue
            for key in store[label][type_apps].get(app, []):
                if key != 'name':
                    if key not in new_store_label_obj[app]:
                        new_store_label_obj[app][key] = {
                            conda_channel: {}
                        }
                    for label_app in store[label][type_apps][app][key][conda_channel]:
                        new_store_label_obj[app][key][conda_channel][label_app] = store[label][type_apps][app][key][conda_channel][label_app]  # noqa: E501
                else:
                    new_store_label_obj[app][key] = store[label][type_apps][app][key]

    return new_store_label_obj


def merge_labels_single_store(store, channel, type_apps):
    """Merges all resources from all the labels for a specific conda channel

    Args:
        store (dict): Apps that are found from the conda channel
        conda_channel (str): Name of the conda channel to use for app discovery
        type_apps (str): availableApps, installedApps, or incompatibleApps

    Returns:
        dict: Merged resource dictionary for all apps within conda channel
    """
    apps_labels = get_app_label_obj_for_store(store, type_apps)
    merged_label_store = merge_labels_for_app_in_store(apps_labels, store, channel, type_apps)

    return merged_label_store


def get_resources_single_store(app_workspace, require_refresh, conda_channel, conda_label, cache_key):
    """Get all the resources for a specific conda channel and conda label. Once resources have been retreived, check
    each resource if it is installed. Once that is checked loop through each version in the metadata. For each version
    we are checking the compatibility map to see if the compatible tethys version will work with this portal setup.

    Args:
        app_workspace (str): Path pointing to the app workspace within the app store
        require_refresh (bool): Indicates whether resources should be refreshed or use a cache
        conda_channel (str): Name of the conda channel to use for app discovery
        conda_label (str): Name of the conda label to use for app discovery
        cache_key (str): Key to be used for caching strategy

    Returns:
        Dict: A dictionary that contains resource info for availableApps, installedApps, incompatibleApps, and
        current tethysVersion
    """
    installed_apps = {}
    available_apps = {}
    incompatible_apps = {}
    all_resources = fetch_resources(app_workspace, require_refresh, conda_channel, conda_label, cache_key)
    tethys_version_regex = re.search(r'([\d.]+[\d])', tethys_version).group(1)
    for resource in all_resources:
        if resource["installed"][conda_channel][conda_label]:
            installed_apps[resource['name']] = resource

        add_compatible = False
        add_incompatible = False
        new_compatible_app = copy.deepcopy(resource)
        new_compatible_app['versions'][conda_channel][conda_label] = []
        new_incompatible_app = copy.deepcopy(new_compatible_app)
        for version in resource['versions'][conda_channel][conda_label]:
            # Assume if not found, that it is compatible with Tethys Platform 3.4.4
            compatible_tethys_version = "<=3.4.4"
            if version in resource['compatibility'][conda_channel][conda_label]:
                compatible_tethys_version = resource['compatibility'][conda_channel][conda_label][version]
            if semver.match(tethys_version_regex, compatible_tethys_version):
                add_compatible = True
                new_compatible_app['versions'][conda_channel][conda_label].append(version)
            else:
                add_incompatible = True
                new_incompatible_app['versions'][conda_channel][conda_label].append(version)

        if add_compatible:
            available_apps[resource['name']] = new_compatible_app
        if add_incompatible:
            incompatible_apps[resource['name']] = new_incompatible_app

    return_object = {
        'availableApps': available_apps,
        'installedApps': installed_apps,
        'incompatibleApps': incompatible_apps,
        'tethysVersion': tethys_version_regex,
    }

    return return_object


def fetch_resources(app_workspace, refresh=False, conda_package="tethysapp", conda_label="main", cache_key=None):
    """_summary_

    Args:
        app_workspace (_type_): _description_
        refresh (bool, optional): _description_. Defaults to False.
        conda_package (str, optional): _description_. Defaults to "tethysapp".
        conda_label (str, optional): _description_. Defaults to "main".
        cache_key (_type_, optional): _description_. Defaults to None.

    Raises:
        Exception: _description_

    Returns:
        _type_: _description_
    """
    CHANNEL_NAME = conda_package

    if conda_label != 'main':
        CHANNEL_NAME = f'{conda_package}/label/{conda_label}'

    CACHE_KEY = cache_key
    refresh = True

    if (cache.get(CACHE_KEY) is None) or refresh:

        # Look for packages:
        logger.info("Refreshing list of apps cache")

        [resp, err, code] = conda_run(Commands.SEARCH, ["-c", CHANNEL_NAME, "--override-channels", "-i", "--json"])

        if code != 0:
            # In here maybe we just try re running the install
            raise Exception(f"ERROR: Couldn't search packages in the {CHANNEL_NAME} channel")

        conda_search_result = json.loads(resp)

        resource_metadata = []
        logger.info("Total Apps Found:" + str(len(conda_search_result)))
        if 'error' in conda_search_result and 'The following packages are not available from current channels' in conda_search_result['error']:  # noqa: E501
            logger.info(f'no packages found with the label {conda_label} in channel {CHANNEL_NAME}')
            return resource_metadata

        for app_package in conda_search_result:

            installed_version = check_if_app_installed(app_package)

            newPackage = {
                'name': app_package,
                'installed': {
                    conda_package: {
                        conda_label: False
                    }
                },
                'versions': {
                    conda_package: {
                        conda_label: []
                    }
                },
                'versionURLs': {
                    conda_package: {
                        conda_label: []
                    }
                },
                'channels_and_labels': {
                    conda_package: {
                        conda_label: []
                    }
                },
                'timestamp': {
                    conda_package: {
                        conda_label: conda_search_result[app_package][-1]["timestamp"]
                    }
                },
                'compatibility': {
                    conda_package: {
                        conda_label: {}
                    }
                },
                'license': {
                    conda_package: {
                        conda_label: None
                    }
                },
                'licenses': {
                    conda_package: {
                        conda_label: []
                    }
                }
            }

            if "license" in conda_search_result[app_package][-1]:
                newPackage["license"][conda_package][conda_label] = conda_search_result[app_package][-1]["license"]

            if installed_version['isInstalled']:
                if CHANNEL_NAME == installed_version['channel']:
                    newPackage["installed"][conda_package][conda_label] = True
                    newPackage["installedVersion"] = {
                        conda_package: {}
                    }
                    newPackage["installedVersion"][conda_package][conda_label] = installed_version['version']
            for conda_version in conda_search_result[app_package]:
                newPackage["versions"][conda_package][conda_label].append(conda_version.get('version'))
                newPackage["versionURLs"][conda_package][conda_label].append(conda_version.get('url'))
                newPackage["licenses"][conda_package][conda_label].append(conda_version.get('license'))

                if "license" in conda_version:
                    try:
                        license_json = json.loads(conda_version['license'].replace("', '", '", "')
                                                  .replace("': '", '": "').replace("'}", '"}').replace("{'", '{"'))
                        if 'tethys_version' in license_json:
                            newPackage["compatibility"][conda_package][conda_label][conda_version['version']] = license_json.get('tethys_version')  # noqa: E501
                    except (ValueError, TypeError):
                        pass

            resource_metadata.append(newPackage)

        resource_metadata = process_resources(resource_metadata, app_workspace, conda_package, conda_label)

        cache.set(CACHE_KEY, resource_metadata)
        return resource_metadata
    else:
        logger.info("Found in cache")
        return cache.get(CACHE_KEY)


def process_resources(resources, app_workspace, conda_channel, conda_label):
    for app in resources:
        workspace_folder = os.path.join(app_workspace.path, 'apps')
        if not os.path.exists(workspace_folder):
            os.makedirs(workspace_folder)

        tethys_version_regex = re.search(r'([\d.]+[\d])', tethys_version).group(1)
        # Set Latest Version
        app["latestVersion"] = {
            conda_channel: {}
        }

        app["latestVersion"][conda_channel][conda_label] = app.get("versions").get(conda_channel).get(conda_label)[-1]

        # Check if latest version is compatible. If not, append an asterisk
        license = app.get("license").get(f"{conda_channel}").get(f"{conda_label}")
        comp_dict = None
        compatible = None
        try:
            comp_dict = ast.literal_eval(license)
        except Exception:
            pass
        if comp_dict and 'tethys_version' in comp_dict:
            compatible = comp_dict['tethys_version']

        if compatible is None:
            compatible = "<=3.4.4"

        if not semver.match(tethys_version_regex, compatible):
            app["latestVersion"][conda_channel][conda_label] = app["latestVersion"][conda_channel][conda_label] + "*"

        if (app['installed']):
            if 'installedVersion' in app:
                latestVersion = app["latestVersion"][conda_channel][conda_label]
                installedVersion = app["installedVersion"][conda_channel][conda_label]
                if (latestVersion.find("*") is False):
                    if parse_version(latestVersion) > parse_version(installedVersion):
                        app["updateAvailable"] = {
                            conda_channel: {
                                conda_label: True
                            }
                        }
                else:
                    app["updateAvailable"] = {
                        conda_channel: {
                            conda_label: False
                        }
                    }
            else:
                app["updateAvailable"] = {
                    conda_channel: {
                        conda_label: False
                    }
                }
        latest_version_url = app.get("versionURLs").get(f"{conda_channel}").get(f"{conda_label}")[-1]
        file_name = latest_version_url.split('/')
        folder_name = app.get("name")

        # Check for metadata in the Search Description
        # That path will work for newly submitted apps with warehouse ver>0.25

        try:
            if "license" not in app or app['license'][conda_channel][conda_label] is None:
                raise ValueError
            license_metadata = json.loads(app["license"][conda_channel][conda_label]
                                          .replace("', '", '", "').replace("': '", '": "')
                                          .replace("'}", '"}').replace("{'", '{"'))

            # create new one
            app = add_if_exists_keys(license_metadata, app, [
                'author', 'description', 'license', 'author_email', 'keywords'], conda_channel, conda_label)

            if "url" in license_metadata:
                app['dev_url'] = {
                    conda_channel: {
                        conda_label: ''
                    }
                }
                app['dev_url'][conda_channel][conda_label] = license_metadata["url"]

            else:
                app['dev_url'] = {
                    conda_channel: {
                        conda_label: ''
                    }
                }
                app['dev_url'][conda_channel][conda_label] = ''

        except (ValueError, TypeError):
            # There wasn't json found in license. Get Metadata from downloading the file
            download_path = os.path.join(workspace_folder, conda_channel, conda_label, file_name[-1])
            output_path = os.path.join(workspace_folder, conda_channel, conda_label, folder_name)
            if not os.path.exists(download_path):
                if not os.path.exists(os.path.join(workspace_folder, conda_channel, conda_label)):
                    os.makedirs(os.path.join(workspace_folder, conda_channel, conda_label))

                logger.info("License field metadata not found. Downloading: " + file_name[-1])
                urllib.request.urlretrieve(latest_version_url, download_path)

                if os.path.exists(output_path):
                    # Clear the output extracted folder
                    shutil.rmtree(output_path)

                shutil.unpack_archive(download_path, output_path)

            app["filepath"] = {
                conda_channel: {
                    conda_label: output_path
                }
            }

            # Get Meta.Yaml for this file
            try:
                meta_yaml_path = os.path.join(output_path, 'info', 'recipe', 'meta.yaml')
                if os.path.exists(meta_yaml_path):
                    with open(meta_yaml_path) as f:
                        meta_yaml = yaml.safe_load(f)
                        # Add metadata to the resources object.

                        attr_about = ['author', 'description', 'dev_url', 'license']
                        attr_extra = ['author_email', 'keywords']

                        app = add_if_exists_keys(meta_yaml.get('about'), app, attr_about, conda_channel, conda_label)
                        app = add_if_exists_keys(meta_yaml.get('extra'), app, attr_extra, conda_channel, conda_label)
                        if 'dev_url' not in app:
                            app['dev_url'] = {
                                conda_channel: {
                                    conda_label: ''
                                }
                            }
                            app['dev_url'][conda_channel][conda_label] = ''
            except Exception as e:
                logger.info("Error happened while downloading package for metadata")
                logger.error(e)

    return resources


def get_resource(resource_name, channel, label, app_workspace):
    all_resources = fetch_resources(app_workspace=app_workspace, conda_package=channel, conda_label=label)

    resource = [x for x in all_resources if x['name'] == resource_name]

    if len(resource) > 0:
        return resource[0]
    else:
        return None
