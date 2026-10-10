from django import forms
from wagtail.blocks import (
    IntegerBlock,
    CharBlock,
    ChoiceBlock,
    FloatBlock,
    ListBlock,
    RichTextBlock,
    StreamBlock,
    StructBlock,
)

from wagtail.embeds.blocks import EmbedBlock
from wagtail.images.blocks import ImageChooserBlock

from base.blocks import BlockQuote, HeadingBlock, ImageBlock, MultipleLinksBlock, IngedientsListBlock, StepsListBlock

class RecipeStreamBlock(StreamBlock):
    heading_block = HeadingBlock(group="Obsah", label="Nadpis")
    paragraph_block = RichTextBlock(
        icon="pilcrow", template="blocks/paragraph_block.html", group="Obsah", label="Odstavec"
    )
    block_quote = BlockQuote(group="Obsah", label="Citát")
    image_block = ImageBlock(
        group="Média",
        label="Obrázek",
        help_text="Fotka v postupu na místě tohoto bloku. Popisek a zdroj se zobrazí pod fotkou; popisek slouží také jako alternativní text.",
    )
    embed_block = EmbedBlock(
        help_text="Vložte URL média např. https://www.youtube.com/watch?v=SGJFWirQ3ks",
        icon="media",
        template="blocks/embed_block.html",
        group="Média",
        label="Média",
    )
    difficulty = ChoiceBlock(
        widget=forms.RadioSelect,
        choices=[("* nízká", "Nízká"), ("** střední", "Střední"), ("*** vysoká", "Vysoká")],
        default="* nízká",
        icon="cogs",
        template="blocks/difficulty.html",        
        group="Vaření",
        label="Obtížnost",
        help_text="Zobrazí obtížnost přípravy s jednou až třemi hvězdami na místě tohoto bloku v receptu.",
    )
    ingredients_list = IngedientsListBlock(   
        group="Vaření",
        help_text="Každou surovinu včetně množství vložte jako samostatnou položku. Na webu se zobrazí seznam s odrážkami (2 až 15 položek).",
    )
    steps_list = StepsListBlock(    
        group="Vaření",
        help_text="Každý krok přípravy vložte jako samostatnou položku. Na webu se automaticky očíslují podle zdejšího pořadí (2 až 15 kroků).",
    )
    links = MultipleLinksBlock(
        group = "Vaření",
        help_text="Vyberte související stránky, např. recept na vhodnou přílohu. Zobrazí se jako karty s odkazy na místě tohoto bloku.",
    )

    class Meta:
        label = "Bloky receptu"
