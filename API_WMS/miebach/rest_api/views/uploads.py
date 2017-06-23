from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.encoding import smart_str
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
import csv
from sync_sku import *
log = init_logger('logs/uploads.log')

@csrf_exempt
def error_file_download(error_file):
    with open(error_file, 'r') as excel:
        data = excel.read()
    response = HttpResponse(data, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=%s' % smart_str(error_file)
    return response

def get_cell_data(row_idx, col_idx, reader='', file_type='xls'):
    try:
        if file_type == 'csv':
            cell_data = reader[row_idx][col_idx]
        else:
            cell_data = reader.cell(row_idx, col_idx).value
    except:
        cell_data = ''
    return cell_data

def get_order_mapping(reader, file_type):

    order_mapping = {}
    if get_cell_data(0, 2, reader, file_type) == 'Channel' and get_cell_data(0, 6, reader, file_type) == 'Fulfillment TAT':
        order_mapping = copy.deepcopy(UNI_COMMERCE_EXCEL)
    elif get_cell_data(0, 1, reader, file_type) == 'Order No':
        order_mapping = copy.deepcopy(SHOPCLUES_EXCEL)
    elif get_cell_data(0, 4, reader, file_type) == 'Priority Level':
        order_mapping = copy.deepcopy(SHOPCLUES_EXCEL1)
    elif get_cell_data(0, 1, reader, file_type) == 'FSN' and get_cell_data(0, 16, reader, file_type) == 'Invoice No.':
        order_mapping = copy.deepcopy(FLIPKART_EXCEL)
    elif get_cell_data(0, 1, reader, file_type) == 'FSN' and get_cell_data(0, 16, reader, file_type) != 'Invoice No.':
        order_mapping = copy.deepcopy(FLIPKART_EXCEL1)
    elif get_cell_data(0, 1, reader, file_type) == 'Shipment ID' and get_cell_data(0, 2, reader, file_type) == 'ORDER ITEM ID':
        order_mapping = copy.deepcopy(FLIPKART_EXCEL2)
    elif get_cell_data(0, 1, reader, file_type) == 'Shipment Id' and get_cell_data(0, 2, reader, file_type) == 'Order Item Id'\
         and get_cell_data(0, 16, reader, file_type) != 'SKU Code':
        order_mapping = copy.deepcopy(FLIPKART_EXCEL3)
    elif get_cell_data(0, 1, reader, file_type) == 'Shipment Id' and get_cell_data(0, 2, reader, file_type) == 'Order Item Id'\
         and get_cell_data(0, 16, reader, file_type) == 'SKU Code':
        order_mapping = copy.deepcopy(FLIPKART_EXCEL4)
    elif get_cell_data(0, 3, reader, file_type) == 'customer_firstname':
        order_mapping = copy.deepcopy(PAYTM_EXCEL1)
    elif get_cell_data(0, 1, reader, file_type) == 'item_name':
        order_mapping = copy.deepcopy(PAYTM_EXCEL2)
    elif get_cell_data(0, 1, reader, file_type) == 'Order Item ID':
        order_mapping = copy.deepcopy(FLIPKART_FA_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Sr. No' and get_cell_data(0, 1, reader, file_type) == 'PO No':
        order_mapping = copy.deepcopy(MYNTRA_EXCEL)
    elif get_cell_data(0, 1, reader, file_type) == 'PO No' and get_cell_data(0, 3, reader, file_type) == 'Supp. Color':
        order_mapping = copy.deepcopy(JABONG_EXCEL)
    elif get_cell_data(0, 3, reader, file_type) == 'Jabong SKU':
        order_mapping = copy.deepcopy(JABONG_EXCEL1)
    elif get_cell_data(0, 0, reader, file_type) == 'Product Name' and get_cell_data(0, 1, reader, file_type) == 'FSN':
        order_mapping = copy.deepcopy(FLIPKART_FA_EXCEL1)
    elif get_cell_data(0, 0, reader, file_type) == 'Shipping' and get_cell_data(0, 1, reader, file_type) == 'Date':
        order_mapping = copy.deepcopy(CAMPUS_SUTRA_EXCEL)
    #Xls and Xlsx Reading
    elif get_cell_data(0, 0, reader, file_type) == 'Order ID' and not get_cell_data(0, 1, reader, file_type) == 'UOR ID':
        order_mapping = copy.deepcopy(ORDER_DEF_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Courier':
        order_mapping = copy.deepcopy(SNAPDEAL_EXCEL)
    elif 'Courier' in get_cell_data(0, 1, reader, file_type):
        order_mapping = copy.deepcopy(SNAPDEAL_EXCEL1)
    elif get_cell_data(0, 0, reader, file_type) == 'ASIN':
        order_mapping = copy.deepcopy(AMAZON_FA_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Sl no':
        order_mapping = copy.deepcopy(SNAPDEAL_FA_EXCEL)
    elif get_cell_data(0, 1, reader, file_type) == 'Payment Mode':
        order_mapping = copy.deepcopy(INDIA_TIMES_EXCEL)
    elif get_cell_data(0, 3, reader, file_type) == 'Billing Name':
        order_mapping = copy.deepcopy(HOMESHOP18_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Voonik Order Number':
        order_mapping = copy.deepcopy(VOONIK_EXCEL)
    elif get_cell_data(0, 2, reader, file_type) == 'purchase-date' and get_cell_data(0, 4, reader, file_type) == 'payments-date':
        order_mapping = copy.deepcopy(AMAZON_EXCEL)
    elif get_cell_data(0, 2, reader, file_type) == 'purchase-date' and get_cell_data(0, 4, reader, file_type) == 'buyer-email':
        order_mapping = copy.deepcopy(AMAZON_EXCEL1)
    elif get_cell_data(0, 1, reader, file_type) == 'AMB Order No':
        order_mapping = copy.deepcopy(ASKMEBAZZAR_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Order Id' and get_cell_data(0, 1, reader, file_type) == 'Date Time':
        order_mapping = copy.deepcopy(LIMEROAD_EXCEL)
    elif get_cell_data(0, 1, reader, file_type) == 'Uniware Created At' and get_cell_data(0, 0, reader, file_type) == 'Order #':
        order_mapping = copy.deepcopy(UNI_COMMERCE_EXCEL1)
    elif get_cell_data(0, 0, reader, file_type) == 'Order Date' and get_cell_data(0, 3, reader, file_type) == 'Total Value':
        order_mapping = copy.deepcopy(EASYOPS_ORDER_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Shipment' and get_cell_data(0, 1, reader, file_type) == 'Products':
        order_mapping = copy.deepcopy(UNI_WARE_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Sale Order Item Code' and get_cell_data(0, 2, reader, file_type) == 'Reverse Pickup Code':
        order_mapping = copy.deepcopy(UNI_WARE_EXCEL1)
    elif get_cell_data(0, 0, reader, file_type) == 'SOR ID' and get_cell_data(0, 1, reader, file_type) == 'UOR ID':
        order_mapping = copy.deepcopy(SHOTANG_ORDER_FILE_EXCEL)
    elif get_cell_data(0, 2, reader, file_type) == 'VENDOR ARTICLE NUMBER' and get_cell_data(0, 3, reader, file_type) == 'VENDOR ARTICLE NAME':
        order_mapping = copy.deepcopy(MYNTRA_BULK_PO_EXCEL)

    return order_mapping

def get_customer_master_mapping(reader, file_type):
    ''' Return Customer Master Excel file indexes'''
    mapping_dict = {}
    if get_cell_data(0, 0, reader, file_type) == 'Customer Id' and get_cell_data(0, 1, reader, file_type) == 'Customer Name':
        mapping_dict = copy.deepcopy(CUSTOMER_EXCEL_MAPPING)
    elif get_cell_data(0, 0, reader, file_type) == 'customer_id' and get_cell_data(0, 1, reader, file_type) == 'phone':
        mapping_dict = copy.deepcopy(MARKETPLACE_CUSTOMER_EXCEL_MAPPING)

    return mapping_dict


def check_create_seller_order(seller_order_dict, order, user):
    if seller_order_dict.get('seller_id', ''):
        sell_order_ins = SellerOrder.objects.filter(sor_id=seller_order_dict['sor_id'], order_id=order.id, seller__user=user.id)
        seller_order_dict['order_id'] = order.id
        if not sell_order_ins:
            seller_order = SellerOrder(**seller_order_dict)
            seller_order.save()

def update_seller_order(seller_order_dict, order, user):
    seller_orders = SellerOrder.objects.filter(sor_id=seller_order_dict['sor_id'], order_id=order.id, seller__user=user.id)
    for seller_order in seller_orders:
        seller_order.order_status = seller_order_dict.get('order_status', '')
        seller_order.status = 1
        seller_order.save()

def order_csv_xls_upload(request, reader, user, no_of_rows, fname, file_type='xls'):
    index_status = {}
    order_mapping = get_order_mapping(reader, file_type)
    if not order_mapping:
        return "Headers not matching"

    count = 0
    exclude_rows = []
    for row_idx in range(1, no_of_rows):
        if not order_mapping:
            break

        count += 1
        if 'seller' in order_mapping:
            seller_id = get_cell_data(row_idx, order_mapping['seller'], reader, file_type)
            seller_master = None
            if seller_id:
                if isinstance(seller_id, float):
                    seller_id = int(seller_id)
                seller_master = SellerMaster.objects.filter(seller_id=seller_id, user=user.id)
            if not seller_master or not seller_id:
                exclude_rows.append(row_idx)
                continue
        cell_data = get_cell_data(row_idx, order_mapping['sku_code'], reader, file_type)
        title = ''
        if 'title' in order_mapping.keys():
            title = get_cell_data(row_idx, order_mapping['title'], reader, file_type)

        if type(cell_data) == float:
            sku_code = str(int(cell_data))
        elif isinstance(cell_data, str) and '.' in cell_data:
            sku_code = str(int(float(cell_data)))
        else:
            sku_code = cell_data.upper()

        sku_codes = sku_code.split(',')
        for sku_code in sku_codes:
            sku_id = check_and_return_mapping_id(sku_code, title, user)
            if not sku_id:
                index_status.setdefault(count, set()).add('SKU Mapping Not Available')
        #count += 1

        if "shipment_check" in order_mapping:
            _shipping_date = get_cell_data(row_idx, order_mapping['shipment_date'], reader, file_type)
            if _shipping_date:
                try:
                    ship_date = xldate_as_tuple(_shipping_date, 0)

                except:
                    index_status.setdefault(count, set()).add('Shipping Date is not proper')

        if 'tax_percentage' in order_mapping:
            _tax_percentage = get_cell_data(row_idx, order_mapping['tax_percentage'][0], reader, file_type)
            if _tax_percentage and not isinstance(_tax_percentage, float):
                index_status.setdefault(count, set()).add('Tax Percentage should be Number')
            _invoice_amount_value = get_cell_data(row_idx, order_mapping['tax_percentage'][1], reader, file_type)
            if _invoice_amount_value and not isinstance(_invoice_amount_value, float):
                index_status.setdefault(count, set()).add('Invoice Amount should be Number')

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        rewrite_csv_file(f_name, index_status, reader)
        return f_name

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        rewrite_excel_file(f_name, index_status, reader)
        return f_name

    sku_ids = []

    user_profile = UserProfile.objects.get(user_id=user.id)
    for row_idx in range(1, no_of_rows):
        if not order_mapping:
            break
        if row_idx in exclude_rows:
            continue
        order_data = copy.deepcopy(UPLOAD_ORDER_DATA)
        order_summary_dict = copy.deepcopy(ORDER_SUMMARY_FIELDS)
        seller_order_dict = copy.deepcopy(SELLER_ORDER_FIELDS)
        if order_mapping.get('marketplace', ''):
            order_data['marketplace'] = order_mapping['marketplace']
        if order_mapping.get('status', '') and get_cell_data(row_idx, order_mapping['status'], reader, file_type) != 'New':
            continue

        for key, value in order_mapping.iteritems():
            if key in ['marketplace', 'status', 'split_order_id', 'recreate', 'shipment_check'] or key not in order_mapping.keys():
                continue
            if key == 'order_id' and 'order_id' in order_mapping.keys():
                order_id = get_cell_data(row_idx, order_mapping['order_id'], reader, file_type)
                if isinstance(order_id, float):
                    order_id = str(int(order_id))
                order_data['original_order_id'] = order_id
                if order_mapping.get('split_order_id', '') and '/' in order_id:
                    order_id = order_id.split('/')[0]
                order_code = (''.join(re.findall('\D+', order_id))).replace("'", "").replace("`", "")
                order_id = ''.join(re.findall('\d+', order_id))
                if order_mapping.get('recreate', ""):
                    order_exist = OrderDetail.objects.filter(Q(order_id = order_id, order_code=order_code) |
                                                          Q(original_order_id=order_data['original_order_id']), marketplace = "JABONG_SC",
                                                             user=user.id)
                    if order_exist:
                        order_id = ""

                if order_id:
                    order_data['order_id'] = int(order_id)
                    order_data['order_code'] = 'OD'
                    if order_code:
                        order_data['order_code'] = order_code
                else:
                    order_data['order_id'] = get_order_id(user.id)
                    order_data['order_code'] = 'MN'

            elif key == 'quantity':
                order_data[key] = int(get_cell_data(row_idx, value, reader, file_type))
            elif key == 'unit_price':
                order_data[key] = float(get_cell_data(row_idx, value, reader, file_type))
            elif key == 'invoice_amount':
                if isinstance(value, list):
                    cell_data = float(get_cell_data(row_idx, value[0], reader, file_type)) * \
                                float(get_cell_data(row_idx, value[1], reader, file_type))
                else:
                    cell_data = get_cell_data(row_idx, value, reader, file_type)
                if cell_data:
                    order_data[key] = float(cell_data)
                else:
                    order_data[key] = 0
                sku_length = get_cell_data(row_idx, order_mapping['sku_code'], reader, file_type)
                if isinstance(sku_length, float):
                    sku_length = str(sku_length)
                if ',' in sku_length:
                    sku_length = len(sku_length.split(','))
                    order_data[key] = float(get_cell_data(row_idx, value, reader, file_type))/sku_length

            elif key == 'item_name':
                order_data['invoice_amount'] += int(get_cell_data(row_idx, 11, reader, file_type))
            elif key == 'vat':
                cell_data = ''
                if isinstance(value, list):
                    quantity = 1
                    sku_length = get_cell_data(row_idx, order_mapping['sku_code'], reader, file_type)
                    if 'quantity' in order_mapping.keys():
                        quantity = float(get_cell_data(row_idx, order_mapping['quantity'], reader, file_type))
                    elif ',' in sku_length:
                        quantity = len(sku_length.split(','))
                    amount = float(get_cell_data(row_idx, value[0], reader, file_type))/quantity
                    rate = float(get_cell_data(row_idx, value[1], reader, file_type))
                    tax_value_item = (amount - rate)
                    tax_value = tax_value_item * quantity
                    vat = "%.2f" % (float(tax_value_item * 100) / rate)
                    order_summary_dict['issue_type'] = 'order'
                    order_summary_dict['vat'] = vat
                    order_summary_dict['tax_value'] = "%.2f" % tax_value
                elif isinstance(value, dict):
                    vat = float(get_cell_data(row_idx, value['tax'], reader, file_type))
                    quantity = float(get_cell_data(row_idx, value['quantity'], reader, file_type))
                    order_summary_dict['issue_type'] = 'order'
                    order_summary_dict['vat'] = vat
                    if not value.get('tot_tax', ''):
                        tax_value = float(get_cell_data(row_idx, value['tax_value'], reader, file_type))
                        order_summary_dict['tax_value'] = "%.2f" % (tax_value * quantity)
                    else:
                        order_summary_dict['tax_value'] = "%.2f" % (float(get_cell_data(row_idx, value['tot_tax'], reader, file_type)))
            elif key == 'address':
                if isinstance(value, (list)):
                    cell_data = ''
                    for val in value:
                        if not cell_data:
                            cell_data = str(get_cell_data(row_idx, val, reader, file_type))
                        else:
                            cell_data = str(cell_data) + ", " + str(get_cell_data(row_idx, val, reader, file_type))
                else:
                    order_data[key] = str(get_cell_data(row_idx, value, reader, file_type))[:256]
            elif key == 'sku_code':
                sku_code =  get_cell_data(row_idx, value, reader, file_type)
            elif key == 'shipment_date':
                _shippment_date  = get_cell_data(row_idx, value, reader, file_type)
                try:
                    year, month, day, hour, minute, second  = xldate_as_tuple(_shippment_date, 0)
                    order_data['shipment_date'] = datetime.datetime(year, month, day, hour, minute, second)
                except:
                    order_data['shipment_date'] = datetime.datetime.now()
            elif key == 'channel_name':
                order_data['marketplace'] = get_cell_data(row_idx, value, reader, file_type)
            elif key == 'title':
                order_data[key] = str(get_cell_data(row_idx, value, reader, file_type))[:256]
            elif key == 'pin_code':
                pin_code = get_cell_data(row_idx, value, reader, file_type)
                if isinstance(pin_code, float) or isinstance(pin_code, int):
                    order_data[key] = int(pin_code)
            elif key == 'mrp':
                order_summary_dict['mrp'] = get_cell_data(row_idx, value, reader, file_type)
            elif key == 'discount':
                discount = get_cell_data(row_idx, value, reader, file_type)
                if discount:
                    order_summary_dict['discount'] = get_cell_data(row_idx, value, reader, file_type)
            elif key == 'quantity_count':
                if isinstance(value, (list)):
                    try:
                        cell_data = get_cell_data(row_idx, value[0], reader, file_type)
                        order_data['quantity'] = len(cell_data.split(value[1]))
                    except:
                        order_data['quantity'] = 1
            elif key == 'sor_id':
                cell_data = get_cell_data(row_idx, value, reader, file_type)
                if isinstance(cell_data, float):
                    cell_data = str(int(cell_data))
                seller_order_dict['sor_id'] = cell_data
            elif key == 'order_date':
                try:
                    cell_data = get_cell_data(row_idx, value, reader, file_type)
                    year, month, day, hour, minute, second = xldate_as_tuple(cell_data, 0)
                    order_date = datetime.datetime(year, month, day, hour, minute, second)
                except:
                    order_date = datetime.datetime.now()
                order_data['creation_date'] = order_date
            elif key == 'order_status':
                seller_order_dict[key] = get_cell_data(row_idx, value, reader, file_type)
            elif key == 'seller':
                seller_id = get_cell_data(row_idx, value, reader, file_type)
                if isinstance(seller_id, float):
                    seller_id = int(seller_id)
                seller_master = SellerMaster.objects.filter(seller_id=seller_id, user=user.id)
                if seller_master:
                    seller_order_dict['seller_id'] = seller_master[0].id
            elif key == 'invoice_no':
                seller_order_dict['invoice_no'] = get_cell_data(row_idx, value, reader, file_type)
            elif key == 'tax_percentage':
                tax_percentage = get_cell_data(row_idx, value[0], reader, file_type)
                if not tax_percentage:
                    tax_percentage = 0
                invoice_amount_value = get_cell_data(row_idx, value[1], reader, file_type)
                if not invoice_amount_value:
                    invoice_amount_value = 0
                order_data['vat_percentage'] = tax_percentage
                order_summary_dict['vat'] = tax_percentage
                order_summary_dict['tax_value'] = "%.2f" % ((tax_percentage*invoice_amount_value)/100)
                invoice_amount_value = invoice_amount_value + ((tax_percentage*invoice_amount_value)/100)
                order_data['invoice_amount'] = invoice_amount_value
                if not order_data['marketplace']:
                    order_data['marketplace'] = "Offline"
            else:
                order_data[key] = get_cell_data(row_idx, value, reader, file_type)

        order_data['user'] = user.id
        if not 'quantity' in order_data.keys():
            order_data['quantity'] = 1

        seller_order_dict['quantity'] = order_data['quantity']

        if type(sku_code) == float:
            cell_data = int(sku_code)
        else:
            cell_data = sku_code.upper()

        if not order_data.get('order_id', ''):
            order_data['order_id'] = get_order_id(user_id)
            order_data['order_code'] = 'MN'

        sku_codes = str(cell_data).split(',')
        for cell_data in sku_codes:
            sku_master=SKUMaster.objects.filter(sku_code=cell_data, user=user.id)
            if sku_master:
                order_data['sku_id'] = sku_master[0].id
                if not 'title' in order_mapping.keys():
                    order_data['title'] = sku_master[0].sku_desc
            else:
                market_mapping = ''
                if cell_data:
                    market_mapping = MarketplaceMapping.objects.filter(marketplace_code=cell_data, sku__user=user.id, sku__status=1)
                if not market_mapping and order_data['title']:
                    market_mapping = MarketplaceMapping.objects.filter(description=order_data['title'], sku__user=user.id, sku__status=1)
                if market_mapping:
                    order_data['sku_id'] = market_mapping[0].sku_id
                    if not 'title' in order_mapping.keys():
                        order_data['title'] = market_mapping[0].sku.sku_desc
                #else:
                #    order_data['sku_id'] = SKUMaster.objects.get(sku_code='TEMP', user=user.id).id
                #    order_data['sku_code'] = sku_code

            order_obj = OrderDetail.objects.filter(order_id = order_data['order_id'], sku=order_data['sku_id'], user=user.id)
            order_create = True
            if user_profile.user_type == 'marketplace_user':
                if not seller_order_dict['seller_id'] or (not seller_order_dict.get('order_status','') in ['PROCESSED', 'DELIVERY_RESCHEDULED']):
                    order_create = False
            if not order_obj and order_create:
                if not 'shipment_date' in order_mapping.keys():
                    order_data['shipment_date'] = datetime.datetime.now()
                order_detail = OrderDetail(**order_data)
                order_detail.save()
                check_create_seller_order(seller_order_dict, order_detail, user)
                if order_data['sku_id'] not in sku_ids:
                    sku_ids.append(order_data['sku_id'])
                #if order_summary_dict.get('vat', '') or order_summary_dict.get('tax_value', '') or order_summary_dict.get('mrp', '') or\
                #                         order_summary_dict.get('discount', ''):

                order_summary_dict['order_id'] = order_detail.id
                time_slot = get_local_date(user, datetime.datetime.now())
                order_summary_dict['shipment_time_slot'] = " ".join(time_slot.split(" ")[-2:])
                order_summary = CustomerOrderSummary(**order_summary_dict)
                order_summary.save()

            elif order_data['sku_id'] in sku_ids and order_create:
                order_obj = order_obj[0]
                order_obj.quantity = order_obj.quantity + order_data['quantity']
                order_obj.save()
                check_create_seller_order(seller_order_dict, order_obj, user)
            elif order_obj and order_create and seller_order_dict.get('seller_id', '') and \
                 seller_order_dict.get('order_status') == 'DELIVERY_RESCHEDULED':
                order_obj = order_obj[0]
                if int(order_obj.status) in [2, 4]:
                    order_obj.status = 1
                    update_seller_order(seller_order_dict, order_obj, user)
                    order_obj.save()


    return 'success'

@csrf_exempt
@login_required
@get_admin_user
def order_upload(request, user=''):
    fname = request.FILES['files']
    if (fname.name).split('.')[-1] == 'csv':
        reader = [[val.replace('\n', '').replace('\t', '').replace('\r','') for val in row] for row in csv.reader(fname.read().splitlines())]
        no_of_rows = len(reader)
        file_type = 'csv'

    elif (fname.name).split('.')[-1] == 'xls' or (fname.name).split('.')[-1] == 'xlsx':
        try:
            data = fname.read()
            if '<table' in data:
                open_book, open_sheet = html_excel_data(data, fname)
            else:
                open_book = open_workbook(filename=None, file_contents=data)
                open_sheet = open_book.sheet_by_index(0)
        except:
            return HttpResponse("Invalid File")
        reader = open_sheet
        no_of_rows = reader.nrows
        file_type = 'xls'

    try:
        upload_status = order_csv_xls_upload(request, reader, user, no_of_rows, fname, file_type=file_type)
    except Exception as e:
        log.info('Order Upload failed for %s and params are %s and error statement is %s' % (str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Order Upload Failed")

    if not upload_status == 'success':
        return HttpResponse(upload_status)

    return HttpResponse('Success')

@csrf_exempt
def rewrite_excel_file(f_name, index_status, open_sheet):
    #wb = Workbook()
    #ws = wb.add_sheet(open_sheet.name)
    wb1, ws1 = get_work_sheet(open_sheet.name, [], f_name)

    if 'xlsx' in f_name:
        header_style = wb1.add_format({'bold': True})
    else:
        header_style = easyxf('font: bold on')

    for row_idx in range(0, open_sheet.nrows):
        if row_idx == 0:
            for col_idx in range(0, open_sheet.ncols):
                ws1.write(row_idx, col_idx, str(open_sheet.cell(row_idx, col_idx).value), header_style)
            ws1.write(row_idx, col_idx + 1, 'Status', header_style)

        else:
            for col_idx in range(0, open_sheet.ncols):
                #print row_idx, col_idx, open_sheet.cell(row_idx, col_idx).value
                if col_idx == 4 and 'xlsx' in f_name:
                    date_format = wb1.add_format({'num_format': 'yyyy-mm-dd'})
                    ws1.write(row_idx, col_idx, open_sheet.cell(row_idx, col_idx).value, date_format)
                else:
                    ws1.write(row_idx, col_idx, open_sheet.cell(row_idx, col_idx).value)

            index_data = index_status.get(row_idx, '')
            if index_data:
                index_data = ', '.join(index_data)
                ws1.write(row_idx, col_idx + 1, index_data)

    if 'xlsx' in f_name:
        wb1.close()
    else:
        wb1.save(f_name)

@csrf_exempt
@get_admin_user
def order_form(request, user=''):
    order_file = request.GET['download-order-form']
    if order_file:
        with open(order_file, 'r') as excel:
            data = excel.read()
        response = HttpResponse(data, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s' % smart_str(order_file)
        return response

    wb = Workbook()
    ws = wb.add_sheet('supplier')
    header_style = easyxf('font: bold on')

    for count, header in enumerate(ORDER_HEADERS):
        ws.write(0, count, header, header_style)

    return xls_to_response(wb, '%s.order_form.xls' % str(user.id))

def xls_to_response(xls, fname):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename=%s' % fname
    xls.save(response)
    return response

@csrf_exempt
@get_admin_user
def sku_form(request, user=''):
    sku_file = request.GET['download-sku-file']
    if sku_file:
        return error_file_download(sku_file)
    user_profile = UserProfile.objects.get(user_id=user.id)

    wb, ws = get_work_sheet('skus', USER_SKU_EXCEL[user_profile.user_type])
    data = SKUMaster.objects.filter(wms_code='', user = user.id)
    for data_count, record in enumerate(data):
        if record.wms_code:
            continue

        data_count += 1
        ws.write(data_count, 0, record.wms_code)

    return xls_to_response(wb, '%s.sku_form.xls' % str(user.id))

@csrf_exempt
@get_admin_user
def sales_returns_form(request, user=''):
    returns_file = request.GET['download-sales-returns']
    if returns_file:
        return error_file_download(returns_file)

    wb, ws = get_work_sheet('returns', SALES_RETURNS_HEADERS)
    return xls_to_response(wb, '%s.returns_form.xls' % str(user.id))

@csrf_exempt
@login_required
@get_admin_user
def inventory_form(request, user=''):
    inventory_file = request.GET['download-file']
    if inventory_file:
        return error_file_download(inventory_file)
    pallet_switch = get_misc_value('pallet_switch', user.id)
    if pallet_switch == 'true' and 'Pallet Number' not in EXCEL_HEADERS:
        EXCEL_HEADERS.append("Pallet Number")
    wb, ws = get_work_sheet('Inventory', EXCEL_HEADERS)
    return xls_to_response(wb, '%s.inventory_form.xls' % str(user.id))

@csrf_exempt
@get_admin_user
def supplier_form(request, user=''):
    supplier_file = request.GET['download-supplier-file']
    if supplier_file:
        return error_file_download(supplier_file)

    wb, ws = get_work_sheet('supplier', SUPPLIER_HEADERS)
    return xls_to_response(wb, '%s.supplier_form.xls' % str(user.id))

@csrf_exempt
@get_admin_user
def supplier_sku_form(request, user=''):
    supplier_file = request.GET['download-supplier-sku-file']
    if supplier_file:
        return error_file_download(supplier_file)

    wb, ws = get_work_sheet('supplier', SUPPLIER_SKU_HEADERS)
    return xls_to_response(wb, '%s.supplier_sku_form.xls' % str(user.id))

@csrf_exempt
@get_admin_user
def location_form(request, user=''):
    loc_file = request.GET['download-loc-file']
    if loc_file:
        return error_file_download(loc_file)

    wb, ws = get_work_sheet('Locations', LOCATION_HEADERS)
    return xls_to_response(wb, '%s.location_form.xls' % str(user.id))

@csrf_exempt
@get_admin_user
def purchase_order_form(request, user=''):
    order_file = request.GET['download-purchase-order-form']
    if order_file:
        with open(order_file, 'r') as excel:
            data = excel.read()
        response = HttpResponse(data, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s' % smart_str(order_file)
        return response
    wb = Workbook()
    ws = wb.add_sheet('supplier')
    header_style = easyxf('font: bold on')
    for count, header in enumerate(PURCHASE_ORDER_HEADERS):
        ws.write(0, count, header, header_style)

    return xls_to_response(wb, '%s.purchase_order_form.xls' % str(user.id))

@csrf_exempt
@login_required
@get_admin_user
def move_inventory_form(request, user=''):
    inventory_file = request.GET['download-move-inventory-file']
    if inventory_file:
        return error_file_download(inventory_file)
    wb, ws = get_work_sheet('Inventory', MOVE_INVENTORY_UPLOAD_FIELDS)
    return xls_to_response(wb, '%s.move_inventory_form.xls' % str(user.id))

@csrf_exempt
@get_admin_user
def marketplace_sku_form(request, user=''):
    market_list = ['WMS Code']
    market_sku = []
    market_desc = []
    supplier_file = request.GET['download-marketplace-sku-file']
    if supplier_file:
        return error_file_download(supplier_file)
    market_places = Marketplaces.objects.filter(user=user.id).values_list('name', flat=True)
    for market in market_places:
        market_sku.append(market + " SKU")
        market_desc.append(market + " Description")
    market_list = market_list + market_sku + market_desc

    wb, ws = get_work_sheet('supplier', market_list)
    return xls_to_response(wb, '%s.marketplace_sku_form.xls' % str(user.id))

@csrf_exempt
@login_required
@get_admin_user
def bom_form(request, user=''):
    bom_file = request.GET['download-bom-file']
    if bom_file:
        return error_file_download(bom_file)
    wb, ws = get_work_sheet('BOM', BOM_UPLOAD_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.bom_form.xls' % str(user.id))

@csrf_exempt
@login_required
@get_admin_user
def combo_sku_form(request, user=''):
    combo_sku_file = request.GET['download-combo-sku-file']
    if combo_sku_file:
        return error_file_download(combo_sku_file)
    wb, ws = get_work_sheet('COMBO_SKU', COMBO_SKU_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.combo_sku_form.xls' % str(user.id))

@csrf_exempt
@login_required
@get_admin_user
def inventory_adjust_form(request, user=''):
    inventory_file = request.GET['download-inventory-adjust-file']
    if inventory_file:
        return error_file_download(inventory_file)
    wb, ws = get_work_sheet('INVENTORY_ADJUST', ADJUST_INVENTORY_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.inventory_adjustment_form.xls' % str(user.id))

@csrf_exempt
@get_admin_user
def vendor_form(request, user=''):
    vendor_file = request.GET['download-vendor-file']
    if vendor_file:
        return error_file_download(vendor_file)

    wb, ws = get_work_sheet('vendor', VENDOR_HEADERS)
    return xls_to_response(wb, '%s.vendor_form.xls' % str(user.id))

@csrf_exempt
@get_admin_user
def pricing_master_form(request, user=''):
    returns_file = request.GET['download-pricing-master']
    if returns_file:
        return error_file_download(returns_file)

    wb, ws = get_work_sheet('Prices', PRICING_MASTER_HEADERS)
    return xls_to_response(wb, '%s.pricing_master_form.xls' % str(user.id))

@csrf_exempt
def validate_sku_form(request, reader, user, no_of_rows, fname, file_type='xls'):
    sku_data = []
    wms_data = []
    index_status = {}

    sku_file_mapping = get_sku_file_mapping(reader, file_type, user=user.id)
    if not sku_file_mapping:
        return 'Invalid File'
    for row_idx in range(1, no_of_rows):
        sku_code = ''
        for key, value in sku_file_mapping.iteritems():
            cell_data = get_cell_data(row_idx, sku_file_mapping[key], reader, file_type)

            if key == 'wms_code':
                data_set = wms_data
                data_type = 'WMS'
                sku_code = cell_data
                #index_status = check_duplicates(data_set, data_type, cell_data, index_status, row_idx)
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('WMS Code missing')
            elif key == 'sku_group':
                if cell_data:
                    sku_groups = SKUGroups.objects.filter(group__iexact=cell_data, user=user.id)
                    if not sku_groups:
                        index_status.setdefault(row_idx, set()).add("Group doesn't exists")

            elif key == 'zone_id':
                if cell_data:
                    data = ZoneMaster.objects.filter(zone=cell_data.upper(),user=user.id)
                    if not data:
                        index_status.setdefault(row_idx, set()).add('Invalid Zone')
                #else:
                #    index_status.setdefault(row_idx, set()).add('Zone should not be empty')
            elif key == 'ean_number':
                if not isinstance(cell_data, (int, float)) and cell_data:
                    index_status.setdefault(row_idx, set()).add('EAN must be integer')
                elif cell_data:
                    ean_status = check_ean_number(sku_code, cell_data, user)
                    if ean_status:
                        index_status.setdefault(row_idx, set()).add(ean_status)

            elif key == 'sku_size':
                if cell_data:
                    all_sizes = all_size_list(user)
                    try:
                        _size = str(int(cell_data))
                    except:
                        _size = cell_data

                    _size_type = get_cell_data(row_idx, sku_file_mapping['size_type'], reader, file_type)
                    if not _size_type:
                        index_status.setdefault(row_idx, set()).add('Size Type should not be blank, if size is there')

                    else:
                        size_master = SizeMaster.objects.filter(user=user.id, size_name=_size_type)
                        if not size_master:
                            index_status.setdefault(row_idx, set()).add('Please Enter Correct Size type')
                        else:
                            _sizes_all = size_master[0].size_value.split("<<>>")
                            if _size not in _sizes_all:
                                index_status.setdefault(row_idx, set()).add('Size type and size are not matching')

                    if _size not in all_sizes:
                        index_status.setdefault(row_idx, set()).add('Size is not Correct')

            elif key == 'threshold_quantity':
                if not isinstance(cell_data, (int, float)) and cell_data:
                    index_status.setdefault(row_idx, set()).add('Invalid Quantity')

                if cell_data and isinstance(cell_data, (int, float)):
                    if int(cell_data) < 0:
                        index_status.setdefault(row_idx, set()).add('Quantity should not be in negative')

            elif key == 'price':
                if not isinstance(cell_data, (int, float)) and cell_data:
                    index_status.setdefault(row_idx, set()).add('Invalid Price')
            elif key == 'mix_sku':
                if cell_data and cell_data.lower() not in MIX_SKU_MAPPING.keys():
                    index_status.setdefault(row_idx, set()).add('Invalid option for Mix SKU')
            elif key == 'load_unit_handle':
                if cell_data and cell_data.lower() not in LOAD_UNIT_HANDLE_DICT.keys():
                    index_status.setdefault(row_idx, set()).add('Invalid option for Load Unit Handling')

    master_sku = SKUMaster.objects.filter(user=user.id)
    master_sku = [data.sku_code for data in master_sku]
    missing_data = set(sku_data) - set(master_sku)

    if not index_status:
        return 'Success'

    if index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        rewrite_excel_file(f_name, index_status, reader)
        return f_name
    elif index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        rewrite_csv_file(f_name, index_status, reader)
        return f_name


def get_sku_file_mapping(reader, file_type, user=''):
    sku_file_mapping = {}
    if get_cell_data(0, 0, reader, file_type) == 'WMS Code' and get_cell_data(0, 1, reader, file_type) == 'SKU Description':
        if user:
            user_profile = UserProfile.objects.get(user_id=user)
            sku_file_mapping = copy.deepcopy(USER_SKU_EXCEL_MAPPING[user_profile.user_type])
        else:
            sku_file_mapping = copy.deepcopy(SKU_DEF_EXCEL)
    elif get_cell_data(0, 1, reader, file_type) == 'Product Code' and get_cell_data(0, 2, reader, file_type) == 'Name':
        sku_file_mapping = copy.deepcopy(ITEM_MASTER_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'product_id' and get_cell_data(0, 1, reader, file_type) == 'product_variant_id':
        sku_file_mapping = copy.deepcopy(SHOTANG_SKU_MASTER_EXCEL)

    return sku_file_mapping

def sku_excel_upload(request, reader, user, no_of_rows, fname, file_type='xls'):

    from masters import check_update_size_type
    all_sku_masters = []
    zone_master = ZoneMaster.objects.filter(user=user.id).values('id', 'zone')
    zones = map(lambda d: d['zone'], zone_master)
    zone_ids = map(lambda d: d['id'], zone_master)
    sku_file_mapping = get_sku_file_mapping(reader, file_type, user)
    for row_idx in range(1, no_of_rows):
        if not sku_file_mapping:
            continue

        data_dict = copy.deepcopy(SKU_DATA)
        data_dict['user'] = user.id

        sku_code = ''
        wms_code = ''
        sku_data = None
        _size_type = ''
        for key, value in sku_file_mapping.iteritems():
            cell_data = get_cell_data(row_idx, sku_file_mapping[key], reader, file_type)

            if key == 'wms_code':
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(xcode(cell_data))

                wms_code = cell_data
                data_dict[key] = wms_code
                if wms_code:
                    sku_data = SKUMaster.objects.filter(wms_code = wms_code,user=user.id)
                    if sku_data:
                        sku_data = sku_data[0]

            elif key == 'zone_id':
                zone_id = None
                if cell_data:
                    cell_data = cell_data.upper()
                    if cell_data in zones:
                        #zone_id = ZoneMaster.objects.get(zone=cell_data.upper(),user=user.id).id
                        zone_id = zone_ids[zones.index(cell_data)]
                    if sku_data and cell_data:
                        sku_data.zone_id = zone_id
                    data_dict[key] = zone_id

            elif key == 'status':
                if cell_data.lower() == 'inactive':
                    status = 0
                else:
                    status = 1
                if sku_data and cell_data:
                    sku_data.status = status
                data_dict[key] = status

            elif key == 'sku_desc':
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                try:
                    cell_data = (str(re.sub(r'[^\x00-\x7F]+','', cell_data))).replace('\n', '')
                except:
                    cell_data = ''
                if sku_data and cell_data:
                    sku_data.sku_desc = cell_data
                data_dict[key] = cell_data

            elif key == 'threshold_quantity':
                if not cell_data:
                    cell_data = 0
                if sku_data and cell_data:
                    sku_data.threshold_quantity = cell_data
                data_dict[key] = cell_data

            elif key == 'price':
                if not cell_data:
                    cell_data = 0
                if sku_data and cell_data:
                    sku_data.price = cell_data
                data_dict[key] = cell_data

            elif key == 'mix_sku':
                if cell_data:
                    cell_data = MIX_SKU_MAPPING[cell_data.lower()]
                if sku_data and cell_data:
                    sku_data.mix_sku = cell_data
                data_dict[key] = cell_data

            elif key == 'load_unit_handle':
                if cell_data:
                    cell_data = LOAD_UNIT_HANDLE_DICT[cell_data.lower()]
                if sku_data and cell_data:
                    setattr(sku_data, key, cell_data)
                data_dict[key] = cell_data


            elif key == 'sku_size':
                try:
                    data_dict['sku_size'] = str(int(cell_data))
                except:
                    data_dict['sku_size'] = cell_data
                _size_type = get_cell_data(row_idx, sku_file_mapping['size_type'], reader, file_type)

            elif key == 'size_type':
                continue

            elif cell_data:
                data_dict[key] = cell_data
                if sku_data:
                    setattr(sku_data, key, cell_data)
                data_dict[key] = cell_data
        if sku_data:
            sku_data.save()

        if not sku_data:
            data_dict['sku_code'] = data_dict['wms_code']
            sku_master = SKUMaster(**data_dict)
            sku_master.save()
            all_sku_masters.append(sku_master)
            sku_data = sku_master

        if _size_type:
            check_update_size_type(sku_data, _size_type)

    #get_user_sku_data(user)
    insert_update_brands(user)

    all_users = get_related_users(user.id)
    sync_sku_switch = get_misc_value('sku_sync', user.id)
    if all_users and sync_sku_switch == 'true' and all_sku_masters:
        create_sku(all_sku_masters, all_users)
    return 'success'


@csrf_exempt
@login_required
@get_admin_user
def sku_upload(request, user=''):
    fname = request.FILES['files']
    if (fname.name).split('.')[-1] == 'csv':
        reader = [[val.replace('\n', '').replace('\t', '').replace('\r','') for val in row] for row in csv.reader(fname.read().splitlines())]
        no_of_rows = len(reader)
        file_type = 'csv'
    elif (fname.name).split('.')[-1] == 'xls' or (fname.name).split('.')[-1] == 'xlsx':
        try:
            data = fname.read()
            if '<table' in data:
                open_book, open_sheet = html_excel_data(data, fname)
            else:
                open_book = open_workbook(filename=None, file_contents=data)
                open_sheet = open_book.sheet_by_index(0)
        except:
            return HttpResponse("Invalid File")
        reader = open_sheet
        no_of_rows = reader.nrows
        file_type = 'xls'
    else:
        return HttpResponse('Invalid File')

    try:
        status = validate_sku_form(request, reader, user, no_of_rows, fname, file_type=file_type)
        if status != 'Success':
            return HttpResponse(status)

        sku_excel_upload(request, reader, user, no_of_rows, fname, file_type=file_type)
    except Exception as e:
        log.info('SKU Master Upload failed for %s and params are %s and error statement is %s' % (str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("SKU Master Upload Failed")


    return HttpResponse('Success')

@csrf_exempt
def validate_inventory_form(open_sheet, user_id):
    mapping_dict = {}
    index_status = {}
    location = {}
    for row_idx in range(0, open_sheet.nrows):
        for col_idx in range(0, len(EXCEL_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if row_idx == 0:
                if col_idx == 0 and cell_data != 'Receipt Number':
                    return 'Invalid File'
                break

            validation_dict = {0: 'Receipt Number', 1: 'receipt date', 3: 'Location'}
            if col_idx in validation_dict and not cell_data:
                index_status.setdefault(row_idx, set()).add('Invalid %s' % validation_dict[col_idx])

            if col_idx == 1:
                try:
                    receipt_date = xldate_as_tuple(cell_data, 0)
                except:
                    index_status.setdefault(row_idx, set()).add('Invalid Receipt Date format')

            if col_idx == 2:
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                try:
                    cell_data = str(re.sub(r'[^\x00-\x7F]+','', cell_data))
                except:
                    cell_data = ''

                mapping_dict[row_idx] = cell_data
                #sku_master = SKUMaster.objects.filter(wms_code = cell_data,user=user_id)
                #if not sku_master:
                user = User.objects.get(id = user_id)
                sku_id = check_and_return_mapping_id(cell_data, '', user)
                if not sku_id:
                    index_status.setdefault(row_idx, set()).add('Invalid SKU-WMS Mapping')
            elif col_idx == 3:
                location[row_idx] = cell_data
            elif col_idx == 4:
                if cell_data and (not isinstance(cell_data, (int, float)) or (int(cell_data) < 0)):
                    index_status.setdefault(row_idx, set()).add('Invalid Quantity')
            elif col_idx == 5:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing Receipt Type')

    locations = LocationMaster.objects.filter(zone__user=user_id).values('location')
    locations = [loc['location'] for loc in locations]
    location_diff = set(location.values()) - set(locations)

    for key, value in location.iteritems():
        if value and value in location_diff:
            index_status.setdefault(key, set()).add('Invalid Location')

    if not index_status:
        return 'Success'

    f_name = '%s.inventory_form.xls' % user_id
    write_error_file(f_name, index_status, open_sheet, EXCEL_HEADERS, 'Inventory')
    return f_name

def check_location(location, user, quantity=0):
    loc_existance = LocationMaster.objects.get(location=location, zone__user=user)
    if loc_existance:
        return int(loc_existance.id)
    else:
        return

def inventory_excel_upload(request, open_sheet, user):
    RECORDS = list(EXCEL_RECORDS)
    sku_codes = []
    mod_locations = []
    pallet_switch = get_misc_value('pallet_switch', user.id)
    if pallet_switch == 'true' and 'Pallet Number' not in EXCEL_HEADERS:
        EXCEL_HEADERS.append('Pallet Number')
        RECORDS.append('pallet_number')

    for row_idx in range(1, open_sheet.nrows):
        location_data = ''
        inventory_data = {}
        pallet_number = ''
        for col_idx in range(0, len(EXCEL_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value

            if col_idx == 1:
                year, month, day, hour, minute, second = xldate_as_tuple(cell_data, 0)
                receipt_date = datetime.datetime(year, month, day, hour, minute, second)

            if col_idx == 2 and cell_data:
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(cell_data)
                inventory_data['sku_id'] = check_and_return_mapping_id(cell_data, '', user)

                if cell_data not in sku_codes:
                    sku_codes.append(cell_data)
                if not inventory_data['sku_id']:
                    break
                continue
            elif col_idx == 2 and not cell_data:
                break

            if not cell_data:
                continue
            data_id = RECORDS[col_idx]
            if data_id in ('wms_code', 'location'):
                cell_data = cell_data.strip().upper()

            if data_id == 'location':
                location_data = cell_data

            if data_id == 'wms_quantity':
                inventory_data['quantity'] = cell_data

            if data_id == 'receipt_number':
                receipt_number = cell_data

            if data_id == 'wms_code':
                wms_id = SKUMaster.objects.get(wms_code=cell_data, user=user.id)
                inventory_data['sku_id'] = wms_id.id
            if data_id == 'pallet_number':
                pallet_number = cell_data
            if data_id == 'receipt_type':
                inventory_data['receipt_type'] = cell_data
        if location_data:
            quantity = inventory_data.get('quantity', 0)
            location_id = check_location(location_data, user.id, quantity)
            inventory_data['location_id'] = location_id

        if inventory_data.get('sku_id', '') and inventory_data.get('location_id', ''):
            if pallet_number:
                pallet_data = {'pallet_code': pallet_number, 'quantity': int(inventory_data['quantity']), 'user': user.id,
                               'status': 1, 'creation_date': str(datetime.datetime.now()), 'updation_date': str(datetime.datetime.now())}
                pallet_detail = PalletDetail(**pallet_data)
                pallet_detail.save()
                inventory_status = StockDetail.objects.filter(sku_id=inventory_data.get('sku_id', ''), location_id=inventory_data.get('location_id', ''), receipt_number=receipt_number, sku__user=user.id, pallet_detail_id=pallet_detail.id)
            else:
                inventory_status = StockDetail.objects.filter(sku_id=inventory_data.get('sku_id', ''), location_id=inventory_data.get('location_id', ''), receipt_number=receipt_number, sku__user=user.id)
            if not inventory_status and inventory_data.get('quantity', ''):
                inventory_data['status'] = 1
                inventory_data['creation_date'] = str(datetime.datetime.now())
                inventory_data['receipt_date'] = receipt_date
                inventory_data['receipt_number'] = receipt_number
                if pallet_switch == 'true' and pallet_number:
                    inventory_data['pallet_detail_id'] = pallet_detail.id
                sku_master = SKUMaster.objects.get(id=inventory_data['sku_id'])
                if not sku_master.zone:
                    location_master = LocationMaster.objects.get(id=inventory_data['location_id'])
                    sku_master.zone_id = location_master.zone_id
                    sku_master.save()
                inventory = StockDetail(**inventory_data)
                inventory.save()
                mod_locations.append(inventory.location.location)

            elif inventory_status and inventory_data.get('quantity', ''):
                inventory_status = inventory_status[0]
                inventory_status.quantity = int(inventory_status.quantity) + int(inventory_data.get('quantity', 0))
                inventory_status.receipt_date = receipt_date
                inventory_status.save()
                mod_locations.append(inventory_status.location.location)

            location_master = LocationMaster.objects.get(id=inventory_data.get('location_id', ''), zone__user=user.id)
            location_master.filled_capacity += inventory_data.get('quantity', 0)
            location_master.save()

    check_and_update_stock(sku_codes, user)
    if mod_locations:
        update_filled_capacity(list(set(mod_locations)), user.id)

    return 'success'

@csrf_exempt
@login_required
@get_admin_user
def inventory_upload(request, user=''):
    fname = request.FILES['files']
    try:
        open_book = open_workbook(filename=None, file_contents=fname.read())
        open_sheet = open_book.sheet_by_index(0)
    except:
        return HttpResponse('Invalid File')
    status =  validate_inventory_form(open_sheet, str(user.id))

    if status != 'Success':
        return HttpResponse(status)

    inventory_excel_upload(request, open_sheet, user)

    return HttpResponse('Success')

@csrf_exempt
def validate_supplier_form(open_sheet, user_id):
    index_status = {}
    supplier_ids = []
    mapping_dict = copy.deepcopy(SUPPLIER_EXCEL_FIELDS)
    for row_idx in range(0, open_sheet.nrows):
        for key, value in mapping_dict.iteritems():
            cell_data = open_sheet.cell(row_idx, mapping_dict[key]).value
            if row_idx == 0:
                if open_sheet.cell(row_idx, 0).value != 'Supplier Id':
                    return 'Invalid File'
                break

            if key == 'id':
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                if cell_data and cell_data in supplier_ids:
                    index_status.setdefault(row_idx, set()).add('Duplicate Supplier ID')
                    for index, data in enumerate(supplier_ids):
                        if data == cell_data:
                            index_status.setdefault(index + 1, set()).add('Duplicate Supplier ID')
                supplier_ids.append(cell_data)

            elif key == 'name':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing Supplier Name')
            elif key == 'email_id':
                if cell_data and validate_email(cell_data):
                    index_status.setdefault(row_idx, set()).add('Enter Valid Email address')

            elif key == 'phone_number':
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Wrong contact information')

    if not index_status:
        return 'Success'

    f_name = '%s.supplier_form.xls' % user_id
    write_error_file(f_name, index_status, open_sheet, SUPPLIER_HEADERS, 'Supplier')
    return f_name

def supplier_excel_upload(request, open_sheet, user, demo_data=False):
    mapping_dict = copy.deepcopy(SUPPLIER_EXCEL_FIELDS)
    number_str_fields = ['pincode', 'phone_number']
    for row_idx in range(1, open_sheet.nrows):
        sku_code = ''
        wms_code = ''
        supplier_data = copy.deepcopy(SUPPLIER_DATA)
        supplier_master = None
        for key, value in mapping_dict.iteritems():
            cell_data = open_sheet.cell(row_idx, mapping_dict[key]).value
            if key == 'id':
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                supplier_data['id'] = cell_data
                supplier_obj = SupplierMaster.objects.filter(id=cell_data)
                if supplier_obj:
                    supplier_master = supplier_obj[0]
                if demo_data:
                    user_profile = UserProfile.objects.filter(user_id=user.id)
                    if user_profile:
                        supplier_data['id'] = user_profile[0].prefix + '_' + supplier_data['id']
            elif key == 'name':
                if not isinstance(cell_data, (str, unicode)):
                    cell_data = str(int(cell_data))
                supplier_data['name'] = cell_data
                if supplier_master and cell_data:
                    setattr(supplier_master, key, cell_data)

            elif key in number_str_fields:
                if cell_data:
                    cell_data = int(float(cell_data))
                    supplier_data[key] = cell_data
                    if supplier_master:
                        setattr(supplier_master, key, cell_data)

            else:
                supplier_data[key] = cell_data
                if supplier_master and cell_data:
                    setattr(supplier_master, key, cell_data)

        if not supplier_master:
            supplier = SupplierMaster.objects.filter(id=supplier_data['id'], user=user.id)
            if not supplier:
                supplier_data['creation_date'] = datetime.datetime.now()
                supplier_data['user'] = user.id
                supplier = SupplierMaster(**supplier_data)
                supplier.save()
        else:
            supplier_master.save()

    return 'success'

@csrf_exempt
@login_required
@get_admin_user
def supplier_upload(request, user=''):
    fname = request.FILES['files']
    if fname.name.split('.')[-1] == 'xls' or fname.name.split('.')[-1] == 'xlsx':
        try:
            open_book = open_workbook(filename=None, file_contents=fname.read())
            open_sheet = open_book.sheet_by_index(0)
        except:
            return HttpResponse('Invalid File')

        status = validate_supplier_form(open_sheet, str(user.id))
        if status != 'Success':
            return HttpResponse(status)

        supplier_excel_upload(request, open_sheet, user)

    return HttpResponse('Success')

@csrf_exempt
def validate_vendor_form(open_sheet, user_id):
    index_status = {}
    vendor_ids = []
    for row_idx in range(0, open_sheet.nrows):
        for col_idx in range(0, len(VENDOR_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if row_idx == 0:
                if col_idx == 0 and cell_data != 'Vendor Id':
                    return 'Invalid File'
                break

            if col_idx == 0:
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                if cell_data and cell_data in vendor_ids:
                    index_status.setdefault(row_idx, set()).add('Duplicate Vendor ID')
                    for index, data in enumerate(vendor_ids):
                        if data == cell_data:
                            index_status.setdefault(index + 1, set()).add('Duplicate Vendor ID')
                if cell_data:
                    vendor_master = VendorMaster.objects.filter(vendor_id=cell_data, user=user_id)
                    if vendor_master:
                        index_status.setdefault(row_idx, set()).add('Vendor Id already exists')
                vendor_ids.append(cell_data)

            if col_idx == 1:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing Vendor Name')

            if col_idx == 4:
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Wrong contact information')

    if not index_status:
        return 'Success'

    f_name = '%s.vendor_form.xls' % user_id
    write_error_file(f_name, index_status, open_sheet, VENDOR_HEADERS, 'Vendor')
    return f_name

@csrf_exempt
@login_required
@get_admin_user
def vendor_upload(request, user=''):
    fname = request.FILES['files']
    if fname.name.split('.')[-1] == 'xls' or fname.name.split('.')[-1] == 'xlsx':
        try:
            open_book = open_workbook(filename=None, file_contents=fname.read())
            open_sheet = open_book.sheet_by_index(0)
        except:
            return HttpResponse('Invalid File')

        status = validate_vendor_form(open_sheet, str(user.id))
        if status != 'Success':
            return HttpResponse(status)

        for row_idx in range(1, open_sheet.nrows):
            sku_code = ''
            wms_code = ''
            vendor_data = copy.deepcopy(VENDOR_DATA)
            for col_idx in range(0, len(VENDOR_HEADERS)):
                cell_data = open_sheet.cell(row_idx, col_idx).value
                if col_idx == 0:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    vendor_data['vendor_id'] = cell_data
                if col_idx == 1:
                    vendor_data['name']  = cell_data
                    if not isinstance(cell_data, (str, unicode)):
                        vendor_data['name'] = str(int(cell_data))

                if col_idx == 2:
                    vendor_data['address'] = cell_data
                if col_idx == 3:
                    vendor_data['email_id'] = cell_data
                if col_idx == 4:
                    if cell_data:
                        cell_data = int(float(cell_data))
                        vendor_data['phone_number'] = cell_data

            vendor = VendorMaster.objects.filter(vendor_id=vendor_data['vendor_id'], user=user.id)
            if not vendor:
                vendor_data['user'] = user.id
                vendor = VendorMaster(**vendor_data)
                vendor.save()

    return HttpResponse('Success')


@csrf_exempt
def validate_supplier_sku_form(open_sheet, user_id):
    index_status = {}
    supplier_ids = []
    temp1 = ''
    supplier_list = SupplierMaster.objects.filter(user=user_id).values_list('id',flat=True)
    if supplier_list:
        for i in supplier_list:
            supplier_ids.append(i)
    for row_idx in range(0, open_sheet.nrows):
        wms_code1 = ''
        preference1 = ''
        supplier_id = ''
        for col_idx in range(0, len(SUPPLIER_SKU_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if row_idx == 0:
                if col_idx == 0 and cell_data != 'Supplier Id':
                    return 'Invalid File'
                break
            if col_idx == 0:
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                supplier_id = cell_data
                if cell_data and cell_data not in supplier_ids:
                    index_status.setdefault(row_idx, set()).add('Supplier ID Not Found')
                    for index, data in enumerate(supplier_ids):
                        if data == cell_data:
                            index_status.setdefault(index + 1, set()).add('Supplier ID Not Found')
                supplier_ids.append(cell_data)

            if col_idx == 1:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing WMS Code')
                else:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    wms_check = SKUMaster.objects.filter(wms_code=cell_data,user=user_id)
                    if not wms_check:
                        index_status.setdefault(row_idx, set()).add('Invalid WMS Code')
                    wms_code1=cell_data
            if col_idx == 3:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing Preference')
                else:
                    preference1 = int(cell_data)

        if wms_code1 and preference1 and row_idx > 0:
            supp_val=SKUMaster.objects.filter(wms_code=wms_code1,user=user_id)
            if supp_val:
                temp1 = SKUSupplier.objects.filter(Q(sku_id=supp_val[0].id) & Q(preference=preference1), sku__user=user_id)
                sku_supplier = SKUSupplier.objects.filter(sku_id=supp_val[0].id, supplier_id=supplier_id, sku__user=user_id)
                if sku_supplier:
                    temp1 = []
            if temp1:
                index_status.setdefault(row_idx, set()).add('Preference matched with existing WMS Code')

    if not index_status:
        return 'Success'

    f_name = '%s.supplier_sku_form.xls' % user_id
    write_error_file(f_name, index_status, open_sheet, SUPPLIER_SKU_HEADERS, 'Supplier')
    return f_name

@csrf_exempt
@login_required
@get_admin_user
def supplier_sku_upload(request, user=''):
    fname = request.FILES['files']
    if fname.name.split('.')[-1] == 'xls' or fname.name.split('.')[-1] == 'xlsx':
        try:
            open_book = open_workbook(filename=None, file_contents=fname.read())
            open_sheet = open_book.sheet_by_index(0)
        except:
            return HttpResponse('Invalid File')

        status = validate_supplier_sku_form(open_sheet, str(user.id))
        if status != 'Success':
            return HttpResponse(status)

        supplier_sku_instance = None
        for row_idx in range(1, open_sheet.nrows):
            sku_code = ''
            wms_code = ''
            supplier_data = copy.deepcopy(SUPPLIER_SKU_DATA)
            for col_idx in range(0, len(SUPPLIER_SKU_HEADERS)):
                cell_data = open_sheet.cell(row_idx, col_idx).value
                if col_idx == 0:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    supplier_data['supplier_id'] = cell_data
                elif col_idx == 1:
                    if isinstance(cell_data, (int, float)):
                        cell_data = int(cell_data)
                    cell_data = str(cell_data)
                    sku_master = SKUMaster.objects.filter(wms_code=cell_data, user=user.id)
                    if sku_master:
                        supplier_data['sku'] = sku_master[0]
                    supplier_sku_obj = SKUSupplier.objects.filter(supplier_id=supplier_data['supplier_id'], sku_id=sku_master[0].id)
                    if supplier_sku_obj:
                        supplier_sku_instance = supplier_sku_obj[0]
                elif col_idx == 2:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    supplier_data['supplier_code'] = cell_data
                    if cell_data and supplier_sku_instance:
                        supplier_sku_instance.supplier_code = cell_data
                elif col_idx == 3:
                    supplier_data['preference'] = str(int(cell_data))
                    if supplier_data['preference'] and supplier_sku_instance:
                        supplier_sku_instance.preference = supplier_data['preference']
                elif col_idx == 4:
                    if not cell_data:
                        cell_data = 0
                    cell_data = int(cell_data)
                    supplier_data['moq'] = cell_data
                    if cell_data and supplier_sku_instance:
                        supplier_sku_instance.moq = cell_data
                elif col_idx == 5:
                    if not cell_data:
                        cell_data = 0
                    cell_data = float(cell_data)
                    supplier_data['price'] = cell_data
                    if cell_data and supplier_sku_instance:
                        supplier_sku_instance.price = cell_data

            supplier_sku = SupplierMaster.objects.filter(id=supplier_data['supplier_id'], user=user.id)
            if supplier_sku and not supplier_sku_obj:
                supplier_sku = SKUSupplier(**supplier_data)
                supplier_sku.save()
            elif supplier_sku_instance:
                supplier_sku_instance.save()
        return HttpResponse('Success')
    else:
        return HttpResponse('Invalid File Format')

@csrf_exempt
def validate_location_form(open_sheet, user):
    location_data = []
    index_status = {}
    header_data = open_sheet.cell(0, 0).value
    if header_data != 'Zone':
        return 'Invalid File'

    for row_idx in range(1, open_sheet.nrows):
        for col_idx in range(0, len(LOCATION_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value

            validation_dict = {0: 'Zone', 1: 'Location'}
            if col_idx in validation_dict:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing %s' % validation_dict[col_idx])
                    break

                value = validation_dict[col_idx]
                #index_status = alphanum_validation(cell_data, value, index_status, row_idx)

            if col_idx == 1:
                if cell_data in location_data:
                    index_status.setdefault(row_idx, set()).add('Duplicate Location')
                for index, location in enumerate(location_data):
                    if location == cell_data:
                        index_status.setdefault(index + 1, set()).add('Duplicate Location')

                location_data.append(cell_data)
            elif col_idx in (2, 3, 4):
                if cell_data and (not isinstance(cell_data, (int, float)) or int(cell_data) < 0):
                    index_status.setdefault(row_idx, set()).add('Invalid Quantity')
            elif col_idx == 5 and cell_data:
                all_groups = SKUGroups.objects.filter(user=user).values_list('group', flat=True)
                cell_datas = cell_data.split(',')
                for cell_data in cell_datas:
                    if cell_data and not cell_data in all_groups:
                        index_status.setdefault(row_idx, set()).add('SKU Group not found')


    if not index_status:
        return 'Success'
    f_name = '%s.location_form.xls' % user
    write_error_file(f_name, index_status, open_sheet, LOCATION_HEADERS, 'Issues')
    return f_name

@csrf_exempt
def process_location(request, open_sheet, user):
    for row_idx in range(1, open_sheet.nrows):
        location_data = copy.deepcopy(LOC_DATA)
        for col_idx in range(0, len(LOCATION_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value

            if col_idx == 0:
                zone = cell_data.upper()
                zone_data = ZoneMaster.objects.filter(zone=zone, user=user.id)
                if not zone_data:
                    zone_data = copy.deepcopy(ZONE_DATA)
                    zone_data['user'] = user.id
                    zone_data['zone'] = zone
                    zone_data = ZoneMaster(**zone_data)
                    zone_data.save()
                else:
                    zone_data = zone_data[0]

            if not cell_data:
                continue

            index_dict = {1: 'location', 2: 'max_capacity', 3: 'fill_sequence', 4: 'pick_sequence'}

            if col_idx in index_dict:
                location_data[index_dict[col_idx]] = cell_data

        location = LocationMaster.objects.filter(location=location_data['location'], zone__user = user.id)
        if not location:
            location_data['zone_id'] = zone_data.id
            location = LocationMaster(**location_data)
            location.save()
        else:
            location = location[0]
        sku_group = open_sheet.cell(row_idx, 5).value
        if sku_group:
            sku_group = sku_group.split(',')
            save_location_group(location.id, sku_group, user)

@csrf_exempt
@get_admin_user
def location_upload(request, user=''):
    fname = request.FILES['files']
    try:
        open_book = open_workbook(filename=None, file_contents=fname.read())
        open_sheet = open_book.sheet_by_index(0)
    except:
        return HttpResponse('Invalid File')

    status = validate_location_form(open_sheet, user.id)
    if status != 'Success':
        return HttpResponse(status)
    process_location(request, open_sheet, user)
    return HttpResponse('Success')

@csrf_exempt
def validate_purchase_order(open_sheet, user):
    index_status = {}
    for row_idx in range(0, open_sheet.nrows):
        for col_idx in range(0, len(PURCHASE_ORDER_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if row_idx == 0:
                if col_idx == 0 and cell_data != 'PO Name':
                    return 'Invalid File'
                break
            if col_idx == 2:
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                if cell_data:
                    supplier = SupplierMaster.objects.filter(user=user, id=cell_data.upper())
                    if not supplier:
                        index_status.setdefault(row_idx, set()).add("Supplier ID doesn't exist")
                else:
                    index_status.setdefault(row_idx, set()).add('Missing Supplier ID')
            elif col_idx == 1:
                if not (isinstance(cell_data, float) or '-' in str(cell_data)):
                    index_status.setdefault(row_idx, set()).add('Check the date format')
            elif col_idx == 3:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing WMS Code')
                else:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    sku_master = SKUMaster.objects.filter(wms_code=cell_data.upper())
                    if not sku_master:
                        index_status.setdefault(row_idx, set()).add("WMS Code doesn't exist")
            elif col_idx == 4:
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Quantity should be integer')
                else:
                    index_status.setdefault(row_idx, set()).add('Missing Quantity')
            elif col_idx == 5:
                if cell_data !='':
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Price should be a number')
                else:
                    index_status.setdefault(row_idx, set()).add('Missing Price')

    if not index_status:
        return 'Success'
    wb = Workbook()
    ws = wb.add_sheet('Purchase Order')
    header_style = easyxf('font: bold on')
    headers = copy.copy(PURCHASE_ORDER_HEADERS)
    headers.append('Status')
    for count, header in enumerate(headers):
        ws.write(0, count, header, header_style)

    for row_idx in range(1, open_sheet.nrows):
        for col_idx in range(0, len(PURCHASE_ORDER_HEADERS)):
            ws.write(row_idx, col_idx, open_sheet.cell(row_idx, col_idx).value)
        else:
            index_data = index_status.get(row_idx, '')
            if index_data:
                index_data = ', '.join(index_data)
            ws.write(row_idx, col_idx + 1, index_data)

    wb.save('%s.purchase_order_form.xls' % user)
    return '%s.purchase_order_form.xls' % user

def purchase_order_excel_upload(request, open_sheet, user, demo_data=False):
    order_ids = {}
    data_req = {}
    mail_result_data = ""
    for row_idx in range(1, open_sheet.nrows):
        order_data = copy.deepcopy(PO_SUGGESTIONS_DATA)
        data = copy.deepcopy(PO_DATA)
        for col_idx in range(0, len(PURCHASE_ORDER_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if col_idx == 2:
                if type(cell_data) == float:
                    cell_data = int(cell_data)
                else:
                    cell_data = cell_data.upper()
                if demo_data:
                    user_profile = UserProfile.objects.filter(user_id=user.id)
                    if user_profile:
                        cell_data = user_profile[0].prefix + '_' + cell_data
                supplier = SupplierMaster.objects.filter(user=user.id, id=cell_data)
                if supplier:
                    order_data['supplier_id'] = cell_data
            elif col_idx == 3:
                if type(cell_data) == float:
                    cell_data = int(cell_data)
                else:
                    cell_data = cell_data.upper()
                sku_master = SKUMaster.objects.filter(wms_code=cell_data, user=user.id)
                if sku_master:
                    order_data['sku_id'] = sku_master[0].id
            elif col_idx == 4:
                order_data['order_quantity'] = int(cell_data)
            elif col_idx == 5:
                order_data['price'] = cell_data
            elif col_idx == 1:
                if cell_data and '-' in str(cell_data):
                    order_date = cell_data.split('-')
                    data['po_date'] = datetime.date(int(order_date[2]), int(order_date[0]), int(order_date[1]))
                elif isinstance(cell_data, float):
                    data['po_date'] = xldate_as_tuple(cell_data, 0)
            elif col_idx == 0:
                order_data['po_name'] = cell_data
            elif col_idx == 6:
                data['ship_to'] = cell_data

        if (order_data['po_name'], order_data['supplier_id'], data['po_date']) not in order_ids.keys():
            po_data = PurchaseOrder.objects.filter(open_po__sku__user=user.id).order_by('-order_id')
            if not po_data:
                po_id = 0
            else:
                po_id = po_data[0].order_id
            order_ids[order_data['po_name'], order_data['supplier_id'], data['po_date']] = po_id
        else:
            po_id = order_ids[order_data['po_name'], order_data['supplier_id'], data['po_date']]
        ids_dict = {}
        po_data = []
        total = 0
        order_data['status'] = 0
        data1 = OpenPO(**order_data)
        data1.save()
        purchase_order = OpenPO.objects.get(id=data1.id, sku__user=user.id)
        sup_id = purchase_order.id
        supplier = purchase_order.supplier_id
        if supplier not in ids_dict:
            po_id = po_id + 1
            ids_dict[supplier] = po_id
        data['open_po_id'] = sup_id
        data['order_id'] = ids_dict[supplier]
        user_profile = UserProfile.objects.filter(user_id=user.id)
        if user_profile:
            data['prefix'] = user_profile[0].prefix
        order = PurchaseOrder(**data)
        order.save()
        order.po_date = data['po_date']
        order.save()
        mail_result_data = purchase_order_dict(data1, data_req, purchase_order, user, order)
    if mail_result_data:
        mail_status = purchase_upload_mail(request, mail_result_data)
    return 'success'

def purchase_order_dict(data, data_req, purch, user, order):
    if data.supplier.name in data_req.keys():
        data_req[data.supplier.name].append({'sku_code': data.sku.sku_code, 'price': data.price, 'quantity': data.order_quantity, 
                                             'purch': purch, 'user': user, 'purchase_order': order})
    else:
        data_req[data.supplier.name] = [{'sku_code': data.sku.sku_code, 'price': data.price, 'quantity': data.order_quantity, 
                                         'purch': purch, 'user': user, 'purchase_order': order}]
    return data_req

def purchase_upload_mail(request, data_to_send):
    from django.template import loader, Context
    from inbound import write_and_mail_pdf
    for key, value in data_to_send.iteritems():
        status = ''
        customization = ''
        supplier_code = ''
        supplier_mapping = SKUSupplier.objects.filter(sku_id = value[0]['purch'].sku_id, supplier_id = value[0]['purch'].supplier_id,
                                                      sku__user = value[0]['user'].id)
        if supplier_mapping:
            supplier_code = supplier_mapping[0].supplier_code

        supplier = value[0]['purch'].supplier
        wms_code = value[0]['purch'].sku.wms_code
        telephone = supplier.phone_number
        name = supplier.name
        order_id =  value[0]['purchase_order'].order_id
        supplier_email = supplier.email_id
        order_date = get_local_date(request.user, value[0]['purchase_order'].creation_date)
        address = '\n'.join(supplier.address.split(','))
        vendor_name = ''
        vendor_address = ''
        vendor_telephone = ''

        if value[0]['purch'].order_type == 'VR':
            vendor_address = value[0]['purch'].vendor.address
            vendor_address = '\n'.join(vendor_address.split(','))
            vendor_name = value[0]['purch'].vendor.name
            vendor_telephone = value[0]['purch'].vendor.phone_number

        po_reference = '%s%s_%s' % (value[0]['purchase_order'].prefix,
                                    str(value[0]['purchase_order'].creation_date).split(' ')[0].replace('-', ''), order_id)

        table_headers = ('WMS Code', 'Supplier Code', 'Description', 'Quantity', 'Unit Price', 'Amount')
        po_data = []

        amount = 0
        total = 0
        total_qty = 0
        for one_stat in value:
            amount = (one_stat['quantity']) * (one_stat['price'])
            total += amount
            total_qty += one_stat['quantity']
            po_data.append((one_stat['sku_code'], '', '', one_stat['quantity'], one_stat['price'], one_stat['quantity']*one_stat['price'] ))

        profile = UserProfile.objects.get(user=request.user.id)
        t = loader.get_template('templates/toggle/po_download.html')
        data_dictionary = { 'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id,
                            'telephone': str(telephone), 'name': name, 'order_date': order_date, 'total': total, 'po_reference': po_reference,
                            'user_name': request.user.username, 'total_qty': total_qty, 'company_name': profile.company_name,
                            'location': profile.location, 'w_address': profile.address, 'vendor_name': vendor_name,
                            'vendor_address': vendor_address, 'vendor_telephone': vendor_telephone, 'customization': customization }
        c = Context(data_dictionary)
        rendered = t.render(c)
        write_and_mail_pdf(po_reference, rendered, request, supplier_email, telephone, po_data, str(order_date).split(' ')[0])

@csrf_exempt
@login_required
@get_admin_user
def purchase_order_upload(request, user=''):

    fname = request.FILES['files']
    if fname.name.split('.')[-1] == 'xls' or fname.name.split('.')[-1] == 'xlsx':
        try:
            open_book = open_workbook(filename=None, file_contents=fname.read())
            open_sheet = open_book.sheet_by_index(0)
        except:
            return HttpResponse('Invalid File')

        status = validate_purchase_order(open_sheet, str(user.id))
        if status != 'Success':
            return HttpResponse(status)

        purchase_order_excel_upload(request, open_sheet, user)

    return HttpResponse('Success')

@csrf_exempt
def validate_move_inventory_form(open_sheet, user):
    mapping_dict = {}
    index_status = {}
    location = {}
    for row_idx in range(0, open_sheet.nrows):
        for col_idx in range(0, len(MOVE_INVENTORY_UPLOAD_FIELDS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if row_idx == 0:
                if col_idx == 0 and cell_data != 'WMS Code':
                    return 'Invalid File'
                break
            if col_idx == 0:
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(cell_data)
                #sku_master = SKUMaster.objects.filter(wms_code=cell_data, user=user)
                _user = User.objects.get(id = user)
                _sku_master = check_and_return_mapping_id(cell_data, "", _user, False)
                sku_master = SKUMaster.objects.filter(id = _sku_master)
                if not sku_master:
                    index_status.setdefault(row_idx, set()).add('Invalid WMS Code')
            elif col_idx == 1:
                if cell_data:
                    location_master = LocationMaster.objects.filter(zone__user=user, location=cell_data)
                    if not location_master:
                        index_status.setdefault(row_idx, set()).add('Invalid Source Location')
                    if location_master and sku_master:
                        source_stock = StockDetail.objects.filter(sku__user=user, location__location=cell_data, sku_id=sku_master[0].id)
                        if not source_stock:
                            index_status.setdefault(row_idx, set()).add('location not have the stock of wms code')
                else:
                    index_status.setdefault(row_idx, set()).add('Source Location should not be empty')
            elif col_idx == 2:
                if cell_data:
                    dest_location = LocationMaster.objects.filter(zone__user=user, location=cell_data)
                    if not dest_location:
                        index_status.setdefault(row_idx, set()).add('Invalid Destination Location')
                else:
                    index_status.setdefault(row_idx, set()).add('Destination Location should not be empty')
            elif col_idx == 3:
                if cell_data and (not isinstance(cell_data, (int, float)) or int(cell_data) < 0):
                    index_status.setdefault(row_idx, set()).add('Invalid Quantity')

    if not index_status:
        return 'Success'
    f_name = '%s.move_inventory_form.xls' % user
    write_error_file(f_name, index_status, open_sheet, MOVE_INVENTORY_UPLOAD_FIELDS, 'Move Inventory')
    return f_name

@csrf_exempt
@login_required
@get_admin_user
def move_inventory_upload(request, user=''):
    fname = request.FILES['files']
    try:
        open_book = open_workbook(filename=None, file_contents=fname.read())
        open_sheet = open_book.sheet_by_index(0)
    except:
        return HttpResponse('Invalid File')

    status = validate_move_inventory_form(open_sheet, str(user.id))
    if status != 'Success':
        return HttpResponse(status)
    cycle_count = CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
    if not cycle_count:
        cycle_id = 1
    else:
        cycle_id = cycle_count[0].cycle + 1
    mod_locations = []
    for row_idx in range(1, open_sheet.nrows):
        location_data = ''
        for col_idx in range(0, len(MOVE_INVENTORY_UPLOAD_FIELDS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if col_idx == 0 and cell_data:
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(cell_data)
                wms_code = cell_data
            elif col_idx == 1:
                source_loc = cell_data
            elif col_idx == 2:
                dest_loc = cell_data
            elif col_idx == 3:
               quantity = int(cell_data)
        move_stock_location(cycle_id, wms_code, source_loc, dest_loc, quantity, user)
        mod_locations.append(source_loc)
        mod_locations.append(dest_loc)
    update_filled_capacity(list(set(mod_locations)), user.id)
    return HttpResponse('Success')

def get_marketplace_headers(row_idx, open_sheet):
    market_excel = {}
    mapping = OrderedDict()
    for col_idx in range(1, open_sheet.ncols):
        cell_data = open_sheet.cell(row_idx, col_idx).value
        if ' SKU' in cell_data:
            market_excel[cell_data] = col_idx
        if ' Description' in cell_data:
            sub_str = ' '.join(cell_data.split(' ')[:-1])
            for s in filter (lambda x: sub_str in x, market_excel.keys()):
                mapping[market_excel[s]] = col_idx
    marketplace_excel = {'marketplace_code': mapping.keys(), 'description': mapping.values()}
    return marketplace_excel

@csrf_exempt
@login_required
@get_admin_user
def marketplace_sku_upload(request, user=''):
    fname = request.FILES['files']
    if (fname.name).split('.')[-1] == 'xls' or (fname.name).split('.')[-1] == 'xlsx':
        try:
            open_book = open_workbook(filename=None, file_contents=fname.read())
            open_sheet = open_book.sheet_by_index(0)
        except:
            return HttpResponse('Invalid File')

        market_excel = {}
        for row_idx in range(0, open_sheet.nrows):
            save_records = []
            print 'Record Processing Started: %s' % str(datetime.datetime.now())
            if row_idx == 0:
                marketplace_excel = get_marketplace_headers(row_idx, open_sheet)
                continue

            sku_code = ''
            sku_desc = ''
            wms_code_data = open_sheet.cell(row_idx, 0).value
            if not wms_code_data:
                continue

            if isinstance(wms_code_data, float):
                sku_code = str(int(wms_code_data))
            else:
                sku_code = wms_code_data.upper()

            sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
            if sku_master:
                sku_master = sku_master[0]

            for marketplace_code, marketplace_desc in zip(marketplace_excel['marketplace_code'], marketplace_excel['description']):
                marketplace_name = open_sheet.cell(0, marketplace_code).value.split(' ')[0]
                market_sku = open_sheet.cell(row_idx, marketplace_code).value
                market_desc = open_sheet.cell(row_idx, marketplace_desc).value

                if isinstance(market_sku, (int, float)):
                    market_sku = str(int(market_sku))
                else:
                    market_sku = market_sku.upper()

                if not market_sku:
                    continue

                sku_codes = market_sku.split('###')
                sku_descs = market_desc.split('###')
                for key, value in zip(sku_codes, sku_descs):
                    market_sku_mapping = MarketplaceMapping.objects.filter(sku_type=marketplace_name, marketplace_code=key, sku__user=user.id)
                    if market_sku_mapping:
                        continue

                    if not sku_desc:
                        sku_desc = value

                    if not sku_master:
                        sku_data = {'sku_code': sku_code, 'wms_code': sku_code, 'sku_desc': sku_desc, 'status': 1,
                                    'creation_date': datetime.datetime.now(),
                                    'user': user.id, 'threshold_quantity': 0, 'online_percentage': 0}
                        sku_master = SKUMaster(**sku_data)
                        sku_master.save()

                    if not sku_master.sku_desc and sku_desc:
                        sku_master.sku_desc = sku_desc
                        sku_master.save()

                    market_mapping = copy.deepcopy(MARKETPLACE_SKU_FIELDS)
                    market_mapping['sku_type'] = marketplace_name
                    market_mapping['marketplace_code'] = key
                    market_mapping['description'] = value
                    market_mapping['sku_id'] = sku_master.id
                    market_data = MarketplaceMapping(**market_mapping)
                    save_records.append(market_data)
                    #market_data.save()
            if save_records:
                MarketplaceMapping.objects.bulk_create(save_records)

            print 'Record processing ended: %s' % str(datetime.datetime.now())
        return HttpResponse('Success')
    else:
        return HttpResponse('Invalid File Format')

def validate_bom_form(open_sheet, user, bom_excel):
    index_status = {}
    for row_idx in range(0, open_sheet.nrows):
        if row_idx == 0:
            cell_data = open_sheet.cell(row_idx, 0).value
            if cell_data != 'Product SKU Code':
                return 'Invalid File'
            continue
        for key, value in bom_excel.iteritems():
            if key == 'product_sku':
                product_sku = open_sheet.cell(row_idx, bom_excel[key]).value
                if isinstance(product_sku, (int, float)):
                    product_sku = int(product_sku)
                sku_code = SKUMaster.objects.filter(sku_code=product_sku, user=user)
                if not sku_code:
                    index_status.setdefault(row_idx, set()).add('Invalid SKU Code %s' % product_sku)
            if key == 'material_sku':
                material_sku = open_sheet.cell(row_idx, bom_excel[key]).value
                if isinstance(material_sku, (int, float)):
                    material_sku = int(material_sku)
                sku_code = SKUMaster.objects.filter(sku_code=material_sku, user=user)
                if not sku_code:
                    index_status.setdefault(row_idx, set()).add('Invalid SKU Code %s'% material_sku)
            elif key == 'material_quantity':
                cell_data = open_sheet.cell(row_idx, bom_excel[key]).value
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Quantity Should be in integer or float')
                #else:
                #    index_status.setdefault(row_idx, set()).add('Quantity Should not be empty')
            elif key == 'wastage_percent':
                cell_data = open_sheet.cell(row_idx, bom_excel[key]).value
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Wastage Percent Should be in integer or float')
                    elif not float(cell_data) in range(0, 100):
                        index_status.setdefault(row_idx, set()).add('Wastage Percent Should be in between 0 and 100')

        if product_sku == material_sku:
            index_status.setdefault(row_idx, set()).add('Product and Material SKU Code should not be same')
        #bom = BOMMaster.objects.filter(product_sku__sku_code=product_sku, material_sku__sku_code=material_sku, product_sku__user=user)
        #if bom:
        #    index_status.setdefault(row_idx, set()).add('Product and Material Sku codes combination already exists')
    if not index_status:
        return 'Success'

    f_name = '%s.bom_form.xls' % user
    write_error_file(f_name, index_status, open_sheet, BOM_UPLOAD_EXCEL_HEADERS, 'BOM')
    return f_name

@csrf_exempt
@login_required
@get_admin_user
def bom_upload(request, user=''):
    from masters import *
    fname = request.FILES['files']
    bom_excel = {'product_sku': 0, 'material_sku': 1, 'material_quantity': 2, 'wastage_percent': 3, 'unit_of_measurement': 4}
    try:
        open_book = open_workbook(filename=None, file_contents=fname.read())
        open_sheet = open_book.sheet_by_index(0)
    except:
        return HttpResponse("Invalid File")
    status = validate_bom_form(open_sheet, str(user.id), bom_excel)

    if status != 'Success':
        return HttpResponse(status)
    for row_idx in range(1, open_sheet.nrows):
        all_data = {}
        product_sku = open_sheet.cell(row_idx, bom_excel['product_sku']).value
        material_sku = open_sheet.cell(row_idx, bom_excel['material_sku']).value
        material_quantity = open_sheet.cell(row_idx, bom_excel['material_quantity']).value
        uom = open_sheet.cell(row_idx, bom_excel['unit_of_measurement']).value
        wastage_percent = open_sheet.cell(row_idx, bom_excel['wastage_percent']).value
        if isinstance(product_sku, (int, float)):
            product_sku = int(product_sku)
        if isinstance(material_sku, (int, float)):
            material_sku = int(material_sku)
        if not material_quantity:
            material_quantity = 0
        data_id = ''
        cond = (material_sku)
        all_data.setdefault(cond, [])
        all_data[cond].append([float(material_quantity), uom, data_id, wastage_percent ])
        insert_bom(all_data, product_sku, user.id)
    return HttpResponse('Success')


def validate_combo_sku_form(open_sheet, user):
    index_status = {}
    header_data = open_sheet.cell(0, 1).value
    if header_data != 'Combo SKU':
        return 'Invalid File'

    for row_idx in range(1, open_sheet.nrows):

        for col_idx in range(0, len(COMBO_SKU_EXCEL_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if not cell_data:
                if col_idx == 0:
                    message = 'SKU Code Missing'
                if col_idx == 1:
                    message = 'Combo SKU Code Missing'
                index_status.setdefault(row_idx, set()).add(message)
                continue
            if isinstance(cell_data, (int, float)):
                cell_data = int(cell_data)
            cell_data = str(cell_data)

            sku_master = MarketplaceMapping.objects.filter(marketplace_code=cell_data, sku__user=user)
            if not sku_master:
                sku_master = SKUMaster.objects.filter(sku_code=cell_data, user=user)
            if not sku_master:
                if col_idx == 0:
                    message = 'Invalid SKU Code'
                else:
                    message = 'Invalid Combo SKU'
                index_status.setdefault(row_idx, set()).add(message)

    if not index_status:
        return 'Success'

    f_name = '%s.combo_sku_form.xls' % user
    write_error_file(f_name, index_status, open_sheet, COMBO_SKU_EXCEL_HEADERS, 'Combo SKU')
    return f_name

@csrf_exempt
@login_required
@get_admin_user
def combo_sku_upload(request, user=''):
    fname = request.FILES['files']
    if (fname.name).split('.')[-1] != 'xls' and (fname.name).split('.')[-1] != 'xlsx':
        return HttpResponse('Invalid File Format')

    try:
        open_book = open_workbook(filename=None, file_contents=fname.read())
        open_sheet = open_book.sheet_by_index(0)
    except:
        return HttpResponse('Invalid File')

    status = validate_combo_sku_form(open_sheet, str(user.id))
    if status != 'Success':
        return HttpResponse(status)

    for row_idx in range(1, open_sheet.nrows):
        for col_idx in range(0, len(COMBO_SKU_EXCEL_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value

            if col_idx in (0, 1):
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(cell_data)
                sku_data = MarketplaceMapping.objects.filter(marketplace_code=cell_data, sku__user=user.id)
                if sku_data:
                    sku_data = sku_data[0].sku
                if not sku_data:
                    sku_data = SKUMaster.objects.filter(sku_code=cell_data, user=user.id)[0]

            if col_idx == 0:
                sku_code = sku_data

            if col_idx == 1:
                combo_data = sku_data

        relation_data = {'relation_type': 'combo', 'member_sku': combo_data, 'parent_sku': sku_code}
        sku_relation = SKURelation.objects.filter(**relation_data)
        if not sku_relation:
            sku_relation = SKURelation(**relation_data)
            sku_relation.save()
        elif sku_relation:
            sku_relation = sku_relation[0]
        sku_relation.parent_sku.relation_type = 'combo'
        sku_relation.parent_sku.save()

    return HttpResponse('Success')

@csrf_exempt
def validate_inventory_adjust_form(open_sheet, user):
    mapping_dict = {}
    index_status = {}
    location = {}
    for row_idx in range(0, open_sheet.nrows):
        for col_idx in range(0, len(ADJUST_INVENTORY_EXCEL_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if row_idx == 0:
                if col_idx == 0 and cell_data != 'WMS Code':
                    return 'Invalid File'
                break
            if col_idx == 0:
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(xcode(cell_data))
                sku_master = SKUMaster.objects.filter(wms_code=cell_data, user=user)
                if not sku_master:
                    index_status.setdefault(row_idx, set()).add('Invalid WMS Code')
            elif col_idx == 1:
                if cell_data:
                    location_master = LocationMaster.objects.filter(zone__user=user, location=cell_data)
                    if not location_master:
                        index_status.setdefault(row_idx, set()).add('Invalid Location')
                else:
                    index_status.setdefault(row_idx, set()).add('Location should not be empty')
            elif col_idx == 2:
                if cell_data and (not isinstance(cell_data, (int, float)) or int(cell_data) < 0):
                    index_status.setdefault(row_idx, set()).add('Invalid Quantity')
                #if cell_data == '':
                #    index_status.setdefault(row_idx, set()).add('Quantity should not be empty')

    if not index_status:
        return 'Success'
    f_name = '%s.inventory_adjust_form.xls' % user
    write_error_file(f_name, index_status, open_sheet, ADJUST_INVENTORY_EXCEL_HEADERS, 'Inventory Adjustment')
    return f_name

@csrf_exempt
@login_required
@get_admin_user
def inventory_adjust_upload(request, user=''):
    fname = request.FILES['files']
    try:
        open_book = open_workbook(filename=None, file_contents=fname.read())
        open_sheet = open_book.sheet_by_index(0)
    except:
        return HttpResponse('Invalid File')

    status = validate_inventory_adjust_form(open_sheet, str(user.id))
    if status != 'Success':
        return HttpResponse(status)
    sku_codes = []
    len1 = len(ADJUST_INVENTORY_EXCEL_HEADERS)
    cycle_count = CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
    if not cycle_count:
        cycle_id = 0
    else:
        cycle_id = cycle_count[0].cycle

    for row_idx in range(1, open_sheet.nrows):
        cycle_id += 1
        #location_data = ''
        for col_idx in range(len1):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if col_idx == 0 and cell_data:
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(xcode(cell_data))
                wms_code = cell_data
                if wms_code not in sku_codes:
                    sku_codes.append(wms_code)
            elif col_idx == 1:
                loc = cell_data
            elif col_idx == 2:
               quantity = int(cell_data)
            elif col_idx == 3:
               reason = cell_data
        adjust_location_stock(cycle_id, wms_code, loc, quantity, reason, user)
    check_and_update_stock(sku_codes, user)
    return HttpResponse('Success')

@csrf_exempt
@get_admin_user
def customer_form(request, user=''):
    customer_file = request.GET['download-customer-file']
    if customer_file:
        return error_file_download(customer_file)

    wb, ws = get_work_sheet('customer', CUSTOMER_HEADERS)
    return xls_to_response(wb, '%s.customer_form.xls' % str(user.id))

@csrf_exempt
def validate_customer_form(request, reader, user, no_of_rows, fname, file_type='xls'):
    index_status = {}
    customer_ids = []
    mapping_dict = get_customer_master_mapping(reader, file_type)
    if not mapping_dict:
        return "Headers not Matching"
    number_fields = {'credit_period': 'Credit Period', 'phone_number': 'Phone Number', 'pincode': 'PIN Code', 'phone': 'Phone Number'}
    for row_idx in range(1, no_of_rows):
        if not mapping_dict:
            break
        customer_master = None
        for key, value in mapping_dict.iteritems():
            cell_data = get_cell_data(row_idx, mapping_dict[key], reader, file_type)

            if key == 'customer_id':
                if cell_data:
                    try:
                        cell_data = int(cell_data)
                    except:
                        index_status.setdefault(row_idx, set()).add('Customer ID Should be in number')
                    if cell_data:
                        cell_data = int(cell_data)
                        customer_master_obj = CustomerMaster.objects.filter(customer_id=cell_data, user=user.id)
                        if customer_master_obj:
                            customer_master = customer_master_obj[0]
                else:
                    index_status.setdefault(row_idx, set()).add('Customer ID is Missing')

            elif key == 'name':
                if not cell_data and not customer_master:
                    index_status.setdefault(row_idx, set()).add('Missing Customer Name')

            elif key in number_fields.keys():
                if cell_data:
                    try:
                        cell_data = float(cell_data)
                    except:
                        index_status.setdefault(row_idx, set()).add('%s Should be in number' % number_fields[key])

            elif key == 'price_type':
                if cell_data:
                    price_types = list(PriceMaster.objects.filter(sku__user=user.id).values_list('price_type', flat=True).distinct())
                    if not cell_data in price_types:
                        index_status.setdefault(row_idx, set()).add('Invalid Selling Price Type')

    if not index_status:
        return 'Success'

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        rewrite_csv_file(f_name, index_status, reader)
        return f_name

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        rewrite_excel_file(f_name, index_status, reader)
        return f_name

def customer_excel_upload(request, reader, user, no_of_rows, fname, file_type):
    mapping_dict = get_customer_master_mapping(reader, file_type)
    number_fields = ['credit_period', 'phone_number', 'pincode', 'phone']
    for row_idx in range(1, no_of_rows):
        if not mapping_dict:
            break
        customer_data = copy.deepcopy(CUSTOMER_DATA)
        customer_master = None

        for key, value in mapping_dict.iteritems():
            cell_data = get_cell_data(row_idx, mapping_dict[key], reader, file_type)
            #cell_data = open_sheet.cell(row_idx, mapping_dict[key]).value
            if key == 'customer_id':
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                customer_data['customer_id'] = cell_data
                customer_master = CustomerMaster.objects.filter(customer_id=cell_data, user=user.id)
                if customer_master:
                    customer_master = customer_master[0]
            elif key == 'name':
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                cell_data = str(re.sub(r'[^\x00-\x7F]+','', cell_data))
                customer_data['name']  = cell_data
                if customer_master:
                    customer_master.name = customer_data['name']
            elif key in number_fields:
                try:
                    cell_data = int(cell_data)
                except:
                    print "error"
                if isinstance(cell_data, (int, float)):
                    if customer_master:
                        if key == 'phone':
                            setattr(customer_master, 'phone_number', cell_data)
                        else:
                            setattr(customer_master, key, cell_data)
                    else:
                        if key == 'phone':
                            customer_data['phone_number'] = cell_data
                        else:
                            customer_data[key] = cell_data
            else:
                if key == 'tin':
                    if customer_master:
                        setattr(customer_master, 'tin_number', cell_data)
                    else:
                        customer_data['tin_number'] = cell_data
                else:
                    customer_data[key] = cell_data
                if cell_data and customer_master:
                   setattr(customer_master, key, cell_data)

        if customer_master:
            customer_master.save()
        else:
            customer_data['user'] = user.id
            customer = CustomerMaster(**customer_data)
            customer.save()

    return 'success'

@csrf_exempt
@login_required
@get_admin_user
def customer_upload(request, user=''):
    fname = request.FILES['files']
    try:
        if (fname.name).split('.')[-1] == 'csv':
            reader = [[val.replace('\n', '').replace('\t', '').replace('\r','') for val in row] for row in csv.reader(fname.read().splitlines())]
            no_of_rows = len(reader)
            file_type = 'csv'

        elif (fname.name).split('.')[-1] == 'xls' or (fname.name).split('.')[-1] == 'xlsx':
            try:
                data = fname.read()
                if '<table' in data:
                    open_book, open_sheet = html_excel_data(data, fname)
                else:
                    open_book = open_workbook(filename=None, file_contents=data)
                    open_sheet = open_book.sheet_by_index(0)
            except:
                return HttpResponse("Invalid File")
            reader = open_sheet
            no_of_rows = reader.nrows
            file_type = 'xls'

        status = validate_customer_form(request, reader, user, no_of_rows, fname, file_type)
        if status != 'Success':
            return HttpResponse(status)

        customer_excel_upload(request, reader, user, no_of_rows, fname, file_type)
    except Exception as e:
        import traceback
        log.info(traceback.format_exc())
        log.info('Customer Upload failed for %s and params are %s and error statement is %s' % (str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Customer Upload Failed")

    return HttpResponse('Success')

@csrf_exempt
@login_required
@get_admin_user
def sales_returns_upload(request, user=''):
    fname = request.FILES['files']
    if (fname.name).split('.')[-1] == 'csv':
        reader = [[val.replace('\n', '').replace('\t', '').replace('\r','') for val in row] for row in csv.reader(fname.read().splitlines())]
        no_of_rows = len(reader)
        file_type = 'csv'
    elif (fname.name).split('.')[-1] == 'xls' or (fname.name).split('.')[-1] == 'xlsx':
        try:
            data = fname.read()
            if '<table' in data:
                open_book, open_sheet = html_excel_data(data, fname)
            else:
                open_book = open_workbook(filename=None, file_contents=data)
                open_sheet = open_book.sheet_by_index(0)
        except:
            return HttpResponse("Invalid File")
        reader = open_sheet
        no_of_rows = reader.nrows
        file_type = 'xls'

    status = validate_sales_return_form(request, reader, user, no_of_rows, fname, file_type=file_type)
    if status != 'Success':
        return HttpResponse(status)

    upload_status = sales_returns_csv_xls_upload(request, reader, user, no_of_rows, fname, file_type=file_type)
    return HttpResponse('Success')

@csrf_exempt
def validate_sales_return_form(request, reader, user, no_of_rows, fname, file_type='xls'):
    sku_data = []
    wms_data = []
    index_status = {}
    order_mapping = get_sales_returns_mapping(reader, file_type)
    if not order_mapping:
        return 'Invalid File'
    for row_idx in range(1, no_of_rows):
        for key, value in order_mapping.iteritems():
            if isinstance(order_mapping[key], list):
                cell_data = ''
                for item in order_mapping[key]:
                    cell_dat = get_cell_data(row_idx, item, reader, file_type)
                    if isinstance(cell_dat, float):
                        cell_dat = str(int(cell_dat))
                    cell_data += cell_dat
            else:
                cell_data = get_cell_data(row_idx, order_mapping[key], reader, file_type)

            if key == 'sku_id':
                if isinstance(cell_data, float):
                    cell_data = str(int(cell_data))
                sku_code = cell_data
                if cell_data:
                    sku_id = check_and_return_mapping_id(sku_code, '', user)
                    if not sku_id:
                        index_status.setdefault(row_idx, set()).add("WMS Code doesn't exists")
                else:
                    index_status.setdefault(row_idx, set()).add('WMS Code missing')
            elif key == 'order_id':
                if cell_data and sku_code:
                    if isinstance(cell_data, float):
                        cell_data = str(int(cell_data))
                    order_id = ''.join(re.findall('\d+', cell_data))
                    order_filter = {'order_id': order_id}
                    order_code = ''.join(re.findall('\D+', cell_data))
                    if order_code:
                        order_filter['order_code'] = order_code
                    order_detail = OrderDetail.objects.filter(Q(original_order_id=cell_data) | Q(**order_filter),
                                                              sku_id__sku_code=sku_code, user=user.id)
                    if not order_detail:
                        index_status.setdefault(row_idx, set()).add("Order ID doesn't exists")
                    #elif int(order_detail[0].status) == 4:
                    #    index_status.setdefault(row_idx, set()).add("Order Processed already")

            elif key == 'quantity':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Return quantity cannot be blank')
                if cell_data and not isinstance(cell_data, (int, float)):
                    if not cell_data.isdigit():
                        index_status.setdefault(row_idx, set()).add('Invalid Return Quantity')

                if cell_data and isinstance(cell_data, (int, float)):
                    if int(cell_data) < 0:
                        index_status.setdefault(row_idx, set()).add('Return Quantity should not be in negative')

            elif key == 'damaged_quantity':
                if not isinstance(cell_data, (int, float)) and cell_data:
                    if not cell_data.isdigit():
                        index_status.setdefault(row_idx, set()).add('Invalid Damaged Quantity')

                if cell_data and isinstance(cell_data, (int, float)):
                    if int(cell_data) < 0:
                        index_status.setdefault(row_idx, set()).add('Damaged Quantity should not be in negative')

            elif key == 'return_id':
                sku_cod = get_cell_data(row_idx, order_mapping['sku_id'], reader, file_type)
                return_cod = get_cell_data(row_idx, order_mapping['return_id'], reader, file_type)
                if sku_cod and return_cod:
                    return_obj = OrderReturns.objects.filter(return_id = return_cod, sku__sku_code = sku_cod, sku__user = user.id)
                    if return_obj:
                        index_status.setdefault(row_idx, set()).add('Return Order is already exist')
            elif key == 'seller_order_id':
                sor_id = get_cell_data(row_idx, order_mapping[key], reader, file_type)
                sku_code = get_cell_data(row_idx, order_mapping['sku_id'], reader, file_type)
                order_id = get_cell_data(row_idx, order_mapping['order_id'], reader, file_type)
                if isinstance(sor_id, float):
                    sor_id = str(int(sor_id))
                if isinstance(order_id, float):
                    order_id = str(int(order_id))
                if isinstance(sku_code, float):
                    sku_code = str(int(sku_code))
                if sor_id:
                    seller_order = SellerOrder.objects.filter(sor_id=sor_id, order__order_id=order_id,
                                                              order__sku__sku_code=sku_code, order__user=user.id)
                    if not seller_order:
                        index_status.setdefault(row_idx, set()).add('Invalid Sor ID')

    if not index_status:
        return 'Success'

    if index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        rewrite_excel_file(f_name, index_status, reader)
        return f_name
    elif index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        rewrite_csv_file(f_name, index_status, reader)
        return f_name


def sales_returns_csv_xls_upload(request, reader, user, no_of_rows, fname, file_type='xls'):

    from inbound import save_return_locations
    index_status = {}
    order_mapping = get_sales_returns_mapping(reader, file_type)
    count = 1

    for row_idx in range(1, no_of_rows):
        all_data = []
        order_data = copy.deepcopy(UPLOAD_SALES_ORDER_DATA)
        if not order_mapping:
            break
        for key, value in order_mapping.iteritems():
            if key == 'sku_id':
                sku_code= ""
                if isinstance(value, list):
                    for item in value:
                        if isinstance(get_cell_data(row_idx, item, reader, file_type), float):
                            content = int(get_cell_data(row_idx, item, reader, file_type))
                        sku_code = "%s%s" %(sku_code, get_cell_data(row_idx, item, reader, file_type))
                else:
                    sku_code = get_cell_data(row_idx, order_mapping[key], reader, file_type)
                    if isinstance(sku_code, float):
                        sku_code = str(int(sku_code))
                sku_id = check_and_return_mapping_id(sku_code, '', user)
                order_data['sku_id'] = sku_id
            elif key == 'order_id':
                cell_data = get_cell_data(row_idx, order_mapping[key], reader, file_type)
                if cell_data and sku_code:
                    if isinstance(cell_data, float):
                        cell_data = str(int(cell_data))
                    order_id = ''.join(re.findall('\d+', cell_data))
                    order_filter = {'order_id': order_id}
                    order_code = ''.join(re.findall('\D+', cell_data))
                    if order_code:
                        order_filter['order_code'] = order_code
                    order_detail = OrderDetail.objects.filter(Q(original_order_id=cell_data) | Q(**order_filter),
                                                              sku_id__sku_code=sku_code, user=user.id)
                    if order_detail:
                        order_data[key] = order_detail[0].id
                        order_detail[0].status = 4
                        order_detail[0].save()
            elif key == 'quantity':
                order_data[key] = int(get_cell_data(row_idx, order_mapping[key], reader, file_type))
                if not order_data[key]:
                    order_data[key] = 0
            elif key == 'damaged_quantity':
                order_data[key] = get_cell_data(row_idx, order_mapping[key], reader, file_type)
                if not order_data[key]:
                    order_data[key] = 0
            elif key == 'return_date':
                cell_data = get_cell_data(row_idx, order_mapping[key], reader, file_type)
                if cell_data:
                    if isinstance(cell_data, str):
                        try:
                            order_data[key] = datetime.datetime.strptime(cell_data, "%d-%m-%Y %H:%M")
                        except:
                            order_data[key] = datetime.datetime.now()
                    else:
                        order_data[key] = xldate_as_tuple(cell_data, 0)

            elif key == 'marketplace':
                order_data[key] = value
            elif key == 'channel':
                order_data["marketplace"] = get_cell_data(row_idx, order_mapping[key], reader, file_type)
            elif key == 'seller_order_id':
                sor_id = get_cell_data(row_idx, order_mapping[key], reader, file_type)
                if isinstance(sor_id, float):
                    sor_id = str(int(sor_id))
                if sor_id:
                    seller_order = SellerOrder.objects.filter(sor_id=sor_id, order_id=order_data['order_id'],
                                                              order__sku__sku_code=sku_code, order__user=user.id)
                    if seller_order:
                        order_data[key] = seller_order[0].id
            else:
                cell_data = get_cell_data(row_idx, order_mapping[key], reader, file_type)
                if cell_data:
                    order_data[key] = cell_data

            if "quantity" not in order_mapping.keys():
                order_data['quantity'] = 1

        if not order_data['return_date']:
            order_data['return_date'] = datetime.datetime.now()

        if order_data.get('return_type', '') == 'DAMAGED_MISSING':
            order_data['damaged_quantity'] = order_data['quantity']
        if (order_data['quantity'] or order_data['damaged_quantity']) and sku_id:
            #if order_data.get('seller_order_id', '') and 'order_id' in order_data.keys():
            #    del order_data['order_id']
            returns = OrderReturns(**order_data)
            returns.save()

            if not returns.return_id:
                returns.return_id = 'MN%s' % returns.id
            returns.save()

            if not order_data.get('seller_order_id', ''):
                save_return_locations([returns], all_data, order_data['damaged_quantity'], request, user)
    return 'Success'

def get_sales_returns_mapping(reader, file_type):

    order_mapping = {}
    if get_cell_data(0, 0, reader, file_type) == 'Return ID':
        order_mapping = copy.deepcopy(GENERIC_RETURN_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'GatePass No':
        order_mapping = copy.deepcopy(MYNTRA_RETURN_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Sale Order Item Code':
        order_mapping = copy.deepcopy(UNIWEAR_RETURN_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'SOR ID' and get_cell_data(0, 1, reader, file_type) == 'UOR ID':
        order_mapping = copy.deepcopy(SHOTANG_RETURN_EXCEL)
    return order_mapping


def sales_return_order(data,user):

    return_details = {'return_id': '', 'return_date': datetime.datetime.now(), 'quantity': data['quantity'],
                          'sku_id': sku_id, 'status': 1}

    returns = OrderReturns(**return_details)
    returns.save()

    if not returns.return_id:
        returns.return_id = 'MN%s' % returns.id
    returns.save()
    return returns.id

def pricing_excel_upload(request, reader, user, no_of_rows, fname, file_type='xls'):

    price_file_mapping = copy.deepcopy(PRICE_DEF_EXCEL)
    for row_idx in range(1, no_of_rows):
        if not price_file_mapping:
            continue

        data_dict = copy.deepcopy(PRICE_MASTER_DATA)
        price_master_obj = None
        for key, value in price_file_mapping.iteritems():
            cell_data = get_cell_data(row_idx, price_file_mapping[key], reader, file_type)

            if key == 'sku_id':
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(xcode(cell_data))

                wms_code = cell_data
                if wms_code:
                    sku_data = SKUMaster.objects.filter(wms_code = wms_code,user=user.id)
                    data_dict[key] = sku_data[0].id
                    if price_master_obj:
                        price_master_obj = price_master_obj[0]
            elif key == 'price_type':
                data_dict[key] = cell_data
                if data_dict['sku_id'] and cell_data:
                    price_instance = PriceMaster.objects.filter(sku_id=data_dict['sku_id'], sku__user=user.id, price_type=cell_data)
                    if price_instance:
                        price_master_obj = price_instance[0]
                data_dict[key] = cell_data

            elif key in ['price', 'discount']:
                if not cell_data:
                    cell_data = 0
                if price_master_obj and cell_data:
                    setattr(price_master_obj, key, cell_data)
                data_dict[key] = cell_data

            elif cell_data:
                data_dict[key] = cell_data
                if price_master_obj:
                    setattr(price_master_obj, key, cell_data)
                data_dict[key] = cell_data
        if price_master_obj:
            price_master_obj.save()

        if not price_master_obj:
            price_master = PriceMaster(**data_dict)
            price_master.save()

    return 'success'


@csrf_exempt
def validate_pricing_form(request, reader, user, no_of_rows, fname, file_type='xls'):
    sku_data = []
    wms_data = []
    index_status = {}

    price_file_mapping = copy.deepcopy(PRICE_DEF_EXCEL)
    if not price_file_mapping:
        return 'Invalid File'
    for row_idx in range(1, no_of_rows):
        for key, value in price_file_mapping.iteritems():
            cell_data = get_cell_data(row_idx, price_file_mapping[key], reader, file_type)

            if key == 'sku_id':
                if cell_data:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    data = SKUMaster.objects.filter(user=user.id, wms_code=cell_data)
                    if not data:
                        index_status.setdefault(row_idx, set()).add('Invalid SKU Code')
                else:
                    index_status.setdefault(row_idx, set()).add('SKU Code missing')
            elif key == 'price_type':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add("Selling Price Type Missing")

            elif key == 'price':
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Invalid Price')
            elif key == 'discount':
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Invalid Discount')

    if not index_status:
        return 'Success'

    if index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        rewrite_excel_file(f_name, index_status, reader)
        return f_name
    elif index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        rewrite_csv_file(f_name, index_status, reader)
        return f_name


@csrf_exempt
@login_required
@get_admin_user
def pricing_master_upload(request, user=''):
    fname = request.FILES['files']
    if fname.name.split('.')[-1] != 'xls' and fname.name.split('.')[-1] != 'xlsx':
        return HttpResponse('Invalid File Format')

    try:
        open_book = open_workbook(filename=None, file_contents=fname.read())
        open_sheet = open_book.sheet_by_index(0)
    except:
        return HttpResponse('Invalid File')

    file_type = 'xls'
    reader = open_sheet
    no_of_rows = reader.nrows

    status = validate_pricing_form(request, reader, user, no_of_rows, fname, file_type=file_type)
    if status != 'Success':
        return HttpResponse(status)

    pricing_excel_upload(request, reader, user, no_of_rows, fname, file_type=file_type)

    return HttpResponse('Success')

