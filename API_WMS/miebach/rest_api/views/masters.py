from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import copy
import json
from itertools import chain
from django.db.models import Q, F
from collections import OrderedDict
from django.contrib.auth import authenticate
from django.contrib import auth
from miebach_admin.models import *
from common import *
from miebach_utils import *
from django.core import serializers
import os
from sync_sku import *
import simplejson

log = init_logger('logs/masters.log')


# Create your views here.

def save_image_file(image_file, data, user, extra_image='', saved_file_path='', file_name=''):
    extension = image_file.name.split('.')[-1]
    path = 'static/images/'
    folder = str(user.id)
    image_name = str(data.wms_code).replace('/', '--')
    if extra_image:
        image_name = image_file.name.strip('.' + image_file.name.split('.')[-1])
    if not os.path.exists(path + folder):
        os.makedirs(path + folder)
    full_filename = os.path.join(path, folder, str(image_name) + '.' + str(extension))
    fout = open(full_filename, 'wb+')
    file_content = ContentFile(image_file.read())

    try:
        # Iterate through the chunks.
        file_contents = file_content.chunks()
        for chunk in file_contents:
            fout.write(chunk)
        fout.close()
        if not saved_file_path:
            image_url = '/' + path + folder + '/' + str(image_name) + '.' + str(extension)
            saved_file_path = image_url
        else:
            image_url = saved_file_path
        if not extra_image:
            data.image_url = image_url
            data.save()
            return saved_file_path
        sku_image = SKUImages.objects.filter(sku_id=data.id, image_url=image_url)
        if not sku_image:
            SKUImages.objects.create(sku_id=data.id, image_url=image_url, creation_date=datetime.datetime.now())
        return saved_file_path

    except:
        print 'not saved'
        return ''


@csrf_exempt
def get_sku_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['wms_code', 'sku_desc', 'sku_type', 'sku_category', 'sku_class', 'color', 'zone__zone', 'status']
    order_data = SKU_MASTER_HEADERS.values()[col_num]
    search_params1, search_params2 = get_filtered_params_search(filters, lis)
    if 'status__icontains' in search_params1.keys():
        if (str(search_params['status__icontains']).lower() in "active"):
            search_params1["status__icontains"] = 1
            search_params2["status__icontains"] = 1
        elif (str(search_params1['status__icontains']).lower() in "inactive"):
            search_params1["status__icontains"] = 0
            search_params2["status__icontains"] = 0
        else:
            search_params["status__icontains"] = "none"
    if order_term == 'desc':
        order_data = '-%s' % order_data
    master_data = []
    ids = []
    if search_term:

        status_dict = {'active': 1, 'inactive': 0}
        if search_term.lower() in status_dict:
            search_terms = status_dict[search_term.lower()]
            if search_params1:
                for item in [search_params1, search_params2]:
                    master_data1 = sku_master.exclude(id__in=ids).filter(status=search_terms, user=user.id,
                                                                         **item).order_by(order_data)
                    ids.extend(master_data1.values_list('id', flat=True))
                    master_data.extend(list(master_data1))
            else:
                master_data1 = sku_master.filter(status=search_terms, user=user.id).order_by(order_data)
        else:
            list1 = []
            if search_params1:
                list1 = [search_params1, search_params2]
            else:
                list1 = [{}]

            for item in list1:
                master_data1 = sku_master.exclude(id__in=ids).filter(
                    Q(sku_code__iexact=search_term) | Q(wms_code__iexact=search_term) | Q(
                        sku_desc__iexact=search_term) | Q(sku_type__iexact=search_term) | Q(
                        sku_category__iexact=search_term) | Q(sku_class__iexact=search_term) | Q(
                        zone__zone__iexact=search_term) | Q(color__iexact=search_term), user=user.id, **item).order_by(
                    order_data)
                ids.extend(master_data1.values_list('id', flat=True))

                master_data2 = sku_master.exclude(id__in=ids).filter(
                    Q(sku_code__istartswith=search_term) | Q(wms_code__istartswith=search_term) | Q(
                        sku_desc__istartswith=search_term) | Q(sku_type__istartswith=search_term) | Q(
                        sku_category__istartswith=search_term) | Q(sku_class__istartswith=search_term) | Q(
                        zone__zone__istartswith=search_term) | Q(color__istartswith=search_term), user=user.id,
                    **item).order_by(order_data)

                ids.extend(master_data2.values_list('id', flat=True))

                master_data3 = sku_master.filter(
                    Q(sku_code__icontains=search_term) | Q(wms_code__icontains=search_term) | Q(
                        sku_desc__icontains=search_term) | Q(sku_type__icontains=search_term) | Q(
                        sku_category__icontains=search_term) | Q(sku_class__icontains=search_term) | Q(
                        zone__zone__icontains=search_term) | Q(color__icontains=search_term), user=user.id,
                    **item).exclude(id__in=ids).order_by(order_data)
                ids.extend(master_data3.values_list('id', flat=True))
                master_data.extend(list(master_data1))
                master_data.extend(list(master_data2))
                master_data.extend(list(master_data3))

    else:
        if search_params1:
            master_data = []
            ids = []
            for item in [search_params1, search_params2]:
                master_data1 = sku_master.exclude(id__in=ids).filter(**item).order_by(order_data)
                ids.extend(master_data1.values_list('id', flat=True))
                master_data.extend(list(master_data1))
        else:
            master_data = sku_master.order_by(order_data)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        status = 'Inactive'
        if data.status:
            status = 'Active'

        zone = ''
        if data.zone_id:
            zone = data.zone.zone
        temp_data['aaData'].append(OrderedDict(
            (('WMS SKU Code', data.wms_code), ('Product Description', data.sku_desc), ('image_url', data.image_url),
             ('SKU Type', data.sku_type), ('SKU Category', data.sku_category), ('DT_RowClass', 'results'),
             ('Zone', zone), ('SKU Class', data.sku_class), ('Status', status), ('DT_RowAttr', {'data-id': data.id}),
             ('Color', data.color))))


@csrf_exempt
@login_required
@get_admin_user
def get_location_data(request, user=''):
    FIELDS = ''
    location_group = ''
    loc_id = request.GET['location_id']
    filter_params = {'location': loc_id, 'zone__user': user.id}
    data = get_or_none(LocationMaster, filter_params)
    FIELDS = LOCATION_FIELDS
    pallet_switch = get_misc_value('pallet_switch', user.id)
    if pallet_switch == "true":
        FIELDS = FIELDS + ((('Pallet Capacity', 'pallet_capacity'),),)
    all_groups = SKUGroups.objects.filter(user=user.id).values_list('group', flat=True)
    location_map = LocationGroups.objects.filter(location__zone__user=user.id, location_id=data.id)
    if location_map:
        location_group = location_map[0].group
    return HttpResponse("")
    # json.dumps({'data': data, 'update_location': FIELDS, 'lock_fields': LOCK_FIELDS,
    # 'all_groups': all_groups, 'location_group': location_group}))


def get_supplier_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    search_dict = {'active': 1, 'inactive': 0}
    order_data = SUPPLIER_MASTER_HEADERS.values()[col_num]
    search_params = get_filtered_params(filters, SUPPLIER_MASTER_HEADERS.values())
    if 'status__icontains' in search_params.keys():
        if (str(search_params['status__icontains']).lower() in "active"):
            search_params["status__icontains"] = 1
        elif (str(search_params['status__icontains']).lower() in "inactive"):
            search_params["status__icontains"] = 0
        else:
            search_params["status__icontains"] = "none"

    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        if search_term.lower() in search_dict:
            search_terms = search_dict[search_term.lower()]
            master_data = SupplierMaster.objects.filter(status=search_terms, user=user.id, **search_params).order_by(
                order_data)

        else:
            master_data = SupplierMaster.objects.filter(
                Q(id__icontains=search_term) | Q(name__icontains=search_term) | Q(address__icontains=search_term) | Q(
                    phone_number__icontains=search_term) | Q(email_id__icontains=search_term), user=user.id,
                **search_params).order_by(order_data)

    else:
        master_data = SupplierMaster.objects.filter(user=user.id, **search_params).order_by(order_data)

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)

    for data in master_data[start_index: stop_index]:
        status = 'Inactive'
        if data.status:
            status = 'Active'

        login_created = False
        user_role_mapping = UserRoleMapping.objects.filter(role_id=data.id, role_type='supplier')
        username = ""
        if user_role_mapping:
            login_created = True
            username = user_role_mapping[0].user.username

        if data.phone_number:
            data.phone_number = int(float(data.phone_number))
        temp_data['aaData'].append(OrderedDict((('id', data.id), ('name', data.name), ('address', data.address),
                                                ('phone_number', data.phone_number), ('email_id', data.email_id),
                                                ('cst_number', data.cst_number), ('tin_number', data.tin_number),
                                                ('pan_number', data.pan_number), ('city', data.city),
                                                ('state', data.state),
                                                ('country', data.country), ('pincode', data.pincode),
                                                ('status', status), ('supplier_type', data.supplier_type),
                                                ('username', username), ('login_created', login_created),
                                                ('DT_RowId', data.id), ('DT_RowClass', 'results'))))


