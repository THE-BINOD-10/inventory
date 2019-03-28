"""
 Code for Stock Reconciliation
"""
from collections import OrderedDict
from django.core.management import BaseCommand
from django.db.models import Q, Sum, F
import os
import logging
import datetime
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
        
        def stock_reconciliation(report_type, user):
            filterStats = {}
            today = datetime.datetime.now().date()
            filterStats['sku__user'] = user.id
            filterStats['transact_type'] = report_type
            filterStats['creation_date__startswith'] = today
            sku_detail_stats = SKUDetailStats.objects.filter(**filterStats)
            if sku_detail_stats:
                po_skus = sku_detail_stats
                loop_po_skus = po_skus.values_list('sku__id', flat=True).distinct()
                po_skus = po_skus.values_list('sku__id').distinct()
                po_qty = dict(po_skus.annotate(quantity=Sum(F('quantity'))))
                po_count_qty = dict(po_skus.annotate(count_skus=Count(F('sku__id'))))
                po_avg_rate = dict(po_skus.exclude(stock_detail__batch_detail=None).annotate(weighted_cost=Sum(F('quantity') * F('stock_detail__batch_detail__buy_price'))))
                amount_before_tax = po_avg_rate
                tax_rate = dict(po_skus.exclude(stock_detail__batch_detail=None).annotate(weighted_cost=Sum(F('stock_detail__batch_detail__tax_percent') * F('quantity') * F('stock_detail__batch_detail__buy_price') / 100)))
                seller_po_query = {}
                seller_po_query['purchase_order__open_po__sku__id__in'] = loop_po_skus
                seller_po_query['purchase_order__open_po__sku__user'] = user.id
                seller_po_query['purchase_order__open_po__creation_date__startswith'] = datetime.datetime.now().date()
                seller_po = dict(SellerPOSummary.objects.filter(**seller_po_query).values_list('purchase_order__open_po__sku__id').distinct().annotate(quantity=Sum(F('cess_tax') * F('purchase_order__open_po__price') * F('purchase_order__open_po__order_quantity') / 100)))
                for sku in loop_po_skus:
                    data_dict = {}
                    data_dict['sku_id'] = str(sku)
                    data_dict['report_type'] = report_type
                    data_dict['created_date'] = str(datetime.datetime.now().date())
                    stock_recon = StockReconciliation.objects.filter(**data_dict)
                    if stock_recon:
                        stock_recon = stock_recon[0]
                        stock_recon.quantity = po_qty.get(sku, 0)
                        stock_recon.avg_rate = po_avg_rate.get(sku, 0) / po_count_qty.get(sku, 0)
                        stock_recon.amount_before_tax = amount_before_tax.get(sku, 0) / po_count_qty.get(sku, 0)
                        stock_recon.tax_rate = tax_rate.get(sku, 0) / po_count_qty.get(sku, 0)
                        stock_recon.cess_rate =  seller_po.get(sku, 0) / po_count_qty.get(sku, 0)
                        stock_recon.amount_after_tax = stock_recon.amount_before_tax + stock_recon.tax_rate + stock_recon.cess_rate
                        stock_recon.save()
                    else:
                        data_dict['vendor_name'] = ''
                        data_dict['quantity'] = po_qty.get(sku, 0)
                        data_dict['avg_rate'] = po_avg_rate.get(sku, 0)/po_count_qty.get(sku, 0)
                        data_dict['amount_before_tax'] = amount_before_tax.get(sku, 0)/po_count_qty.get(sku, 0)
                        data_dict['tax_rate'] = tax_rate.get(sku, 0) / po_count_qty.get(sku, 0)
                        data_dict['cess_rate'] = seller_po.get(sku, 0) / po_count_qty.get(sku, 0)
                        data_dict['amount_after_tax'] = data_dict['amount_before_tax'] + data_dict['tax_rate'] + data_dict['cess_rate']
                        data_dict['created_date'] = str(datetime.datetime.now().date())
                        data_dict['creation_date'] = str(datetime.datetime.now())
                        StockReconciliation.objects.create(**data_dict)

        users = User.objects.filter(username='milkbasket')
        log.info(str(datetime.datetime.now()))
        report_types = ['po', 'picklist']
        for user in users:
            for report in report_types:
                stock_reconciliation(report, user)
        
        users = User.objects.filter(username='milkbasket')
        log.info(str(datetime.datetime.now()))
        
        for user in users:
            search_params = {}
            search_params['sku__user'] = user.id
            stock_data = StockDetail.objects.exclude(Q(receipt_number=0) | Q(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE'])).filter(**search_params)
            stock_buy_price = dict(stock_data.values_list('sku__id').exclude(batch_detail=None).annotate(buy_price=Sum(F('batch_detail__buy_price'))))
            batch_detail_tax = dict(stock_data.values_list('sku__id').exclude(batch_detail=None).annotate(tax=Sum(F('batch_detail__tax_percent') * F('quantity') * F('batch_detail__buy_price') / 100)))
            po_count = dict(stock_data.values_list('sku__id').annotate(count_skus=Count(F('sku__id'))))
            get_all_skus = stock_data.values_list('sku__id', flat=True).distinct()
            seller_po_query = {}
            seller_po_query['purchase_order__open_po__sku__id__in'] = get_all_skus
            seller_po_query['purchase_order__open_po__sku__user'] = user.id
            get_cess_tax = dict(SellerPOSummary.objects.filter(**seller_po_query).values_list('purchase_order__open_po__sku__id').distinct().annotate(quantity=Sum(F('cess_tax') * F('purchase_order__open_po__price') * F('purchase_order__open_po__order_quantity') / 100)))
            zones_data = {}
            available_quantity = {}
            industry_type = user.userprofile.industry_type
            for wms_code in get_all_skus:
                sku_stock_obj = stock_data.filter(sku__id=wms_code)
                for stock in sku_stock_obj:
                    res_qty = PicklistLocation.objects.filter(stock_id=stock.id, status=1, picklist__order__user=user.id).aggregate(Sum('reserved'))['reserved__sum']
                    raw_reserved = RMLocation.objects.filter(status=1, material_picklist__jo_material__material_code__user=user.id, stock_id=stock.id).aggregate(Sum('reserved'))['reserved__sum']
                    if not res_qty:
                        res_qty = 0
                    if raw_reserved:
                        res_qty = float(res_qty) + float(raw_reserved)
                    location = stock.location.location
                    zone = stock.location.zone.zone
                    pallet_number, batch, mrp, ean, weight = ['']*5
                    buy_price = 0
                    tax_percent = 0
                    if industry_type == "FMCG" and stock.batch_detail:
                        batch_detail = stock.batch_detail
                        batch = batch_detail.batch_no
                        mrp = batch_detail.mrp
                        
                        weight = batch_detail.weight
                        if batch_detail.ean_number:
                            ean = int(batch_detail.ean_number)
                        buy_price = batch_detail.buy_price
                        tax_percent = batch_detail.tax_percent

                    cond = str((zone, location, pallet_number, batch, mrp, ean, weight))
                    zones_data.setdefault(cond,
                                          {'zone': zone, 'location': location, 'pallet_number': pallet_number, 'total_quantity': 0,
                                           'reserved_quantity': 0, 'batch': batch, 'mrp': mrp, 'ean': ean,
                                           'weight': weight})
                    zones_data[cond]['total_quantity'] += stock.quantity
                    zones_data[cond]['reserved_quantity'] += res_qty
                    available_quantity.setdefault(location, 0)
                    available_quantity[location] += (stock.quantity - res_qty)
                avail_qty = sum(map(lambda d: available_quantity[d] if available_quantity[d] > 0 else 0, available_quantity))
                buy_price = stock_buy_price.get(wms_code, 0) * avail_qty
                tax_total = batch_detail_tax.get(wms_code, 0)
                data_dict = {}
                data_dict['sku_id'] = str(wms_code)
                data_dict['report_type'] = "closing_stock"
                data_dict['created_date'] = str(datetime.datetime.now().date())
                stock_recon = StockReconciliation.objects.filter(**data_dict)
                if stock_recon:
                    stock_recon = stock_recon[0]
                    stock_recon.quantity = avail_qty
                    stock_recon.avg_rate = buy_price / po_count.get(wms_code, 0)
                    stock_recon.amount_before_tax = stock_recon.avg_rate
                    stock_recon.tax_rate = tax_total / po_count.get(wms_code, 0)
                    stock_recon.cess_rate = get_cess_tax.get(wms_code, 0) / po_count.get(wms_code, 0)
                    stock_recon.amount_after_tax = stock_recon.amount_before_tax + stock_recon.tax_rate + stock_recon.cess_rate
                    stock_recon.save()
                else:
                    data_dict['vendor_name'] = ''
                    data_dict['quantity'] = avail_qty
                    data_dict['avg_rate'] = buy_price / po_count.get(wms_code, 0)
                    data_dict['amount_before_tax'] = data_dict['avg_rate']
                    data_dict['tax_rate'] = tax_total / po_count.get(wms_code, 0)
                    data_dict['cess_rate'] = get_cess_tax.get(wms_code, 0) / po_count.get(wms_code, 0)
                    data_dict['amount_after_tax'] = data_dict['amount_before_tax'] + data_dict['tax_rate'] + data_dict['cess_rate']
                    data_dict['creation_date'] = str(datetime.datetime.now())
                    StockReconciliation.objects.create(**data_dict)
