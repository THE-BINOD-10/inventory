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
from rest_api.views.inbound_common_operations import *
log = init_logger('logs/final_batch_upload_PO_scripts.log')



def upload_po_data(file_location):
    import datetime
    import pandas as pd
    from rest_api.views.common import get_user_prefix_incremental, get_sku_ean_list
    from rest_api.views.inbound import netsuite_po
    # file_location = "/var/www/metropolis_prod/WMS_ANGULAR/API_WMS/miebach/"
    #  UserProfile.objects.get(stockone_code="33004")
    # SupplierMaster.objects.get(user=55, supplier_id__contains='LO2145A018').tin_number
    from pytz import timezone
    from django.forms.models import model_to_dict
    df = pd.read_excel(file_location, header=1)
    df = df.fillna('')
    data= df.groupby('PO No.'.strip()).apply(lambda x: x.to_dict(orient='r')).to_dict()
    count=1
    failed=0
    already_complted=0
    success_count=0
    for key, value in data.iteritems():
        sku_code = value[0]['Material code.1'].strip()
        print(sku_code)
        user=''
        user_profile_obj=UserProfile.objects.filter(stockone_code=value[0]['STOCKONE Plant code'])
        if user_profile_obj:
            user=user_profile_obj[0].user
        else:
            user_profile_obj=UserProfile.objects.filter(stockone_code="0"+str(value[0]['STOCKONE Plant code']))
            if user_profile_obj:
                user=user_profile_obj[0].user
            else:
                print('PO Upload failed for %s and params are %s and plantcode is %s' % (str(key), str(value), str(value[0]['STOCKONE Plant code'])))
                log.info('PO Upload failed for %s and params are %s and plant code is %s' % (str(key), str(value), str(value[0]['STOCKONE Plant code'])))
                continue
        print("\n plant_user",user)
        try:
            po_id, prefix, full_po_number, check_prefix, inc_status = get_user_prefix_incremental(user, 'po_prefix', sku_code)
            if inc_status:
                continue
        except Exception as e:
            print('PO Upload failed for %s and params are %s and error statement is %s' % (str(key), str(value), str(e)))
            log.info('PO Upload failed for %s and params are %s and error statement is %s' % (str(key), str(value), str(e)))
            continue
        flag=True
        check_po=False
        utc_tz=timezone("UTC")
        po_date_time =utc_tz.localize(datetime.datetime.strptime(value[0]["PO Date"], '%d.%m.%Y'))
        po_obj= PurchaseOrder.objects.filter(po_number=str(key))
        if po_obj:
            po_id=po_obj[0].order_id
            flag= True
            check_po= True
            po_obj.update(creation_date=po_date_time,updation_date=po_date_time, po_date= po_date_time)
            already_complted=already_complted+1
        f1_sku_product="Kits&Consumables"
        product_category_test=True
        # if "4000097443"== str(key):
        if flag:
            for index, row in enumerate(value):
                if row['Material code.1']:
                    sku_id = SKUMaster.objects.filter(wms_code=row['Material code.1'].upper().strip(), user=user.id)
                    if sku_id:
                        sku= sku_id[0]
                        if not sku.hsn_code:
                            log.info('PO Upload failed hsn code is not present for %s and params are %s and PO is %s' % (str(row[    'Material code.1']), str(value), str(key)))
                            flag= False
                            break
                        try:
                            if sku.assetmaster:
                                if index==0:
                                    f1_sku_product="Assets"
                                elif f1_sku_product!="Assets":
                                    product_category_test=False
                                    log.info('PO Upload failed SKU Category is different for %s and params are %s and PO is %s' % (str(row['Material code.1']), str(value), str(key)))
                                    break
                        except:
                            pass
                        try:
                            if sku.servicemaster:
                                if index==0:
                                    f1_sku_product="Services"
                                elif f1_sku_product!="Services":
                                    product_category_test=False
                                    log.info('PO Upload failed SKU Category is different for %s and params are %s and PO is %s' % (str(row['Material code.1']), str(value), str(key)))
                                    break
                        except:
                            pass
                        try:
                            if sku.otheritemsmaster:
                                if index==0:
                                    f1_sku_product="OtherItems"
                                elif f1_sku_product!="OtherItems":
                                    product_category_test=False
                                    log.info('PO Upload failed SKU Category is different for %s and params are %s and PO is %s' % (str(row['Material code.1']), str(value), str(key)))
                                    break
                        except:
                            pass
                    if not row['Pending PO Qty'] or not sku_id:
                        log.info('PO Upload failed for %s and params are %s and PO error is PO QTY or sku_code is empty' % (str(key), str(value)))
                        flag= False
                        break
                    if index >1:
                        break
                    supplier_obj = SupplierMaster.objects.filter(user=user.id, supplier_id__contains=str(row['Vendor Code']).strip())
                    if not supplier_obj:
                        log.info('PO Upload failed Beacause Vendor not present for %s and PO is %s and params are %s and error statement is %s' % (user.username, str(key), str(value), str(row['Vendor Code'])))
                        print('PO Upload failed Beacause Vendor not present for %s and PO is %s and params are %s and error statement is %s' % (user.username, str(key), str(value), str(row['Vendor Code'])))
                        ori_sup_obj= SupplierMaster.objects.filter(user=2,  supplier_id__contains=str(row['Vendor Code']).strip())
                        if ori_sup_obj:
                            log.info("need to create vendor\n\n")
                            ori_sup=model_to_dict(ori_sup_obj[0])
                            supp_id=ori_sup['id']
                            temp_suplier_id= ori_sup['id'].split('_')
                            del temp_suplier_id[0]
                            ori_sup["id"]= (str(user.id)+"_")+"_".join(temp_suplier_id)
                            ori_sup["user"]= user.id
                            obj=SupplierMaster(**ori_sup)
                            obj.save()
                            ori_pay=PaymentTerms.objects.filter(supplier=supp_id)
                            for pay in ori_pay:
                                temp_dict= { "supplier": obj, "payment_code": pay.payment_code, "payment_description": pay.payment_description}
                                payment_obj=PaymentTerms(**temp_dict)
                                payment_obj.save()
                        else:
                            print('PO Upload failed Beacause MHL admin vendor is not present for %s and params are %s and error statement is %s' % (str(key), str(value), str(row['Vendor Code'])))
                            log.info('PO Upload failed Beacause MHL admin vendor is not present for %s and params are %s and error statement is %s' % (str(key), str(value), str(row['Vendor Code'])))
                            flag= False
                            break
                else:
                    log.info('PO Upload failed for %s and params are %s and PO error is StockOne SKU Code or StockOne Plant ID is empty' % (str(key), str(value)))
                    flag= False
                    break
        po_data = {'open_po_id': '', 'status': '', 'received_quantity': 0}
        product_category=f1_sku_product
        # check_po=False
        # po_obj= PurchaseOrder.objects.filter(po_number=str(key))
        # if po_obj:
        #     po_id=po_obj[0].order_id
        #     check_po=True
        print(flag,"key",key, "f1_sku_product", f1_sku_product)
        if flag:
            log.info("PO upload started for PO_number %s and data %s" % (str(key),str(value)))
            print("PO upload started for PO_number =%s and data = " % str(key),str(value))
            for row in value:
                po_suggestions={'supplier_id': '', 'sku_id': '', 'order_quantity': '', 'order_type': 'SR', 'price': 0,
                           'status': 1}
                sku_id = SKUMaster.objects.filter(wms_code=row['Material code.1'].upper(), user=user.id)
                ean_number = ''
                if sku_id:
                    sku= sku_id[0]
                    eans = get_sku_ean_list(sku_id[0])
                    if eans:
                        ean_number = eans[0]
                if not check_po:
                    supplier_obj = SupplierMaster.objects.filter(user=user.id, supplier_id__contains=str(row['Vendor Code']).strip())
                    if supplier_obj:
                        supplier=supplier_obj[0]
                    price= 0
                    if row.get("Basic Amt",0):
                        if not row.get("Basic Amt",0)=="nan":
                            price = row['Basic Amt']
                    # else:
                    #     price = 0
                    po_suggestions['sku_id'] = sku_id[0].id
                    po_suggestions['supplier_id'] = supplier.id
                    po_suggestions['order_quantity'] = row['Pending PO Qty']
                    # po_suggestions['po_name'] = value['po_name']
                    # po_suggestions['supplier_code'] = value['supplier_code']
                    po_suggestions['price'] = float(price)
                    po_suggestions['status'] = 'Manual'
                    # po_suggestions['remarks'] = value['remarks']
                    po_suggestions['measurement_unit'] = "UNITS"
                    # po_suggestions['mrp'] = float(mrp)
                    if row.get("SGST",0):
                        if not row.get("SGST",0)=="nan":
                            po_suggestions['sgst_tax'] = row['SGST']
                    if row.get("CGST",0):
                        if not row.get("CGST",0)=="nan":
                            po_suggestions['cgst_tax'] = row['CGST']
                    if row.get("IGST",0):
                        if not row.get("IGST",0)=="nan":
                            po_suggestions['igst_tax'] = row['IGST']
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
                    # po_data['prefix'] = prefix
                    po_data['po_number'] = str(key)
                    order = PurchaseOrder(**po_data)
                    order.save()
                    order.creation_date= po_date_time
                    order.updation_date= po_date_time
                    order.po_date= po_date_time
                    order.save()
                    log.info("PO created Success stockone  PO Number= %s" % (str(key)))
                else:
                    break
                    log.info("PO already present in stockone PO Number= %s" % (str(key)))
            success_count= success_count+1
        else:
            failed=failed+1
        #print("total_count",len(data), "completed= ", count, "failed=",failed, "success_count=", success_count, "already_complted=", already_complted)
        #count=count+1
        #continue
        if not check_po:
            po_date_time =datetime.datetime.strptime(value[0]["PO Date"], '%d.%m.%Y')
            delivery_date= po_date_time.strftime('%d-%m-%Y')
            data_dict={'terms_condition': '',"delivery_date": delivery_date, 'ship_to_address':""}
            try:
                netsuite_po(int(po_id), user, "open_po", data_dict, str(key), product_category, None, "")
            except Exception as e:
                log.info("PO netsuite_exception =%s and error statement is  = %s" % str(key),str(e))
                pass
        print("total_count",len(data), "completed= ", count, "failed=",failed, "success_count=", success_count, "already_complted=", already_complted)
        count=count+1

