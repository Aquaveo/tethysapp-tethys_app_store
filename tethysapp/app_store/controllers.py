import re
from tethys_portal import __version__ as tethys_version
from django.http import JsonResponse
from django.shortcuts import render
from tethys_sdk.routing import controller

from .resource_helpers import get_stores_reformatted
from .app import AppStore as app
from .utilities import decrypt
ALL_RESOURCES = []
CACHE_KEY = "warehouse_app_resources"


@controller(
    name='home',
    url='app-store',
    permissions_required='use_app_store'
)
def home(request):
    """Created the context for the home page of the app store

    Args:
        request (Django Request): Django request object containing information about the user and user request

    Returns:
        object: Rendered html Django object
    """
    available_stores_data_dict = app.get_custom_setting("stores_settings")['stores']
    encryption_key = app.get_custom_setting("encryption_key")
    for store in available_stores_data_dict:
        store['github_token'] = decrypt(store['github_token'], encryption_key)

    context = {
        'storesData': available_stores_data_dict,
        'show_stores': True if len(available_stores_data_dict) > 0 else False
    }

    return render(request, 'app_store/home.html', context)


@controller(
    name='get_available_stores',
    url='app-store/get_available_stores',
    permissions_required='use_app_store',
    app_workspace=True,
)
def get_available_stores(request, app_workspace):

    available_stores_data_dict = app.get_custom_setting("stores_settings")
    encryption_key = app.get_custom_setting("encryption_key")
    for store in available_stores_data_dict['stores']:
        store['github_token'] = decrypt(store['github_token'], encryption_key)

    return JsonResponse(available_stores_data_dict)


@controller(
    name='get_merged_resources',
    url='app-store/get_merged_resources',
    permissions_required='use_app_store',
    app_workspace=True,
)
def get_resources_multiple_stores(request, app_workspace):

    stores_active = request.GET.get('active_store')

    object_stores_formatted_by_label_and_channel = get_stores_reformatted(app_workspace, refresh=False,
                                                                          stores=stores_active)

    tethys_version_regex = re.search(r'([\d.]+[\d])', tethys_version).group(1)
    object_stores_formatted_by_label_and_channel['tethysVersion'] = tethys_version_regex

    return JsonResponse(object_stores_formatted_by_label_and_channel)
