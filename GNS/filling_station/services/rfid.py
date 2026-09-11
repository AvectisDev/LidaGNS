"""Обработка сигналов RFID-считывателей: баллоны, партии, кэш Redis.

Роли считывателей Лиды (нумерация совпадает с меню «Считыватели» и ``ReaderSettings``):

===  ==========================================================  =====================
 №   Назначение                                                  Роль в интеграциях
===  ==========================================================  =====================
 1   Погрузка полного баллона на трал 1                          отгрузка (function=u)
 2   Погрузка полного баллона на трал 2                          отгрузка (function=u)
 3   Приёмка пустого баллона из трала 1                          приёмка  (function=l)
 4   Приёмка пустого баллона из трала 2                          приёмка  (function=l)
 5   Регистрация полного баллона на складе                       склад, статус сразу
 6   Регистрация пустого баллона в цеху                          только учёт прохода
 7   Наполнение баллона. Карусель №1                             очередь карусели, статус сразу
 8   Наполнение баллона. Карусель №2                             очередь карусели, статус сразу
9-12 Переходы между наполнительным и ремонтным цехами            только учёт прохода
===  ==========================================================  =====================

Наборы для Мириады заданы в ``filling_station.services.batches`` и
``filling_station.services.miriada``.
"""

import logging
from typing import Optional, Dict, Any, Tuple

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F

from core.redis_queue import get_reader_balloon_queue_key, push_json_to_queue
from core.timeutils import current_date
from filling_station.exceptions import ReaderNotFoundError, MiriadaAPIError
from filling_station.models import (
    Balloon,
    BalloonAmount,
    Reader,
    BalloonsBatch,
    BatchStatus,
    DailyReaderCounter,
    ReaderSettings,
)
from filling_station.services.miriada import get_balloon_data_from_miriada

logger = logging.getLogger('filling_station')

# Паспорт перезапрашивается в Мириаде принудительно: на приёмке приходят баллоны
# сторонних организаций, а карусели нужны актуальные netto/brutto.
PASSPORT_REFRESH_READERS = frozenset({3, 4, 7, 8})


def processing_request_without_nfc(reader_number: int) -> Optional[ReaderSettings]:
    """
    Обрабатывает сигнал от ридера о сработке оптического датчика.

    Args:
        reader_number (int): номер RFID-считывателя.

    Returns:
        ReaderSettings: настройки считывателя при успехе.

    Raises:
        ReaderNotFoundError: если считыватель не найден.
        Exception: при прочих ошибках обработки сигнала.
    """
    try:
        reader = ReaderSettings.objects.get(number=reader_number)

        DailyReaderCounter.add_sensor(reader)
        _update_legacy_balloon_amount(reader, 'amount_of_balloons')

        logger.info(f'Ридер {reader_number}. Создана запись баллона без NFC')

        if reader.function in ['l', 'u']:
            add_sensor_count_to_batch(reader)
        return reader
    except ObjectDoesNotExist:
        error_msg = f"Ридер {reader_number} не найден в настройках"
        logger.error(error_msg)
        raise ReaderNotFoundError(error_msg) from None
    except Exception as error:
        logger.error(f"Ошибка обработки сигнала от оптического датчика: {error}")
        raise


def processing_request_with_nfc(nfc_tag: str, reader_number: int) -> Optional[Tuple[Balloon, ReaderSettings]]:
    """
    Обрабатывает сигнал от ридера при получении NFC-метки.

    Args:
        nfc_tag (str): NFC-метка баллона.
        reader_number (int): номер RFID-считывателя.

    Returns:
        tuple[Balloon, ReaderSettings] | None: баллон и настройки ридера либо None при ошибке.

    Raises:
        ReaderNotFoundError: если считыватель не найден.
    """
    try:
        reader = ReaderSettings.objects.get(number=reader_number)

        balloon, created = Balloon.objects.update_or_create(
            nfc_tag=nfc_tag,
            defaults={
                'status': reader.status
            }
        )
        logger.info(f"Ридер {reader.number}: Сохранение баллона с меткой {nfc_tag} успешно")

        DailyReaderCounter.add_rfid(reader)
        _update_legacy_balloon_amount(reader, 'amount_of_rfid')

        if balloon.update_passport_required or reader.number in PASSPORT_REFRESH_READERS:
            update_balloon_passport(balloon)

        if reader.function in ['l', 'u']:
            add_balloon_to_batch(reader, balloon)

        add_balloon_to_reader_table(balloon, reader)

        if reader.need_cache:
            add_balloon_to_cache(balloon, reader)

        return balloon, reader
    except ObjectDoesNotExist:
        error_msg = f"Ридер {reader_number} не найден в настройках"
        logger.error(error_msg)
        raise ReaderNotFoundError(error_msg) from None
    except Exception as error:
        logger.error(f"Ошибка при создании/изменении паспорта баллона: {error}")
        return None


def _update_legacy_balloon_amount(reader: ReaderSettings, field_name: str) -> None:
    """
    DEPRECATED: дублирует счётчик прохода в legacy-таблицу ``BalloonAmount``.

    Нужен, пока веб-страницы считывателей и статистики читают ``BalloonAmount``;
    удаляется вместе с переводом ``filling_station.views`` на ``DailyReaderCounter``.

    Args:
        reader (ReaderSettings): считыватель, через который прошёл баллон.
        field_name (str): ``amount_of_rfid`` или ``amount_of_balloons``.
    """
    try:
        counter, created = BalloonAmount.objects.get_or_create(
            change_date=current_date(),
            reader_id=reader.number,
            defaults={
                'amount_of_rfid': 0,
                'amount_of_balloons': 0,
                'reader_status': reader.status,
            },
        )
        BalloonAmount.objects.filter(pk=counter.pk).update(
            **{field_name: F(field_name) + 1}
        )
    except Exception as error:
        logger.error(f"Ошибка обновления legacy-счётчика ридера {reader.number}: {error}")


