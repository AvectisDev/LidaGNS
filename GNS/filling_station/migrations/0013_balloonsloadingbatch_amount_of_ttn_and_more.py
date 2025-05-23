# Generated by Django 5.0.6 on 2025-04-17 21:32

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filling_station', '0012_carousel_carousel_number_carousel_size'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='balloonsloadingbatch',
            name='amount_of_ttn',
            field=models.IntegerField(blank=True, null=True, verbose_name='Количество баллонов по ТТН'),
        ),
        migrations.AddField(
            model_name='balloonsunloadingbatch',
            name='amount_of_ttn',
            field=models.IntegerField(blank=True, null=True, verbose_name='Количество баллонов по ТТН'),
        ),
        migrations.AlterField(
            model_name='balloon',
            name='user',
            field=models.ForeignKey(default=1, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Пользователь'),
        ),
        migrations.AlterField(
            model_name='balloonevent',
            name='user',
            field=models.ForeignKey(db_constraint=False, default=1, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь'),
        ),
        migrations.AlterField(
            model_name='balloonsloadingbatch',
            name='ttn',
            field=models.CharField(default='', max_length=20, verbose_name='Номер ТТН'),
        ),
        migrations.AlterField(
            model_name='balloonsunloadingbatch',
            name='ttn',
            field=models.CharField(default='', max_length=20, verbose_name='Номер ТТН'),
        ),
        migrations.DeleteModel(
            name='AutoGasBatch',
        ),
    ]
