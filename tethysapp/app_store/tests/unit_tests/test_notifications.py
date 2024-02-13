import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from django.test import override_settings
from django.contrib.auth.models import User
from tethysapp.app_store.notifications import notificationsConsumer, check_user_permissions


@pytest.mark.asyncio
async def test_check_user_permissions(mocker):
    mock_user = MagicMock()
    mock_user.has_perm.return_value = True
    mocker.patch("tethysapp.app_store.notifications.User.objects.get", return_value=mock_user)

    assert await check_user_permissions(1)


@pytest.mark.asyncio
async def test_check_user_permissions_unauthorized(mocker):
    mock_user = MagicMock()
    mock_user.has_perm.return_value = False
    mocker.patch("tethysapp.app_store.notifications.User.objects.get", return_value=mock_user)

    assert not await check_user_permissions(1)


@pytest.mark.asyncio
async def test_check_user_permissions_dne(mocker):
    mocker.patch("tethysapp.app_store.notifications.User.objects.get", side_effect=[User.DoesNotExist])

    assert not await check_user_permissions(1)


@pytest.mark.asyncio
async def test_notificationsConsumer_connect_disconnect(caplog):
    consumer = notificationsConsumer
    consumer._authorized = True
    consumer.channel_layer_alias = "testlayer"
    channel_layers_setting = {
        "testlayer": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }
    with override_settings(CHANNEL_LAYERS=channel_layers_setting):
        communicator = WebsocketCommunicator(consumer.as_asgi(), "GET", "install/notifications")
        connected, _ = await communicator.connect()
        assert connected
        channel_layer = get_channel_layer("testlayer")
        channel_name = list(channel_layer.channels.keys())[0]

        await communicator.disconnect()
        assert f"Added {channel_name} channel to notifications" in caplog.messages
        assert f"Removed {channel_name} channel from notifications" in caplog.messages


@pytest.mark.asyncio
async def test_notificationsConsumer_install_notifications(caplog):
    consumer = notificationsConsumer
    consumer._authorized = True
    consumer.channel_layer_alias = "testlayer"
    channel_layers_setting = {
        "testlayer": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }
    with override_settings(CHANNEL_LAYERS=channel_layers_setting):
        communicator = WebsocketCommunicator(consumer.as_asgi(), "GET", "install/notifications")
        connected, _ = await communicator.connect()
        assert connected

        channel_layer = get_channel_layer("testlayer")
        channel_name = list(channel_layer.channels.keys())[0]
        assert "notifications" in channel_layer.groups

        message = "Sending a message"
        await channel_layer.group_send("notifications", {"type": "install_notifications", "message": message})
        response = await communicator.receive_from()
        assert response == json.dumps({'message': message})

        await communicator.disconnect()
        assert f"Added {channel_name} channel to notifications" in caplog.messages
        assert f"Sent message {message} at {channel_name}" in caplog.messages
        assert f"Removed {channel_name} channel from notifications" in caplog.messages


@pytest.mark.asyncio
async def test_notificationsConsumer_receive_begin_install(mocker, caplog):
    mock_begin_install = mocker.patch('tethysapp.app_store.notifications.begin_install')
    mock_workspace = MagicMock()
    mock_get_workspace = AsyncMock(return_value=mock_workspace)
    mocker.patch('tethysapp.app_store.notifications.sync_to_async', side_effect=[mock_get_workspace])
    mock_threading = mocker.patch('tethysapp.app_store.notifications.threading')
    consumer = notificationsConsumer
    consumer._authorized = True
    consumer.channel_layer_alias = "testlayer"
    channel_layers_setting = {
        "testlayer": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }
    with override_settings(CHANNEL_LAYERS=channel_layers_setting):
        communicator = WebsocketCommunicator(consumer.as_asgi(), "GET", "install/notifications")
        connected, _ = await communicator.connect()
        assert connected

        channel_layer = get_channel_layer("testlayer")
        channel_name = list(channel_layer.channels.keys())[0]

        install_data = {
            "data": {
                "name": "appName",
                "channel": "channel_app",
                "label": "label_app",
                "version": "current_version"
            },
            "type": "begin_install"
        }
        await communicator.send_json_to(install_data)

        await communicator.disconnect()
        assert f"Added {channel_name} channel to notifications" in caplog.messages
        assert f"Received message {json.dumps(install_data)} at {channel_name}" in caplog.messages
        assert f"Removed {channel_name} channel from notifications" in caplog.messages
        mock_threading.Thread.assert_called_with(target=mock_begin_install,
                                                 args=[install_data['data'], channel_layer, mock_workspace])
        mock_threading.Thread().start.assert_called_once()


@pytest.mark.asyncio
async def test_notificationsConsumer_receive_invalid_type(caplog):
    consumer = notificationsConsumer
    consumer._authorized = True
    consumer.channel_layer_alias = "testlayer"
    channel_layers_setting = {
        "testlayer": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }
    with override_settings(CHANNEL_LAYERS=channel_layers_setting):
        communicator = WebsocketCommunicator(consumer.as_asgi(), "GET", "install/notifications")
        connected, _ = await communicator.connect()
        assert connected

        channel_layer = get_channel_layer("testlayer")
        channel_name = list(channel_layer.channels.keys())[0]

        install_data = {"data": {}}
        await communicator.send_json_to(install_data)

        await communicator.disconnect()
        assert f"Added {channel_name} channel to notifications" in caplog.messages
        assert f"Received message {json.dumps(install_data)} at {channel_name}" in caplog.messages
        assert "Can't redirect incoming message." in caplog.messages
        assert f"Removed {channel_name} channel from notifications" in caplog.messages
