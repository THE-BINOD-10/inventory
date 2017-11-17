import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()
from miebach_admin.models import *
import datetime

class UpdateHotReleaseData:
    ''' Updating hot releases in SKUField Model(30 days) '''
    def __init__(self, days=30):
        self.days = days
        self.hot_releases = SKUFields.objects.filter(field_type='hot_release', field_value='1')

    def run_main(self):
        for hot_release in self.hot_releases:
            update_date = hot_release.updation_date.date()
            current_date = datetime.date.today()
            delta =  current_date - update_date
            if delta.days > self.days:
                print delta.days
                hot_release.field_value = '0'
                hot_release.save()

UpdateHotReleaseData(30).run_main()
