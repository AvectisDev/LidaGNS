from django.urls import path
import views


urlpatterns = [
    # path('', views.index, name="home"),
    path('reader/<str:reader>', views.reader_info, name="ballons_table"),
    path('api/GetBallonPassport', views.apiGetBallonPassport, name="ballons_table"),
    path('api/UpdateBallonPassport', views.apiUpdateBallonPassport, name="ballons_table"),
    path('client/', views.client, name="client"),
    #path('client/loading/', views.loading, name='loading'),
    #path('client/unloading/', views.unloading, name='unloading')
]