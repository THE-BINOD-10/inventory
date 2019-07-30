"""
 Code for Stock Reconciliation
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
from miebach_admin.models import *
from rest_api.views.common import get_sku_weight
from rest_api.views.miebach_utils import MILKBASKET_USERS
from django.db.models import Count
from datetime import datetime, date, timedelta

def init_logger(log_file):
    log = logging.getLogger(log_file)
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    return log

log = init_logger('logs/stock_reconciliation_report.log')

class Command(BaseCommand):
    help = "Stock Reconciliation"

    def handle(self, *args, **options):
        self.stdout.write("Started Stock Reconciliation Updating")



        def sku_stats_group(group_val, group_name, sku_stats_dict, sku_detail, mrp, weight, tax, unit_price):
            sku_stats_dict[sku_detail.sku_id][group_val][group_name]['quantity'] += sku_detail.quantity
            qty_price = sku_detail.quantity * unit_price
            amount = qty_price
            tax_rate = 0
            if tax:
                tax_rate = ((amount / 100) * tax)
                amount = amount + tax_rate
            sku_stats_dict[sku_detail.sku_id][group_val][group_name]['unit_price_list'].append(amount)
            sku_stats_dict[sku_detail.sku_id][group_val][group_name]['amount'] += amount
        def stock_reconciliation_for_po_picklist(user, today):
            filterStats = OrderedDict()
            sku_stats_dict = {}
            filterStats['sku__user'] = user.id
            filterStats['creation_date__startswith'] = today.date()
            filterStats['transact_type__in'] = ['PO', 'picklist', 'inventory-upload', 'inventory-adjustment',
                                                'return', 'rtv']
            sku_detail_stats = SKUDetailStats.objects.filter(**filterStats).exclude(stock_detail__isnull=True)
            for sku_detail in sku_detail_stats:
                mrp = 0
                weight = ''
                tax = 0
                unit_price = sku_detail.stock_detail.unit_price
                if sku_detail.stock_detail.batch_detail:
                    batch_obj = sku_detail.stock_detail.batch_detail
                    mrp = batch_obj.mrp
                    weight = batch_obj.weight
                    unit_price = batch_obj.buy_price
                    tax = batch_obj.tax_percent
                order_type = ''
                if sku_detail.transact_type == 'return':
                    order_return = OrderReturns.objects.filter(id=sku_detail.transact_id, order__isnull=False)
                    if order_return.exists():
                        order_return = order_return[0]
                        unit_price = order_return.order.unit_price
                        cod = order_return.order.customerordersummary_set.filter()
                        if cod.exists():
                            cod = cod[0]
                            if cod.cgst_tax:
                                tax += (cod.cgst_tax + cod.sgst_tax)
                            else:
                                tax = cod.igst_tax

                if sku_detail.transact_type == 'picklist':
                    discount = 0
                    picklist_obj = Picklist.objects.filter(id=sku_detail.transact_id)
                    if picklist_obj.exists() and picklist_obj[0].order:
                        picklist_obj = picklist_obj[0]
                        unit_price = picklist_obj.order.unit_price
                        cod = picklist_obj.order.customerordersummary_set.filter()
                        so = picklist_obj.order.sellerorder_set.filter()
                        if so.exists():
                            seller_id = int(so[0].seller.seller_id)
                            if seller_id == 2:
                                order_type = 'customer_sales'
                            elif seller_id == 1 and picklist_obj.order.marketplace == 'STOCK TRANSFER':
                                order_type = 'stock_transfer'
                            else:
                                order_type = 'internal_sales'
                        if cod.exists():
                            cod = cod[0]
                            if cod.cgst_tax:
                                tax += (cod.cgst_tax + cod.sgst_tax)
                            else:
                                tax = cod.igst_tax
                            if order_type == 'internal_sales':
                                discount = cod.discount
                    else:
                        unit_price = 0
                group_val = (sku_detail.sku_id, mrp, weight)
                sku_stats_dict.setdefault(sku_detail.sku_id, {})
                sku_stats_dict[sku_detail.sku_id].setdefault(group_val,
                                          {'PO': {'quantity': 0, 'unit_price_list': [], 'amount': 0},
                                           'customer_sales': {'quantity': 0, 'unit_price_list': [], 'amount': 0},
                                           'internal_sales': {'quantity': 0, 'unit_price_list': [], 'amount': 0},
                                           'stock_transfer': {'quantity': 0, 'unit_price_list': [], 'amount': 0},
                                           'inventory-adjustment': {'quantity': 0, 'unit_price_list': [], 'amount': 0},
                                           'rtv': {'quantity': 0, 'unit_price_list': [], 'amount': 0},
                                           'return': {'quantity': 0, 'unit_price_list': [], 'amount': 0},
                                           })
                if sku_detail.transact_type in ['PO', 'inventory-upload']:
                    sku_stats_group(group_val, 'PO', sku_stats_dict, sku_detail, mrp, weight, tax, unit_price)
                elif sku_detail.transact_type == 'inventory-adjustment':
                    sku_stats_group(group_val, 'inventory-adjustment', sku_stats_dict, sku_detail, mrp, weight, tax, unit_price)
                elif sku_detail.transact_type == 'rtv':
                    sku_stats_group(group_val, 'rtv', sku_stats_dict, sku_detail, mrp, weight, tax, unit_price)
                elif sku_detail.transact_type == 'return':
                    sku_stats_group(group_val, 'return', sku_stats_dict, sku_detail, mrp, weight, tax, unit_price)
                elif sku_detail.transact_type == 'picklist' and order_type:
                    sku_stats_dict[sku_detail.sku_id][group_val][order_type]['quantity'] += sku_detail.quantity
                    qty_price = (sku_detail.quantity * unit_price) - discount
                    amount = qty_price
                    tax_rate = 0
                    if tax:
                        tax_rate = ((amount/100)* tax)
                        amount = amount + tax_rate
                    sku_stats_dict[sku_detail.sku_id][group_val][order_type]['unit_price_list'].append(amount)
                    sku_stats_dict[sku_detail.sku_id][group_val][order_type]['amount'] += amount
            return sku_stats_dict

        def get_sku_stock_total(user):
            search_params = {}
            sku_stock_dict = {}
            search_params['sku__user'] = user.id
            search_params['quantity__gt'] = 0
            stock_data = StockDetail.objects.exclude(Q(receipt_number=0) | Q(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE'])).filter(**search_params)
            for stock in stock_data:
                mrp = 0
                weight = ''
                unit_price = stock.unit_price
                tax = 0
                if stock.batch_detail:
                    batch_detail = stock.batch_detail
                    mrp = batch_detail.mrp
                    weight = batch_detail.weight
                    unit_price = batch_detail.buy_price
                    tax = batch_detail.tax_percent
                group_val = (stock.sku_id, mrp, weight)
                sku_stock_dict.setdefault(stock.sku_id, {})
                sku_stock_dict[stock.sku_id].setdefault(group_val, {'quantity': 0, 'unit_price_list': [], 'amount': 0})
                sku_stock_dict[stock.sku_id][group_val]['quantity'] += stock.quantity
                qty_price = stock.quantity * unit_price
                amount = qty_price
                if tax:
                    amount = amount + ((amount/100) * tax)
                sku_stock_dict[stock.sku_id][group_val]['unit_price_list'].append(qty_price)
                sku_stock_dict[stock.sku_id][group_val]['amount'] += amount
            return sku_stock_dict

        def get_opening_stock_dict(user, today, sku_stats_dict, sku_stock_dict):
            opening_stock_dict = {}
            query_opening_stock = {'sku__user': user.id}
            yesterday = (today - timedelta(days=1)).date()
            query_opening_stock['creation_date__startswith'] = yesterday
            stock_rec_objs = StockReconciliation.objects.filter(**query_opening_stock)
            if stock_rec_objs:
                for stock_rec_obj in stock_rec_objs:
                    opening_stock_dict.setdefault(stock_rec_obj.sku_id, {})
                    group_val = (stock_rec_obj.sku_id, stock_rec_obj.mrp, stock_rec_obj.weight)
                    if group_val not in opening_stock_dict:
                        opening_stock_dict[stock_rec_obj.sku_id].setdefault(group_val, {})
                        opening_stock_dict[stock_rec_obj.sku_id][group_val] =  {'quantity': stock_rec_obj.closing_quantity,
                                                          'avg_rate': stock_rec_obj.closing_avg_rate,
                                                          'amount': stock_rec_obj.closing_amount}
            else:
                opening_stock_dict = {}
                for sku_id, sku_stocks_data in sku_stock_dict.iteritems():
                    opening_stock_dict.setdefault(sku_id, {})
                    for key, sku_stocks in sku_stocks_data.iteritems():
                        opening_stock_dict[sku_id].setdefault(key, {'quantity': 0, 'avg_rate': 0, 'amount': 0,
                                                                    'qty_price_sum': 0})
                        opening_stock_dict[sku_id][key]['quantity'] = sku_stocks.get('quantity', 0)
                        opening_stock_dict[sku_id][key]['amount'] = sku_stocks.get('amount', 0)
                        stock_unit_price_list = sku_stocks.get('unit_price_list', [])
                        if stock_unit_price_list and sku_stocks.get('quantity', 0):
                            opening_stock_dict[sku_id][key]['avg_rate'] = sum(stock_unit_price_list)/sku_stocks['quantity']
                            opening_stock_dict[sku_id][key]['qty_price_sum'] += sum(stock_unit_price_list)
                for sku_id, sku_stats in sku_stats_dict.iteritems():
                    opening_stock_dict.setdefault(sku_id, {})
                    for key, sku_stat in sku_stats.iteritems():
                        opening_stock_dict[sku_id].setdefault(key, {'quantity': 0, 'avg_rate': 0, 'amount': 0})
                        for stat_name, stat_value in sku_stat.iteritems():
                            if stat_name in ['customer_sales', 'internal_sales', 'rtv', 'stock_transfer']:
                                opening_stock_dict[sku_id][key]['quantity'] += stat_value['quantity']
                                opening_stock_dict[sku_id][key]['amount'] += stat_value['amount']
                                stat_unit_price_list = stat_value.get('unit_price_list', [])
                                if stat_unit_price_list and stat_value['quantity']:
                                    opening_stock_dict[sku_id][key]['qty_price_sum'] += sum(stat_unit_price_list)
                            elif stat_name in ['PO', 'return', 'inventory-adjustment']:
                                opening_stock_dict[sku_id][key]['quantity'] -= stat_value['quantity']
                                opening_stock_dict[sku_id][key]['amount'] -= stat_value['amount']
                                stat_unit_price_list = stat_value.get('unit_price_list', [])
                                if stat_unit_price_list and stat_value['quantity']:
                                    opening_stock_dict[sku_id][key]['qty_price_sum'] -= sum(stat_unit_price_list)
                            else:
                                print stat_name
            return opening_stock_dict

        def stock_reconciliation_group(prefix, data_dict, stock_reconciliation_dict):
            stock_reconciliation_dict[key]['%s_quantity' % prefix] = data_dict['quantity']
            avg_rate = 0
            if data_dict['unit_price_list'] and data_dict['quantity']:
                avg_rate = sum(data_dict['unit_price_list']) / data_dict['quantity']
            stock_reconciliation_dict[key][ '%s_avg_rate' % prefix] = avg_rate
            stock_reconciliation_dict[key]['%s_amount' % prefix] = data_dict['amount']
        users = User.objects.filter(username__in=MILKBASKET_USERS)
        #users = User.objects.filter(username='NOIDA02')
        today = datetime.now()
        for user in users:
            try:
                log.info("Stock Reconciliation Report Creation Started for user %s" % (user.username))
                sku_stats_dict = stock_reconciliation_for_po_picklist(user, today)
                sku_stock_dict = get_sku_stock_total(user)
                opening_stock_dict = get_opening_stock_dict(user, today, sku_stats_dict, sku_stock_dict)
                skus = SKUMaster.objects.filter(user=user.id).only('id', 'sku_code')
                for sku in skus:
                    sku_stats = sku_stats_dict.get(sku.id, {})
                    sku_stocks = sku_stock_dict.get(sku.id, {})
                    sku_openings = opening_stock_dict.get(sku.id, {})
                    stock_reconciliation_dict = {}
                    for key, value in sku_stats.iteritems():
                        sku_id, mrp, weight = key
                        po_details = value['PO']
                        customer_sales_details = value['customer_sales']
                        internal_sales_details = value['internal_sales']
                        stock_transfer_details = value['stock_transfer']
                        adj_details = value['inventory-adjustment']
                        rtv_details = value['rtv']
                        return_details = value['return']
                        stock_reconciliation_dict.setdefault(key, {'sku_id': sku_id, 'mrp': mrp, 'weight': weight})
                        if po_details:
                            stock_reconciliation_group('purchase', po_details, stock_reconciliation_dict)
                        if customer_sales_details:
                            stock_reconciliation_group('customer_sales', customer_sales_details, stock_reconciliation_dict)
                        if internal_sales_details:
                            stock_reconciliation_group('internal_sales', internal_sales_details, stock_reconciliation_dict)
                        if stock_transfer_details:
                            stock_reconciliation_group('stock_transfer', stock_transfer_details, stock_reconciliation_dict)
                        if adj_details:
                            stock_reconciliation_group('adjustment', adj_details, stock_reconciliation_dict)
                        if rtv_details:
                            stock_reconciliation_group('rtv', rtv_details, stock_reconciliation_dict)
                        if return_details:
                            stock_reconciliation_group('returns', return_details, stock_reconciliation_dict)
                    for key, value in sku_stocks.iteritems():
                        sku_id, mrp, weight = key
                        stock_reconciliation_dict.setdefault(key, {'sku_id': sku_id, 'mrp': mrp, 'weight': weight})
                        stock_reconciliation_dict[key]['closing_quantity'] = value['quantity']
                        avg_rate = 0
                        if value['unit_price_list'] and value['quantity']:
                            avg_rate = sum(value['unit_price_list'])/value['quantity']
                        stock_reconciliation_dict[key]['closing_avg_rate'] = avg_rate
                        stock_reconciliation_dict[key]['closing_amount'] = value['amount']
                    for key, value in sku_openings.iteritems():
                        sku_id, mrp, weight = key
                        stock_reconciliation_dict.setdefault(key, {'sku_id': sku_id, 'mrp': mrp, 'weight': weight})
                        stock_reconciliation_dict[key]['opening_quantity'] = value['quantity']
                        if stock_reconciliation_dict[key].get('qty_price_sum', 0):
                            stock_reconciliation_dict[key]['opening_avg_rate'] = value['qty_price_sum']/value['quantity']
                        else:
                            stock_reconciliation_dict[key]['opening_avg_rate'] = value['avg_rate']
                        stock_reconciliation_dict[key]['opening_amount'] = abs(value['amount'])

                    for key, stock_reconciliation_data in stock_reconciliation_dict.iteritems():
                        stock_rec_obj = StockReconciliation.objects.update_or_create(sku_id=stock_reconciliation_data['sku_id'],
                                                          mrp=stock_reconciliation_data['mrp'],
                                                          weight=stock_reconciliation_data['weight'],
                                                          creation_date__startswith=today.date(),
                                                                           defaults=stock_reconciliation_data)
                    if not stock_reconciliation_dict:
                        weight = get_sku_weight(sku)
                        stock_rec_obj = StockReconciliation.objects.update_or_create(sku_id=sku.id,
                                                          mrp=sku.mrp,
                                                          weight=weight,
                                                          creation_date__startswith=today.date(),
                                                                           defaults={})
                log.info("Stock Reconciliation Report Creation Ended for user %s" % (user.username))
            except Exception as e:
                import traceback
                log.debug(traceback.format_exc())
                log.info('Stock Reconciliation report creation failed for user %s' % (str(user.username)))
