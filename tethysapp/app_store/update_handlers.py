import subprocess
import os
import time

from .helpers import logger, send_notification, check_all_present
from .installation_handlers import restart_server


def send_update_msg(msg, channel_layer):
    """Send a message to the django channel about the update status

    Args:
        msg (str): Message to send to the django channel
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    data_json = {
        "target": 'update-notices',
        "message": msg
    }
    send_notification(data_json, channel_layer)


def conda_update(app_name, app_version, conda_channel, conda_label, channel_layer):
    """Update the existing conda version to the specified version

    Args:
        app_name (str): Name of the installed app
        app_version (str): Version of the app that will be installed
        conda_channel (str): Name of the conda channel to use for app discovery
        conda_label (str, optional): Name of the conda label to use for app discovery.
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    start_time = time.time()
    start_msg = ("Updating the Conda environment may take a couple minutes to complete depending on how "
                 "complicated the environment is. Please wait....")

    send_update_msg(start_msg, channel_layer)

    dir_path = os.path.dirname(os.path.realpath(__file__))
    script_path = os.path.join(dir_path, "scripts", "mamba_update.sh")

    app_name_with_version = app_name + "=" + app_version
    label_channel = f'{conda_channel}'

    if conda_label != 'main':
        label_channel = f'{conda_channel}/label/{conda_label}'
    install_command = [script_path, app_name_with_version, label_channel]

    # Running this sub process, in case the library isn't installed, triggers a restart.
    p = subprocess.Popen(install_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    while True:
        output = p.stdout.readline()
        if output == '':
            break
        if output:
            str_output = str(output.strip().decode('utf-8'))
            if (check_all_present(str_output, ['Collecting package metadata', 'done'])):
                send_update_msg("Package Metadata Collection: Done", channel_layer)
            if (check_all_present(str_output, ['Solving environment', 'done'])):
                send_update_msg("Solving Environment: Done", channel_layer)
            if (check_all_present(str_output, ['Verifying transaction', 'done'])):
                send_update_msg("Verifying Transaction: Done", channel_layer)
            if (check_all_present(str_output, ['All requested packages already installed.'])):
                send_update_msg("Application package is already installed in this conda environment.",
                                channel_layer)
            if (check_all_present(str_output, ['Mamba Update Complete'])):
                break
            if (check_all_present(str_output, ['Found conflicts!', 'conflicting requests'])):
                send_update_msg("Mamba install found conflicts. Please try running the following command in your "
                                "terminal's conda environment to attempt a manual installation :  mamba install -c "
                                f"{conda_channel} {app_name}",
                                channel_layer)

    send_update_msg("Conda update completed in %.2f seconds." % (time.time() - start_time), channel_layer)


def update_app(data, channel_layer, app_workspace):
    """Attempts to update an application to the specified version. Restarts the server after updating

    Args:
        data (dict): Information about the app that will be updated
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
        app_workspace (str): Path pointing to the app workspace within the app store
    """
    try:
        conda_update(data["name"], data["version"], data["channel"], data["label"], channel_layer)
    except Exception as e:
        logger.error(e)
        send_update_msg("Application update failed. Check logs for more details.", channel_layer)
        return

    # Since all settings are preserved, continue to standard cleanup/restart command
    restart_server(data={"restart_type": "update", "name": data["name"]}, channel_layer=channel_layer,
                   app_workspace=app_workspace)