def zone_location_script():
    from rest_api.views.common import get_related_users_filters
    main_user = User.objects.get(username='mhl_admin')
    # dept_users = get_related_users_filters(main_user.id, warehouse_types=['STORE', 'SUB_STORE', 'ST_HUB', 'DEPT'])
    dept_users = get_related_users_filters(main_user.id, warehouse_types=['DEPT'])
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
                    zone_id = zone_obj.id
                    location_dict={ "zone_id": zone_id,
                                    "location": location_row.location,
                                    "max_capacity": location_row.max_capacity,
                                    "lock_status": '',
                                    "filled_capacity":location_row.filled_capacity,
                                    "pallet_capacity": location_row.pallet_capacity,
                                    "pick_sequence": location_row.pick_sequence,
                                    "fill_sequence": location_row.fill_sequence,
                                    "pallet_filled": location_row.pallet_filled
                                }
                    if not check_location:
                        location_obj1=LocationMaster(**location_dict)
                        location_obj1.save()
                    else:
                        check_location.update(**location_dict)
            else:
                location_obj= LocationMaster.objects.filter(zone=zone_row.id)
                for location_row in location_obj:
                    check_location= LocationMaster.objects.filter(zone=check_zone[0].id, location=location_row.location)
                    zone_id = check_zone[0].id
                    location_dict={ "zone_id": zone_id,
                                    "location": location_row.location,
                                    "max_capacity": location_row.max_capacity,
                                    "lock_status": '',
                                    "filled_capacity":location_row.filled_capacity,
                                    "pallet_capacity": location_row.pallet_capacity,
                                    "pick_sequence": location_row.pick_sequence,
                                    "fill_sequence": location_row.fill_sequence,
                                    "pallet_filled": location_row.pallet_filled
                                }
                    if not check_location:
                        location_obj1=LocationMaster(**location_dict)
                        location_obj1.save()
                    else:
                        check_location.update(**location_dict)

