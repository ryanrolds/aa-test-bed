"""App Views"""

# Standard Library
import logging
from datetime import date

# Django
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .api import AUDIT_PERIOD_MONTHS, WandererApiError
from .leaderboard import ACTIONS, CATEGORIES, month_label, monthly_leaderboard
from .models import TrackedMap

logger = logging.getLogger(__name__)

# Column headings for the three actions, in ACTIONS order. Abbreviated because
# nine of them share a table with the contributor names.
ACTION_LABELS = {
    "created": _("New"),
    "updated": _("Upd"),
    "deleted": _("Del"),
}


def _prev_next(year: int, month: int) -> tuple[tuple[int, int], tuple[int, int]]:
    previous = (year - 1, 12) if month == 1 else (year, month - 1)
    following = (year + 1, 1) if month == 12 else (year, month + 1)

    return previous, following


def _selected_map(maps: list[TrackedMap], map_param: str) -> TrackedMap | None:
    """The requested map, or the first one when nothing valid was asked for.

    One map at a time on purpose: each one costs a synchronous call to a slow
    audit endpoint, so "all maps" was really "wait for all of them in turn".
    """
    for tracked_map in maps:
        if str(tracked_map.pk) == map_param:
            return tracked_map

    return maps[0] if maps else None


def _requested_month(request: HttpRequest) -> tuple[int, int]:
    """The year and month asked for, falling back to the current one."""
    today = timezone.now().date()

    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        date(year, month, 1)  # raises unless the pair is a real month
    except (TypeError, ValueError):
        return today.year, today.month

    return year, month


def _beyond_api_horizon(year: int, month: int) -> bool:
    """Whether a month is outside what the audit API can answer.

    It only reaches back a fixed number of months, and never forward. Outside
    that, an empty table would be indistinguishable from a quiet month.
    """
    today = timezone.now().date()
    months_back = (today.year - year) * 12 + (today.month - month)

    return months_back < 0 or months_back > AUDIT_PERIOD_MONTHS


@login_required
@permission_required("wanderer_leaderboard.basic_access")
def index(request: HttpRequest) -> HttpResponse:
    """The leaderboard for one map and one month."""
    maps = list(TrackedMap.objects.active())
    selected = _selected_map(maps, request.GET.get("map", ""))
    year, month = _requested_month(request)

    rows = []
    error = None
    beyond_horizon = _beyond_api_horizon(year, month)

    if selected is not None and not beyond_horizon:
        try:
            rows = monthly_leaderboard(selected, year, month)
        except WandererApiError as exc:
            # the page shows the short message; the log gets the full context
            logger.warning("audit fetch failed: %s", exc.detail)
            error = str(exc)

    (prev_year, prev_month), (next_year, next_month) = _prev_next(year, month)

    context = {
        "maps": maps,
        "selected_map": selected,
        "rows": rows,
        "error": error,
        "beyond_horizon": beyond_horizon,
        "horizon_months": AUDIT_PERIOD_MONTHS,
        "categories": CATEGORIES,
        "action_labels": [ACTION_LABELS[action] for action in ACTIONS],
        "year": year,
        "month": month,
        "period_label": month_label(year, month),
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
    }

    return render(request, "wanderer_leaderboard/index.html", context)
