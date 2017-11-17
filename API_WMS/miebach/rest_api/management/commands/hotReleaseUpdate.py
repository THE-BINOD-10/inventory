from django.core.management import BaseCommand
import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()
from miebach_admin.models import *
import datetime

class Command(BaseCommand):
    ''' Updating hot releases in SKUField Model(30 days) '''
    help = "Update Hot Release Data"

    def handle(self, *args, **options):
        self.stdout.write("Started Updating")
        self.days = 30
        self.hot_releases = SKUFields.objects.filter(field_type='hot_release', field_value='1')
        print len(self.hot_releases)
        for hot_release in self.hot_releases:
            update_date = hot_release.updation_date.date()
            current_date = datetime.date.today()
            delta =  current_date - update_date
            if delta.days > self.days:
                print delta.days
                hot_release.field_value = '0'
                hot_release.save()

