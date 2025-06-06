# Generated by Django 5.1.4 on 2025-05-19 20:59

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('platea', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='exchangerate',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='exchangerate',
            name='rate_compra',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='exchangerate',
            name='rate_venta',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True),
        ),
    ]
