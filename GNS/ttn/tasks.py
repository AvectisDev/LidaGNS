import logging

from celery import shared_task

from .services import sync_current_ttn_from_miriada

logger = logging.getLogger('celery')


@shared_task
def fetch_current_ttn_from_miriada():
    logger.info("Запуск задачи получения текущих ТТН из Мириады")
    saved_count = sync_current_ttn_from_miriada()
    logger.info("Получение ТТН завершено, сохранено записей: %s", saved_count)
    return saved_count
