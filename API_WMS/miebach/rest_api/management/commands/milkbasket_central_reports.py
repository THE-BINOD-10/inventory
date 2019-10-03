"""
 Code for Milkbasket BA and SA Mail
"""
from collections import OrderedDict
from django.core.management import BaseCommand
from django.db.models import Q, Sum, F
import os
import logging
import copy
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from itertools import chain
from django.db.models import Count
from django.db.models.functions import Cast, Concat
from django.db.models.fields import DateField, CharField
from django.db.models import Value
from datetime import datetime, date, timedelta
from miebach_admin.models import *
from rest_api.views.common import get_sku_weight, get_all_sellable_zones, get_work_sheet, get_utc_start_date
from rest_api.views.miebach_utils import MILKBASKET_USERS, fn_timer
from rest_api.views.mail_server import send_mail_attachment

def init_logger(log_file):
    log = logging.getLogger(log_file)
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    return log

log = init_logger('logs/milkbasket_central_report_mail.log')

ba_location = 'BA'

class Command(BaseCommand):
    help = "Milkbasket Central Reports Mail"

    def handle(self, *args, **options):
        self.stdout.write("Milkbasket Central Reports Script")

        def write_excel_col(ws, row_count, column_count, value):
            ws.write(row_count, column_count, value)
            column_count += 1
            return ws, column_count

        def get_excel_variables(file_name, sheet_name, headers, headers_index=0):
            wb, ws = get_work_sheet(sheet_name, headers, headers_index=headers_index)
            file_name = '%s.%s' % (file_name, 'xls')
            path = ('static/excel_files/%s') % file_name
            if not os.path.exists('static/excel_files/'):
                os.makedirs('static/excel_files/')
            return wb, ws, path, file_name

        users = User.objects.filter(username__in=MILKBASKET_USERS)
        category_list = list(SKUMaster.objects.filter(user__in=users, status=1).exclude(sku_category='').\
                             values_list('sku_category', flat=True).distinct())
        inv_value_dict = OrderedDict()
        doc_value_dict = OrderedDict()
        margin_value_dict = OrderedDict()
        margin_percent_dict = OrderedDict()
        inv_value_headers = ['Category']
        user_mapping = dict(users.values_list('id', 'username'))
        inv_value_headers = list(chain(inv_value_headers, user_mapping.values()))
        try:
            report_file_names = []
            for category in category_list:
                log.info("Calculation started for Category %s" % category)
                for user in users:
                    inv_value_dict.setdefault(category, {})
                    inv_value_dict[category].setdefault(int(user.id), 0)
                    doc_value_dict.setdefault(category, {})
                    doc_value_dict[category].setdefault(int(user.id), 0)
                    margin_value_dict.setdefault(category, {})
                    margin_value_dict[category].setdefault(int(user.id), 0)
                    margin_percent_dict.setdefault(category, {})
                    margin_percent_dict[category].setdefault(int(user.id), 0)
                    # Doc Value Calculation Starts
                    no_stock_days = list(StockStats.objects.filter(sku__sku_category=category, sku__user=user.id, closing_stock=0). \
                                         annotate(creation_date_only=Cast('creation_date', DateField())).values(
                        'creation_date_only').distinct(). \
                                         order_by('-creation_date_only').values_list('creation_date_only', flat=True)[
                                         :7])
                    all_orders = OrderDetail.objects.filter(user=user.id, sku__sku_category=category,
                                                                   customerordersummary__isnull=False)
                    order_detail_objs = all_orders. \
                                            annotate(creation_date_only=Cast('creation_date', DateField())). \
                                            exclude(creation_date_only__in=no_stock_days).values(
                        'creation_date_only').distinct(). \
                                            order_by('-creation_date_only').\
                        annotate(quantity_sum=Sum('quantity'),value_sum=Sum((F('quantity') * F('unit_price')) +\
                                    ((F('quantity')*F('unit_price')/Value('100'))*(F('customerordersummary__cgst_tax')+\
                                     F('customerordersummary__sgst_tax')+F('customerordersummary__igst_tax')+\
                                                                                   F('customerordersummary__cess_tax'))) ))[:7]
                    total_sale_value = 0
                    if order_detail_objs.exists():
                        for order_detail_obj in order_detail_objs:
                            total_sale_value += order_detail_obj['value_sum']
                    avg_sale_value = total_sale_value/7
                    doc_value_dict[category][int(user.id)] = avg_sale_value
                    # Doc Value Calculation Ends

                    # Margin Value and Percent Calculation Starts
                    today_start = get_utc_start_date(datetime.now(), user)
                    today_end = today_start + timedelta(days=1)
                    pick_locs = PicklistLocation.objects.filter(picklist__order__user=user.id,
                                                                picklist__order__sku__sku_category=category,
                                                                creation_date__gte=today_start,
                                                    creation_date__lte=today_end).only('quantity',
                                                    'stock__batch_detail__buy_price', 'picklist__order__unit_price')
                    pick_sale_val = 0
                    pick_cost_val = 0
                    for pick_loc in pick_locs:
                        buy_price = pick_loc.stock.batch_detail.buy_price
                        pick_cost_val += (pick_loc.quantity * buy_price)
                        pick_sale_val += (pick_loc.quantity * pick_loc.picklist.order.unit_price)
                    if pick_sale_val:
                        margin_value_dict[category][int(user.id)] = pick_sale_val - pick_cost_val
                        margin_percent_dict[category][int(user.id)] = (pick_sale_val - pick_cost_val)/pick_sale_val
                    # Margin Value and Percent Calculation Ends
                master_data = SellerStock.objects.filter(stock__sku__user__in=users, stock__sku__sku_category=category,
                                                         stock__batch_detail__isnull=False, quantity__gt=0). \
                    exclude(Q(stock__receipt_number=0)). \
                    values('stock__sku__sku_category', 'stock__sku__user', 'stock__batch_detail__tax_percent').distinct(). \
                    annotate(total_value=Sum(F('quantity') * F('stock__batch_detail__buy_price')))
                for data in master_data:
                    tax_percent = 0
                    if data['stock__batch_detail__tax_percent']:
                        tax_percent = data['stock__batch_detail__tax_percent']
                    total_value = data['total_value']
                    if tax_percent:
                        total_value += (total_value/100)*tax_percent
                    inv_value_dict[data['stock__sku__sku_category']][int(data['stock__sku__user'])] += total_value
            name = 'inventory_value_report'
            wb, ws, path, file_name = get_excel_variables(name, 'inventory_value', inv_value_headers)
            row_count = 1
            for category, user_value in inv_value_dict.iteritems():
                ws, column_count = write_excel_col(ws, row_count, 0, category)
                for user, value in user_value.iteritems():
                    column_count = (user_mapping.keys().index(user)) + 1
                    value = float("%.2f" % value)
                    ws, column_count = write_excel_col(ws, row_count, column_count, value)
                row_count += 1
            wb.save(path)
            report_file_names.append({'name': file_name, 'path': path})
            name = 'days_of_cover_report'
            wb, ws, path, file_name = get_excel_variables(name, 'Days of Cover', inv_value_headers)
            row_count = 1
            for category, user_value in doc_value_dict.iteritems():
                ws, column_count = write_excel_col(ws, row_count, 0, category)
                for user, value in user_value.iteritems():
                    column_count = (user_mapping.keys().index(user)) + 1
                    doc_value = 0
                    if value:
                        stock_value = inv_value_dict[category][user]
                        doc_value = stock_value/value
                    doc_value = float("%.2f" % doc_value)
                    ws, column_count = write_excel_col(ws, row_count, column_count, doc_value)
                row_count += 1
            wb.save(path)
            report_file_names.append({'name': file_name, 'path': path})
            name = 'consolidated_margin_percent'
            wb, ws, path, file_name = get_excel_variables(name, 'consolidated_margin_percent', inv_value_headers,
                                                          headers_index=1)
            ws.write_merge(0, 0, 1, 3, 'Consolidated Margin Percentage')
            row_count = 2
            for category, user_value in margin_percent_dict.iteritems():
                ws, column_count = write_excel_col(ws, row_count, 0, category)
                for user, value in user_value.iteritems():
                    column_count = (user_mapping.keys().index(user)) + 1
                    value = float("%.2f" % value)
                    ws, column_count = write_excel_col(ws, row_count, column_count, value)
                row_count += 1
            row_count += 1
            ws.write_merge(row_count,row_count,1,3, 'Consolidated Margin Value')
            row_count += 1
            for category, user_value in margin_value_dict.iteritems():
                ws, column_count = write_excel_col(ws, row_count, 0, category)
                for user, value in user_value.iteritems():
                    column_count = (user_mapping.keys().index(user)) + 1
                    value = float("%.2f" % value)
                    ws, column_count = write_excel_col(ws, row_count, column_count, value)
                row_count += 1
            wb.save(path)
            report_file_names.append({'name': file_name, 'path': path})
            send_to = ['sreekanth@mieone.com', 'shishir.sharma@milkbasket.com']
            subject = '%s Reports dated %s' % ('Milkbasket', datetime.now().date())
            text = 'Please find the scheduled reports in the attachment dated: %s' % str(
                datetime.now().date())
            send_mail_attachment(send_to, subject, text, files=report_file_names)
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Milkbasket Central report creation failed for user %s and error statement is %s' %
                     (str(user), str(e)))