@csrf_exempt
def get_supplier_mapping(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    order_data = SKU_SUPPLIER_MAPPING.values()[col_num]
    filter_params = get_filtered_params(filters, SKU_SUPPLIER_MAPPING.values())

    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        mapping_results = SKUSupplier.objects.filter(sku_id__in=sku_master_ids).filter(
            Q(supplier__id__icontains=search_term) | Q(preference__icontains=search_term) | Q(
                moq__icontains=search_term) | Q(sku__wms_code__icontains=search_term) | Q(
                supplier_code__icontains=search_term), sku__user=user.id, supplier__user=user.id,
            **filter_params).order_by(order_data)

    else:
        mapping_results = SKUSupplier.objects.filter(sku_id__in=sku_master_ids).filter(sku__user=user.id,
                                                                                       supplier__user=user.id,
                                                                                       **filter_params).order_by(
            order_data)

    temp_data['recordsTotal'] = len(mapping_results)
    temp_data['recordsFiltered'] = len(mapping_results)

    for result in mapping_results[start_index: stop_index]:
        temp_data['aaData'].append(OrderedDict((('supplier_id', result.supplier_id), ('wms_code', result.sku.wms_code),
                                                ('supplier_code', result.supplier_code), ('moq', result.moq),
                                                ('preference', int(result.preference)),
                                                ('price', result.price), ('DT_RowClass', 'results'),
                                                ('DT_RowId', result.id))))


@csrf_exempt
def get_customer_master(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    lis = ['customer_id', 'name', 'email_id', 'phone_number', 'address', 'status']

    search_params = get_filtered_params(filters, lis)
    if 'status__icontains' in search_params.keys():
        if (str(search_params['status__icontains']).lower() in "active"):
            search_params["status__icontains"] = 1
        elif (str(search_params['status__icontains']).lower() in "inactive"):
            search_params["status__icontains"] = 0
        else:
            search_params["status__icontains"] = "none"
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        search_dict = {'active': 1, 'inactive': 0}
        if search_term.lower() in search_dict:
            search_terms = search_dict[search_term.lower()]
            master_data = CustomerMaster.objects.filter(status=search_terms, user=user.id, **search_params).order_by(
                order_data)

        else:
            master_data = CustomerMaster.objects.filter(
                Q(name__icontains=search_term) | Q(address__icontains=search_term) |
                Q(phone_number__icontains=search_term) | Q(email_id__icontains=search_term),
                user=user.id, **search_params).order_by(order_data)

    else:
        master_data = CustomerMaster.objects.filter(user=user.id, **search_params).order_by(order_data)

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index: stop_index]:
        status = 'Inactive'
        if data.status:
            status = 'Active'

        if data.phone_number:
            try:
                data.phone_number = int(float(data.phone_number))
            except:
                data.phone_number = ''
        login_created = False
        customer_login = CustomerUserMapping.objects.filter(customer_id=data.id)
        user_name = ""
        price_type = ""
        if customer_login:
            login_created = True
            # user = customer_login[0].user
            user_name = customer_login[0].user.username

        price_band_flag = get_misc_value('priceband_sync', user.id)
        if price_band_flag == 'true':
            user = get_admin(data.user)

        price_types = list(
            PriceMaster.objects.exclude(price_type__in=["", 'D1-R', 'R-C']).filter(sku__user=user.id).
                values_list('price_type', flat=True).distinct())

        price_type = data.price_type
        phone_number = ''
        if data.phone_number and data.phone_number != '0':
            phone_number = data.phone_number
        temp_data['aaData'].append(
            OrderedDict((('customer_id', data.customer_id), ('name', data.name), ('address', data.address),
                         ('phone_number', phone_number), ('email_id', data.email_id), ('status', status),
                         ('tin_number', data.tin_number), ('credit_period', data.credit_period),
                         ('login_created', login_created), ('username', user_name), ('price_type_list', price_types),
                         ('price_type', price_type), ('cst_number', data.cst_number),
                         ('pan_number', data.pan_number), ('customer_type', data.customer_type),
                         ('pincode', data.pincode), ('city', data.city), ('state', data.state),
                         ('country', data.country), ('tax_type', TAX_TYPE_ATTRIBUTES.get(data.tax_type, '')),
                         ('DT_RowId', data.customer_id), ('DT_RowClass', 'results'),
                         ('discount_percentage', data.discount_percentage), ('lead_time', data.lead_time),
                         ('is_distributor', str(data.is_distributor)), ('markup', data.markup),
                         )))


@csrf_exempt
def get_corporate_master(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    lis = ['corporate_id', 'name', 'email_id', 'phone_number', 'address', 'status']
    search_params = get_filtered_params(filters, lis)
    if 'status__icontains' in search_params.keys():
        if (str(search_params['status__icontains']).lower() in "active"):
            search_params["status__icontains"] = 1
        elif (str(search_params['status__icontains']).lower() in "inactive"):
            search_params["status__icontains"] = 0
        else:
            search_params["status__icontains"] = "none"
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data

    if search_term:
        search_dict = {'active': 1, 'inactive': 0}
        if search_term.lower() in search_dict:
            search_terms = search_dict[search_term.lower()]
            master_data = CorporateMaster.objects.filter(status=search_terms, user=user.id, **search_params).order_by(
                order_data)

        else:
            master_data = CorporateMaster.objects.filter(
                Q(name__icontains=search_term) | Q(address__icontains=search_term) |
                Q(phone_number__icontains=search_term) | Q(email_id__icontains=search_term),
                user=user.id, **search_params).order_by(order_data)

    else:
        master_data = CorporateMaster.objects.filter(user=user.id, **search_params).order_by(order_data)

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index: stop_index]:
        status = 'Inactive'
        if data.status == '1':
            status = 'Active'

        if data.phone_number:
            try:
                data.phone_number = int(data.phone_number)
            except:
                data.phone_number = ''

        phone_number = ''
        if data.phone_number and data.phone_number != '0':
            phone_number = data.phone_number
        temp_data['aaData'].append(
            OrderedDict((('corporate_id', data.corporate_id), ('name', data.name), ('address', data.address),
                         ('phone_number', phone_number), ('email_id', data.email_id), ('status', status),
                         ('tin_number', data.tin_number), ('cst_number', data.cst_number),
                         ('pan_number', data.pan_number), ('pincode', data.pincode), ('city', data.city), 
                         ('state', data.state), ('country', data.country), 
                         ('tax_type', TAX_TYPE_ATTRIBUTES.get(data.tax_type, '')), ('DT_RowId', data.corporate_id), 
                         ('DT_RowClass', 'results'))))


@csrf_exempt
def get_staff_master(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    lis = ['id', 'staff_name', 'email_id', 'phone_number', 'status']

    search_params = get_filtered_params(filters, lis)
    if 'status__icontains' in search_params.keys():
        if (str(search_params['status__icontains']).lower() in "active"):
            search_params["status__icontains"] = 1
        elif (str(search_params['status__icontains']).lower() in "inactive"):
            search_params["status__icontains"] = 0
        else:
            search_params["status__icontains"] = "none"
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        search_dict = {'active': 1, 'inactive': 0}
        if search_term.lower() in search_dict:
            search_terms = search_dict[search_term.lower()]
            master_data = StaffMaster.objects.filter(status=search_terms, user=user.id, **search_params).order_by(
                order_data)

        else:
            master_data = StaffMaster.objects.filter(
                Q(staff_name__icontains=search_term) | Q(phone_number__icontains=search_term) |
                Q(email_id__icontains=search_term),
                user=user.id, **search_params).order_by(order_data)

    else:
        master_data = StaffMaster.objects.filter(user=user.id, **search_params).order_by(order_data)

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index: stop_index]:
        status = 'Inactive'
        if data.status:
            status = 'Active'

        if data.phone_number:
            try:
                data.phone_number = int(float(data.phone_number))
            except:
                data.phone_number = ''
        phone_number = ''
        if data.phone_number and data.phone_number != '0':
            phone_number = data.phone_number
        temp_data['aaData'].append(
            OrderedDict((('staff_id', data.id), ('name', data.staff_name), ('phone_number', phone_number),
                         ('email_id', data.email_id), ('status', status),
                         ('DT_RowId', data.id), ('DT_RowClass', 'results'),
                         )))


@csrf_exempt
def get_bom_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['product_sku__sku_code', 'product_sku__sku_desc']

    search_params = get_filtered_params(filters, lis)
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if order_term:
        master_data = BOMMaster.objects.filter(product_sku_id__in=sku_master_ids).filter(product_sku__user=user.id,
                                                                                         **search_params).order_by(
            order_data). \
            values('product_sku__sku_code', 'product_sku__sku_desc').distinct().order_by(order_data)
    if search_term:
        master_data = BOMMaster.objects.filter(product_sku_id__in=sku_master_ids).filter(
            Q(product_sku__sku_code__icontains=search_term) |
            Q(product_sku__sku_desc__icontains=search_term), product_sku__user=user.id, **search_params). \
            values('product_sku__sku_code', 'product_sku__sku_desc').distinct().order_by(order_data)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        temp_data['aaData'].append(
            {'Product SKU Code': data['product_sku__sku_code'], 'Product Description': data['product_sku__sku_desc'],
             'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data['product_sku__sku_code']}})


def get_customer_sku_mapping(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                             filters):
    order_data = CUSTOMER_SKU_MAPPING_HEADERS.values()[col_num]
    search_params = get_filtered_params(filters, CUSTOMER_SKU_MAPPING_HEADERS.values())
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if order_term:
        master_data = CustomerSKU.objects.filter(sku__user=user.id, **search_params).order_by(order_data)
    if search_term:
        master_data = CustomerSKU.objects.filter(
            Q(customer__customer_id=search_term) | Q(customer__name__icontains=search_term) | Q(
                sku__sku_code__icontains=search_term) | Q(price__icontains=search_term), sku__user=user.id,
            **search_params)

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        temp_data['aaData'].append(OrderedDict((('DT_RowId', data.id), ('customer_id', data.customer.customer_id),
                                                ('customer_name', data.customer.name),
                                                ('sku_code', data.sku.sku_code),
                                                ('customer_sku_code', data.customer_sku_code),
                                                ('DT_RowClass', 'results'))))


@csrf_exempt
def get_vendor_master_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                              filters):
    lis = ['vendor_id', 'name', 'address', 'phone_number', 'email_id', 'status']
    search_params = get_filtered_params(filters, lis)
    if 'status__icontains' in search_params.keys():
        if (str(search_params['status__icontains']).lower() in "active"):
            search_params["status__icontains"] = 1
        elif (str(search_params['status__icontains']).lower() in "inactive"):
            search_params["status__icontains"] = 0
        else:
            search_params["status__icontains"] = "none"
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        search_dict = {'active': 1, 'inactive': 0}
        if search_term.lower() in search_dict:
            search_terms = search_dict[search_term.lower()]
            master_data = VendorMaster.objects.filter(status=search_terms, user=user.id, **search_params).order_by(
                order_data)

        else:
            master_data = VendorMaster.objects.filter(
                Q(vendor_id__icontains=search_term) | Q(name__icontains=search_term) |
                Q(address__icontains=search_term) | Q(phone_number__icontains=search_term) |
                Q(email_id__icontains=search_term), user=user.id, **search_params).order_by(order_data)

    else:
        master_data = VendorMaster.objects.filter(user=user.id, **search_params).order_by(order_data)

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)

    for data in master_data[start_index: stop_index]:
        status = 'Inactive'
        if data.status:
            status = 'Active'

        if data.phone_number:
            data.phone_number = int(float(data.phone_number))
        temp_data['aaData'].append(
            OrderedDict((('vendor_id', data.vendor_id), ('name', data.name), ('address', data.address),
                         ('phone_number', data.phone_number), ('email', data.email_id), ('Status', status),
                         ('DT_RowId', data.vendor_id), ('DT_RowClass', 'results'))))


@get_admin_user
def location_master(request, user=''):
    filter_params = {'user': user.id}
    distinct_loctype = filter_by_values(ZoneMaster, filter_params, ['zone'])
    new_loc = []
    location_groups = LocationGroups.objects.filter(location__zone__user=user.id).values('location__location',
                                                                                         'group').distinct()
    for loc_type in distinct_loctype:
        filter_params = {'zone__zone': loc_type['zone'], 'zone__user': user.id}
        loc = filter_by_values(LocationMaster, filter_params,
                               ['location', 'max_capacity', 'fill_sequence', 'pick_sequence', 'status',
                                'pallet_capacity', 'lock_status'])
        for loc_location in loc:
            loc_group_dict = filter(lambda person: str(loc_location['location']) == str(person['location__location']),
                                    location_groups)
            loc_groups = map(lambda d: d['group'], loc_group_dict)
            loc_groups = [str(x).encode('UTF8') for x in loc_groups]
            loc_location['location_group'] = loc_groups
        new_loc.append(loc)

    data = []
    modified_zone = zip(distinct_loctype, new_loc)
    if modified_zone:
        for loc in modified_zone:
            zone = loc[0]['zone']
            data.append({'zone': zone, 'data': list(loc[1])})

    all_groups = list(SKUGroups.objects.filter(user=user.id).values_list('group', flat=True))

    return HttpResponse(
        json.dumps({'location_data': data, 'sku_groups': all_groups, 'lock_fields': ['Inbound', 'Outbound',
                                                                                     'Inbound and Outbound']}),
        content_type='application/json')


@get_admin_user
def get_sku_data(request, user=''):
    """ Get SKU Details """

    market_data = []
    combo_data = []
    data_id = request.GET['data_id']

    filter_params = {'id': data_id, 'user': user.id}
    data = get_or_none(SKUMaster, filter_params)

    filter_params = {'user': user.id}
    zones = filter_by_values(ZoneMaster, filter_params, ['zone'])
    all_groups = list(SKUGroups.objects.filter(user=user.id).values_list('group', flat=True))
    load_unit_dict = {'unit': 0, 'pallet': 1}

    zone_name = ''
    if data.zone:
        zone_name = data.zone.zone

    zone_list = []
    for zone in zones:
        zone_list.append(zone['zone'])
    market_map = MarketplaceMapping.objects.filter(sku_id=data.id)
    market_data = []
    for market in market_map:
        market_data.append({'market_sku_type': market.sku_type, 'marketplace_code': market.marketplace_code,
                            'description': market.description, 'market_id': market.id})

    combo_skus = SKURelation.objects.filter(relation_type='combo', parent_sku_id=data.id)
    for combo in combo_skus:
        combo_data.append(
            OrderedDict((('combo_sku', combo.member_sku.wms_code), ('combo_desc', combo.member_sku.sku_desc))))

    sku_data = {}
    sku_data['sku_code'] = data.sku_code
    sku_data['wms_code'] = data.wms_code
    sku_data['sku_desc'] = data.sku_desc
    sku_data['sku_group'] = data.sku_group
    sku_data['sku_type'] = data.sku_type
    sku_data['sku_category'] = data.sku_category
    sku_data['sku_class'] = data.sku_class
    sku_data['sku_brand'] = data.sku_brand
    sku_data['style_name'] = data.style_name
    sku_data['sku_size'] = data.sku_size
    sku_data['product_type'] = data.product_type
    sku_data['zone'] = zone_name
    sku_data['threshold_quantity'] = data.threshold_quantity
    sku_data['online_percentage'] = data.online_percentage
    sku_data['image_url'] = data.image_url
    sku_data['qc_check'] = data.qc_check
    sku_data['status'] = data.status
    sku_data['cost_price'] = data.cost_price
    sku_data['price'] = data.price
    sku_data['mrp'] = data.mrp
    sku_data['size_type'] = ''
    sku_data['mix_sku'] = data.mix_sku
    sku_data['ean_number'] = data.ean_number
    sku_data['color'] = data.color
    sku_data['load_unit_handle'] = load_unit_dict.get(data.load_unit_handle, 'unit')
    sku_data['hsn_code'] = data.hsn_code
    sku_data['sub_category'] = data.sub_category
    sku_data['primary_category'] = data.primary_category
    sku_data['hot_release'] = 0
    sku_fields = SKUFields.objects.filter(field_type='size_type', sku_id=data.id)
    if sku_fields:
        sku_data['size_type'] = sku_fields[0].field_value

    sku_fields = SKUFields.objects.filter(field_type='hot_release', sku_id=data.id)
    if sku_fields:
        sku_data['hot_release'] = sku_fields[0].field_value

    size_names = SizeMaster.objects.filter(user=user.id)
    sizes_list = []
    for sizes in size_names:
        sizes_list.append({'size_name': sizes.size_name, 'size_values': (sizes.size_value).split('<<>>')})
    #sizes_list.append({'size_name': 'Default', 'size_values': copy.deepcopy(SIZES_LIST)})
    market_places = list(Marketplaces.objects.filter(user=user.id).values_list('name', flat=True))
    admin_user = get_priceband_admin_user(user)
    if admin_user:
        product_types = list(TaxMaster.objects.filter(user_id=admin_user.id).values_list('product_type',
                                                                                         flat=True).distinct())
    else:
        product_types = list(TaxMaster.objects.filter(user_id=user.id).values_list('product_type',
                                                                                   flat=True).distinct())
    return HttpResponse(
        json.dumps({'sku_data': sku_data, 'zones': zone_list, 'groups': all_groups, 'market_list': market_places,
                    'market_data': market_data, 'combo_data': combo_data, 'sizes_list': sizes_list,
                    'sub_categories': SUB_CATEGORIES, 'product_types': product_types}, cls=DjangoJSONEncoder))


@csrf_exempt
def get_warehouse_user_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                               filters):
    search_params1 = {}
    search_params2 = {}
    lis = ['username', 'first_name', 'email', 'id']

    warehouse_admin = get_warehouse_admin(user)
    exclude_admin = {}
    if warehouse_admin.id == user.id:
        exclude_admin = {'admin_user_id': user.id}
    search_params = get_filtered_params(filters, lis)
    for key, value in search_params.iteritems():
        search_params1['user__' + key] = value
        search_params2['admin_user__' + key] = value
    user_dict = OrderedDict()
    order_data = 'user__' + lis[col_num]
    order_data1 = 'admin_user__' + lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
        order_data1 = '-%s' % order_data1

    all_user_groups = UserGroups.objects.filter(admin_user_id=warehouse_admin.id)
    if search_term:
        master_data1 = all_user_groups.filter(
            Q(user__first_name__icontains=search_term) | Q(user__email__icontains=search_term),
            **search_params1).exclude(user_id=user.id). \
            order_by(order_data).values_list('user__username', 'user__first_name', 'user__email',
                                             'user__warehouse_type', 'user__warehouse_level', 'user__min_order_val',
                                             'user__zone')

        master_data2 = all_user_groups.exclude(**exclude_admin).filter(
            Q(admin_user__first_name__icontains=search_term) |
            Q(admin_user__email__icontains=search_term), **search_params2). \
            order_by(order_data1).values_list('admin_user__username',
                                              'admin_user__first_name', 'admin_user__email',
                                              'admin_user__userprofile__warehouse_type',
                                              'admin_user__userprofile__warehouse_level',
                                              'admin_user__userprofile__min_order_val',
                                              'admin_user__userprofile__zone').distinct()
        master_data = list(chain(master_data1, master_data2))

    elif order_term:
        master_data1 = all_user_groups.filter(**search_params1).exclude(user_id=user.id). \
            order_by(order_data).values_list('user__username', 'user__first_name', 'user__email',
                                             'user__userprofile__warehouse_type', 'user__userprofile__warehouse_level',
                                             'user__userprofile__min_order_val', 'user__userprofile__zone')
        master_data2 = all_user_groups.exclude(**exclude_admin).filter(**search_params2).order_by(order_data1). \
            values_list('admin_user__username', 'admin_user__first_name', 'admin_user__email',
                        'admin_user__userprofile__warehouse_type', 'admin_user__userprofile__warehouse_level',
                        'admin_user__userprofile__min_order_val', 'admin_user__userprofile__zone').distinct()
        master_data = list(chain(master_data1, master_data2))

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        username, name, email, wh_type, wh_level, min_order_val, zone = data
        user_profile = UserProfile.objects.get(user__username=username)
        temp_data['aaData'].append({'Username': username, 'DT_RowClass': 'results', 'Name': name,
                                    'Email': email, 'City': user_profile.city, 'DT_RowId': username,
                                    'Type': wh_type, 'Level': wh_level, 'Min Order Value': min_order_val,
                                    'Zone': zone})


