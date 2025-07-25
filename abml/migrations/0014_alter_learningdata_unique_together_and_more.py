# Generated by Django 4.2.16 on 2025-07-24 14:12

from django.db import migrations, models
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('abml', '0013_learningiteration_mscore'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='learningdata',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='learningdata',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='learningdata',
            name='session_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
