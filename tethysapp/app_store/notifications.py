from channels.generic.websocket import AsyncWebsocketConsumer
from .helpers import restart_server  # noqa: F401
from .installation_handlers import (logger, continueAfterInstall, set_custom_settings,  # noqa: F401
                                    configure_services)  # noqa: F401
from .uninstall_handlers import uninstall_app  # noqa: F401
from .git_install_handlers import get_log_file  # noqa: F401
from .update_handlers import update_app  # noqa: F401
from .resource_helpers import clear_conda_channel_cache  # noqa: F401
from .submission_handlers import submit_tethysapp_to_store, initialize_local_repo_for_active_stores  # noqa: F401
from .proxy_app_handlers import create_proxy_app, delete_proxy_app, update_proxy_app, submit_proxy_app  # noqa: F401
# called with threading.Thread
from .begin_install import begin_install  # noqa: F401
from tethys_sdk.routing import consumer
from tethys_sdk.workspaces import get_app_workspace
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User

import json
import sys
import threading
from .app import AppStore as app
from channels.db import database_sync_to_async


@database_sync_to_async
def check_user_permissions(user_id):
    try:
        user = User.objects.get(id=user_id)
        if user.has_perm("tethys_apps.app_store:use_app_store"):
            return True
        return False
    except User.DoesNotExist:
        return False


@consumer(
    name='install_notifications',
    url='install/notifications',
)
class notificationsConsumer(AsyncWebsocketConsumer):
    authorized = False

    async def connect(self):
        """Connects to the websocket consumer and adds a notifications group to the channel
        """
        self.authorized = await check_user_permissions(self.scope["user"].id)
        if self.authorized:
            await self.accept()
            await self.channel_layer.group_add("notifications", self.channel_name)
            logger.info(f"Added {self.channel_name} channel to notifications")

    async def disconnect(self, _):
        """Disconnects from the websocket consumer and removes a notifications group from the channel
        """
        if "notifications" in self.channel_layer.groups:
            await self.channel_layer.group_discard("notifications", self.channel_name)
            logger.info(f"Removed {self.channel_name} channel from notifications")

    async def install_notifications(self, event):
        """Sends a notification to the notifications group channel

        Args:
            event (dict): event dictionary containing the message that will be sent to the channel group
        """
        if self.authorized:
            message = event['message']
            await self.send(text_data=json.dumps({'message': message, }))
            logger.info(f"Sent message {message} at {self.channel_name}")

    async def receive(self, text_data):
        """Receives information from the user and runs the specified functions and arguments

        Args:
            text_data (str): Json string of information on what function the server should run
        """
        if self.authorized:
            logger.info(f"Received message {text_data} at {self.channel_name}")
            text_data_json = json.loads(text_data)
            function_name = text_data_json.get('type')
            if not function_name:
                logger.info("Can't redirect incoming message.")
                return

            module_name = sys.modules[__name__]
            args = [text_data_json['data'], self.channel_layer]

            app_workspace_functions = ['begin_install', 'restart_server', 'get_log_file', 'submit_tethysapp_to_store',
                                       'initialize_local_repo_for_active_stores', 'update_app', 'uninstall_app',
                                       'submit_proxy_app']

            if function_name in app_workspace_functions:
                app_workspace = await sync_to_async(get_app_workspace, thread_sensitive=True)(app)
                args.append(app_workspace)

            thread = threading.Thread(target=getattr(module_name, function_name), args=args)
            thread.start()
