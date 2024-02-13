from unittest.mock import MagicMock, call
from argparse import Namespace
from django.core.exceptions import ObjectDoesNotExist
from tethys_sdk.app_settings import CustomSetting
from tethysapp.app_store.installation_handlers import (get_service_options, continueAfterInstall,
                                                       set_custom_settings, process_settings, configure_services,
                                                       getServiceList)


def test_get_service_options(mocker):
    mock_query_set = MagicMock(id=1)
    mock_query_set.name = "service_setting"
    mock_services_list_command = mocker.patch('tethysapp.app_store.installation_handlers.services_list_command',
                                              return_value=[[mock_query_set]])
    service_type = "spatial"

    services = get_service_options(service_type)

    expected_services = [{"name": "service_setting", "id": 1}]
    assert services == expected_services
    expected_args = Namespace(spatial=True)
    mock_services_list_command.asserrt_called_with(expected_args)


def test_continueAfterInstall(mocker):
    mock_ws = mocker.patch('tethysapp.app_store.installation_handlers.send_notification')
    mock_dad = mocker.patch('tethysapp.app_store.installation_handlers.detect_app_dependencies')
    app_install_data = {'isInstalled': True, 'channel': 'channel', 'version': '1.0'}
    mocker.patch('tethysapp.app_store.installation_handlers.check_if_app_installed', return_value=app_install_data)
    install_data = {"name": "test_app", "version": "1.0"}
    mock_channel = MagicMock()

    continueAfterInstall(install_data, mock_channel)

    mock_ws.assert_called_with("Resuming processing...", mock_channel)
    mock_dad.assert_called_with(install_data['name'], mock_channel)


def test_continueAfterInstall_incorrect_version(mocker, caplog):
    mock_ws = mocker.patch('tethysapp.app_store.installation_handlers.send_notification')
    mocker.patch('tethysapp.app_store.installation_handlers.detect_app_dependencies')
    app_install_data = {'isInstalled': True, 'channel': 'channel', 'version': '1.0'}
    mocker.patch('tethysapp.app_store.installation_handlers.check_if_app_installed', return_value=app_install_data)
    install_data = {"name": "test_app", "version": "1.5"}
    mock_channel = MagicMock()

    continueAfterInstall(install_data, mock_channel)

    mock_ws.assert_called_with("Server error while processing this installation. Please check your logs", mock_channel)
    assert "ERROR: ContinueAfterInstall: Correct version is not installed of this package." in caplog.messages


def test_set_custom_settings(tethysapp, tmp_path, mocker):
    mock_ws = mocker.patch('tethysapp.app_store.installation_handlers.send_notification')
    app = tethysapp()
    tethysapp_object = MagicMock(id=1)
    mocker.patch('tethysapp.app_store.installation_handlers.get_app_instance_from_path', return_value=app)
    mock_process_settings = mocker.patch('tethysapp.app_store.installation_handlers.process_settings')
    mocker.patch('tethysapp.app_store.installation_handlers.TethysApp.objects.get', return_value=tethysapp_object)
    mock_actual_setting = MagicMock(value="test")
    mocker.patch('tethysapp.app_store.installation_handlers.CustomSetting.objects.get',
                 return_value=mock_actual_setting)
    custom_settings_data = {"app_py_path": tmp_path, "settings": {"mock_setting": "setting_value"}}
    mock_channel = MagicMock()

    set_custom_settings(custom_settings_data, mock_channel)

    mock_ws.assert_has_calls([
        call("Custom Settings configured.", mock_channel),
        call({"data": {}, "jsHelperFunction": "customSettingConfigComplete"}, mock_channel)
    ])
    mock_process_settings.assert_called_once()
    assert mock_actual_setting.value == custom_settings_data['settings']['mock_setting']
    assert mock_actual_setting.clean.call_count == 1
    assert mock_actual_setting.save.call_count == 1


def test_set_custom_settings_skip(tethysapp, tmp_path, mocker, caplog):
    mock_ws = mocker.patch('tethysapp.app_store.installation_handlers.send_notification')
    app = tethysapp()
    mocker.patch('tethysapp.app_store.installation_handlers.get_app_instance_from_path', return_value=app)
    mock_process_settings = mocker.patch('tethysapp.app_store.installation_handlers.process_settings')
    custom_settings_data = {"app_py_path": tmp_path, "skip": True, "noneFound": True}
    mock_channel = MagicMock()

    set_custom_settings(custom_settings_data, mock_channel)

    mock_ws.assert_has_calls([
        call("No Custom Settings Found to process.", mock_channel),
    ])
    mock_process_settings.assert_called_once()
    assert "Skip/NoneFound option called." in caplog.messages


