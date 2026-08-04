"""
Tests for the Wanderer map API client
"""

# Standard Library
from unittest.mock import patch

# Third Party
import requests

# Django
from django.core.cache import cache
from django.test import TestCase, override_settings

from .. import app_settings
from ..api import WandererApiError, audit_events, base_url_for
from ..models import TrackedMap

# the project settings point at Redis, which the suite doesn't require
LOCMEM_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}


class FakeResponse:

    def __init__(
        self, status_code=200, payload=None, raises=False, text="", headers=None
    ):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"data": []}
        self._raises = raises
        self.text = text
        self.headers = headers if headers is not None else {}

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        if self._raises:
            raise ValueError("not json")

        return self._payload


@override_settings(CACHES=LOCMEM_CACHE)
class ApiTestCase(TestCase):

    def setUp(self):
        cache.clear()
        self.map = TrackedMap.objects.create(
            name="Home", slug="home-map", api_token="secret-key"
        )


class TestBaseUrl(ApiTestCase):

    def test_should_use_the_configured_default(self):
        self.assertEqual(base_url_for(self.map), app_settings.WANDERER_BASE_URL)

    def test_should_prefer_the_per_map_override(self):
        self.map.base_url = "https://wanderer.example.com/"
        self.assertEqual(base_url_for(self.map), "https://wanderer.example.com")


class TestAuditEvents(ApiTestCase):

    def test_should_send_the_key_as_a_bearer_token(self):
        with patch("wanderer_leaderboard.api.requests.get") as mock_get:
            mock_get.return_value = FakeResponse(payload={"data": [{"a": 1}]})
            events = audit_events(self.map)

        self.assertEqual(events, [{"a": 1}])
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret-key")
        self.assertEqual(kwargs["params"]["slug"], "home-map")
        self.assertEqual(kwargs["params"]["period"], "3M")

    def test_should_prefer_map_id_over_slug(self):
        self.map.map_id = "550e8400-e29b-41d4-a716-446655440000"
        with patch("wanderer_leaderboard.api.requests.get") as mock_get:
            mock_get.return_value = FakeResponse()
            audit_events(self.map)

        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["map_id"], self.map.map_id)
        self.assertNotIn("slug", kwargs["params"])

    def test_should_reject_a_map_without_a_key(self):
        self.map.api_token = ""
        with self.assertRaises(WandererApiError) as ctx:
            audit_events(self.map)

        self.assertIn("no API key", str(ctx.exception))

    def test_should_reject_a_map_without_slug_or_id(self):
        self.map.slug = ""
        with self.assertRaises(WandererApiError):
            audit_events(self.map)

    def test_should_report_a_rejected_key(self):
        for status in (401, 403):
            with patch("wanderer_leaderboard.api.requests.get") as mock_get:
                mock_get.return_value = FakeResponse(status_code=status)
                with self.assertRaises(WandererApiError) as ctx:
                    audit_events(self.map, use_cache=False)

            self.assertIn("API key rejected", str(ctx.exception))

    def test_should_report_a_missing_map(self):
        with patch("wanderer_leaderboard.api.requests.get") as mock_get:
            mock_get.return_value = FakeResponse(status_code=404)
            with self.assertRaises(WandererApiError) as ctx:
                audit_events(self.map)

        self.assertIn("not found", str(ctx.exception))

    def test_should_report_other_http_errors(self):
        with patch("wanderer_leaderboard.api.requests.get") as mock_get:
            mock_get.return_value = FakeResponse(status_code=503)
            with self.assertRaises(WandererApiError) as ctx:
                audit_events(self.map)

        self.assertIn("HTTP 503", str(ctx.exception))

    def test_should_report_transport_failures(self):
        with patch("wanderer_leaderboard.api.requests.get") as mock_get:
            mock_get.side_effect = requests.ConnectionError("refused")
            with self.assertRaises(WandererApiError) as ctx:
                audit_events(self.map)

        self.assertIn("refused", str(ctx.exception))

    def test_should_reject_non_json_and_odd_shapes(self):
        with patch("wanderer_leaderboard.api.requests.get") as mock_get:
            mock_get.return_value = FakeResponse(raises=True)
            with self.assertRaises(WandererApiError):
                audit_events(self.map)

        with patch("wanderer_leaderboard.api.requests.get") as mock_get:
            mock_get.return_value = FakeResponse(payload={"data": "nope"})
            with self.assertRaises(WandererApiError):
                audit_events(self.map)

    def test_should_cache_between_calls(self):
        with patch("wanderer_leaderboard.api.requests.get") as mock_get:
            mock_get.return_value = FakeResponse(payload={"data": [{"a": 1}]})
            audit_events(self.map)
            audit_events(self.map)

        self.assertEqual(mock_get.call_count, 1)

    def test_should_bypass_the_cache_when_asked(self):
        with patch("wanderer_leaderboard.api.requests.get") as mock_get:
            mock_get.return_value = FakeResponse(payload={"data": [{"a": 1}]})
            audit_events(self.map)
            audit_events(self.map, use_cache=False)

        self.assertEqual(mock_get.call_count, 2)


