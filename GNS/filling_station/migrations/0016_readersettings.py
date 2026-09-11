from django.db import migrations, models


def seed_reader_settings(apps, schema_editor):
    ReaderSettings = apps.get_model('filling_station', 'ReaderSettings')
    for number, need_cache in ((7, True), (8, True)):
        ReaderSettings.objects.get_or_create(
            number=number,
            defaults={
                'status': f'Ридер {number}',
                'need_cache': need_cache,
                'function': 'p',
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('filling_station', '0015_delete_ttn_alter_balloon_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReaderSettings',
            fields=[
                ('number', models.IntegerField(primary_key=True, serialize=False, verbose_name='Номер считывателя')),
                ('status', models.CharField(blank=True, max_length=100, null=True, verbose_name='Статус')),
                ('ip', models.CharField(blank=True, max_length=15, null=True, verbose_name='IP адрес')),
                ('port', models.IntegerField(default=10001, verbose_name='Порт')),
                (
                    'function',
                    models.CharField(
                        choices=[('l', 'Приёмка'), ('u', 'Отгрузка'), ('p', 'Нет')],
                        default='p',
                        verbose_name='Функция',
                    ),
                ),
                ('need_cache', models.BooleanField(default=False, verbose_name='Добавлять в кеш')),
            ],
            options={
                'verbose_name': 'Настройки считывателей',
                'verbose_name_plural': 'Настройки считывателей',
                'ordering': ['number'],
            },
        ),
        migrations.RunPython(seed_reader_settings, migrations.RunPython.noop),
    ]
