"""Small fixtures shared by application tests (no production data required)."""

from datetime import datetime, timezone

from wagtail.images import get_image_model
from wagtail.images.tests.utils import get_test_image_file
from wagtail.models import Site


def home_page():
    return Site.objects.get(is_default_site=True).root_page.specific


def add_page(parent, model, *, title, slug, live=True, **fields):
    page = parent.add_child(instance=model(title=title, slug=slug, live=live, **fields))
    if live:
        page.save_revision().publish()
    return page


def publication_date(page, day):
    # Set explicit dates so ordering assertions do not depend on clock resolution.
    page.first_published_at = datetime(2026, 1, day, tzinfo=timezone.utc)
    page.save(update_fields=["first_published_at"])


def test_image(title="Fotografie"):
    return get_image_model().objects.create(title=title, file=get_test_image_file())


class ArticleTestsMixin:
    """The same public behaviour is required of blog and coding articles."""

    @classmethod
    def setUpTestData(cls):
        cls.home = home_page()
        cls.index = add_page(
            cls.home, cls.index_model, title="Články", slug=cls.index_slug
        )
        cls.older = add_page(
            cls.index,
            cls.page_model,
            title="Starší článek",
            slug="starsi",
            intro="Úvod",
            body="<p>Obsah článku</p>",
        )
        cls.newer = add_page(
            cls.index,
            cls.page_model,
            title="Novější článek",
            slug="novejsi",
            intro="Další úvod",
            body="<p>Další obsah</p>",
        )
        cls.draft = add_page(
            cls.index,
            cls.page_model,
            title="Rozpracovaný článek",
            slug="koncept",
            live=False,
            intro="Úvod",
            body="Text",
        )
        for page, tags in (
            (cls.older, ["Python", "Django"]),
            (cls.newer, ["Python"]),
            (cls.draft, ["Tajné"]),
        ):
            page.tags.add(*tags)
            page.save()
        publication_date(cls.older, 1)
        publication_date(cls.newer, 2)

    def test_listing_is_newest_first_and_excludes_drafts(self):
        self.assertEqual(list(self.index.get_blogpages()), [self.newer, self.older])

    def test_tag_filter_and_unknown_tag(self):
        self.assertEqual(list(self.index.get_blogpages("django")), [self.older])
        self.assertFalse(self.index.get_blogpages("missing").exists())

    def test_tags_are_sorted_unique_and_only_from_live_articles(self):
        self.assertEqual(
            [tag.name for tag in self.index.get_child_tags()], ["Django", "Python"]
        )

    def test_index_renders_filtered_articles_and_all_available_tags(self):
        response = self.client.get(self.index.url, {"tag": "django"})
        self.assertEqual(list(response.context["blogpages"]), [self.older])
        self.assertEqual(
            [tag.name for tag in response.context["tags"]], ["Django", "Python"]
        )
        self.assertContains(response, self.older.title)
        self.assertNotContains(response, self.newer.title)
        self.assertNotContains(response, self.draft.title)

    def test_article_renders_content_and_parent_link(self):
        response = self.client.get(self.older.url)
        self.assertEqual(response.context[self.parent_context_key], self.index)
        self.assertContains(response, "Obsah článku")
        self.assertContains(response, f'href="{self.index.url}"')

    def test_draft_is_not_publicly_accessible(self):
        self.assertEqual(self.client.get(self.draft.url).status_code, 404)

    def test_numbering_starts_at_one_and_survives_edits(self):
        self.assertEqual(self.older.blog_nr, 1)
        self.assertEqual(self.newer.blog_nr, 2)
        self.older.title = "Změněný titulek"
        self.older.save()
        self.older.refresh_from_db()
        self.assertEqual(self.older.blog_nr, 1)

    def test_numbering_uses_highest_number_after_gap(self):
        self.page_model.objects.filter(pk=self.newer.pk).update(blog_nr=20)
        page = add_page(
            self.index,
            self.page_model,
            title="Další",
            slug="dalsi",
            intro="Úvod",
            body="Text",
        )
        self.assertEqual(page.blog_nr, 21)

    def test_main_image_is_none_without_gallery(self):
        self.assertIsNone(self.older.main_image())

    def test_main_image_follows_gallery_order(self):
        first, second = test_image("První"), test_image("Druhá")
        self.older.gallery_images.create(image=first, sort_order=2)
        self.older.gallery_images.create(image=second, sort_order=1)
        self.older.save()
        self.older.refresh_from_db()
        self.assertEqual(self.older.main_image(), second)
