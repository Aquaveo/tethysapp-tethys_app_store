import os
import sys
import subprocess

from argparse import Namespace
from django.core.exceptions import ObjectDoesNotExist
from pathlib import Path

from tethys_apps.models import CustomSetting, TethysApp
from tethys_apps.utilities import (get_app_settings, link_service_to_app_setting)
from tethys_cli.cli_helpers import get_manage_path
from tethys_cli.install_commands import (get_service_type_from_setting, get_setting_type_from_setting)
from tethys_cli.services_commands import services_list_command

from .app import AppStore as app
from .begin_install import detect_app_dependencies
from .resource_helpers import get_app_instance_from_path, check_if_app_installed
from .helpers import logger, run_process, send_notification
from .model import *  # noqa: F401, F403


def get_service_options(service_type):
    """Use the service list command line command to get available tethys services for spatial, persistent, wps, or
     datasets

    Args:
        service_type (str): tethys service type. Can be 'spatial', 'persistent', 'wps', or 'dataset'

    Returns:
        list: List of tethys services for the specified service type
    """
    args = Namespace()

    for conf in ['spatial', 'persistent', 'wps', 'dataset']:
        setattr(args, conf, False)

    setattr(args, service_type, True)

    existing_services_list = services_list_command(args)[0]
    existing_services = []

    if (len(existing_services_list)):
        for service in existing_services_list:
            existing_services.append({
                "name": service.name,
                "id": service.id
            })

    return existing_services


def restart_server(data, channel_layer, app_workspace, run_collect_all=True):
    """Runs some tethys commands after an application is installed. Once finished, try to restart the server to get
    the changes made

    Args:
        data (dict): Dictionary of data with app information and restart type
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
        app_workspace (str): Path pointing to the app workspace within the app store
        run_collect_all (bool, optional): Detemines if collect all needs to be ran. Defaults to True.
    """
    # Check if Install Running file is present and delete it
    workspace_directory = app_workspace.path
    install_running_path = os.path.join(workspace_directory, 'install_status', 'installRunning')
    if os.path.exists(install_running_path):
        os.remove(install_running_path)

    # Check if Scaffold Running file is present and delete it
    scaffold_running_path = os.path.join(workspace_directory, 'install_status', 'scaffoldRunning')
    if os.path.exists(scaffold_running_path):
        os.remove(scaffold_running_path)

    manage_path = get_manage_path({})
    if data["restart_type"] in ["install", "update", "github_install"]:
        # Run SyncStores
        logger.info("Running Syncstores for app: " + data["name"])
        send_notification("Running Syncstores for app: " + data["name"], channel_layer)
        intermediate_process = ['python', manage_path, 'syncstores', data["name"], '-f']
        run_process(intermediate_process)

    if 'runserver' in sys.argv:

        logger.info("Dev Mode. Attempting to restart by changing file")
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(dir_path, 'model.py')
        with open(file_path, "w") as f:
            f.write(f'print("{data["name"]} installed in dev mode")')
            f.write("\n")
    else:
        if run_collect_all and data["restart_type"] in ["install", "update", "github_install"]:

            logger.info("Running Tethys Collectall")
            send_notification("Running Tethys Collectall for app: " + data["name"], channel_layer)
            intermediate_process = ['python', manage_path, 'pre_collectstatic']
            run_process(intermediate_process)
            # Setup for main collectstatic
            intermediate_process = ['python', manage_path, 'collectstatic', '--noinput']
            run_process(intermediate_process)
            # Run collectworkspaces command
            intermediate_process = ['python', manage_path, 'collectworkspaces', '--force']
            run_process(intermediate_process)

        try:
            send_notification("Server Restarting . . .", channel_layer)
            command = 'supervisorctl restart all'
            subprocess.run(['sudo', '-h'], check=True)
            sudoPassword = app.get_custom_setting('sudo_server_pass')

            os.system('echo %s|sudo -S %s' % (sudoPassword, command))
        except Exception as e:
            logger.error(e)
            logger.info("No SUDO. Docker container implied. Restarting without SUDO")
            # Error encountered while running sudo. Let's try without sudo
            # Check if the restart dir exists. If yes then use that dir instead of
            RESTART_FILE_PATH = "/var/lib/tethys_persist/restart"

            if os.path.isdir(RESTART_FILE_PATH):
                logger.info("Restart Directory found. Creating restart file.")
                Path(os.path.join(RESTART_FILE_PATH, 'restart')).touch()
            else:
                os.system(command)


