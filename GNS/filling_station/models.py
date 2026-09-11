from collections import defaultdict
from datetime import date
from typing import Dict, Any, List, Optional

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.urls import reverse
from django.db.models import Q, F, Sum, Count, Case, When, IntegerField
from django.db.models.functions import Coalesce
from django.conf import settings
import pghistory

from core.timeutils import current_date


BATCH_TYPE_CHOICES = [
    ('l', 'Приёмка'),
    ('u', 'Отгрузка'),
]

READER_FUNCTION_CHOICES = [
    ('l', 'Приёмка'),
    ('u', 'Отгрузка'),
    ('p', 'Нет'),
]


BALLOON_SIZE_CHOICES = [
    (5, 5),
    (12, 12),
    (27, 27),
    (50, 50),
]


@pghistory.track(exclude=['filling_status', 'update_passport_required'])
class Balloon(models.Model):
    nfc_tag = models.CharField(primary_key=True,max_length=30, db_index=True, verbose_name="Номер метки")
    serial_number = models.CharField(null=True, blank=True, max_length=30, db_index=True, verbose_name="Серийный номер")
    creation_date = models.DateField(null=True, blank=True, verbose_name="Дата производства")
    size = models.IntegerField(choices=BALLOON_SIZE_CHOICES, default=50, verbose_name="Объём")
    netto = models.FloatField(null=True, blank=True, verbose_name="Вес пустого баллона")
    brutto = models.FloatField(null=True, blank=True, verbose_name="Вес наполненного баллона")
    current_examination_date = models.DateField(null=True, blank=True, verbose_name="Дата освидетельствования")
    next_examination_date = models.DateField(null=True, blank=True, verbose_name="Дата следующего освидетельствования")
    diagnostic_date = models.DateField(null=True, blank=True, verbose_name="Дата последней диагностики")
    working_pressure = models.FloatField(null=True, blank=True, verbose_name="Рабочее давление")
    status = models.CharField(null=True, blank=True, max_length=100, verbose_name="Статус")
    manufacturer = models.CharField(null=True, blank=True, max_length=30, verbose_name="Производитель")
    wall_thickness = models.FloatField(null=True, blank=True, verbose_name="Толщина стенок")
    filling_status = models.BooleanField(default=False, verbose_name="Готов к наполнению")
    update_passport_required = models.BooleanField(default=True, verbose_name="Требуется обновление паспорта")
    change_date = models.DateTimeField(auto_now=True, verbose_name="Дата изменений")
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Пользователь",
        default=1
    )

    def __str__(self):
        return self.nfc_tag

    class Meta:
        verbose_name = "Баллон"
        verbose_name_plural = "Баллоны"
        ordering = ['-change_date']

    def get_absolute_url(self):
        return reverse('filling_station:balloon_detail', args=[self.pk])

    def get_update_url(self):
        return reverse('filling_station:balloon_update', args=[self.pk])

    def get_delete_url(self):
        return reverse('filling_station:balloon_delete', args=[self.pk])

    def clean(self):
        if self.brutto and self.netto and self.brutto < self.netto:
            raise ValidationError("Вес наполненного баллона должен быть больше веса пустого баллона.")


class ReaderSettings(models.Model):
    """Конфигурация RFID-считывателя (номер = PK, для очереди карусели)."""

    number = models.IntegerField(primary_key=True, verbose_name="Номер считывателя")
    status = models.CharField(null=True, blank=True, max_length=100, verbose_name="Статус")
    ip = models.CharField(null=True, blank=True, max_length=15, verbose_name="IP адрес")
    port = models.IntegerField(default=10001, verbose_name="Порт")
    function = models.CharField(
        choices=READER_FUNCTION_CHOICES,
        default='p',
        verbose_name="Функция",
    )
    need_cache = models.BooleanField(default=False, verbose_name="Добавлять в кеш")

    def __int__(self):
        return self.number

    def __str__(self):
        return self.status or str(self.number)

    class Meta:
        verbose_name = "Настройки считывателей"
        verbose_name_plural = "Настройки считывателей"
        ordering = ['number']


