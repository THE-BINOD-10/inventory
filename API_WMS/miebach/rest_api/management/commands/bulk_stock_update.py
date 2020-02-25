from django.core.management import BaseCommand
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
import json
from rest_api.views.common import get_stock_receipt_number, get_all_zones, update_stocks_data,check_and_update_marketplace_stock
from rest_api.views.miebach_utils import MILKBASKET_USERS, fn_timer, MILKBASKET_BULK_ZONE
from django.db.models import Sum
from itertools import chain


def init_logger(log_file):
    log = logging.getLogger(log_file)

    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    return log


log = init_logger('logs/update_ba_sa_quantity.log')

class Command(BaseCommand):
    """
    Auto updating MRP to BA for ba_sa quantity zero 
    """
    help = "Auto updating MRP to BA for ba_sa quantity zero"

    def handle(self, *args, **options):
        self.stdout.write("Started Updating")
        users = User.objects.filter(username__in = MILKBASKET_USERS)
        dest_stocks = ''
        sku_codes = []
        for user in users:
            try:
                collect_all_sellable_location = list(LocationMaster.objects.filter(zone__segregation='sellable',  zone__user=user.id, status=1).values_list('location', flat=True))
                bulk_zones= get_all_zones(user ,zones=[MILKBASKET_BULK_ZONE])
                bulk_locations=list(LocationMaster.objects.filter(zone__zone__in=bulk_zones, zone__user=user.id, status=1).values_list('location', flat=True))
                sellable_bulk_locations=list(chain(collect_all_sellable_location ,bulk_locations))
                ba_sa_data = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0, location__location__in=sellable_bulk_locations).distinct()
                mrp_offer_change_data = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0, location__zone='Non Sellable Zone', location__status=1).distinct()
                stock_zero_skus = list(set(mrp_offer_change_data.values_list('sku__id')) - set(ba_sa_data.values_list('sku__id')))
                for sku in stock_zero_skus:
                    sku_id = sku[0]
                    sku_code = SKUMaster.objects.filter(id = sku_id)[0].sku_code
                    validate_data = mrp_offer_change_data.filter(sku = sku_id).order_by('receipt_date')
                    stocks = validate_data.filter(batch_detail__mrp = validate_data[0].batch_detail.mrp, batch_detail__weight=validate_data[0].batch_detail.weight)
                    quantity = stocks.aggregate(Sum("quantity"))
                    quantity = quantity['quantity__sum']
                    move_quantity = quantity
                    # dest_stocks = StockDetail.objects.filter(sku__user=user.id, quantity=0, location__location__in=sellable_bulk_locations, sku=sku_id).distinct()
                    # desc_loc = dest_stocks[0].location.location
                    dest = LocationMaster.objects.filter(location='BA', zone__user=user.id)
                    seller_stock = stocks[0].sellerstock_set.filter()
                    seller_id = seller_stock[0].seller_id
                    receipt_number = get_stock_receipt_number(user)
                    dest_batch = update_stocks_data(stocks, move_quantity, dest_stocks, quantity, user, dest, sku_id, src_seller_id=seller_id,
                                       dest_seller_id=seller_id, receipt_type='MRP_to_BA_update', receipt_number=receipt_number)
                    sub_data = {'source_sku_code_id': sku_id, 'source_location': 'MRP and Offer Change', 'source_quantity': quantity,
                                'destination_sku_code_id': sku_id, 'destination_location': dest[0].location,
                                'destination_quantity': quantity, 'source_batch_id':stocks[0].batch_detail_id,
                                'dest_batch_id': dest_batch.id, 'seller_id': seller_id, 'summary_type': 'bulk_stock_update'}
                    SubstitutionSummary.objects.create(**sub_data)
                    sku_codes.append(sku_code)
                    check_and_update_marketplace_stock(sku_codes, user)
                    log.info("Bulk Stock Update Done For " + str(json.dumps(sub_data)))
            except Exception as e:
                import traceback
                log.debug(traceback.format_exc())
                log.info('Milkbasket Bulk Stock Update failed for user %s and error statement is %s' %
                         (str(user.username), str(e)))
