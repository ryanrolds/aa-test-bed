"""App Views"""

# Standard Library
from datetime import date

# Django
from django.contrib.auth.decorators import login_required, permission_required
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from .api import AUDIT_PERIOD_MONTHS
from .leaderboard import ACTIONS, CATEGORIES, month_bounds, monthly_leaderboard
from .models import TrackedMap


def _prev_next(year: int, month: int):
    prev = (year - 1, 12) if month == 1 else (year, month - 1)
    nxt = (year + 1, 1) if month == 12 else (year, month + 1)

    return prev, nxt


def _selected_maps(maps, map_param: str):
    if map_param == "all":
        return maps, "all"

    selected = []
    for tracked_map in maps:
        if str(tracked_map.pk) == map_param:
            selected.append(tracked_map)

    if not selected:
        return maps, "all"

    return selected, map_param


def _requested_month(request: WSGIRequest):
    today = timezone.now().date()

    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        date(year, month, 1)
    except (TypeError, ValueError):
        return today.year, today.month

    return year, month


def _beyond_api_horizon(year: int, month: int) -> bool:
    """The audit API only reaches back a fixed number of months, and never
    forward. Anything outside that can't be answered, empty or not."""
    today = timezone.now().date()
    months_back = (today.year - year) * 12 + (today.month - month)

    return months_back < 0 or months_back > AUDIT_PERIOD_MONTHS


@login_required
@permission_required("wanderer_leaderboard.basic_access")
def index(request: WSGIRequest) -> HttpResponse:

    maps = list(TrackedMap.objects.active())
    selected, selected_key = _selected_maps(maps, request.GET.get("map", "all"))
    year, month = _requested_month(request)

    beyond_horizon = _beyond_api_horizon(year, month)
    if selected and not beyond_horizon:
        rows, errors = monthly_leaderboard(selected, year, month)
    else:
        rows, errors = [], []

    (prev_year, prev_month), (next_year, next_month) = _prev_next(year, month)
    _, _, period_label = month_bounds(year, month)

    context = {
        "maps": maps,
        "selected_key": selected_key,
        "rows": rows,
        "errors": errors,
        "beyond_horizon": beyond_horizon,
        "horizon_months": AUDIT_PERIOD_MONTHS,
        "categories": CATEGORIES,
        "actions": ACTIONS,
        "year": year,
        "month": month,
        "period_label": period_label,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
    }

    return render(request, "wanderer_leaderboard/index.html", context)
