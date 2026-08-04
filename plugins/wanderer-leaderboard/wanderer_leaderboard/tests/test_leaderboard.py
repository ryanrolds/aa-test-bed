"""
Tests for the event classification, counting and aggregation helpers
"""

# Standard Library
import json
from unittest.mock import patch

# Django
from django.test import TestCase

from ..api import WandererApiError
from ..leaderboard import (
    METRIC_KEYS,
    classify,
    count_for,
    event_datetime,
    month_bounds,
    monthly_leaderboard,
)
from ..models import TrackedMap


class TestClassify(TestCase):

    def test_should_classify_systems(self):
        self.assertEqual(classify("system_added"), ("systems", "created"))
        self.assertEqual(classify("system_updated"), ("systems", "updated"))
        self.assertEqual(classify("systems_removed"), ("systems", "deleted"))

    def test_should_classify_connections(self):
        self.assertEqual(classify("map_connection_added"), ("connections", "created"))
        self.assertEqual(classify("map_connection_updated"), ("connections", "updated"))
        self.assertEqual(classify("map_connection_removed"), ("connections", "deleted"))

    def test_should_classify_signatures(self):
        self.assertEqual(classify("signatures_added"), ("signatures", "created"))
        self.assertEqual(classify("signatures_updated"), ("signatures", "updated"))
        self.assertEqual(classify("signatures_removed"), ("signatures", "deleted"))

    def test_should_ignore_acl_events(self):
        self.assertIsNone(classify("map_acl_added"))

    def test_should_ignore_unknown_events(self):
        self.assertIsNone(classify("character_added"))
        self.assertIsNone(classify("system_renamed"))
        self.assertIsNone(classify(""))
        self.assertIsNone(classify(None))

    def test_should_be_case_insensitive(self):
        self.assertEqual(classify("SYSTEM_ADDED"), ("systems", "created"))


class TestCountFor(TestCase):

    def test_should_count_one_without_event_data(self):
        self.assertEqual(count_for(None), 1)
        self.assertEqual(count_for(""), 1)

    def test_should_count_list_length(self):
        data = json.dumps({"signatures": ["a", "b", "c"]})
        self.assertEqual(count_for(data), 3)

        data = json.dumps({"solar_system_ids": [30000142, 30002187]})
        self.assertEqual(count_for(data), 2)

    def test_should_count_one_for_empty_list(self):
        self.assertEqual(count_for(json.dumps({"signatures": []})), 1)

    def test_should_count_one_for_unrecognized_payload(self):
        self.assertEqual(count_for(json.dumps({"solar_system_id": 30000142})), 1)
        self.assertEqual(count_for(json.dumps(["a", "b"])), 1)

    def test_should_count_a_mapping_that_was_never_serialized(self):
        self.assertEqual(count_for({"signatures": ["a", "b"]}), 2)

    def test_should_count_items_in_the_api_display_string(self):
        # the shape GET /api/map/audit actually returns
        event_data = (
            "XHQ-7V: ZMK-785, BNJ-940, OSV-920, WIH-964, LWI-780, SAX-322, "
            "HMH-090, YYU-568, ERZ-910, WGM-914, EAB-504, GDY-048, ILU-626, "
            "LCJ-073, ELN-120, AIR-956, IAW-376, LUB-630"
        )
        self.assertEqual(count_for(event_data), 18)

    def test_should_not_count_the_system_prefix(self):
        self.assertEqual(count_for("XHQ-7V: ZMK-785"), 1)

    def test_should_count_one_for_a_bare_subject(self):
        # system_added renders as just the system name
        self.assertEqual(count_for("XHQ-7V"), 1)
        self.assertEqual(count_for("not json"), 1)

    def test_should_count_one_for_an_empty_payload(self):
        self.assertEqual(count_for("XHQ-7V:"), 1)
        self.assertEqual(count_for("XHQ-7V: , ,"), 1)


class TestMonthBounds(TestCase):

    def test_should_bound_a_normal_month(self):
        start, end, label = month_bounds(2026, 3)
        self.assertEqual((start.year, start.month, start.day), (2026, 3, 1))
        self.assertEqual((end.year, end.month, end.day), (2026, 4, 1))
        self.assertEqual(label, "March 2026")

    def test_should_roll_over_december(self):
        start, end, label = month_bounds(2026, 12)
        self.assertEqual((start.year, start.month), (2026, 12))
        self.assertEqual((end.year, end.month, end.day), (2027, 1, 1))
        self.assertEqual(label, "December 2026")


