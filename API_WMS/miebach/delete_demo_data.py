import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()
from miebach_admin.models import *
import datetime

delete_user = ''
def delete_user_demo_data(delete_user):
    delete_models_list = [ZoneMaster, SKUMaster, SellerMaster, SupplierMaster, OrderDetail, PalletDetail, Issues,
                          OrderShipment, CustomerMaster, SizeMaster,
                          SkuTypeMapping, SKUGroups, CategoryDiscount, SalesPersons, VendorMaster, Marketplaces, ProductionStages, OrdersAPI,
                          OrdersTrack, POTaxMaster]

    #delete_models_list = [SKUMaster]
    for delete_model in delete_models_list:
        delete_model.objects.filter(user=delete_user).delete()

    print 'success'

if delete_user:
    delete_user_demo_data(delete_user)

