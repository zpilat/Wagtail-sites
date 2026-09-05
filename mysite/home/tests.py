from django.test import RequestFactory, TestCase

from base.test_utils import add_page, home_page
from blog.models import BlogIndexPage
from coding.models import CodingIndexPage
from recipes.models import RecipeIndexPage
from roadtrips.models import RoadTripIndexPage


class HomePageTests(TestCase):
    def test_empty_home_renders_with_missing_sections(self):
        response = self.client.get(home_page().url)
        self.assertEqual(response.status_code, 200)
        for key in ("blog_index", "coding_index", "recipe_index", "roadtrips_index"):
            self.assertIsNone(response.context[key])

    def test_context_selects_live_sections(self):
        home = home_page()
        for model, key in (
            (BlogIndexPage, "blog_index"),
            (CodingIndexPage, "coding_index"),
            (RecipeIndexPage, "recipe_index"),
            (RoadTripIndexPage, "roadtrips_index"),
        ):
            with self.subTest(model=model):
                page = add_page(home, model, title=key, slug=key.replace("_", "-"))
                self.assertEqual(home.get_context(RequestFactory().get("/"))[key], page)
                page.unpublish()
                self.assertIsNone(home.get_context(RequestFactory().get("/"))[key])

    def test_home_and_navigation_show_only_live_menu_items(self):
        home = home_page()
        visible = add_page(
            home, BlogIndexPage, title="Veřejný blog", slug="blog", show_in_menus=True
        )
        hidden = add_page(
            home,
            CodingIndexPage,
            title="Skrytá sekce",
            slug="coding",
            show_in_menus=False,
        )
        draft = add_page(
            home,
            RecipeIndexPage,
            title="Koncept receptů",
            slug="recepty",
            show_in_menus=True,
            live=False,
        )
        response = self.client.get(home.url)
        self.assertContains(response, visible.title)
        self.assertContains(response, f'href="{visible.url}"')
        self.assertNotContains(response, f'href="{hidden.url}"')
        self.assertNotContains(response, f'href="{draft.url}"')
