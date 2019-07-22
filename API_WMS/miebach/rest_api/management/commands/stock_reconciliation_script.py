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
from rest_api.views.common import get_exclude_zones, get_misc_value, get_picklist_number, \
    get_sku_stock, get_stock_count, save_sku_stats, change_seller_stock, check_picklist_number_created, \
    update_stocks_data, get_max_seller_transfer_id
from rest_api.views.outbound import get_seller_pick_id
from rest_api.views.miebach_utils import MILKBASKET_USERS, PICKLIST_FIELDS, ST_ORDER_FIELDS
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

management_stock_reconciliation_log = init_logger('logs/stock_reconciliation_report.log')

class Command(BaseCommand):
    help = "Stock Reconciliation"

    def handle(self, *args, **options):
        self.stdout.write("Started Stock Reconciliation Updating")

        def stock_reconciliation_for_po_picklist(user, today):
            filterStats = OrderedDict()
            sku_stats_dict = {}
            filterStats['sku__user'] = user.id
            filterStats['creation_date__startswith'] = today.date()
            filterStats['transact_type__in'] = ['PO', 'picklist']
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
                if sku_detail.transact_type == 'picklist':
                    picklist_obj = Picklist.objects.filter(id=sku_detail.transact_id)
                    if picklist_obj.exists() and picklist_obj[0].order:
                        picklist_obj = picklist_obj[0]
                        unit_price = picklist_obj.order.unit_price
                        cod = picklist_obj.order.customerordersummary_set.filter()
                        if cod.exists():
                            cod = cod[0]
                            if cod.cgst_tax:
                                tax += (cod.cgst_tax + cod.sgst_tax)
                            else:
                                tax = cod.igst_tax
                    else:
                        unit_price = 0
                group_val = (sku_detail.sku_id, mrp, weight)
                sku_stats_dict.setdefault(sku_detail.sku_id, {})
                sku_stats_dict[sku_detail.sku_id].setdefault(group_val,
                                          {'PO': {'quantity': 0, 'unit_price_list': [], 'amount': 0},
                                           'picklist': {'quantity': 0, 'unit_price_list': [], 'amount': 0}})
                if sku_detail.transact_type == 'PO':
                    sku_stats_dict[sku_detail.sku_id][group_val]['PO']['quantity'] += sku_detail.quantity
                    amount = sku_detail.quantity * unit_price
                    tax_rate = 0
                    if tax:
                        tax_rate = ((amount/100)* tax)
                        amount = amount + tax_rate
                    sku_stats_dict[sku_detail.sku_id][group_val]['PO']['unit_price_list'].append(unit_price)
                    sku_stats_dict[sku_detail.sku_id][group_val]['PO']['amount'] += amount
                if sku_detail.transact_type == 'picklist':
                    sku_stats_dict[sku_detail.sku_id][group_val]['picklist']['quantity'] += sku_detail.quantity
                    amount = sku_detail.quantity * unit_price
                    tax_rate = 0
                    if tax:
                        tax_rate = ((amount/100)* tax)
                        amount = amount + tax_rate
                    sku_stats_dict[sku_detail.sku_id][group_val]['picklist']['unit_price_list'].append(unit_price)
                    sku_stats_dict[sku_detail.sku_id][group_val]['picklist']['amount'] += amount
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
                amount = stock.quantity * unit_price
                if tax:
                    amount = amount + ((amount/100) * tax)
                sku_stock_dict[stock.sku_id][group_val]['unit_price_list'].append(unit_price)
                sku_stock_dict[stock.sku_id][group_val]['amount'] += amount
            return sku_stock_dict

        def get_opening_stock_dict(user, today):
            opening_stock_dict = {}
            query_opening_stock = {'sku__user': user.id}
            yesterday = (today - timedelta(days=1)).date()
            query_opening_stock['creation_date__startswith'] = yesterday
            stock_rec_objs = StockReconciliation.objects.filter(**query_opening_stock)
            if stock_rec_objs:
                for stock_rec_obj in stock_rec_objs:
                    group_val = (stock_rec_obj.sku_id, stock_rec_obj.mrp, stock_rec_obj.weight)
                    if group_val not in opening_stock_dict:
                        opening_stock_dict[stock_rec_obj.sku_id][group_val] =  {'quantity': stock_rec_obj.closing_quantity,
                                                          'average_rate': stock_rec_obj.closing_avg_rate,
                                                          'amount': stock_rec_obj.closing_amount}
            # else:
            #     sku_detail_stats = SKUDetailStats.objects.filter(sku__user=user.id, creation_date__startswith=yesterday).\
            #                                                 exclude(stock_detail__isnull=True)
            return opening_stock_dict
        #users = User.objects.filter(username__in=MILKBASKET_USERS)
        users = User.objects.filter(username='NOIDA02')
        management_stock_reconciliation_log.info('')
        report_types = ['po', 'picklist']
        today = datetime.now()
        for user in users:
            sku_stats_dict = stock_reconciliation_for_po_picklist(user, today)
            sku_stock_dict = get_sku_stock_total(user)
            opening_stock_dict = get_opening_stock_dict(user, today)
            skus = SKUMaster.objects.filter(user=user.id)
            for sku in skus:
                sku_stats = sku_stats_dict.get(sku.id, {})
                sku_stocks = sku_stock_dict.get(sku.id, {})
                sku_openings = opening_stock_dict.get(sku.id, {})
                stock_reconciliation_dict = {}
                for key, value in sku_stats.iteritems():
                    sku_id, mrp, weight = key
                    po_details = value['PO']
                    order_details = value['picklist']
                    stock_reconciliation_dict.setdefault(key, {'sku_id': sku_id, 'mrp': mrp, 'weight': weight})
                    if po_details:
                        stock_reconciliation_dict[key]['purchase_quantity'] = po_details['quantity']
                        avg_rate = 0
                        if po_details['unit_price_list']:
                            avg_rate = sum(po_details['unit_price_list'])/len(po_details['unit_price_list'])
                        stock_reconciliation_dict[key]['purchase_avg_rate'] = avg_rate
                        stock_reconciliation_dict[key]['purchase_amount'] = po_details['amount']
                    if order_details:
                        stock_reconciliation_dict[key]['customer_sales_quantity'] = order_details['quantity']
                        avg_rate = 0
                        if order_details['unit_price_list']:
                            avg_rate = sum(order_details['unit_price_list'])/len(order_details['unit_price_list'])
                        stock_reconciliation_dict[key]['customer_sales_avg_rate'] = avg_rate
                        stock_reconciliation_dict[key]['customer_sales_amount'] = order_details['amount']
                for key, value in sku_stocks.iteritems():
                    sku_id, mrp, weight = key
                    stock_reconciliation_dict.setdefault(key, {'sku_id': sku_id, 'mrp': mrp, 'weight': weight})
                    stock_reconciliation_dict[key]['closing_quantity'] = value['quantity']
                    avg_rate = 0
                    if value['unit_price_list']:
                        avg_rate = sum(value['unit_price_list'])/len(value['unit_price_list'])
                    stock_reconciliation_dict[key]['closing_avg_rate'] = avg_rate
                    stock_reconciliation_dict[key]['closing_amount'] = value['amount']
                for key, value in sku_openings.iteritems():
                    sku_id, mrp, weight = key
                    stock_reconciliation_dict.setdefault(key, {'sku_id': sku_id, 'mrp': mrp, 'weight': weight})
                    stock_reconciliation_dict[key]['opening_quantity'] = value['quantity']
                    avg_rate = 0
                    if value['unit_price_list']:
                        avg_rate = sum(value['unit_price_list'])/len(value['unit_price_list'])
                    stock_reconciliation_dict[key]['opening_avg_rate'] = avg_rate
                    stock_reconciliation_dict[key]['opening_amount'] = value['amount']

                for key, stock_reconciliation_data in stock_reconciliation_dict.iteritems():
                    stock_rec_obj = StockReconciliation.objects.update_or_create(sku_id=stock_reconciliation_data['sku_id'],
                                                      mrp=stock_reconciliation_data['mrp'],
                                                      weight=stock_reconciliation_data['weight'],
                                                      creation_date__startswith=today.date(),
                                                                       defaults=stock_reconciliation_data)
        #     stock_data = StockDetail.objects.exclude(Q(receipt_number=0) | Q(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE'])).filter(**search_params)
        #     stock_buy_price = dict(stock_data.values_list('sku__id').exclude(batch_detail=None).annotate(buy_price=Sum(F('batch_detail__buy_price'))))
        #     batch_detail_tax = dict(stock_data.values_list('sku__id').exclude(batch_detail=None).annotate(tax=Sum(F('batch_detail__tax_percent') * F('quantity') * F('batch_detail__buy_price') / 100)))
        #     po_count = dict(stock_data.values_list('sku__id').annotate(count_skus=Count(F('sku__id'))))
        #     get_all_skus = stock_data.values_list('sku__id', flat=True).distinct()
        #     seller_po_query = {}
        #     seller_po_query['purchase_order__open_po__sku__id__in'] = get_all_skus
        #     seller_po_query['purchase_order__open_po__sku__user'] = user.id
        #     get_cess_tax = dict(SellerPOSummary.objects.filter(**seller_po_query).values_list('purchase_order__open_po__sku__id').distinct().annotate(quantity=Sum(F('cess_tax') * F('purchase_order__open_po__price') * F('purchase_order__open_po__order_quantity') / 100)))
        #     zones_data = {}
        #     available_quantity = {}
        #     industry_type = user.userprofile.industry_type
        #     for wms_code in get_all_skus:
        #         sku_stock_obj = stock_data.filter(sku__id=wms_code)
        #         avail_qty = sku_stock_obj.aggregate(Sum('quantity'))['quantity__sum']
        #         if not avail_qty:
        #             avail_qty = 0
        #         buy_price = stock_buy_price.get(wms_code, 0) * avail_qty
        #         tax_total = batch_detail_tax.get(wms_code, 0)
        #         data_dict = {}
        #         data_dict['sku_id'] = str(wms_code)
        #         data_dict['report_type'] = "closing_stock"
        #         data_dict['created_date'] = str(datetime.now().date())
        #         stock_recon = StockReconciliation.objects.filter(**data_dict)
        #         if stock_recon:
        #             stock_recon = stock_recon[0]
        #             stock_recon.quantity = avail_qty
        #             stock_recon.avg_rate = buy_price / po_count.get(wms_code, 0)
        #             stock_recon.amount_before_tax = stock_recon.avg_rate
        #             stock_recon.tax_rate = tax_total / po_count.get(wms_code, 0)
        #             stock_recon.cess_rate = get_cess_tax.get(wms_code, 0) / po_count.get(wms_code, 0)
        #             stock_recon.amount_after_tax = stock_recon.amount_before_tax + stock_recon.tax_rate + stock_recon.cess_rate
        #             stock_recon.save()
        #         else:
        #             data_dict['vendor_name'] = ''
        #             data_dict['quantity'] = avail_qty
        #             data_dict['avg_rate'] = buy_price / po_count.get(wms_code, 0)
        #             data_dict['amount_before_tax'] = data_dict['avg_rate']
        #             data_dict['tax_rate'] = tax_total / po_count.get(wms_code, 0)
        #             data_dict['cess_rate'] = get_cess_tax.get(wms_code, 0) / po_count.get(wms_code, 0)
        #             data_dict['amount_after_tax'] = data_dict['amount_before_tax'] + data_dict['tax_rate'] + data_dict['cess_rate']
        #             data_dict['creation_date'] = str(datetime.now())
        #             StockReconciliation.objects.create(**data_dict)
        #
        #     query_opening_stock = {}
        #     query_opening_stock['report_type'] = 'closing_stock'
        #     query_opening_stock['created_date'] = str(date.today() - timedelta(days=int(1)))
        #     opening_stock_obj = StockReconciliation.objects.filter(**query_opening_stock)
        #     for obj in opening_stock_obj:
        #         data_dict['vendor_name'] = ''
        #         data_dict['sku_id'] = obj.sku.id
        #         data_dict['report_type'] = 'opening_stock'
        #         data_dict['quantity'] = obj.quantity
        #         data_dict['avg_rate'] = obj.avg_rate
        #         data_dict['amount_before_tax'] = obj.amount_before_tax
        #         data_dict['tax_rate'] = obj.tax_rate
        #         data_dict['cess_rate'] = obj.cess_rate
        #         data_dict['amount_after_tax'] = obj.amount_after_tax
        #         data_dict['creation_date'] = str(datetime.now())
        #         opening_stock_check = {}
        #         opening_stock_check['report_type'] = 'opening_stock'
        #         opening_stock_check['created_date'] = str(date.today())
        #         opening_stock_check['sku_id'] = obj.sku.id
        #         opening_stock_check = StockReconciliation.objects.filter(**opening_stock_check)
        #         if opening_stock_check:
        #             opening_stock_check = opening_stock_check[0]
        #             opening_stock_check.quantity = obj.quantity
        #             opening_stock_check.avg_rate = obj.avg_rate
        #             opening_stock_check.amount_before_tax = obj.amount_before_tax
        #             opening_stock_check.tax_rate = obj.tax_rate
        #             opening_stock_check.cess_rate = obj.cess_rate
        #             opening_stock_check.amount_after_tax = obj.amount_after_tax
        #             opening_stock_check.created_date = str(datetime.now().date())
        #             opening_stock_check.save()
        #         else:
        #             StockReconciliation.objects.create(**data_dict)
        #     if not opening_stock_obj:
        #         today = str(datetime.now().date())
        #         from django.db.models import Value, CharField
        #         from django.db.models.functions import Concat
        #         all_sku_stats = SKUDetailStats.objects.filter(sku__user=user.id, creation_date__startswith = today)
        #         sku_codes = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values_list('sku_id', flat=True).distinct()
        #
        #         #stock_objs = dict(StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Concat('quantity', Value('<<>>'), 'batch_detail__buy_price', Value('<<>>'), 'batch_detail__tax_percent', output_field=CharField())))
        #
		# stock_sku_count = dict(StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values_list('sku_id').distinct().annotate(count_qty=Count('sku_id')))
        #         stock_qty = dict(StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values_list('sku_id').distinct().annotate(in_stock=Sum('quantity')))
        #         stock_price = dict(StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values_list('sku_id').distinct().annotate(in_stock=Sum('batch_detail__buy_price')))
        #         #stock_tax = dict(StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values_list('sku_id').distinct().annotate(in_stock=Sum('stock_detail__batch_detail__tax_percent')))
		# stock_tax = dict(StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Sum(F('batch_detail__tax_percent') * F('batch_detail__buy_price') * F('quantity') / 100)))
        #
        #
		# putaway_sku_count = dict(all_sku_stats.filter(transact_type='po', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Count('sku_id')) )
		# putaway_qty = dict(all_sku_stats.filter(transact_type='po', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
        #         #putaway_objs = dict(all_sku_stats.filter(transact_type='po', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Concat('quantity', Value('<<>>'), 'stock_detail__batch_detail__buy_price', Value('<<>>'), 'stock_detail__batch_detail__tax_percent', output_field=CharField())))
		# stock_uploaded_count = dict(all_sku_stats.filter(transact_type='inventory-upload', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Count('sku_id')))
		# stock_uploaded_qty = dict(all_sku_stats.filter(transact_type='inventory-upload', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
        #         #stock_uploaded_objs = dict(all_sku_stats.filter(transact_type='inventory-upload', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Concat('quantity', Value('<<>>'), 'stock_detail__batch_detail__buy_price', Value('<<>>'), 'stock_detail__batch_detail__tax_percent', output_field=CharField())))
        #         #picklist_objs = dict(all_sku_stats.filter(transact_type='picklist', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Concat('quantity', Value('<<>>'), 'stock_detail__batch_detail__buy_price', Value('<<>>'), 'stock_detail__batch_detail__tax_percent', output_field=CharField())))
		# picklist_count = dict(all_sku_stats.filter(transact_type='picklist', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Count('sku_id')))
		# picklist_qty = dict(all_sku_stats.filter(transact_type='picklist', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
        #         #inv_adjust_objs = dict(all_sku_stats.filter(transact_type='inventory-adjustment', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Concat('quantity', Value('<<>>'), 'stock_detail__batch_detail__buy_price', Value('<<>>'), 'stock_detail__batch_detail__tax_percent', output_field=CharField())))
		# inv_adjust_count = dict(all_sku_stats.filter(transact_type='inventory-adjustment', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Count('sku_id')))
		# inv_adjust_qty = dict(all_sku_stats.filter(transact_type='inventory-adjustment', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Count('quantity')))
		# return_count = dict(all_sku_stats.filter(transact_type='return', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Count('sku_id')))
		# return_qty = dict(all_sku_stats.filter(transact_type='return', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Count('quantity')))
        #         #return_objs = dict(all_sku_stats.filter(transact_type='return', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Concat('quantity', Value('<<>>'), 'stock_detail__batch_detail__buy_price', Value('<<>>'), 'stock_detail__batch_detail__tax_percent', output_field=CharField())))
		# jo_putaway_count = dict(all_sku_stats.filter(transact_type='jo', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Count('sku_id')))
        #         jo_putaway_qty = dict(all_sku_stats.filter(transact_type='jo', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Count('quantity')))
        #         #jo_putaway_objs = dict(all_sku_stats.filter(transact_type='jo', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Concat('quantity', Value('<<>>'), 'stock_detail__batch_detail__buy_price', Value('<<>>'), 'stock_detail__batch_detail__tax_percent', output_field=CharField())))
		# rm_picklist_count = dict(all_sku_stats.filter(transact_type='rm_picklist', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Count('sku_id')))
        #         rm_picklist_qty = dict(all_sku_stats.filter(transact_type='rm_picklist', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Count('quantity')))
        #
		# rtv_qty = dict(all_sku_stats.filter(transact_type='rtv').values_list('sku_id').distinct().annotate(quantity=Count('quantity')))
		# rtv_count = dict(all_sku_stats.filter(transact_type='rtv').values_list('sku_id').distinct().annotate(quantity=Count('sku_id')))
		#
        #         #rm_picklist_objs = dict(all_sku_stats.filter(transact_type='rm_picklist', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Concat('quantity', Value('<<>>'), 'stock_detail__batch_detail__buy_price', Value('<<>>'), 'stock_detail__batch_detail__tax_percent', output_field=CharField())))
        #         seller_po_query = {}
        #         seller_po_query['purchase_order__open_po__sku__id__in'] = sku_codes
        #         seller_po_query['purchase_order__open_po__sku__user'] = user.id
        #         seller_po_query['purchase_order__open_po__creation_date__startswith'] = datetime.now().date()
        #         seller_po = dict(SellerPOSummary.objects.filter(**seller_po_query).values_list('purchase_order__open_po__sku__id').distinct().annotate(quantity=Sum(F('cess_tax') * F('purchase_order__open_po__price') * F('purchase_order__open_po__order_quantity') / 100)))
        #         for sku in sku_codes:
        #             opening_stock = int(stock_qty.get(sku, 0)) - (int(putaway_qty.get(sku, 0)) + int(stock_uploaded_qty.get(sku, 0)) + int(return_qty.get(sku, 0)) + int(jo_putaway_qty.get(sku, 0))) + int(picklist_qty.get(sku, 0) + int(rm_picklist_qty.get(sku, 0))) - int(inv_adjust_qty.get(sku, 0)) + int(rtv_qty.get(sku, 0))
        #             if opening_stock:
        #                 stock_tax_val, stock_price_val = 0, 0
        #                 if stock_tax.get(sku, 0):
        #                     stock_tax_val = stock_tax.get(sku, 0)
        #                 if stock_price.get(sku, 0):
        #                     stock_price_val = stock_price.get(sku, 0)
        #                 stock_buy_price = float(stock_price_val)/float(stock_sku_count.get(sku, 0))
        #                 stock_tax_value = float(stock_tax_val)/float(stock_sku_count.get(sku, 0))
        #             else:
        #                 stock_buy_price = 0
        #                 stock_tax_value = 0
        #             if not stock_buy_price:
        #                 stock_buy_price = 0
        #             if not stock_tax_value:
        #                 stock_tax_value = 0
        #             if not stock_qty:
        #                 stock_qty = 0
        #             opening_stock_dict = {}
        #             opening_stock_dict['sku_id'] = sku
        #             opening_stock_dict['created_date'] = str(date.today())
        #             opening_stock_dict['report_type'] = 'opening_stock'
        #             opening_stock_check = StockReconciliation.objects.filter(**opening_stock_dict)
        #             if opening_stock_check:
        #                 opening_stock_check = opening_stock_check[0]
        #                 opening_stock_check.quantity = float(opening_stock)
        #                 opening_stock_check.avg_rate = float(opening_stock) * float(stock_buy_price)
        #                 opening_stock_check.amount_before_tax = float(opening_stock) * float(stock_buy_price)
        #                 opening_stock_check.tax_rate = stock_tax_value
        #                 if opening_stock_check.quantity:
        #                     opening_stock_check.cess_rate = float(seller_po.get(sku, 0))
        #                 else:
        #                     opening_stock_check.cess_rate = 0
		# 	opening_stock_check.amount_after_tax = float(opening_stock_check.amount_before_tax) + float(opening_stock_check.cess_rate) + float(opening_stock_check.tax_rate)
        #                 opening_stock_check.created_date = str(datetime.now().date())
        #                 opening_stock_check.save()
        #             else:
        #                 opening_stock_dict['quantity'] = float(opening_stock)
        #                 opening_stock_dict['avg_rate'] = float(opening_stock) * float(stock_buy_price)
        #                 opening_stock_dict['amount_before_tax'] = float(opening_stock) * float(stock_buy_price)
        #                 opening_stock_dict['tax_rate'] = stock_tax_value
        #                 if opening_stock_dict['quantity']:
        #                     opening_stock_dict['cess_rate'] = float(seller_po.get(sku, 0))
        #                 else:
        #                     opening_stock_dict['cess_rate'] = 0
		# 	opening_stock_dict['amount_after_tax'] = float(opening_stock_dict['amount_before_tax']) + float(opening_stock_dict['cess_rate']) + float(opening_stock_dict['tax_rate'])
        #                 opening_stock_dict['created_date'] = str(datetime.now().date())
        #                 StockReconciliation.objects.create(**opening_stock_dict)

