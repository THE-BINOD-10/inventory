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
import pandas as pd


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
log_err = init_logger('logs/metropolis_consumption_errors.log')

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
                    consumption_user = user
                    department_mapping = copy.deepcopy(DEPARTMENT_TYPES_MAPPING)
                    consumption_dict = consumption_objss[key]
                    data_dict = {'user':user}
                    try:
                        test_code = (str(re.sub(r'[^\x00-\x7F]+', '', consumption_dict.get('TCODE', ''))))
                        test_name = (str(re.sub(r'[^\x00-\x7F]+', '', consumption_dict.get('TNAME', ''))))
                    except:
                        test_code, test_name = '', ''
                    consumption_filter = {}
                    machine_name =''
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
                        machine_code = consumption_dict.get('DEVICEID', '')
                        machine_name = consumption_dict.get('DEVICEName', '')
                        if machine_code:
                            machine_obj = MachineMaster.objects.filter(user=company.id, machine_code=str(machine_code))
                            consumption_filter['machine__machine_code'] = str(machine_code)
                            if machine_obj.exists():
                                machine_name = str(machine_obj[0].machine_name)
                                data_dict['machine'] = machine_obj[0]
                            else:
                                machine_obj = MachineMaster.objects.create(**{'machine_code': str(machine_code), 'user': user, 'machine_name': machine_name})
                                data_dict['machine'] = machine_obj
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
                        org_objs = None
                        user_groups = None
                        department = ''
                        # instrument_objs = OrgInstrumentMapping.objects.filter(attune_id=orgid, investigation_id=investigation_id)
                        # if instrument_objs:
                        #     consumption_filter['machine'] = instrument_objs[0].machine
                        #     data_dict['machine'] = instrument_objs[0].machine
                        #     machine_name = instrument_objs[0].instrument_name
                        if machine_name:
                            org_objs = OrgDeptMapping.objects.filter(attune_id=orgid, tcode=test_code, instrument_name=machine_name)
                        #else:
                            #org_objs = OrgDeptMapping.objects.filter(attune_id=orgid, tcode=test_code)
                        consumption_user = user
                        if org_objs:
                            org_dept = org_objs[0].dept_name
                            department = [key for key, value in department_mapping.items() if  value == org_dept]
                            if department:
                                department = department[0]
                                if department == 'IMMUNO':
                                    department = 'IMMUN'
                            if department:
                                user_groups = UserGroups.objects.filter(user__userprofile__warehouse_type='DEPT', admin_user_id=user.id, user__userprofile__stockone_code=department)
                                # if not user_groups:
                                #     continue
                                if user_groups:
                                    consumption_user = User.objects.get(id = user_groups[0].user.id)
                                    data_dict['user'] = consumption_user
                        filter_date = datetime.date.today().strftime('%Y-%m-%d')
                        status = ''
                        consumption_obj_ = Consumption.objects.filter(user=consumption_user.id, creation_date__gt=filter_date, **consumption_filter)
                        if consumption_obj_.exists():
                            status = 'Success'
                            if consumption_obj_[0].status and department and user_groups and user.id in [19]:
                                status = reduce_consumption_stock(consumption_obj=consumption_obj_[0], total_test=data_dict['total_test'])
                            else:
                                exist_total_test = consumption_obj_[0].total_test
                                if exist_total_test < data_dict['total_test'] and user.id in [19]:
                                    diff_test = data_dict['total_test'] - exist_total_test
                                    status = reduce_consumption_stock(consumption_obj=consumption_obj_[0], total_test=diff_test)
                                    if status == 'Success':
                                        consumption_obj.update(**data_dict)
                        else:
                            run_date = (datetime.date.today() - datetime.timedelta(days=1))
                            data_dict['run_date'] = run_date
                            #if department in ['BIOCHE', 'IMMUN']:
                            consumption_obj_ = Consumption.objects.create(**data_dict)
                            if department and user_groups and user.id in [19]:
                                status = reduce_consumption_stock(consumption_obj=consumption_obj_, total_test=data_dict['total_test'])
                            else:
                                status = 'Not in dept'
                        if status == 'Success':
                            log.info("Reduced consumption stock for user %s and test code %s, plant %s" %  (str(consumption_user.username), str(test_code),str(user.username)))
                        else:
                            log.info("%s for user %s and data %s" % (status, str(consumption_user.username), str(data_dict)))
                    else:
                       log.info("Empty test code for %s,plant %s and data_dict was %s " % (str(consumption_user.username), str(user.username),str(data_dict))) 
                except Exception as e:
                    log.info("Consumption creation/updation failed for %s,plant %s,consumption object %s and data_dict was %s and exception %s" % (str(consumption_user.username), str(user.username), str(consumption_dict), str(data_dict), str(e)))
                    log_err.info("Consumption creation/updation failed for %s,plant %s and data_dict was %s and exception %s" % (str(consumption_user.username), str(user.username),str(data_dict), str(e)))

