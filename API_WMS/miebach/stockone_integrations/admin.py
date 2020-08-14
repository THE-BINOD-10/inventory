# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from models import IntegrationMaster

# Register your models here.

from automate import runStoredAutomatedTasks
from stockone_integrations.automate import executeTaskForRow

@admin.register(IntegrationMaster)
class IntegrationMasterAdmin(admin.ModelAdmin):
    search_fields = ['user__username', 'integration_type', 'stockone_reference', 'integration_reference', 'integration_error']
    list_display = ['user', 'integration_type', 'stockone_reference', 'integration_reference', 'action_type','module_type', 'status', 'integration_error', 'creation_date', 'updation_date']
    list_filter = ('integration_type', 'status', 'user', 'module_type')

    actions = ["execute_queue"]

    def execute_queue(self, request, queryset):
        result = {}
        for row in queryset:
            executeTaskForRow(row)        
        

    execute_queue.short_description = "Execute Queue"


