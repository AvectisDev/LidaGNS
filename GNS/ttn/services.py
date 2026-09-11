import json
import logging
import time
from datetime import datetime
from typing import Optional, Tuple

import requests
from django.conf import settings

logger = logging.getLogger('filling_station')


def get_current_ttn_from_miriada() -> list:
    """Получить и нормализовать текущие баллонные ТТН из Мириады."""
    url = f'{settings.MIRIADA_API_URL}/getcurrentttn?realm=brestoblgas'
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    for attempt in range(settings.MIRIADA_REQUEST_RETRIES + 1):
        try:
            response = requests.get(
                url,
                auth=(settings.MIRIADA_AUTH_LOGIN, settings.MIRIADA_AUTH_PASSWORD),
                headers=headers,
                timeout=settings.MIRIADA_TIMEOUT,
            )
            response.raise_for_status()
            result = []
            for item in response.json():
                try:
                    result.append({
                        'ttn_id': item.get('id'),
                        'name': item.get('name', ''),
                        'auto': item.get('car_plate', ''),
                        'date': datetime.strptime(item.get('date'), '%d.%m.%Y').date(),
                    })
                except (TypeError, ValueError):
                    logger.exception('Некорректная ТТН Мириады: %s', item)
            return result
        except (requests.RequestException, ValueError, TypeError):
            logger.exception('Ошибка получения ТТН из Мириады, попытка %s', attempt + 1)
            if attempt < settings.MIRIADA_REQUEST_RETRIES:
                time.sleep(settings.MIRIADA_RETRY_DELAY_SECONDS)
    return []


def sync_current_ttn_from_miriada() -> int:
    from .models import MiriadaTtn

    saved_count = 0
    for data in get_current_ttn_from_miriada():
        if not data['ttn_id']:
            continue
        MiriadaTtn.objects.update_or_create(
            ttn_id=data['ttn_id'],
            defaults={key: data[key] for key in ('name', 'auto', 'date')},
        )
        saved_count += 1
    return saved_count


def _response_error(response) -> Optional[str]:
    try:
        payload = json.loads(response.text)
    except (json.JSONDecodeError, TypeError):
        return response.text.strip() or None
    if isinstance(payload, dict):
        return payload.get('description') or payload.get('title') or payload.get('message')
    return str(payload)


def close_ttn_in_miriada(ttn_id: int, batch=None) -> Tuple[bool, Optional[str]]:
    """Закрыть баллонную ТТН в Мириаде; интерфейс совместим с batches.py."""
    url = f'{settings.MIRIADA_API_POST_URL}/closettn'
    payload = {'id_ttn': ttn_id, 'realm': 'brestoblgas'}
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    last_error = None
    for attempt in range(settings.MIRIADA_REQUEST_RETRIES + 1):
        try:
            response = requests.post(
                url,
                auth=(settings.MIRIADA_AUTH_LOGIN, settings.MIRIADA_AUTH_PASSWORD),
                headers=headers,
                json=payload,
                timeout=settings.MIRIADA_TIMEOUT,
            )
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, dict) and any(
                    key.lower() == 'result' and str(value).lower() == 'ok'
                    for key, value in result.items()
                ):
                    return True, None
            last_error = _response_error(response) or f'HTTP {response.status_code}'
            if 400 <= response.status_code < 500 and response.status_code not in (408, 429):
                return False, last_error
        except (requests.RequestException, ValueError, TypeError) as exc:
            last_error = str(exc)
            logger.exception('Ошибка закрытия ТТН %s', ttn_id)
        if attempt < settings.MIRIADA_REQUEST_RETRIES:
            time.sleep(settings.MIRIADA_RETRY_DELAY_SECONDS)
    return False, last_error


def save_balloon_ttn(ttn):
    ttn.save()
    return ttn