def continueAfterInstall(installData, channel_layer):
    """If install is still running, check if the app is installed and check that the correct version is installed

    Args:
        installData (dict): User provided information about the application that should be installed
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    app_data = check_if_app_installed(installData['name'])

    if app_data['isInstalled']:
        if app_data["version"] == installData['version']:
            send_notification("Resuming processing...", channel_layer)
            detect_app_dependencies(installData['name'], channel_layer)
        else:
            send_notification(
                "Server error while processing this installation. Please check your logs", channel_layer)
            logger.error("ERROR: ContinueAfterInstall: Correct version is not installed of this package.")


def set_custom_settings(custom_settings_data, channel_layer):
    """Get custom settings from the the app and set the actual value in tethys using the custom settings data

    Args:
        custom_settings_data (dict): Dictionary containing information about the custom settings of the app
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    current_app = get_app_instance_from_path([custom_settings_data['app_py_path']])

    if custom_settings_data.get("skip"):
        logger.info("Skip/NoneFound option called.")

        msg = "Custom Setting Configuration Skipped"
        if custom_settings_data.get("noneFound"):
            msg = "No Custom Settings Found to process."
        send_notification(msg, channel_layer)
        process_settings(current_app, custom_settings_data['app_py_path'], channel_layer)
        return

    current_app_name = current_app.name
    custom_settings = current_app.custom_settings()

    try:
        current_app_tethysapp_instance = TethysApp.objects.get(name=current_app_name)
    except ObjectDoesNotExist:
        logger.error("Couldn't find app instance to get the ID to connect the settings to")
        send_notification("Error Setting up custom settings. Check logs for more details", channel_layer)
        return

    for setting in custom_settings:
        setting_name = setting.name
        actual_setting = CustomSetting.objects.get(name=setting_name, tethys_app=current_app_tethysapp_instance.id)
        if (setting_name in custom_settings_data['settings']):
            actual_setting.value = custom_settings_data['settings'][setting_name]
            actual_setting.clean()
            actual_setting.save()

    send_notification("Custom Settings configured.", channel_layer)

    send_notification({
        "data": {},
        "jsHelperFunction": "customSettingConfigComplete"
    }, channel_layer)

    process_settings(current_app, custom_settings_data['app_py_path'], channel_layer)


def process_settings(app_instance, app_py_path, channel_layer):
    """Retrieve the app settings and processes unlinked and non custom settings. Also get potential existing service
    options that can be used later for linking

    Args:
        app_instance (TethysAppBase Instance): Tethys app instance for the installed application
        app_py_path (str): Path to the app.py file for the application
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    app_settings = get_app_settings(app_instance.package)

    # In the case the app isn't installed, has no settings, or it is an extension,
    # skip configuring services/settings
    if not app_settings:
        send_notification("No Services found to configure.", channel_layer)
        return
    unlinked_settings = app_settings['unlinked_settings']

    services = []
    for setting in unlinked_settings:
        if "CustomSetting" in setting.__class__.__name__:
            continue
        service_type = get_service_type_from_setting(setting)
        newSetting = {
            "name": setting.name,
            "required": setting.required,
            "description": setting.description,
            "service_type": service_type,
            "setting_type": get_setting_type_from_setting(setting),
            "options": get_service_options(service_type)
        }
        services.append(newSetting)

    get_data_json = {
        "data": services,
        "returnMethod": "configure_services",
        "jsHelperFunction": "processServices",
        "app_py_path": app_py_path,
        "current_app_name": app_instance.package
    }
    send_notification(get_data_json, channel_layer)


def configure_services(services_data, channel_layer):
    """Link applications to the specified services

    Args:
        services_data (dict): Contains information about a service for linking and the application it is for
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    try:
        link_service_to_app_setting(services_data['service_type'],
                                    services_data['service_id'],
                                    services_data['app_name'],
                                    services_data['setting_type'],
                                    services_data['service_name'])
    except Exception as e:
        logger.error(e)
        logger.error("Error while linking service")
        return

    get_data_json = {
        "data": {"serviceName": services_data['service_name']},
        "jsHelperFunction": "serviceConfigComplete"
    }
    send_notification(get_data_json, channel_layer)


def getServiceList(data, channel_layer):
    """_summary_

    Args:
        data (dict): Contains the type of setting to be used to get available services
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    get_data_json = {
        "data": {"settingType": data['settingType'],
                 "newOptions": get_service_options(data['settingType'])},
        "jsHelperFunction": "updateServiceListing"
    }
    send_notification(get_data_json, channel_layer)