def hsn_code_internal_id_script(file_location):
    import datetime
    import pandas as pd
    if file_location:
    # file_location="IndiaTaxHSNandSACcodesforGSTList521.csv"
        df = pd.read_csv(file_location, header=0)
        csv_data=df.to_dict('r')
        len(csv_data)
        tax_codes= TaxMaster.objects.filter(user=2).values("product_type").distinct()
        len(tax_codes)
        list_1=[]
        for row in tax_codes:
            test=True
            for row1 in csv_data:
                hsn_code= row1["HSN or SAC code"].split('\xc2\xa0')
                if row["product_type"]==row1["HSN or SAC code"]:
                    list_1.append({"hsn_code": row["product_type"], "internal_id": row1["Internal ID"]})
                    updated_data= TaxMaster.objects.filter(product_type=row["product_type"]).update(reference_id=row1["Internal ID"])
                    print(updated_data)
                    test=False
                    break
                elif str(row["product_type"]) == " "+str(hsn_code[-1]):
                    list_1.append({"hsn_code": row["product_type"], "internal_id": row1["Internal ID"]})
                    updated_data= TaxMaster.objects.filter(product_type=row["product_type"]).update(reference_id=row1["Internal ID"])
                    print(updated_data)
                    test=False
                    print(str(hsn_code[-1]), row["product_type"], row1)
                    break
            if test:
                hsn_lstrip=row["product_type"].lstrip()
                if not row["product_type"]==hsn_lstrip:
                    updated_data= TaxMaster.objects.filter(product_type=row["product_type"]).update(product_type=hsn_lstrip)
                    updated_data1= SKUMaster.objects.filter(hsn_code=row["product_type"]).update(hsn_code=hsn_lstrip)
                    print("updated records",updated_data, updated_data1)
                print("hsn_code not Present",{"hsn_code": row["product_type"]})
    else:
        print("file_locatio is empty")


