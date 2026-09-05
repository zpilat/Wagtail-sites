from django.test import RequestFactory, TestCase

from base.test_utils import add_page, home_page, publication_date, test_image
from .models import RecipeCategoryPage, RecipeIndexPage, RecipePage


class RecipeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.index = add_page(
            home_page(), RecipeIndexPage, title="Recepty", slug="recepty"
        )
        cls.soups = add_page(
            cls.index, RecipeCategoryPage, title="Polévky", slug="polevky"
        )
        cls.mains = add_page(
            cls.index, RecipeCategoryPage, title="Hlavní jídla", slug="hlavni"
        )
        cls.draft_category = add_page(
            cls.index,
            RecipeCategoryPage,
            title="Koncept kategorie",
            slug="koncept-kategorie",
            live=False,
        )
        cls.first = add_page(cls.soups, RecipePage, title="Česnečka", slug="cesnecka")
        cls.second = add_page(
            cls.soups, RecipePage, title="Bramboračka", slug="bramboracka"
        )
        cls.third = add_page(cls.soups, RecipePage, title="Vývar", slug="vyvar")
        cls.draft = add_page(
            cls.soups, RecipePage, title="Tajná polévka", slug="tajna", live=False
        )
        cls.main = add_page(cls.mains, RecipePage, title="Rizoto", slug="rizoto")
        for day, page in enumerate((cls.first, cls.second, cls.third, cls.main), 1):
            publication_date(page, day)
        for page, tags in (
            (cls.first, ["Česnek", "Polévka"]),
            (cls.second, ["Polévka"]),
            (cls.draft, ["Tajné"]),
            (cls.main, ["Rýže"]),
        ):
            page.tags.add(*tags)
            page.save()

    def test_index_lists_live_recipes_across_categories_newest_first(self):
        self.assertEqual(
            list(self.index.get_recipes()),
            [self.main, self.third, self.second, self.first],
        )

    def test_category_lists_only_its_live_recipes(self):
        self.assertEqual(
            list(self.soups.get_recipes()), [self.third, self.second, self.first]
        )

    def test_tag_filter_on_index_and_category(self):
        tag_slug = self.first.tags.get(name="Česnek").slug
        for listing in (self.index, self.soups):
            with self.subTest(listing=listing):
                self.assertEqual(list(listing.get_recipes(tag_slug)), [self.first])
                self.assertFalse(listing.get_recipes("missing").exists())
                response = self.client.get(listing.url, {"tag": tag_slug})
                self.assertEqual(list(response.context["recipes"]), [self.first])
                self.assertContains(response, self.first.title)
                self.assertNotContains(response, self.second.title)
                self.assertNotContains(response, self.draft.title)

    def test_tags_are_unique_sorted_and_scoped_to_listing(self):
        self.assertEqual(
            [tag.name for tag in self.index.get_child_tags()],
            ["Polévka", "Rýže", "Česnek"],
        )
        self.assertEqual(
            [tag.name for tag in self.soups.get_child_tags()], ["Polévka", "Česnek"]
        )

    def test_categories_are_sorted_and_exclude_drafts(self):
        for page in (self.index, self.soups, self.first):
            with self.subTest(page=page):
                self.assertEqual(list(page.get_categories()), [self.mains, self.soups])

    def test_category_context_contains_index_and_active_category(self):
        response = self.client.get(self.soups.url)
        self.assertEqual(response.context["recipe_index_page"], self.index)
        self.assertEqual(response.context["active_category"], self.soups)

    def test_recipe_navigation_wraps_and_skips_drafts_and_other_categories(self):
        for page, previous, following in (
            (self.first, self.third, self.second),
            (self.second, self.first, self.third),
            (self.third, self.second, self.first),
        ):
            with self.subTest(page=page):
                response = self.client.get(page.url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["prev_recipe"], previous)
                self.assertEqual(response.context["next_recipe"], following)
                self.assertEqual(response.context["active_category"], self.soups)
                self.assertEqual(response.context["recipe_index_page"], self.index)
                self.assertContains(response, f'href="{previous.url}"')
                self.assertContains(response, f'href="{following.url}"')

    def test_single_recipe_navigation_points_to_itself(self):
        response = self.client.get(self.main.url)
        self.assertEqual(response.context["prev_recipe"], self.main)
        self.assertEqual(response.context["next_recipe"], self.main)

    def test_draft_preview_does_not_require_a_live_sibling_position(self):
        request = RequestFactory().get(self.draft.url)
        request.is_preview = True
        context = self.draft.get_context(request)
        self.assertEqual(context["prev_recipe"], self.draft)
        self.assertEqual(context["next_recipe"], self.draft)
        self.assertEqual(context["recipe_index_page"], self.index)

    def test_draft_recipe_returns_404(self):
        self.assertEqual(self.client.get(self.draft.url).status_code, 404)

    def test_empty_backstory_has_no_image_or_story_section(self):
        self.assertIsNone(self.first.get_main_image())
        self.assertFalse(self.first.has_backstory_content())
        self.assertNotContains(self.client.get(self.first.url), 'id="story-heading"')

    def test_image_only_backstory_does_not_render_empty_story_section(self):
        image = test_image()
        self.first.backstory = [
            (
                "image_block",
                {"image": image, "caption": "Polévka na stole", "attribution": ""},
            )
        ]
        self.first.save()
        self.assertEqual(self.first.get_main_image()["image"], image)
        self.assertFalse(self.first.has_backstory_content())
        response = self.client.get(self.first.url)
        self.assertContains(response, "Polévka na stole")
        self.assertNotContains(response, 'id="story-heading"')

    def test_backstory_and_recipe_blocks_render_in_order(self):
        self.first.backstory = [("paragraph_block", "<p>Babiččin recept</p>")]
        self.first.body = [
            (
                "ingredients_list",
                {
                    "title": "Suroviny",
                    "ingredients_list": ["<p>Česnek</p>", "<p>Voda</p>"],
                },
            ),
            (
                "steps_list",
                {
                    "title": "Postup",
                    "steps_list": ["<p>Oloupejte česnek</p>", "<p>Povařte</p>"],
                },
            ),
        ]
        self.first.save()
        self.assertTrue(self.first.has_backstory_content())
        self.assertIsNone(self.first.get_main_image())
        response = self.client.get(self.first.url)
        self.assertContains(response, "Babiččin recept")
        self.assertContains(response, "Oloupejte česnek")
        html = response.content.decode()
        self.assertLess(html.index("Suroviny"), html.index("Postup"))
        self.assertLess(html.index("Oloupejte česnek"), html.index("Povařte"))
