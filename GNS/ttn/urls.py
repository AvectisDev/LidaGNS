from django.urls import path
from . import views

app_name = 'ttn'

urlpatterns = [
    # ТТН для баллонов
    path('balloons/', views.TTNView.as_view(), name="ttn_list"),
    path('balloons/create/', views.TTNCreateView.as_view(extra_context={
        "title": "Создание ТТН на приёмку/отгрузку баллонов"
    }),
         name="ttn_create"),
    path('balloons/<pk>/', views.TTNDetailView.as_view(), name="ttn_detail"),
    path('balloons/<pk>/update/', views.TTNUpdateView.as_view(extra_context={
        "title": "Редактирование ТТН на приёмку/отгрузку баллонов"
    }),
         name="ttn_update"),
    path('balloons/<pk>/delete/', views.TTNDeleteView.as_view(), name="ttn_delete"),

]
