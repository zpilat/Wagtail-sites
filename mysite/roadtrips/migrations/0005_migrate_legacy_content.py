import json
import uuid

from django.db import migrations


def make_block(block_type, value):
    return {
        "type": block_type,
        "value": value,
        "id": str(uuid.uuid4()),
    }


def build_content(body, mapy_photos, gallery_items):
    content = []

    if isinstance(mapy_photos, str):
        mapy_photos = json.loads(mapy_photos) if mapy_photos else []
    if isinstance(gallery_items, str):
        gallery_items = json.loads(gallery_items) if gallery_items else []

    if body:
        content.append(make_block("text", str(body)))

    for photo in mapy_photos:
        if photo.get("type") == "mapy_photo":
            content.append(make_block("mapy_photo", photo.get("value", {})))

    for gallery_item in gallery_items:
        if isinstance(gallery_item, dict):
            image_id = gallery_item.get("image")
            caption = gallery_item.get("caption", "")
        else:
            image_id = gallery_item.image_id
            caption = gallery_item.caption

        if not image_id:
            continue

        content.append(
            make_block(
                "image",
                {
                    "image": image_id,
                    "caption": caption,
                    "attribution": "",
                },
            )
        )

    return content


def migrate_page_content(page, gallery_items):
    page.content = build_content(
        page.body,
        page.mapy_photos.get_prep_value(),
        gallery_items,
    )


def migrate_revisions(Revision, model_name, is_day=False):
    revisions = Revision.objects.filter(
        content_type__app_label="roadtrips",
        content_type__model=model_name,
    )

    for revision in revisions.iterator():
        data = revision.content
        gallery_items = data.get("gallery_images", [])
        data["content"] = json.dumps(
            build_content(
                data.get("body", ""),
                data.get("mapy_photos", []),
                gallery_items,
            )
        )

        if is_day and gallery_items and not data.get("image"):
            data["image"] = gallery_items[0].get("image")

        data.pop("body", None)
        data.pop("mapy_photos", None)
        data.pop("gallery_images", None)
        revision.content = data
        revision.save(update_fields=["content"])


def migrate_legacy_content(apps, schema_editor):
    RoadTripPage = apps.get_model("roadtrips", "RoadTripPage")
    RoadTripDayPage = apps.get_model("roadtrips", "RoadTripDayPage")
    RoadTripGalleryImage = apps.get_model("roadtrips", "RoadTripGalleryImage")
    RoadTripDayGalleryImage = apps.get_model(
        "roadtrips", "RoadTripDayGalleryImage"
    )
    Revision = apps.get_model("wagtailcore", "Revision")

    for page in RoadTripPage.objects.all().iterator():
        gallery_items = RoadTripGalleryImage.objects.filter(page_id=page.pk).order_by(
            "sort_order", "pk"
        )
        migrate_page_content(page, gallery_items)
        page.save(update_fields=["content"])

    for page in RoadTripDayPage.objects.all().iterator():
        gallery_items = list(
            RoadTripDayGalleryImage.objects.filter(page_id=page.pk).order_by(
                "sort_order", "pk"
            )
        )
        migrate_page_content(page, gallery_items)

        if gallery_items and not page.image_id:
            page.image_id = gallery_items[0].image_id

        page.save(update_fields=["content", "image"])

    migrate_revisions(Revision, "roadtrippage")
    migrate_revisions(Revision, "roadtripdaypage", is_day=True)


class Migration(migrations.Migration):

    dependencies = [
        ("roadtrips", "0004_roadtripdaypage_content_roadtripdaypage_image_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_content, migrations.RunPython.noop),
    ]
