import os
import re
import json
import shutil

from jinja2 import Template
from subprocess import (Popen, PIPE, STDOUT)
from pathlib import Path

from .git_install_handlers import write_logs
from .helpers import logger, restart_server
from tethys_cli.scaffold_commands import APP_PATH, APP_PREFIX, get_random_color, render_path, TEMPLATE_SUFFIX

from rest_framework.decorators import api_view, authentication_classes
from tethys_sdk.permissions import has_permission
from rest_framework.authentication import TokenAuthentication

from django.http import JsonResponse
from tethys_sdk.routing import controller


def install_app(app_path, project_name, app_workspace):
    """Run tethys install and other necessary tethys commands through the restart server command

    Args:
        app_path (str): Path to the scaffolded application
        project_name (str): Name of the project
        app_workspace (TethysWorkspace): workspace object bound to the app workspace.
    """
    logger.info("Running scaffolded application install....")
    process = Popen(['tethys', 'install', "-d", "-q"],
                    cwd=app_path, stdout=PIPE, stderr=STDOUT)
    write_logs(logger, process.stdout, 'Python Install SubProcess: ')
    exitcode = process.wait()
    logger.info("Python Application install exited with: " + str(exitcode))

    restart_data = {"restart_type": "scaffold_install", "name": project_name}
    restart_server(data=restart_data, channel_layer=None, app_workspace=app_workspace)


def get_develop_dir(app_workspace):
    """Create if needed and retrieve the develop directory where the app will be scaffolded

    Args:
        app_workspace (TethysWorkspace): workspace object bound to the app workspace.

    Returns:
        str: Path to the develop directory where the scaffolded app resides
    """
    workspace_directory = app_workspace.path
    dev_dir = os.path.join(workspace_directory, 'develop')
    if not os.path.exists(dev_dir):
        os.mkdir(dev_dir)

    return dev_dir


def proper_name_validator(value, default):
    """Validate proper_name user input.

    Args:
        value (str): User inputted name for the application
        default (str): Pre formatted inputted name for the application

    Returns:
        bool: Is the given input name valid
        str: the app name to use for the application
    """
    # Check for default
    if value == default:
        return True, value

    # Validate and sanitize user input
    proper_name_error_regex = re.compile(r'^[a-zA-Z0-9\s]+$')
    proper_name_warn_regex = re.compile(r'^[a-zA-Z0-9-\s_\"\']+$')

    if not proper_name_error_regex.match(value):
        # If offending characters are dashes, underscores or quotes, replace and notify user
        if proper_name_warn_regex.match(value):
            value = value.replace('_', ' ')
            value = value.replace('-', ' ')
            value = value.replace('"', '')
            value = value.replace("'", "")
        # Otherwise, throw error
        else:
            return False, value
    return True, value


