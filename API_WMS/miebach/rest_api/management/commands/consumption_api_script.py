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

def update_consumption(consumption_obj, user):
    if consumption_obj and consumption_obj.get('STATUS_CODE', 0) == 200:
        status_time = consumption_obj.get('TIME', 0)
        if consumption_obj.keys() > 2:
            consumption_lis = consumption_obj.keys()
            consumption_lis.remove('STATUS_CODE')
            consumption_lis.remove('TIME')
            for key in consumption_lis:
                consumption_dict = consumption_obj[key]
                data_dict = {'user':user}
                test_code = consumption_dict.get('TCODE', '')
                if test_code:
                    test_obj = TestMaster.objects.filter(test_code=str(test_code))
                    if test_obj.exists():
                        data_dict['test'] = test_obj[0]
                test_name = consumption_dict.get('TNAME', '')
                name = consumption_dict.get('NAME', '')
                orgid = consumption_dict.get('OrgID', '')
                number_dict = {'total_test':'TT', 'one_time_process':'P1', 'two_time_process':'P2','three_time_process':'P3' ,
                'n_time_process':'PN', 'rerun':'RR', 'quality_check':'Q', 'total_patients':'TP', 'total':'T', 'no_patient':'NP',
                'qnp':'QNP', 'patient_samples': 'PatientSamples'}
                for key, value in number_dict.iteritems():
                    data_dict[key] = 0
                    if consumption_dict.get(value, 0):
                        data_dict[key] = float(consumption_dict.get(value, 0))
                sum_ = data_dict['one_time_process'] + data_dict['two_time_process'] + data_dict['three_time_process'] + data_dict['quality_check'] +data_dict['no_patient']
                diff = data_dict['total_test'] - sum_
                if diff and data_dict['n_time_process']:
                    n_time_process_val = diff/data_dict['n_time_process']
                data_dict['n_time_process_val'] = n_time_process_val
                try:
                    Consumption.objects.create(**data_dict)
                except:
                    log.info("Consumption creation failed for %s and data_dict was %s" % str(user.username), str(data_dict))


class Command(BaseCommand):
    help = "Consumption data"

    def handle(self, *args, **options):
        users = User.objects.filter().exclude(userprofile__attune_id=None)
        self.stdout.write("Started Consumption call")
        for user in users:
            integrations = Integrations.objects.filter(user=user.id, status=1, name='metropolis')
            for integrate in integrations:
                obj = eval(integrate.api_instance)(company_name=integrate.name, user=user)
                today = datetime.date.today().strftime('%Y%m%d')
                data = {'fromdate':today, 'todate':today, 'orgid':67}
                consumption_obj = obj.get_consumption_data(data=data,user=user)
                update_consumption(consumption_obj, user)
            log.info("succesfull Consumption call for %s" % user.username)
        self.stdout.write("completed Consumption call")
