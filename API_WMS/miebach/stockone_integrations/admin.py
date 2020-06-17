# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from models import IntegrationMaster

# Register your models here.

from automate import runStoredAutomatedTasks

@admin.register(IntegrationMaster)
class IntegrationMasterAdmin(admin.ModelAdmin):
    search_fields = ['user', 'integration_type', 'stockone_reference', 'integration_reference']
    list_display = ['user', 'integration_type', 'stockone_reference', 'integration_reference', 'module_type', 'status', 'creation_date', 'updation_date']
    list_filter = ('integration_type', 'status', 'user', 'module_type')

    actions = ["execute_queue"]

    def execute_queue(self, request, queryset):
        runStoredAutomatedTasks()

    execute_queue.short_description = "Execute Queue"


