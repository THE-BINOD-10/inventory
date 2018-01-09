activate_this = 'setup/MIEBACH/bin/activate_this.py'
execfile(activate_this, dict(__file__ = activate_this))
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()

from miebach_admin.models import *
from rest_api.views.common import *


def update_inventory(company_name):
    integration_users = Integrations.objects.filter(name = company_name).values_list('user', flat=True)
    for user_id in integration_users:
        user = User.objects.get(id = user_id)
        data = {"SKUIds": []}
        data["SKUIds"].append({"WarehouseId": user.username})
        resp = get_inventory(data, user)
        if resp["Status"].lower() == "success":
            for warehouse in resp["Warehouses"]:
                if warehouse["WarehouseId"] == user.username:
                    for item in warehouse["Result"]["InventoryStatus"]:
                        sku_id = item["SKUId"]
                        inventory = item["Inventory"]
                        sku = SKUMaster.objects.filter(user = user_id, sku_code = sku_id)
                        if sku:
                            sku = sku[0]
                            stock_detail = StockDetail.objects.filter(sku_id = sku.id)
                            if stock_detail:
                                stock_detail = stock_detail[0]
                                stock_detail.quantity = inventory
                                stock_detail.save()
    print "Inventory Updated"
    return "Success"

if __name__ == '__main__':
    company_name = sys.argv[1]
    update_inventory(company_name)
