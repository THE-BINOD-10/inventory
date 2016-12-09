from django.contrib import admin

from models import SKURelation, SKUMaster

# Register your models here.


@admin.register(SKUMaster)
class SKUMasterAdmin(admin.ModelAdmin):
    search_fields = ['sku_code']

@admin.register(SKURelation)
class SKUGroupAdmin(admin.ModelAdmin):
    pass
