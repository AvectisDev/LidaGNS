import logging
import requests
from ..models import (Balloon, BalloonAmount, BalloonsLoadingBatch, BalloonsUnloadingBatch, Reader, Carousel,
                      CarouselSettings)
from django.shortcuts import get_object_or_404
from django.core.cache import cache
import json
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, action, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from filling_station.tasks import send_to_opc
from datetime import datetime, date, timedelta
from .serializers import (BalloonSerializer, CarouselSerializer, CarouselSettingsSerializer, BalloonAmountSerializer,
                          BalloonsLoadingBatchSerializer, BalloonsUnloadingBatchSerializer,
                          ActiveLoadingBatchSerializer, ActiveUnloadingBatchSerializer,
                          BalloonAmountLoadingSerializer, BalloonAmountUnloadingSerializer)

logger = logging.getLogger('filling_station')

USER_STATUS_LIST = [
    'Создание паспорта баллона',
    'Наполнение баллона сжиженным газом',
    'Погрузка полного баллона в кассету',
    'Погрузка полного баллона в трал',
    'Погрузка пустого баллона в кассету',
    'Погрузка пустого баллона в трал',
    'Регистрация полного баллона на складе',
    'Регистрация пустого баллона на складе',
    'Снятие пустого баллона у потребителя',
    'Установка баллона потребителю',
    'Принятие баллона от другой организации',
    'Снятие RFID метки',
    'Установка новой RFID метки',
    'Редактирование паспорта баллона',
    'Покраска',
    'Техническое освидетельствование',
    'Выбраковка',
    'Утечка газа',
    'Опорожнение(слив) баллона',
    'Контрольное взвешивание'
]
BALLOONS_LOADING_READER_LIST = [3, 4]
BALLOONS_UNLOADING_READER_LIST = [1, 2]


class BalloonViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)

    @action(detail=False, methods=['get'], url_path='nfc/(?P<nfc_tag>[^/.]+)')
    def get_by_nfc(self, request, nfc_tag=None):
        balloon = get_object_or_404(Balloon, nfc_tag=nfc_tag)
        serializer = BalloonSerializer(balloon)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='serial-number/(?P<serial_number>[^/.]+)')
    def get_by_serial_number(self, request, serial_number=None):
        balloons = Balloon.objects.filter(serial_number=serial_number)
        serializer = BalloonSerializer(balloons, many=True)
        return Response(serializer.data)

    def get_balloon_by_nfc_tag(self, nfc_tag: str):
        """
        Метод для получения данных о баллоне по NFC-метке из Мириады.
        """
        # miriada server address
        BASE_URL = 'https://publicapi-vitebsk.cloud.gas.by'
        # метод получения основных данных баллона
        url = f'{BASE_URL}/getballoonbynfctag?nfctag={nfc_tag}&realm=brestoblgas'

        try:
            response = requests.get(url, timeout=2)
            response.raise_for_status()
            result = response.json()

            if result.get('status') == "Ok":
                self.logger.info(f"Паспорт баллона получен из Мириады. Номер метки: {nfc_tag}")
                return result['List']
            else:
                self.logger.warning(f"API Мириады вернуло ошибку. Номер метки: {nfc_tag}")
                return []

        except Exception as error:
            self.logger.error(f'Ошибка в методе получения паспорта баллона из Мириады: {error}')
            return None

    def send_status_to_miriada(self, send_type: str, nfc_tag: str, send_data: dict = None):
        """
        Метод для отправки статусов баллонов по NFC-метке в Мириаду.
        Поддерживается 3 основных типа отправки (send_type):
        filling - Наполнение баллона
        registering_in_warehouse - Регистрация баллона на склад
        loading_into_truck - Погрузка баллона в машину
        """
        send_urls = {
            'filling': f'{settings.MIRIADA_API_POST_URL}/fillingballoon',
            'registering_in_warehouse': f'{settings.MIRIADA_API_POST_URL}/balloontosklad',
            'loading_into_truck': f'{settings.MIRIADA_API_POST_URL}/balloontocar',
        }

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        payload = {
            "nfctag": nfc_tag,
            "realm": "grodnooblgas"
        }

        if send_data is not None:
            fulness = send_data.get('fulness')  # 1-полный, 0 — пустой
            if fulness:
                payload.update({"fulness": fulness})

            number_auto = send_data.get('number_auto')  # "AM 7881-2" номер машины.(Номер должен быть добавлен в  ПК «Автопарк»
            type_car = send_data.get('type_car')    # 0-кассета, 1 — трал
            if number_auto and type_car:
                payload.update({
                    "fulness": fulness,
                    "number_auto": number_auto,
                    "type_car": type_car
                })

        try:
            # Создаем запрос в Мириаду
            session = requests.Session()
            req = requests.Request(
                'POST',
                send_urls.get(send_type),
                auth=(settings.MIRIADA_AUTH_LOGIN, settings.MIRIADA_AUTH_PASSWORD),
                headers=headers,
                json=payload
            )
            prepared = session.prepare_request(req)

            self.logger.debug(
                f"Подготовленный запрос:\n"
                f"URL: {prepared.url}\n"
                f"Headers: {prepared.headers}\n"
                f"Body: {prepared.body}"
            )
            self.logger.debug(f'Тело запроса: {payload}')

            response = session.send(prepared, timeout=2)
            response.raise_for_status()
            if response.status_code == 200:
                self.logger.info(f"Статус по {send_type} успешно отправлен")
            else:
                self.logger.warning(f"Ошибка по {send_type}! Код: {response.status_code}, Описание: {response.reason}")

        except Exception as error:
            self.logger.error(f'Ошибка в методе отправки статуса баллона в Мириаду: {error}')

    @action(detail=False, methods=['post'], url_path='update-by-reader')
    def update_by_reader(self, request):
        """
        Метод для обновления данных баллона по NFC-метке. Если у баллона активен флаг "обновление паспорта", то
        повторно запрашиваем данные в Мириаде через метод get_balloon_by_nfc_tag
        """
        balloon_status = request.data.get('status')
        if not balloon_status:
            self.logger.error("Статус баллона отсутствует в теле запроса")

        nfc_tag = request.data.get('nfc_tag')
        if not nfc_tag:
            self.logger.error("Номер метки отсутствует в теле запроса")
            return Response({"error": "nfc_tag is required"}, status=400)

        balloon, created = Balloon.objects.update_or_create(
            nfc_tag=nfc_tag,
            defaults={
                'status': balloon_status
            }
        )
        reader_number = request.data.get('reader_number')
        if reader_number is None:
            self.logger.error("Номер ридера отсутствует в теле запроса")
        elif reader_number == 8:
            self.send_status_to_miriada(nfc_tag=nfc_tag, send_type='filling')
        elif reader_number in [3, 4]:
            self.send_status_to_miriada(nfc_tag=nfc_tag, send_type='registering_in_warehouse', send_data={'fulness': 0})
        elif reader_number == 5:
            self.send_status_to_miriada(nfc_tag=nfc_tag, send_type='registering_in_warehouse', send_data={'fulness': 1})
        elif reader_number in [1, 2]:
            self.send_status_to_miriada(nfc_tag=nfc_tag, send_type='loading_into_truck',
                                        send_data={'fulness': 1, "type_car": 1, "number_auto": ' ', })

        # Если требуется обновление паспорта или идёт приёмка новых баллонов - выполняем запрос в Мириаду
        if balloon.update_passport_required in (True, None) or reader_number in [3, 4]:
            balloon_passport_from_miriada = self.get_balloon_by_nfc_tag(nfc_tag)
            # Данные получены
            if balloon_passport_from_miriada:
                balloon.update_passport_required = False
                balloon.serial_number = balloon_passport_from_miriada['number']
                balloon.netto = balloon_passport_from_miriada['netto']
                balloon.brutto = balloon_passport_from_miriada['brutto']
                balloon.filling_status = balloon_passport_from_miriada['status']
                # Сохраняем модель
                balloon.save()

        # Выполняем передачу данных в OPC сервер (лампочки на считывателях)
        send_to_opc.delay(reader=reader_number, blink=balloon.update_passport_required)

        # Если ридер стоит на приёмке или отгрузке, то добавляем текущий баллон в партию
        reader_function = request.data.get('reader_function')
        if reader_function:
            self.add_balloon_to_batch_from_reader(balloon, reader_number, reader_function)

        # Добавляем информацию по баллону в таблицу с ридерами
        if reader_number:
            reader_balloon = Reader.objects.create(
                number=reader_number,
                nfc_tag=nfc_tag,
                serial_number=balloon.serial_number,
                size=balloon.size,
                netto=balloon.netto,
                brutto=balloon.brutto,
                filling_status=balloon.filling_status
            )
            # Сохраняем баллон в кэш на каруселях наполнения №1 и 2)
            if reader_number in [7, 8]:
                cache_key = f'reader_{reader_number}_balloon_stack'
                stack = cache.get(cache_key, [])

                # Добавляем объект в стек
                stack.insert(0, {
                    'number': reader_balloon.number,
                    'nfc_tag': reader_balloon.nfc_tag,
                    'serial_number': reader_balloon.serial_number,
                    'size': reader_balloon.size,
                    'netto': reader_balloon.netto,
                    'brutto': reader_balloon.brutto,
                    'filling_status': reader_balloon.filling_status,
                })
                logger.debug(f'Стек считывателя {reader_number} = {stack}')

                # Сохраняем обновленный стек в кэш
                cache.set(cache_key, stack, timeout=None)

        serializer = BalloonSerializer(balloon)
        return Response(serializer.data)

    def add_balloon_to_batch_from_reader(self, balloon, reader_number, batch_type):
        today = date.today()

        if batch_type == 'loading':
            batch = BalloonsLoadingBatch.objects.filter(begin_date=today,
                                                        reader_number=reader_number,
                                                        is_active=True).first()
        elif batch_type == 'unloading':
            batch = BalloonsUnloadingBatch.objects.filter(begin_date=today,
                                                          reader_number=reader_number,
                                                          is_active=True).first()
        else:
            batch = None

        if batch:
            batch.balloon_list.add(balloon)
            batch.amount_of_rfid = (batch.amount_of_rfid or 0) + 1
            batch.save()

    def create(self, request):
        nfc_tag = request.data.get('nfc_tag', None)
        balloons = Balloon.objects.filter(nfc_tag=nfc_tag).exists()
        if not balloons:
            serializer = BalloonSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_409_CONFLICT)

    def partial_update(self, request, pk=None):
        balloon = get_object_or_404(Balloon, id=pk)

        serializer = BalloonSerializer(balloon, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_balloon_status_options(request):
    return Response(USER_STATUS_LIST)


@api_view(['GET'])
def get_loading_balloon_reader_list(request):
    return Response(BALLOONS_LOADING_READER_LIST)


@api_view(['GET'])
def get_unloading_balloon_reader_list(request):
    return Response(BALLOONS_UNLOADING_READER_LIST)


class CarouselViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'], url_path='get-parameter')
    def get_parameter(self, request):
        settings = CarouselSettings.objects.get(id=1)
        serializer = CarouselSettingsSerializer(settings)
        return Response(serializer.data)

    def partial_update(self, request, pk=1):
        """
        Запись параметров карусели
        :param request:
        :param pk: номер карусели
        :return:
        """
        carousel = get_object_or_404(CarouselSettings, id=pk)

        serializer = CarouselSettingsSerializer(carousel, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='balloon-update')
    def update_from_carousel(self, request):
        """

        """
        request_type = request.data.get('request_type')
        post_number = request.data.get('post_number')

        logger.debug(f"Обработка запроса от карусели: Тип - {request_type}, пост - {post_number}")
        if not request_type:
            logger.error("Тип запроса отсутствует в теле запроса")
            return Response({"error": "Не указан тип запроса"}, status=status.HTTP_400_BAD_REQUEST)

        if request_type == '0x7a':
            # Валидируем и сохраняем данные через сериализатор
            serializer = CarouselSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                logger.debug(f"Данные по запросу 0x7a успешно сохранены")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            try:
                carousel_post = Carousel.objects.filter(post_number=post_number).first()
                carousel_post.is_empty = False
                carousel_post.full_weight = request.data.get('full_weight')
                carousel_post.save()
                logger.debug(f"Данные по запросу 0x70 успешно сохранены")
                return Response(status=status.HTTP_200_OK)
            except Exception as error:
                logger.error(f'Ошибка при обработке запроса типа 0x70 - {error}')
                return Response({"error": str(error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BalloonsLoadingBatchViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='active')
    def is_active(self, request):
        batches = BalloonsLoadingBatch.objects.filter(is_active=True)
        serializer = ActiveLoadingBatchSerializer(batches, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='last-active')
    def last_active(self, request):
        batch = BalloonsLoadingBatch.objects.filter(is_active=True).first()
        if not batch:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = BalloonsLoadingBatchSerializer(batch)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='rfid-amount')
    def rfid_amount(self, request, pk=None):
        batch = get_object_or_404(BalloonsLoadingBatch, id=pk)
        serializer = BalloonAmountLoadingSerializer(batch)
        return Response(serializer.data)

    def create(self, request):
        serializer = BalloonsLoadingBatchSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        batch = get_object_or_404(BalloonsLoadingBatch, id=pk)

        if not request.data.get('is_active', True):
            current_date = datetime.now()
            request.data['end_date'] = current_date.date()
            request.data['end_time'] = current_date.time()

        serializer = BalloonsLoadingBatchSerializer(batch, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='add-balloon')
    def add_balloon(self, request, pk=None):
        balloon_id = request.data.get('balloon_id', None)
        batch = get_object_or_404(BalloonsLoadingBatch, id=pk)

        if balloon_id:
            balloon = get_object_or_404(Balloon, id=balloon_id)
            if batch.balloon_list.filter(id=balloon_id).exists():
                return Response(status=status.HTTP_409_CONFLICT)
            else:
                batch.balloon_list.add(balloon)
                batch.amount_of_rfid = (batch.amount_of_rfid or 0) + 1
                batch.save()
                return Response(status=status.HTTP_200_OK)

        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='remove-balloon')
    def remove_balloon(self, request, pk=None):
        balloon_id = request.data.get('balloon_id', None)
        batch = get_object_or_404(BalloonsLoadingBatch, id=pk)

        if balloon_id:
            balloon = get_object_or_404(Balloon, id=balloon_id)
            if batch.balloon_list.filter(id=balloon_id).exists():
                batch.balloon_list.remove(balloon)
                if batch.amount_of_rfid:
                    batch.amount_of_rfid -= 1
                else:
                    batch.amount_of_rfid = 0
                batch.save()
                return Response(status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_400_BAD_REQUEST)


class BalloonsUnloadingBatchViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='active')
    def is_active(self, request):
        batches = BalloonsUnloadingBatch.objects.filter(is_active=True)
        serializer = ActiveUnloadingBatchSerializer(batches, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='last-active')
    def last_active(self, request):
        batch = BalloonsUnloadingBatch.objects.filter(is_active=True).first()
        if not batch:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = BalloonsUnloadingBatchSerializer(batch)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='rfid-amount')
    def rfid_amount(self, request, pk=None):
        batch = get_object_or_404(BalloonsUnloadingBatch, id=pk)
        serializer = BalloonAmountUnloadingSerializer(batch)
        return Response(serializer.data)

    def create(self, request):
        serializer = BalloonsUnloadingBatchSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        batch = get_object_or_404(BalloonsUnloadingBatch, id=pk)

        if not request.data.get('is_active', True):
            current_date = datetime.now()
            request.data['end_date'] = current_date.date()
            request.data['end_time'] = current_date.time()

        serializer = BalloonsUnloadingBatchSerializer(batch, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='add-balloon')
    def add_balloon(self, request, pk=None):
        balloon_id = request.data.get('balloon_id', None)
        batch = get_object_or_404(BalloonsUnloadingBatch, id=pk)

        if balloon_id:
            balloon = get_object_or_404(Balloon, id=balloon_id)
            if batch.balloon_list.filter(id=balloon_id).exists():
                return Response(status=status.HTTP_409_CONFLICT)
            else:
                batch.balloon_list.add(balloon)
                batch.amount_of_rfid = (batch.amount_of_rfid or 0) + 1
                batch.save()
                return Response(status=status.HTTP_200_OK)

        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='remove-balloon')
    def remove_balloon(self, request, pk=None):
        balloon_id = request.data.get('balloon_id', None)
        batch = get_object_or_404(BalloonsUnloadingBatch, id=pk)

        if balloon_id:
            balloon = get_object_or_404(Balloon, id=balloon_id)
            if batch.balloon_list.filter(id=balloon_id).exists():
                batch.balloon_list.remove(balloon)
                if batch.amount_of_rfid:
                    batch.amount_of_rfid -= 1
                else:
                    batch.amount_of_rfid = 0
                batch.save()
                return Response(status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_400_BAD_REQUEST)


class BalloonAmountViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'], url_path='update-amount-of-rfid')
    def update_amount_of_rfid(self, request, *args, **kwargs):
        today = date.today()
        reader_id = request.data.get('reader_id')

        instance, created = BalloonAmount.objects.get_or_create(
            change_date=today,
            reader_id=reader_id,
            defaults={
                'amount_of_rfid': 1,
                'amount_of_balloons': 0,
                'reader_status': request.data.get('reader_status')
            }
        )

        if not created:
            instance.amount_of_rfid += 1
            instance.save()

        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='update-amount-of-sensor')
    def update_amount_of_sensor(self, request, *args, **kwargs):
        today = date.today()
        reader_id = request.data.get('reader_id')

        instance, created = BalloonAmount.objects.get_or_create(
            change_date=today,
            reader_id=reader_id,
            defaults={
                'amount_of_rfid': 0,
                'amount_of_balloons': 1,
                'reader_status': request.data.get('reader_status')
            }
        )

        if not created:
            instance.amount_of_balloons += 1
            instance.save()

        return Response(status=status.HTTP_200_OK)
