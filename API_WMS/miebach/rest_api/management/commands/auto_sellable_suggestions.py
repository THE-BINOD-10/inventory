from collections import OrderedDict
from django.core.management import BaseCommand
from django.db.models import Q, Sum
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
from rest_api.views.common import update_auto_sellable_data
import datetime

class Command(BaseCommand):
    """
    Auto Sellable Suggestions
    """
    help = "Save Auto sellable suggestions data"

    def handle(self, *args, **options):
        self.stdout.write("Started Updating")
        misc_details = MiscDetail.objects.filter(misc_type='sellable_segregation', misc_value='true').\
            values_list('user', flat=True)
        users = User.objects.filter(id__in=misc_details)
        for user in users:
            update_auto_sellable_data(user)
        self.stdout.write("Updating Completed")
