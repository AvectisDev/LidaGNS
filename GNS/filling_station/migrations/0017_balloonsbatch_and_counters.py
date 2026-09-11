"""
Единая модель партий ``BalloonsBatch`` и счётчики считывателей.

Переносит данные из legacy-таблиц ``BalloonsLoadingBatch``/``BalloonsUnloadingBatch``:
пара дата+время сворачивается в один ``DateTimeField``, ``is_active`` — в ``status``,
строковый ``ttn`` — в целочисленный ``ttn_id``. Идентификаторы разводятся через
смещение (``pk * 2`` для приёмки, ``pk * 2 + 1`` для отгрузки), чтобы партии обоих
типов ужились в одной таблице; в конце сбрасывается sequence.
"""

import datetime

import django.db.models.deletion
from django.conf import settings
from django.core.management.color import no_style
from django.db import migrations, models
from django.utils import timezone

LEGACY_SOURCES = (
    ('BalloonsLoadingBatch', 'l', 0),
    ('BalloonsUnloadingBatch', 'u', 1),
)


def _combine(date_value, time_value):
    """Собирает дату и время legacy-партии в один datetime с учётом USE_TZ."""
    if not date_value:
        return None
    value = datetime.datetime.combine(date_value, time_value or datetime.time.min)
    if settings.USE_TZ and timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value


def _copy_batches(apps, schema_editor):
    """Переносит legacy-партии приёмки и отгрузки в ``BalloonsBatch``."""
    BalloonsBatch = apps.get_model('filling_station', 'BalloonsBatch')
    Truck = apps.get_model('filling_station', 'Truck')
    Trailer = apps.get_model('filling_station', 'Trailer')
    User = apps.get_model(settings.AUTH_USER_MODEL)

    truck_ids = set(Truck.objects.values_list('id', flat=True))
    trailer_ids = set(Trailer.objects.values_list('id', flat=True))
    user_ids = set(User.objects.values_list('id', flat=True))

    counters = {'copied': 0, 'skipped': 0}
    for model_name, batch_type, id_offset in LEGACY_SOURCES:
        source_model = apps.get_model('filling_station', model_name)
        for old in source_model.objects.all().iterator():
            # Legacy-таблицы используют DO_NOTHING, поэтому ссылки могут быть битыми,
            # а новая модель защищена внешними ключами PROTECT/SET_NULL.
            if old.truck_id not in truck_ids:
                counters['skipped'] += 1
                print(
                    f'0017: партия {model_name} #{old.pk} пропущена — '
                    f'нет грузовика id={old.truck_id}'
                )
                continue

            ttn_text = (old.ttn or '').strip()
            new = BalloonsBatch.objects.create(
                id=old.pk * 2 + id_offset,
                batch_type=batch_type,
                completed_at=_combine(old.end_date, old.end_time),
                truck_id=old.truck_id,
                trailer_id=old.trailer_id if old.trailer_id in trailer_ids else None,
                reader_number=old.reader_number,
                amount_of_rfid=old.amount_of_rfid or 0,
                amount_of_sensor=0,
                amount_of_ttn=old.amount_of_ttn or 0,
                amount_of_5_liters=old.amount_of_5_liters or 0,
                amount_of_12_liters=old.amount_of_12_liters or 0,
                amount_of_27_liters=old.amount_of_27_liters or 0,
                amount_of_50_liters=old.amount_of_50_liters or 0,
                gas_amount=old.gas_amount,
                status='active' if old.is_active else 'completed',
                ttn_id=int(ttn_text) if ttn_text.isdigit() else 0,
                balloons_type='e',
                user_id=old.user_id if old.user_id in user_ids else None,
            )
            # started_at объявлен как auto_now_add, поэтому пишется отдельным UPDATE.
            BalloonsBatch.objects.filter(pk=new.pk).update(
                started_at=_combine(old.begin_date, old.begin_time)
            )
            new.balloon_list.set(old.balloon_list.all())
            counters['copied'] += 1

    print(f"0017: перенесено партий — {counters['copied']}, пропущено — {counters['skipped']}")

    statements = schema_editor.connection.ops.sequence_reset_sql(no_style(), [BalloonsBatch])
    with schema_editor.connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


def _delete_copied_batches(apps, schema_editor):
    """Откат переноса: legacy-таблицы не менялись, поэтому достаточно очистить новую."""
    apps.get_model('filling_station', 'BalloonsBatch').objects.all().delete()


