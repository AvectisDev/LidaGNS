from django.urls import path
from filling_station import views


urlpatterns = [
    # path('', views.index, name="home"),
    path('', views.reader1, name="ballons_table"),
    path('reader2/', views.reader2, name="ballons_table"),
    path('reader3/', views.reader3, name="ballons_table"),
    path('reader4/', views.reader4, name="ballons_table"),
    path('reader5/', views.reader5, name="ballons_table"),
    path('reader6/', views.reader6, name="ballons_table"),
    path('reader7/', views.reader7, name="ballons_table"),
    path('reader8/', views.reader8, name="ballons_table"),

    path('client/', views.client, name="client"),
    #path('client/loading/', views.loading, name='loading'),
    #path('client/unloading/', views.unloading, name='unloading')
]