from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook
from django.utils.translation import gettext_lazy as _

from . import urls


class WandererMenuItem(MenuItemHook):
    def __init__(self):
        super().__init__(
            _("Wanderer"),
            "fas fa-map fa-fw",
            "wanderer:index",
            navactive=["wanderer:"],
        )

    def render(self, request):
        if request.user.has_perm("wanderer.basic_access"):
            return MenuItemHook.render(self, request)
        return ""


@hooks.register("menu_item_hook")
def register_menu():
    return WandererMenuItem()


@hooks.register("url_hook")
def register_urls():
    return UrlHook(urls, "wanderer", r"^wanderer/")
