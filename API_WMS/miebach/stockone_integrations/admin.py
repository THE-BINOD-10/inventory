# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from models import IntegrationMaster

# Register your models here.

@admin.register(IntegrationMaster)
class IntegrationMasterAdmin(admin.ModelAdmin):
    search_fields = ['user', 'integration_type', 'stockone_reference', 'integration_reference']
    list_display = ['user', 'integration_type', 'stockone_reference', 'integration_reference', 'creation_date', 'updation_date']