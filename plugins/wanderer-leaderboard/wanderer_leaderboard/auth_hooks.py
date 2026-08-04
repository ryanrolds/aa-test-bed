"""Hook into Alliance Auth"""

# Django
from django.utils.translation import gettext_lazy as _

# Alliance Auth
from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

from . import urls


class WandererLeaderboardMenuItem(MenuItemHook):
    """This class ensures only authorized users will see the menu entry"""

    def __init__(self):
        # setup menu entry for sidebar
        MenuItemHook.__init__(
            self,
            _("Wanderer Leaderboard"),
            "fas fa-trophy fa-fw",
            "wanderer_leaderboard:index",
            navactive=["wanderer_leaderboard:"],
        )

    def render(self, request):
        """Render the menu item"""

        if request.user.has_perm("wanderer_leaderboard.basic_access"):
            return MenuItemHook.render(self, request)

        return ""


@hooks.register("menu_item_hook")
def register_menu():
    """Register the menu item"""

    return WandererLeaderboardMenuItem()


@hooks.register("url_hook")
def register_urls():
    """Register app urls"""

    return UrlHook(urls, "wanderer_leaderboard", r"^wanderer-leaderboard/")
