import json
from datetime import date
from importlib import import_module
from types import SimpleNamespace

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TestCase

from base.test_utils import add_page, home_page
from .models import RoadTripDayPage, RoadTripIndexPage, RoadTripPage


migration = import_module("roadtrips.migrations.0015_clear_manual_day_distances")


class ManualDistanceCleanupTests(SimpleTestCase):
    def test_cleanup_preserves_total_and_other_fields_in_both_storage_formats(self):
        raw = [
            {"type": "text", "id": "text-id", "value": "Příběh"},
            {
                "type": "day_summary",
                "id": "summary-id",
                "value": {
                    "distance_km": "42",
                    "total_distance_km": "142",
                    "countries": ["Česko"],
                    "seas": ["Baltské moře"],
                },
            },
        ]
        expected = json.loads(json.dumps(raw))
        del expected[1]["value"]["distance_km"]
        self.assertEqual(migration.remove_manual_distance(raw), expected)
        self.assertEqual(
            json.loads(migration.remove_manual_distance(json.dumps(raw))), expected
        )
        self.assertEqual(migration.remove_manual_distance(expected), expected)
        self.assertIn("distance_km", raw[1]["value"])

    def test_unexpected_data_is_preserved(self):
        for value in (
            None,
            {},
            "invalid json",
            "null",
            [],
            [None],
            [{"type": "day_summary", "value": None}],
        ):
            with self.subTest(value=value):
                self.assertEqual(migration.remove_manual_distance(value), value)


class ManualDistanceDatabaseMigrationTests(TestCase):
    def test_cleanup_removes_manual_values_from_live_draft_and_all_day_revisions(self):
        home = home_page()
        index = add_page(home, RoadTripIndexPage, title="Cesty", slug="cesty")
        trip = add_page(
            index,
            RoadTripPage,
            title="Výlet",
            slug="vylet",
            intro="Výlet",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
        )
        days = [
            add_page(
                trip,
                RoadTripDayPage,
                title=f"Den {number}",
                slug=f"den-{number}",
                day_number=number,
                date=date(2026, 7, number),
                intro="Zápis",
                live=number == 1,
            )
            for number in (1, 2)
        ]
        raw = [
            {"type": "text", "id": "text-id", "value": "Ponechat příběh"},
            {
                "type": "day_summary",
                "id": "summary-id",
                "value": {
                    "heading": "Přehled dne",
                    "distance_km": "42",
                    "total_distance_km": "142",
                    "note": "Ponechat poznámku",
                },
            },
        ]
        expected = json.loads(json.dumps(raw))
        del expected[1]["value"]["distance_km"]
        revisions = []
        for day in days:
            RoadTripDayPage.objects.filter(pk=day.pk).update(content=raw)
            for serialized in (False, True):
                revision = day.save_revision()
                revision.content["content"] = json.dumps(raw) if serialized else raw
                revision.save(update_fields=["content"])
                revisions.append((revision, serialized))
        unrelated = home.save_revision()
        unrelated.content["content"] = raw
        unrelated.save(update_fields=["content"])

        apps = (
            MigrationExecutor(connection)
            .loader.project_state([("roadtrips", "0014_remove_manual_day_distance")])
            .apps
        )
        migration.remove_manual_distances(apps, SimpleNamespace(connection=connection))

        for day in days:
            was_live = day.live
            day.refresh_from_db()
            self.assertEqual(list(day.content.raw_data), expected)
            self.assertEqual(day.live, was_live)
        for revision, serialized in revisions:
            revision.refresh_from_db()
            content = revision.content["content"]
            self.assertEqual(json.loads(content) if serialized else content, expected)
        unrelated.refresh_from_db()
        self.assertEqual(unrelated.content["content"], raw)
