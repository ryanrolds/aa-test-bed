"""
Tests for the tracked map admin form
"""

# Django
from django.test import TestCase

from ..admin import TrackedMapForm
from ..models import TrackedMap

MAP_UUID = "550e8400-e29b-41d4-a716-446655440000"


def form_data(**overrides):
    data = {
        "name": "Home",
        "identifier_type": "slug",
        "identifier": "home-map",
        "base_url": "",
        "api_token": "secret-key",
        "is_active": "on",
    }
    data.update(overrides)

    return data


class TestIdentifierChoice(TestCase):
    """One identifier goes in, and only that column comes out."""

    def test_should_default_to_slug(self):
        self.assertEqual(TrackedMapForm().fields["identifier_type"].initial, "slug")

    def test_should_store_a_slug(self):
        form = TrackedMapForm(data=form_data())

        self.assertTrue(form.is_valid(), form.errors)
        tracked_map = form.save()

        self.assertEqual(tracked_map.slug, "home-map")
        self.assertEqual(tracked_map.map_id, "")

    def test_should_store_a_map_id(self):
        form = TrackedMapForm(
            data=form_data(identifier_type="map_id", identifier=MAP_UUID)
        )

        self.assertTrue(form.is_valid(), form.errors)
        tracked_map = form.save()

        self.assertEqual(tracked_map.map_id, MAP_UUID)
        self.assertEqual(tracked_map.slug, "")

    def test_should_trim_surrounding_whitespace(self):
        form = TrackedMapForm(data=form_data(identifier="  home-map  "))

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().slug, "home-map")

    def test_should_clear_the_other_column_when_switching(self):
        tracked_map = TrackedMap.objects.create(name="Home", map_id=MAP_UUID)

        form = TrackedMapForm(
            instance=tracked_map, data=form_data(identifier="now-a-slug")
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        tracked_map.refresh_from_db()
        self.assertEqual(tracked_map.slug, "now-a-slug")
        self.assertEqual(tracked_map.map_id, "")


class TestIdentifierPreselection(TestCase):
    """Editing shows the identifier the map actually uses."""

    def test_should_preselect_slug(self):
        tracked_map = TrackedMap.objects.create(name="Home", slug="home-map")
        form = TrackedMapForm(instance=tracked_map)

        self.assertEqual(form.fields["identifier_type"].initial, "slug")
        self.assertEqual(form.fields["identifier"].initial, "home-map")

    def test_should_preselect_map_id(self):
        tracked_map = TrackedMap.objects.create(name="Home", map_id=MAP_UUID)
        form = TrackedMapForm(instance=tracked_map)

        self.assertEqual(form.fields["identifier_type"].initial, "map_id")
        self.assertEqual(form.fields["identifier"].initial, MAP_UUID)


class TestIdentifierValidation(TestCase):

    def test_should_require_an_identifier(self):
        for value in ("", "   "):
            form = TrackedMapForm(data=form_data(identifier=value))

            self.assertFalse(form.is_valid())
            self.assertEqual(form.errors["identifier"], ["This field is required."])

    def test_should_reject_a_map_id_longer_than_its_column(self):
        limit = TrackedMap._meta.get_field("map_id").max_length
        form = TrackedMapForm(
            data=form_data(identifier_type="map_id", identifier="x" * (limit + 1))
        )

        self.assertFalse(form.is_valid())
        self.assertIn("at most 64 characters", form.errors["identifier"][0])

    def test_should_reject_a_slug_longer_than_its_column(self):
        limit = TrackedMap._meta.get_field("slug").max_length
        form = TrackedMapForm(data=form_data(identifier="y" * (limit + 1)))

        self.assertFalse(form.is_valid())
        # one complaint, not the max_length error plus a bogus "required"
        self.assertEqual(len(form.errors["identifier"]), 1)

    def test_should_accept_a_map_id_at_the_limit(self):
        limit = TrackedMap._meta.get_field("map_id").max_length
        form = TrackedMapForm(
            data=form_data(identifier_type="map_id", identifier="x" * limit)
        )

        self.assertTrue(form.is_valid(), form.errors)
