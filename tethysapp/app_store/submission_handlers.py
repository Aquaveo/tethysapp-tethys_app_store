import git
import os
import shutil
import github
import fileinput
import yaml
import stat
import json
import time
import requests
import ast
from requests.exceptions import HTTPError
from github.GithubException import UnknownObjectException

from pathlib import Path

from .helpers import logger, send_notification, apply_template, parse_setup_py

LOCAL_DEBUG_MODE = False
CHANNEL_NAME = 'tethysapp'


def update_anaconda_dependencies(github_dir, recipe_path, source_files_path, keywords=None, email=""):
    """Updates the anaconda package dependencies for the submitted github application. This file will be used in the
    github actions to build the anaconda package for the application.

    Args:
        github_dir (str): The directory path that contains the cloned github repository
        recipe_path (str): The directory path that contains necessary files for building the anaconda package
        source_files_path (str): The directory path that contains additional templates needed for anaconda recipes
        keywords (list, optional): Keywords in the extra section of the anaconda packages meta yaml. Defaults to None.
        email (str, optional): Author email in the extra section of the anaconda packages meta yaml. Defaults to "".
    """
    install_yml = os.path.join(github_dir, 'install.yml')
    app_files_dir = os.path.join(github_dir, 'tethysapp')
    meta_yaml = os.path.join(source_files_path, 'meta_reqs.yaml')
    meta_extras = os.path.join(source_files_path, 'meta_extras.yaml')

    app_folders = next(os.walk(app_files_dir))[1]
    app_scripts_path = os.path.join(app_files_dir, app_folders[0], 'scripts')

    Path(app_scripts_path).mkdir(parents=True, exist_ok=True)

    with open(install_yml) as f:
        install_yml_file = yaml.safe_load(f)

    with open(meta_yaml) as f:
        meta_yaml_file = yaml.safe_load(f)

    with open(meta_extras) as f:
        meta_extras_file = yaml.safe_load(f)

    if not keywords:
        keywords = []

    meta_extras_file['extra']['author_email'] = email
    meta_extras_file['extra']['keywords'] = keywords

    meta_yaml_file['requirements']['run'] = install_yml_file['requirements']['conda']['packages']

    # Dynamically create an bash install script for pip install dependency
    if ("pip" in install_yml_file['requirements']):
        pip_deps = install_yml_file['requirements']["pip"]
        if pip_deps is not None:
            logger.info("Pip dependencies found")
            pre_link = os.path.join(app_scripts_path, "install_pip.sh")
            pip_install_string = "pip install " + " ".join(pip_deps)
            with open(pre_link, "w") as f:
                f.write(pip_install_string)
                f.write('\necho "PIP Install Complete"')
            st = os.stat(pre_link)
            os.chmod(pre_link, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # Add additional package metadata to meta.yml for anaconda packaging
    with open(os.path.join(recipe_path, 'meta.yaml'), 'a') as f:
        yaml.safe_dump(meta_extras_file, f, default_flow_style=False)
        f.write("\n")
        yaml.safe_dump(meta_yaml_file, f, default_flow_style=False)


def get_github_repo(repo_name, organization):
    """Retrieve the github repository. If the repository exists, use the existing repository, otherwise create a new one

    Args:
        repo_name (str): Name of the github repository to check
        organization (github.Github.Organization): github organization that hosts the repositories

    Returns:
        tethysapp_repo (github.Github.Repository): returns a repository object, whether an existing repo or a newly
        created one
    """
    try:
        tethysapp_repo = organization.get_repo(repo_name)
        logger.info(f"{organization.login}/{repo_name} Exists. Will have to delete")
        return tethysapp_repo

    except UnknownObjectException as e:
        logger.info(f"Received a {e.status} error when checking {organization.login}/{repo_name}. Error: {e.message}")
        logger.info(f"Creating a new repository at {organization.login}/{repo_name}")
        tethysapp_repo = organization.create_repo(
            repo_name,
            allow_rebase_merge=True,
            auto_init=False,
            description="For Tethys App Store Purposes",
            has_issues=False,
            has_projects=False,
            has_wiki=False,
            private=False,
        )
        return tethysapp_repo


def initialize_local_repo_for_active_stores(install_data, channel_layer, app_workspace):
    """Loop through all stores and initialize a local github repo for each active store within the app workspace

    Args:
        install_data (dict): Dictionary containing installation information such as the github url and a list of stores
            and associated metadata
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
        app_workspace (str): Path pointing to the app workspace within the app store
    """
    github_url = install_data.get("url")
    stores = install_data.get("stores")
    for store_name in stores:
        if (stores[store_name]['active']):
            initialize_local_repo(github_url, stores[store_name], channel_layer, app_workspace)


def initialize_local_repo(github_url, active_store, channel_layer, app_workspace):
    """Create and initialize a local github repo with a path for a specific conda channel. Once a repo is initialized,
    get a list of branches and send back the information to the application submission modal.

    Args:
        github_url (str): Url for the github repo that will be submitted to the app store
        active_store (str): Name of the store that will be used for creating github files and app submission
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
        app_workspace (str): Path pointing to the app workspace within the app store
    """
    # Create/Refresh github directories within the app workspace for the given channel
    app_name = github_url.split("/")[-1].replace(".git", "")
    github_dir = os.path.join(app_workspace.path, 'gitsubmission', active_store['conda_channel'])
    app_github_dir = os.path.join(github_dir, app_name)

    if not os.path.exists(github_dir):
        os.makedirs(github_dir)

    if os.path.exists(app_github_dir):
        shutil.rmtree(app_github_dir)

    # Initialize the github repo and fetch
    repo = git.Repo.init(app_github_dir)
    origin = repo.create_remote('origin', github_url)
    origin.fetch()

    # Get remote branches and get list of branch names
    branches = [refs.name.replace("origin/", "") for refs in repo.remote().refs]

    # Send notification back to websocket about available branches and other store information
    get_data_json = {
        "data": {
            "branches": branches,
            "github_dir": app_github_dir,
            "conda_channel": active_store['conda_channel'],
            "github_token": active_store['github_token'],
            "conda_labels": active_store['conda_labels'],
            "github_organization": active_store['github_organization']
        },
        "jsHelperFunction": "showBranches",
        "helper": "addModalHelper"
    }
    send_notification(get_data_json, channel_layer)


def apply_setup_template(template_path, setup_path, setup_data):
    # reading from file1 and writing to file2
    # open the file using read only mode
    handle = open(template_path, "r")

    # reading the file and storing the data in content
    content = handle.read()
    # replacing the data using replace()
    for key in setup_data.keys():
        if f'replace_{key}' in content:
            content = content.replace(f'replace_{key}', setup_data[key])
    # content = content.replace("File", "Data")

    # close the file
    handle.close()

    handle = open(setup_path, "w")
    handle.write(content)
    handle.close()


def get_app_name_and_version(user, repo_name, branch):
    github_object_api = github.Github()
    github_submit_repo = github_object_api.get_repo(f'{user}/{repo_name}')
    setup_content_object = github_submit_repo.get_contents('setup.py', ref=branch)
    setup_content = setup_content_object.decoded_content.decode('utf-8')
    app_package_name = ''
    version_setup = ''

    left0 = 'version'
    right0 = 'description'
    susbstring0 = setup_content[setup_content.index(left0) + len(left0):setup_content.index(right0)]
    version_setup = susbstring0.strip().replace("'", "").replace(",", "").split('=')[1]

    left = 'app_package'
    right = 'release_package'
    susbstring = setup_content[setup_content.index(left) + len(left):setup_content.index(right)]
    app_package_name = susbstring.strip().replace("'", "").split('=')[1].strip(' ')

    return app_package_name, version_setup


def validation_is_setup_complete(user, repo_name, branch, json_response):
    github_object_api = github.Github()
    github_submit_repo = github_object_api.get_repo(f'{user}/{repo_name}')
    setup_content_object = github_submit_repo.get_contents('setup.py', ref=branch)
    setup_content = setup_content_object.decoded_content.decode()

    prejson_string = setup_content.split("setup(")[-1].replace("\n", "").replace(",    ", ",").replace("dependencies,)", "dependencies").strip().split(",")  # noqa: E501
    # json_dict = {}
    array_emptyness = []
    string_fields = '<ul>'
    get_data_json = {}

    for line in prejson_string:
        property_name = line.split("=")[0].strip()
        property_value = line.split("=")[1].strip().replace("'", "")
        if property_value == '':
            array_emptyness.append(property_name)
            string_fields += f'<li>{property_name}</li>'
        # json_dict[property_name] = property_value

    string_fields += '</ul>'
    if array_emptyness:
        mssge_string = f'<p>The setup.py of your repository contain the following fields empty: {string_fields}</p>'
        json_response['next_move'] = False
        get_data_json = {
            "data": {
                "mssge_string": mssge_string,
                "metadata": json_response
            },
            "jsHelperFunction": "validationResults",
            "helper": "addModalHelper"
        }

    return get_data_json


def validation_is_a_fork(user, repo_name, json_response):
    get_data_json = {}
    github_object_api = github.Github()
    github_submit_repo = github_object_api.get_repo(f'{user}/{repo_name}')
    if github_submit_repo.fork:
        parent_repo = github_submit_repo.parent.html_url
        mssge_string = f'<p>Your repository is a fork, Please submit a pull request to the original app repository ' \
                       f'<a href="{parent_repo}">Here</a>, and ask the owner to submit the app to the app store ' \
                       'later.</p>'
        json_response['next_move'] = False
        get_data_json = {
            "data": {
                "mssge_string": mssge_string,
                "metadata": json_response
            },
            "jsHelperFunction": "validationResults",
            "helper": "addModalHelper"
        }
        # send_notification(get_data_json, channel_layer)
    return get_data_json


def validation_is_new_app(github_url, app_package_name, json_response):
    get_data_json = {}
    if json_response["latest_github_url"] == github_url.replace(".git", ""):
        mssge_string = "<p>The submitted Github url is an update of an existing application, The app store will " \
                       "proceed to pull the repository</p>"
        json_response['next_move'] = True
        get_data_json = {
            "data": {
                "mssge_string": mssge_string,
                "metadata": json_response
            },
            "jsHelperFunction": "validationResults",
            "helper": "addModalHelper"
        }

    else:
        mssge_string = f'<p>The app_package name <b>{app_package_name}</b> of the submitted <a ' \
                       f'href="{github_url.replace(".git","")}">GitHub url</a> was found at an already submitted ' \
                       'application.</p> <ul><li>If the application is the same, please open a pull ' \
                       'request</li><li>If the application is not the same, please change the name of the ' \
                       'app_package found at the setup.py, app.py and other files</li></ul>'
        json_response['next_move'] = False
        get_data_json = {
            "data": {
                "mssge_string": mssge_string,
                "metadata": json_response
            },
            "jsHelperFunction": "validationResults",
            "helper": "addModalHelper"
        }
    return get_data_json


def validation_is_new_version(conda_search_result_package, version_setup, json_response):
    get_data_json = {}
    json_response["latest_github_url"] = ast.literal_eval(conda_search_result_package[-1]['license'])['dev_url']

    # json_response["github_urls"] = []
    json_response["versions"] = []

    string_versions = '<ul>'
    for conda_version in conda_search_result_package:
        json_response.get("versions").append(conda_version.get('version'))
        # json_response.get("metadata").get("license").get('url').append(conda_version.get('version'))
        # json_response.get("github_urls").append(ast.literal_eval(conda_version.get('license')).get('dev_url'))
        string_versions += f'<li>{conda_version.get("version")}</li>'

    string_versions += '</ul>'
    # CHECK if it is a new version or not
    if version_setup in json_response["versions"]:
        mssge_string = f'<p>The current version of your application is {version_setup}, and it was already ' \
                       f'submitted.</p><p>Current versions of your application are: {string_versions}</p> ' \
                       '<p>Please use a new version in the <b>setup.py</b> and <b>install.yml</b> files</p>'
        json_response['next_move'] = False

        get_data_json = {
            "data": {
                "mssge_string": mssge_string,
                "metadata": json_response
            },
            "jsHelperFunction": "validationResults",
            "helper": "addModalHelper"
        }

    return get_data_json


# some ideas of how to refactor the code here for testing
def generate_label_strings(conda_labels):
    labels_string = ''
    for i in range(len(conda_labels)):
        if i < 1:
            labels_string += conda_labels[i]
        else:
            labels_string += f' --label {conda_labels[i]}'
    return labels_string


def create_tethysapp_warehouse_release(repo, branch):
    if 'tethysapp_warehouse_release' not in repo.heads:
        repo.create_head('tethysapp_warehouse_release')
    else:
        repo.git.checkout('tethysapp_warehouse_release')
        repo.git.merge(branch)


def generate_current_version(setup_py_data):
    current_version = setup_py_data["version"]
    return current_version


def reset_folder(file_path):
    if os.path.exists(file_path):
        shutil.rmtree(file_path)

    os.makedirs(file_path)


def copy_files_for_recipe(source, destination, files_changed):
    if not os.path.exists(destination):
        files_changed = True
        shutil.copyfile(source, destination)
    return files_changed


def create_upload_command(labels_string, source_files_path, recipe_path):
    label = {'label_string': labels_string}
    if os.path.exists(os.path.join(recipe_path, 'upload_command.txt')):
        os.remove(os.path.join(recipe_path, 'upload_command.txt'))

    shutil.copyfile(os.path.join(source_files_path, 'upload_command.txt'),
                    os.path.join(recipe_path, 'upload_command.txt'))

    apply_template(os.path.join(source_files_path, 'upload_command.txt'),
                   label, os.path.join(recipe_path, 'upload_command.txt'))


def drop_keywords(setup_py_data):
    # setup_py_data = parse_setup_py(filename)
    keywords = []
    email = ""
    try:
        keywords = setup_py_data.pop('keywords', None)
        email = setup_py_data["author_email"]

        # Clean up keywords
        keywords = keywords.replace('"', '').replace("'", '')
        if ',' in keywords:
            keywords = keywords.split(',')
        keywords = list(map(lambda x: x.strip(), keywords))

    except Exception as err:
        logger.error("Error ocurred while formatting keywords from setup.py")
        logger.error(err)
    return keywords, email


def create_template_data_for_install(install_data, setup_py_data):
    install_yml = os.path.join(install_data['github_dir'], 'install.yml')
    with open(install_yml) as f:
        install_yml_file = yaml.safe_load(f)
        metadata_dict = {**setup_py_data, "tethys_version": install_yml_file.get('tethys_version', '<=3.4.4'),
                         "dev_url": f'{install_data["dev_url"]}'}

    template_data = {
        'metadataObj': json.dumps(metadata_dict).replace('"', "'")
    }
    return template_data


def fix_setup(filename):
    rel_package = ""
    with fileinput.FileInput(filename, inplace=True) as f:
        for line in f:
            # logger.info(line)

            if "import find_all_resource_files" in line or "import find_resource_files" in line:
                print("from setup_helper import find_all_resource_files", end='\n')

            elif ("setup(" in line):
                print(line, end='')
            elif "namespace =" in line:
                print('', end='\n')
            elif ("app_package = " in line):
                rel_package = line
                print("namespace = 'tethysapp'")
                print(line, end='')

            elif "from tethys_apps.base.app_base import TethysAppBase" in line:
                print('', end='\n')

            elif "TethysAppBase.package_namespace" in line:
                new_replace_line = line.replace("TethysAppBase.package_namespace", "namespace")
                print(new_replace_line, end='\n')

            elif "resource_files = find_resource_files" in line:
                print("resource_files = find_all_resource_files(app_package, namespace)", end='\n')

            elif "resource_files += find_resource_files" in line:
                print('', end='\n')
            else:
                print(line, end='')
    return rel_package


def remove_init_file(install_data):
    init_path = os.path.join(install_data['github_dir'], '__init__.py')

    if os.path.exists(init_path):
        os.remove(init_path)


def apply_main_yml_template(source_files_path, workflows_path, rel_package, install_data):
    source = os.path.join(source_files_path, 'main_template.yaml')
    destination = os.path.join(workflows_path, 'main.yaml')
    app_name = rel_package.replace("app_package", '').replace("=", '').replace("'", "").strip()
    template_data = {
        'subject': "Tethys App Store: Build complete for " + app_name,
        'email': install_data['email'],
        'buildMsg': """
        Your Tethys App has been successfully built and is now available on the Tethys App Store.
        This is an auto-generated email and this email is not monitored for replies.
        Please send any queries to gromero@aquaveo.com
        """
    }
    apply_template(source, template_data, destination)


def get_head_names(repo):
    heads_names_list = []

    for ref in repo.references:
        heads_names_list.append(ref.name)
    return heads_names_list


def create_current_tag_version(current_version, heads_names_list):
    current_tag_name = ''
    today = time.strftime("%Y_%m_%d")
    dev_attempt = 0
    current_tag_name = "v" + str(current_version) + "_" + str(dev_attempt) + "_" + today

    if current_tag_name in heads_names_list:
        dev_attempt += 1

    current_tag_name = "v" + str(current_version) + "_" + str(dev_attempt) + "_" + today
    return current_tag_name


def check_if_organization_in_remote(repo, github_organization, remote_url):

    # if 'tethysapp' in repo.remotes:
    if github_organization in repo.remotes:
        logger.info("Remote already exists")
        tethysapp_remote = repo.remotes[github_organization]
        # tethysapp_remote = repo.remotes.tethysapp
        tethysapp_remote.set_url(remote_url)
    else:
        # tethysapp_remote = repo.create_remote('tethysapp', remote_url)
        tethysapp_remote = repo.create_remote(github_organization, remote_url)
    return tethysapp_remote


def add_and_commit_if_files_changed(repo, files_changed, current_tag_name):
    if files_changed:
        repo.git.add(A=True)
        repo.git.commit(m=f'tag version {current_tag_name}')


def push_to_warehouse_release_remote_branch(repo, tethysapp_remote, current_tag_name, files_changed):
    add_and_commit_if_files_changed(repo, files_changed, current_tag_name)
    tethysapp_remote.push('tethysapp_warehouse_release')


def create_head_current_version(repo, current_tag_name, heads_names_list, tethysapp_remote):
    if current_tag_name not in heads_names_list:
        new_release_branch = repo.create_head(current_tag_name)
        repo.git.checkout(current_tag_name)
        # push the new branch in remote
        tethysapp_remote.push(new_release_branch)
    else:
        repo.git.checkout(current_tag_name)
        # push the new branch in remote
        tethysapp_remote.push(current_tag_name)


def create_tags_for_current_version(repo, current_tag_name, heads_names_list, tethysapp_remote):
    tag_name = current_tag_name + "_release"
    if tag_name not in heads_names_list:

        # Create tag
        new_tag = repo.create_tag(
            tag_name,
            ref=repo.heads["tethysapp_warehouse_release"],
            message=f'This is a tag-object pointing to tethysapp_warehouse_release branch with release version {current_tag_name}',  # noqa: E501
        )
        tethysapp_remote.push(new_tag)

    else:
        repo.git.tag('-d', tag_name)  # remove locally
        tethysapp_remote.push(refspec=(':%s' % (tag_name)))  # remove from remote
        new_tag = repo.create_tag(
            tag_name,
            ref=repo.heads["tethysapp_warehouse_release"],
            message=f'This is a tag-object pointing to tethysapp_warehouse_release branch with release version {current_tag_name}',  # noqa: E501
        )
        tethysapp_remote.push(new_tag)


def get_workflow_job_url(tethysapp_repo, github_organization, key):
    workflowFound = False

    # Sometimes due to weird conda versioning issues the get_workflow_runs is not found
    # In that case return no value for the job_url and handle it in JS
    try:
        while not workflowFound:
            time.sleep(4)
            if tethysapp_repo.get_workflow_runs().totalCount > 0:
                logger.info("Obtained Workflow for Submission. Getting Job URL")

                try:
                    # response = requests.get(tethysapp_repo.get_workflow_runs()[0].jobs_url, auth=('tethysapp', key))
                    response = requests.get(tethysapp_repo.get_workflow_runs()[0].jobs_url,
                                            auth=(github_organization, key))

                    response.raise_for_status()
                    jsonResponse = response.json()
                    workflowFound = jsonResponse["total_count"] > 0

                except HTTPError as http_err:
                    logger.error(f'HTTP error occurred while getting Jobs from GITHUB API: {http_err}')
                except Exception as err:
                    logger.error(f'Other error occurred while getting jobs from GITHUB API: {err}')

            if workflowFound:
                job_url = jsonResponse["jobs"][0]["html_url"]

        logger.info("Obtained Job URL: " + job_url)
    except AttributeError:
        logger.info("Unable to obtain Workflow Run")
        job_url = None

    return job_url


def process_branch(install_data, channel_layer):
    # 1. Get Variables
    github_organization = install_data["github_organization"]
    key = install_data["github_token"]
    g = github.Github(key)
    repo = git.Repo(install_data['github_dir'])
    filename = os.path.join(install_data['github_dir'], 'setup.py')
    conda_labels = install_data["conda_labels"]
    labels_string = generate_label_strings(conda_labels)
    files_changed = False

    # 2. From the origin remote checkout the selected branch and pull
    origin = repo.remote(name='origin')
    repo.git.checkout(install_data['branch'])
    origin.pull()
    setup_py_data = parse_setup_py(filename)
    current_version = generate_current_version(setup_py_data)

    # 3. create head tethysapp_warehouse_release and checkout the head
    create_tethysapp_warehouse_release(repo, install_data['branch'])
    repo.git.checkout('tethysapp_warehouse_release')

    # 4. Delete workflow directory if exits in the repo folder, and create the directory workflow.
    # Add the required files if they don't exist.
    workflows_path = os.path.join(install_data['github_dir'], '.github', 'workflows')
    source_files_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'application_files')
    reset_folder(workflows_path)

    # 5. Delete conda.recipes directory if exits in the repo folder, and create the directory conda.recipes.
    recipe_path = os.path.join(install_data['github_dir'], 'conda.recipes')
    reset_folder(recipe_path)

    # 6. copy the getChannels.py from the source to the destination
    # if does not exits Channels purpose is to have conda build -c conda-forge -c x -c x2 -c x3 --output-folder . .
    source = os.path.join(source_files_path, 'getChannels.py')
    destination = os.path.join(recipe_path, 'getChannels.py')
    files_changed = copy_files_for_recipe(source, destination, files_changed)

    # 7. Create the label string to upload to multiple labels a conda package
    source = os.path.join(source_files_path, 'meta_template.yaml')
    destination = os.path.join(recipe_path, 'meta.yaml')
    create_upload_command(labels_string, source_files_path, recipe_path)

    # 8. Drop keywords from setup.py
    keywords, email = drop_keywords(setup_py_data)

    # 9 get the data from the install.yml and create a metadata dict
    template_data = create_template_data_for_install(install_data, setup_py_data)
    apply_template(source, template_data, destination)
    files_changed = copy_files_for_recipe(source, destination, files_changed)

    # 10. Copy the setup_helper.py
    source = os.path.join(source_files_path, 'setup_helper.py')
    destination = os.path.join(install_data['github_dir'], 'setup_helper.py')
    files_changed = copy_files_for_recipe(source, destination, files_changed)

    # 11. Fix setup.py file to remove dependency on tethys
    rel_package = fix_setup(filename)

    # 12. Update the dependencies of the package
    update_anaconda_dependencies(install_data['github_dir'], recipe_path, source_files_path, keywords, email)

    # 13. apply data to the main.yml for the github action
    apply_main_yml_template(source_files_path, workflows_path, rel_package, install_data)

    # 14. remove __init__.py file if present at top level
    remove_init_file(install_data)

    if LOCAL_DEBUG_MODE:
        logger.info("Completed Local Debug Processing for Git Repo")
        return

    # 15. Check if this repo already exists on our remote:
    repo_name = install_data['github_dir'].split('/')[-1]
    organization = g.get_organization(github_organization)
    tethysapp_repo = get_github_repo(repo_name, organization)

    heads_names_list = get_head_names(repo)
    current_tag_name = create_current_tag_version(current_version, heads_names_list)
    remote_url = tethysapp_repo.git_url.replace("git://", "https://" + key + ":x-oauth-basic@")
    tethysapp_remote = check_if_organization_in_remote(repo, github_organization, remote_url)

    # 16. add, commit, and push to the tethysapp_warehouse_release remote branch
    push_to_warehouse_release_remote_branch(repo, tethysapp_remote, current_tag_name, files_changed)

    # 17 create/ push current tag branch to remote
    create_head_current_version(repo, current_tag_name, heads_names_list, tethysapp_remote)

    # 18. create/push tag for current tag version in remote
    create_tags_for_current_version(repo, current_tag_name, heads_names_list, tethysapp_remote)

    # 19. return workflow job url
    job_url = get_workflow_job_url(tethysapp_repo, github_organization, key)

    get_data_json = {
        "data": {
            "githubURL": tethysapp_repo.git_url.replace("git:", "https:"),
            "job_url": job_url,
            "conda_channel": install_data['conda_channel']
        },
        "jsHelperFunction": "addComplete",
        "helper": "addModalHelper"
    }
    send_notification(get_data_json, channel_layer)
