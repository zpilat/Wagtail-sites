from django.test import TestCase

from base.test_utils import ArticleTestsMixin
from .models import Author, BlogIndexPage, BlogPage


class BlogTests(ArticleTestsMixin, TestCase):
    index_model = BlogIndexPage
    page_model = BlogPage
    index_slug = "blog"
    parent_context_key = "blog_index"

    def test_author_name_is_displayed_on_article(self):
        author = Author.objects.create(name="Jana Pilátová")
        self.older.authors.add(author)
        self.older.save()
        self.assertEqual(str(author), "Jana Pilátová")
        self.assertContains(self.client.get(self.older.url), author.name)
