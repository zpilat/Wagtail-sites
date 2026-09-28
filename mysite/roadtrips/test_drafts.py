from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from wagtail.documents import get_document_model

from base.test_utils import add_page, home_page
from .models import RoadTripIndexPage, RoadTripPage


class RoadTripDraftTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = get_user_model().objects.create_superuser(
            username="editor", email="editor@example.com", password="test-password"
        )
        cls.index = add_page(
            home_page(), RoadTripIndexPage, title="Autovandry", slug="autovandry"
        )
        cls.trip = add_page(
            cls.index,
            RoadTripPage,
            title="Cesta",
            slug="cesta",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 10),
            intro="Zveřejněný úvod",
            content=[("text", "Zveřejněný zápis")],
        )

    def setUp(self):
        self.client.force_login(self.editor)
        self.edit_url = reverse("wagtailadmin_pages:edit", args=[self.trip.pk])

    def video_data(self, **overrides):
        return {
            "title": self.trip.title,
            "slug": self.trip.slug,
            "start_date": "2026-07-01",
            "end_date": "2026-07-10",
            "intro": "Rozpracovaný úvod",
            "content-count": "1",
            "content-0-type": "video",
            "content-0-order": "0",
            "content-0-deleted": "",
            "content-0-value-video": "",
            "content-0-value-caption": "Video doplním později",
            "comments-TOTAL_FORMS": "0",
            "comments-INITIAL_FORMS": "0",
            **overrides,
        }

    def assert_video_draft_preserved(self):
        self.trip.refresh_from_db()
        draft = self.trip.get_latest_revision_as_object()
        self.assertEqual(draft.content[0].block_type, "video")
        self.assertIsNone(draft.content[0].value["video"])
        self.assertEqual(draft.content[0].value["caption"], "Video doplním později")
        self.assertEqual(self.trip.intro, "Zveřejněný úvod")
        self.assertEqual(self.trip.content[0].block_type, "text")
        self.assertContains(self.client.get(self.trip.url), "Zveřejněný zápis")

    def test_unfilled_video_can_be_saved_as_draft(self):
        response = self.client.post(self.edit_url, self.video_data())
        self.assertEqual(response.status_code, 302)
        self.assert_video_draft_preserved()

    def test_autosave_accepts_unfilled_video(self):
        response = self.client.post(
            self.edit_url, self.video_data(), HTTP_ACCEPT="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assert_video_draft_preserved()

    def test_unfilled_video_cannot_be_published(self):
        response = self.client.post(
            self.edit_url, self.video_data(**{"action-publish": "1"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("content", response.context["form"].errors)
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.intro, "Zveřejněný úvod")
        self.assertEqual(self.trip.content[0].block_type, "text")

    def test_draft_still_rejects_non_video_documents(self):
        document = get_document_model().objects.create(
            title="Dokument", file="documents/document.pdf"
        )
        response = self.client.post(
            self.edit_url,
            self.video_data(**{"content-0-value-video": str(document.pk)}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("content", response.context["form"].errors)
