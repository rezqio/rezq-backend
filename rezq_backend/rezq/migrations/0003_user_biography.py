# Generated by Django 2.1.7 on 2019-03-01 05:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rezq', '0002_auto_20190213_0013'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='biography',
            field=models.TextField(blank=True, default=''),
        ),
    ]