@csrf_exempt
def get_discount_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    order_data = ''
    index_headers = {0: 'sku_code', 1: 'sku_category', 2: 'discount_percentage', 3: 'id'}
    reverse = False

    if order_term and index_headers.get(col_num):
        order_data = '%s' % index_headers[col_num]
        if order_term == 'desc':
            reverse = True
            order_data = '%s' % index_headers[col_num]

    sku_filters = get_filtered_params(filters, index_headers.values())
    category_filter = {'user': user.id, 'discount__gt': 0}
    if 'id__icontains' in sku_filters.keys():
        category_filter['discount__icontains'] = sku_filters['id__icontains']
        del sku_filters['id__icontains']

    category = CategoryDiscount.objects.filter(**category_filter)
    category_list = category.values_list('category', flat=True)

    search_params = {'user': user.id}
    if search_term:
        master_data = SKUMaster.objects.filter(Q(discount_percentage__gt=0) | Q(sku_category__in=category_list)). \
            filter(Q(sku_code__icontains=search_term) | Q(sku_category__icontains=search_term),
                   **search_params).filter(**sku_filters)
    else:
        master_data = SKUMaster.objects.filter(Q(discount_percentage__gt=0) | Q(sku_category__in=category_list),
                                               **search_params). \
            filter(**sku_filters)

    if order_data:
        master_data = sorted(master_data, key=lambda instance: getattr(instance, order_data), reverse=reverse)

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)

    for data in master_data[start_index:stop_index]:
        sku_category = category.filter(category=data.sku_category)
        category_discount = 0
        if sku_category:
            category_discount = sku_category[0].discount

        temp_data['aaData'].append(OrderedDict((('sku', data.wms_code), ('category', data.sku_category),
                                                ('sku_discount', data.discount_percentage),
                                                ('category_discount', category_discount),
                                                ('DT_RowClass', 'results'), ('DT_RowAttr', {'data-id': data.id}))))


def check_update_size_type(data, value):
    sku_fields = SKUFields.objects.filter(sku_id=data.id, field_type='size_type')
    size_master = SizeMaster.objects.filter(user=data.user, size_name=value)
    if not size_master:
        return
    size_master = size_master[0]
    _value = size_master.size_name
    if not sku_fields:
        SKUFields.objects.create(sku_id=data.id, field_id=size_master.id, field_type='size_type', field_value=_value,
                                 creation_date=datetime.datetime.now())
    else:
        sku_fields[0].field_value = _value
        sku_fields[0].field_id = size_master.id
        sku_fields[0].save()


def check_update_hot_release(data, value):
    sku_fields = SKUFields.objects.filter(sku_id=data.id, field_type='hot_release')
    if not sku_fields:
        SKUFields.objects.create(sku_id=data.id, field_type='hot_release', field_value=value,
                                 creation_date=datetime.datetime.now())
    else:
        if sku_fields[0].field_value != value:
            sku_fields[0].field_value = value
            sku_fields[0].save()


@csrf_exempt
@login_required
@get_admin_user
def update_sku(request, user=''):
    """ Update SKU Details"""

    log.info('Update SKU request params for ' + user.username + ' is ' + str(request.POST.dict()))
    load_unit_dict = LOAD_UNIT_HANDLE_DICT
    try:
        wms = request.POST['wms_code']
        description = request.POST['sku_desc']
        zone = request.POST['zone_id']
        if not wms or not description:
            return HttpResponse('Missing Required Fields')
        data = get_or_none(SKUMaster, {'wms_code': wms, 'user': user.id})
        image_file = request.FILES.get('files-0', '')
        if image_file:
            save_image_file(image_file, data, user)
        for key, value in request.POST.iteritems():

            if key == 'status':
                if value == 'Active':
                    value = 1
                else:
                    value = 0
            elif key == 'qc_check':
                if value == 'Enable':
                    value = 1
                else:
                    value = 0
            elif key == 'threshold_quantity':
                if not value:
                    value = 0
            elif key == 'zone_id' and value:
                zone = get_or_none(ZoneMaster, {'zone': value, 'user': user.id})
                key = 'zone_id'
                if zone:
                    value = zone.id
            elif key == 'ean_number':
                if not value:
                    value = 0
                else:
                    ean_status = check_ean_number(data.sku_code, value, user)
                    if ean_status:
                        return HttpResponse(ean_status)
            elif key == 'load_unit_handle':
                value = load_unit_dict.get(value.lower(), 'unit')
            elif key == 'size_type':
                check_update_size_type(data, value)
                continue
            elif key == 'hot_release':
                value = 1 if (value.lower() == 'enable') else 0;
                check_update_hot_release(data, value)
                continue
            setattr(data, key, value)

        data.save()

        update_marketplace_mapping(user, data_dict=dict(request.POST.iterlists()), data=data)
        # update master sku txt file
        status = subprocess.check_output(['pgrep -lf sku_master_file_creator'], stderr=subprocess.STDOUT, shell=True)
        if "python" not in status:
            sku_query = "%s %s/%s %s&" % ("python", settings.BASE_DIR, "sku_master_file_creator.py", str(user.id))
            subprocess.call(sku_query, shell=True)
        else:
            print "already running"

        insert_update_brands(user)

        # Sync sku's with sister warehouses
        sync_sku_switch = get_misc_value('sku_sync', user.id)
        if sync_sku_switch == 'true':
            all_users = get_related_users(user.id)
            create_update_sku([data], all_users)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update SKU Data failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse('Update SKU Failed')

    return HttpResponse('Updated Successfully')


def update_marketplace_mapping(user, data_dict={}, data=''):
    if 'market_sku_type' not in data_dict.keys():
        return

    for i in range(len(data_dict['market_sku_type'])):
        if (data_dict['market_sku_type'][i] and data_dict['marketplace_code'][i]):
            market_mapping = MarketplaceMapping.objects.filter(sku_type=data_dict['market_sku_type'][i],
                                                               description=data_dict['description'][i],
                                                               marketplace_code=data_dict['marketplace_code'][i],
                                                               sku_id=data.id, sku__user=user.id)
            if market_mapping:
                continue

            mapping_data = {'sku_id': data.id, 'sku_type': data_dict['market_sku_type'][i],
                            'marketplace_code': data_dict['marketplace_code'][i],
                            'description': data_dict['description'][i],
                            'creation_date': datetime.datetime.now()}
            map_data = MarketplaceMapping(**mapping_data)
            map_data.save()


def get_supplier_update(request):
    data_id = request.GET['data_id']
    filter_params = {'id': data_id, 'user': 4}
    data = get_or_none(SupplierMaster, filter_params)
    return HttpResponse(json.dumps({'data': data, 'update_supplier': SUPPLIER_FIELDS}))


@csrf_exempt
@login_required
@get_admin_user
def get_bom_data(request, user=''):
    all_data = []
    data_id = request.GET['data_id']
    bom_master = BOMMaster.objects.filter(product_sku__sku_code=data_id, product_sku__user=user.id)
    for bom in bom_master:
        cond = (bom.material_sku.sku_code)
        all_data.append({"Material_sku": cond, "Material_Quantity": get_decimal_limit(user.id, bom.material_quantity),
                         "Units": bom.unit_of_measurement.upper(),
                         "BOM_ID": bom.id, "wastage_percent": bom.wastage_percent})
    title = 'Update BOM Data'
    return HttpResponse(json.dumps({'data': all_data, 'product_sku': data_id}))