def _create_warehouse_counter(apps, schema_editor):
    """Создаёт единственную строку свода по складу (pk=1), с которой работают счётчики."""
    TotalReadersCounter = apps.get_model('filling_station', 'TotalReadersCounter')
    TotalReadersCounter.objects.get_or_create(pk=1, defaults={'total_empty': 0, 'total_full': 0})


def _delete_warehouse_counter(apps, schema_editor):
    """Откат: удаляет строку свода по складу."""
    apps.get_model('filling_station', 'TotalReadersCounter').objects.filter(pk=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('filling_station', '0016_readersettings'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TotalReadersCounter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_empty', models.IntegerField(default=0, verbose_name='Всего пустых баллонов')),
                ('total_full', models.IntegerField(default=0, verbose_name='Всего полных баллонов')),
                ('changed_at', models.DateTimeField(auto_now=True, verbose_name='Дата последнего изменения')),
            ],
            options={
                'verbose_name': 'Свод по складу',
                'verbose_name_plural': 'Свод по складу',
                'ordering': ['-changed_at'],
            },
        ),
        migrations.CreateModel(
            name='BalloonsBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch_type', models.CharField(choices=[('l', 'Приёмка'), ('u', 'Отгрузка')], default='l', verbose_name='Тип партии')),
                ('started_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата и время начала')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата и время окончания')),
                ('reader_number', models.IntegerField(blank=True, null=True, verbose_name='Номер считывателя')),
                ('amount_of_rfid', models.IntegerField(default=0, verbose_name='Количество баллонов по rfid')),
                ('amount_of_sensor', models.IntegerField(default=0, verbose_name='Количество баллонов по датчику')),
                ('amount_of_ttn', models.IntegerField(default=0, verbose_name='Количество баллонов по электронной ТТН')),
                ('amount_of_5_liters', models.IntegerField(default=0, verbose_name='Количество 5л баллонов')),
                ('amount_of_12_liters', models.IntegerField(default=0, verbose_name='Количество 12л баллонов')),
                ('amount_of_27_liters', models.IntegerField(default=0, verbose_name='Количество 27л баллонов')),
                ('amount_of_50_liters', models.IntegerField(default=0, verbose_name='Количество 50л баллонов')),
                ('gas_amount', models.FloatField(blank=True, null=True, verbose_name='Количество газа')),
                ('status', models.CharField(choices=[('active', 'В работе'), ('paused', 'Приостановлена'), ('completed', 'Завершена'), ('miriada_error', 'Завершена, ошибка Мириады')], db_index=True, default='paused', max_length=20, verbose_name='Статус партии')),
                ('miriada_close_failed', models.BooleanField(default=False, verbose_name='Ошибка закрытия ТТН в Мириаде')),
                ('miriada_error_message', models.CharField(blank=True, max_length=200, null=True, verbose_name='Текст ошибки при неудачном закрытии ТТН')),
                ('miriada_balloons_sent', models.BooleanField(default=False, verbose_name='Статусы баллонов отправлены в Мириаду')),
                ('ttn_id', models.IntegerField(default=0, verbose_name='ID ТТН')),
                ('balloons_type', models.CharField(choices=[('e', 'Пустой'), ('f', 'Полный')], default='e', verbose_name='Пустой/полный')),
                ('balloon_list', models.ManyToManyField(blank=True, to='filling_station.balloon', verbose_name='Список баллонов')),
                ('trailer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='filling_station.trailer', verbose_name='Прицеп')),
                ('truck', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='filling_station.truck', verbose_name='Автомобиль')),
                ('user', models.ForeignKey(default=1, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Партия баллонов',
                'verbose_name_plural': 'Партии баллонов',
                'ordering': ['-started_at'],
            },
        ),
        migrations.CreateModel(
            name='DailyReaderCounter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day', models.DateField(db_index=True, verbose_name='Дата')),
                ('amount_of_rfid', models.IntegerField(default=0, verbose_name='Баллонов по RFID')),
                ('amount_of_sensor', models.IntegerField(default=0, verbose_name='Баллонов по сенсору')),
                ('change_at', models.DateTimeField(auto_now=True, verbose_name='Дата последнего изменения')),
                ('number', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='daily_counters', to='filling_station.readersettings', verbose_name='Номер считывателя')),
            ],
            options={
                'verbose_name': 'Счетчики по ридерам за день',
                'verbose_name_plural': 'Счетчики по ридерам за день',
                'ordering': ['-day'],
                'constraints': [models.UniqueConstraint(fields=('number', 'day'), name='uniq_number_day')],
            },
        ),
        migrations.RunPython(_copy_batches, _delete_copied_batches),
        migrations.RunPython(_create_warehouse_counter, _delete_warehouse_counter),
    ]
