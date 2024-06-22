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

from base.blocks import BlockQuote, HeadingBlock, ImageBlock

class RecipeStreamBlock(StreamBlock):
    heading_block = HeadingBlock(group="Obsah", label="Nadpis")
    paragraph_block = RichTextBlock(
        icon="pilcrow", template="blocks/paragraph_block.html", group="Obsah", label="Odstavec"
    )
    block_quote = BlockQuote(group="Obsah", label="Citát")
    image_block = ImageBlock(group="Média", label="Obrázek")
    embed_block = EmbedBlock(
        help_text="Vložte URL např. https://www.youtube.com/watch?v=SGJFWirQ3ks",
        icon="media",
        template="blocks/embed_block.html",
        group="Média",
        label="Embed",
    )
    difficulty = ChoiceBlock(
        widget=forms.RadioSelect,
        choices=[("Nízká *", "Nízká"), ("Střední **", "Střední"), ("Vysoká ***", "Vysoká")],
        default="Nízká obtížnost",
        icon="cogs",
        group="Vaření",
        label="Obtížnost",
    )
    ingredients_list = ListBlock(
        RichTextBlock(features=["bold", "italic", "link"]),
        min_num=2,
        max_num=15,
        icon="list-ol",
        group="Vaření",
        label="Seznam ingrediencí",
    )
    steps_list = ListBlock(
        RichTextBlock(features=["bold", "italic", "link"]),
        min_num=2,
        max_num=15,
        icon="tasks",
        group="Vaření",
        label="Seznam kroků",
    )

    class Meta:
        label = "Bloky receptu"
