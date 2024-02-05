import re
from tethys_portal import __version__ as tethys_version
from django.http import JsonResponse
from django.shortcuts import render
from tethys_sdk.routing import controller

from .resource_helpers import get_stores_reformatted
from .helpers import get_conda_stores, html_label_styles, get_color_label_dict
from .proxy_app_handlers import list_proxy_apps
ALL_RESOURCES = []
CACHE_KEY = "warehouse_app_resources"


@controller(
    name='home',
    url='app-store',
    permissions_required='use_app_store',
    app_workspace=True
)
def home(request, app_workspace):
    """Created the context for the home page of the app store

    Args:
        request (Django Request): Django request object containing information about the user and user request

    Returns:
        object: Rendered html Django object
    """
    available_stores = get_conda_stores()
    labels_style_dict, available_stores = get_color_label_dict(available_stores)

    object_stores_formatted_by_label_and_channel = get_stores_reformatted(app_workspace, refresh=False,
                                                                          conda_channels="all")

    tethys_version_regex = re.search(r'([\d.]+[\d])', tethys_version).group(1)
    object_stores_formatted_by_label_and_channel['tethysVersion'] = tethys_version_regex

    availableApps = object_stores_formatted_by_label_and_channel['availableApps']
    installedApps = object_stores_formatted_by_label_and_channel['installedApps']
    incompatibleApps = object_stores_formatted_by_label_and_channel['incompatibleApps']
    tethysVersion = object_stores_formatted_by_label_and_channel['tethysVersion']
    
    proxyApps = list_proxy_apps()

    context = {
        'storesData': available_stores,
        'show_stores': True if len(available_stores) > 0 else False,
        'list_styles': html_label_styles,
        'labels_style_dict': labels_style_dict,
        'availableApps': availableApps,
        'installedApps': installedApps,
        'proxyApps': proxyApps,
        'incompatibleApps': incompatibleApps,
        'tethysVersion': tethysVersion
    }

    return render(request, 'app_store/home.html', context)


@controller(
    name='get_available_stores',
    url='app-store/get_available_stores',
    permissions_required='use_app_store'
)
def get_available_stores(request):
    """Retrieves the available stores through an ajax request

    Args:
        request (Django Request): Django request object containing information about the user and user request

    Returns:
        JsonResponse: A json reponse of the available conda stores
    """
    available_stores = get_conda_stores()
    available_stores_dict = {"stores": available_stores}
    return JsonResponse(available_stores_dict)


@controller(
    name='get_merged_resources',
    url='app-store/get_merged_resources',
    permissions_required='use_app_store',
    app_workspace=True,
)
def get_merged_resources(request, app_workspace):

    stores_active = request.GET.get('active_store')

    object_stores_formatted_by_label_and_channel = get_stores_reformatted(app_workspace, refresh=False,
                                                                          conda_channels=stores_active)

    tethys_version_regex = re.search(r'([\d.]+[\d])', tethys_version).group(1)
    object_stores_formatted_by_label_and_channel['tethysVersion'] = tethys_version_regex

    return JsonResponse(object_stores_formatted_by_label_and_channel)
