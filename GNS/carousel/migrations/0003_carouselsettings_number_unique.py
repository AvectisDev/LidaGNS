from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('carousel', '0002_unify_carousel_tcp_settings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='carouselsettings',
            name='number',
            field=models.IntegerField(unique=True, verbose_name='Номер карусели'),
        ),
        migrations.AlterModelOptions(
            name='carouselsettings',
            options={
                'ordering': ['number'],
                'verbose_name': 'Настройки карусели',
                'verbose_name_plural': 'Настройки карусели',
            },
        ),
    ]
