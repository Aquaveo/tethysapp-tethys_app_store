import os
import importlib
import subprocess
import tethysapp
import site
import yaml

from django.core.cache import cache

from subprocess import call

from .helpers import check_all_present, logger, send_notification
from .resource_helpers import get_resource, get_app_instance_from_path
from .proxy_app_handlers import create_proxy_app, list_proxy_apps
from .mamba_helpers import mamba_download, mamba_install
from tethys_apps.base.workspace import TethysWorkspace


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


def detect_app_dependencies(
    app_name, channel_layer, notification_method=send_notification
):
    """Check the application for pip (via a pip_install.sh) and custom setting dependencies

    Args:
        app_name (str): Name of the application being installed
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
        notification_method (Object, optional): Method of how to send notifications. Defaults to send_notification
            which is a WebSocket.
    """

    logger.info("Running a DB sync")
    call(["tethys", "db", "sync"])
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
    app_scripts_path = os.path.join(installed_app_path, app_folders[0], "scripts")
    pip_install_script_path = os.path.join(app_scripts_path, "install_pip.sh")

    if os.path.exists(pip_install_script_path):
        logger.info("PIP dependencies found. Running Pip install script")

        notification_method("Running PIP install....", channel_layer)
        process = subprocess.Popen(
            ["sh", pip_install_script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        while True:
            output = process.stdout.readline()
            if output == "":
                break
            if output:
                str_output = str(output.strip())
                logger.info(str_output)
                if check_all_present(str_output, ["PIP Install Complete"]):
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
            default = setting.default
            if isinstance(default, TethysWorkspace):
                default = default.path

            setting = {
                "name": setting.name,
                "description": setting.description,
                "required": setting.required,
                "default": str(default),
            }
            custom_settings_json.append(setting)

    get_data_json = {
        "data": custom_settings_json,
        "returnMethod": "set_custom_settings",
        "jsHelperFunction": "processCustomSettings",
        "app_py_path": str(installed_app_path),
    }
    notification_method(get_data_json, channel_layer)

    return


def begin_install(installData, channel_layer, app_workspace):
    """Using the install data, this function will retrieve a specific app resource and install the application as well
    as update any app dependencies

    Args:
        installData (dict): User provided information about the application that should be installed
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
        app_workspace (TethysWorkspace): workspace object bound to the app workspace.
    """
    resource = get_resource(
        installData["name"], installData["channel"], installData["label"], app_workspace
    )
    if not resource:
        send_notification(
            f"Failed to get the {installData['name']} resource", channel_layer
        )
        return

    send_notification(
        f"Starting installation of app: {resource['name']} from store {installData['channel']} "
        f"with label {installData['label']}",
        channel_layer,
    )
    send_notification(f"Installing Version: {installData['version']}", channel_layer)

    try:
        if resource["app_type"] == "proxyapp":
            proxy_apps = list_proxy_apps()
            installed_app = [
                app
                for app in proxy_apps
                if app["name"] == resource["name"].replace("proxyapp_", "")
            ]
            if installed_app:
                message = "Proxy App is already installed with this name"
                send_notification(message, channel_layer)
                raise Exception(message)

            successful_install = mamba_download(
                resource,
                installData["channel"],
                installData["label"],
                installData["version"],
                channel_layer,
            )

            site_packages = os.path.join(
                os.path.dirname(subprocess.__file__), "site-packages"
            )
            proxy_package = [
                package
                for package in os.listdir(site_packages)
                if resource["name"] in package
            ][0]
            proxyapp_yaml = os.path.join(
                site_packages, proxy_package, "config", "proxyapp.yaml"
            )
            with open(proxyapp_yaml) as f:
                proxy_app_data = yaml.safe_load(f)

            create_proxy_app(proxy_app_data, channel_layer)

            get_data_json = {
                "data": {
                    "app_name": resource["name"],
                    "message": f"Proxy app {resource['name']} added",
                },
                "jsHelperFunction": "proxyAppInstallComplete",
                "helper": "addModalHelper",
            }
            send_notification(get_data_json, channel_layer)
        else:
            successful_install = mamba_install(
                resource,
                installData["channel"],
                installData["label"],
                installData["version"],
                channel_layer,
            )
            if not successful_install:
                raise Exception("Mamba install script failed to install application.")
            detect_app_dependencies(resource["name"], channel_layer)
    except Exception as e:
        logger.error(e)
        send_notification(
            "Application installation failed. Check logs for more details.",
            channel_layer,
        )
        return
