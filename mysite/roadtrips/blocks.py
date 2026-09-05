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
