import os
import time
import importlib
import subprocess
import tethysapp
import site

from django.core.cache import cache

from subprocess import call

from .helpers import check_all_present, get_app_instance_from_path, logger, send_notification
from .resource_helpers import get_resource


def handle_property_not_present(prop):
    """Handles any issues if certain properties/metadata are not present

    Args:
        prop (dict): application metadata
    """
    # TODO: Generate an error message that metadata is incorrect for this application
    pass


def process_post_install_scripts(scripts_dir):
    """Process any post installation scripts from the installed application

    Args:
        path (str): Path to the application base directory
    """
    if os.path.exists(scripts_dir):
        # Currently only processing the pip install script, but need to add ability to process post scripts as well
        pass


def detect_app_dependencies(app_name, channel_layer, notification_method=send_notification):
    """Check the application for pip (via a pip_install.sh) and custom setting dependencies

    Args:
        app_name (str): Name of the application being installed
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
        notification_method (Object, optional): Method of how to send notifications. Defaults to send_notification
            which is a WebSocket.
    """

    logger.info("Running a DB sync")
    call(['tethys', 'db', 'sync'])
    cache.clear()

    # After install we need to update the sys.path variable so we can see the new apps that are installed.
    # We need to do a reload here of the sys.path and then reload the tethysapp
    # https://stackoverflow.com/questions/25384922/how-to-refresh-sys-path
    importlib.reload(site)
    importlib.reload(tethysapp)

    installed_app_paths = [path for path in tethysapp.__path__ if app_name in path]

    if len(installed_app_paths) < 1:
        logger.error("Can't find the installed app location.")
        return

    installed_app_path = installed_app_paths[0]
    app_folders = next(os.walk(installed_app_path))[1]
    app_scripts_path = os.path.join(installed_app_path, app_folders[0], 'scripts')
    pip_install_script_path = os.path.join(app_scripts_path, 'install_pip.sh')

    if os.path.exists(pip_install_script_path):
        logger.info("PIP dependencies found. Running Pip install script")

        notification_method("Running PIP install....", channel_layer)
        process = subprocess.Popen(['sh', pip_install_script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while True:
            output = process.stdout.readline()
            if output == '':
                break
            if output:
                str_output = str(output.strip())
                logger.info(str_output)
                if (check_all_present(str_output, ['PIP Install Complete'])):
                    break

        notification_method("PIP install completed", channel_layer)

    # @TODO: Add support for post installation scripts as well.
    process_post_install_scripts(app_scripts_path)

    app_instance = get_app_instance_from_path(installed_app_paths)
    custom_settings_json = []
    custom_settings = app_instance.custom_settings()

    if custom_settings:
        notification_method("Processing App's Custom Settings....", channel_layer)
        for setting in custom_settings:
            setting = {"name": setting.name,
                       "description": setting.description,
                       "default": str(setting.default),
                       }
            custom_settings_json.append(setting)

    get_data_json = {
        "data": custom_settings_json,
        "returnMethod": "set_custom_settings",
        "jsHelperFunction": "processCustomSettings",
        "app_py_path": str(installed_app_path)
    }
    notification_method(get_data_json, channel_layer)

    return


def conda_install(app_metadata, app_channel, app_label, app_version, channel_layer):
    """Run a conda install with a application using the anaconda package

    Args:
        app_metadata (dict): Dictionary representing an app and its conda metadata
        app_channel (str): Conda channel to use for the app install
        app_label (str): Conda label to use for the app install
        app_version (str): App version to use for app install
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    start_time = time.time()
    send_notification("Mamba install may take a couple minutes to complete depending on how complicated the "
                      "environment is. Please wait....", channel_layer)

    latest_version = app_metadata['latestVersion'][app_channel][app_label]
    if not app_version:
        app_version = latest_version

    # Running the conda install as a subprocess to get more visibility into the running process
    dir_path = os.path.dirname(os.path.realpath(__file__))
    script_path = os.path.join(dir_path, "scripts", "conda_install.sh")

    app_name = app_metadata['name'] + "=" + app_version

    label_channel = f'{app_channel}'

    if app_label != 'main':
        label_channel = f'{app_channel}/label/{app_label}'

    install_command = [script_path, app_name, label_channel]

    # Running this sub process, in case the library isn't installed, triggers a restart.
    p = subprocess.Popen(install_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    while True:
        output = p.stdout.readline()
        if output == '':
            break
        if output:
            # Checkpoints for the output
            str_output = str(output.strip())
            logger.info(str_output)
            if (check_all_present(str_output, ['Collecting package metadata', 'done'])):
                send_notification("Package Metadata Collection: Done", channel_layer)
            if (check_all_present(str_output, ['Solving environment', 'done'])):
                send_notification("Solving Environment: Done", channel_layer)
            if (check_all_present(str_output, ['Verifying transaction', 'done'])):
                send_notification("Verifying Transaction: Done", channel_layer)
            if (check_all_present(str_output, ['All requested packages already installed.'])):
                send_notification("Application package is already installed in this conda environment.",
                                  channel_layer)
            if (check_all_present(str_output, ['Mamba Install Complete'])):
                break
            if (check_all_present(str_output, ['Found conflicts!'])):
                send_notification("Mamba install found conflicts."
                                  "Please try running the following command in your terminal's"
                                  "conda environment to attempt a manual installation : "
                                  "mamba install -c " + label_channel + " " + app_name,
                                  channel_layer)

    send_notification("Mamba install completed in %.2f seconds." % (time.time() - start_time), channel_layer)


def begin_install(installData, channel_layer, app_workspace):

    resource = get_resource(installData["name"], installData['channel'], installData['label'], app_workspace)

    send_notification(f"Starting installation of app: {resource['name']} from store {installData['channel']} with label {installData['label']}", channel_layer)  # noqa: E501
    send_notification(f"Installing Version: {installData['version']}", channel_layer)

    try:
        conda_install(resource, installData['channel'], installData['label'], installData["version"], channel_layer)
    except Exception as e:
        logger.error("Error while running conda install")
        logger.error(e)
        send_notification("Error while Installing Conda package. Please check logs for details", channel_layer)
        return

    try:
        detect_app_dependencies(resource['name'], channel_layer)
    except Exception as e:
        logger.error(e)
        send_notification("Error while checking package for services", channel_layer)
        return
