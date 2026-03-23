from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ListingPhoto',
        ),
    ]
