from collections import OrderedDict
from django.core.management import BaseCommand
from django.db.models import Q, Sum
import os
import tarfile
import os.path
import logging
import django
import datetime
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from django.template import loader, Context
from django.db.models import F
from miebach_admin.models import *
from rest_api.views.mail_server import *
from rest_api.views.common import *
from rest_api.views.sendgrid_mail import *
from rest_api.views.reports import *
from rest_api.management.commands.analytics_script import *
import dateutil.relativedelta

def init_logger(log_file):
    log = logging.getLogger(log_file)

    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    return log


log = init_logger('logs/analytics_mhl.log')


class Command(BaseCommand):
    """
    Update the incremental data
    """
    help = "MHL ANANLYTICS"

    def handle(self, *args, **options):
        self.stdout.write("Script Started")
        user = User.objects.get(username='mhl_admin')
        report_file_names = []
        subject = '%s Reports dated on : %s for %s' % ('Analytics reports ', datetime.datetime.now().date(), 'Metropolis')
        text = 'Please find the scheduled reports in the below attachments dated: %s' % str(datetime.datetime.now().date())
        now =  datetime.datetime.now()
        from_date = now + dateutil.relativedelta.relativedelta(minutes= -90)
        search_params ={'from_date': from_date}
        data= get_pr_detail_report_data(search_params, user, user)
        data= get_po_detail_report_data(search_params, user, user)
        data= get_grn_detail_report_data(search_params, user, user)

