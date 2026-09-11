# Unify Carousel/CarouselSettings with Pinsk TCP stack + Lida size classification.
# Идемпотентна: безопасно при частичном прошлом прогоне (колонка change_at уже есть).

import django.db.models.deletion
from django.db import migrations, models


def _columns(schema_editor, table: str) -> set[str]:
    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(
            cursor, table
        )
    return {col.name for col in description}


def ensure_change_at(apps, schema_editor):
    table = 'carousel_carousel'
    cols = _columns(schema_editor, table)
    if 'change_at' not in cols:
        schema_editor.execute(
            f'ALTER TABLE {table} ADD COLUMN change_at timestamp with time zone '
            f'DEFAULT CURRENT_TIMESTAMP NOT NULL'
        )
        cols = _columns(schema_editor, table)

    # Одним UPDATE: из старых date+time, если колонки ещё есть
    if 'change_date' in cols and 'change_time' in cols:
        schema_editor.execute(
            f"""
            UPDATE {table}
            SET change_at = (
                (change_date + change_time)
                AT TIME ZONE 'UTC'
            )
            WHERE change_date IS NOT NULL AND change_time IS NOT NULL
            """
        )


def drop_legacy_date_fields(apps, schema_editor):
    table = 'carousel_carousel'
    cols = _columns(schema_editor, table)
    if 'change_date' in cols:
        schema_editor.execute(f'ALTER TABLE {table} DROP COLUMN change_date')
    if 'change_time' in cols:
        schema_editor.execute(f'ALTER TABLE {table} DROP COLUMN change_time')


