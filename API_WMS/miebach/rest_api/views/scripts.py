from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.encoding import smart_str
import copy
import json
import time
from itertools import chain
from django.db.models import Q, F
from collections import OrderedDict
from django.contrib.auth import authenticate
from django.contrib import auth
from miebach_admin.models import *
# from miebach_admin.choices import *
from common import *
# from masters import *
# from miebach_utils import *
from django.core import serializers
import csv
# from sync_sku import *
from outbound import get_syncedusers_mapped_sku
from rest_api.views.excel_operations import write_excel_col, get_excel_variables
from rest_api.views.common import create_user_wh
from inbound_common_operations import *
from stockone_integrations.views import Integrations
from rest_api.views.inbound import confirm_grn
from miebach.celery import app

log = init_logger('logs/scripts.log')

def upload_po_data(file_location):
    import datetime
    import pandas as pd
    from common import get_user_prefix_incremental, get_sku_ean_list
    from rest_api.views.inbound import netsuite_po
    # file_location = "Upload in STOCKONE_Materials PO_01.04.2020 to 31.07.2020.xlsx"
    df = pd.read_excel(file_location, header=1)
    data= df.groupby('PO No').apply(lambda x: x.to_dict(orient='r')).to_dict()
    for key, value in data.iteritems():
        sku_code = value[0]['StockOne SKU Code']
        user=''
        try:
            user=UserProfile.objects.get(stockone_code=value[0]['StockOne Plant ID']).user
        except  Exception as e:
            print(e, "\nplant_id:", value[0]['StockOne Plant ID'], "po_number", key, "sku_code", sku_code)
            # log.info('PO Upload failed for %s and params are %s and error statement is %s' % (str(key), str(value), str(e)))
            pass
        if not user:
            try:
                user=UserProfile.objects.get(stockone_code="0"+str(value[0]['StockOne Plant ID'])).user
            except  Exception as e:
                log.info('PO Upload failed for %s and params are %s and error statement is %s' % (str(key), str(value), str(e)))
                continue
        try:
            po_id, prefix, full_po_number, check_prefix, inc_status = get_user_prefix_incremental(user, 'po_prefix', sku_code)
            if inc_status:
                continue
        except Exception as e:
            log.info('PO Upload failed for %s and params are %s and error statement is %s' % (str(key), str(value), str(e)))
            continue
        flag=True
        for row in value:
            if row['StockOne SKU Code']:
                sku_id = SKUMaster.objects.filter(wms_code=row['StockOne SKU Code'].upper(), user=user.id)
                if not row['Pending Qty'] or not sku_id:
                    log.info('PO Upload failed for %s and params are %s and PO error is PO QTY or sku_code is empty' % (str(key), str(value)))
                    flag= False
                    break
                try:
                    supplier = SupplierMaster.objects.get(user=user.id, supplier_id__contains=row['Vendor Code'])
                except Exception as e:
                    log.info('PO Upload failed for %s and params are %s and error statement is %s' % (str(key), str(value), str(e)))
                    flag= False
                    break
            else:
                log.info('PO Upload failed for %s and params are %s and PO error is StockOne SKU Code or StockOne Plant ID is empty' % (str(key), str(value)))
                flag= False
                break
        po_data = {'open_po_id': '', 'status': '', 'received_quantity': 0}
        product_category="Kits&Consumables"
        if flag==True:
            log.info("PO upload started for PO_number =%s and data = " % str(key),str(value))
            for row in value:
                po_suggestions={'supplier_id': '', 'sku_id': '', 'order_quantity': '', 'order_type': 'SR', 'price': 0,
                           'status': 1}
                sku_id = SKUMaster.objects.filter(wms_code=row['StockOne SKU Code'].upper(), user=user.id)
                ean_number = ''
                if sku_id:
                    sku= sku_id[0]
                    try:
                        if sku.assetmaster:
                            product_category="Services"
                    except:
                        pass
                    try:
                        if sku.servicemaster:
                            product_category="Assets"
                    except:
                        pass
                    try:
                        if sku.otheritemsmaster:
                            product_category="OtherItems"
                    except:
                        pass
                    eans = get_sku_ean_list(sku_id[0])
                    if eans:
                        ean_number = eans[0]
                supplier = SupplierMaster.objects.get(user=user.id, supplier_id__contains=row['Vendor Code'])
                price = row['Unit Price']
                if not price:
                    price = 0
                po_suggestions['sku_id'] = sku_id[0].id
                po_suggestions['supplier_id'] = supplier.id
                po_suggestions['order_quantity'] = row['Pending Qty']
                # po_suggestions['po_name'] = value['po_name']
                # po_suggestions['supplier_code'] = value['supplier_code']
                po_suggestions['price'] = float(price)
                po_suggestions['status'] = 'Manual'
                # po_suggestions['remarks'] = value['remarks']
                po_suggestions['measurement_unit'] = "UNITS"
                # po_suggestions['mrp'] = float(mrp)
                po_suggestions['sgst_tax'] = row['SGST']*100
                po_suggestions['cgst_tax'] = row['CGST']*100
                po_suggestions['igst_tax'] = row['IGST']*100
                utc_tz=timezone("UTC")
                po_date_time =utc_tz.localize(datetime.datetime.strptime(row["PO date"], '%d.%m.%Y'))
                data1 = OpenPO(**po_suggestions)
                data1.save()
                data1.creation_date= po_date_time
                data1.updation_date= po_date_time
                data1.save()
                purchase_order = OpenPO.objects.get(id=data1.id, sku__user=user.id)
                sup_id = purchase_order.id
                supplier = purchase_order.supplier_id
                po_data['open_po_id'] = sup_id
                po_data['order_id'] = int(po_id)
                po_data['prefix'] = prefix
                po_data['po_number'] = str(key)
                order = PurchaseOrder(**po_data)
                order.save()
                order.creation_date= po_date_time
                order.updation_date= po_date_time
                order.po_date= po_date_time
                order.save()
            po_date_time =datetime.strptime(value[0]["PO date"], '%d.%m.%Y')
            delivery_date= po_date_time.strftime('%d-%m-%Y')
            data_dict={'terms_condition': '',"delivery_date": delivery_date, 'ship_to_address':""}
            try:
                netsuite_po(int(po_id), user, "open_po", data_dict, str(key), product_category, None, "")
            except Exception as e:
                log.info("PO netsuite_exception =%s and error statement is  = %s" % str(key),str(e))
                pass
