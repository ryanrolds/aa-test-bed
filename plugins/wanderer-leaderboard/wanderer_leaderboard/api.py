"""Client for Wanderer's map API

The leaderboard reads `GET /api/map/audit`, authenticated with the per-map API
key stored on TrackedMap. That endpoint only accepts a *relative* period
(1H/1D/1W/1M/2M/3M), so there is no way to ask it for a specific calendar month:
we pull the widest window and filter locally. Anything older than the window is
simply not retrievable.
"""

# Standard Library
import logging

# Third Party
import requests

# Django
from django.core.cache import cache

from . import app_settings

logger = logging.getLogger(__name__)

AUDIT_PATH = "/api/map/audit"

# widest window the API offers
AUDIT_PERIOD = "3M"
AUDIT_PERIOD_MONTHS = 3

# bump when the shape of a cached entry changes
CACHE_VERSION = 1


# enough of an error body to identify the failure, not enough to flood the log
BODY_EXCERPT_CHARS = 300


class WandererApiError(Exception):
    """A map's audit log could not be fetched.

    str() stays short because the leaderboard page shows it to users verbatim.
    `detail` carries the request context — url, params, status, response body —
    for the log, which is where a failing map actually gets diagnosed. Neither
    ever contains the API key.
    """

    def __init__(self, message, detail=None):
        super().__init__(message)
        self.detail = detail or message


def base_url_for(tracked_map):
    return (tracked_map.base_url or app_settings.WANDERER_BASE_URL).rstrip("/")


def _map_params(tracked_map):
    # the API takes either map_id or slug; prefer the explicit uuid
    if tracked_map.map_id:
        return {"map_id": tracked_map.map_id}

    if tracked_map.slug:
        return {"slug": tracked_map.slug}

    raise WandererApiError(f"{tracked_map.name}: no map id or slug configured")


def _cache_key(tracked_map, period):
    return f"wanderer_leaderboard:audit:{CACHE_VERSION}:{tracked_map.pk}:{period}"


def _body_excerpt(response):
    """The response body on one line, trimmed. Wanderer answers a failed audit
    request with plain text ("Something went wrong") as often as with JSON, so
    this is frequently the only thing that distinguishes one 500 from another."""
    body = " ".join((response.text or "").split())
    if not body:
        return "<empty>"

    if len(body) > BODY_EXCERPT_CHARS:
        return f"{body[:BODY_EXCERPT_CHARS]}… ({len(body)} chars)"

    return body


def _request_detail(tracked_map, url, params, response=None, exc=None):
    """Log-facing context for a failed fetch.

    Only the query params go in, never the Authorization header — the whole
    point of a detailed log line is that it can be pasted into a bug report.
    """
    bits = [
        f"map={tracked_map.name!r} (pk={tracked_map.pk})",
        f"url={url}",
        f"params={{{', '.join(f'{k}={v}' for k, v in sorted(params.items()))}}}",
    ]

    if response is not None:
        bits.append(f"status={response.status_code}")

        content_type = response.headers.get("Content-Type")
        if content_type:
            bits.append(f"content_type={content_type}")

        elapsed = getattr(response, "elapsed", None)
        if elapsed is not None:
            bits.append(f"elapsed={elapsed.total_seconds():.2f}s")

        bits.append(f"body={_body_excerpt(response)}")

    if exc is not None:
        bits.append(f"exception={type(exc).__name__}: {exc}")

    return " ".join(bits)


def _unwrap(response, tracked_map, detail):
    try:
        payload = response.json()
    except ValueError as exc:
        raise WandererApiError(
            f"{tracked_map.name}: API returned non-JSON response",
            detail=detail(response=response, exc=exc),
        ) from exc

    events = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(events, list):
        raise WandererApiError(
            f"{tracked_map.name}: unexpected API response shape",
            detail=(
                f"{detail(response=response)} "
                f"payload_type={type(payload).__name__} "
                f"data_type={type(events).__name__}"
            ),
        )

    return events


def audit_events(tracked_map, period=AUDIT_PERIOD, use_cache=True):
    """Raw audit events for one map, as returned by the API.

    Each event carries event_name, event_data, inserted_at and an embedded
    character (eve_id, name, corporation_ticker, alliance_ticker).
    """
    if not tracked_map.api_token:
        raise WandererApiError(f"{tracked_map.name}: no API key configured")

    cache_key = _cache_key(tracked_map, period)
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    params = _map_params(tracked_map)
    params["period"] = period
    url = base_url_for(tracked_map) + AUDIT_PATH

    def detail(**kwargs):
        return _request_detail(tracked_map, url, params, **kwargs)

    try:
        response = requests.get(
            url,
            params=params,
            headers={
                "Authorization": f"Bearer {tracked_map.api_token}",
                "Accept": "application/json",
            },
            timeout=app_settings.API_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise WandererApiError(
            f"{tracked_map.name}: {exc}", detail=detail(exc=exc)
        ) from exc

    if response.status_code in (401, 403):
        raise WandererApiError(
            f"{tracked_map.name}: API key rejected by Wanderer",
            detail=detail(response=response),
        )

    if response.status_code == 404:
        # a wrong base_url reaches something that isn't Wanderer and 404s too,
        # so the url in the detail matters as much as the status
        raise WandererApiError(
            f"{tracked_map.name}: map not found at {url}",
            detail=detail(response=response),
        )

    if not response.ok:
        raise WandererApiError(
            f"{tracked_map.name}: API returned HTTP {response.status_code}",
            detail=detail(response=response),
        )

    events = _unwrap(response, tracked_map, detail)
    logger.debug("fetched %d audit events for %s", len(events), tracked_map.name)

    if use_cache:
        cache.set(cache_key, events, app_settings.CACHE_TTL)

    return events