def test_set_custom_settings_object_dne(tethysapp, tmp_path, mocker, caplog):
    mock_ws = mocker.patch('tethysapp.app_store.installation_handlers.send_notification')
    app = tethysapp()
    mocker.patch('tethysapp.app_store.installation_handlers.get_app_instance_from_path', return_value=app)
    mocker.patch('tethysapp.app_store.installation_handlers.TethysApp.objects.get', side_effect=[ObjectDoesNotExist])
    custom_settings_data = {"app_py_path": tmp_path, "settings": {"mock_setting": "setting_value"}}
    mock_channel = MagicMock()

    set_custom_settings(custom_settings_data, mock_channel)

    mock_ws.assert_has_calls([
        call("Error Setting up custom settings. Check logs for more details", mock_channel)
    ])
    assert "Couldn't find app instance to get the ID to connect the settings to" in caplog.messages


def test_process_settings(tmp_path, tethysapp, mocker):
    mock_ws = mocker.patch('tethysapp.app_store.installation_handlers.send_notification')
    custom_setting = CustomSetting(
        name='default_name',
        type=CustomSetting.TYPE_STRING,
        description='Default model name.',
        required=True,
        default="Name_123"
    )
    mock_setting = MagicMock(required=True, description="description")
    mock_setting.name = "test_setting"
    mock_settings = {"unlinked_settings": [mock_setting, custom_setting]}
    mocker.patch('tethysapp.app_store.installation_handlers.get_app_settings', return_value=mock_settings)
    mocker.patch('tethysapp.app_store.installation_handlers.get_service_type_from_setting', return_value="spatial")
    mocker.patch('tethysapp.app_store.installation_handlers.get_setting_type_from_setting', return_value="ds_spatial")
    service_options = {"name": "spatial_service", "id": 1}
    mocker.patch('tethysapp.app_store.installation_handlers.get_service_options', return_value=service_options)
    app = tethysapp()
    mock_channel = MagicMock()

    process_settings(app, tmp_path, mock_channel)

    expected_data_json = {
        "data": [{
            "name": "test_setting",
            "required": True,
            "description": "description",
            "service_type": "spatial",
            "setting_type": "ds_spatial",
            "options": service_options
        }],
        "returnMethod": "configure_services",
        "jsHelperFunction": "processServices",
        "app_py_path": tmp_path,
        "current_app_name": "test_app"
    }
    mock_ws.assert_called_with(expected_data_json, mock_channel)


def test_process_settings_no_settings(tmp_path, tethysapp, mocker):
    mock_ws = mocker.patch('tethysapp.app_store.installation_handlers.send_notification')
    mocker.patch('tethysapp.app_store.installation_handlers.get_app_settings', return_value=[])
    app = tethysapp()
    mock_channel = MagicMock()

    process_settings(app, tmp_path, mock_channel)

    mock_ws.assert_called_with("No Services found to configure.", mock_channel)


def test_configure_services(mocker):
    mock_ws = mocker.patch('tethysapp.app_store.installation_handlers.send_notification')
    mock_link = mocker.patch('tethysapp.app_store.installation_handlers.link_service_to_app_setting')
    mock_channel = MagicMock()
    services_data = {
        "app_name": "test_setting",
        "service_name": "spatial_service",
        "service_type": "spatial",
        "setting_type": "ds_spatial",
        "service_id": 1
    }

    configure_services(services_data, mock_channel)

    mock_link.assert_called_with(services_data['service_type'], services_data['service_id'], services_data['app_name'],
                                 services_data['setting_type'], services_data['service_name'])
    get_data_json = {
        "data": {"serviceName": services_data['service_name']},
        "jsHelperFunction": "serviceConfigComplete"
    }
    mock_ws.assert_called_with(get_data_json, mock_channel)


def test_configure_services_error(mocker, caplog):
    mocker.patch('tethysapp.app_store.installation_handlers.link_service_to_app_setting',
                 side_effect=[Exception("failed to link")])
    mock_channel = MagicMock()
    services_data = {
        "app_name": "test_setting",
        "service_name": "spatial_service",
        "service_type": "spatial",
        "setting_type": "ds_spatial",
        "service_id": 1
    }

    config = configure_services(services_data, mock_channel)

    assert config is None
    assert "failed to link" in caplog.messages
    assert "Error while linking service" in caplog.messages


def test_getServiceList(mocker):
    mock_ws = mocker.patch('tethysapp.app_store.installation_handlers.send_notification')
    service_options = {"name": "spatial_service", "id": 1}
    mocker.patch('tethysapp.app_store.installation_handlers.get_service_options', return_value=service_options)
    mock_channel = MagicMock()
    data = {"settingType": "spatial"}

    getServiceList(data, mock_channel)

    get_data_json = {
        "data": {"settingType": data['settingType'], "newOptions": service_options},
        "jsHelperFunction": "updateServiceListing"
    }
    mock_ws.assert_called_with(get_data_json, mock_channel)
