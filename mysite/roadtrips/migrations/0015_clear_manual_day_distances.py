import json

from django.db import migrations


def remove_manual_distance(value):
    """Remove only the obsolete summary field, preserving other stored data."""
    stored_as_string = isinstance(value, str)
    if stored_as_string:
        try:
            content = json.loads(value)
        except (TypeError, ValueError):
            return value
    elif hasattr(value, "raw_data"):
        content = list(value.raw_data)
    else:
        content = value
    if not isinstance(content, list):
        return value

    cleaned = []
    for block in content:
        if (
            isinstance(block, dict)
            and block.get("type") == "day_summary"
            and isinstance(block.get("value"), dict)
        ):
            fields = block["value"].copy()
            fields.pop("distance_km", None)
            block = {**block, "value": fields}
        cleaned.append(block)
    return json.dumps(cleaned) if stored_as_string else cleaned


def remove_manual_distances(apps, schema_editor):
    Day = apps.get_model("roadtrips", "RoadTripDayPage")
    Revision = apps.get_model("wagtailcore", "Revision")
    alias = schema_editor.connection.alias
    days = Day.objects.using(alias)
    for page in days.all().iterator():
        days.filter(pk=page.pk).update(content=remove_manual_distance(page.content))

    revisions = Revision.objects.using(alias).filter(
        content_type__app_label="roadtrips",
        content_type__model="roadtripdaypage",
    )
    for revision in revisions.iterator():
        data = revision.content
        if not isinstance(data, dict) or "content" not in data:
            continue
        revisions.filter(pk=revision.pk).update(
            content={**data, "content": remove_manual_distance(data["content"])}
        )


class Migration(migrations.Migration):
    dependencies = [("roadtrips", "0014_remove_manual_day_distance")]

    operations = [migrations.RunPython(remove_manual_distances)]
