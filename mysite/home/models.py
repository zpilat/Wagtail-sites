from wagtail.models import Page
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from django.db import models

from blog.models import BlogIndexPage
from recipes.models import RecipeIndexPage

class HomePage(Page):
    max_count = 1
    
    body = RichTextField(null=True, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    def get_context(self, request):
        context = super().get_context(request)

        # Fetch BlogIndexPage
        blog_index = self.get_children().type(BlogIndexPage).live().specific().first()
        context['blog_index'] = blog_index

        # Fetch RecipeIndexPage
        recipe_index = self.get_children().type(RecipeIndexPage).live().specific().first()
        context['recipe_index'] = recipe_index

        # Další indexové stránky podle potřeby
        return context

