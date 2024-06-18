from wagtail.models import Page
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from django.db import models

from blog.models import BlogIndexPage
from cookbook.models import CookbookIndexPage

class HomePage(Page):
    body = RichTextField(null=True, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    def get_context(self, request):
        context = super().get_context(request)

        # Fetch BlogIndexPage
        blog_index = self.get_children().type(BlogIndexPage).live().specific().first()
        context['blog_index'] = blog_index

        # Fetch CookbookIndexPage
        cookbook_index = self.get_children().type(CookbookIndexPage).live().specific().first()
        context['cookbook_index'] = cookbook_index

        # Další indexové stránky podle potřeby
        return context