class TestErrorDetail(ApiTestCase):
    """The short message goes on the page, `detail` goes in the log."""

    def _failure(self, **response_kwargs):
        with patch("wanderer_leaderboard.api.requests.get") as mock_get:
            mock_get.return_value = FakeResponse(**response_kwargs)
            with self.assertRaises(WandererApiError) as ctx:
                audit_events(self.map, use_cache=False)

        return ctx.exception

    def test_should_describe_the_failed_request(self):
        exc = self._failure(
            status_code=500,
            text="Something went wrong",
            headers={"Content-Type": "text/plain"},
        )

        # short message for the user-facing alert
        self.assertEqual(str(exc), "Home: API returned HTTP 500")

        # everything needed to debug it, for the log
        self.assertIn("map='Home'", exc.detail)
        self.assertIn("url=http://wanderer.example.com/api/map/audit", exc.detail)
        self.assertIn("slug=home-map", exc.detail)
        self.assertIn("period=3M", exc.detail)
        self.assertIn("status=500", exc.detail)
        self.assertIn("content_type=text/plain", exc.detail)
        self.assertIn("body=Something went wrong", exc.detail)

    def test_should_never_leak_the_api_key(self):
        exc = self._failure(status_code=401, text="unauthorized")

        self.assertNotIn(self.map.api_token, exc.detail)
        self.assertNotIn("Authorization", exc.detail)
        self.assertNotIn("Bearer", exc.detail)

    def test_should_collapse_and_trim_a_long_body(self):
        exc = self._failure(status_code=500, text="<html>\n  " + "x" * 500)

        self.assertIn("…", exc.detail)
        self.assertNotIn("\n", exc.detail)
        self.assertLess(len(exc.detail), 600)

    def test_should_mark_an_empty_body(self):
        exc = self._failure(status_code=500, text="")

        self.assertIn("body=<empty>", exc.detail)

    def test_should_describe_a_transport_failure(self):
        with patch("wanderer_leaderboard.api.requests.get") as mock_get:
            mock_get.side_effect = requests.ConnectionError("name resolution failed")
            with self.assertRaises(WandererApiError) as ctx:
                audit_events(self.map, use_cache=False)

        self.assertIn(
            "url=http://wanderer.example.com/api/map/audit", ctx.exception.detail
        )
        self.assertIn("exception=ConnectionError", ctx.exception.detail)
        self.assertNotIn("status=", ctx.exception.detail)

    def test_should_describe_an_unexpected_payload(self):
        exc = self._failure(status_code=200, payload={"data": "nope"})

        self.assertEqual(str(exc), "Home: unexpected API response shape")
        self.assertIn("data_type=str", exc.detail)

    def test_should_default_detail_to_the_message(self):
        self.map.api_token = ""
        with self.assertRaises(WandererApiError) as ctx:
            audit_events(self.map, use_cache=False)

        self.assertEqual(ctx.exception.detail, str(ctx.exception))
