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

def update_consumption(consumption_obj):
	if consumption_obj and consumption_obj.get('STATUS_CODE', 0) == 200:
		status_time = consumption_obj.get('TIME', 0)
		if consumption_obj.keys() > 2:
			for key in consumption_obj.keys():
				if key != 'TIME' or key != 'STATUS_CODE':
					consumption_dict = consumption_obj[key]
					test_code = consumption_dict.get('TCode', '')
					test_name = consumption_dict.get('TNAME', '')
					name = consumption_dict.get('NAME', '')
					orgid = consumption_dict.get('OrgID', '')
					total_test = float(consumption_dict.get('TT', 0))
					one_time_process = float(consumption_dict.get('P1', 0))
					two_time_process = float(consumption_dict.get('P2', 0))
					three_time_process = float(consumption_dict.get('P3', 0))
					n_time_process = float(consumption_dict.get('Pn', 0))
					rerun = float(consumption_dict.get('RR', 0))
					quality_check  = float(consumption_dict.get('Q', 0))
					total_patients = float(consumption_dict.get('TP', 0))
					total = float(consumption_dict.get('T', 0))
					no_patient = float(consumption_dict.get('NP', 0))
					qnp = float(consumption_dict.get('QNP', 0))
					patient_samples = float(consumption_dict.get('PatientSamples', 0))
					sum_ = one_time_process + two_time_process + three_time_process + quality_check +no_patient
					diff = total_test - sum_
					n_time_process_val = diff/n_time_process
					Consumption.objects.create(**{'user':user, 'test':'', 'patient_samples':patient_samples, 'rerun': rerun,'total_test': total_test,
						                          'one_time_process': one_time_process, 'two_time_process':two_time_process, 'three_time_process':three_time_process,
						                          'n_time_process': n_time_process, 'quality_check': quality_check, 'total_patients': total_patients,
						                           'total': total, 'no_patient': no_patient, 'qnp': qnp, 'n_time_process_val': n_time_process_val})


class Command(BaseCommand):
    help = "Consumption data"

    def handle(self, *args, **options):
    	user = User.objects.get(username='demo')
    	self.stdout.write("Started Consumption call")
    	integrations = Integrations.objects.filter(user=user.id, status=1, name='metropolis')
    	for integrate in integrations:
    		obj = eval(integrate.api_instance)(company_name=integrate.name, user=user)
    		today = datetime.date.today().strftime('%Y%m%d')
    		data = {'fromdate':today, 'todate':today, 'orgid':67}
    		consumption_obj = obj.get_consumption_data(data=data,user=user)
    		update_consumption(consumption_obj)
    	log.info("succesfull Consumption call for %s" % user.username)
    	self.stdout.write("completed Consumption call")
