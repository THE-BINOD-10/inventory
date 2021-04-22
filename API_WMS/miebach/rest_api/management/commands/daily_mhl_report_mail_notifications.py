from collections import OrderedDict
from django.core.management import BaseCommand
from django.db.models import Q, Sum
import os
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
from rest_api.views.reports import *



def init_logger(log_file):
    log = logging.getLogger(log_file)

    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    return log


log = init_logger('logs/daily_report_mails.log')


class Command(BaseCommand):
    """
    Sending Remainder Mails
    """
    help = "Daily Remainder Mails for Reports"

    def handle(self, *args, **options):
        self.stdout.write("Script Started")
        user = User.objects.get(username='met_admin')
        report_file_names = []
        subject = '%s Reports dated on : %s for %s' % ('Automated Email for PR, PO, GRN ', datetime.datetime.now().date(), 'Metropolis')
        text = 'Please find the scheduled reports in the below attachments dated: %s' % str(datetime.datetime.now().date())
        start_date = datetime.datetime.strptime('2018-01-01', '%Y-%m-%d')
        start_date = get_utc_start_date(start_date)
        today = datetime.datetime.now()
        search_params = {'from_date': start_date, 'order_term': 'asc'}

        # SKU Wise PR Report
        try:
            pr_grn = get_pr_detail_report_data(search_params, user, user)
            if pr_grn:
                excel_name = 'PR_SKU_Report'
                headers = pr_grn['aaData'][0].keys()
                excel_path = async_excel(pr_grn, headers, today, excel_name=excel_name, user=user,
                                     file_type='', tally_report=0, automated_emails=True)
                if '.xls' in excel_path.split('/')[-1]:
                    excel_name += '.xls'
                else:
                    excel_name += '.csv'
                report_file_names.append({'name': excel_name, 'path': excel_path})
        except Exception as e:
            pass

        # SKU Wise PO Report
        try:
            po_grn = get_metropolis_po_detail_report_data(search_params, user, user)
            if po_grn:
                excel_name = 'PO_SKU_Report'
                headers = po_grn['aaData'][0].keys()
                excel_path = async_excel(po_grn, headers, today, excel_name=excel_name, user=user,
                                     file_type='', tally_report=0, automated_emails=True)
                if '.xls' in excel_path.split('/')[-1]:
                    excel_name += '.xls'
                else:
                    excel_name += '.csv'
                report_file_names.append({'name': excel_name, 'path': excel_path})
        except Exception as e:
            pass

        # PR PO GRN Report
        try:
            pr_po_grn = get_pr_po_grn_filter_data('', search_params, user, user)
            if pr_po_grn:
                excel_name = 'PR_PO_GRN_Report'
                headers = pr_po_grn['aaData'][0].keys()
                excel_path = async_excel(pr_po_grn, headers, today, excel_name=excel_name, user=user,
                                     file_type='', tally_report=0, automated_emails=True)
                if '.xls' in excel_path.split('/')[-1]:
                    excel_name += '.xls'
                else:
                    excel_name += '.csv'
                report_file_names.append({'name': excel_name, 'path': excel_path})
        except Exception as e:
            pass

        send_mail_attachment(['kaladhar@mieone.com', 'nagi@mieone.com', 'karthik@mieone.com', 'imran@mieone.com'], subject, text, files=report_file_names)
        self.stdout.write("Updating Completed")