def update_balloon_passport(balloon: Balloon) -> None:
    """
    Обрабатывает данные от API Мириады и обновляет запись баллона.

    Args:
        balloon (Balloon): баллон для обновления паспорта.

    Raises:
        MiriadaAPIError: при ошибке запроса к Мириаде.
        Exception: при прочих ошибках сохранения паспорта.
    """
    try:
        api_data = get_balloon_data_from_miriada(balloon.nfc_tag)
        if api_data:
            balloon.serial_number = api_data['number']
            balloon.netto = api_data['netto']
            balloon.brutto = api_data['brutto']
            balloon.filling_status = api_data['status']
            balloon.update_passport_required = False
            balloon.save()
            logger.info(f"Обновление паспорта баллона с меткой {balloon.nfc_tag} успешно")
    except MiriadaAPIError:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении паспорта баллона {balloon.nfc_tag}: {e}")
        raise


def get_active_batch_for_reader(reader: ReaderSettings) -> Optional[BalloonsBatch]:
    """
    Возвращает активную партию приёмки/отгрузки, привязанную к считывателю на сегодня.

    Args:
        reader (ReaderSettings): настройки считывателя.

    Returns:
        BalloonsBatch | None: активная партия или None, если функция ридера не l/u.
    """
    if reader.function not in ['l', 'u']:
        return None
    return BalloonsBatch.objects.select_related('truck', 'trailer', 'truck__type').filter(
        batch_type=reader.function,
        started_at__date=current_date(),
        reader_number=reader.number,
        status=BatchStatus.ACTIVE,
    ).first()


def add_sensor_count_to_batch(reader: ReaderSettings) -> None:
    """
    Увеличивает счётчик оптического датчика у активной партии считывателя.

    Args:
        reader (ReaderSettings): считыватель, для которого ищется активная партия.
    """
    batch = get_active_batch_for_reader(reader)
    if not batch:
        return
    result = batch.add_balloon()
    if result.get('success'):
        logger.info(f"Оптический датчик: партия {batch.id}, считыватель {reader.number}")
    else:
        logger.warning(
            f"Не удалось учесть оптический датчик в партии {batch.id}: {result.get('message')}"
        )


def add_balloon_to_batch(reader: ReaderSettings, balloon: Optional[Balloon] = None) -> Optional[Dict[str, Any]]:
    """
    Добавляет баллон в активную партию в зависимости от номера ридера.

    Args:
        reader (ReaderSettings): считыватель с функцией приёмки/отгрузки.
        balloon (Balloon | None): баллон для добавления.

    Returns:
        dict | None: результат add_balloon, сообщение об отсутствии партии или None.
    """
    if not balloon:
        return None

    try:
        batch = get_active_batch_for_reader(reader)

        if not batch:
            logger.warning(f'Нет подходящей партии баллонов для ридера {reader.number}')
            return {'message': 'Нет подходящей партии баллонов'}

        result = batch.add_balloon(balloon.nfc_tag)
        if result.get('success', False):
            logger.info(f"Баллон {balloon.nfc_tag} добавлен в партию {batch.id}")
        else:
            logger.warning(f"Не удалось добавить баллон {balloon.nfc_tag} в партию: {result.get('message')}")

        return result
    except Exception as e:
        logger.error(f"Ошибка добавления баллона {balloon.nfc_tag if balloon else 'None'} в партию: {e}")
        return None


def add_balloon_to_reader_table(balloon: Balloon, reader: ReaderSettings) -> None:
    """
    Добавляет запись о прохождении баллона с меткой через определённый ридер.

    Args:
        balloon (Balloon): баллон с данными паспорта.
        reader (ReaderSettings): считыватель, через который прошёл баллон.

    Raises:
        Exception: при ошибке создания записи Reader.
    """
    try:
        Reader.objects.create(
            number=reader.number,
            nfc_tag=balloon.nfc_tag,
            serial_number=balloon.serial_number,
            size=balloon.size,
            netto=balloon.netto,
            brutto=balloon.brutto,
            filling_status=balloon.filling_status
        )
    except Exception as error:
        logger.error(f"Ошибка добавления баллона с NFC {balloon.nfc_tag} в таблицу считывателей: {error}")
        raise


def add_balloon_to_cache(balloon: Balloon, reader: ReaderSettings) -> None:
    """
    Добавляет паспорт баллона в нативную FIFO-очередь Redis.

    Очередь читает listener карусели: ``need_cache`` включается у считывателей,
    закреплённых за каруселями (в Лиде это 7 и 8, привязка задаётся в ``CarouselSettings``).

    Args:
        balloon (Balloon): баллон для кэширования.
        reader (ReaderSettings): считыватель (ключ очереди).

    Raises:
        Exception: при ошибке записи в Redis.
    """
    cache_timeout_seconds = 10 * 60

    try:
        queue_key = get_reader_balloon_queue_key(reader.number)
        queue_length = push_json_to_queue(queue_key, {
            'nfc_tag': balloon.nfc_tag,
            'serial_number': balloon.serial_number,
            'size': balloon.size,
            'netto': balloon.netto,
            'brutto': balloon.brutto,
            'filling_status': balloon.filling_status,
        }, timeout=cache_timeout_seconds)
        logger.debug(
            f'Баллон с NFC {balloon.nfc_tag} добавлен в Redis-очередь '
            f'{queue_key}. Размер очереди: {queue_length}'
        )
    except Exception as error:
        logger.error(
            f"Ошибка добавления баллона с NFC {balloon.nfc_tag} "
            f"в Redis-очередь: {error}"
        )
        raise
