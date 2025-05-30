"""
URL configuration for GNS project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls')
"""
from django.contrib import admin
from django.urls import path, include
from debug_toolbar.toolbar import debug_toolbar_urls
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("filling_station.urls", namespace='filling_station')),
    path('carousel/', include("carousel.urls", namespace='carousel')),
    path('ttn/', include("ttn.urls", namespace='ttn')),

    path('api/', include("filling_station.api.urls", namespace='filling_station_api')),
    path('api/app/', include("mobile.urls", namespace='mobile_api')),
    path('api/carousel/', include("carousel.api.urls", namespace='carousel_api')),
] + debug_toolbar_urls()

urlpatterns += [
    path('accounts/', include('django.contrib.auth.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
