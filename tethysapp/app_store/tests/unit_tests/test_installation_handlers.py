from unittest.mock import MagicMock
from argparse import Namespace
from tethysapp.app_store.installation_handlers import (get_service_options)


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
    assert mock_services_list_command.called_with(expected_args)