def inventory_upload(file_location):
    from miebach_admin.models import *
    import datetime
    import pandas as pd
    from rest_api.views.common import create_update_batch_data,add_ean_weight_to_batch_detail
    from pytz import timezone
    df = pd.read_excel(file_location, header=0)
    df = df.fillna('')
    csv_data=df.to_dict('r')
    total_count=len(csv_data)
    failed_count=0
    completed_count=0
    for row in csv_data:
        try:
            user=""
            sku_code=""
            receipt_type= "Opening Stock"
            if row.get('WH username', None):
                user_obj= User.objects.filter(username=str(row['WH username']).strip())
                if user_obj:
                    user= user_obj[0]
                else:
                    print("username is not present and User= ", row['WH username'])
                    failed_count+=1
                    continue
            else:
                failed_count+=1
                print("username is empty and data= ", row)
                continue
            sku_id, location= "",""
            if row.get('SKU Code', ''):
                sku_code = str(row['SKU Code']).strip()
                sku_id = SKUMaster.objects.filter(wms_code=sku_code.upper(), user=user.id)
                if sku_id:
                    sku_obj= sku_id[0]
            if not row.get('SKU Code', '')  or not sku_id:
                failed_count+=1
                print("SKU_CODE is not present data =", str(row))
                continue
            if row.get('Location', ''):
                location = str(row['Location']).strip()
                location_obj=LocationMaster.objects.filter(location=location, zone__user=user.id)
                if location_obj:
                    location_obj=location_obj[0]
            if not location_obj or not row.get('Location', ''):
                failed_count+=1
                print("Location is not present data =", str(row))
                continue
            unit_price, buy_price, mrp ,quantity= [0]*4
            if row.get('Price', 0):
                buy_price= row['Price']
                unit_price= row['Price']
            if row.get('MRP', 0):
                mrp= row['MRP']
            if row.get('Base UOM Quantity', 0):
                quantity= row['Base UOM Quantity']
            if 'Receipt Type' in row:
                receipt_type = row['Receipt Type']
            if row.get('Receipt Number', ''):
                receipt_number =row['Receipt Number']
            else:
                failed_count+=1
                print("Receipt Number is not present data", str(row))
                continue
            if row.get('Receipt Date(YYYY-MM-DD)'):
                receipt_date= datetime.datetime.strptime(row['Receipt Date(YYYY-MM-DD)'], "%Y-%m-%d").strftime("%m/%d/%Y")
                receipt_date = datetime.datetime.strptime(receipt_date, '%m/%d/%Y')
            else:
                failed_count+=1
                print("Receipt Date is not present data= ", str(row))
                continue
            puom, pcf, pquantity, weight, expiry_date, manufactured_date, batch_no = ['']*7
            if 'Purchase UOM' in row:
                puom = row['Purchase UOM']
            if 'Purchase Conversion Factor' in row:
                pcf= row['Purchase Conversion Factor']
            if 'Purchase Quantity' in row:
                pquantity =row['Purchase Quantity']
            if 'Weight' in row:
                weight= row['Weight']
            if row.get('Expiry Date(YYYY-MM-DD)', ''):
                expiry_date = row['Expiry Date(YYYY-MM-DD)']
                expiry_date= datetime.datetime.strptime(expiry_date, "%Y-%m-%d").strftime("%m/%d/%Y")
            if row.get('Manufactured Date(YYYY-MM-DD)', ''):
                manufactured_date = row['Manufactured Date(YYYY-MM-DD)']
                manufactured_date = datetime.datetime.strptime(manufactured_date, "%Y-%m-%d").strftime("%m/%d/%Y")
            if 'Batch Number' in row:
                batch_no = row['Batch Number']
                if isinstance(batch_no, float):
                    batch_no=str(int(batch_no))
            batch_dict = {
                # 'transact_type': 'upload_loc',
                'batch_no': str(batch_no),
                'expiry_date': expiry_date,
                'manufactured_date': manufactured_date,
                'mrp': mrp,
                'buy_price': buy_price,
                'weight': weight,
                'puom': puom,
                'pquantity': pquantity,
                'pcf': pcf
            }
            add_ean_weight_to_batch_detail(sku_obj, batch_dict)
            batch_obj= create_update_batch_data(batch_dict)
            stock_details={
                'batch_detail_id': batch_obj.id,
                'location_id' : location_obj.id,
                'sku_id': sku_obj.id,
                'receipt_number': receipt_number,
                'receipt_date': receipt_date,
                'receipt_type' : receipt_type,
                'quantity': quantity,
                'unit_price': unit_price,
            }
            print(batch_dict)
            print(stock_details)
            stockdetail_obj = StockDetail(**stock_details)
            stockdetail_obj.save()
            completed_count+=1
            print("completed_count",completed_count, "failed_count ",failed_count)
        except Exception as e:
            failed_count+=1
            completed_count+=1
            print("completed_count",completed_count, "failed_count ",failed_count)
            print("\n\n\n Exception data = ", str(row), "\n error is =" ,str(e))


