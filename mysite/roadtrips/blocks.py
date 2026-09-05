from pathlib import Path

from django.core.exceptions import ValidationError
from wagtail import blocks
from wagtail.documents.blocks import DocumentChooserBlock

from base.blocks import ImageBlock


class RoadTripImageBlock(ImageBlock):
    link_url = blocks.URLBlock(
        required=False,
        label="Odkaz po kliknutí",
        help_text=(
            "Volitelná cílová adresa obrázku, například sdílecí odkaz "
            "https://mapy.com/s/hejunakope."
        ),
    )

    class Meta:
        icon = "image"
        label = "Vlastní obrázek"
        template = "blocks/road_trip_image_block.html"


class RoadTripVideoBlock(blocks.StructBlock):
    video = DocumentChooserBlock(
        label="Video",
        help_text="Pro nejlepší kompatibilitu použijte formát MP4 nebo WebM.",
    )
    caption = blocks.CharBlock(required=False, label="Popisek")

    allowed_extensions = {".m4v", ".mov", ".mp4", ".ogv", ".webm"}

    def clean(self, value):
        result = super().clean(value)
        extension = Path(result["video"].file.name).suffix.lower()
        if extension not in self.allowed_extensions:
            raise blocks.StructBlockValidationError(
                block_errors={
                    "video": ValidationError(
                        "Vyberte video ve formátu MP4, WebM, OGV, MOV nebo M4V."
                    )
                }
            )
        return result

    class Meta:
        icon = "media"
        label = "Vlastní video"
        template = "blocks/road_trip_video_block.html"


class RoadTripContentBlock(blocks.StreamBlock):
    text = blocks.RichTextBlock(
        icon="pilcrow",
        label="Text",
        template="blocks/paragraph_block.html",
    )
    image = RoadTripImageBlock()
    video = RoadTripVideoBlock()

    class Meta:
        label = "Obsah autovandru"


class RoadTripDaySummaryBlock(blocks.StructBlock):
    heading = blocks.CharBlock(label="Nadpis", default="Přehled dne")
    distance_km = blocks.DecimalBlock(
        required=False,
        min_value=0,
        max_digits=7,
        decimal_places=1,
        label="Ujeté kilometry",
        help_text="Vzdálenost za tento den. Pro den bez přejezdu zadejte 0.",
    )
    countries = blocks.ListBlock(
        blocks.CharBlock(label="Země"),
        required=False,
        default=[],
        label="Navštívené země",
        help_text="Přidejte země v pořadí, ve kterém jste jimi projížděli.",
    )
    seas = blocks.ListBlock(
        blocks.CharBlock(label="Moře"),
        required=False,
        default=[],
        label="Navštívená moře",
        help_text="Přidejte moře v pořadí, ve kterém jste je navštívili.",
    )
    route = blocks.CharBlock(
        required=False, label="Trasa", help_text="Například Praha → Drážďany → Berlín."
    )
    driving_time = blocks.CharBlock(
        required=False, label="Čas na cestě", help_text="Například 4 h 30 min."
    )
    overnight_stay = blocks.CharBlock(required=False, label="Místo noclehu")
    extra_items = blocks.ListBlock(
        blocks.StructBlock(
            [
                ("label", blocks.CharBlock(label="Název údaje")),
                ("value", blocks.CharBlock(label="Hodnota")),
            ]
        ),
        required=False,
        default=[],
        label="Další údaje",
        help_text="Například Počasí: Slunečno, 24 °C nebo Pěšky: 8 km.",
    )
    note = blocks.TextBlock(required=False, label="Poznámka")

    class Meta:
        icon = "list-ul"
        label = "Přehled dne"
        template = "blocks/road_trip_day_summary.html"
        help_text = "Vložte na konec zápisu dne. Nevyplněné údaje se nezobrazí."


class RoadTripDayContentBlock(RoadTripContentBlock):
    day_summary = RoadTripDaySummaryBlock()