@csrf_exempt
@login_required
@get_admin_user
def delete_bom_data(request, user=''):
    for key, value in request.GET.iteritems():
        bom_master = BOMMaster.objects.get(id=value, product_sku__user=user.id).delete()

    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def update_supplier_values(request, user=''):
    """ Update Supplier Data """

    log.info('Update Supplier request params for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        data_id = request.POST['id']
        data = get_or_none(SupplierMaster, {'id': data_id, 'user': user.id})
        old_name = data.name

        create_login = request.POST.get('create_login', '')
        password = request.POST.get('password', '')
        username = request.POST.get('username', '')
        login_created = request.POST.get('login_created', '')

        for key, value in request.POST.iteritems():
            if key not in data.__dict__.keys():
                continue
            if key == 'status':
                if value == 'Active':
                    value = 1
                else:
                    value = 0
            setattr(data, key, value)

        data.save()
        if create_login == 'true':
            status_msg, new_user_id = create_update_user(data.name, data.email_id, data.phone_number,
                                                         password, username, role_name='supplier')
            if 'already' in status_msg:
                return HttpResponse(status_msg)
            UserRoleMapping.objects.create(role_id=data.id, role_type='supplier', user_id=new_user_id,
                                           creation_date=datetime.datetime.now())
        name_ch = False
        if old_name != data.name:
            name_ch = True
        if login_created == 'true':
            if password or name_ch:
                user_role_mapping = UserRoleMapping.objects.filter(role_id=data.id, role_type='supplier')
                if user_role_mapping:
                    update_user_password(data.name, data.email_id, data.phone_number, password,
                                         user_role_mapping[0].user_id, user, 'Supplier')
                #update_customer_password(data, password, user)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Supplier Values failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse('Update Supplier Failed')
    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def insert_supplier(request, user=''):
    """ Add New Supplier"""

    log.info('Add New Supplier request params for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        supplier_id = request.POST['id']
        if not supplier_id:
            return HttpResponse('Missing Required Fields')
        data = filter_or_none(SupplierMaster, {'id': supplier_id})
        status_msg = 'Supplier Exists'
        sku_status = 0
        rep_email = filter_or_none(SupplierMaster, {'email_id': request.POST['email_id'], 'user': user.id})
        rep_phone = filter_or_none(SupplierMaster, {'phone_number': request.POST['phone_number'], 'user': user.id})
        if rep_email and request.POST['email_id']:
            return HttpResponse('Email already exists')
        if rep_phone and request.POST['phone_number']:
            return HttpResponse('Phone Number already exists')

	create_login = request.POST.get('create_login', '')
        password = request.POST.get('password', '')
        username = request.POST.get('username', '')
        login_created = request.POST.get('login_created', '')
        if not data:
            data_dict = copy.deepcopy(SUPPLIER_DATA)
            for key, value in request.POST.iteritems():
                if key == 'status':
                    if value == 'Active':
                        value = 1
                    else:
                        value = 0
                if value == '':
                    continue
                if key in ['login_created', 'create_login', 'password', 'username']:
                    continue
                data_dict[key] = value

            data_dict['user'] = user.id
            supplier_master = SupplierMaster(**data_dict)
            supplier_master.save()
            status_msg = 'New Supplier Added'
	    if create_login == 'true':
	        data = supplier_master
                status_msg, new_user_id = create_update_user(data.name, data.email_id, data.phone_number,
                                                         password, username, role_name='supplier')
                if 'already' in status_msg:
                    return HttpResponse(status_msg)
                UserRoleMapping.objects.create(role_id=data.id, role_type='supplier', user_id=new_user_id,
                                           creation_date=datetime.datetime.now())

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Add New Supplier failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        status_msg = 'Add Supplier Failed'
    return HttpResponse(status_msg)


@csrf_exempt
@get_admin_user
def update_sku_supplier_values(request, user=''):
    data_id = request.POST['data-id']
    data = get_or_none(SKUSupplier, {'id': data_id})
    for key, value in request.POST.iteritems():
        if key in ('moq', 'price'):
            if not value:
                value = 0
        elif key == 'preference':
            sku_supplier = SKUSupplier.objects.exclude(id=data.id).filter(Q(sku_id=data.sku_id) & Q(preference=value),
                                                                          sku__user=user.id)
            if sku_supplier:
                return HttpResponse('Preference matched with existing WMS Code')

        setattr(data, key, value)
    data.save()
    return HttpResponse('Updated Successfully')


@csrf_exempt
@get_admin_user
def insert_mapping(request, user=''):
    data_dict = copy.deepcopy(SUPPLIER_SKU_DATA)
    integer_data = ('preference')
    for key, value in request.POST.iteritems():

        if key == 'wms_code':
            sku_id = SKUMaster.objects.filter(wms_code=value.upper(), user=user.id)
            if not sku_id:
                return HttpResponse('Wrong WMS Code')
            key = 'sku'
            value = sku_id[0]

        elif key == 'supplier_id':
            supplier = SupplierMaster.objects.get(id=value, user=user.id)
            value = supplier.id

        elif key == 'price' and not value:
            value = 0

        elif key in integer_data:
            if not value.isdigit():
                return HttpResponse('Plese enter Integer values for Priority and MOQ')

        if key == 'preference':
            preference = value

        if value != '':
            data_dict[key] = value

    data = SKUSupplier.objects.filter(supplier_id=supplier, sku_id=sku_id[0].id)
    if data:
        return HttpResponse('Duplicate Entry')
    preference_data = SKUSupplier.objects.filter(sku_id=sku_id[0].id).order_by('-preference').\
                                            values_list('preference', flat=True)
    min_preference = 0
    if preference_data:
        min_preference = int(preference_data[0])
    if int(preference) in preference_data:
        return HttpResponse('Duplicate Priority, Next incremantal value is %s' % str(min_preference + 1))

    sku_supplier = SKUSupplier(**data_dict)
    sku_supplier.save()
    return HttpResponse('Added Successfully')


def update_user_password(data_name, data_email, phone_number, password, cur_user_id, user, role_name):
    cur_user = User.objects.get(id=cur_user_id)
    if password:
        cur_user.set_password(password)
    cur_user.email = data_email
    cur_user.first_name  = data_name
    cur_user.save()
    if user.first_name:
        name = user.first_name
    else:
        name = user.username
    if password:
        password_notification_message(cur_user.username, password, name, phone_number, role_name)


def update_customer_password(data, password, user):
    customer_user_map = CustomerUserMapping.objects.filter(customer_id=data.id, customer__user=data.user)
    if customer_user_map:
        customer_user = customer_user_map[0].user
        if password:
            customer_user.set_password(password)
        customer_user.email = data.email_id
        customer_user.first_name = data.name
        customer_user.save()
        if user.first_name:
            name = user.first_name
        else:
            name = user.username
        if password:
            password_notification_message(customer_user.username, password, name, data.phone_number)



@csrf_exempt
@login_required
@get_admin_user
def update_customer_values(request, user=''):
    """ Update Customer Data"""

    log.info('Update Customer Values request params for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        data_id = request.POST['customer_id']
        username = request.POST.get('username', '')
        data = get_or_none(CustomerMaster, {'customer_id': data_id, 'user': user.id})
        create_login = request.POST.get('create_login', '')
        login_created = request.POST.get('login_created', '')
        password = request.POST.get('password', '')
        _name = data.name
        for key, value in request.POST.iteritems():
            if key not in data.__dict__.keys():
                continue
            if key == 'status':
                if value == 'Active':
                    value = 1
                else:
                    value = 0
            if key == 'email_id':
                if not value:
                    continue
                setattr(data, key, value)
            if key in ['discount_percentage', 'markup']:
                if not value:
                    value = 0
                setattr(data, key, float(value))
            else:
                setattr(data, key, value)

        data.save()
        if create_login == 'true':
            status_msg, new_user_id = create_update_user(data.name, data.email_id, data.phone_number,
                                                         password, username, role_name='customer')
            #status_msg = create_update_user(data, password, username)
            if 'already' in status_msg:
                return HttpResponse(status_msg)
            else:
                CustomerUserMapping.objects.create(customer_id=data.id, user_id=new_user_id,
                                                   creation_date=datetime.datetime.now())
        name_ch = False
        if _name != data.name:
            name_ch = True
        if login_created == 'true':
            if password or name_ch:
                customer_user_map = CustomerUserMapping.objects.filter(customer_id=data.id, customer__user=data.user)
                if customer_user_map:
                    cur_user_id = customer_user_map[0].user.id
                    update_user_password(data.name, data.email_id, data.phone_number, password, cur_user_id, user,
                                         role_name='Customer')
                update_customer_password(data, password, user)

        # Level 2 price type creation
        create_level_wise_price_type(2, 'D1-R', data, user)

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Customer Values failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse('Update Customer Data Failed')
    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def update_corporate_values(request, user=''):
    """ Update Corporate Data"""
    log.info('Update Corporate Values request params for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        data_id = request.POST['corporate_id']
        data = get_or_none(CorporateMaster, {'corporate_id': data_id, 'user': user.id})
        _name = data.name
        for key, value in request.POST.iteritems():
            if key not in data.__dict__.keys():
                continue
            if key == 'status':
                if value == 'Active':
                    value = 1
                else:
                    value = 0
            if key == 'email_id':
                if not value:
                    continue
                setattr(data, key, value)

            setattr(data, key, value)
        data.save()
        name_ch = False
        if _name != data.name:
            name_ch = True
        
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Corporate Values failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse('Update Corporate Data Failed')
    return HttpResponse('Updated Successfully')


def create_level_wise_price_type(level, price_type, customer_master, user):
    if price_type:
        customer_price_type = CustomerPricetypes.objects.filter(level=level, price_type=price_type,
                                                                customer_id=customer_master.id)

        if not customer_price_type:
            CustomerPricetypes.objects.create(level=level, price_type=price_type,
                                              customer_id=customer_master.id, status=1,
                                              creation_date=datetime.datetime.now())
            log.info('Level type 2 created for %s login for customer %s and price type is %s' % (
                user.username, customer_master.name, price_type
            ))

@csrf_exempt
@login_required
@get_admin_user
def insert_corporate(request, user=''):
    """ Add New Corporate"""
    log.info('Add New Corporate request params for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        corporate_id = request.POST['corporate_id']
        if not corporate_id:
            return HttpResponse('Missing Required Fields')
        data = filter_or_none(CorporateMaster, {'corporate_id': corporate_id, 'user': user.id})
        status_msg = 'Corporate Exists'
        sku_status = 0
        if not data:
            data_dict = copy.deepcopy(CORPORATE_DATA)
            for key, value in request.POST.iteritems():
                if key == 'status':
                    if value == 'Active':
                        value = 1
                    else:
                        value = 0
                if value == '':
                    continue
                data_dict[key] = value
            data_dict['user'] = user.id
            corporate_master = CorporateMaster(**data_dict)
            corporate_master.save()
            status_msg = 'New Corporate Added' 
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Add New Corporate failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
    
    return HttpResponse(status_msg)


@csrf_exempt
@login_required
@get_admin_user
def insert_customer(request, user=''):
    """ Add New Customer"""
    log.info('Add New Customer request params for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        loop_exclude_list = ['create_login', 'password', 'login_created', 'username', 'data-id', 'login-created',
                             'level_2_price_type']
        customer_id = request.POST['customer_id']
        create_login = request.POST.get('create_login', '')
        password = request.POST.get('password', '')
        username = request.POST.get('username', '')
        level_2_price_type = request.POST.get('level_2_price_type', '')
        if not customer_id:
            return HttpResponse('Missing Required Fields')
        data = filter_or_none(CustomerMaster, {'customer_id': customer_id, 'user': user.id})
        status_msg = 'Customer Exists'
        sku_status = 0
        # rep_email = filter_or_none(CustomerMaster, {'email_id': request.POST['email_id'], 'user': user.id})
        # rep_phone = filter_or_none(CustomerMaster, {'phone_number': request.POST['phone_number'], 'user': user.id})
        # if rep_email:
        #    return HttpResponse('Email already exists')
        # if rep_phone:
        #    return HttpResponse('Phone Number already exists')

        if create_login == 'true':
            if not username:
                return HttpResponse('Username is Mandatory')
            rep_username = filter_or_none(User, {'username': username})
            if rep_username:
                return HttpResponse('Username already exists')
        if not data:
            data_dict = copy.deepcopy(CUSTOMER_DATA)
            for key, value in request.POST.iteritems():
                if key in loop_exclude_list:
                    continue
                if key == 'status':
                    if value == 'Active':
                        value = 1
                    else:
                        value = 0
                if value == '':
                    continue
                data_dict[key] = value

            data_dict['user'] = user.id
            customer_master = CustomerMaster(**data_dict)
            customer_master.save()

            # Level 2 price type creation
            create_level_wise_price_type(2, level_2_price_type, customer_master, user)
            status_msg = 'New Customer Added'
            if create_login == 'true':
                status_msg, new_user_id = create_update_user(customer_master.name, customer_master.email_id,
                                                             customer_master.phone_number, password, username,
                                                             role_name='customer')
                CustomerUserMapping.objects.create(customer_id=customer_master.id, user_id=new_user_id,
                                                   creation_date=datetime.datetime.now())
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Add New Customer failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))

    return HttpResponse(status_msg)


@csrf_exempt
@login_required
@get_admin_user
def update_customer_sku_mapping(request, user=""):
    data_id = request.POST['data-id']
    cust_name = request.POST['customer_name']
    cust_sku = request.POST['sku_code']
    cust_sku_code = request.POST.get('customer_sku_code', '')
    customer_id = request.POST['customer_id']
    data = CustomerSKU.objects.filter(id=data_id)
    if not data:
        return HttpResponse("This Customer SKU Mapping doesn't exists")
    sku_data = SKUMaster.objects.filter(sku_code=cust_sku, user=user.id)
    cust_sku = CustomerSKU.objects.filter(customer__customer_id=customer_id, customer__name=cust_name,
                                          sku__sku_code=cust_sku, sku__user=user.id).exclude(id=data_id)
    if not sku_data:
        return HttpResponse("Given SKU Code doesn't exists")
    elif cust_sku:
        return HttpResponse("Mapping Already exists")
    else:
        data = data[0]
        data.sku_id = sku_data[0].id
        data.customer_sku_code = cust_sku_code
        data.save()
    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def insert_customer_sku(request, user=''):
    customer_id = request.POST['customer_id']
    if not ":" in customer_id:
        return HttpResponse('Given Customer ID / Name not correct.')
    ID = str(customer_id.split(":")[0])
    name = str(customer_id.split(":")[1][1:])
    customer_sku_data = filter_or_none(CustomerSKU,
                                       {'customer__customer_id': ID, 'sku__sku_code': request.POST['sku_code'],
                                        'sku__user': user.id})
    if customer_sku_data:
        return HttpResponse('Customer SKU Mapping already exists.')
    status_msg = 'Supplier Exists'
    sku_status = 0
    customer_data = filter_or_none(CustomerMaster, {'customer_id': ID, 'user': user.id})
    customer_sku = filter_or_none(SKUMaster, {'sku_code': request.POST['sku_code'], 'user': user.id})
    if not customer_data:
        return HttpResponse("customer doesn't exists.")
    elif not customer_sku:
        return HttpResponse("Customer SKU doesn't exists.")
    data_dict = copy.deepcopy(CUSTOMER_SKU_DATA)
    for key, value in request.POST.iteritems():
        if key == 'customer_id':
            value = customer_data[0].id
        elif key == 'sku_code':
            value = customer_sku[0].id
            key = "sku_id"
        elif key == 'price':
            if not value:
                value = 0
        data_dict[key] = value

    customer = CustomerSKU(**data_dict)
    customer.save()
    status_msg = 'New Customer SKU Mapping Added'
    return HttpResponse(status_msg)


@csrf_exempt
@login_required
@get_admin_user
def search_customer_sku_mapping(request, user=''):
    data_id = request.GET.get('q', '')
    if request.GET.get('type', '') == 'shipment':
        data = Picklist.objects.exclude(order__customer_name='').filter(Q(order__customer_id__icontains=data_id) |
                                                                        Q(order__customer_name__icontains=data_id),
                                                                        picked_quantity__gt=0,
                                                                        status__icontains='picked',
                                                                        order__user=user.id).values_list(
            'order__customer_id', 'order__customer_name').distinct()
    elif request.GET.get('type', '') == 'orders':
        data = OrderDetail.objects.exclude(customer_name='').filter(
            Q(customer_id__icontains=data_id) | Q(customer_name__icontains=data_id),
            quantity__gt=0, status=1, user=user.id).values_list('customer_id', 'customer_name'). \
            distinct()
    else:
        data = CustomerMaster.objects.filter(Q(customer_id__icontains=data_id) | Q(name__icontains=data_id),
                                             user=user.id). \
            values_list('customer_id', 'name').distinct()
    search_data = []
    if data:
        for record in data[:10]:
            search_data.append('%s:%s' % (record[0], record[1]))
    return HttpResponse(json.dumps(search_data))


@csrf_exempt
@login_required
@get_admin_user
def get_supplier_list(request, user=''):
    suppliers = SupplierMaster.objects.filter(user=user.id)
    supplier_list = []
    for supplier in suppliers:
        supplier_list.append({'id': supplier.id, 'name': supplier.name})
    return HttpResponse(json.dumps({'suppliers': supplier_list}))


def validate_bom_data(all_data, product_sku, user):
    status = ''
    m_status = ''
    q_status = ''
    d_status = ''
    p_sku = SKUMaster.objects.filter(sku_code=product_sku, user=user)
    if not p_sku:
        status = "Invalid Product SKU Code %s" % product_sku
    else:
        if p_sku[0].sku_type not in ('FG', 'RM', 'CS'):
            status = 'Invalid Product SKU Code %s' % product_sku

    for key, value in all_data.iteritems():
        if product_sku == key:
            status = "Product and Material SKU's should not be equal"
        for val in value:
            m_sku = SKUMaster.objects.filter(sku_code=key, user=user)
            if not m_sku:
                if not m_status:
                    m_status = "Invalid Material SKU Code %s" % key
                else:
                    m_status += ', %s' % key
            else:
                if m_sku[0].sku_type != 'RM':
                    if not m_status:
                        m_status = 'Invalid Material SKU Code %s' % key
                    else:
                        m_status += ', %s' % key

            if not val[0]:
                if not q_status:
                    q_status = 'Quantity missing for Material Sku Codes %s' % key
                else:
                    q_status += ', %s' % key
            bom_master = BOMMaster.objects.filter(product_sku__sku_code=product_sku, material_sku__sku_code=key)
            if bom_master and not val[2]:
                if not d_status:
                    d_status = 'SKU Codes already exists (%s,%s)' % (product_sku, key)
                else:
                    d_status += ', (%s,%s)' % (product_sku, key)
    if m_status:
        status += ' ' + m_status
    if q_status:
        status += ' ' + q_status
    if d_status:
        status += ' ' + d_status
    return status


def insert_bom(all_data, product_code, user):
    product_sku = SKUMaster.objects.get(sku_code=product_code, user=user)
    for key, value in all_data.iteritems():
        for val in value:
            bom = BOMMaster.objects.filter(product_sku__sku_code=product_code, material_sku__sku_code=key,
                                           product_sku__user=user)
            if bom:
                bom = bom[0]
                bom.material_quantity = float(val[0])
                bom.unit_of_measurement = val[1]
                bom.wastage_percent = 0
                if val[3]:
                    bom.wastage_percent = float(val[3])
                bom.save()
            else:
                material_sku = SKUMaster.objects.get(sku_code=key, user=user)
                bom_dict = copy.deepcopy(ADD_BOM_FIELDS)
                bom_dict['product_sku_id'] = product_sku.id
                bom_dict['material_sku_id'] = material_sku.id
                bom_dict['unit_of_measurement'] = val[1]
                if val[0]:
                    bom_dict['material_quantity'] = float(val[0])
                if val[3]:
                    bom_dict['wastage_percent'] = val[3]
                bom_master = BOMMaster(**bom_dict)
                bom_master.save()


@csrf_exempt
@login_required
@get_admin_user
def insert_bom_data(request, user=''):
    all_data = {}
    product_sku = request.POST.get('product_sku', '')
    if not product_sku:
        return HttpResponse('Product Sku Code should not be empty')
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['material_sku'])):
        if not data_dict['material_sku'][i]:
            continue
        data_id = ''
        if data_dict['id'][i]:
            data_id = data_dict['id'][i]
        cond = (data_dict['material_sku'][i])
        all_data.setdefault(cond, [])
        all_data[cond].append([data_dict['material_quantity'][i], data_dict['unit_of_measurement'][i], data_id,
                               data_dict['wastage_percent'][i]])
    status = validate_bom_data(all_data, product_sku, user.id)
    if not status:
        all_data = insert_bom(all_data, product_sku, user.id)
        status = "Added Successfully"
    return HttpResponse(status)


@csrf_exempt
@login_required
@get_admin_user
def insert_discount(request, user=''):
    save = {}
    for key, value in request.POST.iteritems():
        if not value:
            continue
        save[key] = value

    if save.get('sku'):
        sku = SKUMaster.objects.filter(wms_code=save['sku'], user=user.id)
        if not sku:
            return HttpResponse("Given SKU not found")

        sku = sku[0]
        sku.discount_percentage = float(save['sku_discount'].strip('%'))
        sku.save()

    if save.get('category'):
        category = CategoryDiscount.objects.filter(category=save.get('category', ''), user_id=user.id)
        if category:
            category = category[0]
            category.discount = float(save['category_discount'].strip('%'))
            category.save()
        else:
            category = CategoryDiscount(discount=float(save['category_discount'].strip('%')),
                                        category=save.get('category', ''),
                                        creation_date=datetime.datetime.now(), user_id=user.id)
            category.save()

    return HttpResponse('Updated Successfully')


def validate_customer_warehouse(customer_name, user, warehouse=''):
    customer_status = False
    child_warehouse = UserGroups.objects.filter(admin_user=user).values_list('user_id', flat=True)
    if not child_warehouse:
        customer_status = True
    customer = CustomerUserMapping.objects.filter(customer__user__in=child_warehouse, user__username=customer_name)
    if not customer:
        customer_status = True
    if customer_status:
        return "Customer Not Found", {}
    customer_check = WarehouseCustomerMapping.objects.filter(customer=customer[0].customer, status=1)
    if customer_check:
        if warehouse:
            if warehouse != customer_check[0].warehouse.id:
                return "Customer Already Mapped", {}
        else:
            return "Customer Already Mapped", {}
    return "", customer[0]


@csrf_exempt
@login_required
@get_admin_user
def update_warehouse_user(request, user=''):
    username = request.POST['username']
    user_dict = copy.deepcopy(ADD_USER_DICT)
    user_profile_dict = copy.deepcopy(ADD_WAREHOUSE_DICT)
    user_profile = UserProfile.objects.get(user__username=username)
    customer_name = request.POST.get('customer_name', '')
    if customer_name:
        status, customer = validate_customer_warehouse(customer_name, user, user_profile.user.id)
        if status:
            return HttpResponse(status)
        mapping = WarehouseCustomerMapping.objects.filter(warehouse=user_profile.user, status=1)
        if mapping:
            mapping = mapping[0]
            if mapping.customer_id != customer.customer.id:
                mapping.status = 0
                mapping.save()
                mapping = WarehouseCustomerMapping.objects.filter(warehouse=user_profile.user,
                                                                  customer_id=customer.customer.id, status=0)
                if mapping:
                    mapping = mapping[0]
                    mapping.status = 1
                    mapping.save()
                else:
                    WarehouseCustomerMapping.objects.create(warehouse_id=user_profile.user.id,
                                                            customer_id=customer.customer.id)
        else:
            WarehouseCustomerMapping.objects.create(warehouse_id=user_profile.user.id, customer_id=customer.customer.id)

    for key, value in request.POST.iteritems():
        if key in user_dict.keys() and not key in ['username', 'customer_name']:
            setattr(user_profile.user, key, value)
        if key in user_profile_dict.keys():
            setattr(user_profile, key, value)
    user_profile.user.save()
    user_profile.save()
    return HttpResponse("Updated Successfully")


@csrf_exempt
@login_required
@get_admin_user
def add_warehouse_user(request, user=''):
    status = ''
    exist_user_profile = UserProfile.objects.get(user_id=user.id)
    user_dict = copy.deepcopy(ADD_USER_DICT)
    user_profile_dict = copy.deepcopy(ADD_WAREHOUSE_DICT)
    for key, value in request.POST.iteritems():
        if key in user_dict.keys():
            user_dict[key] = value
        if key in user_profile_dict.keys():
            user_profile_dict[key] = value
    if not user_dict['password'] == request.POST['re_password']:
        status = "Passwords doesn't match"

    customer_name = request.POST.get('customer_name', '')
    if customer_name:
        customer_status, customer = validate_customer_warehouse(customer_name, user)
        if customer_status:
            return HttpResponse(customer_status)

    user_exists = User.objects.filter(username=user_dict['username'])
    if not user_exists and not status:
        user_dict['last_login'] = datetime.datetime.now()
        new_user = User.objects.create_user(**user_dict)
        new_user.is_staff = True
        new_user.save()
        user_profile_dict['user_id'] = new_user.id
        user_profile_dict['location'] = user_profile_dict['state']
        user_profile_dict['prefix'] = new_user.username[:3]
        if not user_profile_dict.get('pin_code', 0):
            user_profile_dict['pin_code'] = 0
        if not user_profile_dict.get('phone_number', 0):
            user_profile_dict['phone_number'] = 0
        user_profile_dict['user_type'] = exist_user_profile.user_type
        user_profile = UserProfile(**user_profile_dict)
        user_profile.save()
        add_user_type_permissions(user_profile)
        group, created = Group.objects.get_or_create(name=new_user.username)
        admin_dict = {'group_id': group.id, 'user_id': new_user.id}
        admin_group = AdminGroups(**admin_dict)
        admin_group.save()
        new_user.groups.add(group)
        warehouse_admin = get_warehouse_admin(user)
        UserGroups.objects.create(admin_user_id=warehouse_admin.id, user_id=new_user.id)
        if customer_name:
            WarehouseCustomerMapping.objects.create(warehouse_id=new_user.id, customer_id=customer.customer.id)
        status = 'Added Successfully'
    else:
        status = 'Username already exists'
    return HttpResponse(status)


@csrf_exempt
def get_warehouse_user_data(request, user=''):
    username = request.GET['username']
    user_profile = UserProfile.objects.get(user__username=username)
    mapping = WarehouseCustomerMapping.objects.filter(warehouse=user_profile.user, status=1)
    customer_username = ''
    customer_fullname = ''
    if mapping:
        mapping = mapping[0]
        customer_profile = CustomerUserMapping.objects.filter(customer__id=mapping.customer.id)
        if customer_profile:
            customer_username = customer_profile[0].user.username
            customer_fullname = customer_profile[0].user.first_name
    data = {'username': user_profile.user.username, 'first_name': user_profile.user.first_name,
            'last_name': user_profile.user.last_name, 'phone_number': user_profile.phone_number,
            'email': user_profile.user.email, 'country': user_profile.country, 'state': user_profile.state,
            'city': user_profile.city, 'address': user_profile.address, 'pin_code': user_profile.pin_code,
            'warehouse_type': user_profile.warehouse_type, 'warehouse_level': user_profile.warehouse_level,
            'customer_name': customer_username, 'customer_fullname': customer_fullname,
            'min_order_val': user_profile.min_order_val, 'level_name': user_profile.level_name,
            'zone': user_profile.zone}
    return HttpResponse(json.dumps({'data': data}))


@csrf_exempt
@login_required
def delete_market_mapping(request):
    data_id = request.GET.get('data_id', '')
    if data_id:
        MarketplaceMapping.objects.get(id=data_id).delete()
    return HttpResponse("Deleted Successfully")


@csrf_exempt
@login_required
@get_admin_user
def get_vendor_data(request, user=''):
    data_id = request.GET['data_id']
    filter_params = {'vendor_id': data_id, 'user': user.id}
    data = get_or_none(VendorMaster, filter_params)
    total_data = {}
    if data:
        total_data['vendor_id'] = data.vendor_id
        total_data['name'] = data.name
        total_data['email_id'] = data.email_id
        total_data['phone_number'] = data.phone_number
        total_data['address'] = data.address
        total_data['status'] = data.status
    else:
        return HttpResponse("fail")
    return HttpResponse(json.dumps(total_data))


@csrf_exempt
@login_required
@get_admin_user
def update_vendor_values(request, user=''):
    data_id = request.GET['vendor_id']
    data = get_or_none(VendorMaster, {'vendor_id': data_id, 'user': user.id})
    for key, value in request.GET.iteritems():
        if key == 'status':
            if value == 'Active':
                value = 1
            else:
                value = 0
        setattr(data, key, value)

    data.save()
    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def insert_vendor(request, user=''):
    vendor_id = request.GET['vendor_id']
    if not vendor_id:
        return HttpResponse('Missing Required Fields')
    data = filter_or_none(VendorMaster, {'vendor_id': vendor_id, 'user': user.id})
    status_msg = 'Vendor Exists'
    sku_status = 0
    rep_email = filter_or_none(VendorMaster, {'email_id': request.GET['email_id'], 'user': user.id})
    rep_phone = filter_or_none(VendorMaster, {'phone_number': request.GET['phone_number'], 'user': user.id})
    if rep_email:
        return HttpResponse('Email already exists')
    if rep_phone:
        return HttpResponse('Phone Number already exists')

    if not data:
        data_dict = copy.deepcopy(VENDOR_DATA)
        for key, value in request.GET.iteritems():
            if key == 'status':
                if value == 'Active':
                    value = 1
                else:
                    value = 0
            if value == '':
                continue
            data_dict[key] = value

        data_dict['user'] = user.id
        vendor_master = VendorMaster(**data_dict)
        vendor_master.save()
        status_msg = 'New Vendor Added'

    return HttpResponse(status_msg)


def update_zone_marketplace_mapping(zone, marketplace_list):
    mappings = ZoneMarketplaceMapping.objects.filter(zone__user=zone.user, zone__zone=zone.zone)
    marketplace = []
    resp = ''
    if marketplace_list:
        marketplace = marketplace_list.split(",")
    if mappings:
        for mapping in mappings:
            status = 0
            if mapping.marketplace in marketplace:
                marketplace.remove(mapping.marketplace)
                status = 1
            mapping.status = status
            mapping.save()
        resp = 'updated'
    if marketplace:
        for mkp in marketplace:
            zone_marketplace = ZoneMarketplaceMapping(**{'zone_id': zone.id, 'marketplace': mkp})
            zone_marketplace.save()
        reps = 'created'
    return resp


@csrf_exempt
@login_required
@get_admin_user
def add_zone(request, user=''):
    zone = request.GET.get('zone', '')
    if not zone:
        status = 'Please enter ZONE value'
    data = ZoneMaster.objects.filter(zone=zone, user=user.id)
    update = request.GET.get('update', '')
    marketplace = request.GET.get('marketplaces', '')
    if update == 'true':
        if not data:
            status = 'ZONE not found'
        else:
            update_zone_marketplace_mapping(data[0], marketplace)
            status = 'Update Successfully'
    else:
        if not data:
            location_dict = copy.deepcopy(ZONE_DATA)
            location_dict['user'] = user.id
            location_dict['zone'] = zone
            loc_master = ZoneMaster(**location_dict)
            loc_master.save()
            update_zone_marketplace_mapping(loc_master, marketplace)
            status = 'Added Successfully'
        else:
            status = 'Entry Exists in DB'
    return HttpResponse(status)


@csrf_exempt
@login_required
@get_admin_user
def get_zone_data(request, user=''):
    zone = request.GET.get('zone', '')
    data = ZoneMaster.objects.filter(user=user.id, zone=zone)
    resp = {'zone': zone}
    if not data:
        status = 'ZONE not found'
    else:
        marketplace_list = list(
            ZoneMarketplaceMapping.objects.filter(zone__user=user.id, zone__zone=zone, status=1).values_list(
                'marketplace', flat=True))
        resp['marketplaces'] = marketplace_list
        status = 'Success'
    resp['msg'] = status
    return HttpResponse(json.dumps(resp))


@csrf_exempt
@login_required
@get_admin_user
def add_location(request, user=''):
    loc_id = request.GET['location']
    data = LocationMaster.objects.filter(location=loc_id, zone__user=user.id)
    if not data and loc_id:
        location_dict = copy.deepcopy(LOC_DATA)

        for key, value in request.GET.iteritems():
            if key == 'status':
                value = 0
                if value == 'Active':
                    value = 1
            elif key == 'zone_id':
                value = ZoneMaster.objects.get(zone=value, user=user.id).id
            elif key == 'location_group':
                continue
            if not value:
                continue
            location_dict[key] = value

        loc_master = LocationMaster(**location_dict)
        loc_master.save()
        loc_group = request.GET.get('location_group', '')
        if loc_group:
            save_location_group(loc_master.id, loc_group, user)
        status = 'Added Successfully'
    else:
        status = 'Entry Exists in DB'

    if not loc_id:
        status = 'Missing required parameters'
    return HttpResponse(status)


def save_location_group(data_id, value, user):
    all_groups = SKUGroups.objects.filter(user=user.id).values_list('group', flat=True)
    for sku_group in all_groups:
        loc_map = LocationGroups.objects.filter(location__zone__user=user.id, location_id=data_id, group=sku_group)
        if sku_group in value:
            if not loc_map:
                map_dict = copy.deepcopy(LOCATION_GROUP_FIELDS)
                map_dict['group'] = sku_group
                map_dict['location_id'] = data_id
                new_map = LocationGroups(**map_dict)
                new_map.save()
        elif loc_map:
            loc_map.delete()


@csrf_exempt
@login_required
@get_admin_user
def update_location(request, user=''):
    loc_id = request.GET['location']
    data = LocationMaster.objects.get(location=loc_id, zone__user=user.id)
    for key, value in request.GET.iteritems():
        if key in ('max_capacity', 'pick_sequence', 'fill_sequence', 'pallet_capacity'):
            if not value:
                value = 0
        elif key == 'location_group':
            value = value.split(',')
            save_location_group(data.id, value, user)
            continue

        elif key == 'status':
            if value == 'Active':
                value = 1
            else:
                value = 0
        elif key == 'zone_id':
            continue
        setattr(data, key, value)
    data.save()
    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def get_zones_list(request, user=''):
    zones_list = list(ZoneMaster.objects.filter(user=user.id).values_list('zone', flat=True))
    all_groups = list(SKUGroups.objects.filter(user=user.id).values_list('group', flat=True))
    market_places = list(Marketplaces.objects.filter(user=user.id).values_list('name', flat=True))
    size_names = SizeMaster.objects.filter(user=user.id)
    product_types = list(TaxMaster.objects.filter(user_id=user.id).values_list('product_type', flat=True).distinct())
    sizes_list = []
    for sizes in size_names:
        sizes_list.append({'size_name': sizes.size_name, 'size_values': (sizes.size_value).split('<<>>')})
    sizes_list.append({'size_name': 'Default', 'size_values': copy.deepcopy(SIZES_LIST)})
    return HttpResponse(json.dumps(
        {'zones': zones_list, 'sku_groups': all_groups, 'market_places': market_places, 'sizes_list': sizes_list,
         'product_types': product_types, 'sub_categories': SUB_CATEGORIES}))


@csrf_exempt
@login_required
@get_admin_user
def insert_sku(request, user=''):
    """ Insert New SKU Details """

    log.info('Insert SKU request params for ' + user.username + ' is ' + str(request.POST.dict()))
    load_unit_dict = LOAD_UNIT_HANDLE_DICT
    try:
        wms = request.POST['wms_code']
        description = request.POST['sku_desc']
        zone = request.POST['zone_id']
        size_type = request.POST.get('size_type', '')
        hot_release = request.POST.get('hot_release', '')
        if not wms or not description or not zone:
            return HttpResponse('Missing Required Fields')
        filter_params = {'zone': zone, 'user': user.id}
        zone_master = filter_or_none(ZoneMaster, filter_params)
        if not zone_master:
            return HttpResponse('Invalid Zone, Please enter valid Zone')
        filter_params = {'wms_code': wms, 'user': user.id}
        data = filter_or_none(SKUMaster, filter_params)
        status_msg = 'SKU exists'

        if not data:
            data_dict = copy.deepcopy(SKU_DATA)
            data_dict['user'] = user.id
            for key, value in request.POST.iteritems():
                if key in data_dict.keys():
                    if key == 'zone_id':
                        value = get_or_none(ZoneMaster, {'zone': value, 'user': user.id})
                        value = value.id
                    elif key == 'status':
                        if value == 'Active':
                            value = 1
                        else:
                            value = 0
                    elif key == 'qc_check':
                        if value == 'Enable':
                            value = 1
                        else:
                            value = 0
                    elif key == 'load_unit_handle':
                        value = load_unit_dict.get(value.lower(), 'unit')
                    elif key == 'ean_number' and value:
                        ean_status = check_ean_number(wms, value, user)
                        if ean_status:
                            return HttpResponse(ean_status)
                    if value == '':
                        continue
                    data_dict[key] = value

            data_dict['sku_code'] = data_dict['wms_code']
            sku_master = SKUMaster(**data_dict)
            sku_master.save()
            image_file = request.FILES.get('files-0', '')
            if image_file:
                save_image_file(image_file, sku_master, user)
            if size_type:
                check_update_size_type(sku_master, size_type)
            if hot_release:
                value = 1 if (value.lower() == 'enable') else 0;
                check_update_hot_release(sku_master, value)
            status_msg = 'New WMS Code Added'

            update_marketplace_mapping(user, data_dict=dict(request.POST.iterlists()), data=sku_master)

        insert_update_brands(user)
        # update master sku txt file
        status = subprocess.check_output(['pgrep -lf sku_master_file_creator'], stderr=subprocess.STDOUT, shell=True)
        if "python" not in status:
            sku_query = "%s %s/%s %s&" % ("python", settings.BASE_DIR, "sku_master_file_creator.py", str(user.id))
            subprocess.call(sku_query, shell=True)
        else:
            print "already running"

        all_users = get_related_users(user.id)
        sync_sku_switch = get_misc_value('sku_sync', user.id)
        if sync_sku_switch == 'true':
            all_users = get_related_users(user.id)
            create_update_sku([sku_master], all_users)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Insert New SKU failed for %s and params are %s and error statement is %s' % (str(user.username), \
                                                                                               str(request.POST.dict()),
                                                                                               str(e)))
        status_msg = 'Insert SKU Falied'

    return HttpResponse(status_msg)