class Reader(models.Model):
    number = models.IntegerField(verbose_name="Номер считывателя")
    nfc_tag = models.CharField(max_length=30, verbose_name="Номер метки")
    serial_number = models.CharField(null=True, blank=True, max_length=30, verbose_name="Серийный номер")
    size = models.IntegerField(choices=BALLOON_SIZE_CHOICES, default=50, verbose_name="Объём")
    netto = models.FloatField(null=True, blank=True, verbose_name="Вес пустого баллона")
    brutto = models.FloatField(null=True, blank=True, verbose_name="Вес наполненного баллона")
    filling_status = models.BooleanField(default=False, verbose_name="Готов к наполнению")
    change_date = models.DateField(auto_now=True, verbose_name="Дата изменений")
    change_time = models.TimeField(auto_now=True, verbose_name="Время изменений")

    def __int__(self):
        return self.pk

    def __str__(self):
        return self.number

    class Meta:
        verbose_name = "Считыватель"
        verbose_name_plural = "Считыватели"
        ordering = ['-change_date', '-change_time']

    @classmethod
    def get_all_readers_stats(cls, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        Статистика по всем считывателям за период.
        Источник — DailyReaderCounter (те же счётчики, что и в RFID-таблицах).

        Args:
            start_date: Начало периода (включительно).
            end_date: Конец периода (включительно).

        Returns:
            Список словарей с номером, статусом и суммами RFID/сенсор/всего по каждому считывателю.
        """
        period_stats = (
            DailyReaderCounter.objects
            .filter(day__gte=start_date, day__lte=end_date)
            .values('number_id')
            .annotate(
                total_rfid=Sum('amount_of_rfid'),
                total_sensor=Sum('amount_of_sensor'),
            )
        )
        stats_by_reader = {row['number_id']: row for row in period_stats}

        result: List[Dict[str, Any]] = []
        for reader in ReaderSettings.objects.order_by('number'):
            counter = stats_by_reader.get(reader.number, {})
            total_rfid = counter.get('total_rfid') or 0
            total_sensor = counter.get('total_sensor') or 0
            result.append({
                'number': reader.number,
                'status': reader.status,
                'total_rfid': total_rfid,
                'total_sensor': total_sensor,
                'total_balloons': total_rfid + total_sensor,
            })
        return result

    @classmethod
    def get_common_stats_for_gns(cls) -> List[Dict[str, Any]]:
        """
        Статистика по считывателям за текущий месяц и за сегодня.

        Returns:
            Список словарей с ``reader_id`` и счётчиками RFID/сенсора за месяц и день.
        """
        return DailyReaderCounter.get_common_stats_for_gns()


class DailyReaderCounter(models.Model):
    """Ежедневные счётчики проходов по конкретному RFID-считывателю."""

    number = models.ForeignKey(
        ReaderSettings,
        on_delete=models.PROTECT,
        verbose_name="Номер считывателя",
        related_name='daily_counters'
    )
    day = models.DateField(verbose_name="Дата", db_index=True)
    amount_of_rfid = models.IntegerField(default=0, verbose_name="Баллонов по RFID")
    amount_of_sensor = models.IntegerField(default=0, verbose_name="Баллонов по сенсору")
    change_at = models.DateTimeField(auto_now=True, verbose_name="Дата последнего изменения")

    def __str__(self):
        return f'Количество баллонов на ридере {self.number_id}'

    class Meta:
        verbose_name = "Счетчики по ридерам за день"
        verbose_name_plural = "Счетчики по ридерам за день"
        ordering = ['-day']
        constraints = [
            models.UniqueConstraint(fields=['number', 'day'], name='uniq_number_day'),
        ]

    @classmethod
    def add_rfid(cls, reader: ReaderSettings) -> None:
        """Атомарно увеличивает счётчик RFID-проходов за текущий день."""
        cls._increment(reader, 'amount_of_rfid')

    @classmethod
    def add_sensor(cls, reader: ReaderSettings) -> None:
        """Атомарно увеличивает счётчик проходов по оптическому датчику за текущий день."""
        cls._increment(reader, 'amount_of_sensor')

    @classmethod
    def _increment(cls, reader: ReaderSettings, field_name: str) -> None:
        """
        Инкрементирует указанное поле счётчика за сегодня.

        Args:
            reader: Настройки считывателя, для которого ведётся учёт.
            field_name: ``amount_of_rfid`` или ``amount_of_sensor``.
        """
        obj, _ = cls.objects.get_or_create(
            number=reader,
            day=current_date(),
            defaults={'amount_of_rfid': 0, 'amount_of_sensor': 0},
        )
        cls.objects.filter(pk=obj.pk).update(
            **{field_name: F(field_name) + 1},
            change_at=timezone.now(),
        )

    @classmethod
    def get_reader_period_stats(cls, reader: ReaderSettings, start_date: date, end_date: date) -> Dict[str, int]:
        """
        Статистика по конкретному ридеру за период.

        Args:
            reader: Считыватель, по которому агрегируются данные.
            start_date: Начало периода (включительно).
            end_date: Конец периода (включительно).

        Returns:
            Словарь с ключами ``total_rfid`` и ``total_sensor``.
        """
        stats = cls.objects.filter(
            number=reader,
            day__gte=start_date,
            day__lte=end_date,
        ).aggregate(
            total_rfid=Sum('amount_of_rfid'),
            total_sensor=Sum('amount_of_sensor'),
        )
        return {
            'total_rfid': stats.get('total_rfid') or 0,
            'total_sensor': stats.get('total_sensor') or 0,
        }

    @classmethod
    def get_common_stats_for_gns(cls) -> List[Dict[str, Any]]:
        """
        Статистика по ридерам за месяц и за сегодня.
        ``balloons_*`` — проходы по оптическому датчику, ``rfid_*`` — по метке.

        Returns:
            Список словарей с данными по каждому считывателю.
        """
        today = current_date()
        first_day_of_month = today.replace(day=1)

        month_stats = cls.objects.filter(day__gte=first_day_of_month).values('number__number').annotate(
            rfid_month=Sum('amount_of_rfid'),
            balloons_month=Sum('amount_of_sensor'),
        )
        today_stats = cls.objects.filter(day=today).values('number__number').annotate(
            rfid_today=Sum('amount_of_rfid'),
            balloons_today=Sum('amount_of_sensor'),
        )

        month_dict = {stat['number__number']: stat for stat in month_stats}
        today_dict = {stat['number__number']: stat for stat in today_stats}

        stats = []
        for reader in ReaderSettings.objects.all():
            month = month_dict.get(reader.number, {})
            day = today_dict.get(reader.number, {})
            stats.append({
                "reader_id": reader.number,
                "balloons_month": month.get('balloons_month', 0) or 0,
                "rfid_month": month.get('rfid_month', 0) or 0,
                "balloons_today": day.get('balloons_today', 0) or 0,
                "rfid_today": day.get('rfid_today', 0) or 0,
            })
        return stats


class TotalReadersCounter(models.Model):
    """
    Свод по складу: сколько пустых и полных баллонов числится на станции.

    Значения задаются вручную/из SCADA (``insert_manual_values``). Автоматический
    пересчёт по проходам ридеров в Лиде пока не включён: соответствие
    «номер ридера → движение склада» нужно подтвердить на площадке
    (см. комментарий к ролям ридеров в ``filling_station/services/rfid.py``).
    """

    total_empty = models.IntegerField(default=0, verbose_name="Всего пустых баллонов")
    total_full = models.IntegerField(default=0, verbose_name="Всего полных баллонов")
    changed_at = models.DateTimeField(auto_now=True, verbose_name='Дата последнего изменения')

    class Meta:
        verbose_name = "Свод по складу"
        verbose_name_plural = "Свод по складу"
        ordering = ['-changed_at']

    def __str__(self):
        return f'Свод (E={self.total_empty}, F={self.total_full})'

    @classmethod
    def add_full_balloon(cls):
        """Увеличивает счётчик полных баллонов на складе на единицу."""
        cls.objects.filter(pk=1).update(total_full=F('total_full') + 1, changed_at=timezone.now())

    @classmethod
    def add_empty_balloon(cls):
        """Увеличивает счётчик пустых баллонов на складе на единицу."""
        cls.objects.filter(pk=1).update(total_empty=F('total_empty') + 1, changed_at=timezone.now())

    @classmethod
    def sub_full_balloon(cls):
        """Уменьшает счётчик полных баллонов на единицу, если он больше нуля."""
        cls.objects.filter(pk=1, total_full__gt=0).update(total_full=F('total_full') - 1, changed_at=timezone.now())

    @classmethod
    def sub_empty_balloon(cls):
        """Уменьшает счётчик пустых баллонов на единицу, если он больше нуля."""
        cls.objects.filter(pk=1, total_empty__gt=0).update(total_empty=F('total_empty') - 1, changed_at=timezone.now())

    @classmethod
    def insert_manual_values(cls, empty: int = None, full: int = None):
        """
        Записывает ручные значения со SCADA (поля с ``None`` остаются без изменений).

        Args:
            empty: Новое число пустых баллонов; ``None`` — не менять.
            full: Новое число полных баллонов; ``None`` — не менять.
        """
        cls.objects.filter(pk=1).update(
            total_empty=empty if empty is not None else F('total_empty'),
            total_full=full if full is not None else F('total_full'),
            changed_at=timezone.now(),
        )

    @classmethod
    def get_balloons_stats(cls) -> Dict[str, int]:
        """
        Количество полных и пустых баллонов на станции.

        Returns:
            Словарь с ключами ``filled`` и ``empty``; при отсутствии записи — нули.
        """
        counter = cls.objects.filter(pk=1).first()
        if counter:
            return {'filled': counter.total_full, 'empty': counter.total_empty}
        return {'filled': 0, 'empty': 0}


class TruckType(models.Model):
    type = models.CharField(max_length=100, verbose_name="Тип грузовика")

    def __str__(self):
        return self.type

    class Meta:
        verbose_name = "Тип грузовика"
        verbose_name_plural = "Типы грузовиков"


class Truck(models.Model):
    car_brand = models.CharField(null=True, blank=True, max_length=20, verbose_name="Марка авто")
    registration_number = models.CharField(max_length=10, verbose_name="Регистрационный знак")
    type = models.ForeignKey(
        TruckType,
        on_delete=models.DO_NOTHING,
        verbose_name="Тип",
        default=1
    )
    capacity_cylinders = models.IntegerField(null=True, blank=True, verbose_name="Максимальная вместимость баллонов")
    max_weight_of_transported_cylinders = models.FloatField(null=True, blank=True,
                                                            verbose_name="Максимальная масса перевозимых баллонов")
    max_mass_of_transported_gas = models.FloatField(null=True, blank=True,
                                                    verbose_name="Максимальная масса перевозимого газа")
    max_gas_volume = models.FloatField(null=True, blank=True, verbose_name="Максимальный объём перевозимого газа")
    empty_weight = models.FloatField(null=True, blank=True, verbose_name="Вес пустого т/с (по техпаспорту)")
    full_weight = models.FloatField(null=True, blank=True, verbose_name="Вес полного т/с (по техпаспорту)")
    is_on_station = models.BooleanField(null=True, blank=True, verbose_name="Находится на станции")
    entry_date = models.DateField(null=True, blank=True, verbose_name="Дата въезда")
    entry_time = models.TimeField(null=True, blank=True, verbose_name="Время въезда")
    departure_date = models.DateField(null=True, blank=True, verbose_name="Дата выезда")
    departure_time = models.TimeField(null=True, blank=True, verbose_name="Время выезда")

    def __str__(self):
        return self.registration_number

    class Meta:
        verbose_name = "Грузовик"
        verbose_name_plural = "Грузовики"
        ordering = ['-is_on_station', '-entry_date', '-entry_time', '-departure_date', '-departure_time']

    def get_absolute_url(self):
        return reverse('filling_station:truck_detail', args=[self.pk])

    def get_update_url(self):
        return reverse('filling_station:truck_update', args=[self.pk])

    def get_delete_url(self):
        return reverse('filling_station:truck_delete', args=[self.pk])


class TrailerType(models.Model):
    type = models.CharField(max_length=100, verbose_name="Тип прицепа")

    def __str__(self):
        return self.type

    class Meta:
        verbose_name = "Тип прицепа"
        verbose_name_plural = "Типы прицепов"


class Trailer(models.Model):
    truck = models.ForeignKey(
        Truck,
        on_delete=models.DO_NOTHING,
        verbose_name="Автомобиль",
        related_name='trailer',
        default=1
    )
    trailer_brand = models.CharField(null=True, blank=True, max_length=20, verbose_name="Марка прицепа")
    registration_number = models.CharField(max_length=10, verbose_name="Регистрационный знак")
    type = models.ForeignKey(
        TrailerType,
        on_delete=models.DO_NOTHING,
        verbose_name="Тип",
        default=1
    )
    capacity_cylinders = models.IntegerField(null=True, blank=True, verbose_name="Максимальная вместимость баллонов")
    max_weight_of_transported_cylinders = models.FloatField(null=True, blank=True,
                                                            verbose_name="Максимальная масса перевозимых баллонов")
    max_mass_of_transported_gas = models.FloatField(null=True, blank=True,
                                                    verbose_name="Максимальная масса перевозимого газа")
    max_gas_volume = models.FloatField(null=True, blank=True, verbose_name="Максимальный объём перевозимого газа")
    empty_weight = models.FloatField(null=True, blank=True, verbose_name="Вес пустого т/с (по техпаспорту)")
    full_weight = models.FloatField(null=True, blank=True, verbose_name="Вес полного т/с (по техпаспорту)")

    is_on_station = models.BooleanField(null=True, blank=True, verbose_name="Находится на станции")
    entry_date = models.DateField(null=True, blank=True, verbose_name="Дата въезда")
    entry_time = models.TimeField(null=True, blank=True, verbose_name="Время въезда")
    departure_date = models.DateField(null=True, blank=True, verbose_name="Дата выезда")
    departure_time = models.TimeField(null=True, blank=True, verbose_name="Время выезда")

    def __str__(self):
        return self.registration_number

    class Meta:
        verbose_name = "Прицеп"
        verbose_name_plural = "Прицепы"
        ordering = ['-is_on_station', '-entry_date', '-entry_time', '-departure_date', '-departure_time']

    def get_absolute_url(self):
        return reverse('filling_station:trailer_detail', args=[self.pk])

    def get_update_url(self):
        return reverse('filling_station:trailer_update', args=[self.pk])

    def get_delete_url(self):
        return reverse('filling_station:trailer_delete', args=[self.pk])


class BalloonAmount(models.Model):
    reader_id = models.IntegerField(null=True, blank=True, verbose_name="Номер считывателя")
    reader_status = models.CharField(null=True, blank=True, max_length=50, verbose_name="Статус")
    amount_of_balloons = models.IntegerField(null=True, blank=True, verbose_name="Количество баллонов по датчику")
    amount_of_rfid = models.IntegerField(null=True, blank=True, verbose_name="Количество баллонов по считывателю")
    change_date = models.DateField(null=True, blank=True, auto_now=True, verbose_name="Дата обновления")
    change_time = models.TimeField(null=True, blank=True, auto_now=True, verbose_name="Время обновления")


class BatchStatus(models.TextChoices):
    """Статусы жизненного цикла партии баллонов (приёмка/отгрузка)."""

    ACTIVE = 'active', 'В работе'
    PAUSED = 'paused', 'Приостановлена'
    COMPLETED = 'completed', 'Завершена'
    MIRIADA_ERROR = 'miriada_error', 'Завершена, ошибка Мириады'


class BalloonsBatch(models.Model):
    """
    Единая модель партий приёмки и отгрузки баллонов.

    Заменяет ``BalloonsLoadingBatch``/``BalloonsUnloadingBatch``: тип задаётся
    полем ``batch_type``, состояние — полем ``status`` (вместо ``is_active``),
    номер ТТН — целочисленным ``ttn_id`` из Мириады (вместо строкового ``ttn``).
    """

    batch_type = models.CharField(choices=settings.BATCH_TYPE_CHOICES, default='l', verbose_name="Тип партии")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время начала")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата и время окончания")
    truck = models.ForeignKey(Truck, on_delete=models.PROTECT, verbose_name="Автомобиль")
    trailer = models.ForeignKey(
        Trailer, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Прицеп"
    )
    reader_number = models.IntegerField(null=True, blank=True, verbose_name="Номер считывателя")
    amount_of_rfid = models.IntegerField(default=0, verbose_name="Количество баллонов по rfid")
    amount_of_sensor = models.IntegerField(default=0, verbose_name="Количество баллонов по датчику")
    amount_of_ttn = models.IntegerField(default=0, verbose_name="Количество баллонов по электронной ТТН")
    amount_of_5_liters = models.IntegerField(default=0, verbose_name="Количество 5л баллонов")
    amount_of_12_liters = models.IntegerField(default=0, verbose_name="Количество 12л баллонов")
    amount_of_27_liters = models.IntegerField(default=0, verbose_name="Количество 27л баллонов")
    amount_of_50_liters = models.IntegerField(default=0, verbose_name="Количество 50л баллонов")
    gas_amount = models.FloatField(null=True, blank=True, verbose_name="Количество газа")
    balloon_list = models.ManyToManyField(Balloon, blank=True, verbose_name="Список баллонов")
    status = models.CharField(
        max_length=20,
        choices=BatchStatus.choices,
        default=BatchStatus.PAUSED,
        verbose_name="Статус партии",
        db_index=True,
    )
    miriada_close_failed = models.BooleanField(default=False, verbose_name="Ошибка закрытия ТТН в Мириаде")
    miriada_error_message = models.CharField(
        null=True, blank=True, max_length=200,
        verbose_name="Текст ошибки при неудачном закрытии ТТН",
    )
    miriada_balloons_sent = models.BooleanField(
        default=False, verbose_name="Статусы баллонов отправлены в Мириаду"
    )
    ttn_id = models.IntegerField(default=0, verbose_name="ID ТТН")
    balloons_type = models.CharField(
        choices=settings.BALLOON_TYPE_CHOICES, default='e', verbose_name="Пустой/полный"
    )
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, default=1, verbose_name="Пользователь"
    )

    class Meta:
        verbose_name = "Партия баллонов"
        verbose_name_plural = "Партии баллонов"
        ordering = ['-started_at']

    def __str__(self):
        return f'Партия №{self.id}. Тип {self.batch_type}'

    def _batch_url_prefix(self) -> str:
        """Префикс имени URL для приёмки или отгрузки в зависимости от типа партии."""
        return 'balloon_loading_batch' if self.batch_type == 'l' else 'balloon_unloading_batch'

    def get_absolute_url(self):
        return reverse(f'filling_station:{self._batch_url_prefix()}_detail', args=[self.pk])

    def get_update_url(self):
        return reverse(f'filling_station:{self._batch_url_prefix()}_update', args=[self.pk])

    def get_delete_url(self):
        return reverse(f'filling_station:{self._batch_url_prefix()}_delete', args=[self.pk])

    def get_retry_close_url(self):
        return reverse(f'filling_station:{self._batch_url_prefix()}_retry_close', args=[self.pk])

    def can_retry_miriada_close(self) -> bool:
        """Можно ли повторить закрытие ТТН после ошибки Мириады."""
        return self.status == BatchStatus.MIRIADA_ERROR and bool(self.ttn_id)

    def accepts_rfid(self) -> bool:
        """Принимает ли партия RFID-метки и показания датчика (только ACTIVE)."""
        return self.status == BatchStatus.ACTIVE

    def accepts_manual_edits(self) -> bool:
        """Допускает ли партия ручные правки состава (ACTIVE или PAUSED)."""
        return self.status in (BatchStatus.ACTIVE, BatchStatus.PAUSED)

    def save(self, *args, **kwargs):
        """Сохраняет партию и синхронизирует флаг ошибки закрытия ТТН со статусом."""
        if self.status == BatchStatus.MIRIADA_ERROR:
            self.miriada_close_failed = True
        elif self.status == BatchStatus.COMPLETED:
            self.miriada_close_failed = False
        super().save(*args, **kwargs)

    def get_ttn_name(self) -> Optional[str]:
        """
        Номер ТТН из Мириады по сохранённому ``ttn_id``.

        Справочник ``MiriadaTtn`` появится в приложении ``ttn`` на следующем этапе
        синхронизации, до этого возвращается ``None``.
        """
        if not self.ttn_id:
            return None
        try:
            from ttn.models import MiriadaTtn
        except ImportError:
            return None
        return MiriadaTtn.objects.filter(ttn_id=self.ttn_id).values_list('name', flat=True).first()

    def get_amount_without_rfid(self) -> int:
        """Количество баллонов без RFID: сумма полей по объёмам."""
        return sum((
            self.amount_of_5_liters or 0,
            self.amount_of_12_liters or 0,
            self.amount_of_27_liters or 0,
            self.amount_of_50_liters or 0,
        ))

    def add_balloon(self, nfc_tag: str = None) -> dict:
        """
        Добавляет баллон в партию по NFC-метке либо учитывает проход оптического датчика.

        Args:
            nfc_tag: NFC-метка баллона; ``None`` — инкремент счётчика сенсора.

        Returns:
            Словарь с ключами ``success``, ``balloon_id``, ``message``.
        """
        result = {'success': False, 'balloon_id': None, 'message': 'ok'}

        if not self.accepts_manual_edits():
            result['message'] = 'Партия не принимает изменения в текущем статусе'
            return result

        if not nfc_tag:
            if not self.accepts_rfid():
                result['message'] = 'Оптический датчик учитывается только у активной партии'
                return result
            self.amount_of_sensor = (self.amount_of_sensor or 0) + 1
            self.save()
            result['success'] = True
            return result

        try:
            if self.balloon_list.filter(nfc_tag=nfc_tag).exists():
                result['message'] = f'Баллон с меткой {nfc_tag} уже в партии'
                return result

            balloon = Balloon.objects.get(nfc_tag=nfc_tag)
            self.balloon_list.add(balloon)
            self.amount_of_rfid = (self.amount_of_rfid or 0) + 1
            self.save()
            result.update(success=True, balloon_id=balloon.nfc_tag)
        except Balloon.DoesNotExist:
            result['message'] = f'Баллон с меткой {nfc_tag} не найден'
        except Exception as error:
            result['message'] = f'Ошибка сервера: {error}'

        return result

    def remove_balloon(self, nfc_tag) -> dict:
        """
        Удаляет баллон из партии по NFC-метке.

        Args:
            nfc_tag: NFC-метка баллона для удаления из состава партии.

        Returns:
            Словарь с ключами ``success``, ``balloon_id``, ``message``.
        """
        result = {'success': False, 'balloon_id': None, 'message': 'ok'}

        if not self.accepts_manual_edits():
            result['message'] = 'Партия не принимает изменения в текущем статусе'
            return result

        try:
            balloon = self.balloon_list.get(nfc_tag=nfc_tag)
            self.balloon_list.remove(balloon)
            self.amount_of_rfid = max((self.amount_of_rfid or 0) - 1, 0)
            self.save()
            result.update(success=True, balloon_id=balloon.nfc_tag)
        except Balloon.DoesNotExist:
            result['message'] = f'Баллон с меткой {nfc_tag} не найден в партии'
        except Exception as error:
            result['message'] = f'Ошибка сервера: {error}'

        return result

    @classmethod
    def get_period_stats(
        cls,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        batch_type: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Статистика по партиям за период: число партий, баллонов по RFID и по ТТН.

        Args:
            start_date: Начало периода по дате ``started_at``; вместе с ``end_date``.
            end_date: Конец периода; без обеих дат фильтр по дате не применяется.
            batch_type: Тип партии (``l``/``u``); ``None`` — все типы.

        Returns:
            Словарь с ``total_batches``, ``total_balloon_count_by_rfid``,
            ``total_balloon_count_by_ttn``.
        """
        queryset = cls.objects.all()
        if start_date is not None and end_date is not None:
            queryset = queryset.filter(
                started_at__date__gte=start_date,
                started_at__date__lte=end_date,
            )
        if batch_type:
            queryset = queryset.filter(batch_type=batch_type)

        ttn_amount = Case(
            When(amount_of_sensor__gt=0, then=F('amount_of_sensor')),
            default=(
                Coalesce(F('amount_of_5_liters'), 0)
                + Coalesce(F('amount_of_12_liters'), 0)
                + Coalesce(F('amount_of_27_liters'), 0)
                + Coalesce(F('amount_of_50_liters'), 0)
            ),
            output_field=IntegerField(),
        )

        stats = queryset.aggregate(
            total_batches=Count('id'),
            total_balloon_count_by_rfid=Coalesce(Sum('amount_of_rfid'), 0),
            total_balloon_count_by_ttn=Coalesce(Sum(ttn_amount), 0),
        )
        return {key: value or 0 for key, value in stats.items()}

    @classmethod
    def get_common_stats_for_gns(cls, batch_type: Optional[str] = None) -> list:
        """
        Число партий за текущий месяц и за сегодня в разрезе считывателей.

        Args:
            batch_type: Тип партии (``l``/``u``); ``None`` — все типы.

        Returns:
            Список словарей с ``reader_id``, ``truck_month``, ``truck_today``.
        """
        today = current_date()
        month_start = today.replace(day=1)

        queryset = cls.objects.filter(started_at__date__gte=month_start)
        if batch_type:
            queryset = queryset.filter(batch_type=batch_type)

        stats_by_reader = defaultdict(lambda: {"truck_month": 0, "truck_today": 0})
        month_rows = queryset.values('reader_number').annotate(total=Count('id'))
        today_rows = queryset.filter(started_at__date=today).values('reader_number').annotate(total=Count('id'))

        for row in month_rows:
            if row['reader_number'] is None:
                continue
            stats_by_reader[row['reader_number']]["truck_month"] = row['total']
        for row in today_rows:
            if row['reader_number'] is None:
                continue
            stats_by_reader[row['reader_number']]["truck_today"] = row['total']

        return [{"reader_id": reader_id, **data} for reader_id, data in stats_by_reader.items()]


class BalloonsLoadingBatch(models.Model):
    """
    DEPRECATED: используйте ``BalloonsBatch`` (batch_type='l').

    Legacy-таблица сохранена для обратной совместимости миграций и связей
    ``ttn.BalloonTtn``; новый код не должен создавать записи через эту модель.
    """

    begin_date = models.DateField(null=True, blank=True, auto_now_add=True, verbose_name="Дата начала приёмки")
    begin_time = models.TimeField(null=True, blank=True, auto_now_add=True, verbose_name="Время начала приёмки")
    end_date = models.DateField(null=True, blank=True, verbose_name="Дата окончания приёмки")
    end_time = models.TimeField(null=True, blank=True, verbose_name="Время окончания приёмки")
    truck = models.ForeignKey(
        Truck,
        on_delete=models.DO_NOTHING,
        verbose_name="Автомобиль"
    )
    trailer = models.ForeignKey(
        Trailer,
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        default=0,
        verbose_name="Прицеп"
    )
    reader_number = models.IntegerField(null=True, blank=True, verbose_name="Номер считывателя")
    amount_of_rfid = models.IntegerField(null=True, blank=True, verbose_name="Количество баллонов по rfid")
    amount_of_5_liters = models.IntegerField(null=True, blank=True, default=0, verbose_name="Количество 5л баллонов")
    amount_of_12_liters = models.IntegerField(null=True, blank=True, default=0, verbose_name="Количество 12л баллонов")
    amount_of_27_liters = models.IntegerField(null=True, blank=True, default=0, verbose_name="Количество 27л баллонов")
    amount_of_50_liters = models.IntegerField(null=True, blank=True, default=0, verbose_name="Количество 50л баллонов")
    gas_amount = models.FloatField(null=True, blank=True, verbose_name="Количество принятого газа")
    balloon_list = models.ManyToManyField(
        Balloon,
        blank=True,
        verbose_name="Список баллонов"
    )
    is_active = models.BooleanField(null=True, blank=True, verbose_name="В работе")
    ttn = models.CharField(max_length=20, default='', verbose_name="Номер ТТН")
    amount_of_ttn = models.IntegerField(null=True, blank=True, verbose_name="Количество баллонов по ТТН")
    user = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        default=1,
        verbose_name="Пользователь"
    )

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Партия приёмки баллонов"
        verbose_name_plural = "Партии приёмки баллонов"
        ordering = ['-begin_date', '-begin_time']

    def get_absolute_url(self):
        return reverse('filling_station:balloon_loading_batch_detail', args=[self.pk])

    def get_update_url(self):
        return reverse('filling_station:balloon_loading_batch_update', args=[self.pk])

    def get_delete_url(self):
        return reverse('filling_station:balloon_loading_batch_delete', args=[self.pk])

    def get_amount_without_rfid(self):
        amounts = [
            self.amount_of_5_liters or 0,
            self.amount_of_12_liters or 0,
            self.amount_of_27_liters or 0,
            self.amount_of_50_liters or 0
        ]
        total_amount = sum(amounts)
        return total_amount


