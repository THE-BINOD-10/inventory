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
from rest_api.views.sendgrid_mail import *

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

def update_consumption(consumption_objss, user, company, filter_datetime_obj= "", run_date= ""):
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
                    # department_mapping = copy.deepcopy(DEPARTMENT_TYPES_MAPPING)
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
                        consumption_filter = {'test_id': str(test_obj[0].id)}
                        name = consumption_dict.get('NAME', '')
                        orgid = consumption_dict.get('OrgID', '')
                        instrument_id = consumption_dict.get('InstrumentID', '')
                        if not instrument_id:
                            continue
                        instrument_name = consumption_dict.get('DEVICEName', '')
                        if instrument_id:
                            data_dict["instrument_id"]= str(instrument_id)
                            data_dict["instrument_name"]= str(instrument_name)
                            consumption_filter["instrument_id"] = str(instrument_id)
                        if orgid and instrument_id:
                            data_dict["org_id"]= int(orgid)
                            investigation_id = consumption_dict.get('InvestigationID', '')
                            number_dict = {'total_test':'TT', 'one_time_process':'P1', 'two_time_process':'P2','three_time_process':'P3' ,
                            'n_time_process':'PN', 'rerun':'RR', 'quality_check':'Q', 'total_patients':'TP', 'total':'T', 'no_patient':'NP',
                            'qnp':'QNP', 'patient_samples': 'PatientSamples'}
                            for key, value in number_dict.iteritems():
                                data_dict[key] = 0
                                if consumption_dict.get(value, 0):
                                    data_dict[key] = float(consumption_dict.get(value, 0))
                            sum_ = data_dict['one_time_process'] + data_dict['two_time_process'] + data_dict['three_time_process'] + data_dict['quality_check'] +data_dict['no_patient']
                            data_dict['calculated_total_tests']= data_dict['one_time_process'] + data_dict['two_time_process'] + data_dict['three_time_process'] + data_dict['n_time_process'] +  data_dict['quality_check'] +data_dict['no_patient']
                            diff = data_dict['calculated_total_tests'] - sum_
                            n_time_process_val = 0
                            if diff and data_dict['n_time_process']:
                                n_time_process_val = diff/data_dict['n_time_process']
                            data_dict['n_time_process_val'] = n_time_process_val
                            org_objs = None
                            user_groups = None
                            department = ''
                            consumption_user = user
                            to_date = ""
                            if not filter_datetime_obj:
                                filter_date = datetime.date.today().strftime('%Y-%m-%d')
                                to_date = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                            else:
                                to_date = (filter_datetime_obj.date() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                                filter_date = filter_datetime_obj.date().strftime('%Y-%m-%d')
                            status = ''
                            consumption_obj_ = Consumption.objects.filter(org_id=data_dict["org_id"], remarks='Auto-Consumption',  creation_date__gte=filter_date, creation_date__lt=to_date, **consumption_filter).exclude(status=9) #status=9 is deleted
                            if consumption_obj_.exists():
                                status = reduce_consumption_stock(consumption_obj=consumption_obj_[0], total_test=consumption_obj_[0].total_test)
                            else:
                                if not run_date:
                                    run_date = (datetime.date.today() - datetime.timedelta(days=1))
                                data_dict['run_date'] = run_date
                                data_dict['remarks'] = 'Auto-Consumption'
                                consumption_obj_ = Consumption.objects.create(**data_dict)
                                if filter_datetime_obj:
                                    consumption_obj_.creation_date = filter_datetime_obj
                                    consumption_obj_.updation_date = filter_datetime_obj
                                    consumption_obj_.save()
                                status = reduce_consumption_stock(consumption_obj=consumption_obj_, total_test=data_dict['total_test'])
                                if status == 'Success':
                                    log.info("Reduced consumption stock for user %s and test code %s, plant %s" %  (str(consumption_user.username), str(test_code),str(user.username)))
                                else:
                                    log.info("%s for user %s and data %s" % (status, str(consumption_user.username), str(data_dict)))
                        else:
                            log.info("Empty Instrument_id for %s,plant %s and data_dict was %s " % (
                            str(consumption_user.username), str(user.username), str(data_dict)))
                    else:
                       log.info("Empty test code for %s,plant %s and data_dict was %s " % (str(consumption_user.username), str(user.username),str(data_dict)))
                except Exception as e:
                    log.info("Consumption creation/updation failed for %s,plant %s,consumption object %s and data_dict was %s and exception %s" % (str(consumption_user.username), str(user.username), str(consumption_dict), str(data_dict), str(e)))
                    log_err.info("Consumption creation/updation failed for %s,plant %s and data_dict was %s and exception %s" % (str(consumption_user.username), str(user.username),str(data_dict), str(e)))

def insert_update_manual_consumption(consumption_objss, user, company, filter_datetime_obj= "", run_date= ""):
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
                    consumption_dict = consumption_objss[key]
                    data_dict = {'user':user, "instrument_id": "", "instrument_name": ""}
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
                        consumption_filter = {'test_id': str(test_obj[0].id)}
                        name = consumption_dict.get('NAME', '')
                        orgid = consumption_dict.get('OrgID', '')
                        if orgid:
                            data_dict["org_id"]= int(orgid)
                            number_dict = {'total_test':'TT', 'one_time_process':'P1', 'two_time_process':'P2','three_time_process':'P3' ,
                            'n_time_process':'PN', 'rerun':'RR', 'quality_check':'Q', 'total_patients':'TP', 'total':'T', 'no_patient':'NP',
                            'qnp':'QNP', 'patient_samples': 'PatientSamples'}
                            for key, value in number_dict.iteritems():
                                data_dict[key] = 0
                                if consumption_dict.get(value, 0):
                                    data_dict[key] = float(consumption_dict.get(value, 0))
                            sum_ = data_dict['one_time_process'] + data_dict['two_time_process'] + data_dict['three_time_process'] + data_dict['quality_check'] +data_dict['no_patient']
                            data_dict['calculated_total_tests']= data_dict['one_time_process'] + data_dict['two_time_process'] + data_dict['three_time_process'] + data_dict['n_time_process'] +  data_dict['quality_check'] +data_dict['no_patient']
                            diff = data_dict['calculated_total_tests'] - sum_
                            n_time_process_val = 0
                            if diff and data_dict['n_time_process']:
                                n_time_process_val = diff/data_dict['n_time_process']
                            data_dict['n_time_process_val'] = n_time_process_val
                            org_objs = None
                            user_groups = None
                            department = ''
                            consumption_user = user
                            to_date = ""
                            if not filter_datetime_obj:
                                filter_date = datetime.date.today().strftime('%Y-%m-%d')
                                to_date = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                            else:
                                to_date = (filter_datetime_obj.date() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                                filter_date = filter_datetime_obj.date().strftime('%Y-%m-%d')
                            status = ''
                            consumption_obj_ = Consumption.objects.filter(org_id=data_dict["org_id"], remarks='Manual-Consumption', creation_date__gte=filter_date, creation_date__lt=to_date, **consumption_filter).exclude(status=9) #status=9 is deleted
                            if consumption_obj_.exists():
                                print("Manual Consumption, is already  booked ")
                                # status = reduce_consumption_stock(consumption_obj=consumption_obj_[0], total_test=consumption_obj_[0].total_test)
                            else:
                                if not run_date:
                                    run_date = (datetime.date.today() - datetime.timedelta(days=1))
                                data_dict['run_date'] = run_date
                                data_dict['remarks'] = "Manual-Consumption"
                                consumption_obj_ = Consumption.objects.create(**data_dict)
                                if filter_datetime_obj:
                                    consumption_obj_.creation_date = filter_datetime_obj
                                    consumption_obj_.updation_date = filter_datetime_obj
                                    consumption_obj_.save()
                                status = reduce_consumption_stock(consumption_obj=consumption_obj_,
                                                                  total_test=data_dict['total_test'],
                                                                  book_date=run_date,
                                                                  consumption_type="Manual-Consumption")
                                # status = reduce_consumption_stock(consumption_obj=consumption_obj_, total_test=data_dict['total_test'])
                                if status == 'Success':
                                    log.info("Manual Consumption, Reduced consumption stock for user %s and test code %s, plant %s" %  (str(consumption_user.username), str(test_code),str(user.username)))
                                else:
                                    log.info("Manual Consumption, %s for user %s and data %s" % (status, str(consumption_user.username), str(data_dict)))
                        else:
                            log.info("Manual Consumption, Empty Instrument_id for %s,plant %s and data_dict was %s " % (
                            str(consumption_user.username), str(user.username), str(data_dict)))
                    else:
                       log.info("Manual Consumption, Empty test code for %s,plant %s and data_dict was %s " % (str(consumption_user.username), str(user.username),str(data_dict)))
                except Exception as e:
                    log.info("Consumption creation/Manual Consumption, updation failed for %s,plant %s,consumption object %s and data_dict was %s and exception %s" % (str(consumption_user.username), str(user.username), str(consumption_dict), str(data_dict), str(e)))
                    log_err.info("Consumption creation/Manual Consumption, updation failed for %s,plant %s and data_dict was %s and exception %s" % (str(consumption_user.username), str(user.username),str(data_dict), str(e)))

class Command(BaseCommand):
    help = "Consumption data"

    def add_arguments(self, parser):
        parser.add_argument('consumption_type', type=str)

    def handle(self, *args, **options):
        consumption_type = options['consumption_type']
        #users = User.objects.filter().exclude(userprofile__attune_id=None)
        users = User.objects.filter().exclude(userprofile__attune_id=None)
        self.stdout.write("Started Consumption call at"+ str(datetime.datetime.now().strftime('%y-%d-%m %H: %M')) + " Type : "+str(consumption_type))
        i=1
        data_list= []
        start_date=(datetime.date.today() - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
        while i>=1:
            for user in users:
                if consumption_type == "manual_consumption":
                    if user.userprofile.attune_id!=67:
                        continue
                #user.userprofile.stockone_code not in ["27001", "24010", "32006", "24032", "19065", "27023", "27028", "27042", "27062", "27073", "27077", "27080", "27082", "27098", "27103"]
                #if user.userprofile.stockone_code not in ["27001", "24010", "32006", "24032", "19065", "27023", "27028", "27042", "27062", "27073", "27077", "27080", "27082", "27098", "27103", "27019", "27007", "23029", "8049", "23052", "23079", "24022", "24039", "23086", "24072"]:
                #if user.userprofile.stockone_code not in ["29087", "29101", "29188", "19065", "27023", "27028", "27042", "27062", "27073", "27077", "27080", "27082", "27093", "27098", "27103", "6015", "27020", "27019", "8049", "10034", "23029", "23052", "23079", "23086", "24022", "24039", "24072", "30084", "32154", "29055", "32059", "32143"]:
                #    continue
                org_id = user.userprofile.attune_id
                # to_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y%m%d')
                today_date = (datetime.date.today() - datetime.timedelta(days=i))
                from_date= today_date.strftime('%Y%m%d')  #from_date
                print("\nfrom_date ", from_date)
                to_date = from_date
                filter_date = (datetime.datetime.today() - datetime.timedelta(days=i-1))
                run_date = today_date
                subsidiary_id = user.userprofile.company_id
                subsidiary = User.objects.get(id=subsidiary_id)
                company = subsidiary
                integrations = Integrations.objects.filter(user=company.id, status=1, name='metropolis')
                if not integrations:
                    company = User.objects.get(id=subsidiary.userprofile.company_id)
                    integrations = Integrations.objects.filter(user=company.id, status=1, name='metropolis')
                #device_dict = {'date':today, 'org_id':org_id}
                # get_devices(device_dict, company)#
                for integrate in integrations:
                    obj = eval(integrate.api_instance)(company_name=integrate.name, user=company)
                    #today = datetime.date.today().strftime('%Y%m%d') 
                    # for i in range(1,15):
                    servers = list(OrgDeptMapping.objects.filter(attune_id=org_id).values_list('server_location', flat=True).distinct())
                    data = {'FromDate':from_date, 'ToDate':to_date, 'OrgId':org_id}
                    if consumption_type == "manual_consumption":
                        if org_id==67:
                            consumption_obj = obj.get_consumption_data(data=data, user=company,
                                                                       server='MANUAL_CONSUMPTION_API')
                            insert_update_manual_consumption(consumption_obj, user, company,
                                                             filter_datetime_obj=filter_date,
                                                             run_date=run_date)
                            try:
                                df = pd.DataFrame(consumption_obj).T  # transpose to look just like the sheet above
                                data_list.append(df)
                            except Exception as e:
                                print(e)
                            break
                    elif consumption_type == "auto_consumption":
                        for server in servers:
                            consumption_obj = obj.get_consumption_data(data=data, user=company, server=server)
                            update_consumption(consumption_obj, user, company, filter_datetime_obj=filter_date,
                                               run_date=run_date)
                            try:
                                df = pd.DataFrame(consumption_obj).T  # transpose to look just like the sheet above
                                data_list.append(df)
                            except Exception as e:
                                print(e)
            i-=1
        if data_list:
            result = pd.concat(data_list)
            from_date = start_date
            to_date = (datetime.date.today() - datetime.timedelta(days=i+1)).strftime('%Y-%m-%d')
            try:
                result.to_excel('%s_attune_consumption_test_data/Attune_data_Auto_from_%s_to_%s.xlsx'%(consumption_type, from_date, to_date))
            except Exception as e:
                print(e)
        report_data = get_consumption_mail_data(consumption_type='auto', from_date=datetime.date.today())
        #report_data=''
        if report_data:
            receivers = ["alap.christy@metropolisindia.com","pratip.patiyane@metropolisindia.com","flavia@metropolisindia.com","madhuri.bhosale@metropolisindia.com","jyotsna.naik@metropolisindia.com",
                            "thirupathi.battul@metropolisindia.com","nilesh.kamtekar@metropolisindia.com","nisha.dhabolkar@metropolisindia.com","rashid.farooqui@metropolisindia.com","amit.mishra@metropolisindia.com",
                            "kedar.shirodkar@metropolisindia.com","raviraj.deshpande@metropolisindia.com","nilam.tripathi@metropolisindia.com","surekha.kamble@metropolisindia.com","chaitali.berde@metropolisindia.com",
                            "vishal.yamagekar@metropolisindia.com","pravin.rajput@metropolisindia.com","jayant.rajani@metropolisindia.com","sunilpahuja@metropolisindia.com",
                            "medha@metropolisindia.com","vikas.kere@metropolisindia.com","roshan.nagvekar@metropolisindia.com","mahesh.sable@metropolisindia.com", "ashish@metropolisindia.com","salunkhe.yogita@metropolisindia.com","pratibha.pawar@metropolisindia.com","shraddha.lokegaonkar@metropolisindia.com","medha@metropolisindia.com","jyothi.mathias@metropolisindia.com","reshma.haryan@metropolisindia.com","jinal.dedhia@metropolisindia.com","karthik@mieone.com","nagi@mieone.com", "naresh@mieone.com"]
            receivers = ["naresh@mieone.com", "nagi@mieone.com"]
            path = 'static/excel_files/consumption_report.csv'
            df = pd.DataFrame(report_data)
            df.to_csv(path, index=False)
            email_subject = 'Auto Consumption Report'
            email_body = 'Please find the consumption test data report in the attachment'
            attachments = [{'path': path, 'name': 'consumption_report.csv'}]
            send_sendgrid_mail('mb_mail@stockone.in', receivers, email_subject, email_body, files=attachments) 
            #send_mail_attachment(receivers, email_subject, email_body, files=attachments)
        else:
            log.info('No report data')
        log.info("succesfull Consumption call for %s" % user.username)
        self.stdout.write("completed Consumption call at "+ str(datetime.datetime.now().strftime('%y-%d-%m %H: %M')))