@csrf_exempt
@login_required
@get_admin_user
def upload_images(request, user=''):
    status = 'Uploaded Successfully'
    image_file = request.FILES.get('file', '')
    extra_image = ''
    saved_file_path = ''
    if image_file:
        image_name = image_file.name.strip('.' + image_file.name.split('.')[-1])
        sku_code = image_name
        if '__' in image_name:
            sku_code = image_name.split('__')[0]
        sku_masters = SKUMaster.objects.filter(sku_class__iexact=sku_code, user=user.id)
        if not sku_masters:
            sku_masters = SKUMaster.objects.filter(sku_code__iexact=sku_code, user=user.id)
        for sku_master in sku_masters:
            # extra_image = 'true'
            # if 'default-image' in sku_master.image_url or not sku_master.image_url:
            # if not sku_master.image_url:
            extra_image = ''
            saved_file_path = save_image_file(image_file, sku_master, user, extra_image, saved_file_path)
        if not sku_masters:
            status = "SKU Code doesn't exists"
    return HttpResponse(status)


@csrf_exempt
def get_custom_sku_properties(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                              filters={}):
    lis = ['name', 'creation_date']
    order_data = lis[col_num]
    search_params = get_filtered_params(filters, lis)
    if order_term == 'desc':
        order_data = '-%s' % order_data
    product_properties = ProductProperties.objects.filter(user=user.id)
    if search_term:
        master_data = ProductProperties.objects.filter(
            Q(name__icontains=search_term) | Q(creation_date__regex=search_term),
            user=user.id, **search_params).order_by(order_data).values_list('name', flat=True). \
            distinct()
    else:
        master_data = ProductProperties.objects.filter(user=user.id, **search_params).order_by(order_data).values_list(
            'name', flat=True). \
            distinct()
    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = master_data.count()
    for data in master_data[start_index:stop_index]:
        creation_date = product_properties.filter(name=data)[0].creation_date
        temp_data['aaData'].append(
            OrderedDict((('Template Name', data), ('Creation Date', get_local_date(user, creation_date)),
                         ('DT_RowClass', 'results'), ('DT_RowAttr', {'data-id': data}))))


