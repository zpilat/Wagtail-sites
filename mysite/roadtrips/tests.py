import json
from datetime import date
from importlib import import_module
from unittest.mock import Mock

from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, TestCase
from wagtail.blocks import StructBlockValidationError
from wagtail.documents import get_document_model
from wagtail.models import Site

from .models import RoadTripDayPage, RoadTripIndexPage, RoadTripPage
from .blocks import RoadTripVideoBlock
from base.test_utils import add_page, home_page, test_image


class RoadTripPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.video = get_document_model().objects.create(
            title="Přejezd horského průsmyku",
            file="documents/horsky-prusmyk.mp4",
        )
        cls.home = Site.objects.get(is_default_site=True).root_page.specific
        cls.index = RoadTripIndexPage(
            title="Autovandry", slug="roadtrips", intro="Naše cesty"
        )
        cls.home.add_child(instance=cls.index)
        cls.index.save_revision().publish()

        cls.road_trip = RoadTripPage(
            title="Norsko 2026",
            slug="norsko-2026",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 10),
            mapy_route_url="https://mapy.com/s/hodepofuza",
            intro="Cesta na sever",
            content=[
                ("text", "Výprava přes Skandinávii."),
                ("text", "Pokračujeme dál na sever."),
                (
                    "video",
                    {
                        "video": cls.video,
                        "caption": "Přejezd horského průsmyku",
                    },
                ),
            ],
        )
        cls.index.add_child(instance=cls.road_trip)
        cls.road_trip.save_revision().publish()

        cls.day = RoadTripDayPage(
            title="Den 1: Cesta na sever",
            slug="den-1",
            day_number=1,
            date=date(2026, 7, 1),
            mapy_route_url="https://mapy.com/s/hodepofuza",
            intro="Vyrážíme",
            content=[
                ("text", "První den na cestě."),
                ("text", "Večer jsme dorazili do cíle."),
            ],
        )
        cls.road_trip.add_child(instance=cls.day)
        cls.day.save_revision().publish()

        cls.second_day = RoadTripDayPage(
            title="Přes horský průsmyk",
            slug="den-2",
            day_number=2,
            date=date(2026, 7, 2),
            intro="Pokračujeme na sever",
            content=[("text", "Druhý den na cestě.")],
        )
        cls.road_trip.add_child(instance=cls.second_day)
        cls.second_day.save_revision().publish()

    def test_index_lists_road_trips(self):
        response = self.client.get(self.index.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Norsko 2026")

    def test_road_trip_lists_days(self):
        response = self.client.get(self.road_trip.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(
            response,
            'class="article-shell article-shell--wide" style="max-width: 1024px;"',
        )
        self.assertContains(response, "Den 1: Cesta na sever")
        self.assertContains(response, 'src="https://mapy.com/s/hodepofuza"')
        self.assertContains(response, "Mapa trasy – Norsko 2026")
        self.assertContains(response, ">Mapa trasy</h2>")
        self.assertContains(response, 'aria-labelledby="mapy-route-heading"')
        self.assertContains(response, 'class="map-surface map-surface--square"')
        self.assertContains(response, 'width="1200"', count=1)
        self.assertContains(response, 'width="1024"', count=1)
        self.assertContains(response, 'height="1024"')
        self.assertContains(response, "--bs-aspect-ratio: 100%")
        self.assertContains(response, "Pokračujeme dál na sever.")
        self.assertContains(response, "Přejezd horského průsmyku")
        self.assertContains(response, self.video.url)
        self.assertContains(response, "<video controls")

        html = response.content.decode()
        self.assertLess(
            html.index("Výprava přes Skandinávii."),
            html.index("Pokračujeme dál na sever."),
        )
        self.assertLess(
            html.index("Pokračujeme dál na sever."),
            html.index("Přejezd horského průsmyku"),
        )

    def test_day_page_links_back_to_road_trip(self):
        response = self.client.get(self.day.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'class="article-shell article-shell--wide" style="max-width: 1024px;"',
        )
        self.assertContains(response, "Norsko 2026")
        self.assertContains(response, "První den na cestě.")
        self.assertContains(response, 'src="https://mapy.com/s/hodepofuza"')
        self.assertContains(response, "Mapa trasy – Den 1: Cesta na sever")
        self.assertNotContains(response, "map-surface--square")
        self.assertContains(response, 'width="1024"', count=1)
        self.assertContains(response, 'height="768"')
        self.assertContains(response, "--bs-aspect-ratio: 75%")
        self.assertContains(response, "Večer jsme dorazili do cíle.")
        self.assertContains(
            response,
            'class="d-none d-md-inline">2. den · </span>Přes horský průsmyk',
        )
        self.assertContains(
            response,
            'aria-label="Následující: 2. den – Přes horský průsmyk"',
        )
        self.assertContains(
            response,
            'class="article-pagination article-pagination--days"',
        )
        self.assertContains(response, 'aria-label="Navigace mezi dny cesty"')

        second_day_response = self.client.get(self.second_day.url)
        self.assertEqual(second_day_response.status_code, 200)
        self.assertContains(
            second_day_response,
            'class="d-none d-md-inline">1. den · </span>Den 1: Cesta na sever',
        )

    def test_content_supports_text_images_and_video(self):
        content_blocks = RoadTripPage._meta.get_field(
            "content"
        ).stream_block.child_blocks
        self.assertEqual(
            list(content_blocks), ["text", "image", "video", "trip_summary"]
        )

    def test_removed_mapy_photo_blocks_are_cleaned_from_stored_content(self):
        migration = import_module(
            "roadtrips.migrations.0010_alter_roadtripdaypage_content_and_more"
        )
        content = [
            {"type": "text", "value": "Začátek", "id": "1"},
            {
                "type": "mapy_photo",
                "value": {"image_url": "https://example.com"},
                "id": "2",
            },
            {"type": "video", "value": {"video": 1}, "id": "3"},
        ]
        expected = [content[0], content[2]]

        self.assertEqual(migration.remove_block(content), expected)
        self.assertEqual(
            json.loads(migration.remove_block(json.dumps(content))),
            expected,
        )

    def test_custom_image_can_link_to_mapy(self):
        image = Mock()
        image.width = 800
        image.height = 1200
        image.get_rendition.return_value.url = "/media/own-photo.jpg"

        html = render_to_string(
            "blocks/road_trip_image_block.html",
            {
                "value": {
                    "image": image,
                    "caption": "Vyhlídka",
                    "attribution": "",
                    "link_url": "https://mapy.com/s/hejunakope",
                },
            },
        )

        self.assertIn('href="https://mapy.com/s/hejunakope"', html)
        self.assertIn('target="_blank"', html)
        self.assertIn('rel="noopener noreferrer"', html)
        self.assertIn('src="/media/own-photo.jpg"', html)
        self.assertIn("roadtrip-media--portrait", html)

    def test_custom_image_without_link_is_not_wrapped_in_anchor(self):
        image = Mock()
        image.width = 1200
        image.height = 800
        image.get_rendition.return_value.url = "/media/own-photo.jpg"

        html = render_to_string(
            "blocks/road_trip_image_block.html",
            {
                "value": {
                    "image": image,
                    "caption": "Vyhlídka",
                    "attribution": "",
                    "link_url": "",
                },
            },
        )

        self.assertNotIn("<a ", html)
        self.assertIn('src="/media/own-photo.jpg"', html)
        self.assertNotIn("roadtrip-media--portrait", html)

    def test_title_image_uses_separate_card_and_optional_heading(self):
        image = Mock()
        image.get_rendition.return_value.url = "/media/hero.jpg"

        html = render_to_string(
            "blocks/road_trip_hero_image.html",
            {
                "image": image,
                "heading": "Fotografie z Nordkappu",
                "heading_id": "test-image-heading",
                "alt_text": "Norsko 2026",
                "is_roadtrip_day": True,
            },
        )

        self.assertIn('class="media-surface"', html)
        self.assertIn('aria-labelledby="test-image-heading"', html)
        self.assertIn(
            '<h2 id="test-image-heading" class="h4 text-center mb-3">'
            "Fotografie z Nordkappu</h2>",
            html,
        )
        self.assertIn('src="/media/hero.jpg"', html)
        self.assertIn('width="1024"', html)
        self.assertIn('loading="lazy"', html)
        rendition_filter = image.get_rendition.call_args.args[0]
        self.assertEqual(rendition_filter.spec, "width-1024")

        image.reset_mock()
        overview_html = render_to_string(
            "blocks/road_trip_hero_image.html",
            {
                "image": image,
                "heading": "Fotografie z Nordkappu",
                "heading_id": "test-overview-image-heading",
                "alt_text": "Norsko 2026",
            },
        )
        self.assertIn('width="1200"', overview_html)
        rendition_filter = image.get_rendition.call_args.args[0]
        self.assertEqual(rendition_filter.spec, "width-1200")

    def test_end_date_cannot_precede_start_date(self):
        invalid_trip = RoadTripPage(
            title="Neplatná cesta",
            start_date=date(2026, 8, 2),
            end_date=date(2026, 8, 1),
            intro="Úvod",
            content=[("text", "Text")],
        )
        with self.assertRaises(ValidationError):
            invalid_trip.full_clean()


class RoadTripBehaviourTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.index = add_page(
            home_page(), RoadTripIndexPage, title="Autovandry", slug="autovandry"
        )
        cls.trip = add_page(
            cls.index,
            RoadTripPage,
            title="Letní cesta",
            slug="leto",
            intro="Na cestě",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 10),
        )
        # Create out of day-number order to distinguish chronology from tree order.
        cls.last = add_page(
            cls.trip,
            RoadTripDayPage,
            title="Poslední den",
            slug="posledni",
            day_number=10,
            date=date(2026, 7, 10),
            intro="Návrat",
        )
        cls.first = add_page(
            cls.trip,
            RoadTripDayPage,
            title="První den",
            slug="prvni",
            day_number=1,
            date=date(2026, 7, 1),
            intro="Odjezd",
        )
        cls.middle = add_page(
            cls.trip,
            RoadTripDayPage,
            title="Prostřední den",
            slug="prostredni",
            day_number=5,
            date=date(2026, 7, 5),
            intro="Výlet",
        )
        cls.draft = add_page(
            cls.trip,
            RoadTripDayPage,
            title="Koncept dne",
            slug="koncept",
            day_number=2,
            date=date(2026, 7, 2),
            intro="Koncept",
            live=False,
        )

    def test_index_orders_trips_by_start_date_and_excludes_drafts(self):
        older = add_page(
            self.index,
            RoadTripPage,
            title="Zimní cesta",
            slug="zima",
            intro="Zima",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 2),
        )
        add_page(
            self.index,
            RoadTripPage,
            title="Plán",
            slug="plan",
            intro="Plán",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 2),
            live=False,
        )
        self.assertEqual(list(self.index.get_road_trips()), [self.trip, older])

    def test_days_are_ordered_by_number_and_only_include_live_children(self):
        self.assertEqual(
            list(self.trip.get_days()), [self.first, self.middle, self.last]
        )

    def test_navigation_uses_day_numbers_without_wrapping(self):
        for page, previous, following in (
            (self.first, None, self.middle),
            (self.middle, self.first, self.last),
            (self.last, self.middle, None),
        ):
            with self.subTest(page=page):
                response = self.client.get(page.url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["previous_day"], previous)
                self.assertEqual(response.context["next_day"], following)
                self.assertEqual(response.context["road_trip"], self.trip)
                self.assertEqual(response.context["road_trip_index"], self.index)
                self.assertNotContains(response, self.draft.title)

    def test_draft_preview_has_no_previous_or_next_day(self):
        request = RequestFactory().get(self.draft.url)
        request.is_preview = True
        context = self.draft.get_context(request)
        self.assertIsNone(context["previous_day"])
        self.assertIsNone(context["next_day"])

    def test_single_day_has_no_navigation_neighbours(self):
        self.middle.unpublish()
        self.last.unpublish()
        response = self.client.get(self.first.url)
        self.assertIsNone(response.context["previous_day"])
        self.assertIsNone(response.context["next_day"])

    def test_draft_day_is_not_public(self):
        self.assertEqual(self.client.get(self.draft.url).status_code, 404)

    def test_missing_map_url_omits_iframe(self):
        for page in (self.trip, self.first):
            with self.subTest(page=page):
                self.assertNotContains(self.client.get(page.url), "<iframe")

    def test_main_image_returns_selected_image_or_none(self):
        self.assertIsNone(self.first.main_image())
        image = test_image()
        self.first.image = image
        self.assertEqual(self.first.main_image(), image)

    def test_one_day_trip_is_valid(self):
        self.trip.end_date = self.trip.start_date
        self.trip.full_clean()

    def test_day_dates_accept_both_trip_boundaries(self):
        self.first.full_clean()
        self.last.full_clean()

    def test_day_dates_outside_trip_report_date_field_error(self):
        for invalid_date in (date(2026, 6, 30), date(2026, 7, 11)):
            with self.subTest(date=invalid_date):
                self.middle.date = invalid_date
                with self.assertRaises(ValidationError) as error:
                    self.middle.full_clean()
                self.assertIn("date", error.exception.message_dict)

    def test_day_number_must_be_positive(self):
        self.middle.day_number = 0
        with self.assertRaises(ValidationError) as error:
            self.middle.full_clean()
        self.assertIn("day_number", error.exception.message_dict)

    def test_duplicate_number_including_draft_is_rejected(self):
        for number in (self.first.day_number, self.draft.day_number):
            with self.subTest(number=number):
                self.middle.day_number = number
                with self.assertRaises(ValidationError) as error:
                    self.middle.full_clean()
                self.assertIn("day_number", error.exception.message_dict)

    def test_same_day_number_is_allowed_on_another_trip(self):
        trip = add_page(
            self.index,
            RoadTripPage,
            title="Jiná cesta",
            slug="jina",
            intro="Jiná",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 10),
        )
        day = add_page(
            trip,
            RoadTripDayPage,
            title="První den",
            slug="prvni",
            day_number=1,
            date=date(2026, 7, 1),
            intro="Odjezd",
        )
        day.full_clean()
        self.assertEqual(list(trip.get_days()), [day])

    def day_form(self, *, instance=None, parent=None, **overrides):
        data = {
            "title": "Nový den",
            "slug": "novy-den",
            "day_number": "3",
            "date": "2026-07-03",
            "intro": "Zápis z cesty",
            "content-count": "0",
            "comments-TOTAL_FORMS": "0",
            "comments-INITIAL_FORMS": "0",
            **overrides,
        }
        form_class = RoadTripDayPage.get_edit_handler().get_form_class()
        return form_class(
            data,
            instance=instance or RoadTripDayPage(),
            parent_page=parent or self.trip,
        )

    def test_editor_accepts_new_day_without_tree_path(self):
        form = self.day_form()
        self.assertTrue(form.is_valid(), form.errors)

    def test_editor_rejects_duplicate_number_before_inserting_into_tree(self):
        form = self.day_form(day_number="1")
        self.assertFalse(form.is_valid())
        self.assertIn("day_number", form.errors)

    def test_editor_rejects_dates_outside_trip_before_inserting_into_tree(self):
        for value in ("2026-06-30", "2026-07-11"):
            with self.subTest(value=value):
                form = self.day_form(date=value)
                self.assertFalse(form.is_valid())
                self.assertIn("date", form.errors)

    def test_editor_accepts_trip_date_boundaries(self):
        for value in ("2026-07-01", "2026-07-10"):
            with self.subTest(value=value):
                form = self.day_form(date=value)
                self.assertTrue(form.is_valid(), form.errors)

    def test_editor_edit_excludes_current_day_from_duplicate_check(self):
        form = self.day_form(
            instance=self.first, slug=self.first.slug, day_number="1", date="2026-07-01"
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_editor_reports_missing_fields_without_crashing(self):
        form = self.day_form(day_number="", date="")
        self.assertFalse(form.is_valid())
        self.assertIn("day_number", form.errors)
        self.assertIn("date", form.errors)


class RoadTripVideoTests(TestCase):
    def test_supported_extensions_are_case_insensitive(self):
        block = RoadTripVideoBlock()
        for extension in ("mp4", "webm", "ogv", "mov", "m4v", "MP4", "WebM"):
            with self.subTest(extension=extension):
                document = get_document_model().objects.create(
                    title="Video", file=f"documents/video.{extension}"
                )
                value = block.clean(
                    block.to_python({"video": document.pk, "caption": ""})
                )
                self.assertEqual(value["video"], document)

    def test_non_video_documents_are_rejected_on_video_field(self):
        block = RoadTripVideoBlock()
        for filename in ("photo.jpg", "file.pdf", "video.mp4.exe", "no-extension"):
            with self.subTest(filename=filename):
                document = get_document_model().objects.create(
                    title="Soubor", file=f"documents/{filename}"
                )
                with self.assertRaises(StructBlockValidationError) as error:
                    block.clean(block.to_python({"video": document.pk, "caption": ""}))
                self.assertIn("video", error.exception.block_errors)

    def test_missing_video_is_a_validation_error(self):
        block = RoadTripVideoBlock()
        with self.assertRaises(StructBlockValidationError) as error:
            block.clean(block.to_python({"video": None, "caption": ""}))
        self.assertIn("video", error.exception.block_errors)


class RoadTripMigrationHelperTests(SimpleTestCase):
    def test_removal_preserves_unrelated_blocks_and_is_idempotent(self):
        remove = import_module(
            "roadtrips.migrations.0010_alter_roadtripdaypage_content_and_more"
        ).remove_block
        keep = {
            "type": "image",
            "id": "image-id",
            "value": {"image": 42, "link_url": "https://mapy.com/s/test"},
        }
        raw = [
            {"type": "mapy_photo", "value": {}},
            keep,
            {"type": "mapy_photo", "value": {}},
        ]
        self.assertEqual(remove(raw), [keep])
        self.assertEqual(remove(remove(raw)), [keep])
        self.assertEqual(json.loads(remove(json.dumps(raw))), [keep])
        self.assertEqual(len(raw), 3)

    def test_removal_handles_empty_malformed_and_unexpected_data(self):
        remove = import_module(
            "roadtrips.migrations.0010_alter_roadtripdaypage_content_and_more"
        ).remove_block
        for value in (
            None,
            "",
            "invalid json",
            "null",
            {},
            [],
            [None, "unknown"],
            '{"unexpected": true}',
        ):
            with self.subTest(value=value):
                self.assertEqual(remove(value), value)

    def test_removal_accepts_streamvalue_raw_data(self):
        remove = import_module(
            "roadtrips.migrations.0010_alter_roadtripdaypage_content_and_more"
        ).remove_block
        raw = [
            {"type": "text", "value": "Zachovat", "id": "text-id"},
            {"type": "mapy_photo", "value": {}},
        ]
        self.assertEqual(remove(Mock(raw_data=raw)), [raw[0]])

    def test_legacy_conversion_preserves_order_captions_and_image_ids(self):
        build = import_module(
            "roadtrips.migrations.0005_migrate_legacy_content"
        ).build_content
        photos = [
            {"type": "mapy_photo", "value": {"caption": "Mapa"}},
            {"type": "other", "value": {}},
        ]
        gallery = [{"image": 42, "caption": "Vyhlídka"}, {"image": None}]
        for photo_data, gallery_data in (
            (photos, gallery),
            (json.dumps(photos), json.dumps(gallery)),
        ):
            with self.subTest(serialized=isinstance(photo_data, str)):
                result = build("<p>Úvod</p>", photo_data, gallery_data)
                self.assertEqual(
                    [item["type"] for item in result], ["text", "mapy_photo", "image"]
                )
                self.assertEqual(result[0]["value"], "<p>Úvod</p>")
                self.assertEqual(result[1]["value"], {"caption": "Mapa"})
                self.assertEqual(
                    result[2]["value"],
                    {"image": 42, "caption": "Vyhlídka", "attribution": ""},
                )
                self.assertEqual(len({item["id"] for item in result}), 3)

    def test_legacy_conversion_accepts_gallery_model_instances(self):
        build = import_module(
            "roadtrips.migrations.0005_migrate_legacy_content"
        ).build_content
        result = build("", [], [Mock(image_id=42, caption="Obrázek")])
        self.assertEqual(result[0]["value"]["image"], 42)
        self.assertEqual(result[0]["value"]["caption"], "Obrázek")
        self.assertEqual(build("", "", ""), [])


class RoadTripContentMigrationTests(TestCase):
    def test_cleanup_updates_pages_and_revisions_without_changing_other_content(self):
        home = home_page()
        index = add_page(home, RoadTripIndexPage, title="Cesty", slug="cesty")
        trip = add_page(
            index,
            RoadTripPage,
            title="Výlet",
            slug="vylet",
            intro="Úvod",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
        )
        day = add_page(
            trip,
            RoadTripDayPage,
            title="Den",
            slug="den",
            day_number=1,
            date=date(2026, 7, 1),
            intro="Den cesty",
        )
        # Use the historical StreamField definition so removed blocks can still
        # be read and written exactly as they were before migration 0010.
        apps = (
            MigrationExecutor(connection)
            .loader.project_state(
                [("roadtrips", "0009_alter_roadtripdaypage_content_and_more")]
            )
            .apps
        )
        raw = [
            {"type": "text", "id": "text-id", "value": "<p>Ponechat text</p>"},
            {
                "type": "mapy_photo",
                "id": "photo-id",
                "value": {"image_url": "https://example.com/photo.jpg"},
            },
        ]
        revisions = []
        for page in (trip, day):
            historical_model = apps.get_model("roadtrips", type(page).__name__)
            historical_model.objects.filter(pk=page.pk).update(content=raw)
            revision = page.get_latest_revision()
            revision.content["content"] = json.dumps(raw)
            revision.save(update_fields=["content"])
            revisions.append(revision)
        unrelated_revision = home.save_revision()
        unrelated_revision.content["content"] = json.dumps(raw)
        unrelated_revision.save(update_fields=["content"])
        unrelated_before = unrelated_revision.content.copy()

        migration = import_module(
            "roadtrips.migrations.0010_alter_roadtripdaypage_content_and_more"
        )
        migration.remove_mapy_photo_blocks(apps, None)

        for page in (trip, day):
            page.refresh_from_db()
            self.assertEqual(list(page.content.raw_data), [raw[0]])
            self.assertTrue(page.live)
        for revision in revisions:
            title = revision.content["title"]
            revision.refresh_from_db()
            self.assertEqual(json.loads(revision.content["content"]), [raw[0]])
            self.assertEqual(revision.content["title"], title)
        unrelated_revision.refresh_from_db()
        self.assertEqual(unrelated_revision.content, unrelated_before)
