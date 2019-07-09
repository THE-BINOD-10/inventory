"""
 Code for Auto Picklist generation and Confirmation
"""
from collections import OrderedDict
from django.core.management import BaseCommand
from django.db.models import Q, Sum
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
    update_stocks_data, get_max_seller_transfer_id, get_financial_year, get_stock_receipt_number
from rest_api.views.outbound import get_seller_pick_id
from rest_api.views.miebach_utils import MILKBASKET_USERS, PICKLIST_FIELDS, ST_ORDER_FIELDS

def init_logger(log_file):
    log = logging.getLogger(log_file)

    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    return log


log = init_logger('logs/auto_process_picklists.log')

def prepare_picklist_val_dict(user, sku_id_stocks,  is_seller_order, add_mrp_filter):
    val_dict = {}
    val_dict['sku_ids'] = map(lambda d: d['sku_id'], sku_id_stocks)
    val_dict['stock_ids'] = map(lambda d: d['id'], sku_id_stocks)
    val_dict['stock_totals'] = map(lambda d: d['total'], sku_id_stocks)
    pc_loc_filter = {'status': 1}
    if is_seller_order or add_mrp_filter:
        pc_loc_filter['stock_id__in'] = val_dict['stock_ids']
    pick_res_locat = PicklistLocation.objects.prefetch_related('picklist', 'stock').filter(**pc_loc_filter). \
        filter(picklist__order__user=user.id).values('stock__sku_id').annotate(total=Sum('reserved'))

    val_dict['pic_res_ids'] = map(lambda d: d['stock__sku_id'], pick_res_locat)
    val_dict['pic_res_quans'] = map(lambda d: d['total'], pick_res_locat)
    return val_dict

