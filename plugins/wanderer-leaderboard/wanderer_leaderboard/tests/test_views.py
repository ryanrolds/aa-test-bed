"""
Tests for the leaderboard view
"""

# Standard Library
import json
from unittest.mock import patch

# Django
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

# Alliance Auth
from allianceauth.tests.auth_utils import AuthUtils

from ..api import WandererApiError
from ..models import TrackedMap
from ..views import _selected_map
from . import NO_REDIS_CACHE


class TestSelectedMap(TestCase):

    def setUp(self):
        self.first = TrackedMap.objects.create(
            name="Alpha", slug="alpha", base_url="https://wanderer.example.com"
        )
        self.second = TrackedMap.objects.create(
            name="Beta", slug="beta", base_url="https://wanderer.example.com"
        )
        self.maps = list(TrackedMap.objects.active())

    def test_should_return_the_requested_map(self):
        self.assertEqual(_selected_map(self.maps, str(self.second.pk)), self.second)

    def test_should_fall_back_to_the_first_map(self):
        self.assertEqual(_selected_map(self.maps, ""), self.first)
        self.assertEqual(_selected_map(self.maps, "not-a-pk"), self.first)
        self.assertEqual(_selected_map(self.maps, "99999"), self.first)

    def test_should_return_none_without_any_maps(self):
        self.assertIsNone(_selected_map([], "1"))


@override_settings(CACHES=NO_REDIS_CACHE)
class TestIndex(TestCase):

    def setUp(self):
        cache.clear()

        # Alliance Auth sends users without a main character back to the
        # dashboard before the view ever runs, so build a complete one.
        self.user = AuthUtils.create_user("mapper")
        AuthUtils.add_main_character_2(self.user, "Pilot One", 1001)
        self.user = AuthUtils.add_permission_to_user_by_name(
            "wanderer_leaderboard.basic_access", self.user
        )
        self.client.force_login(self.user)

        self.first = TrackedMap.objects.create(
            name="Alpha", slug="alpha", base_url="https://wanderer.example.com"
        )
        self.second = TrackedMap.objects.create(
            name="Beta", slug="beta", base_url="https://wanderer.example.com"
        )

    def test_should_fetch_only_the_selected_map(self):
        """One page view, one map, one call to a slow endpoint."""
        with patch("wanderer_leaderboard.leaderboard.api.audit_events") as mock:
            mock.return_value = []
            response = self.client.get(reverse("wanderer_leaderboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock.call_count, 1)
        self.assertEqual(mock.call_args.args[0], self.first)
        self.assertEqual(response.context["selected_map"], self.first)

    def test_should_honour_the_requested_map(self):
        with patch("wanderer_leaderboard.leaderboard.api.audit_events") as mock:
            mock.return_value = []
            response = self.client.get(
                reverse("wanderer_leaderboard:index"), {"map": self.second.pk}
            )

        self.assertEqual(mock.call_args.args[0], self.second)
        self.assertEqual(response.context["selected_map"], self.second)

    def test_should_not_fetch_anything_without_maps(self):
        TrackedMap.objects.all().delete()

        with patch("wanderer_leaderboard.leaderboard.api.audit_events") as mock:
            response = self.client.get(reverse("wanderer_leaderboard:index"))

        self.assertEqual(response.status_code, 200)
        mock.assert_not_called()
        self.assertIsNone(response.context["selected_map"])

    def test_should_render_a_row_with_all_nine_counts(self):
        """The table body is generated from the row, so it cannot drift from
        the headers the way nine hand-written cells could."""
        today = timezone.now().date()
        when = f"{today.year:04d}-{today.month:02d}-01T12:00:00Z"
        events = [
            {
                "event_name": "signatures_added",
                "event_data": json.dumps({"signatures": ["a", "b", "c"]}),
                "inserted_at": when,
                "character": {
                    "eve_id": "1001",
                    "name": "Pilot One",
                    "corporation_ticker": "ABC",
                },
            }
        ]

        with patch("wanderer_leaderboard.leaderboard.api.audit_events") as mock:
            mock.return_value = events
            response = self.client.get(reverse("wanderer_leaderboard:index"))

        row = response.context["rows"][0]
        self.assertEqual(row.metric_groups, [[0, 0, 0], [0, 0, 0], [3, 0, 0]])

        body = response.content.decode()
        self.assertIn("Pilot One", body)
        # nine metric cells plus the total
        self.assertEqual(body.count("<td"), 12)

    def test_should_show_a_fetch_failure_on_the_page(self):
        with patch("wanderer_leaderboard.leaderboard.api.audit_events") as mock:
            mock.side_effect = WandererApiError("Alpha: API key rejected by Wanderer")
            response = self.client.get(reverse("wanderer_leaderboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["error"], "Alpha: API key rejected by Wanderer"
        )
        self.assertEqual(response.context["rows"], [])

    def test_should_require_the_permission(self):
        self.client.logout()
        without_permission = AuthUtils.create_user("nobody")
        AuthUtils.add_main_character_2(without_permission, "Pilot Two", 1002)
        self.client.force_login(without_permission)

        response = self.client.get(reverse("wanderer_leaderboard:index"))

        self.assertNotEqual(response.status_code, 200)
