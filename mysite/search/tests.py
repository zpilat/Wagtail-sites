from django.test import TestCase
from django.urls import reverse

from base.test_utils import add_page, home_page
from blog.models import BlogIndexPage, BlogPage


class SearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.index = add_page(home_page(), BlogIndexPage, title="Blog", slug="blog")
        cls.articles = [
            add_page(
                cls.index,
                BlogPage,
                title=f"Hledatelny článek {number}",
                slug=f"clanek-{number}",
                intro="Úvod",
                body="Obsah",
            )
            for number in range(12)
        ]
        cls.draft = add_page(
            cls.index,
            BlogPage,
            title="Hledatelny tajný koncept",
            slug="koncept",
            live=False,
            intro="Úvod",
            body="Obsah",
        )

    def test_missing_and_empty_queries_show_empty_search(self):
        for params in ({}, {"query": ""}):
            with self.subTest(params=params):
                response = self.client.get(reverse("search"), params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["search_results"].paginator.count, 0)
                self.assertContains(
                    response, "Výsledky se zobrazí po zadání hledaného výrazu."
                )

    def test_search_uses_real_index_and_excludes_drafts(self):
        response = self.client.get(reverse("search"), {"query": "Hledatelny"})
        results = response.context["search_results"]
        self.assertEqual(results.paginator.count, 12)
        self.assertEqual(len(results), 10)
        self.assertNotContains(response, self.draft.title)
        self.assertContains(response, "page=2")
        self.assertContains(response, f'href="{results[0].url}"')

    def test_second_page_has_remaining_results_without_duplicates(self):
        first = self.client.get(reverse("search"), {"query": "Hledatelny"}).context[
            "search_results"
        ]
        response = self.client.get(
            reverse("search"), {"query": "Hledatelny", "page": 2}
        )
        second = response.context["search_results"]
        self.assertEqual(len(second), 2)
        self.assertEqual(
            {page.pk for page in first} | {page.pk for page in second},
            {page.pk for page in self.articles},
        )
        self.assertContains(response, "page=1")

    def test_invalid_page_numbers_fall_back(self):
        for value, expected in (("abc", 1), ("999", 2), ("0", 2), ("-1", 2)):
            with self.subTest(value=value):
                response = self.client.get(
                    reverse("search"), {"query": "Hledatelny", "page": value}
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["search_results"].number, expected)

    def test_no_matches_with_out_of_range_page(self):
        response = self.client.get(
            reverse("search"), {"query": "nenalezitelnyslovnik", "page": 999}
        )
        self.assertContains(response, "Nic jsme nenašli")
        self.assertEqual(response.context["search_results"].paginator.count, 0)

    def test_query_is_escaped_in_html(self):
        response = self.client.get(
            reverse("search"), {"query": '<script>alert("x")</script>'}
        )
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, "&lt;script&gt;")
