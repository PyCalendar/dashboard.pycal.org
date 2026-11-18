# The site keeps no data of GitHub for now: the repositories, issues, pull requests and
# installations are removed, with the preferences that were based on them.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pycal_dashboard', '0002_remove_label_change'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Item',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='watched',
        ),
        migrations.DeleteModel(
            name='Repository',
        ),
        migrations.DeleteModel(
            name='Installation',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='days',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='email_digest',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='show_drafts',
        ),
        migrations.AddField(
            model_name='profile',
            name='email_notifications',
            field=models.BooleanField(default=True),
        ),
    ]
