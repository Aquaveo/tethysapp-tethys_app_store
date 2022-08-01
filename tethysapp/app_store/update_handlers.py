import subprocess
import os
import time
import copy

from tethys_apps.utilities import get_app_settings
from tethys_cli.cli_helpers import load_apps


from .helpers import logger, send_notification, check_all_present
from .app import AppStore as app
from .resource_helpers import get_resource
from .installation_handlers import restart_server


def send_update_msg(msg, channel_layer):
    data_json = {
        "target": 'update-notices',
        "message": msg
    }
    send_notification(data_json, channel_layer)


def conda_update(app_name, app_version, app_channel, channel_layer):

    start_time = time.time()
    start_msg = ("Updating the Conda environment may take a "
                 "couple minutes to complete depending on how "
                 "complicated the environment is. Please wait...."
                 )

    send_update_msg(start_msg, channel_layer)

    dir_path = os.path.dirname(os.path.realpath(__file__))
    script_path = os.path.join(dir_path, "scripts", "conda_install.sh")

    app_name_with_version = app_name + "=" + app_version
    install_command = [script_path, app_name_with_version, app_channel]

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
            if(check_all_present(str_output, ['Collecting package metadata', 'done'])):
                send_update_msg("Package Metadata Collection: Done", channel_layer)
            if(check_all_present(str_output, ['Solving environment', 'done'])):
                send_update_msg("Solving Environment: Done", channel_layer)
            if(check_all_present(str_output, ['Verifying transaction', 'done'])):
                send_update_msg("Verifying Transaction: Done", channel_layer)
            if(check_all_present(str_output, ['All requested packages already installed.'])):
                send_update_msg("Application package is already installed in this conda environment.",
                                channel_layer)
            if(check_all_present(str_output, ['Conda Install Complete'])):
                break
            if(check_all_present(str_output, ['Found conflicts!'])):
                send_update_msg("Conda install found conflicts."
                                "Please try running the following command in your terminal's"
                                "conda environment to attempt a manual installation : "
                                "conda install -c " + app_metadata['metadata']['channel'] + " " + app_name,
                                channel_layer)

    send_update_msg("Conda update completed in %.2f seconds." % (time.time() - start_time), channel_layer)


def update_app(data, channel_layer, app_workspace):
    resource = get_resource(data["name"], app_workspace)

    # Commenting out back up settings code for now, since only updating the conda package seems to preserve the original settings
    # app_settings = get_app_settings(data["name"])

    # if app_settings is None:
    #     logger.info("No App settings to preserve for " + data["name"])
    # else:
    #     # Only preserve linked settings
    #     app_settings_backup = copy.deepcopy(app_settings['linked_settings'])

    try:
        conda_update(data["name"], data["version"], resource["metadata"]["channel"], channel_layer)
    except Exception as e:
        logger.error("Error while running conda install during the update process")
        logger.error(e)
        send_update_msg("Error while Installing Conda package. Please check logs for details", channel_layer)
        return

    # Since all settings are preserved, continue to standard cleanup/restart command

    restart_server({"restart_type": "update", "name": data["name"]}, None)
