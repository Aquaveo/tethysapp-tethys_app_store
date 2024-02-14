from conda.exceptions import PackagesNotFoundError
from tethys_cli.cli_helpers import get_manage_path
from tethys_apps.exceptions import TethysAppSettingNotAssigned
from tethys_apps.models import TethysApp

import subprocess
import shutil
from .helpers import logger, get_github_install_metadata, clear_github_cache_list
from .mamba_helpers import mamba_uninstall, send_uninstall_messages
from .proxy_app_handlers import delete_proxy_app


def uninstall_app(data, channel_layer, app_workspace):
    """Removed app database connections and uninstall the app. Try to uninstall with mamba first and if that fails,
    assume it is a github app and try to uninstall that.

    Args:
        data (dict): Information about the app that will be uninstalled
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
        app_workspace (TethysWorkspace): workspace object bound to the app workspace.
    """
    manage_path = get_manage_path({})
    app_name = data['name']

    send_uninstall_messages('Starting Uninstall. Please wait...', channel_layer)
    if data['app_type'] == "proxyapp":
        data['app_name'] = data['name'].replace("proxyapp_", "")
        send_uninstall_messages('Uninstalling Proxy App', channel_layer)
        delete_proxy_app(data, channel_layer)
    else:
        try:
            # Check if application had provisioned any Persistent stores and clear them out
            target_app = TethysApp.objects.filter(package=app_name)[0]
            ps_db_settings = target_app.persistent_store_database_settings

            if len(ps_db_settings):
                for setting in ps_db_settings:
                    # If there is a db for this PS, drop it
                    try:
                        if setting.persistent_store_database_exists():
                            logger.info("Dropping Database for persistent store setting: " + str(setting))
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
            logger.info("Couldn't connect to database for removal. Continuing clean up")

        process = ['python', manage_path, 'tethys_app_uninstall', app_name, '-f']

        try:
            subprocess.call(process)
        except KeyboardInterrupt:
            pass

        send_uninstall_messages('Tethys App Uninstalled. Running Conda/GitHub Cleanup...', channel_layer)

    try:
        mamba_uninstall(app_name, channel_layer)
    except PackagesNotFoundError:
        # This was installed using GitHub. Try to clean out
        github_installed = get_github_install_metadata(app_workspace)
        for app in github_installed:
            if app['name'] == app_name:
                # remove App Directory
                shutil.rmtree(app['path'])

        clear_github_cache_list()

    send_uninstall_messages('Uninstall completed. Restarting server...', channel_layer)
