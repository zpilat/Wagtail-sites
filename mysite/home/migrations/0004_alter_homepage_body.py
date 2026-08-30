from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0003_homepage_body"),
    ]

    # The temporary RichTextField -> StreamField conversion used to fail on a
    # clean database because an empty string is not valid JSON. Migration 0005
    # immediately changes the field back to RichTextField, so the intermediate
    # conversion is unnecessary. Keeping the migration as a no-op preserves the
    # migration graph and leaves databases where it is already applied intact.
    operations = []
