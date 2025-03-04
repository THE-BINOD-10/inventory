activate_this = 'setup/MIEBACH/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
import os
import sys
import math

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()

from miebach_admin.models import *
from rest_api.views.common import *
from rest_api.views.utils import *
log = init_logger('logs/qssi_stock_check.log')

# def asn_stock_details(user, sku_code, order_flag=True):
#     # ASN Stock Related to SM
#     # today_filter = datetime.datetime.today()
#     # hundred_day_filter = today_filter + datetime.timedelta(days=100)
#     ints_filters = {'quantity__gt': 0, 'sku__user': user.id, 'sku__sku_code': sku_code}
#     asn_qs = ASNStockDetail.objects.filter(**ints_filters)
#     #intr_obj_100days_qs = asn_qs.filter(Q(arriving_date__lte=hundred_day_filter) | Q(asn_po_num='NON_KITTED_STOCK'))
#     intr_obj_100days_ids = asn_qs.values_list('id', flat=True)
#     asnres_det_qs = ASNReserveDetail.objects.filter(asnstock__in=intr_obj_100days_ids)
#     if order_flag:
#         asn_res_100days_qs = asnres_det_qs.filter(orderdetail__isnull=False)  # Reserved Quantity
#     else:
#         #asn_res_100days_qs = asnres_det_qs.filter(enquirydetail__isnull=False, enquirydetail__warehouse_level=3)
#         asn_res_100days_qs = asnres_det_qs.filter(enquirydetail__isnull=False)
#     asn_res_100days_qty = dict(asn_res_100days_qs.values_list('asnstock__sku__sku_code').
#                                annotate(in_res=Sum('reserved_qty')))
#     enq_ids = asn_res_100days_qs.values_list('enquirydetail_id', flat=True)
#     partial_blocked = dict(EnquiredSku.objects.filter(id__in=enq_ids, warehouse_level=1).values_list('sku__sku_code').annotate(tot_qty=Sum('quantity')))
#     asn_res_stock = asn_res_100days_qty.get(sku_code, 0)
#     l3_res_stock = asn_res_stock + partial_blocked.get(sku_code, 0)
#     return l3_res_stock


def get_asn_res_stock(asn_enq_obj):
    l3_res_stock = 0
    enq_qs = EnquiredSku.objects.filter(id=asn_enq_obj.enquirydetail_id)
    if enq_qs.exists():
        enq_qty = enq_qs[0].quantity
        enq_level = enq_qs[0].warehouse_level
        if enq_level == 1:
            l3_res_stock = enq_qty + asn_enq_obj.reserved_qty
        else:
            l3_res_stock = enq_qty
    return l3_res_stock


def get_wh_open_stock(wh, sku_code):
    total_stock = StockDetail.objects.filter(sku__user=wh.id,
                                             quantity__gt=0,
                                             sku__sku_code=sku_code).only('sku__sku_code', 'quantity').values_list(
        'sku__sku_code').distinct().annotate(in_stock=Sum('quantity'))
    res_stock = PicklistLocation.objects.filter(stock__sku__user=wh.id,
                                                status=1,
                                                stock__sku__sku_code=sku_code).only(
        'stock__sku__sku_code', 'reserved').values_list('stock__sku__sku_code').distinct().annotate(
        in_reserved=Sum('reserved'))
    asn_blocked_ids = ASNReserveDetail.objects.filter(enquirydetail__sku__user=wh.id,
                                                      enquirydetail__sku__sku_code=sku_code,
                                                      enquirydetail__isnull=False,
                                                      enquirydetail__warehouse_level=3).values_list('enquirydetail_id',
                                                                                               flat=True)
    blocked_stock = EnquiredSku.objects.filter(sku__user=wh.id, sku__sku_code=sku_code).exclude(id__in=asn_blocked_ids).filter(
        ~Q(enquiry__extend_status='rejected')).only('sku__sku_code', 'quantity').values_list('sku__sku_code').annotate(
        tot_qty=Sum('quantity'))

    ints_filters = {'quantity__gt': 0, 'sku__user': wh.id, 'status': 'open'}
    asn_qs = ASNStockDetail.objects.filter(**ints_filters)
    non_kitted_stock = asn_qs.filter(asn_po_num='NON_KITTED_STOCK', sku__sku_code=sku_code).only('sku__sku_code', 'quantity').values_list('sku__sku_code').annotate(non_kitted_qty=Sum('quantity'))
    total_stock = dict(total_stock).get(sku_code, 0)
    res_stock = dict(res_stock).get(sku_code, 0)
    blocked_stock = dict(blocked_stock).get(sku_code, 0)
    nk_stock = dict(non_kitted_stock).get(sku_code, 0)
    wh_open_stock = total_stock - res_stock - blocked_stock - nk_stock
    return wh_open_stock


