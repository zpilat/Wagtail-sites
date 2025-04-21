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
    image_block = ImageBlock(group="Média", label="Obrázek")
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
    )
    ingredients_list = IngedientsListBlock(   
        group="Vaření",
    )
    steps_list = StepsListBlock(    
        group="Vaření",
    )
    links = MultipleLinksBlock(
        group = "Vaření"
    )

    class Meta:
        label = "Bloky receptu"