class Command(BaseCommand):
    help = "Consumption data"

    def handle(self, *args, **options):
        #users = User.objects.filter().exclude(userprofile__attune_id=None)
        users = User.objects.filter().exclude(userprofile__attune_id=None)
        self.stdout.write("Started Consumption call at"+ str(datetime.datetime.now().strftime('%y-%d-%m %H: %M')))
        for user in users:
            org_id = user.userprofile.attune_id
            today = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y%m%d')
            #today = 20210502
            subsidiary_id = user.userprofile.company_id
            subsidiary = User.objects.get(id=subsidiary_id)
            company = subsidiary
            integrations = Integrations.objects.filter(user=company.id, status=1, name='metropolis')
            if not integrations:
                company = User.objects.get(id=subsidiary.userprofile.company_id)
                integrations = Integrations.objects.filter(user=company.id, status=1, name='metropolis')
            #device_dict = {'date':today, 'org_id':org_id}
            # get_devices(device_dict, company)
            for integrate in integrations:
                obj = eval(integrate.api_instance)(company_name=integrate.name, user=company)
                #today = datetime.date.today().strftime('%Y%m%d')
                # for i in range(1,15):
                servers = list(OrgDeptMapping.objects.filter(attune_id=org_id).values_list('server_location', flat=True).distinct())
                data = {'FromDate':today, 'ToDate':today, 'OrgId':org_id}
                for server in servers:
                    consumption_obj = obj.get_consumption_data(data=data,user=company,server=server)
                    update_consumption(consumption_obj, user, company)
        report_data = get_consumption_mail_data(consumption_type='auto', from_date=datetime.date.today())
        #report_data=''
        if report_data:
            receivers = ["alap.christy@metropolisindia.com","pratip.patiyane@metropolisindia.com","flavia@metropolisindia.com","madhuri.bhosale@metropolisindia.com","jyotsna.naik@metropolisindia.com",
                            "thirupathi.battul@metropolisindia.com","nilesh.kamtekar@metropolisindia.com","nisha.dhabolkar@metropolisindia.com","rashid.farooqui@metropolisindia.com","amit.mishra@metropolisindia.com",
                            "kedar.shirodkar@metropolisindia.com","raviraj.deshpande@metropolisindia.com","nilam.tripathi@metropolisindia.com","surekha.kamble@metropolisindia.com","chaitali.berde@metropolisindia.com",
                            "vishal.yamagekar@metropolisindia.com","pravin.rajput@metropolisindia.com","jayant.rajani@metropolisindia.com","sunilpahuja@metropolisindia.com",
                            "medha@metropolisindia.com","vikas.kere@metropolisindia.com","roshan.nagvekar@metropolisindia.com","mahesh.sable@metropolisindia.com", "ashish@metropolisindia.com","salunkhe.yogita@metropolisindia.com","pratibha.pawar@metropolisindia.com","shraddha.lokegaonkar@metropolisindia.com","medha@metropolisindia.com","jyothi.mathias@metropolisindia.com","reshma.haryan@metropolisindia.com","jinal.dedhia@metropolisindia.com","karthik@mieone.com","nagi@mieone.com", "avinash@mieone.com"]
            #receivers = ["pravin.rajput@metropolisindia.com", "avinash@mieone.com","karthik@mieone.com","nagi@mieone.com"]
            path = 'static/excel_files/consumption_report.csv'
            df = pd.DataFrame(report_data)
            df.to_csv(path, index=False)
            email_subject = 'Auto Consumption Report'
            email_body = 'Please find the consumption test data report in the attachment'
            attachments = [{'path': path, 'name': 'consumption_report.csv'}]
            send_mail_attachment(receivers, email_subject, email_body, files=attachments)
        else:
            log.info('No report data')
        log.info("succesfull Consumption call for %s" % user.username)
        self.stdout.write("completed Consumption call at "+ str(datetime.datetime.now().strftime('%y-%d-%m %H: %M')))
