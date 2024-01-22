from unittest.mock import MagicMock
import pytest
from tethysapp.app_store.scaffold_handler import (install_app, get_develop_dir, proper_name_validator)


def test_install_app(mocker, caplog):
    mock_restart = mocker.patch('tethysapp.app_store.scaffold_handler.restart_server')
    mock_Popen = mocker.patch('tethysapp.app_store.scaffold_handler.Popen')
    mock_Popen().wait.side_effect = [0]
    mock_PIPE = mocker.patch('tethysapp.app_store.scaffold_handler.PIPE')
    mock_STDOUT = mocker.patch('tethysapp.app_store.scaffold_handler.STDOUT')
    mocker.patch('tethysapp.app_store.scaffold_handler.write_logs')
    mock_workspace = MagicMock()
    app_path = "app_path"
    project_name = "test_app"

    install_app(app_path, project_name, mock_workspace)

    mock_Popen.assert_called_with(['tethys', 'install', "-d", "-q"], cwd=app_path, stdout=mock_PIPE, stderr=mock_STDOUT)
    assert "Running scaffolded application install...." in caplog.messages
    assert "Python Application install exited with: 0" in caplog.messages
    expected_data = {"restart_type": "scaffold_install", "name": project_name}
    mock_restart.assert_called_with(data=expected_data, channel_layer=None, app_workspace=mock_workspace)


def test_get_develop_dir(tmp_path):
    mock_workspace = MagicMock(path=str(tmp_path))

    dev_dir = get_develop_dir(mock_workspace)

    expected_dev_dir = tmp_path / "develop"
    assert expected_dev_dir.is_dir()
    assert str(expected_dev_dir) == dev_dir


@pytest.mark.parametrize(
    "proper_name, default_proper_name, expected_valid, expected_proper_name", [
        ("My App", "My App", True, "My App"),
        ("My App", "My First App", True, "My App"),
        ("My-App", "My First App", True, "My App"),
        ("My/App", "My First App", False, "My/App")])
def test_proper_name_validator(proper_name, default_proper_name, expected_valid, expected_proper_name):

    valid, new_proper_name = proper_name_validator(proper_name, default_proper_name)

    assert new_proper_name == expected_proper_name
    assert valid is expected_valid
