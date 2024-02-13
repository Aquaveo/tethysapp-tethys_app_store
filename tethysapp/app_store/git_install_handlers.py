import os
import git
import threading
import time
import stat
import logging
import uuid
import json

from tethys_cli.install_commands import open_file, validate_schema
from tethys_sdk.routing import controller
from tethys_sdk.workspaces import get_app_workspace
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.exceptions import ValidationError
from tethys_sdk.permissions import has_permission

from django.http import JsonResponse, Http404, HttpResponse

from django.core.cache import cache
from pathlib import Path
from subprocess import Popen, PIPE, STDOUT
from datetime import datetime

from conda.cli.python_api import run_command as conda_run, Commands
from .app import AppStore as app
from .helpers import get_override_key, logger, restart_server, clear_github_cache_list

FNULL = open(os.devnull, 'w')

git_install_logger = logging.getLogger("warehouse_git_install_logger")
git_install_logger.setLevel(logging.DEBUG)
logger_formatter = logging.Formatter('%(asctime)s : %(message)s')


def run_pending_installs():
    """On server reboots, check for pending installs based on the status file and continue with installation if any
    exist
    """
    time.sleep(10)
    logger.info("Checking for Pending Installs")

    app_workspace = get_app_workspace(app)
    workspace_directory = app_workspace.path

    install_status_dir = os.path.join(
        workspace_directory, 'install_status', 'github')
    if not os.path.exists(install_status_dir):
        return
    # Check each file for any that are still not completed or errored out
    for file_name in os.listdir(install_status_dir):
        if file_name.endswith(".json"):
            file_path = os.path.join(install_status_dir, file_name)
            with open(os.path.join(install_status_dir, file_name), "r") as json_file:
                data = json.load(json_file)
                # Check if setupPy is running and continue the install for that
                if data["status"]["setupPy"] == "Running":
                    logger.info("Continuing Install for " + data["installID"])
                    # Create logging handler
                    workspace_directory = app_workspace.path
                    logfile_location = get_log_file(data["installID"], workspace_directory)
                    fh = logging.FileHandler(logfile_location)
                    fh.setFormatter(logger_formatter)
                    fh.setLevel(logging.DEBUG)
                    git_install_logger.addHandler(fh)

                    install_yml_path = Path(os.path.join(
                        data["workspacePath"], 'install.yml'))
                    install_options = open_file(install_yml_path)
                    if "name" in install_options:
                        app_name = install_options['name']

                    continue_install(data["workspacePath"], git_install_logger, file_path, install_options, app_name,
                                     app_workspace)


def update_status_file(path, status, status_key, error_msg=""):
    """Updates a status file for the git install

    Args:
        path (str): Path to the git install status file
        status (str): Status of the install step. i.e. Pending, Running, False, or True
        status_key (str): Install step. i.e. conda, pip, setupPy, dbSync, and post
        error_msg (str, optional): Error message to add to the file. Defaults to "".
    """
    with open(path, "r") as json_file:
        data = json.load(json_file)

    data["status"][status_key] = status

    # Check if all status is set to true
    if all(value is True for value in data["status"].values()):
        # Install is completed
        data["installCompletedTime"] = datetime.now().strftime(
            '%Y-%m-%dT%H:%M:%S.%f')
        data["installComplete"] = True

    if error_msg != "":
        data["errorDateTime"] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
        data["errorMessage"] = error_msg
    else:
        data["lastUpdate"] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')

    with open(path, "w") as json_file:
        json.dump(data, json_file)


def install_packages(conda_config, logger, status_file_path):
    """Install conda packages using the conda CLI

    Args:
        conda_config (dict): Dictionary containing conda information and key/value pairs for channels and packages
        logger (Logger): Logger for the git install
        status_file_path (str): Path to the file tracking the app installation process
    """
    install_args = []
    if validate_schema('channels', conda_config):
        channels = conda_config['channels']
        channels = [channels] if isinstance(channels, str) else channels
        for channel in channels:
            install_args.extend(['-c', channel])

    if validate_schema('packages', conda_config):
        install_args.extend(['--freeze-installed'])
        install_args.extend(conda_config['packages'])
        logger.info("Running conda installation tasks...")
        [resp, err, code] = conda_run(Commands.INSTALL, *install_args, use_exception_handler=False)
        if code != 0:
            error_msg = 'Warning: Packages installation ran into an error. Please try again or a manual install'
            logger.error(error_msg)
            update_status_file(status_file_path, False, "conda", error_msg)
        else:
            update_status_file(status_file_path, True, "conda")
            logger.info(resp)


