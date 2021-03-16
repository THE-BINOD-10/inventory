from collections import OrderedDict
from django.core.management import BaseCommand
from django.db.models import Q, Sum, F
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
from rest_api.views import *
from rest_api.views.common import get_local_date, get_misc_value, reduce_consumption_stock
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

def update_consumption(consumption_objss, user, company):
    if consumption_objss and consumption_objss.get('STATUS_CODE', 0) == 200:
        status_time = consumption_objss.get('TIME', 0)
        if consumption_objss.keys() > 2:
            consumption_lis = consumption_objss.keys()
            consumption_lis.remove('STATUS_CODE')
            consumption_lis.remove('TIME')
            count = 0
            for key in consumption_lis:
                count += 1
                try:
                    department_mapping = copy.deepcopy(DEPARTMENT_TYPES_MAPPING)
                    consumption_dict = consumption_objss[key]
                    data_dict = {'user':user}
                    test_code = consumption_dict.get('TCODE', '')
                    test_name = consumption_dict.get('TNAME', '')
                    consumption_filter = {}
                    if test_code:
                        test_obj = TestMaster.objects.filter(test_code=str(test_code), user=company.id)
                        if test_obj.exists():
                            data_dict['test'] = test_obj[0]
                        else:
                            department_mapping = copy.deepcopy(DEPARTMENT_TYPES_MAPPING)
                            dept_type = department_mapping.get(user.userprofile.stockone_code, '')
                            TestMaster.objects.create(**{'test_code':str(test_code), 'test_type':'', 'test_name':str(test_name),
                                                        'department_type':dept_type,'user':company.id, 
                                                        'sku_code':str(test_code), 'wms_code':str(test_code), 'sku_desc':str(test_name)})
                            test_obj = TestMaster.objects.filter(test_code=str(test_code), user=company.id)
                            data_dict['test'] = test_obj[0]
                        consumption_filter = {'test_id': str(test_obj[0].id)}
                    #machine_code = consumption_dict.get('MachineID', '')
                    #if machine_code:
                        #machine_obj = MachineMaster.objects.filter(user=company.id,machine_code=str(machine_code))
                        #if machine_obj.exists():
                            #data_dict['machine'] = machine_obj[0]
                            #consumption_filter['machine__machine_code'] = str(machine_code)
                    name = consumption_dict.get('NAME', '')
                    orgid = consumption_dict.get('OrgID', '')
                    investigation_id = consumption_dict.get('InvestigationID', '')
                    number_dict = {'total_test':'TT', 'one_time_process':'P1', 'two_time_process':'P2','three_time_process':'P3' ,
                    'n_time_process':'PN', 'rerun':'RR', 'quality_check':'Q', 'total_patients':'TP', 'total':'T', 'no_patient':'NP',
                    'qnp':'QNP', 'patient_samples': 'PatientSamples'}
                    for key, value in number_dict.iteritems():
                        data_dict[key] = 0
                        if consumption_dict.get(value, 0):
                            data_dict[key] = float(consumption_dict.get(value, 0))
                    sum_ = data_dict['one_time_process'] + data_dict['two_time_process'] + data_dict['three_time_process'] + data_dict['quality_check'] +data_dict['no_patient']
                    diff = data_dict['total_test'] - sum_
                    n_time_process_val = 0
                    if diff and data_dict['n_time_process']:
                        n_time_process_val = diff/data_dict['n_time_process']
                    data_dict['n_time_process_val'] = n_time_process_val
                    org_objs = OrgDeptMapping.objects.filter(attune_id=orgid, tcode=test_code)
                    consumption_user = user
                    if org_objs:
                        org_dept = org_objs[0].dept_name
                        department = [key for key, value in department_mapping.items() if  value == org_dept]
                        if department:
                            department = department[0]
                        if department:
                            user_groups = UserGroups.objects.filter(user__userprofile__warehouse_type='DEPT', admin_user_id=user.id, user__userprofile__stockone_code=department)
                            if not user_groups:
                                continue
                            consumption_user = User.objects.get(id = user_groups[0].user.id)
                            data_dict['user'] = consumption_user
                    instrument_objs = OrgInstrumentMapping.objects.filter(attune_id=orgid, investigation_id=investigation_id)
                    if instrument_objs:
                        consumption_filter['machine'] = instrument_objs[0].machine
                        data_dict['machine'] = instrument_objs[0].machine
                    consumption_obj = Consumption.objects.filter(user=consumption_user.id, **consumption_filter)
                    if consumption_obj.exists():
                        status = 'Success'
                        if consumption_obj[0].status == 1:
                            status = reduce_consumption_stock(consumption_obj=consumption_obj[0], total_test=data_dict['total_test'])
                        else:
                            exist_total_test = consumption_obj[0].total_test
                            if exist_total_test < data_dict['total_test']:
                                diff_test = data_dict['total_test'] - exist_total_test
                                status = reduce_consumption_stock(consumption_obj=consumption_obj[0], total_test=diff_test)
                                if status == 'Success':
                                    consumption_obj.update(**data_dict)
                    else:
                        consumption_obj = Consumption.objects.create(**data_dict)
                        status = reduce_consumption_stock(consumption_obj=consumption_obj, total_test=data_dict['total_test'])
                    if status == 'Success':
                        log.info("Reduced consumption stock for user %s and test code %s, plant %s" %  (str(consumption_user.username), str(test_code),str(user.username)))
                except Exception as e:
                    log.info("Consumption creation/updation failed for %s,plant %s and data_dict was %s and exception %s" % (str(consumption_user.username), str(user.username),str(data_dict), str(e)))


class Command(BaseCommand):
    help = "Consumption data"

    def handle(self, *args, **options):
        #users = User.objects.filter().exclude(userprofile__attune_id=None)
        users = User.objects.filter(userprofile__attune_id=67).exclude(userprofile__attune_id=None)
        self.stdout.write("Started Consumption call at"+ str(datetime.datetime.now().strftime('%y-%d-%m %H: %M')))
        for user in users:
            org_id = user.userprofile.attune_id
            today = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y%m%d')
            #today = 20210312
            subsidiary_id = user.userprofile.company_id
            subsidiary = User.objects.get(id=subsidiary_id)
            company = subsidiary
            integrations = Integrations.objects.filter(user=company.id, status=1, name='metropolis')
            if not integrations:
                company = User.objects.get(id=subsidiary.userprofile.company_id)
                integrations = Integrations.objects.filter(user=company.id, status=1, name='metropolis')
            device_dict = {'date':today, 'org_id':org_id}
            get_devices(device_dict, company)
            for integrate in integrations:
                obj = eval(integrate.api_instance)(company_name=integrate.name, user=company)
                #today = datetime.date.today().strftime('%Y%m%d')
                # for i in range(1,15):
                servers = list(OrgDeptMapping.objects.filter(attune_id=org_id).values_list('server_location', flat=True).distinct())
                data = {'fromdate':today, 'todate':today, 'orgid':org_id}
                for server in servers:
                    consumption_obj = obj.get_consumption_data(data=data,user=company,server=server)
                    update_consumption(consumption_obj, user, company)
            log.info("succesfull Consumption call for %s" % user.username)
        self.stdout.write("completed Consumption call at "+ str(datetime.datetime.now().strftime('%y-%d-%m %H: %M')))
