from django.test import TestCase

from base.test_utils import ArticleTestsMixin, add_page
from blog.models import BlogIndexPage, BlogPage
from .models import CodingIndexPage, CodingPage


class CodingTests(ArticleTestsMixin, TestCase):
    index_model = CodingIndexPage
    page_model = CodingPage
    index_slug = "programovani"
    parent_context_key = "coding_index"

    def test_blog_numbering_is_independent_of_coding(self):
        index = add_page(self.home, BlogIndexPage, title="Blog", slug="blog")
        article = add_page(
            index,
            BlogPage,
            title="Blogový článek",
            slug="clanek",
            intro="Úvod",
            body="Text",
        )
        self.assertEqual(article.blog_nr, 1)
        self.assertEqual(self.newer.blog_nr, 2)
