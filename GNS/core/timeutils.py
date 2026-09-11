"""Работа с текущим временем независимо от настройки ``USE_TZ``.

В Лиде ``USE_TZ = False``: ``timezone.now()`` возвращает naive-datetime в
локальной зоне, и ``timezone.localdate()``/``timezone.localtime()`` на нём
падают с ``ValueError: localtime() cannot be applied to a naive datetime``.
Хелперы ниже дают одинаковый результат и при ``USE_TZ = True`` (Пинск,
Руденск), поэтому код сервисов и моделей переносится между площадками
без правок.
"""

import datetime

from django.conf import settings
from django.utils import timezone


def current_datetime() -> datetime.datetime:
    """
    Текущее время в локальной зоне проекта.

    Returns:
        datetime.datetime: aware-значение при ``USE_TZ = True``,
        naive — при ``USE_TZ = False``.
    """
    if settings.USE_TZ:
        return timezone.localtime()
    return timezone.now()


def current_date() -> datetime.date:
    """
    Текущая календарная дата в локальной зоне проекта.

    Returns:
        datetime.date: сегодняшняя дата.
    """
    return current_datetime().date()
