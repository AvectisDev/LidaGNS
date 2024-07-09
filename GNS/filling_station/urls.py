from django.urls import path
from filling_station import views


urlpatterns = [
    # path('', views.index, name="home"),
    path('reader/<str:reader>', views.reader_info, name="ballons_table"),
    path('api/getBallonById', views.apiGetBaallonPassport, name="ballons_table"),


    path('client/', views.client, name="client"),
    #path('client/loading/', views.loading, name='loading'),
    #path('client/unloading/', views.unloading, name='unloading')
]