def write_logs(logger, output, subHeading):
    """Iterates through a standard output and logs the information for each line with a specified prefix

    Args:
        logger (Logger): Logger for the git install
        output (IO BufferedReader): Standard output for a subprocess or other function
        subHeading (str): Prefix string for the standard output before logging
    """
    with output:
        for line in iter(output.readline, b''):
            cleaned_line = line.decode("utf-8").replace("\n", "")
            logger.info(subHeading + cleaned_line)


def continue_install(workspace_apps_path, logger, status_file_path, install_options, app_name, app_workspace):
    """Continues the application install by running a database sync command and any post scripts

    Args:
        workspace_apps_path (str): Path to the application being installed from the app store workspace
        logger (Logger): Logger for the git install
        status_file_path (str): Path to the file tracking the app installation process
        install_options (dict): Dictionary containing the information for the application install
        app_name (str): Name of the application that is being installed
        app_workspace (TethysWorkspace): workspace object bound to the app workspace.
    """
    process = Popen(['tethys', 'db', 'sync'], stdout=PIPE, stderr=STDOUT)
    write_logs(logger, process.stdout, 'Tethys DB Sync : ')
    exitcode = process.wait()
    if exitcode == 0:
        update_status_file(status_file_path, True, "dbSync")
    else:
        update_status_file(status_file_path, False, "dbSync", "Error while running DBSync. Please check logs")

    # Check to see if any extra scripts need to be run
    if validate_schema('post', install_options):
        logger.info("Running post installation tasks...")
        post_scripts = install_options["post"]
        post_scripts = [post_scripts] if isinstance(post_scripts, str) else post_scripts
        for post in post_scripts:
            path_to_post = os.path.join(workspace_apps_path, post)
            # Update permissions so the script can be run
            st = os.stat(path_to_post)
            os.chmod(path_to_post, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

            process = Popen(str(path_to_post), shell=True, stdout=PIPE)
            stdout = process.communicate()[0]
            logger.info(f"Post Script Result: {stdout}")

    update_status_file(status_file_path, True, "post")
    update_status_file(status_file_path, True, "setupPy")
    logger.info("Install completed")
    clear_github_cache_list()
    restart_server({"restart_type": "github_install", "name": app_name}, channel_layer=None,
                   app_workspace=app_workspace)


def install_worker(workspace_apps_path, status_file_path, logger, develop, app_workspace):
    """A worker function that installs application dependencies and the application itself from the app store workspace

    Args:
        workspace_apps_path (str): Path to the application being installed from the app store workspace
        status_file_path (str): Path to the file tracking the app installation process
        logger (Logger): Logger for the git install
        develop (boolean): True if running installing in dev mode. False if installing in production mode
        app_workspace (TethysWorkspace): workspace object bound to the app workspace.
    """
    logger.info("Installing dependencies...")
    file_path = Path(os.path.join(workspace_apps_path, 'install.yml'))
    install_options = open_file(file_path)

    if "name" in install_options:
        app_name = install_options['name']

    if validate_schema('requirements', install_options):
        requirements_config = install_options['requirements']
        skip = False
        if "skip" in requirements_config:
            skip = requirements_config['skip']

        if skip:
            logger.info("Skipping package installation, Skip option found.")
        else:
            if validate_schema('conda', requirements_config):  # noqa: E501
                conda_config = requirements_config['conda']
                install_packages(conda_config, logger, status_file_path)
            if validate_schema('pip', requirements_config):
                logger.info("Running pip installation tasks...")
                process = Popen(
                    ['pip', 'install', *requirements_config["pip"]], stdout=PIPE, stderr=STDOUT)
                write_logs(logger, process.stdout, 'PIP Install: ')
                exitcode = process.wait()
                logger.info(f"PIP Install exited with: {str(exitcode)}")

    update_status_file(status_file_path, True, "conda")
    update_status_file(status_file_path, True, "pip")
    update_status_file(status_file_path, "Running", "setupPy")

    # Run Setup.py
    logger.info("Running application install....")
    command = "develop" if develop else "install"
    process = Popen(['python', 'setup.py', command],
                    cwd=workspace_apps_path, stdout=PIPE, stderr=STDOUT)
    write_logs(logger, process.stdout, 'Python Install SubProcess: ')
    exitcode = process.wait()
    logger.info("Python Application install exited with: " + str(exitcode))

    # This step might cause a server restart and will not have the rest of the code execute.
    continue_install(workspace_apps_path, logger, status_file_path, install_options, app_name, app_workspace)


def get_log_file(install_id, workspace_directory):
    """Get the log file for a specific installation ID

    Args:
        install_id (str): ID of the app installation process
        workspace_directory (str): Path pointing to the app workspace within the app store

    Returns:
        _type_: _description_
    """
    log_file = os.path.join(workspace_directory, 'logs', 'github_install', f'{install_id}.log')

    return log_file


def get_status_file(install_id, workspace_directory):
    """Get the log file for a specific installation ID

    Args:
        install_id (str): ID of the app installation process
        workspace_directory (str): Path pointing to the app workspace within the app store

    Returns:
        _type_: _description_
    """
    status_file = os.path.join(workspace_directory, 'install_status', 'github', f'{install_id}.json')

    return status_file


def get_status_main(request, app_workspace):
    """Get the status of the given install according to the ID

    Args:
        request (Django Request): Django request object containing information about the user and user request
        app_workspace (TethysWorkspace): workspace object bound to the app workspace.

    Raises:
        ValidationError: install_id is not passed to the request or is None
        Http404: install_id does not exist

    Returns:
        JsonResponse: Json containing the install status of the given ID
    """
    install_id = request.GET.get('install_id')
    if install_id is None:
        raise ValidationError({"install_id": "Missing Value"})

    # Find the file in the
    status_file_path = get_status_file(install_id, app_workspace.path)
    if os.path.exists(status_file_path):
        with open(status_file_path, "r") as jsonFile:
            data = json.load(jsonFile)
        return JsonResponse(data)
    else:
        raise Http404(f"No Install with id {install_id} exists")


def get_logs_main(request, app_workspace):
    """Get the logs for the given install according to the ID

    Args:
        request (Django Request): Django request object containing information about the user and user request
        app_workspace (TethysWorkspace): workspace object bound to the app workspace.

    Raises:
        ValidationError: install_id is not passed to the request or is None
        Http404: install_id does not exist

    Returns:
        HttpResponse: HttpResponse containing the install logs for the given ID
    """
    install_id = request.GET.get('install_id')
    if install_id is None:
        raise ValidationError({"install_id": "Missing Value"})

    # Find the file in the
    file_path = get_log_file(install_id, app_workspace.path)
    if os.path.exists(file_path):
        with open(file_path, "r") as logFile:
            return HttpResponse(logFile, content_type='text/plain')
    else:
        raise Http404(f"No Install with id {install_id} exists")


@controller(
    name='git_get_status',
    url='app-store/install/git/status',
    app_workspace=True,
    login_required=False
)
@api_view(['GET'])
@authentication_classes((TokenAuthentication,))
def get_status(request, app_workspace):
    """Get the status of the given install according to the ID

    Args:
        request (Django Request): Django request object containing information about the user and user request
        app_workspace (TethysWorkspace): workspace object bound to the app workspace.

    Returns:
        Web Resonse/Exception: Output of get_status_main
    """
    if not has_permission(request, 'use_app_store'):
        return JsonResponse({'message': 'Missing required permissions'}, status=401)

    # This method is a wrapper function to protect the actual method from being accessed without auth
    return get_status_main(request, app_workspace)


@controller(
    name='git_get_status_override',
    url='app-store/install/git/status_override',
    login_required=False
)
@api_view(['GET'])
def get_status_override(request):
    """This method is an override to the get status method. It allows for installation based on a custom key set in the
    custom settings. This allows app store to process the request without a user token

    Args:
        request (Django Request): Django request object containing information about the user and user request

    Returns:
        Web Resonse/Exception: Output of get_status_main if no auth errors
    """
    override_key = get_override_key()
    if not override_key:
        return JsonResponse({'message': 'API not usable. No override key has been set'}, status=500)

    if (request.GET.get('custom_key') == override_key):
        app_workspace = get_app_workspace(app)
        return get_status_main(request, app_workspace)
    else:
        return JsonResponse({'message': 'Invalid override key provided'}, status=401)


@controller(
    name='git_get_logs',
    url='app-store/install/git/logs',
    app_workspace=True,
    login_required=False
)
@api_view(['GET'])
@authentication_classes((TokenAuthentication,))
def get_logs(request, app_workspace):
    """Get the log of the given install according to the ID

    Args:
        request (Django Request): Django request object containing information about the user and user request
        app_workspace (TethysWorkspace): workspace object bound to the app workspace.

    Returns:
        Web Resonse/Exception: Output of get_logs_main
    """
    if not has_permission(request, 'use_app_store'):
        return JsonResponse({'message': 'Missing required permissions'}, status=401)

    return get_logs_main(request, app_workspace)


@controller(
    name='git_get_logs_override',
    url='app-store/install/git/logs_override',
    login_required=False
)
@api_view(['GET'])
def get_logs_override(request):
    """This method is an override to the get logs method. It allows for installation based on a custom key set in the
    custom settings. This allows app store to process the request without a user token

    Args:
        request (Django Request): Django request object containing information about the user and user request

    Returns:
        Web Resonse/Exception: Output of get_status_main if no auth errors
    """
    override_key = get_override_key()
    if not override_key:
        return JsonResponse({'message': 'API not usable. No override key has been set'}, status=500)

    if (request.GET.get('custom_key') == override_key):
        app_workspace = get_app_workspace(app)
        return get_logs_main(request, app_workspace)
    else:
        return JsonResponse({'message': 'Invalid override key provided'}, status=401)


@controller(
    name='install_git',
    url='app-store/install/git',
    app_workspace=True,
    login_required=False
)
@api_view(['POST'])
@authentication_classes((TokenAuthentication,))
def run_git_install_main(request, app_workspace):
    """POST API call to install an application from a github url. If app already exists, do a git pull and continue
    install

    Args:
        request (Django Request): Django request object containing information about the user and user request
        app_workspace (TethysWorkspace): workspace object bound to the app workspace.

    Input JSON Object:

    {
                url: "https://github.com/app_url",
                branch: "master",
                develop: "true|false"
    }

    Returns:
        _type_: _description_
    """
    if not has_permission(request, 'use_app_store'):
        return JsonResponse({'message': 'Missing required permissions'}, status=401)

    workspace_directory = app_workspace.path
    install_logs_dir = os.path.join(
        workspace_directory, 'logs', 'github_install')
    install_status_dir = os.path.join(
        workspace_directory, 'install_status', 'github')

    if not os.path.exists(install_status_dir):
        os.makedirs(install_status_dir)

    Path(os.path.join(workspace_directory, 'install_status', 'installRunning')).touch()

    received_json_data = json.loads(request.body)
    develop = True if received_json_data.get('develop', True) is True else False

    repo_url = received_json_data.get('url', request.POST.get('url', ''))
    branch = received_json_data.get('branch', request.POST.get('branch', 'master'))

    url_end = repo_url.split("/")[-1].replace(".git", "")

    if not os.path.exists(install_logs_dir):
        os.makedirs(install_logs_dir)

    install_run_id = str(uuid.uuid4())

    logfile_location = get_log_file(install_run_id, workspace_directory)
    fh = logging.FileHandler(logfile_location)
    fh.setFormatter(logger_formatter)
    fh.setLevel(logging.DEBUG)

    # TODO: Validation on the GitHUB URL
    workspace_apps_path = os.path.join(
        workspace_directory, 'apps', 'github_installed', url_end)

    statusfile_location = get_status_file(install_run_id, workspace_directory)
    statusfile_data = {
        'installID': install_run_id,
        'githubURL': repo_url,
        'workspacePath': workspace_apps_path,
        'installComplete': False,
        'status': {
            "installStarted": True,
            "conda": "Pending",
            "pip": "Pending",
            "setupPy": "Pending",
            "dbSync": "Pending",
            "post": "Pending"
        },
        'installStartTime': datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
    }
    with open(statusfile_location, 'w') as outfile:
        json.dump(statusfile_data, outfile)

    git_install_logger.addHandler(fh)
    git_install_logger.info("Starting GitHub Install. Installation ID: " + install_run_id)
    git_install_logger.info("Input URL: " + repo_url)
    git_install_logger.info("Assumed App Name: " + url_end)
    git_install_logger.info("Application Install Path: " + workspace_apps_path)

    if not os.path.exists(workspace_apps_path):
        git_install_logger.info("App folder Directory does not exist. Creating one.")
        os.makedirs(workspace_apps_path)

        repo = git.Repo.init(workspace_apps_path)
        origin = repo.create_remote('origin', repo_url)
        origin.fetch()

        try:
            repo.git.checkout(branch, "-f")
        except Exception as e:
            git_install_logger.info(str(e))
            git_install_logger.info(f"Couldn't check out {branch} branch. Attempting to checkout main")
            repo.git.checkout("main", "-f")
    else:
        git_install_logger.info("Git Repo exists locally. Doing a pull to get the latest")
        g = git.cmd.Git(workspace_apps_path)
        g.pull()

    install_thread = threading.Thread(target=install_worker, name="InstallApps",
                                      args=(workspace_apps_path, statusfile_location, git_install_logger,
                                            develop, app_workspace))
    install_thread.start()

    return JsonResponse({'status': "InstallRunning", 'install_id': install_run_id}, status=200)


@controller(
    name='install_git_override',
    url='app-store/install/git_override',
    login_required=False
)
@api_view(['POST'])
def run_git_install_override(request):
    override_key = get_override_key()
    if not override_key:
        return JsonResponse({'message': 'API not usable. No override key has been set'}, status=500)

    received_json_data = json.loads(request.body)
    if (received_json_data.get('custom_key') == override_key):
        app_workspace = get_app_workspace(app)
        return run_git_install_main(request, app_workspace)
    else:
        return JsonResponse({'message': 'Invalid override key provided'}, status=401)


def resume_pending_installs():
    resume_thread = threading.Thread(
        target=run_pending_installs, name="ResumeGitInstalls")
    resume_thread.setDaemon(True)
    resume_thread.start()


resume_pending_installs()
