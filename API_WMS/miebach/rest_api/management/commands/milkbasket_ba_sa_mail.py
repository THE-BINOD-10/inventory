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
from datetime import datetime, date, timedelta
from miebach_admin.models import *
from rest_api.views.common import get_sku_weight, get_all_sellable_zones, get_work_sheet
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

log = init_logger('logs/milkbasket_ba_sa_mail.log')

ba_location = 'BA'

class Command(BaseCommand):
    help = "Milkbasket BA SA Mail"

    def handle(self, *args, **options):
        self.stdout.write("Started Milkbasket BA SA Mail Updating")


        def write_excel_col(ws, row_count, column_count, value):
            ws.write(row_count, column_count, value)
            column_count += 1
            return ws, column_count

        @fn_timer
        def get_sku_stock_total(stock_data, user, sku_weights):
            sku_stock_dict = {}
            for stock in stock_data:
                sku_weight = sku_weights.get(stock.sku_id, '')
                batch_detail = stock.batch_detail
                mrp = batch_detail.mrp
                weight = batch_detail.weight
                if weight != sku_weight:
                    continue
                group_val = (stock.sku_id, mrp, weight)
                sku_stock_dict.setdefault(stock.sku_id, {})
                sku_stock_dict[stock.sku_id].setdefault(group_val, {'quantity': 0})
                sku_stock_dict[stock.sku_id][group_val]['quantity'] += stock.quantity
            return sku_stock_dict

        users = User.objects.filter(username__in=MILKBASKET_USERS)
        #users = User.objects.filter(username__in=['NOIDA02'])
        today = datetime.now()
        headers = ['SKU Code', 'SKU Desc', 'SKU Category', 'Sub Category', 'Combo Flag', 'MRP', 'Weight',
                   'SA Quantity', 'BA Quantity']
        for user in users:
            try:
                zones = get_all_sellable_zones(user)
                sku_weights = dict(SKUAttributes.objects.filter(sku__user=user.id, attribute_name='weight').\
                    values_list('sku_id', 'attribute_value'))
                sellable_locations = list(LocationMaster.objects.filter(zone__zone__in=zones, zone__user=user.id).\
                                                        values_list('location', flat=True))
                locations = copy.deepcopy(sellable_locations)
                locations.append(ba_location)
                stock_sku_ids = list(StockDetail.objects.exclude(receipt_number=0).\
                                                filter(sku__user=user.id, quantity__gt=0,
                                                       location__location__in=sellable_locations,
                                                       batch_detail__isnull=False,
                                                       batch_detail__mrp=F('sku__mrp'),
                                                       batch_detail__weight__in=sku_weights.values()).\
                                                values_list('sku_id', flat=True))
                skus = SKUMaster.objects.filter(user=user.id).exclude(id__in=stock_sku_ids).\
                                            only('id', 'sku_code', 'sku_desc', 'sku_category',
                                                                   'sub_category', 'relation_type')
                stock_data = StockDetail.objects.exclude(receipt_number=0).\
                                                filter(sku__user=user.id, quantity__gt=0,
                                                       location__location=ba_location,
                                                       batch_detail__isnull=False).\
                                                only('sku_id', 'batch_detail__mrp', 'batch_detail__weight',
                                                     'quantity')
                sku_ba_stock_dict = get_sku_stock_total(stock_data, user, sku_weights)
                wb, ws = get_work_sheet('ba_sa_report', headers)
                row_count = 0
                file_name = '%s.%s.%s' % (str(user.id), 'ba_sa_mail_report', 'xls')
                path = ('static/excel_files/%s') % file_name
                if not os.path.exists('static/excel_files/'):
                    os.makedirs('static/excel_files/')
                for sku in skus:
                    ba_mrp_list = []
                    sku_ba_dict = sku_ba_stock_dict.get(sku.id, {})
                    if sku_ba_dict:
                        for sku_ba, qty in sku_ba_dict.iteritems():
                            row_count += 1
                            sa_quantity = 0
                            sku_id, mrp, weight = sku_ba
                            ba_mrp_list = [mrp]
                            ba_quantity = qty.get('quantity', 0)
                            column_count = 0
                            ws, column_count = write_excel_col(ws, row_count, column_count, sku.sku_code)
                            ws, column_count = write_excel_col(ws, row_count, column_count, sku.sku_desc)
                            ws, column_count = write_excel_col(ws, row_count, column_count, sku.sku_category)
                            ws, column_count = write_excel_col(ws, row_count, column_count, sku.sub_category)
                            combo_flag = 'No'
                            if sku.relation_type == 'combo':
                                combo_flag = 'Yes'
                            ws, column_count = write_excel_col(ws, row_count, column_count, combo_flag)
                            ws, column_count = write_excel_col(ws, row_count, column_count, mrp)
                            ws, column_count = write_excel_col(ws, row_count, column_count, weight)
                            ws, column_count = write_excel_col(ws, row_count, column_count, sa_quantity)
                            ws, column_count = write_excel_col(ws, row_count, column_count, ba_quantity)
                    if sku.mrp not in ba_mrp_list:
                        row_count += 1
                        sa_quantity = 0
                        mrp = sku.mrp
                        weight = sku_weights.get(sku.id, '')
                        sku_sa = (sku.id, mrp, weight)
                        ba_quantity = sku_ba_dict.get(sku_sa, {}).get('quantity', 0)
                        column_count = 0
                        ws, column_count = write_excel_col(ws, row_count, column_count, sku.sku_code)
                        ws, column_count = write_excel_col(ws, row_count, column_count, sku.sku_desc)
                        ws, column_count = write_excel_col(ws, row_count, column_count, sku.sku_category)
                        ws, column_count = write_excel_col(ws, row_count, column_count, sku.sub_category)
                        combo_flag = 'No'
                        if sku.relation_type == 'combo':
                            combo_flag = 'Yes'
                        ws, column_count = write_excel_col(ws, row_count, column_count, combo_flag)
                        ws, column_count = write_excel_col(ws, row_count, column_count, mrp)
                        ws, column_count = write_excel_col(ws, row_count, column_count, weight)
                        ws, column_count = write_excel_col(ws, row_count, column_count, sa_quantity)
                        ws, column_count = write_excel_col(ws, row_count, column_count, ba_quantity)
                wb.save(path)
                internal_mail = MiscDetail.objects.filter(user=user.id, misc_type='Internal Emails')
                misc_internal_mail = MiscDetail.objects.filter(user=user.id, misc_type='internal_mail', misc_value='true')
                receivers = []
                if misc_internal_mail and internal_mail:
                    internal_mail = internal_mail[0].misc_value.split(",")
                    receivers.extend(internal_mail)
                if receivers:
                    email_subject = '%s %s' % (user.username, 'BA SA Report')
                    email_body = 'Please find the BA SA Report for %s in the attachment' % user.username
                    attachments = [{'path': path, 'name': file_name}]
                    send_mail_attachment(receivers, email_subject, email_body, files=attachments)
            except Exception as e:
                import traceback
                log.debug(traceback.format_exc())
                log.info('Milkbasket BA SA report creation failed for user %s and error statement is %s' %
                         (str(user.username), str(e)))