def update_asn_res_stock(order_obj, l3_res_stock):
    ASNReserveDetail.objects.filter(orderdetail=order_obj).update(reserved_qty=l3_res_stock)


def calc_update_inventory(resp, user):
    if resp.get("Status", "").lower() == "success":
        for warehouse in resp["Warehouses"]:
            if warehouse["WarehouseId"] == user.username:
                location_master = LocationMaster.objects.filter(zone__zone="DEFAULT", zone__user=user.id)
                if not location_master:
                    continue
                location_id = location_master[0].id
                stock_dict = {}
                asn_stock_map = {}
                inventory_values = {}
                for item in warehouse["Result"]["InventoryStatus"]:
                    sku_id = item["SKUId"]
                    actual_sku_id = sku_id
                    if sku_id[-3:] == "-TU":
                        sku_id = sku_id[:-3]
                        if sku_id in stock_dict:
                            stock_dict[sku_id] += int(item['Inventory'])
                        else:
                            stock_dict[sku_id] = int(item['Inventory'])
                        if sku_id not in inventory_values:
                            inventory_values[sku_id] = {}
                        inventory_values[sku_id]['TU_INVENTORY'] = item['Inventory']
                        expected_items = item['Expected']
                        if not expected_items:
                            expected_items = []
                        if isinstance(expected_items, list):
                            asn_stock_map.setdefault(sku_id, []).extend(expected_items)
                        wait_on_qc = [v for d in item['OnHoldDetails'] for k, v in d.items() if k == 'WAITONQC']
                        if wait_on_qc:
                            if int(wait_on_qc[0]):
                                wait_on_qc = int(wait_on_qc[0]) * 90 / 100
                            else:
                                wait_on_qc = int(wait_on_qc[0])
                            log.info("Wait ON QC Value %s for SKU %s" % (actual_sku_id, wait_on_qc))
                            if sku_id in stock_dict:
                                stock_dict[sku_id] += int(wait_on_qc)
                            else:
                                stock_dict[sku_id] = int(wait_on_qc)
                    else:
                        if sku_id not in inventory_values:
                            inventory_values[sku_id] = {}
                        inventory_values[sku_id]['NORMAL_INVENTORY'] = item['Inventory']
                        if sku_id in stock_dict:
                            stock_dict[sku_id] += int(item['FG'])
                        else:
                            stock_dict[sku_id] = int(item['FG'])
                else:
                    for sku_id in inventory_values:
                        tu_inv = inventory_values[sku_id].get('TU_INVENTORY', 0)
                        nor_inv = inventory_values[sku_id].get('NORMAL_INVENTORY', 0)
                        inv_stock_diff = int(tu_inv) - int(nor_inv)
                        non_kitted_stock = max(inv_stock_diff, 0)
                        sku = SKUMaster.objects.filter(user=user.id, sku_code=sku_id)
                        if not sku: continue
                        sku = sku[0]
                        exist_nk_stock = ASNStockDetail.objects.filter(sku_id=sku.id, asn_po_num='NON_KITTED_STOCK')
                        exist_nk_open_stock = exist_nk_stock.filter(status='open')
                        exist_nk_closed_stock = exist_nk_stock.filter(status='closed')
                        if non_kitted_stock:
                            if exist_nk_open_stock:
                                exist_nk_open_stock = exist_nk_open_stock[0]
                                exist_nk_open_stock.quantity = non_kitted_stock
                                exist_nk_open_stock.save()
                            else:
                                ASNStockDetail.objects.create(asn_po_num='NON_KITTED_STOCK', sku_id=sku.id,
                                                              quantity=non_kitted_stock)
                        else:
                            exist_nk_closed_stock.delete()
                            exist_nk_open_stock.update(status='closed')

                for sku_id, inventory in stock_dict.iteritems():
                    sku = SKUMaster.objects.filter(user=user.id, sku_code=sku_id)
                    if sku:
                        sku = sku[0]
                        stock_detail = StockDetail.objects.filter(sku_id=sku.id)
                        if stock_detail:
                            stock_detail = stock_detail[0]
                            stock_detail.quantity = inventory
                            stock_detail.save()
                            log.info("Stock updated for user %s for sku %s, new stock is %s" %
                                     (user.username, str(sku.sku_code), str(inventory)))
                        else:
                            new_stock_dict = {"receipt_number": 1,
                                              "receipt_date": datetime.datetime.now(),
                                              "quantity": inventory, "status": 1, "sku_id": sku.id,
                                              "location_id": location_id}
                            StockDetail.objects.create(**new_stock_dict)
                            log.info("New stock created for user %s for sku %s" %
                                     (user.username, str(sku.sku_code)))
                        update_asn_to_stock(user, sku)
                for sku_id, asn_inv in asn_stock_map.iteritems():
                    sku = SKUMaster.objects.filter(user=user.id, sku_code=sku_id)
                    if sku:
                        sku = sku[0]
                        existing_asn = ASNStockDetail.objects.filter(sku_id=sku.id).exclude(
                            asn_po_num='NON_KITTED_STOCK')
                        db_po_nums = existing_asn.values_list('asn_po_num', flat=True)
                        api_po_nums = [i['PO'] for i in asn_inv]
                        expired_po_nums = set(db_po_nums) - set(api_po_nums)
                        if expired_po_nums:
                            log.info('L3 Stock either delivered or cancelled. SKU: %s, POs: %s'
                                     % (sku.sku_code, expired_po_nums))
                            existing_asn.filter(asn_po_num__in=expired_po_nums).update(status='closed')
                        for asn_stock in asn_inv:
                            po = asn_stock['PO']
                            expected_time = asn_stock['By']
                            if expected_time == 'Unknown':
                                continue
                            arriving_date = datetime.datetime.strptime(asn_stock['By'], '%d-%b-%Y')
                            quantity = int(asn_stock['Qty'])
                            qc_quantity = int(math.ceil(quantity * 90.0 / 100))
                            if qc_quantity <= 0:
                                continue
                            asn_stock_detail = ASNStockDetail.objects.filter(sku_id=sku.id, asn_po_num=po)
                            if asn_stock_detail:
                                asn_stock_detail = asn_stock_detail[0]
                                asn_stock_detail.quantity = qc_quantity
                                asn_stock_detail.arriving_date = arriving_date
                                asn_stock_detail.status = 'open'
                                asn_stock_detail.save()
                            else:
                                ASNStockDetail.objects.create(asn_po_num=po, sku_id=sku.id,
                                                              quantity=qc_quantity,
                                                              arriving_date=arriving_date)
                                log.info('New ASN Stock Created for User %s and SKU %s' %
                                         (user.username, str(sku.sku_code)))


