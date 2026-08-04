"""Monthly leaderboard aggregation from Wanderer's audit API"""

# Standard Library
import calendar
import json
import logging
from datetime import datetime, timezone

# Alliance Auth
from allianceauth.authentication.models import CharacterOwnership

from . import api
from .api import WandererApiError

logger = logging.getLogger(__name__)

CATEGORIES = ("systems", "connections", "signatures")
ACTIONS = ("created", "updated", "deleted")
METRIC_KEYS = [f"{c}_{a}" for c in CATEGORIES for a in ACTIONS]

# event_data lists whose length is the real count, one event covers many items.
# Only plural keys belong here: {"solar_system_id": 30003731} is a scalar naming
# one system, which the fallback already counts as 1.
_LIST_COUNT_KEYS = ("signatures", "solar_system_ids")


def classify(event_name):
    et = (event_name or "").lower()
    if "acl" in et:
        return None

    if "signature" in et:
        category = "signatures"
    elif "connection" in et:
        category = "connections"
    elif "system" in et:
        category = "systems"
    else:
        return None

    if "add" in et or "creat" in et:
        action = "created"
    elif "updat" in et:
        action = "updated"
    elif "remov" in et or "delet" in et:
        action = "deleted"
    else:
        return None

    return category, action


def _count_from_mapping(data):
    for key in _LIST_COUNT_KEYS:
        value = data.get(key)
        if isinstance(value, list):
            return max(1, len(value))

    return 1


def _count_from_display_string(event_data):
    """Count items in the audit API's flattened form, e.g.

        "XHQ-7V: ZMK-785, BNJ-940, OSV-920"  -> 3   (system prefix, then items)
        "XHQ-7V"                             -> 1   (the subject itself)

    The prefix before ":" names where the event happened, so it isn't part of the
    count. Nothing EVE puts in a system name or signature id contains "," or ":".
    """
    head, separator, tail = event_data.partition(":")
    payload = tail if separator else head

    items = [part for part in (raw.strip() for raw in payload.split(",")) if part]

    return max(1, len(items))


def count_for(event_data):
    """How many things a single audit event actually covers.

    Wanderer's database stores event_data as JSON ({"signatures": [...]}) but its
    audit API flattens it to a display string first. The API is what this plugin
    reads, so that shape is handled; the JSON branch stays for direct-database
    callers and any version that returns it unflattened.
    """
    if not event_data:
        return 1

    if isinstance(event_data, dict):
        return _count_from_mapping(event_data)

    try:
        data = json.loads(event_data)
    except (ValueError, TypeError):
        return _count_from_display_string(event_data)

    if isinstance(data, dict):
        return _count_from_mapping(data)

    return 1


def month_bounds(year, month):
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

    return start, end, f"{calendar.month_name[month]} {year}"


def _resolve_owners(eve_ids):
    numeric_ids = []
    for eve_id in eve_ids:
        if str(eve_id).isdigit():
            numeric_ids.append(int(eve_id))

    ownerships = CharacterOwnership.objects.filter(
        character__character_id__in=numeric_ids
    ).select_related("character", "user__profile__main_character")

    owners = {}
    for ownership in ownerships:
        main = ownership.user.profile.main_character
        if main:
            owners[str(ownership.character.character_id)] = {
                "main_name": main.character_name,
                "main_eve_id": str(main.character_id),
            }

    return owners


def event_datetime(value):
    """Parse an ISO8601 audit timestamp, assuming UTC when it carries no zone."""
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed


def _per_character_counts(tracked_maps, year, month):
    """Counts and character identities keyed by EVE character id, plus the
    per-map failures worth telling the user about."""
    start, end, _ = month_bounds(year, month)

    counts = {}
    identities = {}
    errors = []

    for tracked_map in tracked_maps:
        try:
            events = api.audit_events(tracked_map)
        except WandererApiError as exc:
            # the page shows str(exc) to users; the log gets the full context
            logger.warning("audit fetch failed: %s", exc.detail)
            errors.append(str(exc))
            continue

        for event in events:
            classified = classify(event.get("event_name"))
            if not classified:
                continue

            # the API window is relative (3 months), so the month is ours to cut
            occurred = event_datetime(event.get("inserted_at"))
            if occurred is None or not start <= occurred < end:
                continue

            character = event.get("character") or {}
            eve_id = str(character.get("eve_id") or "")
            if not eve_id:
                continue

            identities.setdefault(eve_id, character)
            category, action = classified
            bucket = counts.setdefault(eve_id, {k: 0 for k in METRIC_KEYS})
            bucket[f"{category}_{action}"] += count_for(event.get("event_data"))

    return counts, identities, errors


def monthly_leaderboard(tracked_maps, year, month):
    """Ranked rows for the month, plus any per-map fetch errors."""
    counts, identities, errors = _per_character_counts(tracked_maps, year, month)
    if not counts:
        return [], errors

    owners = _resolve_owners(list(counts.keys()))

    groups = {}
    for eve_id, metrics in counts.items():
        character = identities.get(eve_id, {})
        name = character.get("name") or eve_id
        corp = character.get("corporation_ticker") or ""
        character_total = sum(metrics.values())

        owner = owners.get(eve_id)
        if owner:
            key = ("main", owner["main_eve_id"])
            display = owner["main_name"]
            is_linked = True
        else:
            key = ("char", eve_id)
            display = name
            is_linked = False

        group = groups.setdefault(
            key,
            {
                **{k: 0 for k in METRIC_KEYS},
                "total": 0,
                "character_name": display,
                "is_linked": is_linked,
                "corporation_ticker": corp,
                "characters": [],
                "_top": -1,
            },
        )

        for k in METRIC_KEYS:
            group[k] += metrics[k]

        group["total"] += character_total
        group["characters"].append({"name": name, "total": character_total})

        # show the corp of whoever contributed most to the group
        if character_total > group["_top"]:
            group["_top"] = character_total
            group["corporation_ticker"] = corp

    rows = list(groups.values())
    for row in rows:
        row.pop("_top", None)
        row["characters"].sort(key=lambda x: x["total"], reverse=True)

    rows.sort(key=lambda r: r["total"], reverse=True)
    for i, row in enumerate(rows, start=1):
        row["rank"] = i

    return rows, errors
