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
        users = User.objects.filter(username='milkbasket')
        log.info(str(datetime.datetime.now()))
        for user in users:
            filterStats = {}
            today = datetime.datetime.now().date()
            #Purchases
            report_type = "po"
            filterStats['sku__user'] = user.id
            filterStats['transact_type'] = report_type
            filterStats['creation_date__startswith'] = today
            sku_detail_stats = SKUDetailStats.objects.filter(**filterStats)
            if sku_detail_stats:
                po_skus = sku_detail_stats.filter(transact_type=report_type)
                loop_po_skus = po_skus.values_list('sku__wms_code', flat=True).distinct()
                po_skus = po_skus.values_list('sku__wms_code').distinct()
                po_qty = dict(po_skus.annotate(quantity=Sum(F('quantity'))))
                po_count_qty = dict(po_skus.annotate(count_skus=Count(F('sku__wms_code'))))
                po_avg_rate = dict(po_skus.annotate(weighted_cost=Sum(F('quantity') * F('stock_detail__batch_detail__buy_price'))))
                amount_before_tax = po_avg_rate
                tax_rate = dict(po_skus.annotate(weighted_cost=Sum(F('quantity') * F('stock_detail__batch_detail__tax_percent'))))
                seller_po_query = {}
                seller_po_query['purchase_order__open_po__sku__wms_code__in'] = loop_po_skus
                seller_po_query['purchase_order__open_po__sku__user'] = user.id
                seller_po_query['purchase_order__creation_date__startswith'] = today
                seller_po = dict(SellerPOSummary.objects.filter(**seller_po_query).values_list('purchase_order__open_po__sku__wms_code').distinct().annotate(quantity=Sum('cess_tax')))
                for sku in loop_po_skus:
                    data_dict = {}
                    data_dict['sku_id'] = str(sku)
                    data_dict['report_type'] = report_type
                    data_dict['created_date'] = str(datetime.datetime.now().date())
                    stock_recon = StockReconciliation.objects.filter(**data_dict)
                    if stock_recon:
                        stock_recon = stock_recon[0]
                        stock_recon.quantity = po_qty.get(sku, 0)
                        stock_recon.avg_rate = po_avg_rate.get(sku, 0)/po_count_qty.get(sku, 0)
                        stock_recon.amount_before_tax = amount_before_tax.get(sku, 0)/po_count_qty.get(sku, 0)
                        stock_recon.tax_rate = tax_rate.get(sku, 0)/po_count_qty.get(sku, 0)
                        stock_recon.cess_rate = (seller_po.get(sku, 0) * po_qty.get(sku, 0))/po_count_qty.get(sku, 0)
                        stock_recon.amount_after_tax = (amount_before_tax.get(sku, 0)/po_count_qty.get(sku, 0) + tax_rate.get(sku, 0)/po_count_qty.get(sku, 0) + seller_po.get(sku, 0))/po_count_qty.get(sku, 0)
                        stock_recon.save()
                    else:
                        data_dict['vendor_name'] = ''
                        data_dict['quantity'] = po_qty.get(sku, 0)
                        data_dict['avg_rate'] = po_avg_rate.get(sku, 0)/po_count_qty.get(sku, 0)
                        data_dict['amount_before_tax'] = amount_before_tax.get(sku, 0)/po_count_qty.get(sku, 0)
                        data_dict['tax_rate'] = tax_rate.get(sku, 0)/po_count_qty.get(sku, 0)
                        data_dict['cess_rate'] = (seller_po.get(sku, 0) * po_qty.get(sku, 0))/po_count_qty.get(sku, 0)
                        data_dict['amount_after_tax'] = (amount_before_tax.get(sku, 0)/po_count_qty.get(sku, 0) + tax_rate.get(sku, 0)/po_count_qty.get(sku, 0) + seller_po.get(sku, 0))/po_count_qty.get(sku, 0)
                        data_dict['created_date'] = str(datetime.datetime.now().date())
                        data_dict['creation_date'] = str(datetime.datetime.now())
                        StockReconciliation.objects.create(**data_dict)
            #Sales
            report_type = "sales"
            filterStats['sku__user'] = user.id
            filterStats['transact_type'] = report_type
            filterStats['creation_date__startswith'] = today
            sku_detail_stats = SKUDetailStats.objects.filter(**filterStats)
            if sku_detail_stats:
                sales_skus = sku_detail_stats.filter(transact_type=report_type)
                loop_sales_skus = sales_skus.values_list('sku__wms_code').distinct()
                sales_skus = sales_skus.values_list('sku__wms_code', flat=True).distinct()
                sales_qty = dict(sales_skus.annotate(quantity=Sum('quantity')))
                sales_count_qty = sales_skus.annotate(count_skus=Count(F('sku__wms_code')))
                sales_avg_rate = dict(sales_skus.annotate(weighted_cost=Sum(F('quantity') * F('stock_detail__batch_detail__buy_price'))))
                amount_before_tax = sales_avg_rate
                tax_rate = dict(sales_skus.annotate(weighted_cost=Sum(F('quantity') * F('stock_detail__batch_detail__tax_percent'))))
                get_all_batch_detail = sku_detail_stats.values_list('stock_detail__batch_detail__id', flat=True).distinct()
                seller_po = dict(SellerPOSummary.objects.filter(batch_detail__id__in=list(get_all_batch_detail)).values_list('purchase_order__open_po__sku__id').distinct().annotate(quantity=Sum('cess_tax')))
                for sku in loop_sales_skus:
                    data_dict = {}
                    data_dict['sku_id'] = str(sku)
                    data_dict['vendor_name'] = ''
                    data_dict['quantity'] = sales_qty.get(sku, 0)
                    data_dict['report_type'] = report_type
                    data_dict['avg_rate'] = sales_avg_rate.get(sku, 0)/sales_count_qty.get(sku, 0)
                    data_dict['amount_before_tax'] = amount_before_tax.get(sku, 0)/sales_count_qty.get(sku, 0)
                    data_dict['tax_rate'] = tax_rate.get(sku, 0)/sales_count_qty.get(sku, 0)
                    data_dict['cess_rate'] = seller_po.get(sku, 0)/sales_count_qty.get(sku, 0)
                    data_dict['amount_after_tax'] = amount_before_tax.get(sku, 0)/sales_count_qty.get(sku, 0) + tax_rate.get(sku, 0)/sales_count_qty.get(sku, 0) + seller_po.get(sku, 0)/sales_count_qty.get(sku, 0)
                    data_dict['created_date'] = str(datetime.datetime.now().date())
                    data_dict['creation_date'] = str(datetime.datetime.now())
                    StockReconciliation.objects.create(**data_dict)
