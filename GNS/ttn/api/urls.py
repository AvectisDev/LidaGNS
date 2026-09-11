from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MiriadaTtnViewSet

app_name = 'ttn_api'

router = DefaultRouter()
router.register(r'miriada', MiriadaTtnViewSet, basename='miriada-ttn')

urlpatterns = [path('', include(router.urls))]
