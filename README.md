# LidaGNS

Система автоматизации производственного процесса обслуживания и учёта газовых баллонов (ГНС Лида).

Стек: Django / Daphne (ASGI), PostgreSQL, Redis, Celery, DRF, JWT.

Основные приложения: `core`, `filling_station`, `carousel`, `ttn`, `mobile`.

## Установка и запуск

1. Создать окружение Python 3.12 и установить зависимости.
2. Активировать окружение: `.venv\Scripts\activate` (Windows) или `source .venv/bin/activate`.
3. Создать `GNS/.env` (`SECRET_KEY`, `DEBUG`, параметры БД, Miriada и т.д.).
4. Из каталога `GNS`:
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   daphne GNS.asgi:application --bind 0.0.0.0 -p 8000 --application-close-timeout 10
   ```
5. UI: `http://localhost:8000`, Swagger: `http://localhost:8000/api/swagger/`.

## Redis

- **DB 0** (`CELERY_BROKER_URL`): брокер Celery.
- **DB 1** (Django `CACHES`): кэш приложения, FIFO-очереди баллонов для карусели `reader_<N>_balloon_queue`, метрики `carousel_<N>_metric_<name>`.

## Celery

Из каталога `GNS`:

```bash
celery -A GNS worker --loglevel=info --concurrency=8
celery -A GNS beat --loglevel=info
```

## RFID (FEIG Notification Mode)

Процесс RFID стартует из ASGI (`GNS/GNS/asgi.py`) как subprocess:

```bash
python -m filling_station.management.commands.rfid_utils.feig_protocol
```

Также: `python manage.py rfid_process`.

- Слушатель TCP (по умолчанию `0.0.0.0:8002`, env `RFID_NOTIFICATION_LISTEN_HOST` / `RFID_NOTIFICATION_LISTEN_PORT`).
- Конфигурация ридеров — таблица `ReaderSettings` (IP/порт, функция, кэширование).
- Обработка меток и оптики — прямые вызовы `filling_station.services` через `sync_to_async`.
- Индикация на ридере: FEIG `SET_OUTPUT` (зелёный свет / мигание), без OPC. Задача Celery `send_to_opc` удалена.

### Роли считывателей Лиды

| № | Назначение | Роль в интеграциях |
|---|---|---|
| 1 | Погрузка полного баллона на трал 1 | отгрузка (`function=u`) |
| 2 | Погрузка полного баллона на трал 2 | отгрузка (`function=u`) |
| 3 | Приёмка пустого баллона из трала 1 | приёмка (`function=l`) |
| 4 | Приёмка пустого баллона из трала 2 | приёмка (`function=l`) |
| 5 | Регистрация полного баллона на складе | склад, статус в Мириаду сразу |
| 6 | Регистрация пустого баллона в цеху | только учёт прохода |
| 7 | Наполнение баллона. Карусель №1 | очередь карусели, статус сразу |
| 8 | Наполнение баллона. Карусель №2 | очередь карусели, статус сразу |
| 9–12 | Переходы между наполнительным и ремонтным цехами | только учёт прохода |

Наборы для Мириады заданы в `filling_station/services/batches.py`:

- `MIRIADA_BATCH_STATUS_READERS = {1, 2, 3, 4}` — статусы баллонов уходят одним пакетом при закрытии партии.
- `MIRIADA_FILLING_READERS = {7, 8}` — наполнение, статус отправляется сразу.
- `MIRIADA_WAREHOUSE_STATUS_READERS = {5}` — регистрация на складе вне партии, статус сразу.

### Счётчики проходов

- `DailyReaderCounter` — ежедневные счётчики по RFID и оптическому датчику на каждый считыватель; источник данных для страниц `/reader/<N>/` и «Статистика».
- `TotalReadersCounter` — свод по складу (пустые/полные), задаётся вручную или через API `POST /api/total-readers-counter/manual-values`.
- Legacy-таблица `BalloonAmount` пока дублируется из `filling_station/services/rfid.py` и подлежит удалению.

## Карусель наполнения (NPort TCP)

Один subprocess на все активные карусели:

```bash
python manage.py carousel_process
# или
python -m carousel.management.commands.carousel.main
```

Запускается также из ASGI вместе с RFID. Паспорта баллонов передаются от RFID через Redis FIFO `reader_<N>_balloon_queue`.

## Партии баллонов

Единая модель `BalloonsBatch` (`batch_type` `l`/`u`, статусы в `BatchStatus`). Legacy `BalloonsLoadingBatch` / `BalloonsUnloadingBatch` оставлены в БД для миграций и связей `ttn.BalloonTtn`, новый код их не использует.

Веб-маршруты: `/balloons/batch/loading/…` и `/balloons/batch/unloading/…`, включая повторное закрытие ТТН в Мириаде (`retry-close`).
