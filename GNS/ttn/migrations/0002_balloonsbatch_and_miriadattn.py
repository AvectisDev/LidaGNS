import django.db.models.deletion
from django.db import migrations, models


def _map_batch_foreign_keys(apps, schema_editor):
    BalloonTtn = apps.get_model('ttn', 'BalloonTtn')
    for ttn in BalloonTtn.objects.all().iterator():
        updates = {}
        if ttn.loading_batch_id:
            updates['loading_batch_new_id'] = ttn.loading_batch_id * 2
        if ttn.unloading_batch_id:
            updates['unloading_batch_new_id'] = ttn.unloading_batch_id * 2 + 1
        if updates:
            BalloonTtn.objects.filter(pk=ttn.pk).update(**updates)


class Migration(migrations.Migration):
    dependencies = [
        ('filling_station', '0017_balloonsbatch_and_counters'),
        ('ttn', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MiriadaTtn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ttn_id', models.IntegerField(unique=True, verbose_name='ID ТТН в Мириаде')),
                ('name', models.CharField(max_length=100, verbose_name='Номер ТТН')),
                ('auto', models.CharField(max_length=50, verbose_name='Номер автомобиля')),
                ('date', models.DateField(blank=True, null=True, verbose_name='Дата ТТН')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления записи')),
            ],
            options={
                'verbose_name': 'ТТН из Мириады',
                'verbose_name_plural': 'ТТН из Мириады',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddField(
            model_name='balloonttn',
            name='loading_batch_new',
            field=models.ForeignKey(
                blank=True, limit_choices_to={'batch_type': 'l'}, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='balloons_ttn_loading_new',
                to='filling_station.balloonsbatch',
                verbose_name='Партия приёмки',
            ),
        ),
        migrations.AddField(
            model_name='balloonttn',
            name='unloading_batch_new',
            field=models.ForeignKey(
                blank=True, limit_choices_to={'batch_type': 'u'}, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='balloons_ttn_unloading_new',
                to='filling_station.balloonsbatch',
                verbose_name='Партия отгрузки',
            ),
        ),
        migrations.RunPython(_map_batch_foreign_keys, migrations.RunPython.noop),
        migrations.RemoveField(model_name='balloonttn', name='loading_batch'),
        migrations.RemoveField(model_name='balloonttn', name='unloading_batch'),
        migrations.RenameField(model_name='balloonttn', old_name='loading_batch_new', new_name='loading_batch'),
        migrations.RenameField(model_name='balloonttn', old_name='unloading_batch_new', new_name='unloading_batch'),
        migrations.AlterField(
            model_name='balloonttn',
            name='loading_batch',
            field=models.ForeignKey(
                blank=True, limit_choices_to={'batch_type': 'l'}, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='balloons_ttn_loading',
                to='filling_station.balloonsbatch',
                verbose_name='Партия приёмки',
            ),
        ),
        migrations.AlterField(
            model_name='balloonttn',
            name='unloading_batch',
            field=models.ForeignKey(
                blank=True, limit_choices_to={'batch_type': 'u'}, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='balloons_ttn_unloading',
                to='filling_station.balloonsbatch',
                verbose_name='Партия отгрузки',
            ),
        ),
        migrations.AlterField(
            model_name='balloonttn',
            name='date',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Дата формирования накладной'),
        ),
    ]
