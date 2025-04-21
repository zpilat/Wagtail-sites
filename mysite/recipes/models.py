from datetime import date
from django.db import models
from modelcluster.fields import ParentalKey
from taggit.models import Tag, TaggedItemBase
from modelcluster.contrib.taggit import ClusterTaggableManager
from wagtail.admin.panels import (
    FieldPanel,
    InlinePanel,
    HelpPanel,
    MultiFieldPanel,
    MultipleChooserPanel,
)
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Orderable, Page
from wagtail.search import index

from base.blocks import BaseStreamBlock
from .blocks import RecipeStreamBlock


class RecipePageTag(TaggedItemBase):
    content_object = ParentalKey(
        'RecipePage',
        related_name='tagged_items',
        on_delete=models.CASCADE
    )
    

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
        help_text="Pouze režim na šířku; šířka mezi 1000px a 3000px",
    )
    intro = RichTextField(help_text="Úvodní text popisující stránku", blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("image"),
        FieldPanel('intro'),
    ]

    parent_page_types = ["home.HomePage"]
    subpage_types = ['RecipeCategoryPage']

    def get_recipes(self, tag_slug=None):
        recipes = RecipePage.objects.descendant_of(self).live().order_by('-first_published_at')
        if tag_slug:
            recipes = recipes.filter(tags__slug=tag_slug)
        return recipes
    
    def get_categories(self):
        categories = RecipeCategoryPage.objects.live().order_by('title').specific()
        return categories    

    def get_child_tags(self):
        tags = []
        for recipe in self.get_recipes():
            tags += recipe.tags.all()
        tags = sorted(set(tags), key=lambda tag: tag.name)
        return tags    

    def get_context(self, request):
        context = super().get_context(request)
        tag_slug = request.GET.get('tag')
        context['recipes'] = self.get_recipes(tag_slug)
        context['tags'] = self.get_child_tags()
        context['categories'] = self.get_categories()
        return context  
    

class RecipeCategoryPage(Page):
    """
    Stránky pro jednotlivé kategorie receptů - např. Polévky, Hlavní jídla, Pomazánky ...
    """
    intro = RichTextField(help_text="Úvodní text popisující kategorii", blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    parent_page_types = ["RecipeIndexPage"]
    subpage_types = ['RecipePage']

    def get_recipes(self, tag_slug=None):
        recipes = RecipePage.objects.descendant_of(self).live().order_by('-first_published_at')
        if tag_slug:
            recipes = recipes.filter(tags__slug=tag_slug)
        return recipes

    def get_categories(self):
        categories = RecipeCategoryPage.objects.live().order_by('title').specific()
        return categories       
    
    def get_recipe_index_page(self):
        return self.get_parent().specific    

    def get_child_tags(self):
        tags = []
        for recipe in self.get_recipes():
            tags += recipe.tags.all()
        tags = sorted(set(tags), key=lambda tag: tag.name)
        return tags    

    def get_context(self, request):
        context = super().get_context(request)
        tag_slug = request.GET.get('tag')
        context['recipes'] = self.get_recipes(tag_slug)
        context['tags'] = self.get_child_tags()
        context['categories'] = self.get_categories()
        context['recipe_index_page'] = self.get_recipe_index_page()
        context['active_category'] = self
        return context  


class RecipePage(Page):
    """
    Recipe pages are more complex than blog pages, demonstrating more advanced StreamField patterns.
    """
    parent_page_types = ["RecipeCategoryPage"]
    subpage_types = []

    date_published = models.DateField("Datum publikace receptu", default=date.today)
    subtitle = models.CharField("Podtitul receptu, zobrazí se na stránce s receptem", blank=True, max_length=255)
    introduction = models.TextField("Úvod", blank=True, max_length=300)
    backstory = StreamField(
        BaseStreamBlock(),
        block_counts={
            "heading_block": {"max_num": 1},
            "image_block": {"max_num": 0},
            "embed_block": {"max_num": 1},
        },
        blank=True,
        use_json_field=True,
        help_text="Lze použít maximálně jeden nadpis, obrázek a médium.",
    )
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
    tags = ClusterTaggableManager(through=RecipePageTag, blank=True)

    def get_main_image(self):
        gallery_last_item = self.gallery_images.last()
        if gallery_last_item:
            return gallery_last_item
        else:
            return None
    
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
        FieldPanel("tags", heading="Tagy"),
        InlinePanel('gallery_images', label="Galerie obrázků"), 
    ]

    search_fields = Page.search_fields + [
        index.SearchField("backstory"),
        index.SearchField("body"),
    ]

    def get_category(self):
        # specific je property – přetypuje jednu instanci stránky (bez závorek)
        return self.get_parent().specific

    def get_categories(self):
        # specific() je metoda querysetu – přetypuje všechny položky v seznamu (s závorkami)
        return RecipeCategoryPage.objects.live().order_by('title').specific()

    def get_recipe_index_page(self):
        # specific je property – vrací konkrétní typ (např. RecipeIndexPage), ne jen obecný Page
        return self.get_ancestors().type(RecipeIndexPage).first().specific
    
    def get_context(self, request):
        context = super().get_context(request)

        siblings = self.get_siblings().live().order_by('path').specific()
        siblings_list = list(siblings)
        current_index = siblings_list.index(self)

        context['prev_recipe'] = siblings_list[current_index - 1] if current_index > 0 else siblings_list[-1]
        context['next_recipe'] = siblings_list[current_index + 1] if current_index < len(siblings_list) - 1 else siblings_list[0]
        context['active_category'] = self.get_category()
        context['recipe_index_page'] = self.get_recipe_index_page()
        context["categories"] = self.get_categories()
        return context

    
class BlogPageGalleryImage(Orderable):
    page = ParentalKey(RecipePage, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ForeignKey(
        'wagtailimages.Image', on_delete=models.CASCADE, related_name='+'
    )
    caption = models.CharField(blank=True, max_length=250)

    panels = [
        FieldPanel('image', heading="Obrázek"),
        FieldPanel('caption', heading="Popisek obrázku"),
    ]
