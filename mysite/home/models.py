from wagtail.models import Page
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from django.db import models

from blog.models import BlogIndexPage
from recipes.models import RecipeIndexPage
from coding.models import CodingIndexPage
from roadtrips.models import RoadTripIndexPage

class HomePage(Page):
    max_count = 1

    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Landscape mode only; horizontal width between 1000px and 3000px.",
    )     
    
    body = RichTextField(null=True, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("image"),        
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

        # Fetch CodeIndexPage
        coding_index = self.get_children().type(CodingIndexPage).live().specific().first()
        context['coding_index'] = coding_index

        # Fetch RoadTripIndexPage
        roadtrips_index = self.get_children().type(RoadTripIndexPage).live().specific().first()
        context['roadtrips_index'] = roadtrips_index

        # Další indexové stránky podle potřeby
        return context
