from .helpers import logger, send_notification
from .submission_handlers import submit_proxyapp_to_store


def create_proxy_app(install_data, channel_layer):
    """Create a proxy app from the user provided input

    Args:
        install_data (dict): Dictionary containing installation information for the proxy app
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    from tethys_apps.models import ProxyApp

    app_created = False
    app_name = install_data['app_name']
    proxy_endpoint = install_data['endpoint']
    proxy_description = install_data['description']
    proxy_logo = install_data['logo_url']
    proxy_tags = install_data['tags']
    proxy_tags = ",".join(proxy_tags) if isinstance(proxy_tags, list) else proxy_tags
    proxy_enabled = install_data['enabled']
    proxy_shown = install_data['show_in_apps_library']
    try:
        logger.info(f"Checking to see if the {app_name} proxy app exists")
        proxy_app = ProxyApp.objects.get(name=app_name)
        send_notification(f"There is already a proxy app with that name: {app_name}", channel_layer)

    except ProxyApp.DoesNotExist:
        logger.info(f"Creating the {app_name} proxy app")
        proxy_app = ProxyApp(
            name=app_name,
            endpoint=proxy_endpoint,
            logo_url=proxy_logo,
            back_url="",
            description=proxy_description,
            tags=proxy_tags,
            show_in_apps_library=proxy_shown,
            enabled=proxy_enabled,
            open_in_new_tab=True,
            display_external_icon=False,
            order=0,
        )

        proxy_app.save()
        app_created = True
        send_notification(f"Proxy app {app_name} added", channel_layer)

    return app_created


def list_proxy_apps():
    """Retrieves all the installed proxy apps
    """
    from tethys_apps.models import ProxyApp

    proxy_apps = ProxyApp.objects.all()
    proxy_app_list = []
    for proxy_app in proxy_apps:
        proxy_app_list.append({
            "name": proxy_app.name,
            "description": proxy_app.description,
            "endpoint": proxy_app.endpoint,
            "logo": proxy_app.logo_url,
            "tags": proxy_app.tags,
            "enabled": proxy_app.enabled,
            "show_in_apps_library": proxy_app.show_in_apps_library
        })
    return proxy_app_list


def delete_proxy_app(install_data, channel_layer):
    """Delete the proxy app from the specified app name

    Args:
        install_data (dict): Dictionary containing installation information for the proxy app
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    from tethys_apps.models import ProxyApp

    app_name = install_data['app_name']
    proxy_app = ProxyApp.objects.get(name=app_name)
    proxy_app.delete()

    send_notification(f"Proxy app '{app_name}' was deleted successfully", channel_layer)

    return


def update_proxy_app(install_data, channel_layer):
    """Update an existing proxy app with the provided user input data

    Args:
        install_data (dict): Dictionary containing installation information for the proxy app
        channel_layer (Django Channels Layer): Asynchronous Django channel layer from the websocket consumer
    """
    from tethys_apps.models import ProxyApp

    app_name = install_data.pop('app_name')
    try:
        proxy_app = ProxyApp.objects.get(name=app_name)
    except ProxyApp.DoesNotExist:
        logger.info(f"Proxy app named '{app_name}' does not exist")
        return

    for app_key, app_value in install_data.items():
        if not hasattr(proxy_app, app_key):
            logger.info(f"Attribute {app_key} does not exist")

        if app_key == "tags":
            app_value = ",".join(app_value)
        setattr(proxy_app, app_key, app_value)
        proxy_app.save()

        logger.info(f"Attribute {app_key} was updated successfully with {app_value}")

    proxy_app.save()
    send_notification(f"Proxy app '{app_name}' was updated successfully", channel_layer)

    return


def submit_proxy_app(install_data, channel_layer, app_workspace):
    from tethys_apps.models import ProxyApp

    app_name = install_data['app_name']
    active_stores = install_data['active_stores']
    proxy_app = ProxyApp.objects.get(name=app_name)

    for active_store in active_stores:
        submit_data = active_store
        submit_data['email'] = install_data['notification_email']
        submit_proxyapp_to_store(proxy_app, submit_data, channel_layer, app_workspace)

    return