def execute_picklist_confirm_process(order_data, picklist_number, user,
                                     sku_combos, sku_stocks, switch_vals, receipt_number,
                                     is_seller_order=False):
    stock_status = []
    is_marketplace_model = False
    all_zone_mappings = []
    seller_master_id = ''
    if switch_vals['marketplace_model'] == 'true':
        all_zone_mappings = ZoneMarketplaceMapping.objects.filter(zone__user=user.id, status=1)
        is_marketplace_model = True
    fefo_enabled = False
    add_mrp_filter = False
    if user.userprofile.industry_type == 'FMCG':
        fefo_enabled = True
        if user.username in MILKBASKET_USERS:
            add_mrp_filter = True
    if switch_vals['fifo_switch'] == 'true':
        order_by = 'receipt_date'
    else:
        order_by = 'location_id__pick_sequence'
    no_stock_switch = False
    if switch_vals['no_stock_switch'] == 'true':
        no_stock_switch = True
    combo_allocate_stock = False
    if switch_vals.get('combo_allocate_stock', '') == 'true':
        combo_allocate_stock = True
    picklist_data = copy.deepcopy(PICKLIST_FIELDS)
    if is_seller_order:
        seller_order = order_data
        seller_master_id = seller_order.seller_id
        order = order_data.order
    picklist_data['picklist_number'] = picklist_number + 1
    picklist_data['remarks'] = 'Auto Confirmed Picklist'
    financial_year = get_financial_year(datetime.datetime.now())


    combo_sku_ids = list(sku_combos.filter(parent_sku_id=order.sku_id).\
                         values_list('member_sku_id', flat=True))
    combo_sku_ids.append(order.sku_id)
    sku_id_stock_filter = {'sku_id__in': combo_sku_ids}
    needed_mrp_filter = 0
    if add_mrp_filter:
        if 'st_po' not in dir(order) and order.customerordersummary_set.filter().exists():
            needed_mrp_filter = order.customerordersummary_set.filter()[0].mrp
            sku_id_stock_filter['batch_detail__mrp'] = needed_mrp_filter
    if seller_order:
        temp_sku_stocks = sku_stocks
        sku_stocks = sku_stocks.filter(sellerstock__seller_id=seller_order.seller_id)
    if seller_master_id:
        sku_id_stocks = sku_stocks.filter(sellerstock__seller_id=seller_master_id, **sku_id_stock_filter).values('id', 'sku_id'). \
            annotate(total=Sum('sellerstock__quantity')).order_by(order_by)
    else:
        sku_id_stocks = sku_stocks.filter(**sku_id_stock_filter).values('id', 'sku_id'). \
            annotate(total=Sum('quantity')).order_by(order_by)
    val_dict = prepare_picklist_val_dict(user, sku_id_stocks,  is_seller_order, add_mrp_filter)

    if not seller_order:
        order_check_quantity = float(order.quantity)
    else:
        order_check_quantity = float(seller_order.quantity)
    members = {order.sku: order_check_quantity}
    seller_pick_number = ''
    if order.sku.relation_type == 'combo' and not combo_allocate_stock:
        picklist_data['order_type'] = 'combo'
        members = OrderedDict()
        combo_data = sku_combos.filter(parent_sku_id=order.sku.id)
        for combo in combo_data:
            member_check_quantity = order_check_quantity * combo.quantity
            members[combo.member_sku] = member_check_quantity
            stock_detail, stock_quantity, sku_code = get_sku_stock(combo.member_sku, sku_stocks, user,
                                                                   val_dict, sku_id_stocks,
                                                                   add_mrp_filter=add_mrp_filter,
                                                                   needed_mrp_filter=needed_mrp_filter)
            if stock_quantity < float(member_check_quantity):
                if not no_stock_switch:
                    stock_status.append(str(combo.member_sku.sku_code))
                    members = {}
                    break

    for member, member_qty in members.iteritems():
        stock_detail, stock_quantity, sku_code = get_sku_stock(member, sku_stocks, user, val_dict,
                                                               sku_id_stocks, add_mrp_filter=add_mrp_filter,
                                                               needed_mrp_filter=needed_mrp_filter)
        if order.sku.relation_type == 'member':
            parent = sku_combos.filter(member_sku_id=member.id).filter(relation_type='member')
            stock_detail1, stock_quantity1, sku_code = get_sku_stock(parent[0].parent_sku, sku_stocks,
                                                                     user, val_dict, sku_id_stocks)
            stock_detail = list(chain(stock_detail, stock_detail1))
            stock_quantity += stock_quantity1
        elif order.sku.relation_type == 'combo' and not combo_allocate_stock:
            stock_detail, stock_quantity, sku_code = get_sku_stock(member, sku_stocks, user, val_dict,
                                                                   sku_id_stocks)

        order_quantity = member_qty
        if stock_quantity < float(order_quantity):
            is_seller_stock_updated = False
            if seller_order:
                src_stocks = temp_sku_stocks.filter(sellerstock__seller__seller_id=1, **sku_id_stock_filter)
                if src_stocks:
                    src_sku_id_stocks = src_stocks.values('id', 'sku_id').annotate(total=Sum('quantity')).\
                                                                                    order_by(order_by)
                    src_val_dict = prepare_picklist_val_dict(user, src_sku_id_stocks,
                                                             is_seller_order, add_mrp_filter)
                    src_stock_detail, src_stock_quantity, src_sku_code = get_sku_stock(member, src_stocks,
                                                                                       user, src_val_dict,
                                                                                       src_sku_id_stocks)
                    total_sellers_qty = src_stock_quantity + stock_quantity
                    sellers_diff_qty = order_quantity - stock_quantity
                    if sellers_diff_qty <= 0:
                        log.info("Found the sellers quantity difference")
                        continue
                    if total_sellers_qty >= float(order_quantity):
                        source_seller = src_stocks[0].sellerstock_set.filter()[0].seller
                        src_sku_id = src_stock_detail[0].sku_id
                        update_stocks_data(src_stocks, sellers_diff_qty, None,
                                           sellers_diff_qty, user, [src_stocks[0].location], src_sku_id,
                                           src_seller_id=source_seller.id, dest_seller_id=seller_order.seller_id,
                                           receipt_type='auto seller-seller transfer', receipt_number=receipt_number)
                        trans_id = get_max_seller_transfer_id(user)
                        seller_transfer = SellerTransfer.objects.create(source_seller_id=source_seller.id,
                                                                        dest_seller_id=seller_order.seller.id,
                                                                        transact_id=trans_id,
                                                                        transact_type='stock_transfer',
                                                                        creation_date=datetime.datetime.now())
                        seller_st_dict = {'seller_transfer_id': trans_id, 'sku_id': src_sku_id,
                                          'source_location_id': src_stocks[0].location_id,
                                          'dest_location_id': src_stocks[0].location_id}
                        SellerStockTransfer.objects.create(**seller_st_dict)
                        is_seller_stock_updated = True

            if not is_seller_stock_updated:
                continue

        stock_diff = 0

        # Marketplace model suggestions based on Zone Marketplace mapping
        if is_marketplace_model:
            zone_map_ids = all_zone_mappings.filter(marketplace=order.marketplace).values_list('zone_id', flat=True)
            rem_zone_map_ids = all_zone_mappings.exclude(zone_id__in=zone_map_ids).values_list('zone_id', flat=True)
            all_zone_map_ids = zone_map_ids | rem_zone_map_ids
            stock_zones1 = stock_detail.filter(location__zone_id__in=zone_map_ids).order_by(order_by)
            stock_zones2 = stock_detail.exclude(location__zone_id__in=all_zone_map_ids).order_by(order_by)
            stock_zones3 = stock_detail.filter(location__zone_id__in=rem_zone_map_ids).order_by(order_by)
            stock_detail = stock_zones1.union(stock_zones2, stock_zones3)
        elif fefo_enabled:
            stock_detail1 = stock_detail.filter(batch_detail__expiry_date__isnull=False).\
                                            order_by('batch_detail__expiry_date')
            stock_detail2 = stock_detail.exclude(batch_detail__expiry_date__isnull=False).\
                                            order_by(order_by)
            stock_detail = list(chain(stock_detail1, stock_detail2))
        if seller_order and seller_order.order_status == 'DELIVERY_RESCHEDULED':
            rto_stocks = stock_detail.filter(location__zone__zone='RTO_ZONE')
            stock_detail = list(chain(rto_stocks, stock_detail))
        for stock in stock_detail:
            stock_count, stock_diff = get_stock_count(order, stock, stock_diff, user, order_quantity)
            if not stock_count:
                continue

            picklist_data['reserved_quantity'] = 0
            picklist_data['picked_quantity'] = stock_count
            picklist_data['stock_id'] = stock.id
            picklist_data['order_id'] = order.id
            picklist_data['status'] = 'picked'
            new_picklist = Picklist(**picklist_data)
            new_picklist.save()
            if seller_order:
                SellerOrderDetail.objects.create(seller_order_id=seller_order.id, picklist_id=new_picklist.id,
                                                 quantity=new_picklist.picked_quantity,
                                                 reserved=0,
                                                 creation_date=datetime.datetime.now())

            picklist_loc_data = {'picklist_id': new_picklist.id, 'status': 0, 'quantity': stock_count,
                                 'creation_date': datetime.datetime.now(),
                                 'stock_id': new_picklist.stock_id, 'reserved': 0}
            pick_loc = PicklistLocation(**picklist_loc_data)
            pick_loc.save()
            stock.quantity = stock.quantity - stock_count
            stock.save()
            if seller_order:
                change_seller_stock(seller_order.seller_id, stock, user, stock_count, 'dec')
            save_sku_stats(user, stock.sku_id, new_picklist.id, 'picklist', stock_count, stock)
            if not seller_pick_number:
                seller_pick_number = get_seller_pick_id(new_picklist, user)
            if seller_order:
                SellerOrderSummary.objects.create(picklist_id=new_picklist.id, pick_number=seller_pick_number,
                                                  quantity=stock_count, seller_order_id=seller_order.id,
                                                  creation_date=datetime.datetime.now(),
                                                  financial_year=financial_year)
            if not stock_diff:
                if seller_order:
                    seller_order.status = 0
                    seller_order.save()
                    sell_order = SellerOrder.objects.filter(order_id=order.id, status=1)
                    if not sell_order:
                        order.status = 0
                        order.save()
                else:
                    order.status = 0
                    order.save()
                break

        order.save()


