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


log = init_logger('logs/reports_daily_mails.log')


class Command(BaseCommand):
    """
    Reports Daily Mail
    """

    help = "Reports Daily Mail"
    def add_arguments(self, parser):
        parser.add_argument('report_name', type=str)

    def handle(self, *args, **options):
        report_name = options['report_name']
        self.stdout.write("Script Started for %s"% (report_name))
        user = User.objects.get(username='mhl_admin')
        report_file_names = []
        subject = '%s dated on : %s for %s' % ('Automated Email for %s '% report_name.replace("_", " "), datetime.datetime.now().date(), 'Metropolis')
        text = 'Please find the scheduled reports in the below attachments dated: %s' % str(datetime.datetime.now().date())
        start_date = datetime.datetime.strptime('2020-10-01', '%Y-%m-%d')
        #start_date = get_utc_start_date(start_date)
        #days= -100
        #start_date = datetime.datetime.now() + dateutil.relativedelta.relativedelta(days= -50)
        today = datetime.datetime.now()
        search_params = {'from_date': start_date, 'order_term': 'asc'}
        if report_name == "GRN_report_header_level":
            try:
                search_params['grn_from_date'] = search_params['from_date']
                grn_report_header_level = get_po_filter_data('', search_params, user, user)
                if grn_report_header_level:
                    excel_name = 'GRN report Header level'
                    # headers = grn_report_header_level['aaData'][0].keys()
                    headers = GRN_DICT['dt_headers']
                    excel_path = async_excel(grn_report_header_level, headers, today, excel_name=excel_name, user=user,
                                         file_type='', tally_report=0, automated_emails=True)
                    if '.xls' in excel_path.split('/')[-1]:
                        excel_name += '.xls'
                    else:
                        excel_name += '.csv'
                    report_file_names.append({'name': excel_name, 'path': excel_path})
                    print report_file_names
            except Exception as e:
                pass

        elif report_name == "GRN_report_line_level":
            try:
                search_params['grn_from_date'] = search_params['from_date']
                grn_report_line_level = get_sku_wise_po_filter_data('', search_params, user, user)
                if grn_report_line_level:
                    excel_name = 'GRN report Line level'
                    #headers = grn_report_line_level['aaData'][0].keys()
                    headers = SKU_WISE_GRN_DICT['dt_headers']
                    excel_path = async_excel(grn_report_line_level, headers, today, excel_name=excel_name, user=user,
                                         file_type='', tally_report=0, automated_emails=True)
                    if '.xls' in excel_path.split('/')[-1]:
                        excel_name += '.xls'
                    else:
                        excel_name += '.csv'
                    report_file_names.append({'name': excel_name, 'path': excel_path})
                    print report_file_names
            except Exception as e:
                pass

        elif report_name == "PR_report_header_level":
            try:
                search_params['pr_from_date'] = search_params['from_date']
                pr_report_header_level = get_pr_report_data(search_params, user, user)
                if pr_report_header_level:
                    excel_name = 'PR report Header level'
                    headers = PR_REPORT_DICT['dt_headers']
                    # headers = pr_report_header_level['aaData'][0].keys()
                    excel_path = async_excel(pr_report_header_level, headers, today, excel_name=excel_name, user=user,
                                         file_type='', tally_report=0, automated_emails=True)
                    if '.xls' in excel_path.split('/')[-1]:
                        excel_name += '.xls'
                    else:
                        excel_name += '.csv'
                    report_file_names.append({'name': excel_name, 'path': excel_path})
                    print report_file_names
            except Exception as e:
                pass

        elif report_name == "PR_report_line_level":
            try:
                search_params['pr_from_date'] = search_params['from_date']
                pr_report_line_level = get_pr_detail_report_data(search_params, user, user)
                if pr_report_line_level:
                    excel_name = 'PR report Line level'
                    headers = PR_DETAIL_REPORT_DICT['dt_headers']
                    # headers = pr_report_line_level['aaData'][0].keys()
                    excel_path = async_excel(pr_report_line_level, headers, today, excel_name=excel_name, user=user,
                                         file_type='', tally_report=0, automated_emails=True)
                    if '.xls' in excel_path.split('/')[-1]:
                        excel_name += '.xls'
                    else:
                        excel_name += '.csv'
                    report_file_names.append({'name': excel_name, 'path': excel_path})
                    print report_file_names
            except Exception as e:
                pass

        elif report_name == "PO_report_header_level":
            try:
                search_params['po_from_date'] = search_params['from_date']
                po_report_header_level = get_metropolis_po_report_data(search_params, user, user)
                if po_report_header_level:
                    excel_name = 'PO report Header level'
                    headers = METROPOLIS_PO_REPORT_DICT['dt_headers']
                    # headers = po_report_header_level['aaData'][0].keys()
                    excel_path = async_excel(po_report_header_level, headers, today, excel_name=excel_name, user=user,
                                         file_type='', tally_report=0, automated_emails=True)
                    if '.xls' in excel_path.split('/')[-1]:
                        excel_name += '.xls'
                    else:
                        excel_name += '.csv'
                    report_file_names.append({'name': excel_name, 'path': excel_path})
                    print report_file_names
            except Exception as e:
                pass

        elif report_name == "PO_report_line_level":
            try:
                search_params['po_from_date'] = search_params['from_date']
                po_report_line_level = get_metropolis_po_detail_report_data(search_params, user, user)
                if po_report_line_level:
                    excel_name = 'PO report Line level'
                    headers = METROPOLIS_PO_DETAIL_REPORT_DICT['dt_headers']
                    # headers = po_report_line_level['aaData'][0].keys()
                    excel_path = async_excel(po_report_line_level, headers, today, excel_name=excel_name, user=user,
                                         file_type='', tally_report=0, automated_emails=True)
                    if '.xls' in excel_path.split('/')[-1]:
                        excel_name += '.xls'
                    else:
                        excel_name += '.csv'
                    report_file_names.append({'name': excel_name, 'path': excel_path})
                    print report_file_names
            except Exception as e:
                pass

        new_paths = []
        zip_subdir = ""
        for dat in report_file_names:
            print dat
            zip_filename ='static/excel_files/'+dat['name'] + '.tar.gz'
            with tarfile.open(zip_filename, "w:gz") as tar:
                tar.add(dat['path'], arcname=os.path.basename(dat['path']))
            new_paths.append({'path': zip_filename, 'name': zip_filename.split('/')[-1]})
        print new_paths
        mails_list =  ['naresh@mieone.com', 'nagi@mieone.com', 'pradeep@mieone.com', 'jignesh.shah@metropolisindia.com',  'mahesh.sable@metropolisindia.com', 'malay.saha@metropolisindia.com', 'shrawan.kashyap@metropolisindia.com', 'sudeep.das@metropolisindia.com', 'sudhir.mahindrakar@metropolisindia.com', 'dhanashri.surve@metropolisindia.com', 'himanshu.shah@metropolisindia.com', 'kaladhar@mieone.com']
        #mails_list = ['naresh@mieone.com']
        send_sendgrid_mail('mhl_mail@stockone.in', mails_list, subject, text, files=new_paths)
        #send_mail_attachment(['naresh@mieone.com', 'nagi@mieone.com'], subject, text, files=new_paths)
        self.stdout.write("Report sent %s "% report_name)


