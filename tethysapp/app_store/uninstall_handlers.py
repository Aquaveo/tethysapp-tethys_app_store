from conda.exceptions import PackagesNotFoundError
from tethys_cli.cli_helpers import get_manage_path
from tethys_apps.exceptions import TethysAppSettingNotAssigned
from tethys_apps.models import TethysApp

import subprocess
import shutil
import os
from .helpers import logger, send_notification, get_github_install_metadata
from .git_install_handlers import clear_github_cache_list


def send_uninstall_messages(msg, channel_layer):
    """Send a message to the django channel about the uninstall status

    Args:
        msg (str): Message to send to the django channel
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    data_json = {
        "target": 'uninstallNotices',
        "message": msg
    }
    send_notification(data_json, channel_layer)


def uninstall_app(data, channel_layer, app_workspace):
    """Removed app database connections and uninstall the app. Try to uninstall with mamba first and if that fails,
    assume it is a github app and try to uninstall that.

    Args:
        data (dict): Information about the app that will be uninstalled
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
        app_workspace (str): Path pointing to the app workspace within the app store
    """
    manage_path = get_manage_path({})
    app_name = data['name']

    send_uninstall_messages(
        'Starting Uninstall. Please wait...', channel_layer)

    try:
        # Check if application had provisioned any Persistent stores and clear them out
        target_app = TethysApp.objects.filter(package=app_name)[0]
        ps_db_settings = target_app.persistent_store_database_settings

        if len(ps_db_settings):
            for setting in ps_db_settings:
                # If there is a db for this PS, drop it
                try:
                    if setting.persistent_store_database_exists():
                        logger.info(
                            "Dropping Database for persistent store setting: " + str(setting))
                        setting.drop_persistent_store_database()
                except TethysAppSettingNotAssigned:
                    pass

        else:
            logger.info("No Persistent store services found for: " + app_name)
    except IndexError:
        # Couldn't find the target application
        logger.info(
            "Couldn't find the target application for removal of databases. Continuing clean up")
    except Exception as e:
        # Something wrong with the persistent store setting
        # Could not connect to the database
        logger.info(e)
        logger.info(
            "Couldn't connect to database for removal. Continuing clean up")

    process = ['python', manage_path, 'tethys_app_uninstall', app_name, '-f']

    try:
        subprocess.call(process)
    except KeyboardInterrupt:
        pass

    send_uninstall_messages(
        'Tethys App Uninstalled. Running Conda/GitHub Cleanup...', channel_layer)

    try:
        # Running the conda install as a subprocess to get more visibility into the running process
        dir_path = os.path.dirname(os.path.realpath(__file__))
        script_path = os.path.join(dir_path, "scripts", "mamba_uninstall.sh")

        uninstall_command = [script_path, app_name]

        # Running this sub process, in case the library isn't installed, triggers a restart.
        p = subprocess.Popen(uninstall_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        should_not_stop = True
        while should_not_stop:
            output = p.stdout.readline()
            if output.decode('utf-8') == 'Mamba Remove Complete\n':
                break
            if output:
                # Checkpoints for the output
                str_output = output.decode('utf-8')

                send_uninstall_messages(str_output, channel_layer)
                logger.info(str_output)

    except PackagesNotFoundError:
        # This was installed using GitHub. Try to clean out
        github_installed = get_github_install_metadata(app_workspace)
        for app in github_installed:
            if app['name'] == app_name:
                # remove App Directory
                shutil.rmtree(app['path'])

        clear_github_cache_list()

    send_uninstall_messages('Uninstall completed. Restarting server...', channel_layer)
