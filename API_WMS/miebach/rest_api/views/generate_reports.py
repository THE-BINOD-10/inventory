import datetime
import xlwt
import create_environment
from  mail_server import send_mail_attachment
from miebach_utils import *
from miebach_admin.models import *

reports_list = {'SKU List': get_sku_filter_data, 'Location Wise Stock': get_location_stock_data,
                'Receipt Summary': get_receipt_filter_data, 'Dispatch Summary': get_dispatch_data,
                'SKU Wise': sku_wise_purchase_data}

data_dict = {'sku_list': 'SKU List', 'location_wise_stock': 'Location Wise Stock', 'receipt_note': 'Receipt Summary', 'dispatch_summary': 'Dispatch Summary', 'sku_wise':'SKU Wise'}


class MailReports:
    def __init__(self):
        self.report_file_names = []

    def send_reports_mail(self, user, mail_now=False):
        report_frequency = MiscDetail.objects.filter(misc_type__contains='report_frequency', user=user.id)
        if not report_frequency and not mail_now:
            return

        if report_frequency:
            frequency_value = int(report_frequency[0].misc_value)
            report_date = report_frequency[0].creation_date
            date_difference = (datetime.datetime.now().date() - report_date.date()).days
            if (frequency_value in (0, 1) or (date_difference % frequency_value) != 0) and not mail_now:
                return

        enabled_reports = MiscDetail.objects.filter(misc_type__contains='report', misc_value='true', user=user.id)

        for report in enabled_reports:
            report_data = report.misc_type.replace('report_', '')
            report_name = data_dict[report_data]
            report = reports_list[report_name]

            wb = xlwt.Workbook()
            ws = wb.add_sheet(report_name)

            report_data = report({}, user)
            if isinstance(report_data, tuple):
                report_data = report_data[0]
            report_data = report_data.get('aaData')
            if not report_data:
                continue

            headers = report_data[0].keys()
            for index, header in enumerate(headers):
                ws.write(0, index, header)

            counter = 1
            for data in report_data:
                index = 0
                for value in data.values():
                    ws.write(counter, index, value)
                    index += 1

                counter += 1

            report_file = '%s.%s.xls' % (user.id, report_name.replace(' ', '_'))
            self.report_file_names.append(report_file)

            wb.save(report_file)

        if enabled_reports:

            send_to = []
            mailing_list = MiscDetail.objects.filter(misc_type='email', user=user.id)
            if mailing_list and mailing_list[0].misc_value:
                send_to = mailing_list[0].misc_value.split(',')

            if not send_to:
                send_to.append(user.email)

            if send_to:
                subject = '%s Reports dated %s' % (user.username, datetime.datetime.now().date())
                text = 'Please find the scheduled reports in the attachment dated: %s' % str(datetime.datetime.now().date())
                send_mail_attachment(send_to, subject, text, files=self.report_file_names)


if __name__ == "__main__":

    users = User.objects.all()
    for user in users:
        OBJ = MailReports()
        OBJ.send_reports_mail(user)
