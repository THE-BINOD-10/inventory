from __future__ import absolute_import, unicode_literals
from miebach_admin.models import UserAddresses, MiscDetail, SupplierMaster, PaymentTerms
import datetime
import pandas as pd
from django.contrib.auth.models import User
from api_calls.netsuite import createPaymentTermsForSuppliers
from rest_api.views.common import sync_supplier_master
from miebach.celery import app
import ast

def update_profile_shipment_address(data):
    ''' will update profile Shipment Address '''
    try:
        user_id = User.objects.get(username=data.get('username')).id
        shipment_address = {}
        shipment_address['address_type'] = 'Shipment Address'
        shipment_address['address_name'] = data.get('address_title', '')
        shipment_address['user_name'] = data.get('address_name', '')
        shipment_address['mobile_number'] = data.get('address_mobile_number', '')
        shipment_address['pincode'] = data.get('address_pincode', '')
        shipment_address['address'] = data.get('address_shipment', '')
        shipment_address['user_id'] = user_id
        UserAddresses.objects.filter(user_id=user_id).delete()
        UserAddresses.objects.create(**shipment_address)
        print(shipment_address)
    except Exception as e:
        print(e)


def addConfigs(username, user_type):
    user_id = User.objects.get(username=username).id
    ConfigsToUpdateStore = [
        'supplier_mapping',
        'attributes_sync',
        'tax_master_sync',
        'supplier_sync',
        'inbound_supplier_invoice',
        'enable_pending_approval_pos',
        'enable_pending_approval_prs',
        'receive_po_inv_value_qty_check',
    ]
    ConfigsToUpdateForDept = [
        'enable_pending_approval_pos',
        'enable_pending_approval_prs',
        'receive_po_inv_value_qty_check',
    ]
    arayToUse = ConfigsToUpdateStore
    if user_type == 'DEPT':
        arayToUse = ConfigsToUpdateForDept
    for config in arayToUse:
        misc_detail, created = MiscDetail.objects.get_or_create(
            user=user_id,
            misc_type=config
        )
        misc_detail.misc_value = 'true'
        misc_detail.creation_date = datetime.datetime.now()
        misc_detail.updation_date = datetime.datetime.now()
        misc_detail.save()

def addStockoneCode(username, stockone_code):
    user = User.objects.get(username=username)
    user.userprofile.stockone_code = stockone_code
    user.userprofile.save()

def read_csvandaddconfigs():
    df = pd.read_csv('test.csv')
    for index, row in df.iterrows():
        addConfigs(row.username, row.user_type)

def read_csvandchangedepttype():
    df = pd.read_csv('username_stockonecode_mapping.csv')
    for index, row in df.iterrows():
        addStockoneCode(row.uername, row.stockone_code)

def read_csvandaddaddress():
    df = pd.read_csv('plant_address.csv')
    for index, row in df.iterrows():
        update_profile_shipment_address(row.to_dict())

def removeUnnecessaryData(skuDict):
        result = {}
        for key, value in skuDict.iteritems():
            if isinstance(value, (basestring, str, int, float)):
                result[key] = value
            else:
                continue

        return result

def read_suppliers_and_sync():
    suppliers = SupplierMaster.objects.filter(user=2)
    user = User.objects.get(id=2)
    count = 0
    for supplier in suppliers:
        count += 1
        print("Supplier Number :: %s" % count)
        print("Started Sync For :: %s" % supplier.supplier_id)
        sync_supplier_async(supplier.id, user.id)
        #remove_supplier_invalid.apply_async(args=[supplier.id, user.id])
        #sync_supplier_async.apply_async(queue='queueB', args=[supplier.id, user.id])

@app.task
def remove_supplier_invalid(sid, uid):
    supplier = SupplierMaster.objects.get(id=sid)
    admin_subsidiaries = []
    try:
        admin_subsidiaries = ast.literal_eval(supplier.subsidiary)
        admin_subsidiaries = [str(x) for x in admin_subsidiaries]
    except Exception as e:
        admin_subsidiaries = [str(supplier.subsidiary)]
    usernamestoexclude = ['mhl_admin', 'mhl_amin', 'admin']
    invalid_subsidaries = User.objects.filter(is_staff=True).exclude(username__in=usernamestoexclude).exclude(userprofile__company__reference_id__in=admin_subsidiaries).values_list('userprofile__company__reference_id', flat=True).distinct()
    print(list(invalid_subsidaries), admin_subsidiaries)
    invalid_users = User.objects.filter(is_staff=True, userprofile__company__reference_id__in=invalid_subsidaries).values_list('id', flat=True)
    print(invalid_users)
    supstodelete = SupplierMaster.objects.filter(user__in=invalid_users, supplier_id=supplier.supplier_id)
    check1 = False
    check2 = False

    openpos = supstodelete.values('openpo').distinct()
    if openpos.count() == 1:
        if openpos[0].get('openpo', 1) == None:
            check1 = True
    pendingpos = supstodelete.values('pendingpos').distinct()
    if pendingpos.count() == 1:
        if pendingpos[0].get('pendingpos', 1) == None:
            check2 = True

    if check1 and check2:
        supstodelete.delete()

@app.task
def sync_supplier_async(id, user_id):
    supplier = SupplierMaster.objects.get(id=id)
    supplierC = SupplierMaster.objects.filter(supplier_id=supplier.supplier_id)
    user = User.objects.get(id=user_id)
    filter_dict = {'supplier_id': supplier.supplier_id }
    data_dict = removeUnnecessaryData(supplier.__dict__)
    data_dict.pop('id')
    data_dict.pop('user')
    data_dict.pop('tax_type')
    payment_term_arr = [row.__dict__ for row in supplier.paymentterms_set.filter()]
    net_term_arr = [row.__dict__ for row in supplier.netterms_set.filter()]
    #user_names_list= ["mhl_mhl_03197","mhl_mhl_03197_ADMIN","mhl_mhl_03197_SCMMM","mhl_mhl_03197_ACCFI","mhl_mhl_03197_HRDDE","mhl_mhl_03197_ITTEC","mhl_mhl_03197_MARKE"] 
    user_names_list= [] 
    #"mhl_mhl_03184_SCMMM","mhl_mhl_03184_ACCFI","mhl_mhl_03184_HRDDE",
    #"mhl_mhl_03184_ITTEC","mhl_mhl_03184_MARKE"]
    #user_names_list= ["mhl_patel_27182_QUAAU", "mhl_patel_27182_SCMMM", "mhl_patel_27182_ADMIN", "mhl_mhl_01189_ADMIN", "mhl_mhl_01189_ACCFI", "mhl_mhl_01189_HRDDE", "mhl_mhl_01189_ITTEC", "mhl_mhl_01189_LOGIS", "mhl_mhl_01189_MARKE", "mhl_mhl_01189_SCMMM", "mhl_desai_24181_ADMIN", "mhl_desai_24181_ACCFI", "mhl_desai_24181_HRDDE", "mhl_desai_24181_ITTEC", "mhl_desai_24181_LOGIS", "mhl_desai_24181_MARKE", "mhl_desai_24181_SCMMM"]
    users_object_list=[]
    for user_name in user_names_list:
        user_obj= User.objects.get(username=user_name)
        users_object_list.append(user_obj.id)
    master_objs = sync_supplier_master({}, user, data_dict, filter_dict, force=True, userids_list=users_object_list)
    createPaymentTermsForSuppliers(master_objs, payment_term_arr, net_term_arr)
    return "Sync Completed For %s" % supplier.supplier_id
