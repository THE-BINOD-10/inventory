from collections import OrderedDict
from django.core.management import BaseCommand
from django.db.models import Q, Sum, F
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
from rest_api.views.common import get_local_date, get_misc_value
import datetime
from rest_api.views.easyops_api import *


def init_logger(log_file):
    log = logging.getLogger(log_file)

    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    return log

log = init_logger('logs/metropolis_consumption.log')

class Command(BaseCommand):
    help = "Consumption data"

    def handle(self, *args, **options):
    	user = User.objects.filter(username='demo')
    	self.stdout.write("Started Consumption call")
    	integrations = Integrations.objects.filter(user=user.id, status=1)
    	for integrate in integrations:
    		obj = eval(integrate.api_instance)(company_name=integrate.name, user=user)
    		today = datetime.date.today().strftime('%Y%m%d')
    		data = {'fromdate':today, 'todate':today, 'orgid':67}
    		Consumption_obj = obj.get_consumption_data(user=user)
    	log.info("succesfull Consumption call for %s" % user.username)
    	self.stdout.write("completed Consumption call")
