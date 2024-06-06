from django.contrib import admin
from .models import Ballon
from import_export import resources


class BallonResources(resources.ModelResource):
    class Meta:
        model = Ballon
        fields = ('id', 'nfc_tag', 'creation_date', 'state')


# Register your models here.
admin.site.register(Ballon)
