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
        
        def stock_reconciliation_for_po_picklist(report_type, user):
            filterStats = {}
            today = datetime.now().date()
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
                seller_po_query['purchase_order__open_po__creation_date__startswith'] = datetime.now().date()
                seller_po = dict(SellerPOSummary.objects.filter(**seller_po_query).values_list('purchase_order__open_po__sku__id').distinct().annotate(quantity=Sum(F('cess_tax') * F('purchase_order__open_po__price') * F('purchase_order__open_po__order_quantity') / 100)))
                for sku in loop_po_skus:
                    data_dict = {}
                    data_dict['sku_id'] = str(sku)
                    data_dict['report_type'] = report_type
                    data_dict['created_date'] = str(datetime.now().date())
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
                        data_dict['created_date'] = str(datetime.now().date())
                        data_dict['creation_date'] = str(datetime.now())
                        
                        StockReconciliation.objects.create(**data_dict)

        users = User.objects.filter(username='milkbasket')
        management_stock_reconciliation_log.info('')
        report_types = ['po', 'picklist']
        for user in users:
            for report in report_types:
                stock_reconciliation_for_po_picklist(report, user)
        
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
                data_dict['created_date'] = str(datetime.now().date())
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
                    data_dict['creation_date'] = str(datetime.now())
                    StockReconciliation.objects.create(**data_dict)


            query_opening_stock = {}
            query_opening_stock['report_type'] = 'closing_stock'
            query_opening_stock['created_date'] = str(date.today() - timedelta(days=int(1)))
            opening_stock_obj = StockReconciliation.objects.filter(**query_opening_stock)
            for obj in opening_stock_obj:
                data_dict['vendor_name'] = ''
                data_dict['sku_id'] = obj.sku.id
                data_dict['report_type'] = 'opening_stock'
                data_dict['quantity'] = obj.quantity
                data_dict['avg_rate'] = obj.avg_rate
                data_dict['amount_before_tax'] = obj.amount_before_tax
                data_dict['tax_rate'] = obj.tax_rate
                data_dict['cess_rate'] = obj.cess_rate
                data_dict['amount_after_tax'] = obj.amount_after_tax
                data_dict['creation_date'] = str(datetime.now())
                opening_stock_check = {}
                opening_stock_check['report_type'] = 'opening_stock'
                opening_stock_check['created_date'] = str(date.today())
                opening_stock_check['sku_id'] = obj.sku.id
                opening_stock_check = StockReconciliation.objects.filter(**opening_stock_check)
                if opening_stock_check:
                    opening_stock_check = opening_stock_check[0]
                    opening_stock_check.quantity = obj.quantity
                    opening_stock_check.avg_rate = obj.avg_rate
                    opening_stock_check.amount_before_tax = obj.amount_before_tax
                    opening_stock_check.tax_rate = obj.tax_rate
                    opening_stock_check.cess_rate = obj.cess_rate
                    opening_stock_check.amount_after_tax = obj.amount_after_tax
                    opening_stock_check.created_date = str(datetime.now().date())
                    opening_stock_check.save()
                else:
                    StockReconciliation.objects.create(**data_dict)
            else:
                today = str(datetime.now().date())
                from django.db.models import Value, CharField
                from django.db.models.functions import Concat
                all_sku_stats = SKUDetailStats.objects.filter(sku__user=user.id, creation_date__startswith = today)
                sku_codes = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values_list('sku_id', flat=True).distinct()
                stock_objs = dict(StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Concat('quantity', Value('<<>>'), 'batch_detail__buy_price', Value('<<>>'), 'batch_detail__tax_percent', output_field=CharField())))
                putaway_objs = dict(all_sku_stats.filter(transact_type='po', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Concat('quantity', Value('<<>>'), 'stock_detail__batch_detail__buy_price', Value('<<>>'), 'stock_detail__batch_detail__tax_percent', output_field=CharField())))
                stock_uploaded_objs = dict(all_sku_stats.filter(transact_type='inventory-upload', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Concat('quantity', Value('<<>>'), 'stock_detail__batch_detail__buy_price', Value('<<>>'), 'stock_detail__batch_detail__tax_percent', output_field=CharField())))
                picklist_objs = dict(all_sku_stats.filter(transact_type='picklist', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Concat('quantity', Value('<<>>'), 'stock_detail__batch_detail__buy_price', Value('<<>>'), 'stock_detail__batch_detail__tax_percent', output_field=CharField())))
                inv_adjust_objs = dict(all_sku_stats.filter(transact_type='inventory-adjustment', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Concat('quantity', Value('<<>>'), 'stock_detail__batch_detail__buy_price', Value('<<>>'), 'stock_detail__batch_detail__tax_percent', output_field=CharField())))
                return_objs = dict(all_sku_stats.filter(transact_type='return', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Concat('quantity', Value('<<>>'), 'stock_detail__batch_detail__buy_price', Value('<<>>'), 'stock_detail__batch_detail__tax_percent', output_field=CharField())))
                jo_putaway_objs = dict(all_sku_stats.filter(transact_type='jo', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Concat('quantity', Value('<<>>'), 'stock_detail__batch_detail__buy_price', Value('<<>>'), 'stock_detail__batch_detail__tax_percent', output_field=CharField())))
                rm_picklist_objs = dict(all_sku_stats.filter(transact_type='rm_picklist', quantity__gt=0).values_list('sku_id').distinct().annotate(quantity=Concat('quantity', Value('<<>>'), 'stock_detail__batch_detail__buy_price', Value('<<>>'), 'stock_detail__batch_detail__tax_percent', output_field=CharField())))

                seller_po_query = {}
                seller_po_query['purchase_order__open_po__sku__id__in'] = sku_codes
                seller_po_query['purchase_order__open_po__sku__user'] = user.id
                seller_po_query['purchase_order__open_po__creation_date__startswith'] = datetime.now().date()
                seller_po = dict(SellerPOSummary.objects.filter(**seller_po_query).values_list('purchase_order__open_po__sku__id').distinct().annotate(quantity=Sum(F('cess_tax') * F('purchase_order__open_po__price') * F('purchase_order__open_po__order_quantity') / 100)))

                for sku in sku_codes:
                    stock_upload_qty, stock_upload_buy_price, stock_upload_tax_percent = 0, 0, 0
                    picklist_qty, picklist_buy_price, picklist_tax_percent = 0, 0, 0
                    inv_adjust_qty, inv_adjust_buy_price, inv_adjust_tax_percent = 0, 0, 0
                    return_qty, return_buy_price, return_tax_percent = 0, 0, 0
                    jo_qty, jo_buy_price, jo_tax_percent = 0, 0, 0
                    rm_qty, rm_buy_price, rm_tax_percent = 0, 0, 0
                    putaway_qty, putaway_buy_price, putaway_tax_percent = 0, 0, 0
                    stock_qty, stock_buy_price, stock_tax_percent = 0, 0, 0
                    if stock_objs.get(sku, 0):
                        stock_qty, stock_buy_price, stock_tax_percent = stock_objs.get(sku, '').split('<<>>')
                    if putaway_objs.get(sku, 0):
                        putaway_qty, putaway_buy_price, putaway_tax_percent = putaway_objs.get(sku, '').split('<<>>')
                    if stock_uploaded_objs.get(sku, 0):
                        stock_upload_qty, stock_upload_buy_price, stock_upload_tax_percent = stock_uploaded_objs.get(sku, '').split('<<>>')
                    if picklist_objs.get(sku, 0):
                        picklist_qty, picklist_buy_price, picklist_tax_percent = picklist_objs.get(sku, '').split('<<>>')
                    if inv_adjust_objs.get(sku, 0):
                        inv_adjust_qty, inv_adjust_buy_price, inv_adjust_tax_percent = inv_adjust_objs.get(sku, '').split('<<>>')
                    if return_objs.get(sku, 0):
                        return_qty, return_buy_price, return_tax_percent = return_objs.get(sku, '').split('<<>>')
                    if jo_putaway_objs.get(sku, 0):
                        jo_qty, jo_buy_price, jo_tax_percent = jo_putaway_objs.get(sku, '').split('<<>>')
                    if rm_picklist_objs.get(sku, 0):
                        rm_qty, rm_buy_price, rm_tax_percent = rm_picklist_objs.get(sku, '').split('<<>>')

                    opening_stock = int(stock_qty) - (int(putaway_qty) + int(stock_upload_qty) + int(picklist_qty) + int(inv_adjust_qty) + int(return_qty) + int(jo_qty) + int(rm_qty))

                    if not stock_buy_price:
                        stock_buy_price = 0
                    if not stock_tax_percent:
                        stock_tax_percent = 0
                    if not stock_qty:
                        stock_qty = 0

                    opening_stock_dict = {}
                    opening_stock_dict['sku_id'] = sku
                    opening_stock_dict['created_date'] = str(date.today())
                    opening_stock_dict['report_type'] = 'opening_stock'
                    
                    opening_stock_check = StockReconciliation.objects.filter(**opening_stock_dict)
                    if opening_stock_check:
                        opening_stock_check = opening_stock_check[0]
                        opening_stock_check.quantity = opening_stock * stock_buy_price
                        opening_stock_check.avg_rate = opening_stock * stock_buy_price
                        opening_stock_check.amount_before_tax = opening_stock * stock_buy_price
                        opening_stock_check.tax_rate = (float(stock_tax_percent) * int(opening_stock_check.quantity) * float(stock_buy_price))/100
                        if opening_stock_check.quantity:
                            opening_stock_check.cess_rate = seller_po.get(sku, 0)
                            opening_stock_check.amount_after_tax = opening_stock_check.amount_before_tax + opening_stock_check.cess_rate + opening_stock_check.tax_rate
                        else:
                            opening_stock_check.cess_rate = 0
                            opening_stock_check.amount_after_tax = 0
                        opening_stock_check.created_date = str(datetime.now().date())
                        opening_stock_check.save()
                    else:
                        opening_stock_dict['quantity'] = opening_stock * stock_buy_price
                        opening_stock_dict['avg_rate'] = opening_stock * stock_buy_price
                        opening_stock_dict['amount_before_tax'] = opening_stock * stock_buy_price
                        opening_stock_dict['tax_rate'] = (stock_tax_percent * opening_stock_dict['quantity'])/100
                        if opening_stock_dict['quantity']:
                            opening_stock_dict['cess_rate'] = seller_po.get(sku, 0)
                            opening_stock_dict['amount_after_tax'] = opening_stock_dict['amount_before_tax'] + opening_stock_dict['cess_rate'] + opening_stock_dict['tax_rate']
                        else:
                            opening_stock_dict['cess_rate'] = 0
                            opening_stock_dict['amount_after_tax'] = 0
                        opening_stock_dict['created_date'] = str(datetime.now().date())
                        StockReconciliation.objects.create(**opening_stock_dict)

