from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiTypes, extend_schema_view
from rest_framework import generics, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import Truck
from .serializers import TruckSerializer


@extend_schema_view(
    get=extend_schema(
        tags=['Грузовики'],
        summary='Получить список грузовиков',
        description='''Получение списка грузовиков с возможностью фильтрации:
        - По наличию на станции (on_station)
        - По регистрационному номеру (registration_number)''',
        parameters=[
            OpenApiParameter(
                name='on_station',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Фильтр по наличию на станции (true/false)',
                required=False,
                examples=[
                    OpenApiExample(
                        'Только на станции',
                        value=True
                    ),
                    OpenApiExample(
                        'Только вне станции',
                        value=False
                    )
                ]
            ),
            OpenApiParameter(
                name='registration_number',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Поиск по регистрационному номеру (например: АX12347)',
                required=False
            )
        ],
        responses={
            200: TruckSerializer(many=True),
            404: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT
        },
        examples=[
            OpenApiExample(
                'Пример успешного ответа',
                value=[{
                    "id": 1,
                    "car_brand": "МАЗ",
                    "registration_number": "АX12347",
                    "type": "Седельный тягач",
                    "capacity_cylinders": 60,
                    "max_weight_of_transported_cylinders": 1500.5,
                    "max_mass_of_transported_gas": 1200.0,
                    "max_gas_volume": 2000.0,
                    "empty_weight": 7500.0,
                    "full_weight": 20000.0,
                    "is_on_station": True,
                    "entry_date": "2023-05-15",
                    "entry_time": "08:30:00",
                    "departure_date": None,
                    "departure_time": None,
                    "trailer": {
                        "id": 1,
                        "registration_number": "A1234B7"
                    }
                }],
                response_only=True
            )
        ]
    ),
    post=extend_schema(
        tags=['Грузовики'],
        summary='Добавить новый грузовик',
        description='Создание новой записи о грузовике в системе',
        request=TruckSerializer,
        responses={
            201: TruckSerializer,
            400: OpenApiTypes.OBJECT
        },
        examples=[
            OpenApiExample(
                'Пример запроса',
                value={
                    "car_brand": "MAN",
                    "registration_number": "АX12347",
                    "type": 1,
                    "capacity_cylinders": 50,
                    "max_weight_of_transported_cylinders": 1400.0,
                    "max_mass_of_transported_gas": 1100.0,
                    "max_gas_volume": 1800.0,
                    "empty_weight": 8000.0,
                    "full_weight": 21000.0,
                    "is_on_station": False
                },
                request_only=True
            )
        ]
    ),
    patch=extend_schema(
        tags=['Грузовики'],
        summary='Обновить данные грузовика',
        description='Частичное обновление информации о грузовике',
        request=TruckSerializer,
        responses={
            200: TruckSerializer,
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT
        },
        examples=[
            OpenApiExample(
                'Пример запроса на обновление',
                value={
                    "id": 1,
                    "is_on_station": False,
                    "entry_date": "2023-05-16",
                    "entry_time": "10:00:00",
                    "departure_date": "2023-05-16",
                    "departure_time": "16:30:00"
                },
                request_only=True
            )
        ]
    )
)
class TruckView(APIView):
    """
    API для управления грузовиками на станции

    Позволяет:
    - Получать списки грузовиков с детальной информацией
    - Добавлять новые грузовики в систему
    - Обновлять статус пребывания на станции
    - Управлять временем въезда/выезда
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        on_station = request.query_params.get('on_station')
        registration_number = request.query_params.get('registration_number')

        queryset = Truck.objects.all()

        if on_station is not None:
            queryset = queryset.filter(is_on_station=on_station.lower() == 'true')
            if not queryset.exists():
                return Response(
                    {"detail": "Грузовики с указанным фильтром не найдены"},
                    status=status.HTTP_404_NOT_FOUND
                )

        if registration_number:
            truck = get_object_or_404(Truck, registration_number=registration_number)
            serializer = TruckSerializer(truck)
            return Response(serializer.data)

        serializer = TruckSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = TruckSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        truck_id = request.data.get('id')
        if not truck_id:
            return Response(
                {"error": "Параметр 'id' обязателен для обновления"},
                status=status.HTTP_400_BAD_REQUEST
            )

        truck = get_object_or_404(Truck, id=truck_id)
        serializer = TruckSerializer(truck, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