def add_settings_columns(apps, schema_editor):
    table = 'carousel_carouselsettings'
    cols = _columns(schema_editor, table)
    statements = []
    if 'min_balloon_weight_from' not in cols:
        statements.append(
            'ADD COLUMN min_balloon_weight_from double precision DEFAULT 15.6 NOT NULL'
        )
    if 'min_balloon_weight_to' not in cols:
        statements.append(
            'ADD COLUMN min_balloon_weight_to double precision DEFAULT 17.8 NOT NULL'
        )
    if 'max_balloon_weight_from' not in cols:
        statements.append(
            'ADD COLUMN max_balloon_weight_from double precision DEFAULT 44.0 NOT NULL'
        )
    if 'max_balloon_weight_to' not in cols:
        statements.append(
            'ADD COLUMN max_balloon_weight_to double precision DEFAULT 46.5 NOT NULL'
        )
    if 'passport_weight_diff_from' not in cols:
        statements.append(
            'ADD COLUMN passport_weight_diff_from double precision DEFAULT 0.0 NOT NULL'
        )
    if 'passport_weight_diff_to' not in cols:
        statements.append(
            'ADD COLUMN passport_weight_diff_to double precision DEFAULT 21.5 NOT NULL'
        )
    if 'number' not in cols:
        statements.append('ADD COLUMN number integer NULL')
    if 'name' not in cols:
        statements.append(
            "ADD COLUMN name varchar(100) DEFAULT '' NOT NULL"
        )
    if 'tcp_host' not in cols:
        statements.append(
            "ADD COLUMN tcp_host varchar(15) DEFAULT '' NOT NULL"
        )
    if 'tcp_port' not in cols:
        statements.append('ADD COLUMN tcp_port integer DEFAULT 4001 NOT NULL')
    if 'rfid_reader_id' not in cols:
        statements.append('ADD COLUMN rfid_reader_id integer NULL')
    if 'is_active' not in cols:
        statements.append('ADD COLUMN is_active boolean DEFAULT false NOT NULL')
    if 'classify_size_by_weight' not in cols:
        statements.append(
            'ADD COLUMN classify_size_by_weight boolean DEFAULT true NOT NULL'
        )
    if 'size_27_empty_weight_max_g' not in cols:
        statements.append(
            'ADD COLUMN size_27_empty_weight_max_g integer DEFAULT 16000 NOT NULL'
        )

    for fragment in statements:
        schema_editor.execute(f'ALTER TABLE {table} {fragment}')

    # FK на ReaderSettings, если ещё нет
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1 FROM information_schema.table_constraints
            WHERE table_name = %s AND constraint_type = 'FOREIGN KEY'
              AND constraint_name LIKE %s
            """,
            [table, '%rfid_reader%'],
        )
        has_fk = cursor.fetchone() is not None
    if not has_fk and 'rfid_reader_id' in _columns(schema_editor, table):
        schema_editor.execute(
            f'ALTER TABLE {table} ADD CONSTRAINT '
            f'carousel_carouselsettings_rfid_reader_id_fk '
            f'FOREIGN KEY (rfid_reader_id) '
            f'REFERENCES filling_station_readersettings(number) '
            f'DEFERRABLE INITIALLY DEFERRED'
        )


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
        if not getattr(settings, 'name', None):
            settings.name = f'Карусель {index}'
        settings.is_active = False
        settings.classify_size_by_weight = True
        settings.size_27_empty_weight_max_g = 16000
        if getattr(settings, 'rfid_reader_id', None) is None and reader_8 is not None:
            settings.rfid_reader = reader_8
        settings.save()


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('carousel', '0001_initial'),
        ('filling_station', '0016_readersettings'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='carousel',
                    name='change_at',
                    field=models.DateTimeField(
                        auto_now=True,
                        verbose_name='Дата и время изменений',
                    ),
                ),
                migrations.RemoveField(model_name='carousel', name='change_date'),
                migrations.RemoveField(model_name='carousel', name='change_time'),
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
                    field=models.FloatField(
                        default=15.6, verbose_name='Минимальный вес баллона (от)'
                    ),
                ),
                migrations.AddField(
                    model_name='carouselsettings',
                    name='min_balloon_weight_to',
                    field=models.FloatField(
                        default=17.8, verbose_name='Минимальный вес баллона (до)'
                    ),
                ),
                migrations.AddField(
                    model_name='carouselsettings',
                    name='max_balloon_weight_from',
                    field=models.FloatField(
                        default=44.0, verbose_name='Максимальный вес баллона (от)'
                    ),
                ),
                migrations.AddField(
                    model_name='carouselsettings',
                    name='max_balloon_weight_to',
                    field=models.FloatField(
                        default=46.5, verbose_name='Максимальный вес баллона (до)'
                    ),
                ),
                migrations.AddField(
                    model_name='carouselsettings',
                    name='passport_weight_diff_from',
                    field=models.FloatField(
                        default=0.0, verbose_name='Разница паспортных весов (от)'
                    ),
                ),
                migrations.AddField(
                    model_name='carouselsettings',
                    name='passport_weight_diff_to',
                    field=models.FloatField(
                        default=21.5, verbose_name='Разница паспортных весов (до)'
                    ),
                ),
                migrations.AddField(
                    model_name='carouselsettings',
                    name='number',
                    field=models.IntegerField(null=True, verbose_name='Номер карусели'),
                ),
                migrations.AddField(
                    model_name='carouselsettings',
                    name='name',
                    field=models.CharField(
                        blank=True, default='', max_length=100, verbose_name='Название'
                    ),
                ),
                migrations.AddField(
                    model_name='carouselsettings',
                    name='tcp_host',
                    field=models.CharField(
                        blank=True, default='', max_length=15, verbose_name='IP NPort'
                    ),
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
                    field=models.BooleanField(
                        default=False, verbose_name='Активна (listener)'
                    ),
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
            ],
            database_operations=[
                migrations.RunPython(ensure_change_at, migrations.RunPython.noop),
                migrations.RunPython(drop_legacy_date_fields, migrations.RunPython.noop),
                migrations.RunPython(add_settings_columns, migrations.RunPython.noop),
            ],
        ),
        migrations.RunPython(seed_carousel_settings, migrations.RunPython.noop),
    ]
