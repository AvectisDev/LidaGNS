# Unify Carousel/CarouselSettings with Pinsk TCP stack + Lida size classification

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


def migrate_change_at(apps, schema_editor):
    Carousel = apps.get_model('carousel', 'Carousel')
    for row in Carousel.objects.all().iterator():
        change_date = getattr(row, 'change_date', None)
        change_time = getattr(row, 'change_time', None)
        if change_date is not None and change_time is not None:
            row.change_at = django.utils.timezone.datetime.combine(
                change_date,
                change_time,
            )
            if django.utils.timezone.is_naive(row.change_at):
                row.change_at = django.utils.timezone.make_aware(row.change_at)
        else:
            row.change_at = django.utils.timezone.now()
        row.save(update_fields=['change_at'])


def seed_carousel_settings(apps, schema_editor):
    CarouselSettings = apps.get_model('carousel', 'CarouselSettings')
    ReaderSettings = apps.get_model('filling_station', 'ReaderSettings')
    reader_8 = ReaderSettings.objects.filter(number=8).first()

    rows = list(CarouselSettings.objects.all().order_by('pk'))
    if not rows:
        CarouselSettings.objects.create(
            number=1,
            name='Карусель 1',
            tcp_host='',
            tcp_port=4001,
            rfid_reader=reader_8,
            is_active=False,
            classify_size_by_weight=True,
            size_27_empty_weight_max_g=16000,
            user=None,
        )
        return

    for index, settings in enumerate(rows, start=1):
        settings.number = index
        if not settings.name:
            settings.name = f'Карусель {index}'
        settings.is_active = False
        settings.classify_size_by_weight = True
        settings.size_27_empty_weight_max_g = 16000
        if settings.rfid_reader_id is None and reader_8 is not None:
            settings.rfid_reader = reader_8
        settings.save()


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('carousel', '0001_initial'),
        ('filling_station', '0016_readersettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='carousel',
            name='change_at',
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                verbose_name='Дата и время изменений',
            ),
        ),
        migrations.RunPython(migrate_change_at, migrations.RunPython.noop),
        migrations.RemoveField(model_name='carousel', name='change_date'),
        migrations.RemoveField(model_name='carousel', name='change_time'),
        migrations.AlterField(
            model_name='carousel',
            name='change_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Дата и время изменений'),
        ),
        migrations.AlterModelOptions(
            name='carousel',
            options={
                'ordering': ['-change_at'],
                'verbose_name': 'Карусель',
                'verbose_name_plural': 'Карусель',
            },
        ),
        migrations.AddField(
            model_name='carouselsettings',
            name='min_balloon_weight_from',
            field=models.FloatField(default=15.6, verbose_name='Минимальный вес баллона (от)'),
        ),
        migrations.AddField(
            model_name='carouselsettings',
            name='min_balloon_weight_to',
            field=models.FloatField(default=17.8, verbose_name='Минимальный вес баллона (до)'),
        ),
        migrations.AddField(
            model_name='carouselsettings',
            name='max_balloon_weight_from',
            field=models.FloatField(default=44.0, verbose_name='Максимальный вес баллона (от)'),
        ),
        migrations.AddField(
            model_name='carouselsettings',
            name='max_balloon_weight_to',
            field=models.FloatField(default=46.5, verbose_name='Максимальный вес баллона (до)'),
        ),
        migrations.AddField(
            model_name='carouselsettings',
            name='passport_weight_diff_from',
            field=models.FloatField(default=0.0, verbose_name='Разница паспортных весов (от)'),
        ),
        migrations.AddField(
            model_name='carouselsettings',
            name='passport_weight_diff_to',
            field=models.FloatField(default=21.5, verbose_name='Разница паспортных весов (до)'),
        ),
        migrations.AddField(
            model_name='carouselsettings',
            name='number',
            field=models.IntegerField(null=True, verbose_name='Номер карусели'),
        ),
        migrations.AddField(
            model_name='carouselsettings',
            name='name',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='Название'),
        ),
        migrations.AddField(
            model_name='carouselsettings',
            name='tcp_host',
            field=models.CharField(blank=True, default='', max_length=15, verbose_name='IP NPort'),
        ),
        migrations.AddField(
            model_name='carouselsettings',
            name='tcp_port',
            field=models.IntegerField(default=4001, verbose_name='TCP-порт NPort'),
        ),
        migrations.AddField(
            model_name='carouselsettings',
            name='rfid_reader',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='carousels',
                to='filling_station.readersettings',
                verbose_name='RFID-считыватель',
            ),
        ),
        migrations.AddField(
            model_name='carouselsettings',
            name='is_active',
            field=models.BooleanField(default=False, verbose_name='Активна (listener)'),
        ),
        migrations.AddField(
            model_name='carouselsettings',
            name='classify_size_by_weight',
            field=models.BooleanField(
                default=True,
                verbose_name='Определять объём (27/50) по весу пустого баллона',
            ),
        ),
        migrations.AddField(
            model_name='carouselsettings',
            name='size_27_empty_weight_max_g',
            field=models.PositiveIntegerField(
                default=16000,
                verbose_name='Макс. вес пустого 27 л, г',
            ),
        ),
        migrations.RunPython(seed_carousel_settings, migrations.RunPython.noop),
    ]
