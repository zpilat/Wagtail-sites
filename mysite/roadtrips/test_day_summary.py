from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.utils.translation import override
from wagtail.blocks import StructBlockValidationError

from base.test_utils import add_page, home_page
from .blocks import RoadTripDaySummaryBlock
from .models import RoadTripDayPage, RoadTripIndexPage, RoadTripPage


class DaySummaryBlockTests(SimpleTestCase):
    def setUp(self):
        self.block = RoadTripDaySummaryBlock()

    def value(self, **fields):
        return self.block.to_python({"heading": "Přehled dne", **fields})

    def test_distance_accepts_zero_and_one_decimal_place(self):
        for distance in ("0", "428.5"):
            with self.subTest(distance=distance):
                value = self.block.clean(self.value(distance_km=distance))
                self.assertEqual(value["distance_km"], Decimal(distance))

    def test_negative_distance_and_excess_precision_are_rejected(self):
        for distance in ("-1", "12.34"):
            with self.subTest(distance=distance):
                with self.assertRaises(StructBlockValidationError) as error:
                    self.block.clean(self.value(distance_km=distance))
                self.assertIn("distance_km", error.exception.block_errors)

    def test_unfilled_statistics_are_optional_and_hidden(self):
        value = self.block.clean(self.value())
        html = self.block.render(value)
        self.assertIn("Přehled dne", html)
        for label in (
            "<dl",
            "Ujeto",
            "Navštívené země",
            "Trasa",
            "Čas na cestě",
            "Místo noclehu",
        ):
            with self.subTest(label=label):
                self.assertNotIn(label, html)

    def test_zero_distance_is_visible(self):
        html = self.block.render(self.block.clean(self.value(distance_km="0")))
        self.assertIn("Ujeto", html)
        self.assertIn("0 <span>km</span>", html)

    @override("cs")
    def test_decimal_distance_uses_czech_formatting(self):
        html = self.block.render(self.value(distance_km="428.5"))
        self.assertIn("428,5 <span>km</span>", html)

    def test_countries_preserve_travel_order(self):
        html = self.block.render(self.value(countries=["Česko", "Německo", "Dánsko"]))
        self.assertLess(html.index("Česko"), html.index("Německo"))
        self.assertLess(html.index("Německo"), html.index("Dánsko"))

    def test_extra_items_require_both_label_and_value(self):
        for item in ({"label": "", "value": "24 °C"}, {"label": "Počasí", "value": ""}):
            with self.subTest(item=item):
                with self.assertRaises(StructBlockValidationError) as error:
                    self.block.clean(self.value(extra_items=[item]))
                self.assertIn("extra_items", error.exception.block_errors)

    def test_text_fields_are_escaped_and_note_preserves_line_breaks(self):
        unsafe = '<script>alert("x")</script>'
        html = self.block.render(
            self.value(
                heading=unsafe,
                countries=[unsafe],
                route=unsafe,
                driving_time=unsafe,
                overnight_stay=unsafe,
                extra_items=[{"label": unsafe, "value": unsafe}],
                note=f"{unsafe}\nDruhý řádek",
            )
        )
        self.assertNotIn("<script>", html)
        self.assertEqual(html.count("&lt;script&gt;"), 9)
        self.assertIn("<br>Druhý řádek", html)


class DaySummaryPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        index = add_page(
            home_page(), RoadTripIndexPage, title="Autovandry", slug="autovandry"
        )
        cls.trip = add_page(
            index,
            RoadTripPage,
            title="Na sever",
            slug="na-sever",
            intro="Cesta na sever",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 10),
        )
        cls.day = add_page(
            cls.trip,
            RoadTripDayPage,
            title="První den",
            slug="prvni-den",
            day_number=1,
            date=date(2026, 7, 1),
            intro="Vyrážíme",
            content=[
                ("text", "<p>Večer jsme dorazili do kempu.</p>"),
                (
                    "day_summary",
                    {
                        "heading": "Přehled dne",
                        "distance_km": Decimal("428.5"),
                        "countries": ["Česko", "Německo"],
                        "route": "Praha → Berlín",
                        "driving_time": "4 h 30 min",
                        "overnight_stay": "Kemp u jezera",
                        "extra_items": [
                            {"label": "Počasí", "value": "Slunečno, 24 °C"}
                        ],
                        "note": "Klidné místo na noc.",
                    },
                ),
            ],
        )

    def test_published_summary_renders_after_the_story(self):
        response = self.client.get(self.day.url)
        self.assertEqual(response.status_code, 200)
        for text in (
            "428,5",
            "Česko",
            "Německo",
            "Praha → Berlín",
            "4 h 30 min",
            "Kemp u jezera",
            "Počasí",
            "Slunečno, 24 °C",
            "Klidné místo na noc.",
        ):
            with self.subTest(text=text):
                self.assertContains(response, text)
        html = response.content.decode()
        self.assertLess(
            html.index("Večer jsme dorazili"),
            html.index('class="roadtrip-day-summary"'),
        )
        self.assertLess(
            html.index('class="roadtrip-day-summary"'),
            html.index('aria-label="Navigace mezi dny cesty"'),
        )

    def test_summary_survives_database_and_revision_round_trip(self):
        self.day.refresh_from_db()
        for page in (self.day, self.day.get_latest_revision().as_object()):
            with self.subTest(revision=page is not self.day):
                summary = page.content[1].value
                self.assertEqual(summary["distance_km"], Decimal("428.5"))
                self.assertEqual(list(summary["countries"]), ["Česko", "Německo"])
                self.assertEqual(summary["extra_items"][0]["value"], "Slunečno, 24 °C")
                self.assertEqual(page.content[0].block_type, "text")

    def test_summary_is_available_on_days(self):
        day_blocks = RoadTripDayPage._meta.get_field(
            "content"
        ).stream_block.child_blocks
        trip_blocks = RoadTripPage._meta.get_field("content").stream_block.child_blocks
        self.assertIn("day_summary", day_blocks)
        self.assertNotIn("day_summary", trip_blocks)

    def test_editor_saves_summary_with_zero_distance(self):
        form_class = RoadTripDayPage.get_edit_handler().get_form_class()
        form = form_class(
            {
                "title": "Den odpočinku",
                "slug": "odpocinek",
                "day_number": "2",
                "date": "2026-07-02",
                "intro": "Zůstáváme v kempu.",
                "content-count": "1",
                "content-0-type": "day_summary",
                "content-0-order": "0",
                "content-0-deleted": "",
                "content-0-value-heading": "Přehled dne",
                "content-0-value-distance_km": "0",
                "content-0-value-countries-count": "0",
                "content-0-value-extra_items-count": "0",
                "comments-TOTAL_FORMS": "0",
                "comments-INITIAL_FORMS": "0",
            },
            instance=RoadTripDayPage(),
            parent_page=self.trip,
        )
        self.assertTrue(form.is_valid(), form.errors)
        page = form.save(commit=False)
        self.trip.add_child(instance=page)
        page.save_revision().publish()
        self.assertContains(self.client.get(page.url), "0 <span>km</span>")
