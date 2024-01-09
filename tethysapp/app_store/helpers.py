import logging
import os
import re

from django.conf import settings
from django.core.cache import cache

from asgiref.sync import async_to_sync
from string import Template
from subprocess import run
from .utilities import decrypt
from .app import AppStore as app

logger = logging.getLogger('tethys.apps.app_store')
# Ensure that this logger is putting everything out.
# @TODO: Change this back to the default later
logger.setLevel(logging.INFO)

CACHE_KEY = "warehouse_github_app_resources"


def get_override_key():
    try:
        return settings.GITHUB_OVERRIDE_VALUE
    except AttributeError:
        # Setting not defined.
        return None


def check_all_present(string, substrings):
    """Checks to see if all substrings are contained within a string

    Args:
        string (str): The string to check
        substrings (list): List of strings that should be within the main string

    Returns:
        bool: True if all substrings are in the string. False if any substrings are not in the string
    """
    result = True
    for substring in substrings:
        if substring not in string:
            result = False
            break
    return result


def run_process(args):
    """Run a subprocess with the given arguments and log any errors

    Args:
        args (list): List of arguemtns to use for the subprocess
    """
    result = run(args, capture_output=True)
    logger.info(result.stdout)
    if result.returncode != 0:
        logger.error(result.stderr)


def send_notification(msg, channel_layer):
    """Send a message using the django channel layers. Handles the async and sync functionalities and compatibilities

    Args:
        msg (str): Message to send to the django channel layer
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    async_to_sync(channel_layer.group_send)(
        "notifications", {
            "type": "install_notifications",
            "message": msg
        }
    )


def apply_template(template_location, data, output_location):
    """Apply data to a template file and save it in the designated location

    Args:
        template_location (str): path to the template that will be used
        data (dict): Dictionary containing information on what keys to look for and what to replace it with
        output_location (str): path to newly created file with the applied data
    """
    with open(template_location) as filein:
        src = Template(filein.read())
        result = src.substitute(data)

    with open(output_location, "w") as f:
        f.write(result)


def parse_setup_py(file_location):
    """Parses a setup.py file to get the app metadata

    Args:
        file_location (str): Path to the setup.py file to parse

    Returns:
        dict: A dictionary of key value pairs of application metadata
    """
    params = {}
    found_setup = False
    with open(file_location, "r") as f:
        for line in f.readlines():
            if ("setup(" in line):
                found_setup = True
                continue
            if found_setup:
                if (")" in line):
                    found_setup = False
                    break
                else:
                    parts = line.split("=")
                    if len(parts) < 2:
                        continue
                    value = parts[1].strip()
                    if (value[-1] == ","):
                        value = value[:-1]
                    if (value[0] == "'" or value[0] == '"'):
                        value = value[1:]
                    if (value[-1] == "'" or value[-1] == '"'):
                        value = value[:-1]
                    params[parts[0].strip()] = value
    return params


def find_string_in_line(line):
    # try singleQuotes First
    matches = re.findall("'([^']*)'", line)
    if len(matches) > 0:
        return matches[0]
    else:
        # try double quotes
        matches = re.findall('"([^"]*)"', line)
        if len(matches) > 0:
            return matches[0]


def get_github_install_metadata(app_workspace):

    if (cache.get(CACHE_KEY) is None):
        logger.info("GitHub Apps list cache miss")
        workspace_directory = app_workspace.path
        workspace_apps_path = os.path.join(
            workspace_directory, 'apps', 'installed')
        if (not os.path.exists(workspace_apps_path)):
            cache.set(CACHE_KEY, [])
            return []

        possible_apps = [f.path for f in os.scandir(
            workspace_apps_path) if f.is_dir()]
        github_installed_apps_list = []
        for possible_app in possible_apps:
            installed_app = {
                'name': '',
                'installed': True,
                'metadata':
                {
                    'channel': 'tethysapp',
                    'license': 'BSD 3-Clause License',
                },
                'installedVersion': '',
                'path': possible_app
            }
            setup_path = os.path.join(possible_app, 'setup.py')
            with open(setup_path, 'rt') as myfile:
                for myline in myfile:
                    if 'app_package' in myline and 'find_resource_files' not in myline and 'release_package' not in myline: # noqa e501
                        installed_app["name"] = find_string_in_line(myline)
                        continue
                    if 'version' in myline:
                        installed_app["installedVersion"] = find_string_in_line(
                            myline)
                        continue
                    if 'description' in myline:
                        installed_app["metadata"]["description"] = find_string_in_line(
                            myline)
                        continue
                    if 'author' in myline:
                        installed_app["author"] = find_string_in_line(myline)
                        continue
                    if 'description' in myline:
                        installed_app["installedVersion"] = find_string_in_line(
                            myline)
                        continue
                    if 'url' in myline:
                        installed_app["dev_url"] = find_string_in_line(
                            myline)
                        continue
            github_installed_apps_list.append(installed_app)
        cache.set(CACHE_KEY, github_installed_apps_list)
        return github_installed_apps_list
    else:
        return cache.get(CACHE_KEY)


def check_github_install(app_name, app_workspace):
    possible_apps = get_github_install_metadata(app_workspace)
    print(possible_apps)


def get_github_installed_apps():

    # print(possible_apps)

    return ""


def get_conda_stores(active_only=False, channel_names="all"):
    available_stores = app.get_custom_setting("stores_settings")['stores']
    encryption_key = app.get_custom_setting("encryption_key")

    if active_only:
        available_stores = [store for store in available_stores if store['active']]

    if channel_names != "all":
        if isinstance(channel_names, str):
            channel_names = channel_names.split(",")
        available_stores = [store for store in available_stores if store['conda_channel'] in channel_names]

    for store in available_stores:
        store['github_token'] = decrypt(store['github_token'], encryption_key)

    return available_stores
