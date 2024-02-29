import os
import subprocess
import time
from .helpers import logger, send_notification, check_all_present


def mamba_uninstall(app_name, channel_layer):
    """Run a conda uninstall

    Args:
        app_name (dict): Name of the app to uninstall
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    # Running the conda install as a subprocess to get more visibility into the running process
    dir_path = os.path.dirname(os.path.realpath(__file__))
    script_path = os.path.join(dir_path, "scripts", "mamba_uninstall.sh")

    uninstall_command = [script_path, app_name]

    # Running this sub process, in case the library isn't installed, triggers a restart.
    p = subprocess.Popen(
        uninstall_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    while True:
        output = p.stdout.readline()
        if output == "":
            break
        if output:
            # Checkpoints for the output
            str_output = str(output.strip())
            logger.info(str_output)
            if check_all_present(str_output, ["Running Mamba remove"]):
                send_uninstall_messages("Running uninstall script", channel_layer)
            if check_all_present(str_output, ["Transaction starting"]):
                send_uninstall_messages("Starting mamba uninstall", channel_layer)
            if check_all_present(str_output, ["Transaction finished"]):
                send_uninstall_messages("Mamba uninstall complete", channel_layer)
            if check_all_present(str_output, ["Mamba Remove Complete"]):
                break

    return


def send_uninstall_messages(msg, channel_layer):
    """Send a message to the django channel about the uninstall status

    Args:
        msg (str): Message to send to the django channel
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    data_json = {"target": "uninstallNotices", "message": msg}
    send_notification(data_json, channel_layer)


def mamba_download(app_metadata, app_channel, app_label, app_version, channel_layer):
    """Run a conda install with a application using the anaconda package

    Args:
        app_metadata (dict): Dictionary representing an app and its conda metadata
        app_channel (str): Conda channel to use for the app install
        app_label (str): Conda label to use for the app install
        app_version (str): App version to use for app install
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    start_time = time.time()
    send_notification(
        "Mamba install may take a couple minutes to complete depending on how complicated the "
        "environment is. Please wait....",
        channel_layer,
    )

    latest_version = app_metadata["latestVersion"][app_channel][app_label]
    if not app_version:
        app_version = latest_version

    # Running the conda install as a subprocess to get more visibility into the running process
    dir_path = os.path.dirname(os.path.realpath(__file__))
    script_path = os.path.join(dir_path, "scripts", "mamba_download.sh")

    app_name = app_metadata["name"] + "=" + app_version

    label_channel = f"{app_channel}"

    if app_label != "main":
        label_channel = f"{app_channel}/label/{app_label}"

    install_command = [script_path, app_name, label_channel]

    # Running this sub process, in case the library isn't installed, triggers a restart.
    p = subprocess.Popen(
        install_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    success = True
    while True:
        output = p.stdout.readline()
        if output == "":
            break
        if output:
            # Checkpoints for the output
            str_output = str(output.strip())
            logger.info(str_output)
            if check_all_present(
                str_output, ["All requested packages already installed"]
            ):
                send_notification(
                    "Application is already installed in this conda environment.",
                    channel_layer,
                )
                success = False
            if check_all_present(str_output, ["Mamba Download Complete"]):
                break

    send_notification(
        "Mamba download completed in %.2f seconds." % (time.time() - start_time),
        channel_layer,
    )

    return success


def mamba_install(app_metadata, app_channel, app_label, app_version, channel_layer):
    """Run a conda install with a application using the anaconda package

    Args:
        app_metadata (dict): Dictionary representing an app and its conda metadata
        app_channel (str): Conda channel to use for the app install
        app_label (str): Conda label to use for the app install
        app_version (str): App version to use for app install
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    start_time = time.time()
    send_notification(
        "Mamba install may take a couple minutes to complete depending on how complicated the "
        "environment is. Please wait....",
        channel_layer,
    )

    latest_version = app_metadata["latestVersion"][app_channel][app_label]
    if not app_version:
        app_version = latest_version

    # Running the conda install as a subprocess to get more visibility into the running process
    dir_path = os.path.dirname(os.path.realpath(__file__))
    script_path = os.path.join(dir_path, "scripts", "mamba_install.sh")

    app_name = app_metadata["name"] + "=" + app_version

    label_channel = f"{app_channel}"

    if app_label != "main":
        label_channel = f"{app_channel}/label/{app_label}"

    install_command = [script_path, app_name, label_channel]

    # Running this sub process, in case the library isn't installed, triggers a restart.
    p = subprocess.Popen(
        install_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    success = True
    while True:
        output = p.stdout.readline()
        if output == "":
            break
        if output:
            # Checkpoints for the output
            str_output = str(output.strip())
            logger.info(str_output)
            if check_all_present(str_output, ["Collecting package metadata", "done"]):
                send_notification("Package Metadata Collection: Done", channel_layer)
            if check_all_present(str_output, ["Solving environment", "done"]):
                send_notification("Solving Environment: Done", channel_layer)
            if check_all_present(str_output, ["Verifying transaction", "done"]):
                send_notification("Verifying Transaction: Done", channel_layer)
            if check_all_present(
                str_output, ["All requested packages already installed."]
            ):
                send_notification(
                    "Application package is already installed in this conda environment.",
                    channel_layer,
                )
            if check_all_present(
                str_output,
                ["libmamba Could not solve for environment specs", "critical"],
            ):
                success = False
                send_notification(
                    "Failed to resolve environment specs when installing.",
                    channel_layer,
                )
            if check_all_present(str_output, ["Found conflicts!"]):
                success = False
                send_notification(
                    "Mamba install found conflicts. "
                    "Please try running the following command in your terminal's "
                    "conda environment to attempt a manual installation : "
                    f"mamba install -c {label_channel} {app_name}",
                    channel_layer,
                )
            if check_all_present(str_output, ["Mamba failed. Trying conda now."]):
                success = False
                send_notification(
                    "Install failed using mamba. Trying now with conda.", channel_layer
                )
            if check_all_present(str_output, ["Conda Install Success"]):
                success = True
                send_notification("Install succeeded with conda.", channel_layer)
            if check_all_present(str_output, ["Install Complete"]):
                break

    send_notification(
        "Mamba install completed in %.2f seconds." % (time.time() - start_time),
        channel_layer,
    )

    return success