class Command(BaseCommand):
    """
    Auto Sellable Suggestions
    """
    help = "Auto Confirm Picklists"

    def handle(self, *args, **options):
        self.stdout.write("Started Updating")
        users = User.objects.filter(username__in=['NOIDA02'])
        log.info(str(datetime.datetime.now()))
        for user in users:
            picklist_exclude_zones = get_exclude_zones(user)
            receipt_number = get_stock_receipt_number(user)
            open_orders = OrderDetail.objects.prefetch_related('sku').\
                                            filter(user=user.id, status=1, sellerorder__isnull=False,
                                                                             quantity__gt=0, sellerorder__seller__seller_id=2)
            picklist_number = ''
            if open_orders.exists():
                picklist_number = get_picklist_number(user)
            switch_vals = {'marketplace_model': get_misc_value('marketplace_model', user.id),
                           'fifo_switch': get_misc_value('fifo_switch', user.id),
                           'no_stock_switch': get_misc_value('no_stock_switch', user.id),
                           'combo_allocate_stock': get_misc_value('combo_allocate_stock', user.id)}
            sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(
                parent_sku__user=user.id)
            sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(
                location__zone__zone__in=picklist_exclude_zones).filter(sku__user=user.id, quantity__gt=0)
            if switch_vals['fifo_switch'] == 'true':
                stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by(
                    'receipt_date')
                # data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
                stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
            else:
                stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by(
                    'location_id__pick_sequence')
                stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by(
                    'receipt_date')
            all_sku_stocks = stock_detail1 | stock_detail2
            for open_order in open_orders:
                seller_orders = open_order.sellerorder_set.filter()
                if seller_orders:
                    for seller_order in seller_orders:
                        sku_stocks = all_sku_stocks
                        #sku_stocks = all_sku_stocks.filter(sellerstock__seller_id=seller_order.seller_id)
                        execute_picklist_confirm_process(seller_order, picklist_number, user, sku_combos,
                                                         sku_stocks, switch_vals, receipt_number, is_seller_order=True)
                else:
                    log.info("Not Auto Processing %s" % str(open_order.original_order_id))
                    #execute_picklist_confirm_process(seller_order, picklist_number, user, sku_combos,
                    #                                 sku_stocks, switch_vals, is_seller_order=False)
            if picklist_number:
                check_picklist_number_created(user, picklist_number + 1)
        log.info(str(datetime.datetime.now()))
        self.stdout.write("Updating Completed")
