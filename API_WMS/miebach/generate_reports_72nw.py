activate_this = 'setup/MIEBACH/bin/activate_this.py'
execfile(activate_this, dict(__file__ = activate_this))
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()

import pytz
import datetime
import xlwt
#import create_environment
from  rest_api.views.mail_server import send_mail_attachment
from rest_api.views.miebach_utils import *
from miebach_admin.models import *
from rest_api.views.utils import *

log = init_logger('logs/72network_report_mail.log')

reports_list = {'SKU List': get_sku_filter_data, 'Location Wise Stock': get_location_stock_data,
                'Receipt Summary': get_receipt_filter_data, 'Dispatch Summary': get_dispatch_data,
                'SKU Wise': print_sku_wise_data,'Shipment Report':get_shipment_report_data}

data_dict = {'sku_list': 'SKU List', 'location_wise_stock': 'Location Wise Stock', 'receipt_note': 'Receipt Summary',
             'dispatch_summary': 'Dispatch Summary', 'sku_wise': 'SKU Wise','shipment_report':'Shipment Report'}


class MailReports:
    def __init__(self):
        self.report_file_names = []

    def send_reports_mail(self, user, mail_now=False):
        from rest_api.views.common import folder_check, get_work_sheet, write_excel, get_linked_user_objs
        report_frequency = MiscDetail.objects.filter(misc_type__contains='report_frequency', user=user.id)
        log.info("Report Frequency::%s" %report_frequency)
        if not report_frequency and not mail_now:
            return

        if report_frequency:
            report_date = report_frequency[0].creation_date
            frequency_value = int(report_frequency[0].misc_value)
            frequency_range = MiscDetail.objects.filter(misc_type__contains='report_data_range', user=user.id)
            if frequency_range:
                frequency_range = frequency_range[0].misc_value
                date_difference = (datetime.datetime.now(pytz.utc) - report_date)
                date_difference = (date_difference.days*24) + (date_difference.seconds/3600)
                if frequency_range == "Days":
                    frequency_value *= 24
            log.info(("Report config. : user= %s, frequency= %s hrs") % (str(user.id), str(frequency_value)))
            if ((frequency_value in (0,) or (date_difference % frequency_value) != 0) and not mail_now):
                log.info("Came to this if condition ::%s ::%s" %(frequency_value, date_difference))
                return

        enabled_reports = MiscDetail.objects.filter(misc_type__contains='report', misc_value='true', user=user.id)
        sister_whs = [user]
        append_wh_name = False
        firebase_response = None
        if user.username == '72Networks':
            try:
                from firebase import firebase
                firebase = firebase.FirebaseApplication('https://pod-stockone.firebaseio.com/', None)
                firebase_response = firebase.get('/OrderDetails/', None)
            except Exception as e:
                import traceback
                log.debug(traceback.format_exc())
                log.info('Firebase query  failed for %s and params are  and error statement is %s' % (
                    str(user.username), str(e)))

            sister_whs = User.objects.filter(username__in=get_linked_user_objs(user, user))
            append_wh_name = True


        for report in enabled_reports:
            report_misc_data = report.misc_type.replace('report_', '')
            report_name = data_dict[report_misc_data]
            log.info("Report Name::%s" % report_name)
            report = reports_list[report_name]

            mail_report_data = {}
            for each_wh in sister_whs:
                try:
                    wh_report_data = report({}, each_wh, each_wh, serial_view=False, firebase_response=firebase_response)
                except Exception as e:
                    print "Error Occurred"
                    print datetime.datetime.now()
                    import traceback
                    print traceback.format_exc()
                    wh_report_data = {}
                if isinstance(wh_report_data, tuple):
                    wh_report_data = wh_report_data[0]
                if wh_report_data.get('aaData', []):
                    mail_report_data[each_wh.username] = wh_report_data.get('aaData', [])
            report_data = mail_report_data
            if not report_data:
                log.info("No Report Data")
                continue
            self.write_report_excel(report_data, report_name, user, append_wh_name)

        if enabled_reports:
            log.info("Enabled Reports Condition")
            send_to = []
            mailing_list = MiscDetail.objects.filter(misc_type='email', user=user.id)
            if mailing_list and mailing_list[0].misc_value:
                send_to = mailing_list[0].misc_value.split(',')

            if not send_to:
                send_to.append(user.email)

            if send_to:
                subject = '%s Reports dated %s' % (user.username, datetime.datetime.now().date())
                text = 'Please find the scheduled reports in the attachment dated: %s' % str(
                    datetime.datetime.now().date())
                send_mail_attachment(send_to, subject, text, files=self.report_file_names, compressed=True)

    def write_report_excel(self, report_data, report_name, user, append_wh_name=False):
        from rest_api.views.common import folder_check, get_work_sheet, write_excel
        file_type = 'xls'
        headers = report_data.values()[0][0].keys()
        if append_wh_name:
            headers.append('Warehouse')
        file_name = "%s.%s" % (user.id, report_name.replace(' ', '_'))
        wb, ws = get_work_sheet(file_name, headers)
        folder_path = 'static/excel_files/'
        folder_check(folder_path)
        #for i, in report_data.values():
        # report_data.extend(i)
        total_records = 0
        for val in report_data.values():
            total_records += len(val)
        if total_records > 65535:
            file_type = 'csv'
            wb = open(folder_path + file_name + '.' + file_type, 'w')
            ws = ''
            for head in headers:
                ws = ws + str(head).replace(',', '  ') + ','
            ws = ws[:-1] + '\n'
            wb.write(ws)
            ws = ''
        path = folder_path + file_name + '.' + file_type
        counter = 1
        for key, report_value in report_data.items():
            for data in report_value:
                index = 0
                for header_name, value in data.items():#values():
                    if header_name == 'Order ID':
                        value = "'%s" % str(value)
                    ws = write_excel(ws, counter, index, value, file_type)
                    index += 1
                if append_wh_name:
                    ws = write_excel(ws, counter, index, key, file_type)

                counter += 1
                if file_type == 'csv':
                    ws = ws[:-1] + '\n'
                    wb.write(ws)
                    ws = ''

        if file_type == 'xls':
            wb.save(path)
        else:
            wb.close()
        self.report_file_names.append({'name': file_name + '.' + file_type, 'path': path})

if __name__ == "__main__":

    log.info("Started cronjob for report sending\n")
    users = User.objects.filter(username='72Networks')
    for user in users:
        log.info("user : %s"%(str(user.id)))
        OBJ = MailReports()
        OBJ.send_reports_mail(user, mail_now=True)