class BalloonsUnloadingBatch(models.Model):
    """
    DEPRECATED: используйте ``BalloonsBatch`` (batch_type='u').

    Legacy-таблица сохранена для обратной совместимости миграций и связей
    ``ttn.BalloonTtn``; новый код не должен создавать записи через эту модель.
    """

    begin_date = models.DateField(null=True, blank=True, auto_now_add=True, verbose_name="Дата начала отгрузки")
    begin_time = models.TimeField(null=True, blank=True, auto_now_add=True, verbose_name="Время начала отгрузки")
    end_date = models.DateField(null=True, blank=True, verbose_name="Дата окончания отгрузки")
    end_time = models.TimeField(null=True, blank=True, verbose_name="Время окончания отгрузки")
    truck = models.ForeignKey(
        Truck,
        on_delete=models.DO_NOTHING,
        verbose_name="Автомобиль"
    )
    trailer = models.ForeignKey(
        Trailer,
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        default=0,
        verbose_name="Прицеп"
    )
    reader_number = models.IntegerField(null=True, blank=True, verbose_name="Номер считывателя")
    amount_of_rfid = models.IntegerField(null=True, blank=True, verbose_name="Количество баллонов по rfid")
    amount_of_5_liters = models.IntegerField(null=True, blank=True, default=0, verbose_name="Количество 5л баллонов")
    amount_of_12_liters = models.IntegerField(null=True, blank=True, default=0, verbose_name="Количество 12л баллонов")
    amount_of_27_liters = models.IntegerField(null=True, blank=True, default=0, verbose_name="Количество 27л баллонов")
    amount_of_50_liters = models.IntegerField(null=True, blank=True, default=0, verbose_name="Количество 50л баллонов")
    gas_amount = models.FloatField(null=True, blank=True, verbose_name="Количество отгруженного газа")
    balloon_list = models.ManyToManyField(Balloon, blank=True, verbose_name="Список баллонов")
    is_active = models.BooleanField(null=True, blank=True, verbose_name="В работе")
    ttn = models.CharField(max_length=20, default='', verbose_name="Номер ТТН")
    amount_of_ttn = models.IntegerField(null=True, blank=True, verbose_name="Количество баллонов по ТТН")
    user = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        default=1,
        verbose_name="Пользователь"
    )

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Партия отгрузки баллонов"
        verbose_name_plural = "Партии отгрузки баллонов"
        ordering = ['-begin_date', '-begin_time']

    def get_absolute_url(self):
        return reverse('filling_station:balloon_unloading_batch_detail', args=[self.pk])

    def get_update_url(self):
        return reverse('filling_station:balloon_unloading_batch_update', args=[self.pk])

    def get_delete_url(self):
        return reverse('filling_station:balloon_unloading_batch_delete', args=[self.pk])

    def get_amount_without_rfid(self):
        amounts = [
            self.amount_of_5_liters or 0,
            self.amount_of_12_liters or 0,
            self.amount_of_27_liters or 0,
            self.amount_of_50_liters or 0
        ]
        total_amount = sum(amounts)
        return total_amount