@csrf_exempt
@login_required
@get_admin_user
def get_product_properties(request, user=''):
    filter_params = {'user': user.id}
    data_id = request.GET.get('data_id', '')
    if data_id:
        filter_params['name'] = data_id
    size_names = []
    attributes = []
    brands = []
    categories = []
    template_name = ''
    product_properties = ProductProperties.objects.filter(**filter_params)
    if product_properties:
        product = product_properties[0]
        template_name = product.name
        size_names = list(product.size_types.values_list('size_name', flat=True).distinct())
        attributes = list(product.attributes.values('id', 'attribute_name', 'description').distinct())
        brands = list(product_properties.values_list('brand', flat=True).distinct())
        categories = list(product_properties.values_list('category', flat=True).distinct())
        product_images = list(ProductImages.objects.filter(image_id=product.id, image_type='product_property'). \
                              values_list('image_url', flat=True).distinct())
    return HttpResponse(
        json.dumps({'name': template_name, 'size_names': size_names, 'attributes': attributes, 'brands': brands,
                    'categories': categories, 'product_images': product_images}))


def save_template_image_file(image_file, master, user, image_type=''):
    path = 'static/images/sku_templates/' + str(user.id)
    image_name = str(master.name)
    image_url = save_image_file_path(path, image_file, image_name)
    if image_url:
        product_images = ProductImages.objects.filter(image_id=master.id, image_url=image_url, image_type=image_type)
        if not product_images:
            ProductImages.objects.create(image_id=master.id, image_url=image_url, image_type=image_type,
                                         creation_date=datetime.datetime.now())
        else:
            product_images[0].image_url = image_url
            product_images[0].save()
    return image_url


