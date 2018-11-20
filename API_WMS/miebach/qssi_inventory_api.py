activate_this = 'setup/MIEBACH/bin/activate_this.py'
execfile(activate_this, dict(__file__ = activate_this))
import os
import sys
from math import floor

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()

from miebach_admin.models import *
from rest_api.views.common import *
from rest_api.views.utils import *
log = init_logger('logs/qssi_stock_check.log')

def update_inventory(company_name):
    integration_users = Integrations.objects.filter(name = company_name).values_list('user', flat=True)
    for user_id in integration_users:
        user = User.objects.get(id = user_id)
        data = {"SKUIds": []}
        #data["SKUIds"].append({"WarehouseId": user.username})
        resp = get_inventory(data, user)
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
                        if sku_id[-3:]=="-TU":
                            sku_id = sku_id[:-3]
                            if sku_id not in inventory_values:
                                inventory_values[sku_id] = {}
                            inventory_values[sku_id]['TU_INVENTORY'] = item['Inventory']
                            expected_items = item['Expected']
                            if isinstance(expected_items, list) and expected_items:
                                asn_stock_map.setdefault(sku_id, []).extend(expected_items)
                            wait_on_qc = [v for d in item['OnHoldDetails'] for k, v in d.items() if k == 'WAITONQC']
                            if wait_on_qc:
                                if int(wait_on_qc[0]):
                                    log.info("Wait ON QC Value %s for SKU %s" % (actual_sku_id, wait_on_qc))
                                if sku_id in stock_dict:
                                    stock_dict[sku_id] += int(wait_on_qc[0])
                                else:
                                    stock_dict[sku_id] = int(wait_on_qc[0])
                        else:
                            if sku_id not in inventory_values:
                                inventory_values[sku_id] = {}
                            inventory_values[sku_id]['NORMAL_INVENTORY'] = item['Inventory']
                            if sku_id in stock_dict:
                                stock_dict[sku_id] += int(item['Inventory'])
                            else:
                                stock_dict[sku_id] = int(item['Inventory'])
                    else:
                        for sku_id in inventory_values:
                            tu_inv = inventory_values[sku_id].get('TU_INVENTORY', 0)
                            nor_inv = inventory_values[sku_id].get('NORMAL_INVENTORY', 0)
                            inv_stock_diff = int(tu_inv) - int(nor_inv)
                            non_kitted_stock = max(inv_stock_diff, 0)
                            if non_kitted_stock:
                                sku = SKUMaster.objects.filter(user=user_id, sku_code=sku_id)
                                if sku:
                                    sku = sku[0]
                                    asn_obj = ASNStockDetail.objects.filter(sku_id=sku.id, asn_po_num='NON_KITTED_STOCK')
                                    if asn_obj:
                                        asn_obj = asn_obj[0]
                                        asn_obj.quantity = non_kitted_stock
                                        asn_obj.save()
                                    else:
                                        ASNStockDetail.objects.create(asn_po_num='NON_KITTED_STOCK', sku_id=sku.id,
                                                                      quantity=non_kitted_stock)

                    for sku_id, inventory in stock_dict.iteritems():
                        sku = SKUMaster.objects.filter(user = user_id, sku_code = sku_id)
                        if sku:
                            sku = sku[0]
                            stock_detail = StockDetail.objects.filter(sku_id = sku.id)
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
                    for sku_id, asn_inv in asn_stock_map.iteritems():
                        sku = SKUMaster.objects.filter(user=user_id, sku_code=sku_id)
                        if sku:
                            sku = sku[0]
                            for asn_stock in asn_inv:
                                po = asn_stock['PO']
                                expected_time = asn_stock['By']
                                if expected_time == 'Unknown':
                                    continue
                                arriving_date = datetime.datetime.strptime(asn_stock['By'], '%d-%b-%Y')
                                quantity = int(asn_stock['Qty'])
                                qc_quantity = int(floor(quantity*95/100))
                                asn_stock_detail = ASNStockDetail.objects.filter(sku_id=sku.id, asn_po_num=po)
                                if asn_stock_detail:
                                    asn_stock_detail = asn_stock_detail[0]
                                    asn_stock_detail.quantity = qc_quantity
                                    asn_stock_detail.arriving_date = arriving_date
                                    asn_stock_detail.save()
                                else:
                                    ASNStockDetail.objects.create(asn_po_num=po, sku_id=sku.id,
                                                                  quantity=qc_quantity,
                                                                  arriving_date=arriving_date)
                                    log.info('New ASN Stock Created for User %s and SKU %s' %
                                             (user.username, str(sku.sku_code)))
    print "Inventory Updated"
    return "Success"

if __name__ == '__main__':
    company_name = sys.argv[1]
    update_inventory(company_name)
