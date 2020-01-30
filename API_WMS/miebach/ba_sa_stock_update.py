import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()
from django.db.models import Q
from miebach_admin.models import *
import datetime
from rest_api.views.utils import *
from rest_api.views import *
log = init_logger('logs/update_ba_sa_quantity.log')

def update_ba_sa_quantity():
    users = User.objects.filter(username__in = MILKBASKET_USERS)
    dest_stocks = ''
    for user in users:
        collect_all_sellable_location = list(LocationMaster.objects.filter(zone__segregation='sellable',  zone__user=user.id, status=1).values_list('location', flat=True))
        bulk_zones= get_all_zones(user ,zones=[MILKBASKET_BULK_ZONE])
        bulk_locations=list(LocationMaster.objects.filter(zone__zone__in=bulk_zones, zone__user=user.id, status=1).values_list('location', flat=True))
        sellable_bulk_locations=list(chain(collect_all_sellable_location ,bulk_locations))
        ba_sa_data = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0, location__location__in=sellable_bulk_locations).distinct()
        mrp_offer_change_data = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0, location__location='MRP and Offer Change').distinct()
        stock_zero_skus = list(set(mrp_offer_change_data.values_list('sku__id')) - set(ba_sa_data.values_list('sku__id')))
        for sku in stock_zero_skus:
            sku_id = sku[0]
            validate_data = mrp_offer_change_data.filter(sku = sku_id)
            stocks = validate_data.filter(batch_detail__mrp = validate_data[0].batch_detail.mrp, batch_detail__weight=validate_data[0].batch_detail.weight)
            quantity = stocks.aggregate(Sum("quantity"))
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
                        'dest_batch_id': dest_batch.batch_detail_id, 'seller_id': seller_id, 'summary_type': 'bulk_stock_update'}
            SubstitutionSummary.objects.create(**sub_data)
            log.info("Bulk Stock Update Done For " + str(json.dumps(sub_data)))
update_ba_sa_quantity()