def update_asn_to_stock(wh, sku_obj):
    # from rest_api.views.outbound import check_stocks
    sku_code = sku_obj.sku_code
    #wh_open_stock = get_wh_open_stock(wh, sku_code)

    # ord_ids = ASNReserveDetail.objects.filter(orderdetail__user=wh.id, orderdetail__sku__sku_code=sku_code,
    #                                 orderdetail__status=1, reserved_qty__gt=0).values_list('orderdetail_id', flat=True)
    # order_qs = OrderDetail.objects.filter(id__in=ord_ids).order_by('id')
    # if order_qs:
    #     order_obj = order_qs[0]
    #     l3_res_stock = asn_stock_details(wh, sku_code)
    #     picklist_qty_map = {}
    #
    #     if wh_open_stock > 0 and l3_res_stock > 0:
    #         wh_res_stock = min(wh_open_stock, l3_res_stock)
    #         l3_res_stock = l3_res_stock - min(wh_open_stock, l3_res_stock)
    #         picklist_qty_map[sku_obj] = wh_res_stock
    #         # Generate PickList functionality
    #         status_msg = check_stocks(picklist_qty_map, wh, 'false', order_obj, continue_flag=False)
    #         #update_asn_res_stock(order_obj, l3_res_stock)
    #         asnres_qs = ASNReserveDetail.objects.filter(orderdetail_id=order_obj.id)
    #         if l3_res_stock > 0:
    #             asnres_qs.update(reserved_qty=l3_res_stock)
    #         else:
    #             asnres_qs.delete()
    asn_enq_objs = ASNReserveDetail.objects.filter(enquirydetail__sku__user=wh.id, enquirydetail__sku__sku_code=sku_code,
                                              reserved_qty__gt=0).order_by('creation_date')
    wh_open_stock = get_wh_open_stock(wh, sku_code)
    for asn_enq_obj in asn_enq_objs:
        asn_res_qty = 0
        #l3_res_stock = get_asn_res_stock(asn_enq_obj)
        l3_res_stock = asn_enq_obj.reserved_qty
        if wh_open_stock > 0 and l3_res_stock > 0:
            wh_res_stock = min(wh_open_stock, l3_res_stock)
            log.info("EnquiredSku details %s" %asn_enq_obj.enquirydetail.__dict__)
            log.info("EnquiredSku id %s of sku %s with quantity %s moved from L3 to L1." %(asn_enq_obj.enquirydetail_id, sku_code, wh_res_stock))
            if asn_enq_obj.enquirydetail.warehouse_level == 3:
                asn_enq_obj.enquirydetail.quantity=wh_res_stock
                asn_enq_obj.enquirydetail.warehouse_level=1
                asn_enq_obj.enquirydetail.save()
            else:
                partial_l1_qty = asn_enq_obj.enquirydetail.quantity
                asn_enq_obj.enquirydetail.quantity = partial_l1_qty + wh_res_stock
                asn_enq_obj.enquirydetail.save()
            if wh_open_stock > 0 and wh_open_stock < l3_res_stock:
                asn_res_qty = l3_res_stock - wh_open_stock
            if asn_res_qty:
                log.info("ASNReserveDetail %s object reseved quantity %s updated" %(asn_enq_obj.__dict__, l3_res_stock))
                asn_enq_obj.reserved_qty=asn_res_qty
                asn_enq_obj.save()
            else:
                log.info("ASNReserveDetail %s object got removed" %(asn_enq_obj.__dict__))
                asn_enq_obj.delete()
            wh_open_stock = wh_open_stock - wh_res_stock
        else:
            break


def update_inventory(company_name):
    integration_users = Integrations.objects.filter(name=company_name).values_list('user', flat=True)
    resp = {}
    for user_id in integration_users:
        user = User.objects.get(id=user_id)
        data = {"SKUIds": []}
        if not resp:
            resp = get_inventory(data, user)
        calc_update_inventory(resp, user)
    return "Success"


if __name__ == '__main__':
    company_name = sys.argv[1]
    update_inventory(company_name)
