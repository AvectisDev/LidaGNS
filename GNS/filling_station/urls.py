"""URL-маршруты веб-интерфейса filling_station: баллоны, партии, транспорт, статистика."""

from django.urls import path
from . import views

app_name = 'filling_station'

urlpatterns = [
    # Архив баллонов
    path('', views.BalloonListView.as_view(), name='balloon_list'),
    path('balloon/<pk>/', views.BalloonDetailView.as_view(), name='balloon_detail'),
    path("balloon/<pk>/update/", views.BalloonUpdateView.as_view(extra_context={
        "title": "Редактирование паспорта баллона"
    }),
         name="balloon_update"),
    path("balloon/<pk>/delete/", views.BalloonDeleteView.as_view(), name="balloon_delete"),

    # Таблицы считывателей
    path('reader/<int:reader_number>/', views.reader_info, name="reader"),

    # Партии приёмки баллонов
    path('balloons/batch/loading/', views.BalloonBatchListView.as_view(extra_context={
        "title": "Партии приёмки баллонов"
    }),
         name="balloon_loading_batch_list"),
    path('balloons/batch/loading/<pk>/', views.BalloonBatchDetailView.as_view(extra_context={
        "title": "Детали партии приёмки баллонов",
        "main_list": "loading"
    }),
         name="balloon_loading_batch_detail"),
    path('balloons/batch/loading/<pk>/update/', views.BalloonBatchUpdateView.as_view(extra_context={
        "title": "Редактирование партии приёмки баллонов"
    }),
         name="balloon_loading_batch_update"),
    path('balloons/batch/loading/<pk>/delete/', views.BalloonBatchDeleteView.as_view(),
         name="balloon_loading_batch_delete"),
    path('balloons/batch/loading/<pk>/retry-close/', views.balloon_batch_retry_close,
         name="balloon_loading_batch_retry_close"),

    # Партии отгрузки баллонов
    path('balloons/batch/unloading/', views.BalloonBatchListView.as_view(extra_context={
        "title": "Партии отгрузки баллонов"
    }),
         name="balloon_unloading_batch_list"),
    path('balloons/batch/unloading/<pk>/', views.BalloonBatchDetailView.as_view(extra_context={
        "title": "Детали партии отгрузки баллонов",
        "main_list": "unloading"
    }),
         name="balloon_unloading_batch_detail"),
    path('balloons/batch/unloading/<pk>/update/', views.BalloonBatchUpdateView.as_view(extra_context={
        "title": "Редактирование партии отгрузки баллонов"
    }),
         name="balloon_unloading_batch_update"),
    path('balloons/batch/unloading/<pk>/delete/', views.BalloonBatchDeleteView.as_view(),
         name="balloon_unloading_batch_delete"),
    path('balloons/batch/unloading/<pk>/retry-close/', views.balloon_batch_retry_close,
         name="balloon_unloading_batch_retry_close"),

    # Грузовики
    path('transport/trucks/', views.TruckView.as_view(), name="truck_list"),
    path('transport/trucks/create/', views.TruckCreateView.as_view(extra_context={
        "title": "Создание грузовика"
    }),
         name="truck_create"),
    path('transport/trucks/<pk>/', views.TruckDetailView.as_view(), name="truck_detail"),
    path('transport/trucks/<pk>/update/',
         views.TruckUpdateView.as_view(extra_context={
             "title": "Редактирование грузовика"
         }),
         name="truck_update"),
    path('transport/trucks/<pk>/delete/', views.TruckDeleteView.as_view(), name="truck_delete"),

    # Статистика
    path('statistic', views.statistic, name="statistic"),
]