def upload_po_data_to_netsuite(file_location):
    import datetime
    import pandas as pd
    from rest_api.views.common import get_user_prefix_incremental, get_sku_ean_list
    # from rest_api.views.inbound import netsuite_po
    # file_location = "/var/www/metropolis_prod/WMS_ANGULAR/API_WMS/miebach/"
    #  UserProfile.objects.get(stockone_code="33004")
    # SupplierMaster.objects.get(user=55, supplier_id__contains='LO2145A018').tin_number
    from pytz import timezone
    from django.forms.models import model_to_dict
    from rest_api.views.inbound_common_operations import *
    log = init_logger('logs/new_PAST_PO_UPLOAD_scripts.log')
    df = pd.read_excel(file_location, header=1)
    df = df.fillna('')
    data= df.groupby('PO No.'.strip()).apply(lambda x: x.to_dict(orient='r')).to_dict()
    count=1
    failed=0
    success=0
    for key, value in data.iteritems():
        sku_code = value[0]['Material code.1'].strip()
        print(sku_code)
        user=''
        user_profile_obj=UserProfile.objects.filter(stockone_code=value[0]['STOCKONE Plant code'])
        if user_profile_obj:
            user=user_profile_obj[0].user
        else:
            user_profile_obj=UserProfile.objects.filter(stockone_code="0"+str(value[0]['StockOne Plant ID']))
            if user_profile_obj:
                user=user_profile_obj[0].user
            else:
                print('PO Upload failed for %s and params are %s and error statement is %s' % (str(key), str(value), str(e)))
                continue
        print("\n plant_user",user)
        flag=True
        if flag:
            for index, row in enumerate(value):
                if row.get('Material code.1', ''):
                    if not row['Pending PO Qty']:
                        print('PO Upload failed for %s and params are %s and PO error is PO QTY or sku_code is empty' % (str(key), str(value)))
                        flag= False
                        break
                    try:
                        supplier_obj = SupplierMaster.objects.filter(user=user.id, supplier_id__contains=str(row['Vendor Code']).strip())
                        if not supplier_obj:
                            log.info('PO Upload failed Beacause Vendor not present for %s and PO is %s and params are %s and error statement is %s' % (user.username, str(key), str(value), str("e")))
                            print('PO Upload failed Beacause Vendor not present for %s and PO is %s and params are %s and error statement is %s' % (user.username, str(key), str(value), str("e")))
                            ori_sup_obj= SupplierMaster.objects.filter(user=2,  supplier_id__contains=str(row['Vendor Code']).strip())
                            if ori_sup_obj:
                                print("need to create vendor\n\n")
                                log.info("need to create vendor")
                                ori_sup=model_to_dict(ori_sup_obj[0])
                                supp_id=ori_sup['id']
                                temp_suplier_id= ori_sup['id'].split('_')
                                del temp_suplier_id[0]
                                ori_sup["id"]= (str(user.id)+"_")+"_".join(temp_suplier_id)
                                ori_sup["user"]= user.id
                                obj=SupplierMaster(**ori_sup)
                                obj.save()
                                supplier_obj = [obj]
                                ori_pay=PaymentTerms.objects.filter(supplier=supp_id)
                                for pay in ori_pay:
                                    temp_dict= { "supplier": obj, "payment_code": pay.payment_code, "payment_description": pay.payment_description}
                                    payment_obj=PaymentTerms(**temp_dict)
                                    payment_obj.save()
                            else:
                                log.info('PO Upload failed Beacause MHL admin vendor is not present for %s and params are %s and error statement is %s' % (str(key), str(value), str("e")))
                                print('PO Upload failed Beacause MHL admin vendor is not present for %s and params are %s and error statement is %s' % (str(key), str(value), str("e")))
                                flag= False
                                break
                        else:
                            if(supplier_obj[0].reference_id in ['13733','14827']):
                                flag=True
                            else:
                                flag=False
                            break
                    except Exception as e:
                        log.info('PO Upload failed Beacause vendor error for %s and params are %s and error statement is %s' % (str(key), str(value), str(e)))
                else:
                    print('PO Upload failed for %s and params are %s and PO error is StockOne SKU Code or StockOne Plant ID is empty' % (str(key), str(value)))
                    flag= False
                    break
        product_category= "OtherItems"
        if flag:
            po_date_time =datetime.datetime.strptime(value[0]["PO Date"], '%d.%m.%Y')
            delivery_date= po_date_time.strftime('%d-%m-%Y')
            data_dict={'terms_condition': '',"delivery_date": delivery_date, 'ship_to_address':"" , "line_items":value}
            try:
                if supplier_obj:
                    netsuite_po(1, user, "open_po", data_dict, str(key), product_category, None, "", supplier_obj[0])
                else:
                    print("supplier not present",value[0]['Vendor Code'], "User= " ,user.username)
            except Exception as e:
                print("PO netsuite_exception =%s and error statement is  = %s" % str(key),str(e))
                pass
            success+=1
        else:
            failed+=1
        print("total_count= ", len(data), "completed= ", count, "Failed= ", failed, "Success= ", success)
        count=count+1


