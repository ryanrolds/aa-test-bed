"""Monthly leaderboard aggregation from Wanderer's audit API"""

# Standard Library
import calendar
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Django
from django.core.cache import cache

# Alliance Auth
from allianceauth.authentication.models import CharacterOwnership

from . import api, app_settings

CATEGORIES = ("systems", "connections", "signatures")
ACTIONS = ("created", "updated", "deleted")
METRIC_KEYS = [f"{category}_{action}" for category in CATEGORIES for action in ACTIONS]

# bump when LeaderboardRow changes shape, so old pickles are not read back
ROWS_CACHE_VERSION = 1

# event_data lists whose length is the real count, one event covers many items.
# Only plural keys belong here: {"solar_system_id": 30003731} is a scalar naming
# one system, which the fallback already counts as 1.
_LIST_COUNT_KEYS = ("signatures", "solar_system_ids")


def classify(event_name: str | None) -> tuple[str, str] | None:
    """The (category, action) an audit event counts towards, or None to ignore it.

    Both halves are first-match-wins substring tests, so the order matters and
    runs most specific first: "system_signature_added" is a signature event, not
    a system one. Matching on fragments rather than whole names is deliberate —
    Wanderer keeps adding event name variants, and they land in the right column
    without a code change.
    """
    name = (event_name or "").lower()
    if "acl" in name:
        return None

    if "signature" in name:
        category = "signatures"
    elif "connection" in name:
        category = "connections"
    elif "system" in name:
        category = "systems"
    else:
        return None

    if "add" in name or "creat" in name:
        action = "created"
    elif "updat" in name:
        action = "updated"
    elif "remov" in name or "delet" in name:
        action = "deleted"
    else:
        return None

    return category, action


def _count_from_mapping(data: dict) -> int:
    for key in _LIST_COUNT_KEYS:
        value = data.get(key)
        if isinstance(value, list):
            return max(1, len(value))

    return 1


def _count_from_display_string(event_data: str) -> int:
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


def count_for(event_data) -> int:
    """How many things a single audit event actually covers.

    The audit API flattens event_data to a display string before returning it,
    so that is the shape this normally sees. The JSON branch handles the
    unflattened mapping Wanderer stores internally, in case a future version
    stops flattening it.
    """
    if not event_data:
        return 1

    if isinstance(event_data, dict):
        return _count_from_mapping(event_data)

    if not isinstance(event_data, str):
        # a list, a number, anything else: one event, one thing
        return 1

    try:
        data = json.loads(event_data)
    except ValueError:
        return _count_from_display_string(event_data)

    if isinstance(data, dict):
        return _count_from_mapping(data)

    return 1


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    """The half-open UTC interval [start, end) covering one calendar month."""
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

    return start, end


def month_label(year: int, month: int) -> str:
    """One month, named the way it is shown to a user."""
    return f"{calendar.month_name[month]} {year}"


def event_datetime(value) -> datetime | None:
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


@dataclass(frozen=True)
class Main:
    """The Alliance Auth main an audit character belongs to."""

    name: str
    eve_id: int


@dataclass
class CharacterContribution:
    """One character's share of a row's total."""

    name: str
    total: int


@dataclass
class LeaderboardRow:
    """One person on the board: an Auth main and its alts, or a lone character.

    Metrics live in a Counter keyed by METRIC_KEYS, and the template walks
    `metric_groups` rather than naming the nine columns itself, so adding a
    category or an action changes the table without touching the HTML.
    """

    character_name: str
    is_linked: bool
    corporation_ticker: str = ""
    characters: list[CharacterContribution] = field(default_factory=list)
    metrics: Counter = field(default_factory=Counter)
    rank: int = 0

    # the biggest single contribution seen so far, which decides whose corp
    # ticker the row shows. Never rendered.
    _top_contribution: int = field(default=-1, init=False, repr=False)

    @property
    def total(self) -> int:
        return sum(self.metrics.values())

    @property
    def metric_groups(self) -> list[list[int]]:
        """The nine counts as three rows of three, in CATEGORIES x ACTIONS order."""
        return [
            [self.metrics[f"{category}_{action}"] for action in ACTIONS]
            for category in CATEGORIES
        ]

    def add(self, name: str, corporation_ticker: str, metrics: Counter) -> None:
        """Fold one character's counts into this row."""
        self.metrics.update(metrics)

        total = sum(metrics.values())
        self.characters.append(CharacterContribution(name=name, total=total))

        if total > self._top_contribution:
            self._top_contribution = total
            self.corporation_ticker = corporation_ticker

    def sort_characters(self) -> None:
        self.characters.sort(key=lambda char: (-char.total, char.name.lower()))