class TestMetricKeys(TestCase):

    def test_should_have_nine_metrics(self):
        self.assertEqual(len(METRIC_KEYS), 9)
        self.assertIn("systems_created", METRIC_KEYS)
        self.assertIn("signatures_deleted", METRIC_KEYS)


class TestEventDatetime(TestCase):

    def test_should_parse_zulu_timestamps(self):
        parsed = event_datetime("2026-03-05T12:00:00Z")
        self.assertEqual((parsed.year, parsed.month, parsed.day), (2026, 3, 5))
        self.assertEqual(parsed.utcoffset().total_seconds(), 0)

    def test_should_parse_offset_timestamps(self):
        parsed = event_datetime("2026-03-05T12:00:00+02:00")
        self.assertEqual(parsed.utcoffset().total_seconds(), 7200)

    def test_should_assume_utc_when_naive(self):
        parsed = event_datetime("2026-03-05T12:00:00")
        self.assertEqual(parsed.utcoffset().total_seconds(), 0)

    def test_should_return_none_for_junk(self):
        self.assertIsNone(event_datetime(None))
        self.assertIsNone(event_datetime(""))
        self.assertIsNone(event_datetime("not a timestamp"))


def _event(name, when, eve_id="1001", data=None, name_of="Pilot One", corp="ABC"):
    return {
        "event_name": name,
        "event_data": data,
        "inserted_at": when,
        "entity_type": "map",
        "character": {
            "eve_id": eve_id,
            "name": name_of,
            "corporation_ticker": corp,
        },
    }


class TestMonthlyLeaderboard(TestCase):

    def setUp(self):
        self.map = TrackedMap.objects.create(
            name="Home", slug="home-map", api_token="secret-key"
        )

    def _run(self, events, year=2026, month=3):
        with patch("wanderer_leaderboard.leaderboard.api.audit_events") as mock:
            mock.return_value = events

            return monthly_leaderboard([self.map], year, month)

    def test_should_count_and_rank_characters(self):
        rows, errors = self._run(
            [
                _event("system_added", "2026-03-05T12:00:00Z"),
                _event("system_added", "2026-03-06T12:00:00Z"),
                _event(
                    "signatures_added",
                    "2026-03-07T12:00:00Z",
                    data=json.dumps({"signatures": ["a", "b", "c"]}),
                ),
                _event(
                    "connection_removed",
                    "2026-03-08T12:00:00Z",
                    eve_id="1002",
                    name_of="Pilot Two",
                    corp="XYZ",
                ),
            ]
        )

        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 2)

        first, second = rows
        self.assertEqual(first["rank"], 1)
        self.assertEqual(first["character_name"], "Pilot One")
        self.assertEqual(first["corporation_ticker"], "ABC")
        self.assertEqual(first["systems_created"], 2)
        self.assertEqual(first["signatures_created"], 3)
        self.assertEqual(first["total"], 5)
        self.assertFalse(first["is_linked"])

        self.assertEqual(second["character_name"], "Pilot Two")
        self.assertEqual(second["connections_deleted"], 1)
        self.assertEqual(second["total"], 1)

    def test_should_drop_events_outside_the_month(self):
        rows, _ = self._run(
            [
                _event("system_added", "2026-02-28T23:59:59Z"),
                _event("system_added", "2026-03-01T00:00:00Z"),
                _event("system_added", "2026-04-01T00:00:00Z"),
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["systems_created"], 1)

    def test_should_ignore_unclassifiable_and_anonymous_events(self):
        rows, _ = self._run(
            [
                _event("map_acl_added", "2026-03-05T12:00:00Z"),
                _event("character_added", "2026-03-05T12:00:00Z"),
                _event("system_added", "not a timestamp"),
                {
                    "event_name": "system_added",
                    "inserted_at": "2026-03-05T12:00:00Z",
                    "character": {},
                },
            ]
        )

        self.assertEqual(rows, [])

    def test_should_report_fetch_failures_without_failing(self):
        with patch("wanderer_leaderboard.leaderboard.api.audit_events") as mock:
            mock.side_effect = WandererApiError("Home: API key rejected by Wanderer")
            rows, errors = monthly_leaderboard([self.map], 2026, 3)

        self.assertEqual(rows, [])
        self.assertEqual(errors, ["Home: API key rejected by Wanderer"])