def add_new_sku_code_to_netsuite():
    po_number="4000097229"
    stockone_code ="33004"
    PO_Date ="23.07.2020"
    Material_code ="CON001412"
    quantity = 300
    price = 210
    sgst_tax = 9
    cgst_tax = 9
    igst_tax = 0
    product_category = "Kits&Consumables"  #Assets Services OtherItems
    po_data = {'open_po_id': '', 'status': '', 'received_quantity': 0}
    po_suggestions={'supplier_id': '', 'sku_id': '', 'order_quantity': '', 'order_type': 'SR', 'price': 0,
                               'status': 1}
    from miebach_admin.models import *
    from pytz import timezone
    from rest_api.views.inbound import netsuite_po
    import datetime
    utc_tz=timezone("UTC")
    po_date_time =utc_tz.localize(datetime.datetime.strptime(PO_Date, '%d.%m.%Y'))
    po_objs=PurchaseOrder.objects.filter(po_number=po_number).values('order_id', 'open_po__supplier_id')
    len(po_objs)
    if po_objs:
        po_obj = po_objs[0]
        po_id = po_obj["order_id"]
        supplier_id= po_obj['open_po__supplier_id']
        user_profile_obj= UserProfile.objects.filter(stockone_code=stockone_code)
        if user_profile_obj:
            user=user_profile_obj[0].user
        sku_id = SKUMaster.objects.filter(wms_code=Material_code, user=user.id)
        if sku_id:
            sku= sku_id[0]
        po_suggestions['sku_id'] = sku_id[0].id
        po_suggestions['supplier_id'] =  supplier_id
        po_suggestions['order_quantity'] = quantity
        po_suggestions['price'] = price
        po_suggestions['status'] = 'Manual'
        po_suggestions['measurement_unit'] = "UNITS"
        po_suggestions['sgst_tax'] = sgst_tax
        po_suggestions['cgst_tax'] = cgst_tax
        po_suggestions['igst_tax'] = igst_tax
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
        # po_data['prefix'] = prefix
        po_data['po_number'] = str(po_number)
        order = PurchaseOrder(**po_data)
        order.save()
        order.creation_date= po_date_time
        order.updation_date= po_date_time
        order.po_date= po_date_time
        order.save()
        print("Saved data ")
        po_date_time =datetime.datetime.strptime(PO_Date, '%d.%m.%Y')
        delivery_date= po_date_time.strftime('%d-%m-%Y')
        data_dict={'terms_condition': '',"delivery_date": delivery_date, 'ship_to_address':""}
        netsuite_po(int(po_id), user, "open_po", data_dict, str(po_number), product_category, None, "", False)
        # netsuite_po(int(po_id), user, "open_po", data_dict, str(po_number), product_category, None, "")

def update_po_price():
    po_number="4000097850"
    old_sku_code="REG001948"
    new_sku_code = "REG001949"
    stockone_code ="33004"
    price = 8674
    user_profile_obj= UserProfile.objects.filter(stockone_code=stockone_code)
    if user_profile_obj:
        user=user_profile_obj[0].user
    po_1= PurchaseOrder.objects.filter(po_number=po_number, open_po__sku__sku_code= old_sku_code, open_po__sku__user= user.id)[0]
    sku_id = SKUMaster.objects.filter(wms_code=new_sku_code, user=user.id)
    if sku_id:
        OpenPO.objects.filter(id=po_1.open_po.id).update(price=price, sku_id=sku_id[0].id)
