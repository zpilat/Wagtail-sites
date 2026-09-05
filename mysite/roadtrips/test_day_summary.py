from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
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
                value = self.block.clean(self.value(total_distance_km=distance))
                self.assertEqual(value["total_distance_km"], Decimal(distance))

    def test_negative_distance_and_excess_precision_are_rejected(self):
        for distance in ("-1", "12.34"):
            with self.subTest(distance=distance):
                with self.assertRaises(StructBlockValidationError) as error:
                    self.block.clean(self.value(total_distance_km=distance))
                self.assertIn("total_distance_km", error.exception.block_errors)

    def test_unfilled_statistics_are_optional_and_hidden(self):
        value = self.block.clean(self.value())
        html = self.block.render(value)
        self.assertIn("Přehled dne", html)
        for label in (
            "<dl",
            "Ujeto",
            "Celkem najeto",
            "Navštívené země",
            "Navštívená moře",
            "Trasa",
            "Čas na cestě",
            "Místo noclehu",
        ):
            with self.subTest(label=label):
                self.assertNotIn(label, html)

    def test_zero_distance_is_visible(self):
        html = self.block.render(self.block.clean(self.value(total_distance_km="0")))
        self.assertIn("Celkem najeto", html)
        self.assertIn("0 <span>km</span>", html)

    @override("cs")
    def test_decimal_distance_uses_czech_formatting(self):
        html = self.block.render(self.value(total_distance_km="428.5"))
        self.assertIn("428,5 <span>km</span>", html)

    def test_countries_preserve_travel_order(self):
        html = self.block.render(self.value(countries=["Česko", "Německo", "Dánsko"]))
        self.assertLess(html.index("Česko"), html.index("Německo"))
        self.assertLess(html.index("Německo"), html.index("Dánsko"))

    def test_seas_render_in_travel_order_without_other_statistics(self):
        value = self.block.clean(self.value(seas=["Baltské moře", "Severní moře"]))
        html = self.block.render(value)
        self.assertIn("<dt>Navštívená moře</dt>", html)
        self.assertIn("<li>Baltské moře</li>", html)
        self.assertIn("<li>Severní moře</li>", html)
        self.assertLess(html.index("Baltské moře"), html.index("Severní moře"))
        self.assertNotIn("Navštívené země", html)

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
                seas=[unsafe],
                route=unsafe,
                driving_time=unsafe,
                overnight_stay=unsafe,
                extra_items=[{"label": unsafe, "value": unsafe}],
                note=f"{unsafe}\nDruhý řádek",
            )
        )
        self.assertNotIn("<script>", html)
        self.assertEqual(html.count("&lt;script&gt;"), 10)
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
                        "total_distance_km": Decimal("428.5"),
                        "countries": ["Česko", "Německo"],
                        "seas": ["Baltské moře", "Severní moře"],
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
            "Baltské moře",
            "Severní moře",
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
                self.assertEqual(summary["total_distance_km"], Decimal("428.5"))
                self.assertEqual(list(summary["countries"]), ["Česko", "Německo"])
                self.assertEqual(
                    list(summary["seas"]), ["Baltské moře", "Severní moře"]
                )
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
                "content-0-value-total_distance_km": "428.5",
                "content-0-value-countries-count": "0",
                "content-0-value-seas-count": "1",
                "content-0-value-seas-0-deleted": "",
                "content-0-value-seas-0-order": "0",
                "content-0-value-seas-0-value": "Baltské moře",
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
        response = self.client.get(page.url)
        self.assertContains(response, "0 <span>km</span>")
        self.assertContains(response, "<li>Baltské moře</li>")


class DayMileageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.index = add_page(
            home_page(), RoadTripIndexPage, title="Autovandry", slug="autovandry"
        )
        cls.trip = add_page(
            cls.index,
            RoadTripPage,
            title="Cesta",
            slug="cesta",
            intro="Výprava",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 10),
        )
        cls.first = cls.add_day(1, "100.1")
        # Tree order must not determine which mileage is subtracted.
        cls.third = cls.add_day(3, "250.6")
        cls.second = cls.add_day(2, "250.6")

    @classmethod
    def add_day(cls, number, total):
        return add_page(
            cls.trip,
            RoadTripDayPage,
            title=f"Den {number}",
            slug=f"den-{number}",
            day_number=number,
            date=date(2026, 7, number),
            intro="Na cestě",
            content=[
                (
                    "day_summary",
                    {
                        "heading": "Přehled dne",
                        "total_distance_km": Decimal(total),
                    },
                )
            ],
        )

    @staticmethod
    def set_total(page, total):
        page.content[0].value["total_distance_km"] = Decimal(total)

    def test_first_day_starts_at_zero(self):
        self.assertEqual(
            self.first.get_daily_distance_km(Decimal("100.1")), Decimal("100.1")
        )
        response = self.client.get(self.first.url)
        self.assertContains(response, "Ujeto za den")
        self.assertContains(response, "Celkem najeto")
        self.assertContains(response, "100,1 <span>km</span>", count=2)

    def test_difference_uses_day_number_and_exact_decimal_arithmetic(self):
        self.assertEqual(
            self.second.get_daily_distance_km(Decimal("250.6")), Decimal("150.5")
        )
        response = self.client.get(self.second.url)
        self.assertContains(response, "150,5 <span>km</span>")
        self.assertContains(response, "250,6 <span>km</span>")

    def test_equal_totals_show_zero_distance(self):
        self.third.full_clean()
        self.assertContains(self.client.get(self.third.url), "0 <span>km</span>")

    def test_missing_previous_day_does_not_combine_multiple_days(self):
        self.second.delete()
        response = self.client.get(self.third.url)
        self.assertContains(response, "250,6 <span>km</span>")
        self.assertNotContains(response, "Ujeto za den")

    def test_previous_day_without_summary_or_total_hides_daily_distance(self):
        for content in (
            [],
            [
                (
                    "day_summary",
                    {"heading": "Přehled dne"},
                )
            ],
        ):
            with self.subTest(content=content):
                self.second.content = content
                self.second.save_revision().publish()
                response = self.client.get(self.third.url)
                self.assertContains(response, "Celkem najeto")
                self.assertNotContains(response, "Ujeto za den")

    def test_unpublished_previous_day_is_used_only_in_preview(self):
        self.second.unpublish()
        self.assertIsNone(self.third.get_daily_distance_km(Decimal("250.6")))
        self.assertEqual(
            self.third.get_daily_distance_km(Decimal("250.6"), is_preview=True), 0
        )

    def test_preview_uses_latest_draft_while_public_page_uses_published_total(self):
        self.set_total(self.first, "80.1")
        self.first.save_revision()
        self.assertEqual(
            self.second.get_daily_distance_km(Decimal("250.6")), Decimal("150.5")
        )
        self.assertEqual(
            self.second.get_daily_distance_km(Decimal("250.6"), is_preview=True),
            Decimal("170.5"),
        )

    def test_publishing_previous_day_correction_updates_next_day(self):
        self.set_total(self.first, "80.1")
        self.first.save_revision().publish()
        response = self.client.get(self.second.url)
        self.assertContains(response, "170,5 <span>km</span>")
        self.assertNotContains(response, "150,5 <span>km</span>")

    def test_other_trips_do_not_affect_the_difference(self):
        other_trip = add_page(
            self.index,
            RoadTripPage,
            title="Jiná cesta",
            slug="jina",
            intro="Jiná",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 10),
        )
        add_page(
            other_trip,
            RoadTripDayPage,
            title="Den 1",
            slug="den-1",
            day_number=1,
            date=date(2026, 7, 1),
            intro="Na cestě",
            content=[
                (
                    "day_summary",
                    {"heading": "Přehled dne", "total_distance_km": Decimal("999")},
                )
            ],
        )
        self.assertEqual(
            self.second.get_daily_distance_km(Decimal("250.6")), Decimal("150.5")
        )

    def test_legacy_daily_distance_without_total_is_never_displayed(self):
        raw_content = self.second.content.get_prep_value()
        raw_content[0]["value"].pop("total_distance_km")
        raw_content[0]["value"]["distance_km"] = "999"
        RoadTripDayPage.objects.filter(pk=self.second.pk).update(content=raw_content)
        response = self.client.get(self.second.url)
        self.assertNotContains(response, "Ujeto za den")
        self.assertNotContains(response, "999 <span>km</span>")

    def test_model_rejects_total_lower_than_previous_or_higher_than_next(self):
        for page, total in ((self.second, "90"), (self.first, "300")):
            with self.subTest(day=page.day_number):
                self.set_total(page, total)
                with self.assertRaises(ValidationError) as error:
                    page.full_clean()
                self.assertIn("content", error.exception.message_dict)

    def test_invalid_stored_difference_is_not_shown_as_negative_distance(self):
        self.assertIsNone(self.second.get_daily_distance_km(Decimal("90")))

    def day_form(self, total, instance=None):
        day_number = instance.day_number if instance else 4
        data = {
            "title": f"Den {day_number}",
            "slug": f"den-{day_number}",
            "day_number": str(day_number),
            "date": f"2026-07-{day_number:02d}",
            "intro": "Na cestě",
            "content-count": "1",
            "content-0-type": "day_summary",
            "content-0-order": "0",
            "content-0-deleted": "",
            "content-0-value-heading": "Přehled dne",
            "content-0-value-total_distance_km": total,
            "content-0-value-countries-count": "0",
            "content-0-value-seas-count": "0",
            "content-0-value-extra_items-count": "0",
            "comments-TOTAL_FORMS": "0",
            "comments-INITIAL_FORMS": "0",
        }
        form_class = RoadTripDayPage.get_edit_handler().get_form_class()
        return form_class(
            data, instance=instance or RoadTripDayPage(), parent_page=self.trip
        )

    def test_editor_saves_only_total_and_daily_distance_is_computed(self):
        form = self.day_form("300.7")
        self.assertTrue(form.is_valid(), form.errors)
        page = form.save(commit=False)
        self.trip.add_child(instance=page)
        page.save_revision().publish()
        page.refresh_from_db()
        self.assertEqual(page.get_total_distance_km(), Decimal("300.7"))
        self.assertNotIn("distance_km", page.content[0].value)
        self.assertEqual(
            page.get_latest_revision().as_object().get_total_distance_km(),
            Decimal("300.7"),
        )
        response = self.client.get(page.url)
        self.assertContains(response, "50,1 <span>km</span>")
        self.assertContains(response, "300,7 <span>km</span>")

    def test_editor_rejects_lower_total_before_new_day_is_in_tree(self):
        form = self.day_form("200")
        self.assertFalse(form.is_valid())
        self.assertIn("content", form.errors)

    def test_editor_rejects_correction_exceeding_following_day_total(self):
        form = self.day_form("300", instance=self.first)
        self.assertFalse(form.is_valid())
        self.assertIn("content", form.errors)
