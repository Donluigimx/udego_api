# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-02-20 21:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Rides', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='code',
            field=models.CharField(default=11, max_length=10),
            preserve_default=False,
        ),
    ]
