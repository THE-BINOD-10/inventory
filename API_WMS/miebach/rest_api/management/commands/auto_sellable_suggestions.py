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


def init_logger(log_file):
    log = logging.getLogger(log_file)

    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    return log


log = init_logger('logs/auto_sellable_suggestions.log')


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
            log.info("Updated the Auto Sellable suggestions for the following users %s" % user.username)
        self.stdout.write("Updating Completed")
