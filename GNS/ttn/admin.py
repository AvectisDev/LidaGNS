from django.contrib import admin
from .models import BalloonTtn, Contractor, City, FilePath

@admin.register(BalloonTtn)
class TTNAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'number',
        'contract',
        'shipper',
        'consignee',
        'city',
        'date'
    ]
    search_fields = [
        'number',
        'contract',
        'consignee',
        'city'
    ]
    list_filter = ['date']


@admin.register(Contractor)
class ContractorAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code']
    search_fields = ['name', 'code']


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(FilePath)
class FilePathAdmin(admin.ModelAdmin):
    list_display = ['path']
