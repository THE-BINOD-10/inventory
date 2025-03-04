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
from rest_api.views.common import get_sku_weight, get_all_sellable_zones, get_work_sheet, get_utc_start_date, \
    get_local_date
from rest_api.views.excel_operations import write_excel_col, get_excel_variables
from rest_api.views.miebach_utils import MILKBASKET_USERS, fn_timer, BATCH_DETAIL_HEADERS
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

        def get_adjustment_report(users, start_date, end_date, report_file_names, report_file_name):
            col1 = 1
            col2 = 2
            name = report_file_name
            wb, ws, path, file_name = get_excel_variables(name, report_file_name, [])
            ws.write_merge(0, 0, 1, 5, 'Adjustment Report')
            adjustment_column_dict = {3: 'Positive Adjustment', 4: 'Negative Adjustment', 5: 'Total'}
            for key, value in adjustment_column_dict.iteritems():
                ws, column_count = write_excel_col(ws, key, 0, value, bold=True)
            for user in users:
                positive_quantity = InventoryAdjustment.objects.filter(stock__sku__user=user.id,
                                                                       creation_date__gte=start_date,
                                                                       creation_date__lte=end_date,
                                                                       adjusted_quantity__gt=0) \
                    .annotate(total_price=F('adjusted_quantity') * F('stock__batch_detail__buy_price')) \
                    .annotate(
                    total_price_tax=F('total_price') + (F('total_price') / 100) * F('stock__batch_detail__tax_percent')) \
                    .aggregate(Sum('total_price_tax'))['total_price_tax__sum']

                negative_quantity = InventoryAdjustment.objects.filter(stock__sku__user=user.id,
                                                                       creation_date__gte=start_date,
                                                                       creation_date__lte=end_date,
                                                                       adjusted_quantity__lt=0) \
                    .annotate(total_price=F('adjusted_quantity') * F('stock__batch_detail__buy_price')) \
                    .annotate(
                    total_price_tax=F('total_price') + F('total_price') * F('stock__batch_detail__tax_percent') / 100) \
                    .aggregate(Sum('total_price_tax'))['total_price_tax__sum']

                if not positive_quantity: positive_quantity = 0
                if not negative_quantity:
                    negative_quantity = 0
                else:
                    negative_quantity = negative_quantity
                total = positive_quantity + negative_quantity

                ws.write_merge(1, 1, col1, col2, user.username.upper())
                ws, column_count = write_excel_col(ws, 2, col1, 'Amount', bold=True)
                ws, column_count = write_excel_col(ws, 2, col2, 'Realized', bold=True)
                ws, column_count = write_excel_col(ws, 3, col1, float("%.2f" % positive_quantity))
                ws, column_count = write_excel_col(ws, 4, col1, float("%.2f" % abs(negative_quantity)))
                ws, column_count = write_excel_col(ws, 5, col1, float("%.2f" % total))
                for i in [3, 4, 5]:
                    ws, column_count = write_excel_col(ws, i, col2, 0)
                col1 += 2
                col2 += 2
            wb.save(path)
            report_file_names.append({'name': file_name, 'path': path})
            return report_file_names

        def get_batch_detail_report(users, report_file_names, report_file_name='SKU Inventory Value'):
            batch_detail_headers = copy.deepcopy(BATCH_DETAIL_HEADERS)
            for user in users:
                stock_detail_objs = StockDetail.objects.select_related('sku', 'location', 'location__zone',
                                                                       'pallet_detail',
                                                                       'batch_detail').prefetch_related('sku',
                                                                                                        'location',
                                                                                                        'location__zone'). \
                    exclude(Q(receipt_number=0) | Q(batch_detail__buy_price=0)). \
                    filter(sku__user=user.id, quantity__gt=0).values_list('receipt_number', 'receipt_date',
                                                                          'sku__sku_code', 'sku__sku_desc',
                                                                          'sku__sku_category', 'batch_detail__batch_no',
                                                                          'batch_detail__mrp',
                                                                          'batch_detail__weight',
                                                                          'batch_detail__buy_price',
                                                                          'batch_detail__tax_percent',
                                                                          'batch_detail__manufactured_date',
                                                                          'batch_detail__expiry_date',
                                                                          'location__zone__zone',
                                                                          'location__location', 'quantity',
                                                                          'receipt_type')
                name = '%s_%s' % (user.username, report_file_name)
                wb, ws, path, file_name = get_excel_variables(name, name, batch_detail_headers)
                row_count = 1
                for stock_detail_vals in stock_detail_objs:
                    for col_count, stock_detail_val in enumerate(stock_detail_vals):
                        if col_count in [1]:
                            stock_detail_val = get_local_date(user, stock_detail_val, send_date=True).strftime(
                                "%d %b %Y")
                        elif col_count in [10, 11]:
                            if stock_detail_val:
                                stock_detail_val = stock_detail_val.strftime("%d %b %Y")
                            else:
                                stock_detail_val = ''
                        ws, column_count = write_excel_col(ws, row_count, col_count, stock_detail_val)
                    row_count += 1
                wb.save(path)
                report_file_names.append({'name': file_name, 'path': path})
            return report_file_names

        users = User.objects.filter(username__in=['GGN01', 'NOIDA01', 'NOIDA02', 'HYD01', 'BLR01', 'GGN02', 'NOIDA03', 'BLR02', 'HYD02'])
        # users = User.objects.filter(username__in=['GGN01'])
        category_list = list(SKUMaster.objects.filter(user__in=users, status=1).exclude(sku_category=''). \
                             values_list('sku_category', flat=True).distinct())
        inv_value_dict = OrderedDict()
        doc_value_dict = OrderedDict()
        total_doc_dict = OrderedDict()
        margin_value_dict = OrderedDict()
        margin_percent_dict = OrderedDict()
        inv_value_headers = ['Category']
        today_start = get_utc_start_date(datetime.now())
        today_end = today_start + timedelta(days=1)
        adjustment_dict = OrderedDict()
        user_mapping = dict(users.values_list('id', 'username'))
        inv_value_headers = list(chain(inv_value_headers, user_mapping.values()))
        try:
            report_file_names = []
            # Week Report
            start_date = get_utc_start_date(datetime.now() - timedelta(6))
            end_date = start_date + timedelta(days=7)
            report_file_names = get_adjustment_report(users, start_date, end_date, report_file_names,
                                                      report_file_name='Adjustment Report Weekly')
            # MTD Report
            start_date = get_utc_start_date(datetime.now().replace(day=1))
            end_date = get_utc_start_date(datetime.now() + timedelta(days=1))
            report_file_names = get_adjustment_report(users, start_date, end_date, report_file_names,
                                                      report_file_name='Adjustment Report-MTD')
            report_file_names = get_batch_detail_report(users, report_file_names,
                                                        report_file_name='SKU Inventory Value')
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
                    no_zero_stock_days = list(
                        StockStats.objects.filter(sku__sku_category=category, sku__user=user.id, closing_stock__gt=0). \
                            annotate(creation_date_only=Cast('creation_date', DateField())).values(
                            'creation_date_only').distinct(). \
                            order_by('-creation_date_only').values_list('creation_date_only', flat=True)[
                        :7])

                    all_orders = OrderDetail.objects.filter(user=user.id, sku__sku_category=category,
                                                            customerordersummary__isnull=False,
                                                            sellerorder__seller__seller_id=2)
                    order_detail_objs = all_orders. \
                                            annotate(creation_date_only=Cast('creation_date', DateField())). \
                                            filter(creation_date_only__in=no_zero_stock_days).values(
                        'creation_date_only').distinct(). \
                                            order_by('-creation_date_only'). \
                                            annotate(quantity_sum=Sum('quantity'),
                                                     value_sum=Sum((F('quantity') * F('unit_price'))))[:7]  # +\
                    # ((F('quantity')*F('unit_price')/Value('100'))*(F('customerordersummary__cgst_tax')+\
                    # F('customerordersummary__sgst_tax')+F('customerordersummary__igst_tax')+\
                    #                                               F('customerordersummary__cess_tax'))) ))[:7]
                    total_sale_value = 0
                    if order_detail_objs.exists():
                        for order_detail_obj in order_detail_objs:
                            total_sale_value += order_detail_obj['value_sum']
                    avg_sale_value = total_sale_value / 7
                    doc_value_dict[category][int(user.id)] = avg_sale_value
                    # Doc Value Calculation Ends

                    # Margin Value and Percent Calculation Starts
                    '''drspl_order_ids = list(SellerOrder.objects.filter(order__creation_date__gte=today_start,order__creation_date__lte=today_end,
                                                                order__user=user.id, order__sku__sku_category=category,
                                                                seller__seller_id=2).\
                                                        values_list('order_id', flat=True))
                    pick_locs = PicklistLocation.objects.filter(picklist__order__user=user.id,
                                                                picklist__order__sku__sku_category=category,
                                                                picklist__order__creation_date__gte=today_start,
                                                    picklist__order__creation_date__lte=today_end,
                                                    picklist__order_id__in=drspl_order_ids)#.only('quantity',
                                                    #'stock__batch_detail__buy_price', 'picklist__order__unit_price',
                                                    #'stock__batch_detail__tax_percent', 'picklist__order_id')
                    pick_sale_val = 0
                    pick_cost_val = 0
                    for pick_loc in pick_locs:
                        buy_price = pick_loc.stock.batch_detail.buy_price
                        cost_price_tax = pick_loc.stock.batch_detail.tax_percent
                        cod = CustomerOrderSummary.objects.filter(order_id=pick_loc.picklist.order_id)
                        sale_price_tax = 0
                        if cod:
                            cod = cod[0]
                            if cod.cgst_tax:
                                sale_price_tax = cod.cgst_tax + cod.sgst_tax
                            else:
                                sale_price_tax = cod.igst_tax
                        cost_amt = pick_loc.quantity * buy_price
                        cost_amt_tax = (cost_amt/100)*cost_price_tax
                        pick_cost_val += (cost_amt + cost_amt_tax)
                        pick_sale_val += (pick_loc.quantity * pick_loc.picklist.order.unit_price) #+\
                                            #(((piick_loc.quantity * pick_loc.picklist.order.unit_price)/100)*sale_price_tax)
                    if pick_sale_val:
                        margin_value_dict[category][int(user.id)] = pick_sale_val - pick_cost_val
                        margin_percent_dict[category][int(user.id)] = (pick_sale_val - pick_cost_val)/pick_sale_val'''
                    # Margin Value and Percent Calculation Ends
                inventory_value_objs = StockDetail.objects.filter(sku__user__in=users, sku__sku_category=category,
                                                                  quantity__gt=0). \
                    exclude(Q(receipt_number=0) | Q(location__zone__zone='DAMAGED_ZONE')). \
                    values('sku__sku_category', 'sku__user', 'batch_detail__tax_percent',
                           'quantity', 'batch_detail__buy_price')
                for data in inventory_value_objs:
                    tax_percent = 0
                    if data['batch_detail__tax_percent']:
                        tax_percent = data['batch_detail__tax_percent']
                    buy_price = 0
                    if data['batch_detail__buy_price']:
                        buy_price = data['batch_detail__buy_price']
                    total_value = data['quantity'] * buy_price
                    if tax_percent:
                        total_value += (total_value / 100) * tax_percent
                    inv_value_dict[data['sku__sku_category']][int(data['sku__user'])] += total_value

            name = 'inventory_value_report'
            wb, ws, path, file_name = get_excel_variables(name, 'inventory_value', inv_value_headers)
            row_count = 1
            total_inventory_value = {}
            for category, user_value in inv_value_dict.iteritems():
                if sum(user_value.values()) <= 0:
                    continue
                ws, column_count = write_excel_col(ws, row_count, 0, category)
                for user, value in user_value.iteritems():
                    column_count = (user_mapping.keys().index(user)) + 1
                    value = int(value)
                    ws, column_count = write_excel_col(ws, row_count, column_count, value)
                    total_inventory_value.setdefault(user, 0)
                    total_inventory_value[user] += value
                row_count += 1
            # Adding Totals in Bottom for Inventory Value report
            column_count = 0
            ws, column_count = write_excel_col(ws, row_count, column_count, 'Total')
            for user, value in total_inventory_value.iteritems():
                column_count = (user_mapping.keys().index(user)) + 1
                ws, column_count = write_excel_col(ws, row_count, column_count, value)

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
                    total_doc_dict.setdefault(user, {'total_sales': 0, 'total_inventory': 0})
                    if value:
                        stock_value = inv_value_dict[category][user]
                        total_doc_dict[user]['total_sales'] += value
                        total_doc_dict[user]['total_inventory'] += stock_value
                        log.info("Category %s, User %s, Total Avg Sale %s, Total Inventory %s" % (
                            category, str(user), str(value), str(stock_value)))
                        doc_value = stock_value / value
                    doc_value = float("%.2f" % doc_value)
                    ws, column_count = write_excel_col(ws, row_count, column_count, doc_value)
                row_count += 1
            # Adding Totals in Bottom for Doc Report
            column_count = 0
            ws, column_count = write_excel_col(ws, row_count, column_count, 'Total')
            for user, value in total_doc_dict.iteritems():
                column_count = (user_mapping.keys().index(user)) + 1
                total_doc = 0
                if value['total_sales']:
                    total_doc = value['total_inventory'] / value['total_sales']
                log.info("Total Inventory %s, Total Sale %s for DOC, User %s" % (
                    str(value['total_inventory']), str(value['total_sales']), str(user)))
                ws, column_count = write_excel_col(ws, row_count, column_count, total_doc)

            wb.save(path)
            report_file_names.append({'name': file_name, 'path': path})
            '''name = 'consolidated_margin_percent'
            wb, ws, path, file_name = get_excel_variables(name, 'consolidated_margin_percent', inv_value_headers,
                                                          headers_index=1)
            ws.write_merge(0, 0, 1, 3, 'Consolidated Margin Percentage')
            row_count = 2
            for category, user_value in margin_percent_dict.iteritems():
                ws, column_count = write_excel_col(ws, row_count, 0, category)
                for user, value in user_value.iteritems():
                    column_count = (user_mapping.keys().index(user)) + 1
                    value = float("%.2f" % value) * 100
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
            report_file_names.append({'name': file_name, 'path': path})'''
            #send_to = ['avadhani@mieone.com']
            send_to = ['shushant.yadav@milkbasket.com', 'gaurav.srivastava@milkbasket.com',
                       'anubhav.gupta@milkbasket.com', 'Ashok.kumar@milkbasket.com', 'Balaji.srinivasan@milkbasket.com',
                       'ritesh.shah@milkbasket.com', 'tapasya.tibrewal@milkbasket.com', 'prijil.d@milkbasket.com',
                       'sahil.madan@milkbasket.com', 'anurag@milkbasket.com', 'rajiv.joshi@milkbasket.com',
                       'Category-team@milkbasket.com', 'Procurement-team@milkbasket.com','milind.gupta@milkbasket.com',
                       'saurabh.kumar@milkbasket.com', 'naveen.panwar@milkbasket.com', 'jatin.khurana@milkbasket.com']
            subject = '%s Reports dated %s' % ('Milkbasket', datetime.now().date())
            text = 'Please find the scheduled reports in the attachment dated: %s' % str(
                datetime.now().date())
            send_mail_attachment(send_to, subject, text, files=report_file_names)
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Milkbasket Central report creation failed and error statement is %s' %
                     str(e))
