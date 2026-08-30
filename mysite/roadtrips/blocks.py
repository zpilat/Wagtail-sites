from wagtail import blocks


class MapyPhotoBlock(blocks.StructBlock):
    image_url = blocks.URLBlock(label="URL obrázku")
    mapy_url = blocks.URLBlock(label="Odkaz na Mapy.com")
    caption = blocks.CharBlock(required=False, label="Popisek")

    class Meta:
        icon = "image"
        label = "Fotografie z Mapy.com"
        template = "blocks/mapy_photo_block.html"
