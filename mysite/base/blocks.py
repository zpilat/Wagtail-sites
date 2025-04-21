from wagtail.blocks import (
    CharBlock,
    ChoiceBlock,
    ListBlock,
    PageChooserBlock,
    RichTextBlock,
    StreamBlock,
    StructBlock,
    TextBlock,
)
from wagtail.embeds.blocks import EmbedBlock
from wagtail.images.blocks import ImageChooserBlock


class ImageBlock(StructBlock):
    """
    Custom `StructBlock` for utilizing images with associated caption and
    attribution data
    """

    image = ImageChooserBlock(required=True, label="Obrázek")
    caption = CharBlock(required=False, label="Popisek")
    attribution = CharBlock(required=False, label="Zdroj")

    class Meta:
        icon = "image"
        template = "blocks/image_block.html"


class HeadingBlock(StructBlock):
    """
    Custom `StructBlock` that allows the user to select h2 - h4 sizes for headers
    """

    heading_text = CharBlock(classname="title", required=True, label="Text nadpisu")
    size = ChoiceBlock(
        choices=[
            ("", "Vyber velikost nadpisu"),
            ("h2", "H2"),
            ("h3", "H3"),
            ("h4", "H4"),
        ],
        blank=True,
        required=False,
        label="Velikost nadpisu",
    )

    class Meta:
        icon = "title"
        template = "blocks/heading_block.html"


class BlockQuote(StructBlock):
    """
    Custom `StructBlock` that allows the user to attribute a quote to the author
    """

    text = TextBlock(label="Citát")
    attribute_name = CharBlock(blank=True, required=False, label="např. Karel Čapek")

    class Meta:
        icon = "openquote"
        template = "blocks/blockquote.html"


class MultipleLinksBlock(StructBlock):
    title = CharBlock(
        required=False,
        default = "Přílohy:",
        help_text="Tento nadpis se zobrazí nad interními odkazy stránek s přílohami",
        label = "Nadpis bloku s přílohami",
    )
    links = ListBlock(
        PageChooserBlock(),
        label = "Odkazy"
    )                 

    class Meta:
        icon = "link"
        label = "Odkazy na přílohy"
        template = "blocks/multiple_links.html"


class IngedientsListBlock(StructBlock):
    title = CharBlock(
        required=False,
        default = "Seznam ingrediencí:",
        help_text="Tento nadpis se zobrazí nad seznamem ingrediencí",
        label = "Nadpis bloku s ingrediencemi",
    )
    ingredients_list = ListBlock(
        RichTextBlock(features=["bold", "italic", "link"]),
        min_num=2,
        max_num=15, 
        label="Seznam ingrediencí",
    )              

    class Meta:
        icon="tasks"        
        label = "Blok s ingrediencemi"
        template="blocks/ingredients_list_block.html"


class StepsListBlock(StructBlock):
    title = CharBlock(
        required=False,
        default = "Kroky receptu:",
        help_text="Tento nadpis se zobrazí nad seznamem kroků",
        label = "Nadpis bloku s kroky receptu",
    )
    steps_list = ListBlock(
        RichTextBlock(features=["bold", "italic", "link"]),
        min_num=2,
        max_num=15,     
        label="Seznam kroků",
    )         

    class Meta:
        icon="list-ol"        
        label = "Blok s kroky receptu"
        template="blocks/steps_list_block.html"


# StreamBlocks
class BaseStreamBlock(StreamBlock):
    """
    Define the custom blocks that `StreamField` will utilize
    """

    heading_block = HeadingBlock(group="Obsah", label="Nadpis")
    paragraph_block = RichTextBlock(
        icon="pilcrow", template="blocks/paragraph_block.html", group="Obsah", label="Odstavec"
    )
    image_block = ImageBlock(group="Média", label="Obrázek")
    block_quote = BlockQuote(group="Obsah", label="Citát")
    embed_block = EmbedBlock(
        help_text="Vložte URL média např. https://www.youtube.com/watch?v=SGJFWirQ3ks",
        icon="media",
        template="blocks/embed_block.html",
        group="Média",
        label="Média",        
    )
