"""Общие схемы OpenAPI (только документация, не меняют ответы API)."""

from rest_framework import serializers


class ApiErrorSerializer(serializers.Serializer):
    """Единый формат ошибок в OpenAPI."""

    error = serializers.CharField(required=False, allow_blank=True)
    detail = serializers.CharField(required=False, allow_blank=True)
    code = serializers.CharField(required=False, allow_blank=True)
    errors = serializers.DictField(
        child=serializers.JSONField(),
        required=False,
    )