@csrf_exempt
@login_required
@get_admin_user
def create_update_custom_sku_template(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    request_dict = dict(request.POST.iterlists())
    template_name = request.POST.get('name', '')
    is_new = request.POST.get('is_new', '')
    data_list = []
    attributes_list = []
    sizes_list = []
    brands_list = copy.deepcopy(request_dict.get('brands', ''))
    saved_file_path = ''
    log.info('Request params for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        for key, value in request_dict.iteritems():
            if key == 'sizes':
                for val in value:
                    sizes_list.append(SizeMaster.objects.get(size_name=val, user=user.id))
            elif key in ['attribute_name']:
                for ind, val in enumerate(value):
                    attributes_list.append(
                        {'attribute_name': val, 'description': request_dict['description'][ind], 'user_id': user.id})
        for item in range(0, len(request_dict.get('categories', []))):
            category = request_dict['categories'][item]
            brands = sku_master.filter(sku_category=category, sku_brand__in=request_dict['brands']).values_list(
                'sku_brand', flat=True).distinct()
            for brand in brands:
                data_list.append({'name': template_name, 'brand': brand, 'category': category})
            if brand in brands_list:
                brands_list.remove(brand)
        status = ''
        if is_new == 'true':
            prod_pro_obj = ProductProperties.objects.filter(user_id=user.id, name=template_name)
            if prod_pro_obj:
                status = 'Template Name Already exists'
            if brands_list:
                status = 'Please select category or remove the brand for these brands ' + ','.join(brands_list)
        else:
            data_list = ProductProperties.objects.filter(user_id=user.id, name=template_name).values('name', 'brand',
                                                                                                     'category').distinct()
        if not status:
            for data_dict in data_list:
                data_dict['user_id'] = user.id
                product_pro_obj = ProductProperties.objects.filter(**data_dict)
                if not product_pro_obj:
                    data_dict['creation_date'] = datetime.datetime.now()
                    product_property, created = ProductProperties.objects.get_or_create(**data_dict)
                else:
                    product_property = product_pro_obj[0]
                for size_type_obj in sizes_list:
                    product_property.size_types.add(size_type_obj)
                for attr_dict in attributes_list:
                    product_attr_obj = ProductAttributes.objects.filter(user_id=user.id,
                                                                        attribute_name=attr_dict['attribute_name'])
                    if not product_attr_obj:
                        attr_dict['user_id'] = user.id
                        attr_dict['creation_date'] = datetime.datetime.now()
                        product_attribute, created = ProductAttributes.objects.get_or_create(**attr_dict)
                    else:
                        product_attribute = product_attr_obj[0]
                        product_attribute.description = attr_dict['description']
                        product_attribute.save()
                    if attr_dict['attribute_name'] not in product_property.attributes.values_list('attribute_name',
                                                                                                  flat=True):
                        product_property.attributes.add(product_attribute)

                    image_file = request.FILES.get('files-0', '')
                    if image_file and not saved_file_path:
                        saved_file_path = save_template_image_file(image_file, product_property, user,
                                                                   image_type='product_property')
            status = 'Added Successfully'
    except Exception as e:
        log.info('Create or Update Custom sku template failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        if is_new == 'true':
            status = 'SKU Template Creation Failed'
        else:
            status = 'SKU Template Updation Failed'
    return HttpResponse(status)


@csrf_exempt
@login_required
@get_admin_user
def delete_product_attribute(request, user=''):
    data_id = request.GET.get('data_id', '')
    name = request.GET.get('name', '')
    if data_id:
        product_attribute = ProductAttributes.objects.get(id=data_id, user_id=user.id)
        product_properties = ProductProperties.objects.filter(name=name, user_id=user.id)
        for product in product_properties:
            product.attributes.remove(product_attribute)
    return HttpResponse(json.dumps({'message': 'Deleted Successfully'}))


def get_custom_sku_code(user, exist_sku='', sku_size='', group_sku=''):
    filter_params = {'user': user.id}
    if exist_sku:
        filter_params['sku_code'] = exist_sku
    else:
        filter_params['sku_type'] = 'CS'

    sku_instance = SKUMaster.objects.filter(**filter_params).order_by('-creation_date')
    sku_serial = '1'
    if sku_instance:
        sku_serial = re.findall('\d+', sku_instance[0].sku_code)
        if sku_serial:
            sku_serial = str(int(''.join(sku_serial)) + 1)

    sku_code = (user.username[:3]).upper() + sku_serial
    if group_sku:
        sku_code = group_sku

    if sku_size:
        sku_code = sku_code + '-' + sku_size
    sku_object = SKUMaster.objects.filter(user=user.id, sku_code=sku_code)
    if sku_object:
        sku_code, sku_serial = get_custom_sku_code(user, exist_sku=sku_code)

    return sku_code, sku_serial


@csrf_exempt
@login_required
@get_admin_user
def create_custom_sku(request, user=''):
    image_file = request.FILES.get('files-0', '')
    name = request.POST.get('template', '')
    sku_codes_list = []
    # property_type = request.POST.get('property_type', '')
    # display_name, name, property_type = property_type.split(':')
    # property_name = request.POST.get('property_name', '')
    style_data = request.POST.get('style_data', '')
    unit_price = request.POST.get('unit_price', 0)
    printing_vendor = request.POST.get('printing_vendor', [])
    embroidery_vendor = request.POST.get('embroidery_name', [])
    production_unit = request.POST.get('product_unit', [])

    print_vendor_obj = None
    embroidery_vendor_obj = None
    production_unit_obj = None

    log.info('Request params for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        ven_list = {}
        if printing_vendor:
            print_vendor_obj = VendorMaster.objects.filter(user=user.id, vendor_id=printing_vendor)
            if print_vendor_obj:
                ven_list.update({'printing_vendor': print_vendor_obj[0].id})
        if embroidery_vendor:
            embroidery_vendor_obj = VendorMaster.objects.filter(user=user.id, vendor_id=embroidery_vendor)
            if embroidery_vendor_obj:
                ven_list.update({'embroidery_vendor': embroidery_vendor_obj[0].id})
        if production_unit:
            production_unit_obj = VendorMaster.objects.filter(user=user.id, vendor_id=production_unit)
            if production_unit_obj:
                ven_list.update({'production_unit': production_unit_obj[0].id})

        product_property = ProductProperties.objects.filter(name=name, user=user.id)
        if not product_property:
            return HttpResponse(json.dumps({'message': 'Wrong Data', 'data': ''}))
        product_property = product_property[0]
        data_dict = dict(request.POST.iterlists())
        sku_sizes = []

        saved_file_path = ''
        image_url = ''
        if image_file:
            path = 'static/temp_files/' + str(user.id)
            image_name = ('%s_%s') % (str(name), datetime.datetime.now().strftime('%d_%I_%S'))
            image_url = save_image_file_path(path, image_file, image_name)
        for style in eval(style_data):
            for sku_size in style['sizes']:
                try:
                    quantity = float(sku_size['value'])
                except:
                    quantity = 0
                if not quantity:
                    continue
                sku_obj = SKUMaster.objects.filter(user=user.id, sku_class=style['name'], sku_size=sku_size['name'])
                if not sku_obj:
                    continue
                else:
                    sku_obj = sku_obj[0]
                attribute_data = []
                for i in range(0, len(data_dict['field_name'])):
                    attribute_name = data_dict['field_name'][i]
                    attribute_value = data_dict['field_value'][i]
                    attribute_data.append(
                        {'attribute_name': data_dict['field_name'][i], 'attribute_value': data_dict['field_value'][i]})
                sku_codes_list.append(
                    {'sku_code': sku_obj.sku_code, 'quantity': quantity, 'description': sku_obj.sku_desc,
                     'unit_price': unit_price, 'remarks': style.get('remarks', ''), 'image_url': image_url,
                     'attribute_data': attribute_data,
                     'vendors_list': ven_list})
        return HttpResponse(json.dumps({'message': 'Success', 'data': sku_codes_list}))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create Custom SKU failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse(json.dumps({'message': 'Failed', 'data': []}))


@csrf_exempt
def get_size_master_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    order_data = SIZE_MASTER_HEADERS.values()[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        master_data = SizeMaster.objects.filter(
            Q(size_name__icontains=search_term) | Q(size_value__icontains=search_term), user=user.id).order_by(
            order_data)
    else:
        master_data = SizeMaster.objects.filter(user=user.id).order_by(order_data)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        temp = data.size_value.split('<<>>')
        temp_data['aaData'].append(OrderedDict((('size_name', data.size_name), ('size_value', temp),
                                                ('DT_RowAttr', {'data-id': data.id}))))


@csrf_exempt
@login_required
@get_admin_user
def add_size(request, user=''):
    response = {'msg': 'fail', 'data': ''}
    size_name = request.POST['size_name']
    if not size_name:
        response['data'] = 'Missing Required Fields'
        return HttpResponse(json.dumps(response))

    data = filter_or_none(SizeMaster, {'size_name': size_name, 'user': user.id})
    if data:
        response['data'] = 'Size Name Already Exist'
        return HttpResponse(json.dumps(response))

    size_value = request.POST['size_value']
    if not size_value:
        response['data'] = 'Please Enter Atleast One Size'
        return HttpResponse(json.dumps(response))

    if not data:
        data_dict = copy.deepcopy(SIZE_DATA)
        data_dict['size_name'] = size_name
        data_dict['size_value'] = size_value
        data_dict['user'] = user.id
        size_master = SizeMaster(**data_dict)
        size_master.save()
        response['msg'] = 'Success'
        response['data'] = 'New Size Added'

    return HttpResponse(json.dumps(response))


@csrf_exempt
@login_required
@get_admin_user
def update_size(request, user=''):
    response = {'msg': 'fail', 'data': ''}
    id = request.POST['id']

    data = SizeMaster.objects.get(id=id)

    size_value = request.POST['size_value']
    if not size_value:
        response['data'] = 'Please Enter Atleast One Size'
        return HttpResponse(json.dumps(response))

    if data:
        data.size_value = size_value
        data.save()
        response['msg'] = 'Success'
        response['data'] = 'Updated Successfully'

    return HttpResponse(json.dumps(response))


@csrf_exempt
@login_required
@get_admin_user
def generate_barcodes(request, user=''):
    myDict = dict(request.POST.iterlists())
    pdf_format = myDict['pdf_format'][0]
    barcodes_list = generate_barcode_dict(pdf_format, myDict, user)
    return HttpResponse(json.dumps(barcodes_list))


@csrf_exempt
def get_price_master_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                             filters={}):
    price_band_flag = get_misc_value('priceband_sync', user.id)
    if price_band_flag == 'true':
        user = get_admin(user)

    objs = PriceMaster.objects.filter(sku__user=user.id)
    lis = ['sku__sku_code', 'sku__sku_desc', 'price_type', 'price', 'discount']
    order_data = PRICING_MASTER_HEADER.values()[col_num]
    search_params = get_filtered_params(filters, lis)
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        master_data = objs.filter(Q(sku__sku_code__icontains=search_term) | Q(sku__sku_desc__icontains=search_term) | Q(
            price_type__icontains=search_term) | Q(price__icontains=search_term) | Q(discount__icontains=search_term),
                                  sku__user=user.id, **search_params).order_by(order_data).values_list('sku__sku_code', 'sku__sku_desc',
                                                                                    'price_type', 'price'
                                                                                    ).distinct()
    else:
        master_data = objs.filter(**search_params).order_by(order_data).values_list('sku__sku_code', 'sku__sku_desc',
                                                                                    'price_type', 'price'
                                                                                    ).distinct()

    temp_map = OrderedDict()
    for data in master_data:
        sku_code, sku_desc, price_type, price = data
        temp_map.setdefault((sku_code, sku_desc, price_type), []).append(price)

    temp_data['recordsTotal'] = len(temp_map)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    for key, val in temp_map.items()[start_index:stop_index]:
        sku_code, sku_desc, price_type = key
        temp_data['aaData'].append(OrderedDict((('SKU Code', sku_code), ('SKU Description', sku_desc),
                                                ('Selling Price Type', price_type), ('Price', val))))


@csrf_exempt
@login_required
@get_admin_user
def add_pricing(request, user=''):
    ''' add pricing '''
    post_data_dict = dict(request.POST.iterlists())
    sku_code = post_data_dict['sku_code'][0]
    price_type = post_data_dict['price_type'][0]
    min_unit_ranges = post_data_dict['min_unit_range']
    max_unit_ranges = post_data_dict['max_unit_range']
    prices = post_data_dict['price']
    discounts = post_data_dict['discount']
    if not sku_code and price_type:
        return HttpResponse('Missing Required Fields')
    sku = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
    if not sku:
        return HttpResponse('Invalid SKU Code')
    for i in range(len(max_unit_ranges)):
        min_unit_range = min_unit_ranges[i]
        max_unit_range = max_unit_ranges[i]
        price = prices[i]
        discount = discounts[i]
        price_data = PriceMaster.objects.filter(sku__user=user.id, sku__sku_code=sku_code, price_type=price_type,
                                                min_unit_range=min_unit_range, max_unit_range=max_unit_range)
        if price_data:
            return HttpResponse('Price type already exist in Pricing Master')
        else:
            data_dict = copy.deepcopy(PRICING_DATA)
            data_dict['sku'] = sku[0]
            data_dict['max_unit_range'] = max_unit_range
            data_dict['min_unit_range'] = min_unit_range
            data_dict['price_type'] = price_type
            data_dict['price'] = price
            if discount:
                data_dict['discount'] = float(discount)
            pricing_master = PriceMaster(**data_dict)
            pricing_master.save()
    return HttpResponse('New Pricing Added')


@csrf_exempt
@login_required
@get_admin_user
def update_pricing(request, user=''):
    ''' update pricing '''
    post_data_dict = dict(request.POST.iterlists())
    sku_code = post_data_dict['sku_code'][0]
    price_type = post_data_dict['price_type'][0]
    price_master_data = PriceMaster.objects.filter(sku__user=user.id, sku__sku_code=sku_code, price_type=price_type)
    if not price_master_data:
        return HttpResponse('Invalid data')

    db_set = set(price_master_data.values_list('min_unit_range', 'max_unit_range'))
    ui_set = set()
    ui_map = {}
    for i in range(len(post_data_dict['max_unit_range'])):
        min_amt, max_amt = float(post_data_dict['min_unit_range'][i]), float(post_data_dict['max_unit_range'][i])
        ui_discount = post_data_dict['discount'][i]
        ui_price = post_data_dict['price'][i]
        if ui_discount:
            discount = float(ui_discount)
        else:
            discount = 0.0
        if ui_price:
            price = float(ui_price)
        ui_set.add((min_amt, max_amt))
        ui_map[(float(post_data_dict['min_unit_range'][i]), float(post_data_dict['max_unit_range'][i]))] = (
        price, discount)

    sku = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)

    new_ranges = ui_set - db_set
    existing_ranges = db_set - ui_set
    common_ranges = ui_set.intersection(db_set)
    if existing_ranges:
        # Delete
        for existing_range in existing_ranges:
            min_unit_range, max_unit_range = existing_range
            price_master_data.filter(min_unit_range=min_unit_range, max_unit_range=max_unit_range).delete()
    if common_ranges:
        # Update
        for common_range in common_ranges:
            min_unit_range, max_unit_range = common_range
            price, discount = ui_map[(min_unit_range, max_unit_range)]
            p = price_master_data.filter(min_unit_range=min_unit_range, max_unit_range=max_unit_range)[0]
            print p.id, min_unit_range, max_unit_range
            p.price = price
            p.discount = discount
            p.save()
    if new_ranges:
        for new_range in new_ranges:
            min_unit_range, max_unit_range = new_range
            price, discount = ui_map[(min_unit_range, max_unit_range)]
            new_price_map = {'sku': sku[0], 'price_type': price_type, 'min_unit_range': min_unit_range,
                             'max_unit_range': max_unit_range, 'price': price, 'discount': discount}
            pricing_master = PriceMaster(**new_price_map)
            pricing_master.save()

    return HttpResponse('Updated Successfully')


def create_network_supplier(dest, src):
    ''' creating supplier in destination with source details '''

    user_profile = UserProfile.objects.get(user_id=src.id)
    max_sup_id = SupplierMaster.objects.count()
    phone_number = ''
    if user_profile.phone_number:
        phone_number = user_profile.phone_number
    supplier = SupplierMaster.objects.create(id=max_sup_id, user=dest.id, name=user_profile.user.username,
                                             email_id=user_profile.user.email,
                                             phone_number=phone_number,
                                             address=user_profile.address, status=1)
    return supplier


@csrf_exempt
def add_network(request):
    dest_loc_code = request.POST.get('destination_location_code', '')
    src_loc_code = request.POST.get('source_location_code', '')
    sku_stage = request.POST.get('sku_stage', '')
    lead_time = request.POST.get('lead_time', '')
    priority = request.POST.get('priority', '')
    price_type = request.POST.get('price_type', '')
    charge_remarks = request.POST.get('charge_remarks', '')

    if dest_loc_code:
        dest_user_obj = User.objects.filter(id=dest_loc_code)
        if not dest_user_obj:
            return HttpResponse('Destination Location Code not present')
    if src_loc_code:
        src_user_obj = User.objects.filter(id=src_loc_code)
        if not src_user_obj:
            return HttpResponse('Source Location Code not present')

    network_map = {'dest_location_code_id': dest_loc_code, 'source_location_code_id': src_loc_code,
                   'sku_stage': sku_stage, 'lead_time': lead_time, 'priority': priority,
                   'price_type': price_type, 'charge_remarks': charge_remarks}

    nw_obj = NetworkMaster.objects.filter(dest_location_code_id=dest_loc_code, source_location_code_id=src_loc_code,
                                          sku_stage=sku_stage)
    if nw_obj:
        return HttpResponse('Network object is already exist')
    else:
        nw_obj = NetworkMaster(**network_map)
        supplier = create_network_supplier(dest_user_obj[0], src_user_obj[0])
        nw_obj.supplier_id = supplier.id
        nw_obj.save()
    return HttpResponse('New Network object is created')


@csrf_exempt
def update_network(request):
    dest_loc_code = request.POST.get('destination_location_code', '')
    src_loc_code = request.POST.get('source_location_code', '')
    sku_stage = request.POST.get('sku_stage', '')
    lead_time = request.POST.get('lead_time', '')
    priority = request.POST.get('priority', '')
    price_type = request.POST.get('price_type', '')
    charge_remarks = request.POST.get('charge_remarks', '')
    if not dest_loc_code and src_loc_code and sku_stage and lead_time and priority and price_type:
        return HttpResponse('Values missing')

    nw_obj = NetworkMaster.objects.filter(dest_location_code__username=dest_loc_code,
                                          source_location_code__username=src_loc_code,
                                          sku_stage=sku_stage)
    if nw_obj:
        nw_obj[0].lead_time = lead_time
        nw_obj[0].priority = priority
        nw_obj[0].price_type = price_type
        nw_obj[0].charge_remarks = charge_remarks
        if not nw_obj[0].supplier_id:
            supplier = create_network_supplier(nw_obj[0].dest_location_code, nw_obj[0].source_location_code)
            nw_obj[0].supplier_id = supplier.id
        nw_obj[0].save()
        return HttpResponse('Updated Successfully')
    else:
        return HttpResponse('Record not found')


@csrf_exempt
def get_network_master_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                               filters={}):
    nw_users = UserGroups.objects.filter(admin_user_id=user.id).values_list('user_id', flat=True)
    objs = NetworkMaster.objects.filter(Q(dest_location_code__in=nw_users) | Q(source_location_code__in=nw_users))
    lis = ['dest_location_code__username', 'source_location_code__username', 'lead_time',
           'sku_stage', 'priority', 'price_type', 'charge_remarks']
    order_data = NETWORK_MASTER_HEADER.values()[col_num]
    search_params = get_filtered_params(filters, lis)
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        master_data = objs.filter(Q(dest_location_code__username__icontains=search_term) |
                                  Q(source_location_code__username__icontains=search_term) |
                                  Q(lead_time__icontains=search_term) |
                                  Q(sku_stage__icontains=search_term) |
                                  Q(priority__icontains=search_term) |
                                  Q(price_type__icontains=search_term) |
                                  Q(charge_remarks__icontains=search_term),
                                  **search_params).order_by(order_data).values_list('dest_location_code__username',
                                                                                    'source_location_code__username',
                                                                                    'lead_time', 'sku_stage',
                                                                                    'priority', 'price_type',
                                                                                    'charge_remarks'
                                                                                    ).distinct()
    else:
        master_data = objs.filter(**search_params).order_by(order_data).values_list('dest_location_code__username',
                                                                                    'source_location_code__username',
                                                                                    'lead_time', 'sku_stage',
                                                                                    'priority', 'price_type',
                                                                                    'charge_remarks'
                                                                                    ).distinct()
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    for data in master_data[start_index:stop_index]:
        dst_user, src_user, lead_time, sku_stage, priority, price_type, charge_remarks = data
        temp_data['aaData'].append(OrderedDict((('Destination Location Code', dst_user),
                                                ('Source Location Code', src_user),
                                                ('Lead Time', lead_time),
                                                ('Sku Stage', sku_stage),
                                                ('Priority', priority),
                                                ('Price Type', price_type),
                                                ('Remarks', charge_remarks))))


@csrf_exempt
def get_seller_master(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    ''' Seller Master Datatable '''
    lis = ['seller_id', 'name', 'email_id', 'phone_number', 'address', 'status']

    search_params = get_filtered_params(filters, lis)
    if 'status__icontains' in search_params.keys():
        if (str(search_params['status__icontains']).lower() in "active"):
            search_params["status__icontains"] = 1
        elif (str(search_params['status__icontains']).lower() in "inactive"):
            search_params["status__icontains"] = 0
        else:
            search_params["status__icontains"] = "none"
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        search_dict = {'active': 1, 'inactive': 0}
        if search_term.lower() in search_dict:
            search_terms = search_dict[search_term.lower()]
            master_data = SellerMaster.objects.filter(status=search_terms, user=user.id, **search_params).order_by(
                order_data)

        else:
            master_data = SellerMaster.objects.filter(
                Q(seller_id__icontains=search_term) | Q(name__icontains=search_term) |
                Q(address__icontains=search_term) | Q(phone_number__icontains=search_term) |
                Q(email_id__icontains=search_term),
                user=user.id, **search_params).order_by(order_data)

    else:
        master_data = SellerMaster.objects.filter(user=user.id, **search_params).order_by(order_data)

    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for data in master_data[start_index: stop_index]:
        status = 'Inactive'
        if data.status:
            status = 'Active'

        if data.phone_number:
            data.phone_number = int(float(data.phone_number))
        user_name = ""
        price_type = ""
        price_types = list(
            PriceMaster.objects.exclude(price_type="").filter(sku__user=data.user).values_list('price_type',
                                                                                               flat=True).distinct())

        price_type = data.price_type
        temp_data['aaData'].append(
            OrderedDict((('seller_id', data.seller_id), ('name', data.name), ('address', data.address),
                         ('phone_number', data.phone_number), ('email_id', data.email_id), ('status', status),
                         ('tin_number', data.tin_number), ('vat_number', data.vat_number),
                         ('price_type_list', price_types), ('margin', float(data.margin)),
                         ('price_type', price_type), ('DT_RowId', data.seller_id), ('DT_RowClass', 'results'))))


@login_required
@csrf_exempt
@get_admin_user
def get_seller_master_id(request, user=''):
    seller_id = 1
    seller_master = SellerMaster.objects.filter(user=user.id).values_list('seller_id', flat=True).order_by('-seller_id')
    if seller_master:
        seller_id = seller_master[0] + 1
    return HttpResponse(json.dumps({'seller_id': seller_id}))


@csrf_exempt
@login_required
@get_admin_user
def insert_seller(request, user=''):
    ''' Insert New Seller '''
    seller_id = request.POST['seller_id']
    if not seller_id:
        return HttpResponse('Missing Required Fields')
    data = filter_or_none(SellerMaster, {'seller_id': seller_id, 'user': user.id})
    status_msg = 'Seller Exists'
    if not data:
        data_dict = copy.deepcopy(SELLER_DATA)
        for key, value in request.POST.iteritems():
            if key == 'status':
                if value == 'Active':
                    value = 1
                else:
                    value = 0
            if value == '':
                continue
            data_dict[key] = value

        data_dict['user'] = user.id
        seller_master = SellerMaster(**data_dict)
        seller_master.save()
        status_msg = 'New Seller Added'

    return HttpResponse(status_msg)


@csrf_exempt
@login_required
@get_admin_user
def update_seller_values(request, user=''):
    data_id = request.POST['seller_id']
    log.info('Request params for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        data = get_or_none(SellerMaster, {'seller_id': data_id, 'user': user.id})
        for key, value in request.POST.iteritems():
            if key not in data.__dict__.keys():
                continue
            if key == 'status':
                if value == 'Active':
                    value = 1
                else:
                    value = 0
                setattr(data, key, value)
            else:
                setattr(data, key, value)

        data.save()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Seller Values failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
    return HttpResponse('Updated Successfully')


@csrf_exempt
@get_admin_user
def insert_seller_margin(request, user=''):
    data_dict = copy.deepcopy(SELLER_MARGIN_DICT)
    integer_data = ['margin']
    seller_id = ''
    sku_id = ''
    log.info('Request params are ' + str(request.POST.dict()))
    try:
        for key, value in request.POST.iteritems():

            if key == 'sku_code':
                sku_master = SKUMaster.objects.filter(sku_code=value.upper(), user=user.id)
                if not sku_master:
                    return HttpResponse("WMS Code doesn't exists")
                key = 'sku_id'
                value = sku_master[0].id
                sku_id = value

            elif key == 'seller':
                if not value:
                    return HttpResponse("Please select Seller")
                seller_master = SellerMaster.objects.filter(user=user.id, seller_id=value)
                if not seller_master:
                    return HttpResponse("Seller Master doesn't exists")
                value = seller_master[0].id
                key = 'seller_id'
                seller_id = value

            elif key == 'margin' and not value:
                value = 0

            if value != '':
                data_dict[key] = value

        data = SellerMarginMapping.objects.filter(seller__seller_id=seller_id, sku_id=sku_id)
        if data:
            return HttpResponse('Seller SKU Margin Entry Exists')

        data_dict['creation_date'] = datetime.datetime.now()
        seller_margin = SellerMarginMapping(**data_dict)
        seller_margin.save()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Insert Seller SKU Margin failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Insert Seller SKU Margin Failed")

    return HttpResponse('Added Successfully')


@csrf_exempt
def get_seller_margin_mapping(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                              filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['seller__seller_id', 'seller__name', 'sku__wms_code', 'sku__sku_desc', 'margin']
    order_data = lis[col_num]
    filter_params = get_filtered_params(filters, lis)

    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        mapping_results = SellerMarginMapping.objects.filter(sku_id__in=sku_master_ids).filter(
            Q(seller__seller_id__icontains=search_term) |
            Q(seller__name__icontains=search_term) | Q(sku__wms_code__icontains=search_term) |
            Q(sku__sku_desc__icontains=search_term) | Q(margin__icontains=search_term),
            sku__user=user.id, **filter_params).order_by(order_data)

    else:
        mapping_results = SellerMarginMapping.objects.filter(sku_id__in=sku_master_ids).filter(sku__user=user.id,
                                                                                               **filter_params).order_by(
            order_data)

    temp_data['recordsTotal'] = len(mapping_results)
    temp_data['recordsFiltered'] = len(mapping_results)

    for result in mapping_results[start_index: stop_index]:
        temp_data['aaData'].append(OrderedDict((('seller_id', result.seller.seller_id), ('name', result.seller.name),
                                                ('sku_code', result.sku.wms_code), ('sku_desc', result.sku.sku_desc),
                                                ('margin', result.margin),
                                                ('DT_RowClass', 'results'), ('DT_RowId', result.id))))


@csrf_exempt
@login_required
@get_admin_user
def update_seller_margin(request, user=''):
    data_id = request.POST.get('DT_RowId', '')
    log.info('Request params for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        data = get_or_none(SellerMarginMapping, {'id': data_id, 'sku__user': user.id})
        if data:
            data.margin = request.POST.get('margin', 0)
            data.save()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Seller Margin Values failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse('Update Seller Margin Failed')
    return HttpResponse('Updated Successfully')


@csrf_exempt
def get_tax_master(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters={}):
    admin_user = get_priceband_admin_user(user)
    if admin_user:
        objs = TaxMaster.objects.filter(user=admin_user.id)
    else:
        objs = TaxMaster.objects.filter(user=user.id)
    lis = ['product_type', 'creation_date']
    order_data = TAX_MASTER_HEADER.values()[col_num]
    search_params = get_filtered_params(filters, lis)
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        master_data = objs.filter(Q(product_type__icontains=search_term) | Q(creation_date__icontains=search_term), \
                                  **search_params).values('product_type').distinct().order_by(order_data)
    else:
        master_data = objs.filter(**search_params).values('product_type').distinct().order_by(order_data)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for data in master_data[start_index:stop_index]:
        date = objs.filter(product_type=data['product_type'])
        temp_data['aaData'].append(OrderedDict(
            (('Product Type', data['product_type']), ('Creation Date', get_local_date(user, date[0].creation_date))
             )))


@get_admin_user
def get_tax_data(request, user=''):
    """ Get Tax Details """

    response = {'status': 0, 'msg': ''}
    product_type = request.GET.get('product_type', '')
    if not product_type:
        response['msg'] = 'fail'
        return HttpResponse(response)

    admin_user = get_priceband_admin_user(user)
    if admin_user:
        taxes = TaxMaster.objects.filter(user=admin_user.id, product_type__exact=product_type)
    else:
        taxes = TaxMaster.objects.filter(user=user.id, product_type__exact=product_type)
    if not taxes:
        response['msg'] = 'Product Type Not Found'
        return HttpResponse(response)

    resp = {'data': []}
    resp['product_type'] = taxes[0].product_type
    for tax in taxes:
        temp = tax.json()
        tax_type = 'inter_state'
        if not temp['inter_state']:
            tax_type = 'intra_state'
        temp['tax_type'] = tax_type
        resp['data'].append(temp)

    response['status'] = 1
    response['data'] = resp

    return HttpResponse(json.dumps(response))


@get_admin_user
def get_pricetype_data(request, user=''):
    """ Get all PriceType Details."""
    price_band_flag = get_misc_value('priceband_sync', user.id)
    if price_band_flag == 'true':
        user = get_admin(user)

    response = {'status': 0, 'msg': ''}
    sku_code = request.GET.get('sku_code', '')
    price_type = request.GET.get('price_type', '')
    if not sku_code and price_type:
        response['msg'] = 'fail'
        return HttpResponse(response)

    price_master_objs = PriceMaster.objects.filter(sku__user=user.id, sku__sku_code=sku_code, price_type=price_type)
    if not price_master_objs:
        response['msg'] = 'Price Master values not found'
        return HttpResponse(response)
    resp = {'data': [], 'sku_code': sku_code, 'selling_price_type': price_type}
    for price_master_obj in price_master_objs:
        temp = price_master_obj.json()
        resp['data'].append(temp)

    response['status'] = 1
    response['data'] = resp
    return HttpResponse(json.dumps(response))


def get_network_data(request):
    response = {'status': 0, 'msg': ''}
    dest_loc_code = request.GET.get('destination_location_code', '')
    src_loc_code = request.GET.get('source_location_code', '')
    sku_stage = request.GET.get('sku_stage', '')
    if not dest_loc_code and src_loc_code and sku_stage:
        response['msg'] = 'fail'
        return HttpResponse(response)

    network_master_objs = NetworkMaster.objects.filter(dest_location_code__username=dest_loc_code,
                                                       source_location_code__username=src_loc_code,
                                                       sku_stage=sku_stage)
    if not network_master_objs:
        response['msg'] = 'Network Master Values not found'
        return HttpResponse(response)
    else:
        response['status'] = 1
        response['data'] = {'data': network_master_objs[0].json()}
        return HttpResponse(json.dumps(response))


@csrf_exempt
@login_required
@get_admin_user
def add_or_update_tax(request, user=''):
    """ Add or Update Tax Data"""

    response = {'status': 0, 'msg': ''}
    tax_data = request.POST.get('data', '')
    if not tax_data:
        return HttpResponse('Missing Required Fields')

    log.info('Add or Update Tax request params for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        tax_data = simplejson.loads(str(tax_data))

        if not tax_data['product_type']:
            return HttpResponse('Missing Required Fields')

        product_type = tax_data['product_type']
        if not tax_data['update']:
            taxes = TaxMaster.objects.filter(user=user.id, product_type__exact=product_type)
            if taxes:
                return HttpResponse('Product Type Already Exist')
        columns = ['sgst_tax', 'cgst_tax', 'igst_tax', 'min_amt', 'max_amt']
        for data in tax_data['data']:

            data_dict = {'user_id': user.id}
            if data.get('id', ''):
                tax_master = get_or_none(TaxMaster, {'id': data['id'], 'user_id': user.id})
                for key in columns:
                    if data[key]:
                        setattr(tax_master, key, float(data[key]))
                tax_master.save()
            else:
                if not data['min_amt'] or not data['max_amt']:
                    continue
                for key in columns:
                    if data[key]:
                        data_dict[key] = float(data[key])
                data_dict['inter_state'] = 0
                if data['tax_type'] == 'inter_state':
                    data_dict['inter_state'] = 1
                data_dict['product_type'] = product_type
                tax_master = TaxMaster(**data_dict)
                tax_master.save()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Add or Update Tax failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Add or Update failed")

    return HttpResponse("success")


@get_admin_user
def search_seller_data(request, user=''):
    search_key = request.GET.get('q', '')
    total_data = []

    if not search_key:
        return HttpResponse(json.dumps(total_data))

    master_data = SellerMaster.objects.filter(Q(phone_number__icontains=search_key) | Q(name__icontains=search_key) |
                                              Q(seller_id__icontains=search_key), user=user.id)

    for data in master_data[:30]:
        status = 'Inactive'
        if data.status:
            status = 'Active'

        total_data.append(data.json())
    return HttpResponse(json.dumps(total_data))


@get_admin_user
def search_network_user(request, user=''):
    search_key = request.GET.get('q', '')
    total_data = []

    if not search_key:
        return HttpResponse(json.dumps(total_data))

    users_data = UserGroups.objects.filter(Q(user_id__username__icontains=search_key) |
                                           Q(user_id__id__icontains=search_key))
    for user_data in users_data[:30]:
        total_data.append({"user_id": str(user_data.user.id), "user_name": str(user_data.user.username)})

    return HttpResponse(json.dumps(total_data))


@csrf_exempt
@login_required
@get_admin_user
def get_terms_and_conditions(request, user=''):
    ''' Get Terms and conditions list'''
    tc_type = request.GET.get('tc_type', '')
    admin_user = get_admin(user)
    tc_list = list(TANDCMaster.objects.filter(user=admin_user.id, term_type=tc_type).values('id', 'terms').order_by('id'))
    return HttpResponse(json.dumps({'tc_list': tc_list}))


@csrf_exempt
@login_required
@get_admin_user
def insert_update_terms(request, user=''):
    ''' Create or Update Terms and conditions'''
    terms_dict = request.POST.dict()
    message = ''
    status = 0
    data = {}
    if not terms_dict.get('term_type', ''):
        return HttpResponse(json.dumps({'status': status, 'message': 'Term type missing'}))
    if terms_dict.get('id', ''):
        TANDCMaster.objects.filter(id=terms_dict['id'], term_type=terms_dict['term_type']).\
                            update(terms=terms_dict['terms'])
        message = 'Updated Successfully'
        status = 1
    elif terms_dict.get('terms', ''):
        terms_dict['user'] = user.id
        tc_master = TANDCMaster.objects.create(**terms_dict)
        message = 'Added Successfully'
        data = {'id': tc_master.id}
        status = 1
    else:
        message = 'Mandatory fields missing'
    return HttpResponse(json.dumps({'status': status, 'message': message, 'data': data}))


@csrf_exempt
@login_required
@get_admin_user
def delete_terms(request, user=''):
    ''' Delete Terms and conditions'''
    terms_dict = request.POST.dict()
    message = ''
    status = 0
    data = {}
    if not terms_dict.get('term_type', ''):
        return HttpResponse(json.dumps({'status': status, 'message': 'Term type missing'}))
    if terms_dict.get('id', ''):
        TANDCMaster.objects.filter(id=terms_dict['id']).delete()
        message = 'Deleted Successfully'
        status = 1
    else:
        message = 'Mandatory fields missing'
    return HttpResponse(json.dumps({'status': status, 'message': message, 'data': data}))


@csrf_exempt
@login_required
@get_admin_user
def insert_staff(request, user=''):
    """ Add New Staff"""
    log.info('Add New Staff request params for ' + user.username + ' is ' + str(request.POST.dict()))
    staff_name = request.POST.get('name', '')
    email = request.POST.get('email_id', '')
    phone = request.POST.get('phone_number', '')
    status = 1 if request.POST.get('status', '') == "Active" else 0
    if not staff_name:
        return HttpResponse('Missing Required Fields')
    data = filter_or_none(StaffMaster, {'staff_name': staff_name, 'user': user.id})
    status_msg = 'Staff Exists'

    if not data:
        StaffMaster.objects.create(user=user.id, staff_name=staff_name,\
                            phone_number=phone, email_id=email, status=status)


        status_msg = 'New Staff Added'
    return HttpResponse(status_msg)


@csrf_exempt
@login_required
@get_admin_user
def update_staff_values(request, user=''):
    """ Update Staff values"""
    log.info('Update Staff values for ' + user.username + ' is ' + str(request.POST.dict()))
    staff_name = request.POST.get('name', '')
    email = request.POST.get('email_id', '')
    phone = request.POST.get('phone_number', '')
    status = 1 if request.POST.get('status', '') == "Active" else 0
    data = get_or_none(StaffMaster, {'staff_name': staff_name, 'user': user.id})
    data.email_id = email
    data.phone_number = phone
    data.status = status
    data.save()
    return HttpResponse("Updated Successfully")
