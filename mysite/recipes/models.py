from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import (
    FieldPanel,
    HelpPanel,
    MultiFieldPanel,
    MultipleChooserPanel,
)
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Orderable, Page
from wagtail.search import index

from base.blocks import BaseStreamBlock
from .blocks import RecipeStreamBlock


class RecipeIndexPage(Page):
    """
    Index page for recipe.
    We need to alter the page model's context to return the child page objects,
    the RecipePage objects, so that it works as an index page
    """
    max_count = 1

    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Pouze režim na šířku; horizontální šířka mezi 1000px a 3000px",
    )
    intro = RichTextField(help_text="Text popisující stránku", blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("image"),
        FieldPanel('intro'),
    ]

    parent_page_types = ["home.HomePage"]
    subpage_types = ['RecipePage']

    def get_context(self, request):
        context = super().get_context(request)
        context["recipes"] = (
            self.get_children().live().order_by('-first_published_at')
        )
        return context
    

class RecipePage(Page):
    """
    Recipe pages are more complex than blog pages, demonstrating more advanced StreamField patterns.
    """
    parent_page_types = ["RecipeIndexPage"]

    date_published = models.DateField("Datum publikace článku", blank=True, null=True)
    subtitle = models.CharField("Podtitul článku", blank=True, max_length=255)
    introduction = models.TextField("Úvod", blank=True, max_length=500)
    backstory = StreamField(
        BaseStreamBlock(),
        # Demonstrate block_counts to keep the backstory concise.
        block_counts={
            "heading_block": {"max_num": 1},
            "image_block": {"max_num": 1},
            "embed_block": {"max_num": 1},
        },
        blank=True,
        use_json_field=True,
        help_text="Použij co nejméně hlaviček a velkých bloků.",
    )

    # An example of using rich text for single-line content.
    recipe_headline = RichTextField(
        blank=True,
        max_length=120,
        features=["bold", "italic", "link"],
        help_text="Dodržujte maximálně jeden řádek",
    )
    body = StreamField(
        RecipeStreamBlock(),
        blank=True,
        use_json_field=True,
        help_text="Pokyny k receptu krok za krokem a další důležité informace.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("date_published", heading="Datum publikace článku"),
        FieldPanel("subtitle", classname="title", heading="Podtitul článku"),
        MultiFieldPanel(
            [
                HelpPanel(
                    "Pro nejlepší úvodní příběh a titulek použijte analýzu klíčových slov a správné názvy ingrediencí..."
                ),
                FieldPanel("introduction", heading="Úvod"),
                FieldPanel("backstory", heading="Příběh"),
                FieldPanel("recipe_headline", heading="Titulek receptu"),
            ],
            heading="Předmluva",
        ),
        FieldPanel("body", heading="Tělo receptu"),
    ]

    search_fields = Page.search_fields + [
        index.SearchField("backstory"),
        index.SearchField("body"),
    ]

