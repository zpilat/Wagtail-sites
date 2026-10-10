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

    subtitle = models.CharField(
        max_length=20,
        default="Recepty",
        help_text=(
            "Krátký název kuchařky v hlavním menu, např. Recepty (max. 20 znaků). "
            "Hlavní nadpis stránky určuje Název stránky."
        ),
    )
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=(
            "Společný titulní obrázek kuchařky nad obsahem přehledu, kategorií i jednotlivých receptů. "
            "Použijte obrázek na šířku, široký 1000 až 3000 px. Fotku konkrétního jídla vložte do Příběhu receptu."
        ),
    )
    intro = RichTextField(
        blank=True,
        help_text="Volitelný úvod pod hlavním nadpisem kuchařky, nad filtry a seznamem receptů.",
    )

    content_panels = [
        FieldPanel(
            "title",
            help_text="Hlavní nadpis přehledu kuchařky a název v administraci. Krátký název do menu vyplňte níže.",
        ),
        FieldPanel("subtitle", heading="Název v menu"),
        FieldPanel("image", heading="Titulní obrázek kuchařky"),
        FieldPanel('intro', heading="Úvod kuchařky"),
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
    intro = RichTextField(
        blank=True,
        help_text="Volitelný popis kategorie pod jejím nadpisem, nad filtry a seznamem receptů této kategorie.",
    )

    content_panels = [
        FieldPanel(
            "title",
            help_text=(
                "Název kategorie, např. Polévky. Zobrazuje se jako hlavní nadpis kategorie, "
                "v menu a u receptů zařazených pod tuto stránku."
            ),
        ),
        FieldPanel('intro', heading="Úvod kategorie"),
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

    date_published = models.DateField(
        "Datum publikace receptu",
        default=date.today,
        help_text=(
            "Datum zobrazené u nadpisu receptu a na jeho kartě v přehledech. "
            "Nenastavuje plánované zveřejnění ani pořadí v přehledech; ty se řadí podle skutečného prvního zveřejnění."
        ),
    )
    subtitle = models.CharField(
        "Podtitul receptu",
        blank=True,
        max_length=255,
        help_text=(
            "Volitelný doplňující nadpis přímo pod Názvem stránky na detailu receptu, "
            "např. Rychlá večeře z jedné pánve. V přehledech receptů se nezobrazuje; název jídla patří do Názvu stránky."
        ),
    )
    introduction = models.TextField(
        "Úvod",
        blank=True,
        max_length=300,
        help_text=(
            "Krátké představení jídla (max. 300 znaků). Zobrazí se pod názvem a případným podtitulem "
            "na detailu i jako popis na kartách receptu v přehledech a odkazech na přílohy."
        ),
    )
    backstory = StreamField(
        BaseStreamBlock(),
        block_counts={
            "heading_block": {"max_num": 1},
            "image_block": {"max_num": 1},
            "embed_block": {"max_num": 1},
        },
        blank=True,
        use_json_field=True,
        help_text=(
            "Volitelný příběh nebo tipy před samotným receptem. Obrázek z tohoto pole se zobrazí "
            "jako hlavní fotka pod úvodem a jako náhled v přehledech. Jeho popisek se zobrazí pod hlavní fotkou "
            "a slouží i jako její alternativní text; zdroj se u této fotky nezobrazuje. "
            "Ostatní bloky se zobrazí v části Příběh. Lze vložit nejvýše jeden nadpis, jeden obrázek a jedno médium."
        ),
    )
    recipe_headline = RichTextField(
        blank=True,
        max_length=120,
        features=["bold", "italic", "link"],
        help_text=(
            "Volitelný krátký text v části Recept, pod nadpisem Recept a před bloky Těla receptu. "
            "Název stránky je hlavní název jídla; toto pole využijte např. pro Na 4 porce. "
            "Pokud další text nepotřebujete, nechte pole prázdné. Pište nejvýše jeden řádek."
        ),
    )
    body = StreamField(
        RecipeStreamBlock(),
        blank=True,
        use_json_field=True,
        help_text=(
            "Samotný recept pod nadpisem Recept a případným Titulkem receptu. "
            "Přidejte např. obtížnost, seznam ingrediencí a kroky přípravy. Bloky se na webu zobrazí "
            "v pořadí, v jakém je zde uspořádáte. Fotky v tomto poli zůstanou součástí postupu; titulní fotku vložte do Příběhu."
        ),
    )
    tags = ClusterTaggableManager(
        through=RecipePageTag,
        blank=True,
        help_text=(
            "Volitelné štítky, např. Bez masa nebo Česnek. Zobrazí se jako odkazy pod receptem "
            "a umožní filtrovat přehled kuchařky i kategorie. Kategorii určuje nadřazená stránka receptu."
        ),
    )

    def get_main_image(self):
        for block in self.backstory:
            if block.block_type == "image_block":
                return block.value
        return None

    def has_backstory_content(self):
        return any(block.block_type != "image_block" for block in self.backstory)
    
    content_panels = [
        FieldPanel(
            "title",
            help_text=(
                "Hlavní název jídla, např. Česnečka. Zobrazí se jako hlavní nadpis detailu, "
                "na kartách v přehledech, v odkazech mezi recepty a v administraci. "
                "Použije se i jako titulek záložky prohlížeče, pokud v záložce Propagace nevyplníte SEO titulek."
            ),
        ),
        FieldPanel("date_published", heading="Datum publikace receptu"),
        FieldPanel("subtitle", classname="title", heading="Podtitul receptu"),
        MultiFieldPanel(
            [
                HelpPanel(
                    "Úvod stručně představuje jídlo i v přehledech. Příběh obsahuje titulní fotku a případné vyprávění. "
                    "Titulek receptu doplňuje až část se surovinami a postupem. Všechna tato pole jsou volitelná."
                ),
                FieldPanel("introduction", heading="Úvod"),
                FieldPanel("backstory", heading="Příběh"),
                FieldPanel("recipe_headline", heading="Titulek receptu"),
            ],
            heading="Předmluva",
        ),
        FieldPanel("body", heading="Tělo receptu"),
        FieldPanel("tags", heading="Tagy"),
        InlinePanel(
            'gallery_images',
            label="Galerie obrázků",
            help_text=(
                "Volitelné další fotky v části Galerie pod tělem receptu. Po kliknutí se zvětší. "
                "Zobrazují se v pořadí, v jakém je zde uspořádáte; hlavní fotku vložte do Příběhu."
            ),
        ),
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

        if request.is_preview:
            prev_recipe = next_recipe = self
        else:
            siblings_list = list(self.get_siblings().live().specific())
            current_index = siblings_list.index(self)
            prev_recipe = siblings_list[current_index - 1] if current_index > 0 else siblings_list[-1]
            next_recipe = siblings_list[current_index + 1] if current_index < len(siblings_list) - 1 else siblings_list[0]            
  
        context['prev_recipe'] = prev_recipe
        context['next_recipe'] = next_recipe
        context['active_category'] = self.get_category()
        context['recipe_index_page'] = self.get_recipe_index_page()
        context["categories"] = self.get_categories()
        return context

    
class BlogPageGalleryImage(Orderable):
    page = ParentalKey(RecipePage, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ForeignKey(
        'wagtailimages.Image',
        on_delete=models.CASCADE,
        related_name='+',
        help_text="Fotka do galerie pod receptem. Na webu se zobrazí jako náhled s možností zvětšení.",
    )
    caption = models.CharField(
        blank=True,
        max_length=250,
        help_text=(
            "Volitelný popis fotky pod náhledem i při zvětšení. Slouží také jako alternativní text "
            "pro čtečky obrazovky, proto stručně popište, co na fotce je."
        ),
    )

    panels = [
        FieldPanel('image', heading="Obrázek"),
        FieldPanel('caption', heading="Popisek obrázku"),
    ]
