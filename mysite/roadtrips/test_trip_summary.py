from datetime import date
from decimal import Decimal

from django.test import TestCase

from base.test_utils import add_page, home_page
from .blocks import RoadTripSummaryBlock
from .models import RoadTripDayPage, RoadTripIndexPage, RoadTripPage


class TripSummaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.index = add_page(
            home_page(), RoadTripIndexPage, title="Cesty", slug="cesty"
        )
        cls.trip = add_page(
            cls.index,
            RoadTripPage,
            title="Na sever",
            slug="na-sever",
            intro="Výprava",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 10),
            content=[
                ("text", "<p>Příběh celé výpravy.</p>"),
                (
                    "trip_summary",
                    {
                        "heading": "Přehled autovandru",
                        "route": "Praha → Oslo → Praha",
                        "driving_time": "32 h",
                        "extra_items": [{"label": "Trajekty", "value": "3 plavby"}],
                        "note": "Cesta plná zážitků.",
                    },
                ),
            ],
        )
        # Insert the later day first to test chronological aggregation.
        cls.second = cls.add_day(
            2, "425.5", ["německo", " Dánsko "], ["baltské moře", "Severní moře"]
        )
        cls.first = cls.add_day(1, "100", ["Česko", "Německo"], ["Baltské moře"])
        cls.draft = cls.add_day(3, "999", ["Norsko"], ["Norské moře"], live=False)

    @classmethod
    def add_day(cls, number, total, countries, seas, live=True):
        return add_page(
            cls.trip,
            RoadTripDayPage,
            title=f"Den {number}",
            slug=f"den-{number}",
            day_number=number,
            date=date(2026, 7, number),
            intro="Na cestě",
            live=live,
            content=[
                (
                    "day_summary",
                    {
                        "heading": "Přehled dne",
                        "total_distance_km": Decimal(total),
                        "countries": countries,
                        "seas": seas,
                    },
                )
            ],
        )

    def test_uses_latest_cumulative_distance_without_summing(self):
        self.assertEqual(
            self.trip.get_trip_summary()["total_distance_km"], Decimal("425.5")
        )

    def test_places_are_unique_in_order_of_visit(self):
        summary = self.trip.get_trip_summary()
        self.assertEqual(summary["countries"], ["Česko", "Německo", "Dánsko"])
        self.assertEqual(summary["seas"], ["Baltské moře", "Severní moře"])

    def test_duration_includes_start_and_end_dates(self):
        self.assertEqual(self.trip.get_trip_summary()["duration_days"], 10)
        self.trip.end_date = self.trip.start_date
        self.assertEqual(self.trip.get_trip_summary()["duration_days"], 1)

    def test_empty_trip_shows_dates_without_inventing_mileage_or_places(self):
        self.first.unpublish()
        self.second.unpublish()
        response = self.client.get(self.trip.url)
        self.assertContains(response, "Termín")
        self.assertContains(response, "Počet dnů cesty")
        for label in ("Celkem najeto", "Navštívené země", "Navštívená moře"):
            with self.subTest(label=label):
                self.assertNotContains(response, label)

    def test_published_page_renders_summary_after_text(self):
        response = self.client.get(self.trip.url)
        for text in (
            "Přehled autovandru",
            "425,5",
            "Česko",
            "Dánsko",
            "Severní moře",
            "Praha → Oslo → Praha",
            "32 h",
            "3 plavby",
            "Cesta plná zážitků.",
        ):
            with self.subTest(text=text):
                self.assertContains(response, text)
        self.assertNotContains(response, "Norské moře")
        self.assertNotContains(response, "999 <span>km</span>")
        html = response.content.decode()
        self.assertLess(
            html.index("Příběh celé výpravy."),
            html.index('class="roadtrip-day-summary"'),
        )

    def test_missing_latest_total_labels_the_last_known_distance(self):
        self.second.content[0].value["total_distance_km"] = None
        self.second.save_revision().publish()
        response = self.client.get(self.trip.url)
        self.assertContains(response, "Celkem najeto · k 1. dni")
        self.assertContains(response, "100 <span>km</span>")

    def test_zero_total_is_visible(self):
        self.second.unpublish()
        self.first.content[0].value["total_distance_km"] = Decimal("0")
        self.first.save_revision().publish()
        self.assertContains(self.client.get(self.trip.url), "0 <span>km</span>")

    def test_changes_are_reflected_only_after_day_is_published(self):
        self.second.content[0].value["total_distance_km"] = Decimal("450")
        revision = self.second.save_revision()
        self.assertEqual(
            self.trip.get_trip_summary()["total_distance_km"], Decimal("425.5")
        )
        revision.publish()
        self.assertEqual(
            self.trip.get_trip_summary()["total_distance_km"], Decimal("450")
        )

    def test_other_trips_are_not_aggregated(self):
        other = add_page(
            self.index,
            RoadTripPage,
            title="Jiná cesta",
            slug="jina",
            intro="Jiná",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 10),
        )
        add_page(
            other,
            RoadTripDayPage,
            title="Den",
            slug="den",
            day_number=1,
            date=date(2026, 7, 1),
            intro="Jiný den",
            content=[
                (
                    "day_summary",
                    {
                        "heading": "Přehled dne",
                        "total_distance_km": Decimal("5000"),
                        "countries": ["Itálie"],
                    },
                )
            ],
        )
        self.assertEqual(
            self.trip.get_trip_summary()["total_distance_km"], Decimal("425.5")
        )
        self.assertNotIn("Itálie", self.trip.get_trip_summary()["countries"])

    def test_block_is_available_only_on_whole_trips(self):
        self.assertIn(
            "trip_summary",
            RoadTripPage._meta.get_field("content").stream_block.child_blocks,
        )
        self.assertNotIn(
            "trip_summary",
            RoadTripDayPage._meta.get_field("content").stream_block.child_blocks,
        )

    def test_editor_saves_block_and_revision_preserves_manual_details(self):
        form_class = RoadTripPage.get_edit_handler().get_form_class()
        form = form_class(
            {
                "title": self.trip.title,
                "slug": self.trip.slug,
                "intro": self.trip.intro,
                "start_date": "2026-07-01",
                "end_date": "2026-07-10",
                "content-count": "1",
                "content-0-type": "trip_summary",
                "content-0-order": "0",
                "content-0-deleted": "",
                "content-0-value-heading": "Naše cesta v číslech",
                "content-0-value-route": "Praha → Oslo",
                "content-0-value-extra_items-count": "0",
                "comments-TOTAL_FORMS": "0",
                "comments-INITIAL_FORMS": "0",
            },
            instance=self.trip,
            parent_page=self.index,
        )
        self.assertTrue(form.is_valid(), form.errors)
        page = form.save(commit=False)
        revision = page.save_revision()
        revision.publish()
        restored = revision.as_object()
        self.assertEqual(restored.content[0].value["route"], "Praha → Oslo")
        self.assertContains(self.client.get(page.url), "Naše cesta v číslech")

    def test_manual_text_is_escaped(self):
        block = RoadTripSummaryBlock()
        unsafe = "<script>alert(1)</script>"
        html = block.render(
            block.to_python(
                {
                    "heading": unsafe,
                    "route": unsafe,
                    "driving_time": unsafe,
                    "extra_items": [{"label": unsafe, "value": unsafe}],
                    "note": unsafe,
                }
            ),
            context={"page": self.trip},
        )
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_optional_manual_fields_are_hidden(self):
        block = RoadTripSummaryBlock()
        html = block.render(
            block.to_python({"heading": "Přehled"}), context={"page": self.trip}
        )
        self.assertNotIn("<dt>Trasa</dt>", html)
        self.assertNotIn("<dt>Čas na cestě</dt>", html)
        self.assertIn("425,5", html)
