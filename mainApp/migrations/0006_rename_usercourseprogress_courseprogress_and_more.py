# Generated by Django 5.1.3 on 2024-12-07 08:53

import datetime
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainApp', '0005_course_usercourseprogress'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name='UserCourseProgress',
            new_name='CourseProgress',
        ),
        migrations.RenameField(
            model_name='course',
            old_name='title',
            new_name='name',
        ),
        migrations.RemoveField(
            model_name='course',
            name='content',
        ),
        migrations.RemoveField(
            model_name='course',
            name='hardness',
        ),
        migrations.AddField(
            model_name='course',
            name='slug',
            field=models.SlugField(default=datetime.datetime(2024, 12, 7, 8, 53, 20, 671205, tzinfo=datetime.timezone.utc), unique=True),
            preserve_default=False,
        ),
    ]