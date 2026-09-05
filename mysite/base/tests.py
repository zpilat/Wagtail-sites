from django.template import Context, Template
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from wagtail.blocks import StructBlockValidationError
from wagtail.models import Page, Site

from .blocks import HeadingBlock, IngedientsListBlock, StepsListBlock
from .models import FooterText
from .templatetags.navigation_tags import (
    get_footer_text,
    get_grandchildren,
    get_site_root,
    startswith,
)
from .test_utils import add_page, home_page


class NavigationTests(TestCase):
    def test_footer_without_published_content_is_empty(self):
        FooterText.objects.create(body="<p>Koncept patičky</p>", live=False)
        self.assertEqual(get_footer_text({}), {"footer_text": ""})

    def test_published_footer_is_rendered_as_richtext(self):
        FooterText.objects.create(body="<p>Koncept patičky</p>", live=False)
        FooterText.objects.create(body="<p>Veřejná patička</p>", live=True)
        html = Template("{% load navigation_tags %}{% get_footer_text %}").render(
            Context()
        )
        self.assertIn("<p>Veřejná patička</p>", html)
        self.assertNotIn("Koncept patičky", html)

    def test_preview_footer_overrides_published_footer(self):
        FooterText.objects.create(body="<p>Publikováno</p>", live=True)
        draft = FooterText(body="<p>Náhled změny</p>", live=False)
        context = draft.get_preview_context(RequestFactory().get("/"), "")
        self.assertEqual(get_footer_text(context), {"footer_text": draft.body})
        html = Template("{% load navigation_tags %}{% get_footer_text %}").render(
            Context(context)
        )
        self.assertIn("Náhled změny", html)
        self.assertNotIn("Publikováno", html)

    @override_settings(ALLOWED_HOSTS=["second.test"])
    def test_site_root_uses_request_hostname(self):
        root = Page.get_first_root_node()
        other_home = add_page(root, Page, title="Druhý web", slug="druhy-web")
        Site.objects.create(hostname="second.test", port=80, root_page=other_home)
        request = RequestFactory().get("/", HTTP_HOST="second.test")
        self.assertEqual(get_site_root({"request": request}), other_home)

    def test_grandchildren_count_excludes_direct_children_and_drafts(self):
        parent = add_page(home_page(), Page, title="Sekce", slug="sekce")
        child = add_page(parent, Page, title="Kategorie", slug="kategorie")
        grandchild = add_page(child, Page, title="Článek", slug="clanek")
        add_page(grandchild, Page, title="Příloha", slug="priloha")
        add_page(child, Page, title="Koncept", slug="koncept", live=False)
        self.assertEqual(get_grandchildren(parent), 2)
        self.assertEqual(get_grandchildren(child), 1)
        self.assertEqual(get_grandchildren(grandchild), 0)


class BlockTests(SimpleTestCase):
    def test_startswith_handles_paths_and_non_strings(self):
        for value, prefix, expected in (
            ("/blog/post/", "/blog/", True),
            ("/recepty/", "/blog/", False),
            ("", "/", False),
            (None, "/", False),
            (123, "/", False),
        ):
            with self.subTest(value=value):
                self.assertEqual(startswith(value, prefix), expected)

    def test_heading_levels_render_and_escape_text(self):
        block = HeadingBlock()
        for size in ("h2", "h3", "h4"):
            with self.subTest(size=size):
                value = block.clean(
                    block.to_python(
                        {"heading_text": "<script>text</script>", "size": size}
                    )
                )
                self.assertIn(
                    f"<{size}>&lt;script&gt;text&lt;/script&gt;</{size}>",
                    block.render(value),
                )

    def test_heading_requires_text_and_rejects_unsupported_level(self):
        block = HeadingBlock()
        for value in (
            {"heading_text": "", "size": "h2"},
            {"heading_text": "Nadpis", "size": "script"},
        ):
            with self.subTest(value=value), self.assertRaises(
                StructBlockValidationError
            ):
                block.clean(block.to_python(value))

    def test_recipe_lists_enforce_two_to_fifteen_items(self):
        for block, field in (
            (IngedientsListBlock(), "ingredients_list"),
            (StepsListBlock(), "steps_list"),
        ):
            for count in (0, 1, 2, 15, 16):
                with self.subTest(field=field, count=count):
                    value = block.to_python(
                        {"title": "", field: ["<p>Položka</p>"] * count}
                    )
                    if 2 <= count <= 15:
                        self.assertEqual(len(block.clean(value)[field]), count)
                    else:
                        with self.assertRaises(StructBlockValidationError) as error:
                            block.clean(value)
                        self.assertIn(field, error.exception.block_errors)
