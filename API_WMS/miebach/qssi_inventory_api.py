activate_this = 'setup/MIEBACH/bin/activate_this.py'
execfile(activate_this, dict(__file__ = activate_this))
import os
import sys

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
                    for item in warehouse["Result"]["InventoryStatus"]:
                        sku_id = item["SKUId"]
                        if sku_id[-3:]=="-TU":
                            sku_id = sku_id[:-3]
                            if sku_id in stock_dict:
                                stock_dict[sku_id] += int(item['Inventory'])
                            else:
                                stock_dict[sku_id] = int(item['Inventory'])
                            wait_on_qc = [v for d in item['OnHoldDetails'] for k, v in d.items()
                                          if k == 'WAITONQC']
                            if wait_on_qc:
                                if int(wait_on_qc[0]):
                                    log.info("Wait ON QC Value %s for SKU %s" %(sku_id, wait_on_qc))
                                stock_dict[sku_id] += int(wait_on_qc[0])
                        else:
                            if sku_id in stock_dict:
                                stock_dict[sku_id] += int(item['FG'])
                            else:
                                stock_dict[sku_id] = int(item['FG'])

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
    print "Inventory Updated"
    return "Success"

if __name__ == '__main__':
    company_name = sys.argv[1]
    update_inventory(company_name)