@controller(
    name='scaffold_app',
    url='app-store/scaffold',
    login_required=False,
    app_workspace=True
)
@api_view(['POST'])
@authentication_classes((TokenAuthentication,))
def scaffold_command(request, app_workspace):
    """
    Create a new Tethys app projects in the workspace dir and install the app. After installing, the server will
    restart to get the new app working. User must provide an authenticated token to use

    Args:
        request (Django Request): Django request object containing information about the user and user request
        app_workspace (TethysWorkspace): workspace object bound to the app workspace.

    Input JSON Object:

    {
                name: "newName",
                proper_name: " my First APP",
                description: "Description",
                tags: "",
                author_name: "",
                author_email: "",
                license_name: "",
                overwrite: true/false (defaults to false)
    }

    """
    if not has_permission(request, 'use_app_store'):
        return JsonResponse({'message': 'Missing required permissions'}, status=401)

    # Get template dirs
    logger.debug('APP_PATH: {}'.format(APP_PATH))
    template_name = 'default'
    template_root = os.path.join(APP_PATH, 'default')

    logger.debug('Template root directory: {}'.format(template_root))

    # Validate template
    if not os.path.isdir(template_root):
        return JsonResponse({'status': 'false', 'message': f'Error: "{template_name}" is not a valid template.'},
                            status=500)

    received_json_data = json.loads(request.body)
    project_name = received_json_data.get('name').lower()

    # Check for valid characters name
    project_error_regex = re.compile(r'^[a-zA-Z0-9_]+$')
    project_warning_regex = re.compile(r'^[a-zA-Z0-9_-]+$')

    # Only letters, numbers and underscores allowed in app names
    if not project_error_regex.match(project_name):
        # If the only offending character is a dash, replace dashes with underscores and notify user
        if project_warning_regex.match(project_name):
            project_name = project_name.replace('-', '_')
        # Otherwise, throw error
        else:
            error_msg = f'Error: Invalid characters in project name "{project_name}". Only letters, numbers, and underscores.'  # noqa E501
            return JsonResponse({'status': 'false', 'message': error_msg}, status=400)

    # Project name derivatives
    project_dir = '{0}-{1}'.format(APP_PREFIX, project_name)
    split_project_name = project_name.split('_')
    title_case_project_name = [x.title() for x in split_project_name]
    default_proper_name = ' '.join(title_case_project_name)
    class_name = ''.join(title_case_project_name)
    default_theme_color = get_random_color()

    proper_name = received_json_data.get("proper_name", default_proper_name)

    # Validate Proper Name
    is_name_valid, proper_name = proper_name_validator(proper_name, default_proper_name)
    if not is_name_valid:
        error_msg = 'Error: Proper name can only contain letters and numbers and spaces.'
        return JsonResponse({'status': 'false', 'message': error_msg}, status=400)

    # Build up template context
    context = {
        'project': project_name,
        'project_dir': project_dir,
        'project_url': project_name.replace('_', '-'),
        'class_name': class_name,
        'proper_name': proper_name,
        'description': received_json_data.get("description", ""),
        'color': default_theme_color,
        'tags': received_json_data.get("tags", ''),
        'author': received_json_data.get("author_name", ""),
        'author_email': received_json_data.get("author_email", ""),
        'license_name': received_json_data.get("license_name", "")
    }

    workspace_directory = app_workspace.path
    install_status_dir = os.path.join(workspace_directory, 'install_status')

    if not os.path.exists(install_status_dir):
        os.makedirs(install_status_dir)

    Path(os.path.join(workspace_directory, 'install_status', 'scaffoldRunning')).touch()

    logger.debug('Template context: {}'.format(context))

    # Create root directory
    dev_dir = get_develop_dir(app_workspace)
    project_root = os.path.join(dev_dir, project_dir)
    logger.debug('Project root path: {}'.format(project_root))

    overwrite_if_exists = received_json_data.get("overwrite", False)

    if os.path.isdir(project_root):
        if overwrite_if_exists:
            try:
                shutil.rmtree(project_root)
            except OSError:
                error_msg = (f'Error: Unable to overwrite {project_root}. Please remove the directory and try again.')
                return JsonResponse({'status': 'false', 'message': error_msg}, status=500)
        else:
            error_msg = (f'Error: App directory exists {project_root} and Overwrite was not permitted. '
                         'Please remove the directory and try again.')
            return JsonResponse({'status': 'false', 'message': error_msg}, status=500)

    # Walk the template directory, creating the templates and directories in the new project as we go
    for curr_template_root, _dirs, template_files in os.walk(template_root):
        curr_project_root = curr_template_root.replace(template_root, project_root)
        curr_project_root = render_path(curr_project_root, context)

        # Create Root Directory
        os.makedirs(curr_project_root)

        # Create Files
        for template_file in template_files:
            template_file_path = os.path.join(curr_template_root, template_file)
            project_file = template_file.replace(TEMPLATE_SUFFIX, '')
            project_file_path = os.path.join(curr_project_root, project_file)

            # Load the template
            logger.debug('Loading template: "{}"'.format(template_file_path))

            try:
                with open(template_file_path, 'r') as tfp:
                    template = Template(tfp.read())
            except UnicodeDecodeError:
                with open(template_file_path, 'br') as tfp:
                    with open(project_file_path, 'bw') as pfp:
                        pfp.write(tfp.read())
                continue

            # Render template if loaded
            logger.debug('Rendering template: "{}"'.format(template_file_path))
            if template:
                with open(project_file_path, 'w') as pfp:
                    pfp.write(template.render(context))

    try:
        install_app(project_root, project_name, app_workspace)
        return JsonResponse({'status': 'true', 'message': "App scaffold Succeeded."}, status=200)
    except Exception:
        return JsonResponse({'status': 'false', 'message': "App scaffold failed. Check logs."}, status=500)
