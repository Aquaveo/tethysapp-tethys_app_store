from unittest.mock import MagicMock
from tethysapp.app_store.proxy_app_handlers import (create_proxy_app, list_proxy_apps, delete_proxy_app,
                                                    update_proxy_app, submit_proxy_app)
from tethys_apps.models import ProxyApp


def raise_proxy_dne(name):
    raise ProxyApp.DoesNotExist("ProxyApp matching query does not exist.")


def test_create_proxy_app(mocker, proxy_app_install_data, caplog):
    mock_sn = mocker.patch("tethysapp.app_store.proxy_app_handlers.send_notification")
    mock_ProxyApp = mocker.patch("tethys_apps.models.ProxyApp")
    mocker.patch("tethys_apps.models.ProxyApp.DoesNotExist", ProxyApp.DoesNotExist)
    mocker.patch("tethys_apps.models.ProxyApp.objects.get", raise_proxy_dne)
    mock_channel = MagicMock()

    create_proxy_app(proxy_app_install_data, mock_channel)

    app_name = proxy_app_install_data['app_name']
    mock_ProxyApp.assert_called_with(
        name=app_name,
        endpoint=proxy_app_install_data['endpoint'],
        logo_url=proxy_app_install_data['logo_url'],
        back_url="",
        description=proxy_app_install_data['description'],
        tags=",".join(proxy_app_install_data['tags']),
        show_in_apps_library=proxy_app_install_data['show_in_apps_library'],
        enabled=proxy_app_install_data['enabled'],
        open_in_new_tab=True,
        display_external_icon=False,
        order=0
    )
    mock_ProxyApp().save.assert_called_once()
    mock_sn.assert_called_with(f"Proxy app {app_name} added", mock_channel)
    assert f"Checking to see if the {app_name} proxy app exists" in caplog.messages
    assert f"Creating the {app_name} proxy app" in caplog.messages


def test_create_proxy_app_already_exists(mocker, proxy_app_install_data, caplog):
    mock_sn = mocker.patch("tethysapp.app_store.proxy_app_handlers.send_notification")
    mock_ProxyApp = mocker.patch("tethys_apps.models.ProxyApp")
    mock_channel = MagicMock()

    create_proxy_app(proxy_app_install_data, mock_channel)

    app_name = proxy_app_install_data['app_name']
    mock_ProxyApp.assert_not_called()
    mock_sn.assert_called_with(f"There is already a proxy app with that name: {app_name}", mock_channel)
    assert f"Checking to see if the {app_name} proxy app exists" in caplog.messages


def test_list_proxy_apps(proxyapp, mocker):
    proxyApp = proxyapp()
    mocker.patch("tethys_apps.models.ProxyApp.objects.all", return_value=[proxyApp])

    proxy_apps = list_proxy_apps()

    expected_proxy_apps = [{
        "name": proxyApp.name,
        "description": proxyApp.description,
        "endpoint": proxyApp.endpoint,
        "logo": proxyApp.logo_url,
        "tags": proxyApp.tags,
        "enabled": proxyApp.enabled,
        "show_in_apps_library": proxyApp.show_in_apps_library
    }]
    assert proxy_apps == expected_proxy_apps


def test_delete_proxy_app(mocker):
    mock_app = MagicMock()
    mocker.patch("tethys_apps.models.ProxyApp.objects.get", return_value=mock_app)
    mock_sn = mocker.patch("tethysapp.app_store.proxy_app_handlers.send_notification")
    mock_channel = MagicMock()
    install_data = {"app_name": "test_app"}

    delete_proxy_app(install_data, mock_channel)

    mock_app.delete.assert_called()
    mock_sn.assert_called_with("Proxy app 'test_app' was deleted successfully", mock_channel)


def test_update_proxy_app(mocker, proxy_app_install_data, proxyapp):
    proxyApp = proxyapp()
    mocker.patch("tethys_apps.models.ProxyApp.objects.get", return_value=proxyApp)
    mock_sn = mocker.patch("tethysapp.app_store.proxy_app_handlers.send_notification")
    mock_channel = MagicMock()

    assert proxyApp.description == "proxy app description"
    assert proxyApp.endpoint == "https_endpoint"
    assert proxyApp.tags == "tag1,tag2"

    update_proxy_app(proxy_app_install_data, mock_channel)

    assert proxyApp.description == "This is a test proxy app"
    assert proxyApp.endpoint == "https://google.com"
    assert proxyApp.tags == "tag1,tag2,tag3"
    mock_sn.assert_called_with("Proxy app 'test proxy app' was updated successfully", mock_channel)


def test_update_proxy_app_missing_attr(mocker, proxy_app_install_data, proxyapp, caplog):
    proxyApp = proxyapp()
    mocker.patch("tethys_apps.models.ProxyApp.objects.get", return_value=proxyApp)
    mock_sn = mocker.patch("tethysapp.app_store.proxy_app_handlers.send_notification")
    mock_channel = MagicMock()

    assert proxyApp.description == "proxy app description"
    assert proxyApp.endpoint == "https_endpoint"
    assert proxyApp.tags == "tag1,tag2"
    proxy_app_install_data['bad_attr'] = 'test'

    update_proxy_app(proxy_app_install_data, mock_channel)

    assert proxyApp.description == "This is a test proxy app"
    assert proxyApp.endpoint == "https://google.com"
    assert proxyApp.tags == "tag1,tag2,tag3"
    mock_sn.assert_called_with("Proxy app 'test proxy app' was updated successfully", mock_channel)
    assert "Attribute bad_attr does not exist" in caplog.messages


def test_update_proxy_app_missing_app(mocker, proxy_app_install_data, caplog):
    mocker.patch("tethys_apps.models.ProxyApp")
    mocker.patch("tethys_apps.models.ProxyApp.DoesNotExist", ProxyApp.DoesNotExist)
    mocker.patch("tethys_apps.models.ProxyApp.objects.get", raise_proxy_dne)
    mock_channel = MagicMock()

    update_proxy_app(proxy_app_install_data, mock_channel)

    assert "Proxy app named 'test proxy app' does not exist" in caplog.messages


def test_submit_proxy_app(mocker, store, proxyapp):
    mock_proxy = mocker.patch("tethys_apps.models.ProxyApp")
    mock_submit = mocker.patch("tethysapp.app_store.proxy_app_handlers.submit_proxyapp_to_store")
    app = proxyapp()
    store = store("test_store")
    mock_proxy.objects.get.return_value = app
    install_data = {
        "app_name": "test_app",
        "notification_email": "test_email",
        "active_stores": [store]
    }
    mock_channel = MagicMock()
    mock_workspace = MagicMock()

    submit_proxy_app(install_data, mock_channel, mock_workspace)

    submit_data = store
    submit_data['notification_email'] = install_data['notification_email']
    mock_submit.assert_called_with(app, submit_data, mock_channel, mock_workspace)