def _resolve_mains(eve_ids) -> dict[int, Main]:
    """The Auth main behind each audit character id, for those Auth knows."""
    ownerships = CharacterOwnership.objects.filter(
        character__character_id__in=eve_ids
    ).select_related("character", "user__profile__main_character")

    mains = {}
    for ownership in ownerships:
        main = ownership.user.profile.main_character
        if main:
            mains[ownership.character.character_id] = Main(
                name=main.character_name, eve_id=main.character_id
            )

    return mains


def _per_character_counts(tracked_map, year, month) -> tuple[dict, dict]:
    """Per-character metric counters and identities for one map and month.

    Raises WandererApiError if the map's audit log cannot be read.
    """
    start, end = month_bounds(year, month)
    events = api.audit_events(tracked_map)

    counts = defaultdict(Counter)
    identities = {}

    for event in events:
        classified = classify(event.get("event_name"))
        if not classified:
            continue

        # the API window is relative (3 months), so the month is ours to cut
        occurred = event_datetime(event.get("inserted_at"))
        if occurred is None or not start <= occurred < end:
            continue

        character = event.get("character") or {}
        eve_id = character.get("eve_id")
        if not str(eve_id or "").isdigit():
            continue

        eve_id = int(eve_id)

        # audit events arrive newest first, so the first name seen for a
        # character is its current one
        identities.setdefault(eve_id, character)

        category, action = classified
        counts[eve_id][f"{category}_{action}"] += count_for(event.get("event_data"))

    return counts, identities


def _rows_cache_key(tracked_map, year, month):
    return (
        f"wanderer_leaderboard:rows:{ROWS_CACHE_VERSION}:{tracked_map.pk}:"
        f"{year:04d}-{month:02d}:{api.credentials_fingerprint(tracked_map)}"
    )


def _build_rows(tracked_map, year, month) -> list[LeaderboardRow]:
    counts, identities = _per_character_counts(tracked_map, year, month)
    if not counts:
        return []

    mains = _resolve_mains(counts.keys())

    rows = {}
    for eve_id, metrics in counts.items():
        character = identities.get(eve_id, {})
        name = character.get("name") or str(eve_id)
        corporation_ticker = character.get("corporation_ticker") or ""

        main = mains.get(eve_id)
        key = ("main", main.eve_id) if main else ("character", eve_id)

        row = rows.get(key)
        if row is None:
            row = LeaderboardRow(
                character_name=main.name if main else name,
                is_linked=main is not None,
            )
            rows[key] = row

        row.add(name=name, corporation_ticker=corporation_ticker, metrics=metrics)

    ranked = sorted(
        rows.values(), key=lambda row: (-row.total, row.character_name.lower())
    )
    for rank, row in enumerate(ranked, start=1):
        row.rank = rank
        row.sort_characters()

    return ranked


def monthly_leaderboard(
    tracked_map, year: int, month: int, use_cache: bool = True
) -> list[LeaderboardRow]:
    """Ranked rows for one map and one month.

    One map per call, deliberately: the audit endpoint is slow and this runs
    inside the request, so a page that read every configured map would stack
    their timeouts end to end.

    The finished rows are cached, not just the events they came from. One fetch
    covers three months, so without this every page view re-classified and
    re-totalled the whole window to render one month of it. The cost is that a
    character newly linked to an Auth main keeps its own row until the entry
    expires.

    Raises WandererApiError if the map's audit log cannot be read.
    """
    cache_key = _rows_cache_key(tracked_map, year, month)
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    rows = _build_rows(tracked_map, year, month)

    if use_cache:
        cache.set(cache_key, rows, app_settings.CACHE_TTL)

    return rows
