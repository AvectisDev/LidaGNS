import logging
from datetime import timedelta

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ttn import services
from ttn.api.serializers import MiriadaTtnSerializer
from ttn.models import MiriadaTtn

logger = logging.getLogger('filling_station')


class MiriadaTtnViewSet(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'], url_path='current')
    def get_current_ttn(self, request):
        try:
            services.sync_current_ttn_from_miriada()
        except Exception:
            logger.exception('Ошибка синхронизации ТТН из Мириады')
        start_date = timezone.localdate() - timedelta(days=5)
        queryset = MiriadaTtn.objects.filter(date__gte=start_date)
        return Response(MiriadaTtnSerializer(queryset, many=True).data)