def zone_location_script():
    from miebach_admin.models import *
    from rest_api.views.common import get_related_users_filters
    main_user = User.objects.get(username='mhl_admin')
    dept_users = get_related_users_filters(main_user.id, warehouse_types=['STORE', 'SUB_STORE', 'ST_HUB', 'DEPT'])
    zones_list_obj= ZoneMaster.objects.filter(user=main_user.id)
    for user in dept_users:
        for zone_row in zones_list_obj:
            check_zone= ZoneMaster.objects.filter(user=user.id, zone=zone_row.zone)
            if not check_zone:
                zone_dict_data= {"user": user.id, "zone": zone_row.zone}
                zone_obj= ZoneMaster(**zone_dict_data)
                zone_obj.save()
                location_obj= LocationMaster.objects.filter(zone=zone_row.id)
                for location_row in location_obj:
                    check_location= LocationMaster.objects.filter(zone=zone_obj.id, location=location_row.location)
                    if not check_location:
                        zone_id = zone_obj.id
                        location_dict={ "zone_id": zone_id,
                                        "filled_capacity": 0.0,
                                        "location": location_row.location,
                                        "max_capacity": location_row.max_capacity,
                                        "lock_status": '',
                                        "filled_capacity":location_row.filled_capacity,
                                        "pallet_capacity": location_row.pallet_capacity,
                                        "pick_sequence": location_row.pick_sequence,
                                        "fill_sequence": location_row.fill_sequence,
                                        "pallet_filled": location_row.pallet_filled
                                    }
                        location_obj1=LocationMaster(**location_dict)
                        location_obj1.save()
            else:
                location_obj= LocationMaster.objects.filter(zone=zone_row.id)
                for location_row in location_obj:
                    check_location= LocationMaster.objects.filter(zone=check_zone[0].id, location=location_row.location)
                    if not check_location:
                        zone_id = check_zone[0].id
                        location_dict={ "zone_id": zone_id,
                                        "filled_capacity": 0.0,
                                        "location": location_row.location,
                                        "max_capacity": location_row.max_capacity,
                                        "lock_status": '',
                                        "filled_capacity":location_row.filled_capacity,
                                        "pallet_capacity": location_row.pallet_capacity,
                                        "pick_sequence": location_row.pick_sequence,
                                        "fill_sequence": location_row.fill_sequence,
                                        "pallet_filled": location_row.pallet_filled
                                    }
                        location_obj1=LocationMaster(**location_dict)
                        location_obj1.save()
