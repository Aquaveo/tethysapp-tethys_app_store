import pytest
import shutil


@pytest.fixture()
def tethysapp_base(tmp_path):
    tethysapp_base_dir = tmp_path / "tethysapp-test_app"
    tethysapp_base_dir.mkdir()

    tethysapp_dir = tethysapp_base_dir / "tethysapp"
    tethysapp_dir.mkdir()

    app_dir = tethysapp_dir / "test_app"
    app_dir.mkdir()

    return tethysapp_base_dir


@pytest.fixture()
def tethysapp_base_with_application_files(tethysapp_base, app_files_dir, test_files_dir):

    conda_recipes_dir = tethysapp_base / "conda.recipes"
    conda_recipes_dir.mkdir()

    meta_template = app_files_dir / "meta_template.yaml"
    tethysapp_meta_template = conda_recipes_dir / "meta.yaml"
    shutil.copy(meta_template, tethysapp_meta_template)

    getChannels = app_files_dir / "getChannels.py"
    tethysapp_getChannels = tethysapp_base / "getChannels.py"
    shutil.copy(getChannels, tethysapp_getChannels)

    setup_helper = app_files_dir / "setup_helper.py"
    tethysapp_setup_helper = tethysapp_base / "setup_helper.py"
    shutil.copy(setup_helper, tethysapp_setup_helper)

    setup_helper = test_files_dir / "setup.py"
    tethysapp_setup_helper = tethysapp_base / "setup.py"
    shutil.copy(setup_helper, tethysapp_setup_helper)

    setup_helper = app_files_dir / "__init__.py"
    tethysapp_setup_helper = tethysapp_base / "__init__.py"
    shutil.copy(setup_helper, tethysapp_setup_helper)

    return tethysapp_base


@pytest.fixture()
def basic_tethysapp(tethysapp_base_with_application_files, test_files_dir):
    test_install_yaml = test_files_dir / "basic_install.yml"
    tethysapp_install_yaml = tethysapp_base_with_application_files / "install.yml"
    shutil.copy(test_install_yaml, tethysapp_install_yaml)

    return tethysapp_base_with_application_files


@pytest.fixture()
def complex_tethysapp(tethysapp_base_with_application_files, test_files_dir):
    test_install_yaml = test_files_dir / "complex_install.yml"
    tethysapp_install_yaml = tethysapp_base_with_application_files / "install.yml"
    shutil.copy(test_install_yaml, tethysapp_install_yaml)

    return tethysapp_base_with_application_files


@pytest.fixture()
def basic_meta_yaml(test_files_dir):
    basic_meta_yaml = test_files_dir / "basic_meta.yaml"

    return basic_meta_yaml


@pytest.fixture()
def complex_meta_yaml(test_files_dir):
    complex_meta_yaml = test_files_dir / "complex_meta.yaml"

    return complex_meta_yaml


@pytest.fixture()
def install_pip_bash(test_files_dir):
    install_pip_bash = test_files_dir / "install_pip.sh"

    return install_pip_bash
