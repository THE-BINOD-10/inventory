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
from miebach_admin.choices import *
from common import *
from masters import create_network_supplier
from miebach_utils import *
from django.core import serializers
import csv
from sync_sku import *
from outbound import get_syncedusers_mapped_sku

log = init_logger('logs/uploads.log')


@csrf_exempt
def error_file_download(error_file):
    with open(error_file, 'r') as excel:
        data = excel.read()
    response = HttpResponse(data, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=%s' % smart_str(
        error_file.replace('static/temp_files/', ''))
    return response


def get_cell_data(row_idx, col_idx, reader='', file_type='xls'):
    ''' Reads Excel cell Data '''
    try:
        if file_type == 'csv':
            cell_data = reader[row_idx][col_idx]
        else:
            cell_data = reader.cell(row_idx, col_idx).value
        if not isinstance(cell_data, (int, float)):
            cell_data = str(xcode(cell_data))
            cell_data = str(re.sub(r'[^\x00-\x7F]+', ' ', cell_data))
    except:
        cell_data = ''
    return cell_data


def check_return_excel(fname):
    ''' Check and Return Excel data'''
    status, reader, no_of_rows, no_of_cols, file_type = '', '', '', '', ''
    if (fname.name).split('.')[-1] == 'csv':
        reader = [[val.replace('\n', '').replace('\t', '').replace('\r', '') for val in row] for row in
                  csv.reader(fname.read().splitlines())]
        no_of_rows = len(reader)
        file_type = 'csv'
        no_of_cols = 0
        if reader:
            no_of_cols = len(reader[0])
    elif (fname.name).split('.')[-1] == 'xls' or (fname.name).split('.')[-1] == 'xlsx':
        try:
            data = fname.read()
            if '<table' in data:
                open_book, open_sheet = html_excel_data(data, fname)
            else:
                open_book = open_workbook(filename=None, file_contents=data)
                open_sheet = open_book.sheet_by_index(0)
        except:
            status = 'Invalid File'
        reader = open_sheet
        no_of_rows = reader.nrows
        file_type = 'xls'
        no_of_cols = open_sheet.ncols
    return reader, no_of_rows, no_of_cols, file_type, status


def generate_error_excel(index_status, fname, reader, file_type):
    ''' Generates Error Excel Sheet '''
    f_name = ''
    if file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path

    elif file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
    return f_name


def get_inventory_excel_upload_headers(user):
    excel_headers = copy.deepcopy(INVENTORY_EXCEL_MAPPING)
    pallet_switch = get_misc_value('pallet_switch', user.id)
    userprofile = user.userprofile
    if not pallet_switch == 'true':
        del excel_headers["Pallet Number"]
    if not userprofile.user_type == 'marketplace_user':
        del excel_headers["Seller ID"]
    if not userprofile.industry_type == 'FMCG':
        del excel_headers["Batch Number"]
        del excel_headers["MRP"]
        del excel_headers["Manufactured Date(YYYY-MM-DD)"]
        del excel_headers["Expiry Date(YYYY-MM-DD)"]
    return excel_headers


def get_move_inventory_excel_upload_headers(user):
    excel_headers = copy.deepcopy(MOVE_INVENTORY_EXCEL_MAPPING)
    userprofile = user.userprofile
    if not userprofile.user_type == 'marketplace_user':
        del excel_headers["Seller ID"]
    if not userprofile.industry_type == 'FMCG':
        del excel_headers["Batch Number"]
        del excel_headers["MRP"]
    return excel_headers


def get_sku_substitution_excel_headers(user):
    excel_headers = copy.deepcopy(SKU_SUBSTITUTION_EXCEL_MAPPING)
    userprofile = user.userprofile
    if not userprofile.user_type == 'marketplace_user':
        del excel_headers["Seller ID"]
    if not userprofile.industry_type == 'FMCG':
        del excel_headers["Source Batch Number"]
        del excel_headers["Source MRP"]
        del excel_headers["Destination Batch Number"]
        del excel_headers["Destination MRP"]
    return excel_headers


def get_purchase_order_excel_headers(user):
    excel_headers = copy.deepcopy(PURCHASE_ORDER_UPLOAD_MAPPING)
    userprofile = user.userprofile
    if not userprofile.user_type == 'marketplace_user':
        del excel_headers["Seller ID"]
    return excel_headers


def get_seller_transfer_excel_headers(user):
    excel_headers = copy.deepcopy(SELLER_TRANSFER_MAPPING)
    userprofile = user.userprofile
    if not userprofile.industry_type == 'FMCG':
        del excel_headers["MRP"]
    return excel_headers


def get_inventory_adjustment_excel_upload_headers(user):
    excel_headers = copy.deepcopy(ADJUST_INVENTORY_EXCEL_MAPPING)
    userprofile = user.userprofile
    if not userprofile.user_type == 'marketplace_user':
        del excel_headers["Seller ID"]
    if not userprofile.industry_type == 'FMCG':
        del excel_headers["Batch Number"]
        del excel_headers["MRP"]
    return excel_headers


'''def check_and_get_marketplace(reader, file_type, no_of_rows, no_of_cols):
    marketplace = ''
    if get_cell_data(0, 0, reader, file_type) == 'Order No.':
        marketplace = 'Shopclues'
    elif get_cell_data(0, 0, reader, file_type) == 'Ordered On' and get_cell_data(0, 1, reader, file_type) in ['Shipment Id', 'Shipment ID']:
        marketplace = 'Flipkart'
    elif get_cell_data(0, 0, reader, file_type) == 'Order Id' and get_cell_data(0, 3, reader, file_type) == 'Vendor Code':
        marketplace = 'Paytm'
    elif get_cell_data(0, 0, reader, file_type) == 'Courier':
        marketplace = 'Snapdeal'
    elif get_cell_data(0, 0, reader, file_type) == 'order-id' and get_cell_data(0, 0, reader, file_type) == 'purchase-date':
        marketplace = 'Amazon'
    elif get_cell_data(0, 0, reader, file_type) == 'order_id' and get_cell_data(0, 2, reader, file_type) == 'creation time':
        marketplace = 'Limeroad'
    return marketplace


def get_order_mapping1(reader, file_type, no_of_rows, no_of_cols):
    order_mapping = {}
    if get_cell_data(0, 0, reader, file_type) == 'Sr. No' and get_cell_data(0, 3, reader, file_type) == 'HSN Code':
        order_mapping = copy.deepcopy(MYNTRA_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Sr. No' and get_cell_data(0, 3, reader, file_type) == 'Supp. Color':
        order_mapping = copy.deepcopy(JABONG_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'SOR ID' and get_cell_data(0, 1, reader, file_type) == 'UOR ID':
        order_mapping = copy.deepcopy(SHOTANG_ORDER_FILE_EXCEL)
    elif get_cell_data(0, 2, reader, file_type) == 'VENDOR ARTICLE NUMBER' and get_cell_data(0, 3, reader, file_type) == 'VENDOR ARTICLE NAME':
        order_mapping = copy.deepcopy(MYNTRA_BULK_PO_EXCEL)
    if order_mapping:
        return order_mapping
    order_excel = {}
    order_map = OrderedDict()
    mapping_order = OrderedDict(( ('order_id', 0), ('title', 1), ('sku_code', 2), ('quantity', 3), ('shipment_date', 4), ('channel_name', 5),
                                  ('shipment_check', 6), ('customer_id', 7), ('customer_name', 8), ('email_id', 9), ('telephone', 10),
                                  ('address', 11), ('state', 12), ('city', 13), ('pin_code', 14), ('invoice_amount', 15), ('amount', 16),
                                  ('amount_discount', 17), ('cgst_tax', 18), ('sgst_tax', 19), ('igst_tax', 20) ))

    for col_idx in range(0, no_of_cols):
        cell_data = get_cell_data(0, col_idx, reader, file_type)
        if cell_data in ['SKU Code', 'SKU', 'sku', 'product-name', 'Merchant SKU', 'item.sku', 'Vendor Code', 'Seller SKUs']:
            order_excel['sku_code'] = col_idx
        elif cell_data in ['Order Id', 'Reference Code', 'order-id', 'order_id', 'Order No.', 'Display Order #']:
            order_excel['original_order_id'] = col_idx
            order_excel['order_id'] = col_idx
        elif cell_data in ['Product', 'Product Details', 'item_name', 'Product Name']:
            order_excel['title'] = col_idx
        elif cell_data in ['qty', 'Qty', 'Quantity', 'quantity-to-ship', 'Item Count', 'quantity-purchased']:
            order_excel['quantity'] = col_idx
        elif cell_data in ['Customer Name', 'Ship to name', 'Buyer Name', 'customer_firstname']:
            order_excel['customer_name'] = col_idx
        elif cell_data in ['Selling Price Per Item', 'item_price', 'Price']:
            order_excel['unit_price'] = col_idx
        elif cell_data in ['Invoice Amount', 'InvoiceValue', 'Order Price']:
            order_excel['invoice_amount'] = col_idx
        elif cell_data in ['Address', 'Address Line 1', 'address', 'ship-address-1', 'Shipping Address']:
            order_excel['address'] = col_idx
        elif cell_data in ['CGST', 'Central Goods and Service Tax']:
            order_excel['cgst_tax'] = col_idx
        elif cell_data in ['SGST', 'State Goods and Service Tax']:
            order_excel['sgst_tax'] = col_idx
        elif cell_data in ['IGST', 'Integrated Goods and Service Tax']:
            order_excel['igst_tax'] = col_idx
        elif cell_data in ['Channel']:
            order_excel['channel_name'] = col_idx
        elif cell_data in ['Customer Email']:
            order_excel['email_id'] = col_idx
        elif cell_data in ['Customer Mobile']:
            order_excel['telephone'] = col_idx
        elif cell_data in ['Address City']:
            order_excel['city'] = col_idx
        elif cell_data in ['Address State']:
            order_excel['state'] = col_idx
        elif cell_data in ['Address Pincode']:
            order_excel['pin_code'] = col_idx

    if not order_excel.has_key('channel_name'):
        order_excel['marketplace'] = check_and_get_marketplace(reader, file_type, no_of_rows, no_of_cols)
    order_excel1 = OrderedDict(sorted(order_excel.items(), key=lambda pair: mapping_order.get(pair[0], '')))
    return order_excel1'''


def get_order_mapping(reader, file_type):
    order_mapping = {}
    if get_cell_data(0, 0, reader, file_type) == 'Central Order ID':
        order_mapping = copy.deepcopy(CENTRAL_ORDER_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Main SR Number':
        order_mapping = copy.deepcopy(CENTRAL_ORDER_EXCEL_ONE_ASSIST)
    elif get_cell_data(0, 0, reader, file_type) == 'Warehouse Name':
        order_mapping = copy.deepcopy(STOCK_TRANSFER_ORDER_EXCEL)
    elif get_cell_data(0, 2, reader, file_type) == 'Channel' and get_cell_data(0, 6, reader,
                                                                             file_type) == 'Fulfillment TAT':
        order_mapping = copy.deepcopy(UNI_COMMERCE_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Order No.' and get_cell_data(0, 1, reader,
                                                                                 file_type) == 'Time left for manifest':
        order_mapping = copy.deepcopy(SHOPCLUES_EXCEL)
    # elif get_cell_data(0, 4, reader, file_type) == 'Priority Level':
    #    order_mapping = copy.deepcopy(SHOPCLUES_EXCEL1)
    elif get_cell_data(0, 1, reader, file_type) == 'FSN' and get_cell_data(0, 16, reader, file_type) == 'Invoice No.':
        order_mapping = copy.deepcopy(FLIPKART_EXCEL)
    elif get_cell_data(0, 1, reader, file_type) == 'FSN' and get_cell_data(0, 16, reader, file_type) != 'Invoice No.':
        order_mapping = copy.deepcopy(FLIPKART_EXCEL1)
    elif get_cell_data(0, 1, reader, file_type) == 'Shipment ID' and get_cell_data(0, 2, reader,
                                                                                   file_type) == 'ORDER ITEM ID':
        order_mapping = copy.deepcopy(FLIPKART_EXCEL2)
    elif get_cell_data(0, 1, reader, file_type) == 'Shipment Id' and get_cell_data(0, 2, reader,
                                                                                   file_type) == 'Order Item Id' \
            and get_cell_data(0, 16, reader, file_type) != 'SKU Code':
        order_mapping = copy.deepcopy(FLIPKART_EXCEL3)
    elif get_cell_data(0, 1, reader, file_type) == 'Shipment Id' and get_cell_data(0, 2, reader,
                                                                                   file_type) == 'Order Item Id' \
            and get_cell_data(0, 16, reader, file_type) == 'SKU Code':
        order_mapping = copy.deepcopy(FLIPKART_EXCEL4)
    elif get_cell_data(0, 1, reader, file_type) == 'Date Time' and get_cell_data(0, 3, reader,
                                                                                 file_type) == 'Vendor Code':
        order_mapping = copy.deepcopy(LIMEROAD_EXCEL)
    # elif get_cell_data(0, 1, reader, file_type) == 'item_name':
    #    order_mapping = copy.deepcopy(PAYTM_EXCEL2)
    elif get_cell_data(0, 1, reader, file_type) == 'Order Item ID':
        order_mapping = copy.deepcopy(FLIPKART_FA_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Sr. No' and get_cell_data(0, 3, reader, file_type) == 'HSN Code':
        order_mapping = copy.deepcopy(MYNTRA_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Sr. No' and get_cell_data(0, 3, reader, file_type) == 'Supp. Color':
        order_mapping = copy.deepcopy(JABONG_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Product Name' and get_cell_data(0, 1, reader, file_type) == 'FSN':
        order_mapping = copy.deepcopy(FLIPKART_FA_EXCEL1)
    elif get_cell_data(0, 0, reader, file_type) == 'Shipping' and get_cell_data(0, 1, reader, file_type) == 'Date':
        order_mapping = copy.deepcopy(CAMPUS_SUTRA_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Order ID' and not get_cell_data(0, 1, reader,
                                                                                    file_type) == 'UOR ID':
        order_mapping = copy.deepcopy(ORDER_DEF_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Courier':
        order_mapping = copy.deepcopy(SNAPDEAL_EXCEL)
    elif get_cell_data(0, 1, reader, file_type) == 'Pack ID' and get_cell_data(0, 2, reader, file_type) == 'Pack Quantity'  :
          order_mapping = copy.deepcopy(SKU_PACK_EXCEL)
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
    elif get_cell_data(0, 2, reader, file_type) == 'purchase-date' and get_cell_data(0, 3, reader,
                                                                                     file_type) == 'payments-date':
        order_mapping = copy.deepcopy(AMAZON_EXCEL)
    # elif get_cell_data(0, 2, reader, file_type) == 'purchase-date' and get_cell_data(0, 4, reader, file_type) == 'buyer-email':
    #    order_mapping = copy.deepcopy(AMAZON_EXCEL1)
    elif get_cell_data(0, 1, reader, file_type) == 'AMB Order No':
        order_mapping = copy.deepcopy(ASKMEBAZZAR_EXCEL)
    elif get_cell_data(0, 3, reader, file_type) == 'customer_firstname' and get_cell_data(0, 4, reader,
                                                                                          file_type) == 'customer_lastname':
        order_mapping = copy.deepcopy(PAYTM_EXCEL)
    elif get_cell_data(0, 1, reader, file_type) == 'Uniware Created At' and get_cell_data(0, 0, reader,
                                                                                          file_type) == 'Order #':
        order_mapping = copy.deepcopy(UNI_COMMERCE_EXCEL1)
    elif get_cell_data(0, 0, reader, file_type) == 'Order Date' and get_cell_data(0, 3, reader,
                                                                                  file_type) == 'Total Value':
        order_mapping = copy.deepcopy(EASYOPS_ORDER_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Shipment' and get_cell_data(0, 1, reader, file_type) == 'Products':
        order_mapping = copy.deepcopy(UNI_WARE_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Sale Order Item Code' and get_cell_data(0, 2, reader,
                                                                                            file_type) == 'Reverse Pickup Code':
        order_mapping = copy.deepcopy(UNI_WARE_EXCEL1)
    elif get_cell_data(0, 0, reader, file_type) == 'SOR ID' and get_cell_data(0, 2, reader,
                                                                              file_type) == 'Product Code':
        order_mapping = copy.deepcopy(SHOTANG_ORDER_FILE_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'SOR ID' and get_cell_data(0, 2, reader, file_type) == 'Seller ID':
        order_mapping = copy.deepcopy(MARKETPLACE_ORDER_DEF_EXCEL)
    elif get_cell_data(0, 2, reader, file_type) == 'VENDOR ARTICLE NUMBER' and get_cell_data(0, 3, reader,
                                                                                             file_type) == 'VENDOR ARTICLE NAME':
        order_mapping = copy.deepcopy(MYNTRA_BULK_PO_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'bag_id' and get_cell_data(0, 2, reader, file_type) == 'order_date':
        order_mapping = copy.deepcopy(FYND_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Order_Number' and get_cell_data(0, 4, reader,
                                                                                    file_type) == 'Consignee_Email':
        order_mapping = copy.deepcopy(CRAFTSVILLA_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'amazon-order-id' and get_cell_data(0, 5, reader,
                                                                                       file_type) == 'fulfillment-channel':
        order_mapping = copy.deepcopy(CRAFTSVILLA_AMAZON_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'OrderNo' and get_cell_data(0, 5, reader,
                                                                               file_type) == 'BuyerAccountOrganizationName':
        order_mapping = copy.deepcopy(ALPHA_ACE_ORDER_EXCEL)
    return order_mapping


def get_customer_master_mapping(reader, file_type):
    ''' Return Customer Master Excel file indexes'''
    mapping_dict = {}
    if get_cell_data(0, 0, reader, file_type) == 'Customer Id' and get_cell_data(0, 1, reader,
                                                                                 file_type) == 'Customer Name':
        mapping_dict = copy.deepcopy(CUSTOMER_EXCEL_MAPPING)
    elif get_cell_data(0, 0, reader, file_type) == 'customer_id' and get_cell_data(0, 1, reader, file_type) == 'phone':
        mapping_dict = copy.deepcopy(MARKETPLACE_CUSTOMER_EXCEL_MAPPING)

    return mapping_dict


def myntra_order_tax_calc(key, value, order_mapping, order_summary_dict, row_idx, reader, file_type):
    cell_data = ''
    if isinstance(value, dict):
        vat = float(get_cell_data(row_idx, value['tax'], reader, file_type))
        quantity = float(get_cell_data(row_idx, value['quantity'], reader, file_type))
        order_summary_dict['issue_type'] = 'order'
        order_summary_dict['cgst_tax'] = vat / 2
        order_summary_dict['sgst_tax'] = vat / 2
        order_summary_dict['inter_state'] = 0
    elif isinstance(value, list):
        quantity = 1
        sku_length = get_cell_data(row_idx, order_mapping['sku_code'], reader, file_type)
        if 'quantity' in order_mapping.keys():
            quantity = float(get_cell_data(row_idx, order_mapping['quantity'], reader, file_type))
        elif ',' in sku_length:
            quantity = len(sku_length.split(','))
        amount = float(get_cell_data(row_idx, value[0], reader, file_type)) / quantity
        rate = float(get_cell_data(row_idx, value[1], reader, file_type))
        tax_value_item = (amount - rate)
        tax_value = tax_value_item * quantity
        vat = "%.2f" % (float(tax_value_item * 100) / rate)
        order_summary_dict['issue_type'] = 'order'
        order_summary_dict['cgst_tax'] = float(vat) / 2
        order_summary_dict['sgst_tax'] = float(vat) / 2
        order_summary_dict['inter_state'] = 0
    else:
        quantity = 1
        sku_length = get_cell_data(row_idx, order_mapping['sku_code'], reader, file_type)
        if 'quantity' in order_mapping.keys():
            quantity = float(get_cell_data(row_idx, order_mapping['quantity'], reader, file_type))
        elif ',' in sku_length:
            quantity = len(sku_length.split(','))
        rate = float(get_cell_data(row_idx, order_mapping['unit_price'], reader, file_type))
        tax_amt = float(get_cell_data(row_idx, value, reader, file_type)) / quantity
        tax_percent = tax_amt / (rate / 100)
        if not order_summary_dict.get('issue_type', ''):
            order_summary_dict['issue_type'] = 'order'
        order_summary_dict[key.replace('amt', 'tax')] = float('%.1f' % tax_percent)
        if order_summary_dict.get('igst_tax', 0) or order_summary_dict.get('utgst_tax', 0):
            order_summary_dict['inter_state'] = 1
    return order_mapping, order_summary_dict


@fn_timer
def check_and_save_order(cell_data, order_data, order_mapping, user_profile, seller_order_dict, order_summary_dict,
                         sku_ids,
                         sku_masters_dict, all_sku_decs, exist_created_orders, user):
    order_detail = ''
    order_obj_list = []
    sku_codes = str(cell_data).split(',')
    for cell_data in sku_codes:
        if isinstance(cell_data, float):
            cell_data = str(int(cell_data))
        order_data['sku_id'] = sku_masters_dict[cell_data]
        if not order_data.get('title', ''):
            order_data['title'] = all_sku_decs.get(order_data['sku_id'], '')
        order_obj = OrderDetail.objects.filter(order_id=order_data['order_id'], \
            order_code=order_data.get('order_code', ''), user=user.id, sku_id=order_data['sku_id'])
        order_create = True
        if user_profile.user_type == 'marketplace_user' and order_mapping.has_key('seller_id'):
            if not seller_order_dict['seller_id'] or (
            not seller_order_dict.get('order_status', '') in ['PROCESSED', 'DELIVERY_RESCHEDULED']):
                order_create = False
            elif seller_order_dict['seller_id'] and seller_order_dict.get('order_status', '') == 'DELIVERY_RESCHEDULED':
                seller_order_ins = SellerOrder.objects.filter(sor_id=seller_order_dict['sor_id'],
                                                              order__order_id=order_data['order_id'],
                                                              order__sku_id=order_data['sku_id'],
                                                              seller__user=user.id, order_status='PROCESSED')
                if not seller_order_ins:
                    order_create = False
        if not order_obj and order_create:
            if not order_mapping.has_key('shipment_date'):
                order_data['shipment_date'] = datetime.datetime.now()
            order_detail = OrderDetail(**order_data)
            order_creation_date = datetime.datetime.now()
            exist_order_ins = list(exist_created_orders.filter(order_id=order_data['order_id'],
                                                               order_code=order_data.get('order_code', '')))
            order_detail.save()
            if exist_order_ins:
                order_detail.creation_date = exist_order_ins[0].creation_date
                order_detail.shipment_date = exist_order_ins[0].shipment_date
                order_detail.save()
            if order_data.get('order_type', '') == 'Returnable Order':
                order_obj_list.append(order_obj)
            elif order_data.get('order_type', '').upper() == 'SP':
                if order_detail:
                    order_obj_list.append(order_detail)
                if len(order_obj_list):
                    order_obj_list = list(set(order_obj_list))
            check_create_seller_order(seller_order_dict, order_detail, user)
            if order_data['sku_id'] not in sku_ids:
                sku_ids.append(order_data['sku_id'])
            order_summary_dict['order_id'] = order_detail.id
            time_slot = get_local_date(user, datetime.datetime.now())
            order_summary_dict['shipment_time_slot'] = " ".join(time_slot.split(" ")[-2:])
            order_summary = CustomerOrderSummary(**order_summary_dict)
            order_summary.save()
        elif order_data['sku_id'] in sku_ids and order_create:
            order_obj = order_obj[0]
            order_obj.quantity = order_obj.quantity + order_data['quantity']
            order_obj.save()
            if order_data.get('order_type', '') == 'Returnable Order':
                order_obj_list.append(order_obj)
            elif order_data.get('order_type', '').upper() == 'SP':
                if order_obj:
                    order_obj_list.append(order_obj)
            if len(order_obj_list):
                order_obj_list = list(set(order_obj_list))
            check_create_seller_order(seller_order_dict, order_obj, user)
        elif order_obj and order_create and seller_order_dict.get('seller_id', '') and \
                        seller_order_dict.get('order_status') == 'DELIVERY_RESCHEDULED':
            order_obj = order_obj[0]
            if int(order_obj.status) in [2, 4, 5]:
                order_obj.status = 1
                update_seller_order(seller_order_dict, order_obj, user)
                order_obj.save()
                if order_data.get('order_type', '') == 'Returnable Order':
                    order_obj_list.append(order_obj)
                elif order_data.get('order_type', '').upper() == 'SP':
                    if order_obj:
                        order_obj_list.append(order_obj)
                if len(order_obj_list):
                    order_obj_list = list(set(order_obj_list))
        log.info("Order Saving Ended %s" % (datetime.datetime.now()))
    return sku_ids, order_obj_list, order_detail


def order_csv_xls_upload(request, reader, user, no_of_rows, fname, file_type='xls', no_of_cols=0):
    log.info("order upload started")
    st_time = datetime.datetime.now()
    index_status = {}
    # order_mapping = get_order_mapping1(reader, file_type, no_of_rows, no_of_cols)
    order_mapping = get_order_mapping(reader, file_type)
    if not order_mapping:
        return "Headers not matching"

    count = 0
    exclude_rows = []
    sku_masters_dict = {}
    order_id_order_type = {}
    log.info("Validation Started %s" % datetime.datetime.now())
    exist_created_orders = OrderDetail.objects.filter(user=user.id,
                                                      order_code__in=['MN', 'Delivery Challan', 'sample', 'R&D', 'CO'])
    extra_fields_mapping = OrderedDict()
    extra_fields_data = OrderedDict()
    for row_idx in range(0, 1):
        for col_idx in range(0, no_of_cols):
            excel_header_name = get_cell_data(row_idx, col_idx, reader, file_type)
            if 'Attribute - ' in excel_header_name:
                extra_fields_mapping[excel_header_name.replace('Attribute - ', '')] = col_idx
    for row_idx in range(1, no_of_rows):
        if not order_mapping:
            break
        count += 1
        if order_mapping.has_key('seller'):
            seller_id = get_cell_data(row_idx, order_mapping['seller'], reader, file_type)
            seller_master = None
            if seller_id:
                if isinstance(seller_id, float):
                    seller_id = int(seller_id)
                seller_master = SellerMaster.objects.filter(user=user.id, seller_id=seller_id)
            if not seller_master or not seller_id:
                exclude_rows.append(row_idx)
                continue
        if order_mapping.has_key('order_id'):
            cell_data = get_cell_data(row_idx, order_mapping['order_id'], reader, file_type)
            if not cell_data:
                index_status.setdefault(count, set()).add('Order Id should not be empty')
            if 'order_type' in order_mapping:
                order_type = get_cell_data(row_idx, order_mapping['order_type'], reader, file_type)
                if cell_data in order_id_order_type.keys():
                    if order_id_order_type[cell_data] != order_type:
                        index_status.setdefault(count, set()).add('Order Type are different for same orders')
                else:
                    order_id_order_type[cell_data]=order_type
        cell_data = get_cell_data(row_idx, order_mapping['sku_code'], reader, file_type)
        title = ''
        if order_mapping.has_key('title'):
            title = get_cell_data(row_idx, order_mapping['title'], reader, file_type)

        if type(cell_data) == float:
            sku_code = str(int(cell_data))
        #elif isinstance(cell_data, str) and '.' in cell_data:
        #    sku_code = str(int(float(cell_data)))
        else:
            sku_code = cell_data.upper()

        sku_codes = sku_code.split(',')
        for sku_code in sku_codes:
            sku_id = check_and_return_mapping_id(sku_code, title, user)
            if not sku_id:
                index_status.setdefault(count, set()).add('SKU Mapping Not Available')
            elif not sku_masters_dict.has_key(sku_code):
                sku_masters_dict[sku_code] = sku_id

        if order_mapping.has_key("shipment_check"):
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

        if 'order_type' in order_mapping:
            cell_data = get_cell_data(row_idx, order_mapping['order_type'], reader, file_type)
            if cell_data == 'Returnable Order' or cell_data.upper() == 'SP':
                if not get_cell_data(row_idx, order_mapping['customer_id'], reader, file_type):
                    index_status.setdefault(count, set()).add('Customer ID mandatory for Returnable Order')

        if 'mrp' in order_mapping:
            cell_data = get_cell_data(row_idx, order_mapping['mrp'], reader, file_type)
            if cell_data:
                try:
                    cell_data = float(cell_data)
                except:
                    index_status.setdefault(count, set()).add('MRP should be Number')
        if 'mode_of_transport' in order_mapping:
            mot_options = get_misc_value('mode_of_transport', user.id)
            cell_data = get_cell_data(row_idx, order_mapping['mode_of_transport'], reader, file_type)
            if cell_data and mot_options not in ['', 'false']:
                mot_options = mot_options.split(',')
                if cell_data not in mot_options:
                    index_status.setdefault(count, set()).add('Mode of Transport not defined')

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name

    sku_ids = []
    collect_order_obj_list = []

    user_profile = UserProfile.objects.get(user_id=user.id)
    log.info("Validation Ended %s" % (datetime.datetime.now()))
    all_sku_decs = dict(SKUMaster.objects.filter(user=user.id).values_list('id', 'sku_desc'))
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
        if order_mapping.get('status', '') and get_cell_data(row_idx, order_mapping['status'], reader,
                                                             file_type) != 'New':
            continue
        log.info("Order data Processing Started %s" % (datetime.datetime.now()))
        order_amount = 0
        for extra_key, extra_value in extra_fields_mapping.iteritems():
            extra_cell_val = get_cell_data(row_idx, extra_value, reader, file_type)
            if extra_cell_val:
                extra_fields_data[extra_key] = extra_cell_val
        for key, value in order_mapping.iteritems():
            if key in ['marketplace', 'status', 'split_order_id', 'recreate',
                       'shipment_check'] or key not in order_mapping.keys():
                continue
            if key == 'order_id' and order_mapping.has_key("order_id"):
                order_id = get_cell_data(row_idx, order_mapping['order_id'], reader, file_type)
                if isinstance(order_id, float):
                    order_id = str(int(order_id))
                order_data['original_order_id'] = order_id
                if order_mapping.get('split_order_id', '') and '/' in order_id:
                    order_id = order_id.split('/')[0]
                order_code = (''.join(re.findall('\D+', order_id))).replace("'", "").replace("`", "")
                order_id = ''.join(re.findall('\d+', order_id))
                if order_mapping.get('recreate', ""):
                    order_exist = OrderDetail.objects.filter(Q(order_id=order_id, order_code=order_code) |
                                                             Q(original_order_id=order_data['original_order_id']),
                                                             marketplace="JABONG_SC",
                                                             user=user.id)
                    if order_exist:
                        order_id = ""

                if order_id:
                    order_data['order_id'] = int(order_id)
                    if order_code:
                        order_data['order_code'] = order_code
                else:
                    # order_data['order_id'] = int(str(time.time()).replace(".", ""))
                    # order_data['order_id'] = time.time()* 1000000
                    order_data['order_id'] = get_order_id(user.id)
                    order_data['order_code'] = 'MN'

            elif key == 'quantity':
                order_data[key] = float(get_cell_data(row_idx, value, reader, file_type))
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
                    order_data[key] = float(get_cell_data(row_idx, value, reader, file_type)) / sku_length

            elif key == 'item_name':
                order_data['invoice_amount'] += int(get_cell_data(row_idx, 11, reader, file_type))
            elif key in ['vat', 'cgst_amt', 'sgst_amt', 'igst_amt', 'utgst_amt']:
                order_mapping, order_summary_dict = myntra_order_tax_calc(key, value, order_mapping, order_summary_dict,
                                                                          row_idx, reader, file_type)
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
                sku_code = get_cell_data(row_idx, value, reader, file_type)
            elif key == 'shipment_date':
                _shippment_date = get_cell_data(row_idx, value, reader, file_type)
                try:
                    year, month, day, hour, minute, second = xldate_as_tuple(_shippment_date, 0)
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
                try:
                    order_summary_dict['mrp'] = float(get_cell_data(row_idx, value, reader, file_type))
                except:
                    order_summary_dict['mrp'] = 0
            elif key == 'customer_id':
                cell_data = get_cell_data(row_idx, value, reader, file_type)
                if not cell_data:
                    cell_data = 0
                order_data[key] = cell_data
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
            elif key == 'amount':
                cell_data = get_cell_data(row_idx, value, reader, file_type)
                if not cell_data:
                    cell_data = 0
                order_amount = cell_data
                order_data['invoice_amount'] = cell_data
                order_data['unit_price'] = cell_data / order_data['quantity']
            elif key in ['cgst_tax', 'sgst_tax', 'igst_tax', 'cess_tax']:
                cell_data = get_cell_data(row_idx, value, reader, file_type)
                try:
                    cell_data = float(cell_data)
                except:
                    cell_data = 0
                order_summary_dict[key] = cell_data
                order_data['invoice_amount'] += (float(order_amount) / 100) * float(cell_data)
            elif key == 'amount_discount':
                cell_data = get_cell_data(row_idx, value, reader, file_type)
                if not cell_data:
                    cell_data = 0
                order_amount -= cell_data
                order_summary_dict['discount'] = cell_data
                order_data['invoice_amount'] -= float(cell_data)
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
                order_summary_dict['tax_value'] = "%.2f" % ((tax_percentage * invoice_amount_value) / 100)
                invoice_amount_value = invoice_amount_value + ((tax_percentage * invoice_amount_value) / 100)
                order_data['invoice_amount'] = invoice_amount_value
                if not order_data['marketplace']:
                    order_data['marketplace'] = "Offline"
            elif key == 'mode_of_transport':
                mode_of_transport = get_cell_data(row_idx, value, reader, file_type)
                if mode_of_transport:
                    order_summary_dict['mode_of_transport'] = mode_of_transport
            elif key == 'vehicle_number':
                vehicle_number = get_cell_data(row_idx, value, reader, file_type)
                if vehicle_number:
                    order_summary_dict['vehicle_number'] = vehicle_number
            else:
                order_data[key] = get_cell_data(row_idx, value, reader, file_type)

        order_data['user'] = user.id
        if user.username in ['adam_clothing1', 'adam_abstract'] and 'BOM' in str(order_data['original_order_id']):
            order_data['marketplace'] = 'Jabong'
        log.info("Order data processing ended%s" % (datetime.datetime.now()))
        if not order_data.has_key('quantity'):
            order_data['quantity'] = 1

        seller_order_dict['quantity'] = order_data['quantity']

        if type(sku_code) == float:
            cell_data = int(sku_code)
        else:
            cell_data = sku_code.upper()

        if not order_data.get('order_id', ''):
            order_data['order_id'] = get_order_id(user.id)
            order_data['order_code'] = 'MN'
        if isinstance(order_data['order_id'], float):
            order_data['order_id'] = str(int(order_data['order_id'])).upper()
        if isinstance(order_data['original_order_id'], float):
            order_data['original_order_id'] = str(int(order_data['original_order_id'])).upper()
        if order_data['marketplace']:
            order_data['marketplace'] = order_data['marketplace'].upper()
        if order_data.has_key('order_code'):
            order_data['order_code'] = order_data['order_code'].upper()
        if order_data.has_key('telephone'):
            if isinstance(order_data['telephone'], float):
                order_data['telephone'] = str(int(order_data['telephone']))

        log.info("Order Saving Started %s" % (datetime.datetime.now()))
        sku_ids, order_obj_list, order_detail = check_and_save_order(cell_data, order_data, order_mapping, user_profile, seller_order_dict,
                                       order_summary_dict, sku_ids,
                                       sku_masters_dict, all_sku_decs, exist_created_orders, user)
        if order_detail:
            created_order_id = order_detail.original_order_id
            if extra_fields_data:
                create_extra_fields_for_order(created_order_id, extra_fields_data, user)
        if len(order_obj_list):
            collect_order_obj_list = collect_order_obj_list + order_obj_list
    if len(collect_order_obj_list):
        collect_order_obj_list = list(set(collect_order_obj_list))
        create_order_pos(user, collect_order_obj_list)
    return 'success'


@csrf_exempt
@login_required
@get_admin_user
def order_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        upload_status = order_csv_xls_upload(request, reader, user, no_of_rows, fname, file_type=file_type,
                                             no_of_cols=no_of_cols)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Order Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Order Upload Failed")

    if not upload_status == 'success':
        return HttpResponse(upload_status)

    return HttpResponse('Success')


@csrf_exempt
@get_admin_user
def order_form(request, user=''):
    order_file = request.GET['download-order-form']
    if order_file:
        response = read_and_send_excel(order_file)
        return response

    wb = Workbook()
    ws = wb.add_sheet('order')
    header_style = easyxf('font: bold on')
    user_profile = UserProfile.objects.get(user_id=user.id)
    order_headers = copy.deepcopy(USER_ORDER_EXCEL_MAPPING.get(user_profile.user_type, {}))
    order_field_obj = get_misc_value('extra_order_fields', user.id)
    if not order_field_obj == 'false':
        extra_order_fields = order_field_obj.split(',')
        for extra_field in extra_order_fields:
            order_headers.append('%s - %s' % ('Attribute', str(extra_field)))
    for count, header in enumerate(order_headers):
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
    if user_profile.warehouse_type in ('WH', 'DIST'):
        headers = copy.deepcopy(USER_SKU_EXCEL[user_profile.warehouse_type])
    else:
        headers = copy.deepcopy(USER_SKU_EXCEL[user_profile.user_type])
    attributes = get_user_attributes(user, 'sku')
    attr_headers = list(attributes.values_list('attribute_name', flat=True))
    if get_misc_value('use_imei', user.id)  == 'true':
        headers.append("Enable Serial Number")
    if attr_headers:
        headers += attr_headers
    if user_profile.industry_type == "FMCG":
        headers.append("Shelf life")
    wb, ws = get_work_sheet('skus', headers)

    return xls_to_response(wb, '%s.sku_form.xls' % str(user.id))


@csrf_exempt
@get_admin_user
def sales_returns_form(request, user=''):
    returns_file = request.GET['download-sales-returns']
    if returns_file:
        return error_file_download(returns_file)

    sales_retun_mapping = copy.deepcopy(SALES_RETURNS_HEADERS)
    if user.userprofile.user_type == 'marketplace_user':
        sales_retun_mapping.append('SOR ID')
    wb, ws = get_work_sheet('returns', sales_retun_mapping)
    return xls_to_response(wb, '%s.returns_form.xls' % str(user.id))


@csrf_exempt
@login_required
@get_admin_user
def inventory_form(request, user=''):
    inventory_file = request.GET['download-file']
    if inventory_file:
        return error_file_download(inventory_file)
    excel_headers = get_inventory_excel_upload_headers(user)
    wb, ws = get_work_sheet('Inventory', excel_headers.keys())
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
        response = read_and_send_excel(order_file)
        return response
    wb = Workbook()
    ws = wb.add_sheet('Purchase Order')
    header_style = easyxf('font: bold on')
    excel_headers = get_purchase_order_excel_headers(user)
    for count, header in enumerate(excel_headers):
        ws.write(0, count, header, header_style)

    return xls_to_response(wb, '%s.purchase_order_form.xls' % str(user.id))


@csrf_exempt
@login_required
@get_admin_user
def move_inventory_form(request, user=''):
    inventory_file = request.GET['download-move-inventory-file']
    if inventory_file:
        return error_file_download(inventory_file)
    excel_headers = get_move_inventory_excel_upload_headers(user)
    wb, ws = get_work_sheet('Inventory', excel_headers)
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
    excel_headers = get_inventory_adjustment_excel_upload_headers(user)
    wb, ws = get_work_sheet('INVENTORY_ADJUST', excel_headers)
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
@get_admin_user
def network_master_form(request, user=''):
    returns_file = request.GET['download-network-master']
    if returns_file:
        return error_file_download(returns_file)

    wb, ws = get_work_sheet('Network', NETWORK_MASTER_HEADERS)
    return xls_to_response(wb, '%s.network_master_form.xls' % str(user.id))


@csrf_exempt
@get_admin_user
def order_label_mapping_form(request, user=''):
    label_file = request.GET['order-label-mapping-form']
    if label_file:
        return error_file_download(label_file)

    wb, ws = get_work_sheet('Order Labels', ORDER_LABEL_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.order_label_mapping_form.xls' % str(user.id))


@csrf_exempt
@get_admin_user
def order_serial_mapping_form(request, user=''):
    label_file = request.GET['order-serial-mapping-form']
    if label_file:
        return error_file_download(label_file)

    wb, ws = get_work_sheet('Order Serials', ORDER_SERIAL_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.order_serial_mapping_form.xls' % str(user.id))


@csrf_exempt
@get_admin_user
def po_serial_mapping_form(request, user=''):
    label_file = request.GET['po-serial-mapping-form']
    if label_file:
        return error_file_download(label_file)

    wb, ws = get_work_sheet('PO Serials', PO_SERIAL_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.po_serial_mapping_form.xls' % str(user.id))


@csrf_exempt
@get_admin_user
def job_order_form(request, user=''):
    label_file = request.GET['job-order-file']
    if label_file:
        return error_file_download(label_file)

    wb, ws = get_work_sheet('Job Order', JOB_ORDER_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.job_order_form.xls' % str(user.id))


@csrf_exempt
@get_admin_user
def marketplace_serial_form(request, user=''):
    label_file = request.GET['marketplace-serial-file']
    if label_file:
        return error_file_download(label_file)

    wb, ws = get_work_sheet('Marketplace Serial', MARKETPLACE_SERIAL_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.marketplace_serial_form.xls' % str(user.id))


@csrf_exempt
@get_admin_user
def orderid_awb_mapping_form(request, user=''):
    label_file = request.GET['orderid-awb-map-file']
    if label_file:
        return error_file_download(label_file)

    wb, ws = get_work_sheet('Awb Map', ORDER_ID_AWB_MAP_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.order_id_awb_mapping_form.xls' % str(user.id))


def get_orderid_awb_mapping(reader, file_type):
    order_awb_mapping = {}
    if get_cell_data(0, 0, reader, file_type) == 'Order ID' and get_cell_data(0, 1, reader, file_type) == 'AWB No':
        order_awb_mapping = copy.deepcopy(ORDER_ID_AWB_EXCEL_MAPPING)
    return order_awb_mapping


def check_get_order_id(order_id, user):
    order_obj = ''
    temp = re.findall('\d+', order_id)
    str_order_code = ''.join(re.findall('\D+', order_id))
    int_order_id = ''.join(re.findall('\d+', order_id))
    order_obj = OrderDetail.objects.filter(
        Q(original_order_id=order_id) | Q(order_code=str_order_code, order_id=int_order_id), user=user.id)
    return order_obj


def validate_upload_orderid_awb(request, reader, user, no_of_rows, fname, file_type='xls', no_of_cols=0):
    log.info("OrderID AWB upload started")
    st_time = datetime.datetime.now()
    index_status = {}
    order_mapping = get_orderid_awb_mapping(reader, file_type)
    if not order_mapping:
        return 'Invalid File'
    count = 0
    log.info("Validation Started %s" % datetime.datetime.now())
    all_data_list = []
    duplicate_products = []
    order_ids_list = []
    awb_list = []
    for row_idx in range(1, no_of_rows):
        if not order_mapping:
            break
        count += 1
        sku_code = ''
        orderid_awb_dict = {}
        for key, val in order_mapping.iteritems():
            value = get_cell_data(row_idx, order_mapping[key], reader, file_type)
            if key == 'order_id':
                if not value:
                    index_status.setdefault(count, set()).add('Order ID should not be empty')
                elif value:
                    if isinstance(value, float):
                        value = str(int(value)).upper()
                    order_obj = check_get_order_id(value, user)
                    if not order_obj:
                        index_status.setdefault(count, set()).add('Invalid Order ID')
                    else:
                        orderid_awb_dict['original_order_id'] = value
                        if value and value in order_ids_list:
                            index_status.setdefault(row_idx, set()).add('Duplicate Order Ids present in the sheet')
                    order_ids_list.append(value)
            elif key == 'awb_no':
                if isinstance(value, float):
                    value = str(int(value))
                if not value:
                    index_status.setdefault(count, set()).add('AWB No. not should not be empty')
                elif value:
                    if isinstance(value, float):
                        value = str(int(value)).upper()
                    orderid_awb_dict['awb_no'] = value
                    if value in awb_list:
                        index_status.setdefault(row_idx, set()).add('Duplicate AWB No. Present in the sheet')
                awb_list.append(value)
            elif key == 'courier_name':
                if not value:
                    index_status.setdefault(count, set()).add('Courier Name should not be empty')
                elif value:
                    orderid_awb_dict['courier_name'] = value.upper()
            elif key == 'marketplace':
                if value:
                    orderid_awb_dict['marketplace'] = value.upper()
                else:
                    orderid_awb_dict['marketplace'] = ''

                order_id = ''.join(re.findall('\d+', orderid_awb_dict['original_order_id'] ))
                order_code = ''.join(re.findall('\D+', orderid_awb_dict['original_order_id'] ))
                marketplace_valid = list(OrderDetail.objects.filter(Q(original_order_id= orderid_awb_dict['original_order_id']) |
                    Q(order_id=order_id, order_code= order_code), user=user.id).values_list('marketplace', flat=True).distinct())
                marketplace_valid = list(set(map(lambda x:x.upper(), marketplace_valid)))
                if not orderid_awb_dict['marketplace'] in marketplace_valid:
                    index_status.setdefault(row_idx, set()).add('Invalid Marketplace for this Order ID')

        all_data_list.append(orderid_awb_dict)
    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name
    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name
    create_update_orderid_awb(all_data_list, user)
    return 'Success'


def create_update_orderid_awb(all_data_list, user=''):
    for data_dict in all_data_list:
        order_awb_present = OrderAwbMap.objects.filter(original_order_id=data_dict['original_order_id'], user=user)
        if order_awb_present:
            order_awb_present.update(awb_no=data_dict['awb_no'], courier_name=data_dict['courier_name'],
                                     marketplace=data_dict['marketplace'], user=user,
                                     updation_date=datetime.datetime.now())
        else:
            OrderAwbMap.objects.create(awb_no=data_dict['awb_no'], courier_name=data_dict['courier_name'],
                                       original_order_id=data_dict['original_order_id'],
                                       marketplace=data_dict['marketplace'],
                                       user=user)


@csrf_exempt
@login_required
@get_admin_user
def orderid_awb_upload(request, user=''):
    fname = request.FILES['files']
    if (fname.name).split('.')[-1] == 'csv':
        reader = [[val.replace('\n', '').replace('\t', '').replace('\r', '') for val in row] for row in
                  csv.reader(fname.read().splitlines())]
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
        status = validate_upload_orderid_awb(request, reader, user, no_of_rows, fname, file_type=file_type)
        return HttpResponse(status)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(
            'OrderId-AWB Map Upload failed for %s and params are %s and error statement is %s' % (str(user.username),
                                                                                                  str(
                                                                                                      request.POST.dict()),
                                                                                                  str(e)))
    return HttpResponse("OrderId-AWB Map Upload Failed")


@csrf_exempt
def validate_sku_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type='xls', attributes={}):
    sku_data = []
    wms_data = []
    index_status = {}
    sku_file_mapping = get_sku_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type)
    product_types = list(TaxMaster.objects.filter(user_id=user.id).values_list('product_type', flat=True).distinct())
    if not sku_file_mapping:
        return 'Invalid File'
    for row_idx in range(1, no_of_rows):
        sku_code = ''
        for key, value in sku_file_mapping.iteritems():
            cell_data = get_cell_data(row_idx, sku_file_mapping[key], reader, file_type)
            if key in attributes.keys():
                if attributes[key] == 'Number' and cell_data:
                    try:
                        cell_data = int(cell_data)
                    except:
                        index_status.setdefault(row_idx, set()).add('%s is Number field' % (key))
            if key == 'wms_code':
                data_set = wms_data
                data_type = 'WMS'
                sku_code = cell_data
                if isinstance(cell_data, float):
                    sku_code = str(int(cell_data))
                # index_status = check_duplicates(data_set, data_type, cell_data, index_status, row_idx)
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('WMS Code missing')
            elif key == 'sku_group':
                if cell_data:
                    sku_groups = SKUGroups.objects.filter(group__iexact=cell_data, user=user.id)
                    if not sku_groups:
                        index_status.setdefault(row_idx, set()).add("Group doesn't exists")

            elif key == 'zone_id':
                if cell_data:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    data = ZoneMaster.objects.filter(zone=cell_data.upper(), user=user.id)
                    if not data:
                        index_status.setdefault(row_idx, set()).add('Invalid Zone')
                        # else:
                        #    index_status.setdefault(row_idx, set()).add('Zone should not be empty')
            elif key == 'ean_number':
                if cell_data:
                    try:
                        if ',' in str(cell_data):
                            ean_numbers = str(cell_data).split(',')
                        else:
                            ean_numbers = [int(cell_data)]
                        error_eans = []
                        for ean in ean_numbers:
                            ean = int(float(ean))
                            ean_status, mapping_check = check_ean_number(sku_code, ean, user)
                            if ean_status:
                                error_eans.append(str(ean))
                        if error_eans:
                            ean_error_msg = '%s EAN Numbers already mapped to Other SKUS' % ','.join(error_eans)
                            index_status.setdefault(row_idx, set()).add(ean_error_msg)
                    except:
                        index_status.setdefault(row_idx, set()).add('EAN must be integer')

            elif key == 'hsn_code':
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('HSN Code must be integer')
                        # elif not len(str(int(cell_data))) == 8:
                        #    index_status.setdefault(row_idx, set()).add('HSN Code should be 8 digit')

            elif key == 'product_type':
                if cell_data:
                    if cell_data not in product_types:
                        index_status.setdefault(row_idx, set()).add(
                            'Product Type should match with Tax master product type')

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
                if cell_data and str(cell_data).lower() not in LOAD_UNIT_HANDLE_DICT.keys():
                    index_status.setdefault(row_idx, set()).add('Invalid option for Load Unit Handling')
            elif key == 'sub_category' and user.username == 'sagar_fab':
                if cell_data:
                    if str(cell_data).upper() not in SUB_CATEGORIES.values():
                        index_status.setdefault(row_idx, set()).add('Sub Category Incorrect')
            elif key == 'hot_release':
                if cell_data:
                    if not str(cell_data).lower() in ['enable', 'disable']:
                        index_status.setdefault(row_idx, set()).add('Hot Release Should be Enable or Disable')
            elif key == 'enable_serial_based':
                if cell_data:
                    if not str(cell_data).lower() in ['enable', 'disable']:
                        index_status.setdefault(row_idx, set()).add('Enable Serial Number Should be Enable or Disable')
            elif key == 'sequence':
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Sequence should be in number')

    if not index_status:
        return 'Success'

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name


def get_sku_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type):
    sku_mapping = copy.deepcopy(SKU_COMMON_MAPPING)
    user_attributes = get_user_attributes(user, 'sku')
    attributes = user_attributes.values_list('attribute_name', flat=True)
    sku_mapping.update(dict(zip(attributes, attributes)))
    sku_file_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 sku_mapping)
    if get_cell_data(0, 1, reader, file_type) == 'Product Code' and get_cell_data(0, 2, reader, file_type) == 'Name':
        sku_file_mapping = copy.deepcopy(ITEM_MASTER_EXCEL)
    return sku_file_mapping


def sku_excel_upload(request, reader, user, no_of_rows, no_of_cols, fname, file_type='xls', attributes={}):
    from masters import check_update_size_type
    from masters import check_update_hot_release
    all_sku_masters = []
    zone_master = ZoneMaster.objects.filter(user=user.id).values('id', 'zone')
    zones = map(lambda d: str(d['zone']).upper(), zone_master)
    zone_ids = map(lambda d: d['id'], zone_master)
    sku_file_mapping = get_sku_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type)
    for row_idx in range(1, no_of_rows):
        if not sku_file_mapping:
            continue

        data_dict = copy.deepcopy(SKU_DATA)
        temp_dict = data_dict.keys()
        temp_dict += ['size_type', 'hot_release']
        data_dict['user'] = user.id

        sku_code = ''
        wms_code = ''
        sku_data = None
        _size_type = ''
        hot_release = 0
        attr_dict = {}
        ean_numbers = []
        for key, value in sku_file_mapping.iteritems():
            cell_data = get_cell_data(row_idx, sku_file_mapping[key], reader, file_type)
            if key in attributes.keys():
                try:
                    cell_data = int(cell_data)
                except:
                    pass
                attr_dict[key] = cell_data
                continue
            elif key not in temp_dict:
                continue
            if key == 'wms_code':
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(xcode(cell_data))

                wms_code = cell_data
                data_dict[key] = wms_code
                if wms_code:
                    sku_data = SKUMaster.objects.filter(user=user.id, sku_code=wms_code)
                    if sku_data:
                        sku_data = sku_data[0]

            elif key == 'zone_id':
                zone_id = None
                if cell_data:
                    cell_data = cell_data.upper()
                    if cell_data in zones:
                        # zone_id = ZoneMaster.objects.get(zone=cell_data.upper(),user=user.id).id
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
                    cell_data = (str(re.sub(r'[^\x00-\x7F]+', '', cell_data))).replace('\n', '')
                except:
                    cell_data = ''
                if sku_data and cell_data:
                    sku_data.sku_desc = cell_data
                data_dict[key] = cell_data
            elif key == 'sub_category':
                if cell_data and isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                if sku_data and cell_data:
                    sku_data.sub_category = cell_data.upper()
                data_dict[key] = cell_data.upper()
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
                    cell_data = str(int(cell_data))
                except:
                    cell_data = str(xcode(cell_data))
                if sku_data and cell_data:
                    setattr(sku_data, key, cell_data)
                data_dict[key] = cell_data
                _size_type = get_cell_data(row_idx, sku_file_mapping['size_type'], reader, file_type)

            elif key == 'size_type':
                continue

            elif key == 'hot_release':
                hot_release = str(cell_data).lower()

            elif key == 'shelf_life':
                if not cell_data:
                    cell_data = 0
                if sku_data and cell_data:
                    sku_data.shelf_life = cell_data
                data_dict[key] = cell_data
            elif key == 'ean_number':
                if cell_data:
                    if ',' in str(cell_data):
                        ean_numbers = str(cell_data).split(',')
                    else:
                        ean_numbers = [str(int(cell_data))]
            elif key == 'enable_serial_based':
                toggle_value = str(cell_data).lower()
                if toggle_value == "enable":
                    cell_data = 1
                if toggle_value == "disable":
                    cell_data = 0
                setattr(sku_data, key, cell_data)
                data_dict[key] = cell_data
            elif cell_data:
                data_dict[key] = cell_data
                if sku_data:
                    setattr(sku_data, key, cell_data)
                data_dict[key] = cell_data
        if sku_data:
	    storehippo_sync_price_value(user, {'wms_code':sku_data.wms_code, 'price':sku_data.price})
            sku_data.save()
            all_sku_masters.append(sku_data)
        if not sku_data:
            data_dict['sku_code'] = data_dict['wms_code']
            sku_master = SKUMaster(**data_dict)
            sku_master.save()
            all_sku_masters.append(sku_master)
            sku_data = sku_master

        if _size_type:
            check_update_size_type(sku_data, _size_type)
        if hot_release:
            hot_release = 1 if (hot_release == 'enable') else 0
            check_update_hot_release(sku_data, hot_release)
        for attr_key, attr_val in attr_dict.iteritems():
            update_sku_attributes_data(sku_data, attr_key, attr_val)

        if ean_numbers:
            update_ean_sku_mapping(user, ean_numbers, sku_data, remove_existing=True)
    # get_user_sku_data(user)
    insert_update_brands(user)

    # Sync sku's with sister warehouses
    sync_sku_switch = get_misc_value('sku_sync', user.id)
    if sync_sku_switch == 'true':
        all_users = get_related_users(user.id)
        create_update_sku(all_sku_masters, all_users)

    return 'success'


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False)
def sku_upload(request, user=''):
    try:
        reversion.set_user(request.user)
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        user_attributes = get_user_attributes(user, 'sku')
        attributes = dict(user_attributes.values_list('attribute_name', 'attribute_type'))
        status = validate_sku_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type=file_type,
                                   attributes=attributes)
        if status != 'Success':
            return HttpResponse(status)

        sku_excel_upload(request, reader, user, no_of_rows, no_of_cols, fname, file_type=file_type,
                         attributes=attributes)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('SKU Master Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("SKU Master Upload Failed")

    return HttpResponse('Success')


def get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type, inv_mapping):
    file_mapping = OrderedDict()
    for ind in range(0, no_of_cols):
        cell_data = get_cell_data(0, ind, reader, file_type)
        if cell_data in inv_mapping:
            file_mapping[inv_mapping[cell_data]] = ind
    return file_mapping

@csrf_exempt
def validate_inventory_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type):
    mapping_dict = {}
    index_status = {}
    location = {}
    inv_mapping = get_inventory_excel_upload_headers(user)
    inv_res = dict(zip(inv_mapping.values(), inv_mapping.keys()))
    excel_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 inv_mapping)
    if not set(['receipt_date', 'quantity', 'wms_code', 'location']).issubset(excel_mapping.keys()):
        return 'Invalid File', []
    number_fields = ['quantity', 'mrp']
    optional_fields = ['mrp']
    mandatory_fields = ['receipt_date', 'location', 'quantity', 'receipt_type']
    fields_mapping = {'manufactured_date': 'Manufactured Date', 'expiry_date': 'Expiry Date'}
    location_master = LocationMaster.objects.filter(zone__user=user.id)
    data_list = []
    for row_idx in range(1, no_of_rows):
        data_dict = {}
        for key, value in excel_mapping.iteritems():
            cell_data = get_cell_data(row_idx, value, reader, file_type)
            if key in mandatory_fields and cell_data == '':
                index_status.setdefault(row_idx, set()).add('Missing %s' % inv_res[key])
            if key == 'receipt_date':
                try:
                    receipt_date = ''
                    if isinstance(cell_data, float):
                        year, month, day, hour, minute, second = xldate_as_tuple(cell_data, 0)
                        receipt_date = datetime.datetime(year, month, day, hour, minute, second)
                    elif '-' in cell_data:
                        receipt_date = datetime.datetime.strptime(cell_data, "%Y-%m-%d")
                    else:
                        index_status.setdefault(row_idx, set()).add('Invalid Receipt Date format')
                    data_dict[key] = receipt_date
                except:
                    index_status.setdefault(row_idx, set()).add('Invalid Receipt Date format')
            elif key in ['manufactured_date', 'expiry_date']:
                if cell_data:
                    try:
                        if isinstance(cell_data, float):
                            year, month, day, hour, minute, second = xldate_as_tuple(cell_data, 0)
                            data_dict[key] = datetime.datetime(year, month, day, hour, minute, second)
                        elif '-' in cell_data:
                            data_dict[key] = datetime.datetime.strptime(cell_data, "%Y-%m-%d")
                        else:
                            index_status.setdefault(row_idx, set()).add('Invalid %s format' % (fields_mapping[key]))
                    except:
                        index_status.setdefault(row_idx, set()).add('Invalid %s format' % (fields_mapping[key]))
            elif key == 'wms_code':
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                try:
                    cell_data = str(re.sub(r'[^\x00-\x7F]+', '', cell_data))
                except:
                    cell_data = ''

                mapping_dict[row_idx] = cell_data
                sku_id = check_and_return_mapping_id(cell_data, '', user)
                if not sku_id:
                    index_status.setdefault(row_idx, set()).add('Invalid SKU-WMS Mapping')
                data_dict['sku_id'] = sku_id
            elif key == 'location':
                location_obj = location_master.filter(location=cell_data)
                if not location_obj:
                    index_status.setdefault(row_idx, set()).add('Invalid Location')
                else:
                    data_dict['location_id'] = location_obj[0].id
            elif key == 'seller_id':
                try:
                    seller_master = SellerMaster.objects.filter(user=user.id, seller_id=int(cell_data))
                    if not seller_master:
                        index_status.setdefault(row_idx, set()).add('Invalid Seller ID')
                    else:
                        data_dict['seller_id'] = seller_master[0].id
                except:
                    index_status.setdefault(row_idx, set()).add('Seller ID Should be number')
            elif key in number_fields:
                try:
                    data_dict[key] = float(cell_data)
                except:
                    if key not in optional_fields:
                        index_status.setdefault(row_idx, set()).add('Invalid Value for %s' % inv_res[key])
                data_dict[key] = cell_data
            else:
                data_dict[key] = cell_data
        if user.userprofile.industry_type == 'FMCG' and data_dict['sku_id']:
            if not data_dict.get('manufactured_date', ''):
                data_dict['manufactured_date'] = datetime.datetime.now()
            if not data_dict.get('expiry_date', ''):
                sku_master = SKUMaster.objects.get(id=data_dict['sku_id'])
                data_dict['expiry_date'] = data_dict['manufactured_date'] + datetime.timedelta(sku_master.shelf_life)
        data_list.append(data_dict)

    if not index_status:
        return 'Success', data_list

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name, data_list

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name, data_list


def check_location(location, user, quantity=0):
    loc_existance = LocationMaster.objects.get(location=location, zone__user=user)
    if loc_existance:
        return int(loc_existance.id)
    else:
        return


def inventory_excel_upload(request, user, data_list):
    #RECORDS = list(EXCEL_RECORDS)
    sku_codes = []
    mod_locations = []
    putaway_stock_data = {}
    receipt_number = get_stock_receipt_number(user)
    seller_receipt_dict = {}
    for inventory_data in data_list:
        seller_id = ''
        if 'seller_id' in inventory_data.keys():
            seller_id = inventory_data['seller_id']
            if str(seller_id) in seller_receipt_dict.keys():
                receipt_number = seller_receipt_dict[str(seller_id)]
            else:
                receipt_number = get_stock_receipt_number(user)
                seller_receipt_dict[str(seller_id)] = receipt_number
            del inventory_data['seller_id']
        receipt_date = inventory_data['receipt_date']
        if inventory_data.get('sku_id', '') and inventory_data.get('location_id', ''):
            pallet_number = inventory_data.get('pallet_number', '')
            if 'pallet_number' in inventory_data.keys():
                del inventory_data['pallet_number']
            batch_no = inventory_data.get('batch_no', '')
            if 'batch_no' in inventory_data.keys():
                del inventory_data['batch_no']
            mrp = inventory_data.get('mrp', 0)
            if 'mrp' in inventory_data.keys():
                del inventory_data['mrp']
            mfg_date = inventory_data.get('manufactured_date', '')
            if 'manufactured_date' in inventory_data.keys():
                del inventory_data['manufactured_date']
            exp_date = inventory_data.get('expiry_date', '')
            if 'expiry_date' in inventory_data.keys():
                del inventory_data['expiry_date']

            stock_query_filter = {'sku_id': inventory_data.get('sku_id', ''),
                                  'location_id': inventory_data.get('location_id', ''),
                                  'receipt_number': receipt_number, 'sku__user': user.id}
            if pallet_number:
                pallet_data = {'pallet_code': pallet_number, 'quantity': int(inventory_data['quantity']),
                               'user': user.id,
                               'status': 1, 'creation_date': str(datetime.datetime.now()),
                               'updation_date': str(datetime.datetime.now())}
                pallet_detail = PalletDetail(**pallet_data)
                pallet_detail.save()
                stock_query_filter['pallet_detail_id'] = pallet_detail.id
                inventory_data['pallet_detail_id'] = pallet_detail.id
            if mrp or batch_no or mfg_date or exp_date:
                try:
                    mrp = float(mrp)
                except:
                    mrp = 0
                if isinstance(batch_no, float):
                    batch_no = str(int(batch_no))
                batch_dict = {'batch_no': batch_no, 'mrp': mrp, 'creation_date': datetime.datetime.now()}
                if mfg_date:
                    batch_dict['manufactured_date'] = mfg_date
                if exp_date:
                    batch_dict['expiry_date'] = exp_date
                add_ean_weight_to_batch_detail(SKUMaster.objects.get(id=inventory_data['sku_id']), batch_dict)
                batch_obj = BatchDetail(**batch_dict)
                batch_obj.save()
                stock_query_filter['batch_detail_id'] = batch_obj.id
                inventory_data['batch_detail_id'] = batch_obj.id
            inventory_status = StockDetail.objects.filter(**stock_query_filter)
            if not inventory_status and inventory_data.get('quantity', ''):
                inventory_data['status'] = 1
                inventory_data['creation_date'] = str(datetime.datetime.now())
                inventory_data['receipt_date'] = receipt_date
                inventory_data['receipt_number'] = receipt_number
                sku_master = SKUMaster.objects.get(id=inventory_data['sku_id'])
                if not sku_master.zone:
                    location_master = LocationMaster.objects.get(id=inventory_data['location_id'])
                    sku_master.zone_id = location_master.zone_id
                    sku_master.save()
                inventory = StockDetail(**inventory_data)
                inventory.save()
                if seller_id:
                    #Saving seller stock
                    seller_stock = SellerStock.objects.create(seller_id=seller_id,
                                                              quantity=inventory_data['quantity'],
                                                              creation_date=datetime.datetime.now(), status=1,
                                                              stock_id=inventory.id)

                # SKU Stats
                save_sku_stats(user, inventory.sku_id, inventory.id, 'inventory-upload', inventory.quantity, inventory)

                # Collecting data for auto stock allocation
                putaway_stock_data.setdefault(inventory.sku_id, [])

                mod_locations.append(inventory.location.location)

            elif inventory_status and inventory_data.get('quantity', ''):
                inventory_status = inventory_status[0]
                inventory_status.quantity = int(inventory_status.quantity) + int(inventory_data.get('quantity', 0))
                inventory_status.receipt_date = receipt_date
                inventory_status.save()
                if seller_id:
                    #Saving seller stock
                    seller_stock_obj = SellerStock.objects.filter(seller_id=seller_id,
                                                                  stock_id=inventory_status.id)
                    if not seller_stock_obj:
                        seller_stock = SellerStock.objects.create(seller_id=seller_id,
                                                              quantity=inventory_data['quantity'],
                                                              creation_date=datetime.datetime.now(), status=1,
                                                              stock_id=inventory.id)
                    else:
                        seller_stock = seller_stock_obj[0]
                        seller_stock.quantity = float(seller_stock.quantity) + inventory_data['quantity']
                        seller_stock.save()
                # SKU Stats
                save_sku_stats(user, inventory_status.sku_id, inventory_status.id, 'inventory-upload',
                               int(inventory_data.get('quantity', 0)), inventory_status)
                # Collecting data for auto stock allocation
                putaway_stock_data.setdefault(inventory_status.sku_id, [])

                mod_locations.append(inventory_status.location.location)

            location_master = LocationMaster.objects.get(id=inventory_data.get('location_id', ''), zone__user=user.id)
            location_master.filled_capacity += inventory_data.get('quantity', 0)
            location_master.save()

    check_and_update_stock(sku_codes, user)
    if mod_locations:
        update_filled_capacity(list(set(mod_locations)), user.id)

    # Auto Allocate Stock
    order_allocate_stock(request, user, stock_data=putaway_stock_data, mapping_type='')

    return 'success'


@csrf_exempt
@login_required
@get_admin_user
def inventory_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
    except:
        return HttpResponse('Invalid File')
    status, data_list = validate_inventory_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type)

    if status != 'Success':
        return HttpResponse(status)

    inventory_excel_upload(request, user, data_list)

    return HttpResponse('Success')


@csrf_exempt
def validate_supplier_form(open_sheet, user_id):
    index_status = {}
    supplier_ids = []
    mapping_dict = copy.deepcopy(SUPPLIER_EXCEL_FIELDS)
    messages_dict = {'phone_number': 'Phone Number', 'days_to_supply': 'Days required to supply',
                     'fulfillment_amt': 'Fulfillment Amount', 'owner_number': 'Owner Number',
                     'spoc_number': 'SPOC Number', 'lead_time': 'Lead Time', 'credit_period': 'Credit Period',
                     'account_number': 'Account Number', 'po_exp_duration': 'PO Expiry Duration',
                     'pincode': 'PinCode'}
    number_str_fields = ['phone_number', 'days_to_supply', 'fulfillment_amt', 'po_exp_duration',
                         'owner_number', 'spoc_number', 'lead_time', 'credit_period', 'account_number']
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
                if cell_data:
                    supplier_master = SupplierMaster.objects.filter(id=cell_data)
                    if supplier_master and not str(supplier_master[0].user) == str(user_id):
                        index_status.setdefault(row_idx, set()).add('Supplier ID Already exists')
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
            elif key == 'pincode':
                if cell_data:
                    try:
                        cell_data = float(cell_data)
                    except:
                        index_status.setdefault(row_idx, set()).add('Invalid %s' % messages_dict[key])
            elif key in number_str_fields:
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Invalid %s' % messages_dict[key])


    if not index_status:
        return 'Success'

    f_name = '%s.supplier_form.xls' % user_id
    write_error_file(f_name, index_status, open_sheet, SUPPLIER_HEADERS, 'Supplier')
    return f_name


def supplier_excel_upload(request, open_sheet, user, demo_data=False):
    mapping_dict = copy.deepcopy(SUPPLIER_EXCEL_FIELDS)
    number_str_fields = ['pincode', 'phone_number', 'days_to_supply', 'fulfillment_amt', 'po_exp_duration',
                         'owner_number', 'spoc_number', 'lead_time', 'credit_period', 'account_number']
    rev_tax_types = dict(zip(TAX_TYPE_ATTRIBUTES.values(), TAX_TYPE_ATTRIBUTES.keys()))
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
                cell_data = str(xcode(cell_data))
                supplier_data['name'] = cell_data
                if supplier_master and cell_data:
                    setattr(supplier_master, key, cell_data)
            elif key == 'tax_type':
                if cell_data:
                    cell_data = rev_tax_types.get(cell_data, '')
                supplier_data['tax_type'] = cell_data
                if supplier_master and cell_data:
                    supplier_master.tax_type = supplier_data['tax_type']

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
                    vendor_data['name'] = cell_data
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
    supplier_list = SupplierMaster.objects.filter(user=user_id).values_list('id', flat=True)
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
                    wms_check = SKUMaster.objects.filter(wms_code=cell_data, user=user_id)
                    if not wms_check:
                        index_status.setdefault(row_idx, set()).add('Invalid WMS Code')
                    wms_code1 = cell_data
            if col_idx == 3:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing Preference')
                else:
                    preference1 = int(cell_data)

        if wms_code1 and preference1 and row_idx > 0:
            supp_val = SKUMaster.objects.filter(wms_code=wms_code1, user=user_id)
            if supp_val:
                temp1 = SKUSupplier.objects.filter(Q(sku_id=supp_val[0].id) & Q(preference=preference1),
                                                   sku__user=user_id)
                sku_supplier = SKUSupplier.objects.filter(sku_id=supp_val[0].id, supplier_id=supplier_id,
                                                          sku__user=user_id)
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
                    supplier_sku_obj = SKUSupplier.objects.filter(supplier_id=supplier_data['supplier_id'],
                                                                  sku_id=sku_master[0].id)
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
                # index_status = alphanum_validation(cell_data, value, index_status, row_idx)

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

        location = LocationMaster.objects.filter(location=location_data['location'], zone__user=user.id)
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
def validate_purchase_order(request, reader, user, no_of_rows, no_of_cols, fname, file_type, demo_data=False):
    index_status = {}
    data_list = []
    purchase_mapping = get_purchase_order_excel_headers(user)
    purchase_res = dict(zip(purchase_mapping.values(), purchase_mapping.keys()))
    excel_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 purchase_mapping)
    if not set(['po_name', 'po_date', 'po_delivery_date', 'supplier_id', 'wms_code', 'quantity', 'price', 'mrp',
                'cgst_tax', 'sgst_tax', 'igst_tax', 'utgst_tax', 'apmc_tax', 'ship_to']).issubset(excel_mapping.keys()):
        return 'Invalid File', []
    mapping_fields = {'po_date': 'PO Date', 'po_delivery_date': 'PO Delivery Date', 'mrp': 'MRP',
                      'cgst_tax': 'CGST Tax', 'sgst_tax': 'SGST Tax', 'igst_tax': 'IGST Tax', 'utgst_tax': 'UTGST Tax',
                      'cess_tax': 'CESS Tax', 'apmc_tax': 'APMC Tax'}
    number_fields = ['mrp', 'cgst_tax', 'sgst_tax', 'igst_tax', 'utgst_tax', 'cess_tax', 'apmc_tax']
    user_profile = user.userprofile
    for row_idx in range(1, no_of_rows):
        data_dict = {}
        for key, value in excel_mapping.iteritems():
            cell_data = get_cell_data(row_idx, value, reader, file_type)
            if key == 'supplier_id':
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                if demo_data:
                    cell_data = user_profile.prefix + '_' + cell_data
                if cell_data:
                    supplier = SupplierMaster.objects.filter(user=user.id, id=cell_data.upper())
                    if not supplier:
                        index_status.setdefault(row_idx, set()).add("Supplier ID doesn't exist")
                    else:
                        data_dict['supplier'] = supplier[0]
                else:
                    index_status.setdefault(row_idx, set()).add('Missing Supplier ID')
            elif key in ['po_date', 'po_delivery_date']:
                if cell_data:
                    try:
                        if isinstance(cell_data, float):
                            year, month, day, hour, minute, second = xldate_as_tuple(cell_data, 0)
                            data_dict[key] = datetime.datetime(year, month, day, hour, minute, second)
                        elif '-' in cell_data:
                            data_dict[key] = datetime.datetime.strptime(cell_data, "%m-%d-%Y")
                        else:
                            index_status.setdefault(row_idx, set()).add('Check the date format for %s' %
                                                                        mapping_fields[key])
                    except:
                        index_status.setdefault(row_idx, set()).add('Check the date format for %s' %
                                                                    mapping_fields[key])
            elif key == 'wms_code':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing WMS Code')
                else:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    sku_master = SKUMaster.objects.filter(wms_code=cell_data.upper(), user=user.id)
                    if not sku_master:
                        index_status.setdefault(row_idx, set()).add("WMS Code doesn't exist")
                    else:
                        data_dict['sku'] = sku_master[0]
            elif key == 'seller_id':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing Seller ID')
                else:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Seller ID is Number Field')
                    else:
                        cell_data = int(cell_data)
                        seller_master = SellerMaster.objects.filter(seller_id=cell_data, user=user.id)
                        if not seller_master:
                            index_status.setdefault(row_idx, set()).add("Seller doesn't exist")
                        else:
                            data_dict['seller'] = seller_master[0]
            elif key == 'quantity':
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Quantity should be integer')
                    else:
                        data_dict[key] = float(cell_data)
                else:
                    index_status.setdefault(row_idx, set()).add('Missing Quantity')
            elif key == 'price':
                if cell_data != '':
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Unit Price should be a number')
                    else:
                        data_dict[key] = float(cell_data)
                else:
                    data_dict[key] = 0
            elif key in ['po_name', 'ship_to']:
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                data_dict[key] = cell_data
            elif cell_data:
                if key in number_fields:
                    try:
                        cell_data = float(cell_data)
                        data_dict[key] = cell_data
                    except:
                        index_status.setdefault(row_idx, set()).add('%s is Number Field' % mapping_fields[key])
                else:
                    data_dict[key] = cell_data
        data_list.append(data_dict)
    if not index_status:
        return 'Success', data_list

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name, data_list

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name, data_list


def purchase_order_excel_upload(request, user, data_list, demo_data=False):
    from inbound import write_and_mail_pdf
    order_ids = {}
    data_req = {}
    mail_result_data = ""
    user_profile = user.userprofile
    creation_date = datetime.datetime.now()
    po_sub_user_prefix = get_misc_value('po_sub_user_prefix', user.id)
    show_cess_tax = False
    show_apmc_tax = False
    ean_flag = False
    total_qty = 0
    wms_codes_list = list(set(map(lambda d: d['sku'].wms_code, data_list)))
    ean_data = SKUMaster.objects.filter(Q(ean_number__gt=0) | Q(eannumbers__ean_number__gt=0),
                                        wms_code__in=wms_codes_list, user=user.id)
    if ean_data.exists():
        ean_flag = True
    for final_dict1 in data_list:
        if final_dict1.get('cess_tax', 0):
            show_cess_tax = True
        if final_dict1.get('apmc_tax', 0):
            show_apmc_tax = True
        if show_cess_tax and show_apmc_tax and ean_flag:
            break
    if user_profile.industry_type == 'FMCG':
        table_headers = ['WMS Code', 'Supplier Code', 'Desc', 'Qty', 'UOM', 'Unit Price', 'MRP', 'Amt',
                         'SGST (%)', 'CGST (%)', 'IGST (%)', 'UTGST (%)', 'Total']
    else:
        table_headers = ['WMS Code', 'Supplier Code', 'Desc', 'Qty', 'UOM', 'Unit Price', 'Amt',
                         'SGST (%)', 'CGST (%)', 'IGST (%)', 'UTGST (%)', 'Total']
    if ean_flag:
        table_headers.insert(1, 'EAN')
    if show_cess_tax:
        table_headers.insert(table_headers.index('UTGST (%)'), 'CESS (%)')
    if show_apmc_tax:
        table_headers.insert(table_headers.index('UTGST (%)'), 'APMC (%)')
    po_data = []
    for final_dict in data_list:
        order_data = copy.deepcopy(PO_SUGGESTIONS_DATA)
        data = copy.deepcopy(PO_DATA)
        order_data['supplier_id'] = final_dict['supplier'].id
        order_data['sku_id'] = final_dict['sku'].id
        order_data['order_quantity'] = final_dict['quantity']
        order_data['price'] = final_dict.get('price', 0)
        order_data['po_name'] = final_dict['po_name']
        order_data['mrp'] = final_dict.get('mrp', 0)
        order_data['cgst_tax'] = final_dict.get('cgst_tax', 0)
        order_data['sgst_tax'] = final_dict.get('sgst_tax', 0)
        order_data['igst_tax'] = final_dict.get('igst_tax', 0)
        order_data['utgst_tax'] = final_dict.get('utgst_tax', 0)
        order_data['cess_tax'] = final_dict.get('cess_tax', 0)
        order_data['apmc_tax'] = final_dict.get('apmc_tax', 0)
        order_data['measurement_unit'] = final_dict['sku'].measurement_type
        order_data['creation_date'] = creation_date
        if final_dict.get('po_delivery_date', ''):
            order_data['delivery_date'] = final_dict['po_delivery_date']
        data['po_date'] = final_dict['po_date']
        data['ship_to'] = final_dict['ship_to']
        data['creation_date'] = creation_date
        seller_id = ''
        if final_dict.get('seller', ''):
            seller_id = final_dict['seller'].id
        group_key = (order_data['po_name'], order_data['supplier_id'], data['po_date'], seller_id)
        if group_key not in order_ids.keys():
            po_id = get_purchase_order_id(user)
            if po_sub_user_prefix == 'true':
                po_id = update_po_order_prefix(request.user, po_id)
            order_ids[group_key] = po_id
        else:
            po_id = order_ids[group_key]
        ids_dict = {}
        total = 0
        order_data['status'] = 0
        data1 = OpenPO(**order_data)
        data1.save()
        if seller_id:
            SellerPO.objects.create(seller_id=seller_id, open_po_id=data1.id,
                                    seller_quantity=order_data['order_quantity'], unit_price=order_data['price'],
                                    creation_date=creation_date)
        purchase_order = OpenPO.objects.get(id=data1.id, sku__user=user.id)
        sup_id = purchase_order.id
        supplier = purchase_order.supplier_id
        if supplier not in ids_dict:
            po_id = po_id + 1
            ids_dict[supplier] = po_id
        data['open_po_id'] = sup_id
        data['order_id'] = ids_dict[supplier]
        if user_profile:
            data['prefix'] = user_profile.prefix
        order = PurchaseOrder(**data)
        order.save()
        order.po_date = data['po_date']
        order.save()
        amount = data1.order_quantity * data1.price
        total_qty += data1.order_quantity
        total_tax_amt = (data1.utgst_tax + data1.sgst_tax + data1.cgst_tax + data1.igst_tax + data1.cess_tax + data1.apmc_tax + data1.utgst_tax) * (
                                    amount / 100)
        total_sku_amt = total_tax_amt + amount
        if user_profile.industry_type == 'FMCG':
            po_temp_data = [data1.sku.wms_code, data1.supplier_code, data1.sku.sku_desc,
                            data1.order_quantity,
                            data1.measurement_unit,
                            data1.price, data1.mrp, amount, data1.sgst_tax,
                            data1.cgst_tax,
                            data1.igst_tax,
                            data1.utgst_tax,
                            total_sku_amt
                            ]
        else:
            po_temp_data = [data1.sku.wms_code, data1.supplier_code, data1.sku.sku_desc,
                            data1.order_quantity,
                            data1.measurement_unit,
                            data1.price, amount, data1.sgst_tax, data1.cgst_tax,
                            data1.igst_tax,
                            data1.utgst_tax,
                            total_sku_amt
                            ]
        if ean_flag:
            ean_number = 0
            eans = get_sku_ean_list(data1.sku)
            if eans:
                ean_number = eans[0]
            po_temp_data.insert(1, ean_number)
        if show_cess_tax:
            po_temp_data.insert(table_headers.index('CESS (%)'), data1.cess_tax)
        if show_apmc_tax:
            po_temp_data.insert(table_headers.index('APMC (%)'), data1.apmc_tax)
        po_data.append(po_temp_data)

        #mail_result_data = purchase_order_dict(data1, data_req, purchase_order, user, order)
    try:
        purchase_order = data1
        address = purchase_order.supplier.address
        address = '\n'.join(address.split(','))
        if purchase_order.ship_to:
            ship_to_address = purchase_order.ship_to
            company_address = user.userprofile.address
        else:
            ship_to_address, company_address = get_purchase_company_address(user.userprofile)
        wh_telephone = user.userprofile.wh_phone_number
        ship_to_address = '\n'.join(ship_to_address.split(','))
        vendor_name = ''
        vendor_address = ''
        vendor_telephone = ''
        if purchase_order.order_type == 'VR':
            vendor_address = purchase_order.vendor.address
            vendor_address = '\n'.join(vendor_address.split(','))
            vendor_name = purchase_order.vendor.name
            vendor_telephone = purchase_order.vendor.phone_number
        telephone = purchase_order.supplier.phone_number
        name = purchase_order.supplier.name
        order_id = ids_dict[supplier]
        supplier_email = purchase_order.supplier.email_id
        phone_no = purchase_order.supplier.phone_number
        gstin_no = purchase_order.supplier.tin_number
        po_exp_duration = purchase_order.supplier.po_exp_duration
        order_date = get_local_date(request.user, order.creation_date)
        if po_exp_duration:
            expiry_date = order.creation_date + datetime.timedelta(days=po_exp_duration)
        else:
            expiry_date = ''
        po_reference = '%s%s_%s' % (order.prefix, str(order.creation_date).split(' ')[0].replace('-', ''), order_id)
        profile = UserProfile.objects.get(user=user.id)
        company_name = profile.company_name
        title = 'Purchase Order'
        receipt_type = request.GET.get('receipt_type', '')
        if request.POST.get('seller_id', '') and 'shproc' in str(request.POST.get('seller_id').split(":")[1]).lower():
            company_name = 'SHPROC Procurement Pvt. Ltd.'
            title = 'Purchase Order'
        total_amt_in_words = number_in_words(round(total)) + ' ONLY'
        round_value = float(round(total) - float(total))
        company_logo = get_po_company_logo(user, COMPANY_LOGO_PATHS, request)
        iso_company_logo = get_po_company_logo(user, ISO_COMPANY_LOGO_PATHS, request)
        left_side_logo = get_po_company_logo(user, LEFT_SIDE_COMPNAY_LOGO, request)
        data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address.encode('ascii', 'ignore'),
                     'order_id': order_id,
                     'telephone': str(telephone), 'ship_to_address': ship_to_address.encode('ascii', 'ignore'),
                     'name': name, 'order_date': order_date, 'total': round(total), 'po_reference': po_reference,
                     'user_name': request.user.username, 'total_amt_in_words': total_amt_in_words,
                     'total_qty': total_qty, 'company_name': company_name, 'location': profile.location,
                     'w_address': ship_to_address.encode('ascii', 'ignore'),
                     'vendor_name': vendor_name, 'vendor_address': vendor_address.encode('ascii', 'ignore'),
                     'vendor_telephone': vendor_telephone, 'receipt_type': receipt_type, 'title': title,
                     'gstin_no': gstin_no, 'industry_type': user_profile.industry_type, 'expiry_date': expiry_date,
                     'wh_telephone': wh_telephone, 'wh_gstin': profile.gst_number, 'wh_pan': profile.pan_number,
                     'terms_condition': '',
                     'company_address': company_address.encode('ascii', 'ignore'),
                     'company_logo': company_logo, 'iso_company_logo': iso_company_logo,
                     'left_side_logo': left_side_logo}
        if round_value:
            data_dict['round_total'] = "%.2f" % round_value
        t = loader.get_template('templates/toggle/po_download.html')
        rendered = t.render(data_dict)
        if get_misc_value('raise_po', user.id) == 'true':
            write_and_mail_pdf(po_reference, rendered, request, user, supplier_email, phone_no, po_data,
                               str(order_date).split(' ')[0], ean_flag=ean_flag)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Purchase Order send mail failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
    for key, value in order_ids.iteritems():
        if value:
            check_purchase_order_created(user, value)
    return 'success'


def purchase_order_dict(data, data_req, purch, user, order):
    if data.supplier.name in data_req.keys():
        data_req[data.supplier.name].append(
            {'sku_code': data.sku.sku_code, 'price': data.price, 'quantity': data.order_quantity,
             'purch': purch, 'user': user, 'purchase_order': order})
    else:
        data_req[data.supplier.name] = [
            {'sku_code': data.sku.sku_code, 'price': data.price, 'quantity': data.order_quantity,
             'purch': purch, 'user': user, 'purchase_order': order}]
    return data_req


def purchase_upload_mail(request, data_to_send, user):
    from django.template import loader, Context
    from inbound import write_and_mail_pdf
    for key, value in data_to_send.iteritems():
        status = ''
        customization = ''
        supplier_code = ''
        supplier_mapping = SKUSupplier.objects.filter(sku_id=value[0]['purch'].sku_id,
                                                      supplier_id=value[0]['purch'].supplier_id,
                                                      sku__user=value[0]['user'].id)
        if supplier_mapping:
            supplier_code = supplier_mapping[0].supplier_code

        supplier = value[0]['purch'].supplier
        wms_code = value[0]['purch'].sku.wms_code
        telephone = supplier.phone_number
        name = supplier.name
        order_id = value[0]['purchase_order'].order_id
        supplier_email = supplier.email_id
        order_date = get_local_date(request.user, value[0]['purchase_order'].creation_date)
        address = '\n'.join(supplier.address.split(','))
        vendor_name = ''
        vendor_address, ship_to_address = '', ''
        vendor_telephone = ''
        if value[0]['purchase_order'].ship_to:
            ship_to_address = value[0]['purchase_order'].ship_to
        else:
            ship_to_address = user.userprofile.address
        ship_to_address = '\n'.join(ship_to_address.split(','))

        if value[0]['purch'].order_type == 'VR':
            vendor_address = value[0]['purch'].vendor.address
            vendor_address = '\n'.join(vendor_address.split(','))
            vendor_name = value[0]['purch'].vendor.name
            vendor_telephone = value[0]['purch'].vendor.phone_number

        po_reference = '%s%s_%s' % (value[0]['purchase_order'].prefix,
                                    str(value[0]['purchase_order'].creation_date).split(' ')[0].replace('-', ''),
                                    order_id)

        table_headers = ('WMS Code', 'Supplier Code', 'Description', 'Quantity', 'Unit Price', 'Amount')
        po_data = []

        amount = 0
        total = 0
        total_qty = 0
        for one_stat in value:
            amount = (one_stat['quantity']) * (one_stat['price'])
            total += amount
            total_qty += one_stat['quantity']
            po_data.append((one_stat['sku_code'], '', '', one_stat['quantity'], one_stat['price'],
                            one_stat['quantity'] * one_stat['price']))
        company_logo = get_po_company_logo(user, COMPANY_LOGO_PATHS, request)
        iso_company_logo = get_po_company_logo(user, ISO_COMPANY_LOGO_PATHS, request)
        left_side_logo = get_po_company_logo(user, LEFT_SIDE_COMPNAY_LOGO , request)
        profile = UserProfile.objects.get(user=request.user.id)
        t = loader.get_template('templates/toggle/po_download.html')
        w_address, company_address = get_purchase_company_address(profile)
        data_dictionary = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id,
                           'telephone': str(telephone), 'name': name, 'order_date': order_date, 'total': total,
                           'po_reference': po_reference, 'user_name': request.user.username, 'total_qty': total_qty,
                           'company_name': profile.company_name, 'location': profile.location,
                           'w_address': w_address, 'vendor_name': vendor_name,
                           'vendor_address': vendor_address, 'vendor_telephone': vendor_telephone,
                           'customization': customization, 'ship_to_address': ship_to_address,
                           'company_address': company_address, 'wh_gstin': profile.gst_number,
                           'company_logo': company_logo, 'iso_company_logo': iso_company_logo,'left_side_logo':left_side_logo}
        rendered = t.render(data_dictionary)
        write_and_mail_pdf(po_reference, rendered, request, user, supplier_email, telephone, po_data,
                           str(order_date).split(' ')[0])


@csrf_exempt
@login_required
@get_admin_user
def purchase_order_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
    except:
        return HttpResponse('Invalid File')
    status, data_list = validate_purchase_order(request, reader, user, no_of_rows, no_of_cols, fname, file_type)
    if status != 'Success':
        return HttpResponse(status)
    purchase_order_excel_upload(request, user, data_list)
    return HttpResponse('Success')


@csrf_exempt
def validate_move_inventory_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type):
    mapping_dict = {}
    index_status = {}
    location = {}
    data_list = []
    inv_mapping = get_move_inventory_excel_upload_headers(user)
    inv_res = dict(zip(inv_mapping.values(), inv_mapping.keys()))
    excel_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 inv_mapping)
    if not set(['wms_code', 'source', 'destination', 'quantity']).issubset(excel_mapping.keys()):
        return 'Invalid File'
    fields_mapping = {'quantity': 'Quantity', 'mrp': 'MRP'}
    number_fields = ['quantity', 'mrp']
    for row_idx in range(1, no_of_rows):
        data_dict = {}
        for key, value in excel_mapping.iteritems():
            cell_data = get_cell_data(row_idx, value, reader, file_type)
            if key == 'wms_code':
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(cell_data)
                sku_id = check_and_return_mapping_id(cell_data, "", user, False)
                if not sku_id:
                    index_status.setdefault(row_idx, set()).add('Invalid WMS Code')
                else:
                    data_dict['sku_id'] = sku_id
                    data_dict['wms_code'] = SKUMaster.objects.get(id=sku_id, user=user.id).wms_code
            elif key == 'source':
                if cell_data:
                    location_master = LocationMaster.objects.filter(zone__user=user.id, location=cell_data)
                    if not location_master:
                        index_status.setdefault(row_idx, set()).add('Invalid Source Location')
                    else:
                        data_dict[key] = location_master[0].location
                        data_dict['source_id'] = location_master[0].id
                    if location_master and sku_id:
                        source_stock = StockDetail.objects.filter(sku__user=user.id, location__location=cell_data,
                                                                  sku_id=sku_id)
                        if not source_stock:
                            index_status.setdefault(row_idx, set()).add('location not have the stock of wms code')
                else:
                    index_status.setdefault(row_idx, set()).add('Source Location should not be empty')
            elif key == 'destination':
                if cell_data:
                    dest_location = LocationMaster.objects.filter(zone__user=user.id, location=cell_data)
                    if not dest_location:
                        index_status.setdefault(row_idx, set()).add('Invalid Destination Location')
                    else:
                        data_dict[key] = dest_location[0].location
                        data_dict['destination_id'] = dest_location[0].id
                else:
                    index_status.setdefault(row_idx, set()).add('Destination Location should not be empty')
            elif key == 'seller_id':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Seller ID should not be empty')
                try:
                    seller_id = int(cell_data)
                    seller_master = SellerMaster.objects.filter(user=user.id, seller_id=seller_id)
                    if not seller_master:
                        index_status.setdefault(row_idx, set()).add('Invalid Seller ID')
                    else:
                        data_dict[key] = seller_master[0].seller_id
                        data_dict['seller_master_id'] = seller_master[0].id
                except:
                    index_status.setdefault(row_idx, set()).add('Invalid Seller ID')
            elif key == 'batch_no':
                if isinstance(cell_data, float):
                    cell_data = str(int(cell_data))
                    data_dict[key] = cell_data
            elif key in number_fields:
                if cell_data and (not isinstance(cell_data, (int, float)) or int(cell_data) < 0):
                    index_status.setdefault(row_idx, set()).add('Invalid %s' % fields_mapping[key])
                else:
                    data_dict[key] = cell_data
        if row_idx not in index_status:
            stock_dict = {"sku_id": data_dict['sku_id'],
                          "location_id": data_dict['source_id'],
                          "sku__user": user.id, "quantity__gt": 0}
            reserved_dict = {'stock__sku_id': data_dict['sku_id'], 'stock__sku__user': user.id,
                             'status': 1,
                             'stock__location_id': data_dict['source_id']}
            raw_reserved_dict = {'stock__sku_id': data_dict['sku_id'], 'stock__sku__user': user.id,
                             'status': 1,
                             'stock__location_id': data_dict['source_id']}
            if data_dict.get('batch_no', ''):
                stock_dict["batch_detail__batch_no"] = data_dict['batch_no']
                reserved_dict["stock__batch_detail__batch_no"] = data_dict['batch_no']
                raw_reserved_dict['stock__batch_detail__batch_no'] = data_dict['batch_no']
            if data_dict.get('mrp', ''):
                try:
                    mrp = data_dict['mrp']
                except:
                    mrp = 0
                stock_dict["batch_detail__mrp"] = mrp
                reserved_dict["stock__batch_detail__mrp"] = mrp
                raw_reserved_dict["stock__batch_detail__mrp"] = mrp
            if data_dict.get('seller_master_id', ''):
                stock_dict['sellerstock__seller_id'] = data_dict['seller_master_id']
                stock_dict['sellerstock__quantity__gt'] = 0
                reserved_dict["stock__sellerstock__seller_id"] = data_dict['seller_master_id']
                raw_reserved_dict["stock__sellerstock__seller_id"] = data_dict['seller_master_id']
            stocks = StockDetail.objects.filter(**stock_dict)
            if not stocks:
                index_status.setdefault(row_idx, set()).add('No Stocks Found')
            else:
                stock_count = stocks.aggregate(Sum('quantity'))['quantity__sum']
                reserved_quantity = PicklistLocation.objects.exclude(stock=None).filter(**reserved_dict).\
                                        aggregate(Sum('reserved'))['reserved__sum']
                raw_reserved_quantity = RMLocation.objects.exclude(stock=None).filter(**raw_reserved_dict).\
                                        aggregate(Sum('reserved'))['reserved__sum']
                if not reserved_quantity:
                    reserved_quantity = 0
                if not raw_reserved_quantity:
                    raw_reserved_quantity = 0
                avail_stock = stock_count - reserved_quantity - raw_reserved_quantity
                if avail_stock < float(data_dict['quantity']):
                    index_status.setdefault(row_idx, set()).add('Quantity Exceeding available quantity')
        data_list.append(data_dict)

    if not index_status:
        return 'Success', data_list

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name, data_list

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name, data_list


@csrf_exempt
@login_required
@get_admin_user
def move_inventory_upload(request, user=''):
    fname = request.FILES['files']
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
    except:
        return HttpResponse('Invalid File')
    status, data_list = validate_move_inventory_form(request, reader, user, no_of_rows,
                                                     no_of_cols, fname, file_type)
    if status != 'Success':
        return HttpResponse(status)
    cycle_count = CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
    if not cycle_count:
        cycle_id = 1
    else:
        cycle_id = cycle_count[0].cycle + 1
    mod_locations = []
    for data_dict in data_list:
        extra_dict = {}
        wms_code = data_dict['wms_code']
        source_loc = data_dict['source']
        dest_loc = data_dict['destination']
        quantity = data_dict['quantity']
        if data_dict.get('seller_id', ''):
            extra_dict['seller_id'] = data_dict['seller_id']
        if data_dict.get('batch_no', ''):
            extra_dict['batch_no'] = data_dict['batch_no']
        if data_dict.get('mrp', ''):
            extra_dict['mrp'] = data_dict['mrp']
        move_stock_location(cycle_id, wms_code, source_loc, dest_loc, quantity, user, **extra_dict)
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
            for s in filter(lambda x: sub_str in x, market_excel.keys()):
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

            for marketplace_code, marketplace_desc in zip(marketplace_excel['marketplace_code'],
                                                          marketplace_excel['description']):
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
                    market_sku_mapping = MarketplaceMapping.objects.filter(sku_type=marketplace_name,
                                                                           marketplace_code=key, sku__user=user.id)
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
                    # market_data.save()
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
                    index_status.setdefault(row_idx, set()).add('Invalid SKU Code %s' % material_sku)
            elif key == 'material_quantity':
                cell_data = open_sheet.cell(row_idx, bom_excel[key]).value
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Quantity Should be in integer or float')
                        # else:
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
            # bom = BOMMaster.objects.filter(product_sku__sku_code=product_sku, material_sku__sku_code=material_sku, product_sku__user=user)
            # if bom:
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
    bom_excel = {'product_sku': 0, 'material_sku': 1, 'material_quantity': 2, 'wastage_percent': 3,
                 'unit_of_measurement': 4}
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
        all_data[cond].append([float(material_quantity), uom, data_id, wastage_percent])
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
                if col_idx == 2 :
                    message = 'Combo Quantity value missing'
                index_status.setdefault(row_idx, set()).add(message)
                continue
            if col_idx == 2 :
                if not isinstance(cell_data, (int, float)):
                    message = 'Quantity must be Number'
                    index_status.setdefault(row_idx, set()).add(message)
            else:
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
            if col_idx == 2:
                quantity = float(cell_data)

        relation_data = {'relation_type': 'combo', 'member_sku': combo_data, 'parent_sku': sku_code , 'quantity' :quantity}
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
def validate_inventory_adjust_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type):
    index_status = {}
    data_list = []
    inv_mapping = get_inventory_adjustment_excel_upload_headers(user)
    excel_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 inv_mapping)
    if not set(['wms_code', 'location', 'quantity', 'reason']).issubset(excel_mapping.keys()):
        return 'Invalid File'
    for row_idx in range(1, no_of_rows):
        data_dict = {}
        for key, value in excel_mapping.iteritems():
            cell_data = get_cell_data(row_idx, value, reader, file_type)
            if key == 'wms_code':
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(xcode(cell_data))
                sku_master = SKUMaster.objects.filter(wms_code=cell_data, user=user.id)
                if not sku_master:
                    index_status.setdefault(row_idx, set()).add('Invalid WMS Code')
                else:
                    data_dict['sku_master'] = sku_master[0]
            elif key == 'location':
                if cell_data:
                    location_master = LocationMaster.objects.filter(zone__user=user.id, location=cell_data)
                    if not location_master:
                        index_status.setdefault(row_idx, set()).add('Invalid Location')
                    else:
                        data_dict['location_master'] = location_master[0]
                else:
                    index_status.setdefault(row_idx, set()).add('Location should not be empty')
            elif key == 'seller_id':
                if cell_data and isinstance(cell_data, (int, float)):
                    seller_master = SellerMaster.objects.filter(user=user.id, seller_id=cell_data)
                    if not seller_master:
                        index_status.setdefault(row_idx, set()).add('Seller Not Found')
                    else:
                        data_dict['seller_master'] = seller_master[0]
                else:
                    index_status.setdefault(row_idx, set()).add('Invalid Seller')
            elif key == 'quantity':
                try:
                    data_dict['quantity'] = float(cell_data)
                    if data_dict['quantity'] < 0:
                        index_status.setdefault(row_idx, set()).add('Invalid Quantity')
                except:
                    index_status.setdefault(row_idx, set()).add('Invalid Quantity')
            elif key == 'mrp':
                if cell_data:
                    try:
                        data_dict['mrp'] = float(cell_data)
                        if data_dict['mrp'] < 0:
                            index_status.setdefault(row_idx, set()).add('Invalid MRP')
                    except:
                        index_status.setdefault(row_idx, set()).add('Invalid MRP')
            else:
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                data_dict[key] = cell_data
        data_list.append(data_dict)

    if not index_status:
        return 'Success', data_list

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name, data_list

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name, data_list


    # if not index_status:
    #     return 'Success'
    # f_name = '%s.inventory_adjust_form.xls' % user
    # write_error_file(f_name, index_status, open_sheet, ADJUST_INVENTORY_EXCEL_HEADERS, 'Inventory Adjustment')
    # return f_name


@csrf_exempt
@login_required
@get_admin_user
def inventory_adjust_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
    except:
        return HttpResponse('Invalid File')

    status, data_list = validate_inventory_adjust_form(request, reader, user, no_of_rows, no_of_cols, fname,
                                                       file_type)

    if status != 'Success':
        return HttpResponse(status)
    sku_codes = []
    cycle_count = CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
    if not cycle_count:
        cycle_id = 1
    else:
        cycle_id = cycle_count[0].cycle + 1

    for final_dict in data_list:
        # location_data = ''
        wms_code = final_dict['sku_master'].wms_code
        loc = final_dict['location_master'].location
        quantity = final_dict['quantity']
        reason = final_dict['reason']
        seller_master_id, batch_no, mrp = '', '', 0
        if final_dict.get('seller_master', ''):
            seller_master_id = final_dict['seller_master'].id
        if final_dict.get('batch_no', ''):
            batch_no = final_dict['batch_no']
        if final_dict.get('mrp', 0):
            mrp = final_dict['mrp']
        adjust_location_stock(cycle_id, wms_code, loc, quantity, reason, user, batch_no=batch_no, mrp=mrp,
                              seller_master_id=seller_master_id)
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
    number_fields = {'credit_period': 'Credit Period', 'phone_number': 'Phone Number', 'pincode': 'PIN Code',
                     'phone': 'Phone Number', 'discount_percentage': 'Discount Percentage'}
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

            elif key == 'phone_number':
                if cell_data:
                    try:
                        cell_data = str(int(cell_data))
                    except:
                        cell_data = str(cell_data)

                    if len(cell_data) != 10:
                        index_status.setdefault(row_idx, set()).add('Phone Number should be in 10 digit')

            elif key in number_fields.keys():
                if cell_data:
                    try:
                        cell_data = float(cell_data)
                    except:
                        index_status.setdefault(row_idx, set()).add('%s Should be in number' % number_fields[key])

            elif key == 'price_type':
                if cell_data:
                    price_band_flag = get_misc_value('priceband_sync', user.id)
                    if price_band_flag == 'true':
                        admin_user = get_admin(user)
                        price_types = PriceMaster.objects.filter(sku__user=admin_user.id). \
                            values_list('price_type', flat=True).distinct()
                    else:
                        price_types = PriceMaster.objects.filter(sku__user=user.id).values_list('price_type',
                                                                                                flat=True).distinct()
                    if cell_data not in price_types:
                        index_status.setdefault(row_idx, set()).add('Invalid Selling Price Type')
            elif key == 'tax_type':
                if cell_data:
                    if cell_data not in TAX_TYPE_ATTRIBUTES.values():
                        index_status.setdefault(row_idx, set()).add('Invalid Tax Type')

    if not index_status:
        return 'Success'

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name


def customer_excel_upload(request, reader, user, no_of_rows, fname, file_type):
    mapping_dict = get_customer_master_mapping(reader, file_type)
    number_fields = ['credit_period', 'phone_number', 'pincode', 'phone', 'discount_percentage', 'markup']
    float_fields = ['discount_percentage', 'markup']
    rev_tax_types = dict(zip(TAX_TYPE_ATTRIBUTES.values(), TAX_TYPE_ATTRIBUTES.keys()))
    for row_idx in range(1, no_of_rows):
        if not mapping_dict:
            break
        customer_data = copy.deepcopy(CUSTOMER_DATA)
        customer_master = None
        for key, value in mapping_dict.iteritems():
            cell_data = get_cell_data(row_idx, mapping_dict[key], reader, file_type)
            # cell_data = open_sheet.cell(row_idx, mapping_dict[key]).value
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
                cell_data = str(re.sub(r'[^\x00-\x7F]+', '', cell_data))
                customer_data['name'] = cell_data
                if customer_master and cell_data:
                    customer_master.name = customer_data['name']
            elif key == 'tax_type':
                if cell_data:
                    cell_data = rev_tax_types.get(cell_data, '')
                customer_data['tax_type'] = cell_data
                if customer_master and cell_data:
                    customer_master.tax_type = customer_data['tax_type']
            elif key in number_fields:
                try:
                    if key in float_fields:
                        cell_data = float(cell_data)
                    else:
                        cell_data = int(cell_data)
                except:
                    pass
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
                        customer_data.pop(key)
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
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status = validate_customer_form(request, reader, user, no_of_rows, fname, file_type)
        if status != 'Success':
            return HttpResponse(status)

        customer_excel_upload(request, reader, user, no_of_rows, fname, file_type)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Customer Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Customer Upload Failed")

    return HttpResponse('Success')


@csrf_exempt
@login_required
@get_admin_user
def sales_returns_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status = validate_sales_return_form(request, reader, user, no_of_rows, fname, file_type=file_type)
        if status != 'Success':
            return HttpResponse(status)

        upload_status = sales_returns_csv_xls_upload(request, reader, user, no_of_rows, fname, file_type=file_type)
        return HttpResponse('Success')
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Sales Return Upload failed for %s and params are %s and error statement is %s' % (str(user.username),
                                                                                                    str(
                                                                                                        request.POST.dict()),
                                                                                                    str(e)))
        return HttpResponse("Sales Return Upload Failed")


@csrf_exempt
def validate_sales_return_form(request, reader, user, no_of_rows, fname, file_type='xls'):
    sku_data = []
    wms_data = []
    index_status = {}
    order_mapping = get_sales_returns_mapping(reader, file_type, user)
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
                sku_code = str(xcode(cell_data))
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
                        # elif int(order_detail[0].status) == 4:
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
                    return_obj = OrderReturns.objects.filter(return_id=return_cod, sku__sku_code=sku_cod,
                                                             sku__user=user.id)
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

                order_id_search = ''.join(re.findall('\d+', order_id))
                order_code_search = ''.join(re.findall('\D+', order_id))
                if sor_id:
                    seller_order = SellerOrder.objects.filter(
                        Q(order__order_id=order_id_search, order__order_code=order_code_search) |
                        Q(order__original_order_id=order_id), sor_id=sor_id,
                        order__sku__sku_code=sku_code, order__user=user.id)
                    if not seller_order:
                        index_status.setdefault(row_idx, set()).add('Invalid Sor ID')
                else:
                    index_status.setdefault(row_idx, set()).add('SOR ID is mandatory')

    if not index_status:
        return 'Success'

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name


def sales_returns_csv_xls_upload(request, reader, user, no_of_rows, fname, file_type='xls'):
    from inbound import save_return_locations
    index_status = {}
    order_mapping = get_sales_returns_mapping(reader, file_type, user)
    count = 1

    for row_idx in range(1, no_of_rows):
        all_data = []
        order_data = copy.deepcopy(UPLOAD_SALES_ORDER_DATA)
        if not order_mapping:
            break
        for key, value in order_mapping.iteritems():
            if key == 'sku_id':
                sku_code = ""
                if isinstance(value, list):
                    for item in value:
                        if isinstance(get_cell_data(row_idx, item, reader, file_type), float):
                            content = int(get_cell_data(row_idx, item, reader, file_type))
                        sku_code = "%s%s" % (sku_code, get_cell_data(row_idx, item, reader, file_type))
                else:
                    sku_code = get_cell_data(row_idx, order_mapping[key], reader, file_type)
                    if isinstance(sku_code, float):
                        sku_code = str(int(sku_code))
                    sku_code = str(xcode(sku_code))
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
                seller_order = ''
                if sor_id:
                    seller_order = get_returns_seller_order_id(order_data['order_id'], sku_code, user, sor_id=sor_id)
                if seller_order:
                    order_data[key] = seller_order.id
                    order_data['seller_id'] = seller_order.seller_id
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
            # if order_data.get('seller_order_id', '') and 'order_id' in order_data.keys():
            #    del order_data['order_id']
            returns = OrderReturns(**order_data)
            returns.save()
            if order_data.get('seller_order_id', ''):
                SellerOrder.objects.filter(id=order_data['seller_order_id']).update(status=4)

            if not returns.return_id:
                returns.return_id = 'MN%s' % returns.id
            returns.save()

            if not order_data.get('seller_order_id', ''):
                save_return_locations([returns], all_data, order_data['damaged_quantity'], request, user)
    return 'Success'


def get_sales_returns_mapping(reader, file_type, user):
    order_mapping = {}
    if get_cell_data(0, 0, reader, file_type) == 'Return ID':
        order_mapping = copy.deepcopy(GENERIC_RETURN_EXCEL)
        if user.userprofile.user_type == 'marketplace_user':
            order_mapping['seller_order_id'] = 7
    elif get_cell_data(0, 0, reader, file_type) == 'GatePass No':
        order_mapping = copy.deepcopy(MYNTRA_RETURN_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'Sale Order Item Code':
        order_mapping = copy.deepcopy(UNIWEAR_RETURN_EXCEL)
    elif get_cell_data(0, 0, reader, file_type) == 'SOR ID' and get_cell_data(0, 1, reader, file_type) == 'UOR ID':
        order_mapping = copy.deepcopy(SHOTANG_RETURN_EXCEL)
    return order_mapping


def sales_return_order(data, user):
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
    excel_records_map = {}
    for row_idx in range(1, no_of_rows):
        if not price_file_mapping:
            continue

        each_row_map = copy.deepcopy(PRICE_DEF_EXCEL)
        for key, value in price_file_mapping.iteritems():
            each_row_map[key] = get_cell_data(row_idx, value, reader, file_type)

        sku_code, price_type = each_row_map['sku_id'], each_row_map['price_type']
        max_amount, min_amount = each_row_map['max_unit_range'], each_row_map['min_unit_range']
        discount, price = each_row_map['discount'], each_row_map['price']
        excel_records_map.setdefault((user, sku_code, price_type), []).append((min_amount, max_amount, price, discount))

    for key, vals in excel_records_map.iteritems():
        user, sku_code, price_type = key
        if isinstance(sku_code, float):
            sku_code = str(int(sku_code))
        price_obj = PriceMaster.objects.filter(sku__user=user.id, sku__sku_code=sku_code, price_type=price_type)
        if price_obj:
            price_obj.delete()

        sku_data = SKUMaster.objects.filter(wms_code=sku_code, user=user.id)
        if sku_data:
            each_row_map['sku_id'] = sku_data[0].id

        for val in vals:
            min_amount, max_amount, price, discount = val

            if not discount:
                each_row_map['discount'] = 0

            if not min_amount:
                min_amount = 0
            if not max_amount:
                max_amount = 0
            each_row_map['max_unit_range'] = max_amount
            each_row_map['min_unit_range'] = min_amount
            each_row_map['price'] = price
            each_row_map['price_type'] = price_type
            try:
                price_master = PriceMaster(**each_row_map)
                price_master.save()
            except:
                import traceback
                log.debug(traceback.format_exc())
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
                    cell_data = str(xcode(cell_data))
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

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
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


@csrf_exempt
def validate_network_form(request, reader, no_of_rows, fname, user, file_type='xls'):
    index_status = {}
    network_file_mapping = copy.deepcopy(NETWORK_DEF_EXCEL)
    if not network_file_mapping:
        return 'Invalid File'
    warehouse_users = UserGroups.objects.filter(admin_user=user.id).values_list('user_id__username', flat=True)
    price_band_flag = get_misc_value('priceband_sync', user.id)
    if price_band_flag == 'true':
        admin_user = get_admin(user)
        price_types = PriceMaster.objects.filter(sku__user=admin_user.id). \
            values_list('price_type', flat=True).distinct()
    else:
        price_types = PriceMaster.objects.filter(sku__user=user.id).values_list('price_type',
                                                                                flat=True).distinct()
    for row_idx in range(1, no_of_rows):
        for key, value in network_file_mapping.iteritems():
            cell_data = get_cell_data(row_idx, network_file_mapping[key], reader, file_type)
            if key == 'dest_location_code':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add("Destination Location Code Missing")
                else:
                    if cell_data not in warehouse_users:
                        index_status.setdefault(row_idx, set()).add('Create Destination Location Code first.')
            elif key == 'source_location_code':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add("Source Location Code Missing")
                else:
                    if cell_data not in warehouse_users:
                        index_status.setdefault(row_idx, set()).add('Create Source Location Code first.')
            elif key == 'lead_time':
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Invalid Lead Time')
                else:
                    index_status.setdefault(row_idx, set()).add('Lead Time Missing')
            elif key == 'sku_stage':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Sku Stage Missing')
            elif key == 'priority':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Priority Missing')
            elif key == 'price_type':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Price Type is Missing')
                else:
                    if cell_data not in price_types:
                        index_status.setdefault(row_idx, set()).add('Invalid Price Type')
            elif key == 'charge_remarks':
                remarks_list = [i[0] for i in REMARK_CHOICES]
                if cell_data and cell_data not in remarks_list:
                    index_status.setdefault(row_idx, set()).add('Unknown Remarks')
            else:
                index_status.setdefault(row_idx, set()).add('Invalid Field')

    if not index_status:
        return 'Success'

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name


def network_excel_upload(request, reader, no_of_rows, file_type='xls', user=''):
    users_map = dict(UserGroups.objects.filter(admin_user=user).values_list('user__username', 'user_id'))
    network_file_mapping = copy.deepcopy(NETWORK_DEF_EXCEL)
    for row_idx in range(1, no_of_rows):
        if not network_file_mapping:
            continue
        each_row_map = copy.deepcopy(NETWORK_DEF_EXCEL)
        for key, value in network_file_mapping.iteritems():
            each_row_map[key] = get_cell_data(row_idx, value, reader, file_type)

        dest_lc_code = users_map[each_row_map.pop('dest_location_code')]
        src_lc_code = users_map[each_row_map.pop('source_location_code')]
        sku_stage = each_row_map['sku_stage']
        network_obj = NetworkMaster.objects.filter(dest_location_code=dest_lc_code, source_location_code=src_lc_code,
                                                   sku_stage=sku_stage)
        if not network_obj:
            each_row_map['dest_location_code_id'] = dest_lc_code
            each_row_map['source_location_code_id'] = src_lc_code
            network_master = NetworkMaster(**dict(each_row_map))
            supplier = create_network_supplier(dest_lc_code, src_lc_code)
            network_master.supplier_id = supplier.id
            network_master.save()
        else:
            network_obj[0].lead_time = each_row_map['lead_time']
            network_obj[0].priority = each_row_map['priority']
            network_obj[0].price_type = each_row_map['price_type']
            network_obj[0].remarks = each_row_map['charge_remarks']
            network_obj[0].save()

    return 'success'


@get_admin_user
def network_master_upload(request, user=''):
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

    status = validate_network_form(request, reader, no_of_rows, fname, user, file_type=file_type)
    if status != 'Success':
        return HttpResponse(status)

    network_excel_upload(request, reader, no_of_rows, file_type=file_type, user=user)

    return HttpResponse('Success')


def get_order_lable_mapping(reader, file_type):
    label_mapping = {}
    if get_cell_data(0, 1, reader, file_type) == 'ItemCode' and get_cell_data(0, 7, reader, file_type) == 'mrp':
        label_mapping = copy.deepcopy(MYNTRA_LABEL_EXCEL_MAPPING)
    elif get_cell_data(0, 1, reader, file_type) == 'SKU Code' and get_cell_data(0, 2, reader, file_type) == 'Label':
        label_mapping = copy.deepcopy(ORDER_LABEL_EXCEL_MAPPING)
    elif get_cell_data(0, 1, reader, file_type) == 'ItemCode' and get_cell_data(0, 8, reader, file_type) == 'mrp':
        label_mapping = copy.deepcopy(MYNTRA_LABEL_EXCEL_MAPPING1)

    return label_mapping


@csrf_exempt
def validate_and_insert_order_labels(request, reader, user, no_of_rows, fname, file_type='xls'):
    sku_data = []
    wms_data = []
    index_status = {}

    label_mapping = get_order_lable_mapping(reader, file_type)
    if not label_mapping:
        return 'Invalid File'

    save_records = []
    order_objs = []
    all_order_objs = OrderDetail.objects.filter(user=user.id)
    for row_idx in range(1, no_of_rows):
        label_mapping_dict = {}
        search_params = {'user': user.id}
        for key, value in label_mapping.iteritems():
            cell_data = get_cell_data(row_idx, label_mapping[key], reader, file_type)

            if key == 'sku_code':
                if cell_data:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    cell_data = str(xcode(cell_data))
                    sku_code_id = check_and_return_mapping_id(cell_data, '', user)
                    if not sku_code_id:
                        index_status.setdefault(row_idx, set()).add('Invalid SKU Code')
                    else:
                        search_params['sku_id'] = sku_code_id
                    label_mapping_dict['item_sku'] = cell_data
                else:
                    index_status.setdefault(row_idx, set()).add('SKU Code missing')
            elif key == 'order_id':
                if cell_data:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    cell_data = str(xcode(cell_data))
                    order_objs = get_order_detail_objs(cell_data, user, search_params=search_params,
                                                       all_order_objs=all_order_objs)
                    if not order_objs:
                        index_status.setdefault(row_idx, set()).add('Invalid Order ID')
                    else:
                        label_mapping_dict['order_id'] = order_objs[0].id
                else:
                    index_status.setdefault(row_idx, set()).add('Order ID missing')

            elif key == 'label':
                if cell_data:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    cell_data = str(xcode(cell_data))
                    if order_objs:
                        order_label_objs = OrderLabels.objects.filter(
                            order_id__in=order_objs.values_list('id', flat=True))
                        if order_label_objs:
                            index_status.setdefault(row_idx, set()).add('Order Label Mapping Already exists')
                        else:
                            label_mapping_dict['label'] = cell_data
                else:
                    index_status.setdefault(row_idx, set()).add('Label Missing')
            elif key == 'mrp':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('MRP is mandatory')
                else:
                    try:
                        label_mapping_dict[key] = float(cell_data)
                    except:
                        index_status.setdefault(row_idx, set()).add('MRP should be in number')
            elif key == 'size':
                if cell_data:
                    try:
                        label_mapping_dict[key] = float(cell_data)
                    except:
                        label_mapping_dict[key] = cell_data
            else:
                label_mapping_dict[key] = cell_data
        if not index_status:
            save_records.append(OrderLabels(**label_mapping_dict))

    if not index_status:
        OrderLabels.objects.bulk_create(save_records)
        return 'Success'

    if index_status:
        f_name = generate_error_excel(index_status, fname, reader, file_type)
        return f_name


@csrf_exempt
@login_required
@get_admin_user
def order_label_mapping_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status = validate_and_insert_order_labels(request, reader, user, no_of_rows, fname, file_type=file_type)
        return HttpResponse(status)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Order Label Mapping Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Order Label Mapping Upload Failed")


def get_order_serial_mapping(reader, file_type):
    order_mapping = {}
    if get_cell_data(0, 2, reader, file_type) == 'Uor ID' and get_cell_data(0, 3, reader, file_type) == 'PO Number':
        order_mapping = copy.deepcopy(ORDER_SERIAL_EXCEL_MAPPING)

    return order_mapping


def validate_order_serial_mapping(request, reader, user, no_of_rows, fname, file_type='xls', no_of_cols=0):
    log.info("order upload started")
    st_time = datetime.datetime.now()
    index_status = {}

    order_mapping = get_order_serial_mapping(reader, file_type)
    if not order_mapping:
        return 'Invalid File'

    count = 0
    log.info("Validation Started %s" % datetime.datetime.now())
    final_data_dict = OrderedDict()
    order_po_mapping = []
    for row_idx in range(1, no_of_rows):
        if not order_mapping:
            break

        count += 1
        order_details = {'user': user.id, 'creation_date': datetime.datetime.now(),
                         'shipment_date': datetime.datetime.now(), 'status': 1,
                         'sku_id': ''}
        seller_order_details = {'creation_date': datetime.datetime.now(), 'status': 1}
        customer_order_summary = {'issue_type': 'order', 'creation_date': datetime.datetime.now()}

        sku_code = ''
        seller_id = ''
        for key, val in order_mapping.iteritems():
            value = get_cell_data(row_idx, order_mapping[key], reader, file_type)
            if key == 'order_id':
                if not value:
                    index_status.setdefault(count, set()).add('Order Id should not be empty')
                if isinstance(value, float):
                    value = str(int(value))
                original_order_id = value
                order_code = ''.join(re.findall('\D+', original_order_id))
                order_id = ''.join(re.findall('\d+', original_order_id))
                order_details['original_order_id'] = value
                order_details['order_id'] = order_id
                order_details['order_code'] = order_code
            elif key == 'sku_code':
                if isinstance(value, float):
                    value = str(int(value))
                if not value:
                    index_status.setdefault(count, set()).add('SKU Code should not be empty')
                elif value:
                    sku_id = check_and_return_mapping_id(value, '', user)
                    if not sku_id:
                        index_status.setdefault(count, set()).add('Invalid SKU Code')
                    else:
                        sku_code = value
                        order_details['sku_id'] = sku_id
                        order_details['title'] = SKUMaster.objects.get(id=sku_id).sku_desc
                        # original_order_id = str(original_order_id)+"<<>>"+SKUMaster.objects.get(id=sku_id).sku_code
            elif key == 'seller_id':
                seller_id = value
                seller_master = None
                if not seller_id:
                    index_status.setdefault(count, set()).add('Seller ID should not be empty')
                else:
                    if isinstance(seller_id, float):
                        seller_id = int(seller_id)
                    seller_master = SellerMaster.objects.filter(user=user.id, seller_id=seller_id)
                    if not seller_master:
                        index_status.setdefault(count, set()).add('Invalid Serial ID')
                if seller_master:
                    seller_order_details['seller_id'] = seller_master[0].id
                    seller_order_details['sor_id'] = str(seller_master[0].seller_id) + '-' + str(original_order_id)
            elif key == 'customer_id':
                customer_master = None
                if value:
                    if isinstance(value, float):
                        value = int(value)
                    customer_master = CustomerMaster.objects.filter(user=user.id, customer_id=value)
                    if not customer_master:
                        index_status.setdefault(count, set()).add('Invalid Customer ID')
                if customer_master:
                    order_details['customer_id'] = customer_master[0].customer_id
                    order_details['customer_name'] = customer_master[0].name
                    order_details['address'] = customer_master[0].address
            elif key == 'quantity':
                if not value:
                    index_status.setdefault(count, set()).add('Quantity should not be empty')
                elif not isinstance(value, (int, float)):
                    index_status.setdefault(count, set()).add('Quantity should Number')
                elif not float(value) > 0:
                    index_status.setdefault(count, set()).add('Quantity should be greater than Zero')
                else:
                    order_details['quantity'] = value
                    seller_order_details['quantity'] = value
            elif key == 'unit_price':
                try:
                    value = float(value)
                except:
                    value = 0
                order_details['unit_price'] = value
            elif key in ['cgst_tax', 'sgst_tax', 'igst_tax']:
                try:
                    value = float(value)
                except:
                    value = 0
                customer_order_summary[key] = value
                amount = float(order_details.get('quantity', 0)) * float(order_details['unit_price'])
                if not order_details.has_key('invoice_amount'):
                    order_details['invoice_amount'] = amount
                order_details['invoice_amount'] = order_details['invoice_amount'] + (amount * (float(value) / 100))
            elif key == 'po_number':
                if '_' in str(value):
                    try:
                        value = int(value.split('_')[-1])
                    except:
                        value = 0
                if isinstance(value, float):
                    value = int(value)
                if not isinstance(value, int):
                    index_status.setdefault(count, set()).add('Invalid PO Number')
                if order_details.get('sku_id', ''):
                    po_imei_mapping = POIMEIMapping.objects.filter(
                        sku_id=order_details['sku_id'], status=1,
                        sku__user=user.id, purchase_order__order_id=value)
                    if not po_imei_mapping:
                        index_status.setdefault(count, set()).add('Invalid PO Number')
                    else:
                        order_po_mapping.append({'order_id': original_order_id, 'sku_id': order_details['sku_id'],
                                                 'purchase_order_id': value,
                                                 'status': 1})
            elif key == 'order_type':
                if value not in ['Transit', 'Normal']:
                    index_status.setdefault(count, set()).add('Invalid Order Type')
                else:
                    order_details['order_type'] = value

        if order_details.get('sku_id', ''):
            order_detail_obj = OrderDetail.objects.filter(Q(original_order_id=order_details['original_order_id']) |
                                                          Q(order_id=order_details['order_id'],
                                                            order_code=order_details['order_code']),
                                                          sku_id=order_details['sku_id'], user=user.id)
            if order_detail_obj:
                index_status.setdefault(count, set()).add('Order Exists Already')
        group_key = str(original_order_id) + ":" + str(sku_code) + ":" + str(seller_id)
        final_data_dict = check_and_add_dict(group_key, 'order_details', order_details, final_data_dict=final_data_dict)
        final_data_dict = check_and_add_dict(group_key, 'seller_order_dict', seller_order_details,
                                             final_data_dict=final_data_dict)
        final_data_dict = check_and_add_dict(group_key, 'order_summary_dict', customer_order_summary,
                                             final_data_dict=final_data_dict)
        log.info("Order Saving Started %s" % (datetime.datetime.now()))

    if index_status:
        f_name = generate_error_excel(index_status, fname, reader, file_type)
        return f_name

    status = update_order_dicts(final_data_dict, user=user)
    for order_po in order_po_mapping:
        OrderPOMapping.objects.create(**order_po)

    return 'Success'


@csrf_exempt
@login_required
@get_admin_user
def order_serial_mapping_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status = validate_order_serial_mapping(request, reader, user, no_of_rows, fname, file_type=file_type)
        return HttpResponse(status)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Order Serial Mapping Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Order Serial Mapping Upload Failed")


def get_po_serial_mapping(reader, file_type):
    order_mapping = {}
    if get_cell_data(0, 0, reader, file_type) == 'Supplier ID' and get_cell_data(0, 2, reader, file_type) == 'Location':
        order_mapping = copy.deepcopy(PO_SERIAL_EXCEL_MAPPING)

    return order_mapping


def validate_po_serial_mapping(request, reader, user, no_of_rows, fname, file_type='xls', no_of_cols=0):
    log.info("po serial upload started")
    st_time = datetime.datetime.now()
    index_status = {}

    order_mapping = get_po_serial_mapping(reader, file_type)
    if not order_mapping:
        return 'Invalid File'

    count = 0
    log.info("Validation Started %s" % datetime.datetime.now())
    final_data_dict = OrderedDict()
    all_imeis = []
    for row_idx in range(1, no_of_rows):
        if not order_mapping:
            break

        count += 1
        po_details = {'status': 'confirmed-putaway', 'creation_date': datetime.datetime.now()}
        po_imei_details = {'creation_date': datetime.datetime.now(), 'status': 1}
        sku_code = ''
        supplier_id = ''
        for key, val in order_mapping.iteritems():
            value = get_cell_data(row_idx, order_mapping[key], reader, file_type)

            if key == 'sku_code':
                if isinstance(value, float):
                    value = str(int(value))
                if not value:
                    index_status.setdefault(count, set()).add('SKU Code should not be empty')
                elif value:
                    sku_id = check_and_return_mapping_id(value, '', user)
                    if not sku_id:
                        index_status.setdefault(count, set()).add('Invalid SKU Code')
                    else:
                        sku_code = value
                        po_details['sku_id'] = sku_id

            elif key == 'supplier_id':
                supplier_id = value
                supplier_master = None
                if not supplier_id:
                    index_status.setdefault(count, set()).add('Supplier ID should not be empty')
                else:
                    if isinstance(supplier_id, float):
                        supplier_id = int(supplier_id)
                    supplier_master = SupplierMaster.objects.filter(user=user.id, id=supplier_id)
                    if not supplier_master:
                        index_status.setdefault(count, set()).add('Invalid Supplier ID')
                if supplier_master:
                    po_details['supplier_id'] = supplier_master[0].id

            elif key == 'location':
                location_master = None
                if not value:
                    index_status.setdefault(count, set()).add('Location should not be empty')
                else:
                    if isinstance(value, float):
                        value = int(value)
                    location_master = LocationMaster.objects.filter(zone__user=user.id, location=value)
                    if not location_master:
                        index_status.setdefault(count, set()).add('Invalid Location')
                if location_master:
                    po_details['location_id'] = location_master[0].id

            elif key == 'unit_price':
                try:
                    value = float(value)
                except:
                    value = 0
                po_details['unit_price'] = value

            elif key == 'imei_number':
                imei_number = ''
                try:
                    imei_number = str(int(value))
                except:
                    imei_number = str(value)
                if not imei_number:
                    index_status.setdefault(count, set()).add('Serial Number is Mandatory')
                elif imei_number in all_imeis:
                    index_status.setdefault(count, set()).add('Duplicate Serial Number')
                else:
                    all_imeis.append(imei_number)
                    po_mapping, c_status, c_data = check_get_imei_details(imei_number, sku_code, user.id,
                                                                          check_type='purchase_check', order='')
                    if c_status:
                        index_status.setdefault(count, set()).add(c_status)

        group_key = str(supplier_id) + ':' + str(sku_code)
        final_data_dict = check_and_add_dict(group_key, 'po_details', po_details, final_data_dict=final_data_dict)
        final_data_dict = check_and_add_dict(group_key, 'imei_list', [imei_number], final_data_dict=final_data_dict,
                                             is_list=True)
        # log.info("Order Saving Started %s" %(datetime.datetime.now()))

    if index_status:
        f_name = generate_error_excel(index_status, fname, reader, file_type)
        return f_name

    create_po_serial_mapping(final_data_dict, user)
    return 'Success'


def create_po_serial_mapping(final_data_dict, user):
    order_id_dict = {}
    receipt_number = get_stock_receipt_number(user)
    NOW = datetime.datetime.now()
    user_profile = UserProfile.objects.get(user_id=user.id)
    log.info('PO Serial Mapping data for ' + user.username + ' is ' + str(final_data_dict))
    mod_locations = []
    po_sub_user_prefix = get_misc_value('po_sub_user_prefix', user.id)
    for key, value in final_data_dict.iteritems():
        quantity = len(value['imei_list'])
        po_details = value['po_details']
        location_master = LocationMaster.objects.get(id=po_details['location_id'], zone__user=user.id)
        sku = SKUMaster.objects.get(id=po_details['sku_id'], user=user.id)
        open_po_dict = {'creation_date': NOW, 'order_quantity': quantity,
                        'price': po_details['unit_price'], 'status': 0, 'sku_id': po_details['sku_id'],
                        'supplier_id': po_details['supplier_id'], 'measurement_unit': sku.measurement_type}
        open_po_obj = OpenPO(**open_po_dict)
        open_po_obj.save()
        order_id = order_id_dict.get(po_details['supplier_id'], '')
        if not order_id:
            order_id = get_purchase_order_id(user) + 1
            if po_sub_user_prefix == 'true':
                order_id = update_po_order_prefix(user, order_id)
            order_id_dict[po_details['supplier_id']] = order_id
        purchase_order_dict = {'open_po_id': open_po_obj.id, 'received_quantity': quantity, 'saved_quantity': 0,
                               'po_date': NOW, 'status': po_details['status'], 'prefix': user_profile.prefix,
                               'order_id': order_id, 'creation_date': NOW}
        purchase_order = PurchaseOrder(**purchase_order_dict)
        purchase_order.save()
        imei_nos = ','.join(value['imei_list'])
        insert_po_mapping(imei_nos, purchase_order, user.id)

        po_location_dict = {'creation_date': NOW, 'status': 0, 'quantity': 0, 'original_quantity': quantity,
                            'location_id': po_details['location_id'], 'purchase_order_id': purchase_order.id}
        po_location = POLocation(**po_location_dict)
        po_location.save()
        stock_dict = StockDetail.objects.create(receipt_number=receipt_number, receipt_date=NOW, quantity=quantity,
                                                status=1, location_id=po_details['location_id'],
                                                sku_id=po_details['sku_id'],
                                                receipt_type='purchase order', creation_date=NOW)
        # SKU Stats
        save_sku_stats(user, stock_dict.sku_id, purchase_order.id, 'po', quantity, stock_dict)
        mod_locations.append(location_master.location)

    for key, value in order_id_dict.iteritems():
        if value:
            check_purchase_order_created(user, value)
    if mod_locations:
        update_filled_capacity(mod_locations, user.id)


@csrf_exempt
@login_required
@get_admin_user
def po_serial_mapping_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status = validate_po_serial_mapping(request, reader, user, no_of_rows, fname, file_type=file_type)
        return HttpResponse(status)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('PO Serial Mapping Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("PO Serial Mapping Upload Failed")


def get_job_order_mapping(reader, file_type):
    order_mapping = {}
    if get_cell_data(0, 0, reader, file_type) == 'Product SKU Code' and get_cell_data(0, 1, reader,
                                                                                      file_type) == 'Product SKU Quantity':
        order_mapping = copy.deepcopy(JOB_ORDER_EXCEL_MAPPING)

    return order_mapping


def validate_job_order(request, reader, user, no_of_rows, fname, file_type='xls', no_of_cols=0):
    log.info("Job order upload started")
    st_time = datetime.datetime.now()
    index_status = {}

    order_mapping = get_job_order_mapping(reader, file_type)
    if not order_mapping:
        return 'Invalid File'

    count = 0
    log.info("Validation Started %s" % datetime.datetime.now())
    all_data_list = []
    duplicate_products = []
    for row_idx in range(1, no_of_rows):
        if not order_mapping:
            break

        count += 1
        sku_code = ''

        job_order_dict = {}
        for key, val in order_mapping.iteritems():
            value = get_cell_data(row_idx, order_mapping[key], reader, file_type)

            if key == 'product_code':
                if isinstance(value, float):
                    value = str(int(value))
                if not value:
                    index_status.setdefault(count, set()).add('Product Code should not be empty')
                elif value:
                    sku_id = check_and_return_mapping_id(value, '', user)
                    if not sku_id:
                        index_status.setdefault(count, set()).add('Invalid Product Code')
                    else:
                        sku_master = SKUMaster.objects.get(id=sku_id)
                        if not sku_master.sku_type in ['FG', 'RM']:
                            index_status.setdefault(count, set()).add('Product code sku type should be FG or RM')
                        sku_code = value
                        job_order_dict['product_code_id'] = sku_id
                        bom_master = BOMMaster.objects.filter(product_sku__user=user.id, product_sku__sku_code=sku_code)
                        if bom_master:
                            job_order_dict['bom_objs'] = bom_master
                        else:
                            index_status.setdefault(count, set()).add('BOM Master is not defined')
                        if not sku_code in duplicate_products:
                            duplicate_products.append(sku_code)
                        else:
                            index_status.setdefault(count, set()).add('Product Code repeated in File')

            elif key == 'product_quantity':
                try:
                    value = float(value)
                except:
                    value = 0
                if value:
                    job_order_dict['product_quantity'] = value
                else:
                    index_status.setdefault(count, set()).add('Product Quantity should be number')

        all_data_list.append(job_order_dict)

    if index_status:
        f_name = generate_error_excel(index_status, fname, reader, file_type)
        return f_name

    create_job_order_bulk(all_data_list, user)
    return 'Success'


def create_job_order_bulk(all_data_list, user):
    jo_reference = get_jo_reference(user.id)
    NOW = datetime.datetime.now()
    for data_dict in all_data_list:
        job_order = JobOrder.objects.create(product_code_id=data_dict['product_code_id'],
                                            product_quantity=data_dict['product_quantity'],
                                            jo_reference=jo_reference, job_code=0, status='open', creation_date=NOW)

        for bom_obj in data_dict['bom_objs']:
            unit_material = float(bom_obj.material_quantity) + (
            (float(bom_obj.material_quantity) / 100) * float(bom_obj.wastage_percent))
            material_quantity = unit_material * float(data_dict['product_quantity'])
            measurement_type = bom_obj.unit_of_measurement.upper()
            JOMaterial.objects.create(material_code_id=bom_obj.material_sku_id, material_quantity=material_quantity,
                                      job_order_id=job_order.id, unit_measurement_type=measurement_type,
                                      creation_date=NOW,
                                      status=1)


@csrf_exempt
@login_required
@get_admin_user
def job_order_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status = validate_job_order(request, reader, user, no_of_rows, fname, file_type=file_type)
        return HttpResponse(status)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Job Order Upload failed for %s and params are %s and error statement is %s' % (str(user.username),
                                                                                                 str(
                                                                                                     request.POST.dict()),
                                                                                                 str(e)))
        return HttpResponse("Job Order Upload Failed")


def validate_save_marketplace_serial(request, reader, user, no_of_rows, fname, file_type='xls', no_of_cols=0):
    log.info("Marketplace Serial Order upload started")
    st_time = datetime.datetime.now()
    index_status = {}

    order_mapping = {}
    if get_cell_data(0, 0, reader, file_type) == 'Order Reference' and get_cell_data(0, 2, reader,
                                                                                     file_type) == 'Serial Number':
        order_mapping = copy.deepcopy(MARKETPLACE_SERIAL_EXCEL_MAPPING)
    if not order_mapping:
        return 'Invalid File'

    count = 0
    log.info("Validation Started %s" % datetime.datetime.now())
    all_data_list = []
    for row_idx in range(1, no_of_rows):
        count += 1

        serial_dict = {}
        for key, val in order_mapping.iteritems():
            serial_dict[key] = get_cell_data(row_idx, order_mapping[key], reader, file_type)

        # Order Reference Validation
        if not serial_dict.get('order_reference', ''):
            index_status.setdefault(count, set()).add('Order Reference should not be empty')
        elif isinstance(serial_dict['order_reference'], float):
            serial_dict['order_reference'] = str(int(serial_dict['order_reference']))

        # Serial Number Validation
        if not serial_dict.get('serial_number', ''):
            index_status.setdefault(count, set()).add('Serial Number should not be empty')
        else:
            if isinstance(serial_dict['serial_number'], float):
                serial_dict['serial_number'] = str(int(serial_dict['serial_number']))
            po_mapping, serial_status, serial_data = check_get_imei_details(serial_dict['serial_number'], '', user.id,
                                                                            check_type='shipped_check', order='')
            if serial_data.get('order_imei_obj', ''):
                serial_dict['order_imei_obj'] = serial_data['order_imei_obj']
            else:
                index_status.setdefault(count, set()).add('Invalid Serial Number')

        # Marketplace Float check
        if isinstance(serial_dict['marketplace'], float):
            serial_dict['marketplace'] = str(int(serial_dict['marketplace']))

        all_data_list.append(serial_dict)

    if index_status:
        f_name = generate_error_excel(index_status, fname, reader, file_type)
        return f_name

    # Update Order Reference and Marketplace
    for data_dict in all_data_list:
        order_imei = data_dict['order_imei_obj']
        order_imei.order_reference = data_dict['order_reference']
        order_imei.marketplace = data_dict['marketplace']
        order_imei.save()

    return 'Success'


@csrf_exempt
@login_required
@get_admin_user
def marketplace_serial_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status = validate_save_marketplace_serial(request, reader, user, no_of_rows, fname, file_type=file_type)
        return HttpResponse(status)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Marketplace Order Serial Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username),
        str(request.POST.dict()), str(e)))
        return HttpResponse("Marketplace Serial Upload Failed")


@csrf_exempt
@login_required
@get_admin_user
def seller_transfer_form(request, user=''):
    excel_file = request.GET['download-file']
    if excel_file:
        return error_file_download(excel_file)
    excel_headers = get_seller_transfer_excel_headers(user)
    wb, ws = get_work_sheet('Inventory', excel_headers.keys())
    return xls_to_response(wb, '%s.seller_transfer_form.xls' % str(user.id))


@csrf_exempt
@login_required
@get_admin_user
def targets_form(request, user=''):
    excel_file = request.GET['download-file']
    if excel_file:
        return error_file_download(excel_file)
    excel_headers = TARGET_MASTER_HEADERS
    wb, ws = get_work_sheet('Targets', excel_headers)
    return xls_to_response(wb, '%s.targets_form.xls' % str(user.id))


def validate_targets_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type='xls'):
    index_status = {}
    target_file_mapping = copy.deepcopy(TARGET_DEF_EXCEL)
    if not target_file_mapping:
        return 'Invalid File'
    warehouse_qs = UserGroups.objects.filter(admin_user=user.id)
    dist_users = warehouse_qs.filter(user__userprofile__warehouse_level=2).values_list('user_id__username', flat=True)
    wh_userids = warehouse_qs.values_list('user_id', flat=True)
    reseller_qs = CustomerUserMapping.objects.filter(customer__user__in=wh_userids)
    reseller_ids_map = dict(reseller_qs.values_list('user_id__username', 'customer__id'))
    reseller_ids = reseller_ids_map.values()
    reseller_users = reseller_ids_map.keys()
    res_corp_qs = CorpResellerMapping.objects.filter(reseller_id__in=reseller_ids).values_list('reseller_id', 'corporate_id')
    res_corp_map = {}
    res_corp_names_map = {}
    for res_id, corp_id in res_corp_qs:
        res_corp_map.setdefault(res_id, []).append(corp_id)
    for res_id, corp_ids in res_corp_map.items():
        corp_names = CorporateMaster.objects.filter(id__in=corp_ids).values_list('name', flat=True)
        res_corp_names_map.setdefault(res_id, []).extend(corp_names)

    for row_idx in range(1, no_of_rows):
        for key, value in target_file_mapping.iteritems():
            cell_data = get_cell_data(row_idx, target_file_mapping[key], reader, file_type)
            if key == 'distributor_id':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add("Distributor Missing")
                else:
                    if cell_data not in dist_users:
                        index_status.setdefault(row_idx, set()).add('Invalid Distributor ID')
            elif key == 'reseller_id':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add("Reseller ID Missing")
                else:
                    if cell_data not in reseller_users:
                        index_status.setdefault(row_idx, set()).add('Invalid Reseller ID')
            elif key == 'corporate_name':
                res_code = get_cell_data(row_idx, target_file_mapping['reseller_id'], reader, file_type)
                res_id = reseller_ids_map[res_code]
                mapped_corp_names = res_corp_names_map.get(res_id, [])
                if cell_data:
                    if cell_data not in mapped_corp_names:
                        index_status.setdefault(row_idx, set()).add('Corporate Name not mapped with Reseller')
                else:
                    index_status.setdefault(row_idx, set()).add('Corporate Name Missing')
            elif key == 'target_amt':
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Invalid Target Amount')
                else:
                    index_status.setdefault(row_idx, set()).add('Target Amount Missing')
            elif key == 'target_duration':
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Invalid Target Duration')
                else:
                    index_status.setdefault(row_idx, set()).add('Target Duration Missing')
            else:
                index_status.setdefault(row_idx, set()).add('Invalid Field')

    if not index_status:
        return 'Success'

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name


@csrf_exempt
@login_required
@get_admin_user
def targets_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status = validate_targets_form(request, reader, user, no_of_rows,
                                                  no_of_cols,fname, file_type=file_type)
        if status != 'Success':
            return HttpResponse(status)
        update_targets_upload(request, reader, no_of_rows, file_type, user)
        return HttpResponse('Success')
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Targets Upload failed for %s and params are %s and error statement is %s' % (
                    str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Targets Upload Failed")


def update_targets_upload(request, reader, no_of_rows, file_type='xls', user=''):
    dist_users_map = dict(UserGroups.objects.filter(admin_user=user, user__userprofile__warehouse_level=2).
                          values_list('user__username', 'user_id'))
    reseller_users_map = dict(CustomerUserMapping.objects.filter(customer__user__in=dist_users_map.values()). \
        values_list('user_id__username', 'user_id'))
    corp_names_map = dict(CorporateMaster.objects.filter(user=user.id).values_list('name', 'id'))
    target_file_mapping = copy.deepcopy(TARGET_DEF_EXCEL)
    for row_idx in range(1, no_of_rows):
        if not target_file_mapping:
            continue
        each_row_map = copy.deepcopy(TARGET_DEF_EXCEL)
        for key, value in target_file_mapping.iteritems():
            each_row_map[key] = get_cell_data(row_idx, value, reader, file_type)

        dist_id = dist_users_map.get(each_row_map.pop('distributor_id'), '')
        res_id = reseller_users_map.get(each_row_map.pop('reseller_id'), '')
        corp_id = corp_names_map.get(each_row_map.pop('corporate_name'), '')
        if not dist_id and not res_id and not corp_id:
            continue
        target_obj = TargetMaster.objects.filter(distributor_id=dist_id, reseller_id=res_id, corporate_id=corp_id)
        if not target_obj:
            each_row_map['corporate_id'] = corp_id
            each_row_map['distributor_id'] = dist_id
            each_row_map['reseller_id'] = res_id
            target_master = TargetMaster(**dict(each_row_map))
            target_master.save()
        else:
            target_obj[0].target_amt = each_row_map['target_amt']
            target_obj[0].target_duration = each_row_map['target_duration']
            target_obj[0].save()
    return 'success'


def validate_seller_transfer_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type='xls'):
    log.info("Validate Seller Transfer upload started")
    st_time = datetime.datetime.now()
    index_status = {}
    seller_transfer_mapping = get_seller_transfer_excel_headers(user)

    excel_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                             seller_transfer_mapping)
    if not set(['wms_code', 'source_seller', 'source_location', 'dest_seller', 'dest_location',
                'quantity']).issubset(excel_mapping.keys()):
        return 'Invalid File'

    log.info("Validation Started %s" % datetime.datetime.now())
    all_data_list = []
    exc_reverse = dict(zip(seller_transfer_mapping.values(), seller_transfer_mapping.keys()))
    all_skus = SKUMaster.objects.filter(user=user.id)
    all_sellers = SellerMaster.objects.filter(user=user.id)
    all_locations = LocationMaster.objects.filter(zone__user=user.id)

    for row_idx in range(1, no_of_rows):
        data_dict = {}
        for key, val in excel_mapping.iteritems():
            cell_data = get_cell_data(row_idx, excel_mapping[key], reader, file_type)
            if not cell_data:
                index_status.setdefault(row_idx, set()).add('%s is Mandatory' % (exc_reverse[key]))
            elif key == 'wms_code':
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                sku_obj = all_skus.filter(sku_code=cell_data)
                if not sku_obj:
                    index_status.setdefault(row_idx, set()).add('Invalid SKU Code')
                else:
                    data_dict['sku_id'] = sku_obj[0].id
            elif key in ['source_seller', 'dest_seller']:
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                try:
                    seller_obj = all_sellers.filter(seller_id=cell_data)
                    if not seller_obj:
                        index_status.setdefault(row_idx, set()).add('Invalid %s' % exc_reverse[key])
                    else:
                        data_dict[key] = seller_obj[0].id
                except:
                    index_status.setdefault(row_idx, set()).add('%s should be Number' % exc_reverse[key])
            elif key in ['source_location', 'dest_location']:
                location_obj = all_locations.filter(location=cell_data)
                if not location_obj:
                    index_status.setdefault(row_idx, set()).add('Invalid %s' % exc_reverse[key])
                else:
                    data_dict[key] = location_obj
            elif key == 'mrp':
                if cell_data and cell_data != '':
                    try:
                        data_dict[key] = float(cell_data)
                    except:
                        data_dict[key] = 0
                        index_status.setdefault(row_idx, set()).add('%s should be number' % exc_reverse[key])
            elif key == 'quantity':
                try:
                    data_dict[key] = float(cell_data)
                except:
                    index_status.setdefault(row_idx, set()).add('%s should be number' % exc_reverse[key])
        if row_idx not in index_status.keys():
            src_stock_dict = {'sku_id': data_dict['sku_id'], 'sellerstock__seller_id': data_dict['source_seller'],
                              'location_id': data_dict['source_location'][0].id, 'quantity__gt': 0,
                              'sellerstock__quantity__gt': 0}
            if data_dict.get('mrp', 0):
                src_stock_dict['batch_detail__mrp'] = data_dict['mrp']
            stock_detail = StockDetail.objects.filter(**src_stock_dict)
            stock_ids = []
            if user.userprofile.industry_type == 'FMCG':
                data_dict['dest_stocks'] = StockDetail.objects.none()
                stock_detail1 = stock_detail.filter(batch_detail__expiry_date__isnull=False). \
                    order_by('batch_detail__expiry_date')
                stock_ids = list(stock_detail1.values_list('id', flat=True))
                stock_detail2 = stock_detail.exclude(batch_detail__expiry_date__isnull=False)
                stock_ids = stock_ids + list(stock_detail2.values_list('id', flat=True))
                stocks = list(chain(stock_detail1, stock_detail2))
            else:
                data_dict['dest_stocks'] = StockDetail.objects.filter(sku_id=data_dict['sku_id'],
                                                    sellerstock__seller_id=data_dict['dest_seller'],
                                                    location_id=data_dict['dest_location'][0].id)
                stocks = stock_detail
            data_dict['src_stocks'] = stocks
            if stocks:
                avail_qty = check_stock_available_quantity(stocks, user, stock_ids=stock_ids)
            else:
                avail_qty = 0
            #avail_qty = check_auto_stock_availability(stocks, user)
            if data_dict['quantity'] > avail_qty:
                index_status.setdefault(row_idx, set()).add('Available quantity is %s' % str(avail_qty))
        all_data_list.append(data_dict)

    if index_status:
        f_name = generate_error_excel(index_status, fname, reader, file_type)
        return f_name, all_data_list

    return 'Success', all_data_list


def update_seller_transer_upload(user, data_list):
    trans_mapping = {}
    stock_transfer_objs = []
    grouping_data = []
    for data_dict in data_list:
        update_stocks_data(data_dict['src_stocks'], data_dict['quantity'], data_dict.get('dest_stocks', ''),
                           data_dict['quantity'], user, data_dict['dest_location'], data_dict['sku_id'],
                           src_seller_id=data_dict['source_seller'], dest_seller_id=data_dict['dest_seller'])
        group_key = '%s:%s' % (str(data_dict['source_seller']), str(data_dict['dest_seller']))
        if group_key not in trans_mapping.keys():
            trans_id = get_max_seller_transfer_id(user)
            seller_transfer = SellerTransfer.objects.create(source_seller_id=data_dict['source_seller'],
                                          dest_seller_id=data_dict['dest_seller'],transact_id=trans_id,
                                          transact_type='stock_transfer', creation_date=datetime.datetime.now())
            trans_mapping[group_key] = seller_transfer.id
        seller_st_dict = {'seller_transfer_id': trans_mapping[group_key], 'sku_id': data_dict['sku_id'],
                          'source_location_id': data_dict['source_location'][0].id,
                          'dest_location_id': data_dict['dest_location'][0].id }
        exist_obj = SellerStockTransfer.objects.filter(**seller_st_dict)
        if not exist_obj:
            seller_st_dict['creation_date'] = datetime.datetime.now()
            seller_st_dict['quantity'] = data_dict['quantity']
            seller_st_obj = SellerStockTransfer(**seller_st_dict)
            seller_st_obj.save()
        else:
            exist_seller_obj = exist_obj[0]
            exist_seller_obj.quantity = exist_seller_obj.quantity + data_dict['quantity']
            exist_seller_obj.save()
        #stock_transfer_objs.append(seller_st_obj)
    #SellerStockTransfer.objects.bulk_create(stock_transfer_objs)


@csrf_exempt
@login_required
@get_admin_user
def seller_transfer_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status, data_list = validate_seller_transfer_form(request, reader, user, no_of_rows, no_of_cols,fname,
                                               file_type=file_type)
        if status != 'Success':
            return HttpResponse(status)
        update_seller_transer_upload(user, data_list)
        return HttpResponse('Success')
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Seller-Seller Transfer Upload failed for %s and params are %s and error statement is %s' % (
                    str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Seller-Seller Transfer Upload Failed")


@csrf_exempt
def validate_sku_substitution_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type):
    mapping_dict = {}
    index_status = {}
    location = {}
    data_list = []
    inv_mapping = get_sku_substitution_excel_headers(user)
    inv_res = dict(zip(inv_mapping.values(), inv_mapping.keys()))
    excel_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 inv_mapping)
    if not set(['source_sku_code', 'source_location', 'source_quantity', 'dest_sku_code',
                'dest_location', 'dest_quantity']).issubset(excel_mapping.keys()):
        return 'Invalid File'
    number_fields = ['source_quantity', 'source_mrp', 'dest_quantity', 'dest_mrp']
    prev_data_dict = {}
    for row_idx in range(1, no_of_rows):
        data_dict = {'source_updated': False}
        for key, value in excel_mapping.iteritems():
            cell_data = get_cell_data(row_idx, value, reader, file_type)
            if key in ['source_sku_code', 'dest_sku_code']:
                if cell_data:
                    if isinstance(cell_data, (int, float)):
                        cell_data = int(cell_data)
                    cell_data = str(cell_data)
                    sku_id = check_and_return_mapping_id(cell_data, "", user, False)
                    if not sku_id:
                        index_status.setdefault(row_idx, set()).add('Invalid %s' % inv_res[key])
                    else:
                        sku_master = SKUMaster.objects.get(id=sku_id, user=user.id)
                        data_dict['%s_obj' % key] = sku_master
                        data_dict[key] = sku_master.wms_code
                elif 'source' in key and prev_data_dict.get(key, ''):
                    data_dict['%s_obj' % key] = prev_data_dict['%s_obj' % key]
                    data_dict[key] = prev_data_dict[key]
                    data_dict['source_updated'] = True
                else:
                    index_status.setdefault(row_idx, set()).add('Invalid %s' % inv_res[key])
            elif key in ['source_location', 'dest_location']:
                if cell_data:
                    if isinstance(cell_data, (int, float)):
                        cell_data = int(cell_data)
                    cell_data = str(cell_data)
                    location_master = LocationMaster.objects.filter(zone__user=user.id, location=cell_data)
                    if not location_master:
                        index_status.setdefault(row_idx, set()).add('Invalid %s' % inv_res[key])
                    else:
                        data_dict[key] = location_master[0].location
                        data_dict['%s_obj' % key] = location_master[0]
                elif 'source' in key and prev_data_dict.get(key, ''):
                    data_dict['%s_obj' % key] = prev_data_dict['%s_obj' % key]
                    data_dict[key] = prev_data_dict[key]
                    data_dict['source_updated'] = True
                else:
                    index_status.setdefault(row_idx, set()).add('%s should not be empty' % inv_res[key])
            elif key == 'seller_id':
                if cell_data:
                    try:
                        seller_id = int(cell_data)
                        seller_master = SellerMaster.objects.filter(user=user.id, seller_id=seller_id)
                        if not seller_master:
                            index_status.setdefault(row_idx, set()).add('Invalid Seller ID')
                        else:
                            data_dict[key] = seller_master[0].seller_id
                            data_dict['seller_master_id'] = seller_master[0].id
                            prev_data_dict = {}
                    except:
                        index_status.setdefault(row_idx, set()).add('Invalid Seller ID')
                elif prev_data_dict:
                    data_dict[key] = prev_data_dict[key]
                    data_dict['seller_master_id'] = prev_data_dict['seller_master_id']
                    data_dict['source_updated'] = True
                else:
                    index_status.setdefault(row_idx, set()).add('Seller ID should not be empty')
            elif key in ['source_batch_no', 'dest_batch_no']:
                if 'source' in key and not cell_data and prev_data_dict.get(key, ''):
                    data_dict[key] = prev_data_dict[key]
                    data_dict['source_updated'] = True
                    continue
                if isinstance(cell_data, float):
                    cell_data = str(int(cell_data))
                    data_dict[key] = cell_data
            elif key in number_fields:
                if cell_data and (not isinstance(cell_data, (int, float)) or int(cell_data) < 0):
                    index_status.setdefault(row_idx, set()).add('Invalid %s' % inv_res[key])
                elif 'source' in key and prev_data_dict.get(key, ''):
                    data_dict[key] = prev_data_dict[key]
                    data_dict['source_updated'] = True
                else:
                    data_dict[key] = cell_data
        if row_idx not in index_status:
            prev_data_dict = copy.deepcopy(data_dict)
            stock_dict = {"sku_id": data_dict['source_sku_code_obj'].id,
                          "location_id": data_dict['source_location_obj'].id,
                          "sku__user": user.id, "quantity__gt": 0}
            reserved_dict = {'stock__sku_id': data_dict['source_sku_code_obj'].id, 'stock__sku__user': user.id,
                             'status': 1,
                             'stock__location_id': data_dict['source_location_obj'].id}
            if data_dict.get('source_batch_no', ''):
                stock_dict["batch_detail__batch_no"] = data_dict['source_batch_no']
                reserved_dict["stock__batch_detail__batch_no"] = data_dict['source_batch_no']
            if data_dict.get('source_mrp', ''):
                try:
                    mrp = data_dict['source_mrp']
                except:
                    mrp = 0
                stock_dict["batch_detail__mrp"] = mrp
                reserved_dict["stock__batch_detail__mrp"] = mrp
            if data_dict.get('seller_master_id', ''):
                stock_dict['sellerstock__seller_id'] = data_dict['seller_master_id']
                stock_dict['sellerstock__quantity__gt'] = 0
                reserved_dict["stock__sellerstock__seller_id"] = data_dict['seller_master_id']
            stocks = StockDetail.objects.filter(**stock_dict)
            data_dict['src_stocks'] = stocks
            if not stocks:
                index_status.setdefault(row_idx, set()).add('No Stocks Found')
            else:
                stock_count = stocks.aggregate(Sum('quantity'))['quantity__sum']
                reserved_quantity = PicklistLocation.objects.exclude(stock=None).filter(**reserved_dict).\
                                        aggregate(Sum('reserved'))['reserved__sum']
                if reserved_quantity:
                    if (stock_count - reserved_quantity) < float(data_dict['source_quantity']):
                        index_status.setdefault(row_idx, set()).add('Source Quantity reserved for Picklist')
        data_list.append(data_dict)

    if not index_status:
        return 'Success', data_list

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name, data_list

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name, data_list


@csrf_exempt
@login_required
@get_admin_user
def sku_substitution_form(request, user=''):
    excel_file = request.GET['download-file']
    if excel_file:
        return error_file_download(excel_file)
    excel_headers = get_sku_substitution_excel_headers(user)
    wb, ws = get_work_sheet('SKU Substitution', excel_headers)
    return xls_to_response(wb, '%s.sku_substitution_form.xls' % str(user.id))


@csrf_exempt
@login_required
@get_admin_user
def sku_substitution_upload(request, user=''):
    fname = request.FILES['files']
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
    except:
        return HttpResponse('Invalid File')
    status, data_list = validate_sku_substitution_form(request, reader, user, no_of_rows,
                                                     no_of_cols, fname, file_type)
    if status != 'Success':
        return HttpResponse(status)

    for data_dict in data_list:
        dest_filter = {'sku_id': data_dict['dest_sku_code_obj'].id, 'location_id': data_dict['dest_location_obj'].id,
                       'sku__user': user.id, 'quantity__gt': 0}
        mrp_dict = {}
        if data_dict.get('dest_batch_no', ''):
            dest_filter['batch_detail__batch_no'] = data_dict['dest_batch_no']
            mrp_dict['batch_no'] = data_dict['dest_batch_no']
        if data_dict.get('dest_mrp', 0):
            dest_filter['batch_detail__mrp'] = data_dict['dest_mrp']
            mrp_dict['mrp'] = data_dict['dest_mrp']
        if data_dict.get('seller_master_id', 0):
            dest_filter['sellerstock__seller_id'] = data_dict['seller_master_id']
            mrp_dict['mrp'] = data_dict['dest_mrp']
        if not data_dict['source_updated']:
            transact_number = get_max_substitute_allocation_id(user)
        dest_stocks = StockDetail.objects.filter(**dest_filter)
        update_substitution_data(data_dict['src_stocks'], dest_stocks, data_dict['source_sku_code_obj'],
                                 data_dict['source_location_obj'], data_dict['source_quantity'],
                                 data_dict['dest_sku_code_obj'], data_dict['dest_location_obj'],
                                 data_dict['dest_quantity'],user, data_dict.get('seller_master_id', ''),
                                 data_dict['source_updated'], mrp_dict, transact_number)
    return HttpResponse('Success')


@csrf_exempt
@login_required
@get_admin_user
def central_order_form(request, user=''):
    central_order_file = request.GET['download-file']
    if central_order_file:
        return error_file_download(central_order_file)
    if user.username == 'one_assist':
        wb, ws = get_work_sheet('central_order_form', CENTRAL_ORDER_ONE_ASSIST_MAPPING.keys())
    if user.username != 'one_assist':
        wb, ws = get_work_sheet('central_order_form', CENTRAL_ORDER_MAPPING.keys())
    return xls_to_response(wb, '%s.central_order_form.xls' % str(user.id))


@csrf_exempt
@login_required
@get_admin_user
def stock_transfer_order_form(request, user=''):
    error_file = request.GET['download-stock-transfer-file']
    if error_file:
        return error_file_download(error_file)
    wb, ws = get_work_sheet('stock_transfer_order_form', STOCK_TRANSFER_ORDER_MAPPING.keys())
    return xls_to_response(wb, '%s.stock_transfer_order_form.xls' % str(user.id))

def create_order_fields_entry(interm_order_id, name, value, user, is_bulk_create=False,
                              order_fields_objs=None):
    if not order_fields_objs:
        order_fields_objs = []
    order_fields_data = {}
    order_fields_data['original_order_id'] = interm_order_id
    order_fields_data['name'] = name
    order_fields_data['value'] = value
    order_fields_data['user'] = user.id
    order_fields_data['order_type'] = 'intermediate_order'
    if not is_bulk_create:
        OrderFields.objects.create(**order_fields_data)
    else:
        order_fields_objs.append(OrderFields(**order_fields_data))
    return order_fields_objs


def central_order_xls_upload(request, reader, user, no_of_rows, fname, file_type='xls', no_of_cols=0):
    log.info("Central order upload started")
    st_time = datetime.datetime.now()
    index_status = {}
    order_mapping = get_order_mapping(reader, file_type)
    if not order_mapping:
        return "Headers not matching"
    count = 0
    exclude_rows = []
    sku_masters_dict = {}
    order_id_order_type = {}
    order_data = {}
    log.info("Validation Started %s" % datetime.datetime.now())
    log.info("Order data Processing Started %s" % (datetime.datetime.now()))
    loan_proposal_ids_list = []
    sister_wh = get_sister_warehouse(user)
    sister_wh_names = dict(sister_wh.values_list('user__username', 'user_id'))
    sister_user_sku_map = {}
    user_sku_map = {}
    if no_of_rows > 1500:
        return "Orders exceeded. Please upload 1500 at a time."
    for row_idx in range(1, no_of_rows):
        print "Validation Row: " + str(row_idx)
        user_obj = ''
        if not order_mapping:
            break
        count += 1
        if order_mapping.has_key('location'):
            try:
                location = str(int(get_cell_data(row_idx, order_mapping['location'], reader, file_type)))
            except:
                location = str(get_cell_data(row_idx, order_mapping['location'], reader, file_type))
            if not location:
                index_status.setdefault(count, set()).add('Invalid Location')
            else:
                try:
                    if location not in sister_wh_names.keys():
                        index_status.setdefault(count, set()).add('Invalid Warehouse Location')
                except:
                    index_status.setdefault(count, set()).add('Invalid Warehouse Location')
        if order_mapping.has_key('loan_proposal_id'):
            try:
                loan_proposal_id = str(int(get_cell_data(row_idx, order_mapping['loan_proposal_id'], reader, file_type)))
            except:
                loan_proposal_id = str(get_cell_data(row_idx, order_mapping['loan_proposal_id'], reader, file_type))
            if not loan_proposal_id:
                index_status.setdefault(count, set()).add('Invalid loan_proposal_id')
            if loan_proposal_id in loan_proposal_ids_list:
                index_status.setdefault(count, set()).add('Loan Proposal ID already present in same excel sheet')
            else:
                loan_proposal_ids_list.append(loan_proposal_id)

            order_obj = OrderDetail.objects.filter(original_order_id = loan_proposal_id,
                                                   user__in=sister_wh_names.values())
            if order_obj.exists():
                index_status.setdefault(count, set()).add('loan_proposal_id existed previously')

        if order_mapping.has_key('sku_code'):
            try:
                sku_id = str(int(get_cell_data(row_idx, order_mapping['sku_code'], reader, file_type)))
            except:
                sku_id = str(get_cell_data(row_idx, order_mapping['sku_code'], reader, file_type))
            sku_master = SKUMaster.objects.filter(user=user.id, sku_code=sku_id)
            if not sku_master:
                index_status.setdefault(count, set()).add('Invalid SKU Code')
            else:
                if location in sister_wh_names.keys():
                    wh_id = sister_wh_names[location]
                    sku_master_id = sku_master[0].id
                    parent_grouping_key = '%s:%s' % (str(user.id), str(sku_id))
                    user_sku_map[parent_grouping_key] = sku_master_id
                    map_sku_id = get_syncedusers_mapped_sku(wh=wh_id, sku_id=sku_master_id)
                    if not map_sku_id:
                        index_status.setdefault(count, set()).add('SKU Code Not found in mentioned Location')
                    else:
                        sister_grouping_key = '%s:%s' % (str(wh_id), str(sku_id))
                        sister_user_sku_map[sister_grouping_key] = map_sku_id
        """
        if order_mapping.has_key('location'):
            try:
                location = str(int(get_cell_data(row_idx, order_mapping['location'], reader, file_type)))
            except:
                location = str(get_cell_data(row_idx, order_mapping['location'], reader, file_type))
            warehouse_admin = get_warehouse_admin(user)
            all_user_groups = UserGroups.objects.filter(admin_user_id=warehouse_admin.id)
            if not all_user_groups:
                index_status.setdefault(count, set()).add('Invalid Location')

        if order_mapping.has_key('original_order_id'):
            try:
                original_order_id = str(int(get_cell_data(row_idx, order_mapping['original_order_id'], reader, file_type)))
            except:
                original_order_id = str(get_cell_data(row_idx, order_mapping['original_order_id'], reader, file_type))
            order_fields_obj = OrderFields.objects.filter(user=user.id, name='original_order_id',
                value=original_order_id, order_type = 'intermediate_order')
            if order_fields_obj:
                index_status.setdefault(count, set()).add('Order ID already present')
            else:
                order_detail_obj = OrderDetail.objects.filter(user=user.id, original_order_id=original_order_id)
                if order_detail_obj:
                    index_status.setdefault(count, set()).add('Order ID already present')
        """
    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name
    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name
    order_amount = 0
    interm_order_id = ''
    client_code = ''
    address1 = ''
    address2 = ''
    address_value = ''
    mobile_no = ''
    alt_mobile_no = ''
    cos_objs = []
    order_fields_objs = []
    inter_objs = []
    get_interm_order_id = IntermediateOrders.objects.filter(user=user.id). \
        aggregate(Max('interm_order_id'))
    if get_interm_order_id['interm_order_id__max']:
        interm_order_id = get_interm_order_id['interm_order_id__max']
    else:
        interm_order_id = 10000
    for row_idx in range(1, no_of_rows):
        order_data = copy.deepcopy(CENTRAL_ORDER_XLS_UPLOAD)
        order_data['user'] = user
        for key, value in order_mapping.iteritems():
            order_fields_data = {}
            if key == 'original_order_id':
                try:
                    order_id = str(int(get_cell_data(row_idx, value, reader, file_type)))
                except:
                    order_id = str(get_cell_data(row_idx, value, reader, file_type))
                order_data['interm_order_id'] = interm_order_id
                order_fields_objs= create_order_fields_entry(order_id, key, order_id, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
            elif key == 'batch_number':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user,
                                                        is_bulk_create=True, order_fields_objs=order_fields_objs)
            elif key == 'batch_date':
                try:
                    cell_data = str(get_cell_data(row_idx, value, reader, file_type))
                    year, month, day, hour, minute, second = xldate_as_tuple(float(cell_data), 0)
                    key_value = datetime.datetime(year, month, day, hour, minute, second)
                except:
                    key_value = datetime.datetime.now()
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
            elif key == 'branch_id':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
            elif key == 'branch_name':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
            elif key == 'loan_proposal_id':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
                order_fields_objs = create_order_fields_entry(order_id , 'marketplace','Offline' , user,is_bulk_create=True,order_fields_objs=order_fields_objs)
            elif key == 'loan_proposal_code':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
            elif key == 'client_code':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                client_code = key_value
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
            elif key == 'client_id':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
            elif key == 'customer_id':
                order_data['customer_id'] = 0
            elif key == 'customer_name':
                order_data['customer_name'] = get_cell_data(row_idx, value, reader, file_type)
            elif key == 'address1':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
                address1 = key_value
            elif key == 'address2':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
                address2 = key_value
            elif key == 'landmark':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
            elif key == 'village':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
            elif key == 'district':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
            elif key == 'state':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
            elif key == 'pincode':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
            elif key == 'mobile_no':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                mobile_no = key_value
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
            elif key == 'alternative_mobile_no':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                alt_mobile_no = key_value
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
            elif key == 'sku_code':
                try:
                    value = str(int(get_cell_data(row_idx, value, reader, file_type)))
                except:
                    value = str(get_cell_data(row_idx, value, reader, file_type))
                excel_sku_code = ''
                if value:
                    order_data['sku_id'] = user_sku_map[str(user.id)+':'+str(value)]
                    excel_sku_code = str(value)
                    if 'sku' in order_data.keys():
                        del order_data['sku']
            elif key == 'model':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
            elif key == 'unit_price':
                try:
                    order_data['unit_price'] = float(get_cell_data(row_idx, value, reader, file_type))
                    unit_price = order_data['unit_price']
                except:
                    order_data['unit_price'] = 0
                    unit_price = order_data['unit_price']
            elif key == 'cgst':
                try:
                    order_data['cgst_tax'] = float(get_cell_data(row_idx, value, reader, file_type))
                except:
                    order_data['cgst_tax'] = 0

            elif key == 'sgst':
                try:
                    order_data['sgst_tax'] = float(get_cell_data(row_idx, value, reader, file_type))
                except:
                    order_data['sgst_tax'] = 0
            elif key == 'igst':
                try:
                    order_data['igst_tax'] = float(get_cell_data(row_idx, value, reader, file_type))
                except:
                    order_data['igst_tax'] = 0
            elif key == 'total_price':
                try:
                    key_value = float(get_cell_data(row_idx, value, reader, file_type))
                except:
                    key_value = 0
                order_fields_objs = create_order_fields_entry(order_id, key, key_value, user, is_bulk_create=True,
                              order_fields_objs=order_fields_objs)
            elif key == 'location':
                try:
                    value = str(int(get_cell_data(row_idx, value, reader, file_type)))
                except:
                    value = str(get_cell_data(row_idx, value, reader, file_type))
                if value:
                    order_data['order_assigned_wh_id'] = sister_wh_names[value]
                    order_data['status'] = ''
        try:
            only_addr = address1[:200] + ' ' + address2[:200]  # Max length of addr in OrderFields is 255, but text field in OrderDetail
            address_value = only_addr + ' ' + client_code + ' ' + mobile_no + ' ' + alt_mobile_no
            order_dict = {}
            order_dict['user'] = order_data['order_assigned_wh_id']
            sku_id = sister_user_sku_map[str(order_data['order_assigned_wh_id'])+':'+str(excel_sku_code)]
            if not sku_id:
                return HttpResponse("SKU Not found in Selected Warehouse")
            order_dict['sku_id'] = sku_id
            order_dict['title'] = SKUMaster.objects.filter(sku_code=excel_sku_code, user=user.id)[0].sku_desc
            order_dict['status'] = 1

            if order_data['customer_id']:
               customer_master = CustomerMaster.objects.filter(user=user.id,
                                                               customer_id=order_data['customer_id'])
               if customer_master:
                   order_dict['customer_id'] = customer_master[0].customer_id
                   order_dict['email_id'] = customer_master[0].email_id
                   order_dict['telephone'] = customer_master[0].phone_number
                   order_dict['address'] = customer_master[0].address
            else:
                order_dict['customer_id'] = 0
                if mobile_no:
                    order_dict['telephone'] = mobile_no
                if address_value:
                    order_dict['address'] = address_value
                order_dict['customer_name'] = order_data.get('customer_name', '')
            order_dict['original_order_id'] = order_id
            order_code = ''.join(re.findall('\D+', order_id))
            ord_id = ''.join(re.findall('\d+', order_id))
            order_dict['order_code'] = order_code
            order_dict['order_id'] = ord_id
            order_dict['shipment_date'] = datetime.datetime.now() #interm_obj.shipment_date
            order_dict['quantity'] = 1
            order_dict['unit_price'] = unit_price
            if order_mapping.has_key('loan_proposal_id'):
                order_dict['marketplace'] = 'Offline'
            get_existing_order = OrderDetail.objects.filter(**{'sku_id': sku_id,
                'original_order_id': order_id, 'user':order_data['order_assigned_wh_id'] })
            if get_existing_order.exists():
                continue
            else:
                try:
                    ord_obj = OrderDetail(**order_dict)
                    ord_obj.save()
                except:
                    log.info("Central Order Upload: Order Not Created: %s" % order_dict)
                    continue
            interm_order_id += 1
            cust_ord_dict = {'order_id': ord_obj.id, 'sgst_tax': order_data['sgst_tax'],
                             'cgst_tax': order_data['cgst_tax'],
                             'igst_tax': order_data['igst_tax']}
            cos_objs.append(CustomerOrderSummary(**cust_ord_dict))
            order_data['order_id'] = ord_obj.id
            order_data['status'] = 1
            inter_objs.append(IntermediateOrders(**order_data))
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info("Create Central Order failed")
    if cos_objs:
        CustomerOrderSummary.objects.bulk_create(cos_objs)
    if order_fields_objs:
        OrderFields.objects.bulk_create(order_fields_objs)
    if inter_objs:
        IntermediateOrders.objects.bulk_create(inter_objs)
    return 'success'


@csrf_exempt
@login_required
@get_admin_user
def central_order_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        if user.username == 'one_assist':
            upload_status = central_order_one_assist_upload(request, reader, user, no_of_rows, fname,
                file_type=file_type, no_of_cols=no_of_cols)
        else:
            upload_status = central_order_xls_upload(request, reader, user, no_of_rows, fname,
                file_type=file_type, no_of_cols=no_of_cols)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Order Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Order Upload Failed")
    if not upload_status == 'success':
        return HttpResponse(upload_status)

    return HttpResponse('Success')


def central_order_one_assist_upload(request, reader, user, no_of_rows, fname, file_type='xls', no_of_cols=0):
    log.info("order upload started")
    st_time = datetime.datetime.now()
    index_status = {}
    order_mapping = get_order_mapping(reader, file_type)
    if not order_mapping:
        return "Headers not matching"
    count = 0
    exclude_rows = []
    sku_masters_dict = {}
    order_id_order_type = {}
    order_data = {}
    log.info("Validation Started %s" % datetime.datetime.now())
    log.info("Central Order data Processing Started %s" % (datetime.datetime.now()))
    for row_idx in range(1, no_of_rows):
        user_obj = ''
        if not order_mapping:
            break
        count += 1
        if order_mapping.has_key('original_order_id'):
            try:
                original_order_id = str(int(get_cell_data(row_idx, order_mapping['original_order_id'], reader, file_type)))
            except:
                original_order_id = str(get_cell_data(row_idx, order_mapping['original_order_id'], reader, file_type))
            if not original_order_id:
                index_status.setdefault(count, set()).add('Main SR Number is mandatory')
        if order_mapping.has_key('customer_name'):
            customer_name = str(get_cell_data(row_idx, order_mapping['customer_name'], reader, file_type))
            if not customer_name:
                index_status.setdefault(count, set()).add('Customer Name is Mandatory')
        if order_mapping.has_key('sku_code'):
            try:
                sku_id = str(int(get_cell_data(row_idx, order_mapping['sku_code'], reader, file_type)))
            except:
                sku_id = str(get_cell_data(row_idx, order_mapping['sku_code'], reader, file_type))
            sku_master = SKUMaster.objects.filter(user=user.id, sku_code=sku_id)
            if not sku_master:
                index_status.setdefault(count, set()).add('Invalid SKU Code')
            else:
                if user_obj:
                    wh_id = user_obj[0].user.id
                    sku_master_id = sku_master[0].id
                    sku_id = get_syncedusers_mapped_sku(wh=wh_id, sku_id=sku_master_id)
                    if not sku_id:
                        index_status.setdefault(count, set()).add('SKU Code Not found in mentioned Location')

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name
    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name
    order_amount = 0
    interm_order_id = ''
    for row_idx in range(1, no_of_rows):
        order_data = copy.deepcopy(CENTRAL_ORDER_XLS_UPLOAD)
        order_data['user'] = user
        order_data['status'] = 2
        customer_info = {}
        for key, value in order_mapping.iteritems():
            order_fields_data = {}
            if key == 'original_order_id':
                try:
                    order_id = str(int(get_cell_data(row_idx, value, reader, file_type)))
                except:
                    order_id = str(get_cell_data(row_idx, value, reader, file_type))
                get_interm_order_id = IntermediateOrders.objects.filter(sku__user=user.id).aggregate(Max('interm_order_id'))['interm_order_id__max']
                if get_interm_order_id:
                    interm_order_id = int(get_interm_order_id) + 1
                else:
                    interm_order_id = 10000
                order_data['interm_order_id'] = interm_order_id
                create_order_fields_entry(interm_order_id, key, order_id, user)
            elif key == 'sku_code':
                try:
                    value = str(int(get_cell_data(row_idx, value, reader, file_type)))
                except:
                    value = str(get_cell_data(row_idx, value, reader, file_type))
                sku_data = SKUMaster.objects.filter(wms_code=value, user=user.id)
                if sku_data:
                    order_data['sku'] = sku_data[0]
            elif key == 'customer_name':
                order_data['customer_name'] = get_cell_data(row_idx, value, reader, file_type)
                customer_info['name'] = order_data['customer_name']
            elif key == 'city':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                customer_info['city'] = key_value
                create_order_fields_entry(interm_order_id, key, key_value, user)
            elif key == 'pincode':
                try:
                    key_value = str(int(get_cell_data(row_idx, value, reader, file_type)))
                except:
                    key_value = str(get_cell_data(row_idx, value, reader, file_type))
                customer_info['pincode'] = key_value
                create_order_fields_entry(interm_order_id, key, key_value, user)
            elif key == 'mobile_no':
                try:
                    key_value = str(int(get_cell_data(row_idx, value, reader, file_type)))
                except:
                    key_value = str(get_cell_data(row_idx, value, reader, file_type))
                customer_info['phone_number'] = key_value
                create_order_fields_entry(interm_order_id, key, key_value, user)
            elif key == 'email_id':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                customer_info['email_id'] = key_value
                create_order_fields_entry(interm_order_id, key, key_value, user)
            elif key == 'address':
                key_value = str(get_cell_data(row_idx, value, reader, file_type))
                customer_info['address'] = key_value
                create_order_fields_entry(interm_order_id, key, key_value, user)
        if user.username == 'one_assist':
            customer_master = CustomerMaster.objects.filter(user=user.id, email_id=customer_info['email_id'], name=customer_info['name'])
            if customer_master.exists():
                order_data['customer_id'] = customer_master[0].customer_id
            else:
                customer_info['user'] = user.id
                customer_master_ins = CustomerMaster.objects.filter(user=user.id).values_list('customer_id', flat=True).order_by(
                                           '-customer_id')
                if customer_master_ins:
                    customer_id = customer_master_ins[0] + 1
                else:
                    customer_id = 1
                customer_info['customer_id'] = customer_id
                customer_master = CustomerMaster.objects.create(**customer_info)
                order_data['customer_id'] = customer_master.customer_id
        try:
            IntermediateOrders.objects.create(**order_data)
        except:
            pass
    return 'success'

@csrf_exempt
@login_required
@get_admin_user
def stock_transfer_order_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        upload_status = stock_transfer_order_xls_upload(request, reader, user, no_of_rows, fname,
            file_type=file_type, no_of_cols=no_of_cols)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Stock Transfer Order Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse(" Stock Transfer Order Upload Failed")
    if not upload_status == 'success':
        return HttpResponse(upload_status)

    return HttpResponse('Success')

def stock_transfer_order_xls_upload(request, reader, user, no_of_rows, fname, file_type='xls', no_of_cols=0):
    log.info("stock transfer order upload started")
    st_time = datetime.datetime.now()
    index_status = {}
    order_mapping = get_order_mapping(reader, file_type)
    if not order_mapping:
        return "Headers not matching"
    count = 0
    exclude_rows = []
    sku_masters_dict = {}
    order_id_order_type = {}
    order_data = {}
    log.info("Validation Started %s" % datetime.datetime.now())
    log.info("Order data Processing Started %s" % (datetime.datetime.now()))
    for row_idx in range(1, no_of_rows):
        user_obj = ''
        if not order_mapping:
            break
        count += 1
        if order_mapping.has_key('warehouse_name') :
            try:
                warehouse_name = str(int(get_cell_data(row_idx, order_mapping['warehouse_name'], reader, file_type)))
            except:
                warehouse_name = str(get_cell_data(row_idx, order_mapping['warehouse_name'], reader, file_type))
            if not warehouse_name:
                index_status.setdefault(count, set()).add('Invalid warehouse')
            else:
                try:
                    sister_wh = get_sister_warehouse(user)
                    user_obj = sister_wh.filter(user__username=warehouse_name)
                    if not user_obj:
                        index_status.setdefault(count, set()).add('Invalid Warehouse Location')
                except:
                    index_status.setdefault(count, set()).add('Invalid Warehouse Location')
        if order_mapping.has_key('wms_code'):
            try:
                wms_code = str(int(get_cell_data(row_idx, order_mapping['wms_code'], reader, file_type)))
            except:
                wms_code = str(get_cell_data(row_idx, order_mapping['wms_code'], reader, file_type))
            sku_master = SKUMaster.objects.filter(user=user.id, sku_code=wms_code)
            if not sku_master:
                index_status.setdefault(count, set()).add('Invalid SKU Code')
            else:
                if user_obj:
                    wh_id = user_obj[0].user.id
                    sku_master_id = sku_master[0].id
                    sku_id = get_syncedusers_mapped_sku(wh=wh_id, sku_id=sku_master_id)
                    if not sku_id:
                        index_status.setdefault(count, set()).add('SKU Code Not found in mentioned Location')
        number_fields = {'quantity': 'Quantity', 'price': 'Price', 'cgst_tax': 'CGST Tax', 'sgst_tax': 'SGST Tax',
                         'igst_tax': 'IGST Tax'}
        for key, value in number_fields.iteritems():
            if order_mapping.has_key(key):
                cell_data = get_cell_data(row_idx, order_mapping[key], reader, file_type)
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(count, set()).add('Invalid %s' % number_fields[key])
                elif key == 'quantity':
                    index_status.setdefault(count, set()).add('Quantity is mandatory')

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name
    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name
    order_amount = 0
    interm_order_id = ''
    for row_idx in range(1, no_of_rows):
        all_data = {}
        for key, value in order_mapping.iteritems():
            if key == 'warehouse_name':
                try:
                    warehouse = str(int(get_cell_data(row_idx, value, reader, file_type)))
                except:
                    warehouse = str(get_cell_data(row_idx, value, reader, file_type))
            elif key == 'wms_code':
                try:
                    wms_code = str(int(get_cell_data(row_idx, value, reader, file_type)))
                except:
                    wms_code = str(get_cell_data(row_idx, value, reader, file_type))
            elif key == 'quantity':
                 quantity = int(get_cell_data(row_idx, value, reader, file_type))
            elif key == 'price':
                 price = int(get_cell_data(row_idx, value, reader, file_type))
            elif key == 'cgst_tax':
                try:
                    cgst_tax = str(int(get_cell_data(row_idx, value, reader, file_type)))
                except:
                    cgst_tax = str(get_cell_data(row_idx, value, reader, file_type))
                if cgst_tax == '':
                    cgst_tax = 0
            elif key == 'sgst_tax':
                try:
                    sgst_tax = str(int(get_cell_data(row_idx, value, reader, file_type)))
                except:
                    sgst_tax = str(get_cell_data(row_idx, value, reader, file_type))
                if sgst_tax == '':
                    sgst_tax = 0
            elif key == 'igst_tax':
                try:
                    igst_tax = str(int(get_cell_data(row_idx, value, reader, file_type)))
                except:
                    igst_tax = str(get_cell_data(row_idx, value, reader, file_type))
                if igst_tax == '':
                    igst_tax = 0

        cond = (user.username)
        all_data.setdefault(cond, [])
        all_data[cond].append([wms_code, quantity, price,cgst_tax,sgst_tax,igst_tax, 0])
        warehouse = User.objects.get(username=warehouse)
        f_name = 'stock_transfer_' + warehouse_name + '_'
        all_data = insert_st_gst(all_data, warehouse)
        status = confirm_stock_transfer_gst(all_data, warehouse, user.username)

    if status.status_code == 200:
        return 'Success'
    else:
        return 'Failed'

@csrf_exempt
@login_required
@get_admin_user
def skupack_master_download(request, user=''):
    wb, ws = get_work_sheet('sku_pack_form', SKU_PACK_MAPPING.keys())
    return xls_to_response(wb, '%s.sku_pack_form.xls' % str(user.id))

@csrf_exempt
@login_required
@get_admin_user
def skupack_master_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        upload_status = sku_pack_xls_upload(request, reader, user, no_of_rows, fname,file_type=file_type, no_of_cols=no_of_cols)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Sku Pack form Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse(" Sku Pack Upload Failed")
    if not upload_status == 'Success':
        return HttpResponse(upload_status)
    return HttpResponse('Success')

def sku_pack_xls_upload(request, reader, user, no_of_rows, fname, file_type='xls', no_of_cols=0):
    log.info("Sku Pack  upload started")
    st_time = datetime.datetime.now()
    index_status = {}
    order_mapping = get_order_mapping(reader, file_type)
    if not order_mapping:
        return "Headers not matching"
    count = 0
    exclude_rows = []
    sku_masters_dict = {}
    order_id_order_type = {}
    order_data = {}
    log.info("Validation Started %s" % datetime.datetime.now())
    log.info("Sku Pack data Processing Started %s" % (datetime.datetime.now()))
    for row_idx in range(1, no_of_rows):
        user_obj = ''
        if not order_mapping:
            break
        count += 1
        if order_mapping.has_key('sku_code') :
            try:
                sku_code = str(int(get_cell_data(row_idx, order_mapping['sku_code'], reader, file_type)))
            except:
                sku_code = str(get_cell_data(row_idx, order_mapping['sku_code'], reader, file_type))
            if not sku_code:
                index_status.setdefault(count, set()).add('Invalid sku code')
            else:
                try:
                    sku_obj = SKUMaster.objects.filter(wms_code=sku_code.upper(), user=user.id)
                    if not sku_obj:
                        index_status.setdefault(count, set()).add('Invalid sku code')
                except:
                    index_status.setdefault(count, set()).add('Invalid sku code')
            redundent_sku_obj = SKUPackMaster.objects.filter(sku__wms_code= sku_code , sku__user = user.id)

        if order_mapping.has_key('pack_id'):
            try:
                pack_id = str(int(get_cell_data(row_idx, order_mapping['pack_id'], reader, file_type)))
            except:
                pack_id = str(get_cell_data(row_idx, order_mapping['pack_id'], reader, file_type))

            if not pack_id:
                index_status.setdefault(count, set()).add('Invalid pack_id')
            if redundent_sku_obj :
                if redundent_sku_obj[0].pack_id != pack_id :
                    index_status.setdefault(count, set()).add('SKU Code is already mapped to other pack_id')
        if order_mapping.has_key('pack_quantity'):
            try:
                pack_quantity = int(get_cell_data(row_idx, order_mapping['pack_quantity'], reader, file_type))
            except:
                index_status.setdefault(count, set()).add('Invalid pack quantity')
            if not pack_id:
                index_status.setdefault(count, set()).add('Invalid pack quantity')

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name
    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name

    sku_pack = copy.deepcopy(SKU_PACK_DATA)
    for row_idx in range(1, no_of_rows):
        for key, value in order_mapping.iteritems():
            if key == 'sku_code':
                try:
                    sku_code = str(int(get_cell_data(row_idx, value, reader, file_type)))
                except:
                    sku_code = str(get_cell_data(row_idx, value, reader, file_type))
            elif key == 'pack_id':
                try:
                    pack_id = str(int(get_cell_data(row_idx, value, reader, file_type)))
                except:
                    pack_id = str(get_cell_data(row_idx, value, reader, file_type))
            elif key == 'pack_quantity':
                 pack_quantity = int(get_cell_data(row_idx, value, reader, file_type))

                 pack_obj = SKUPackMaster.objects.filter(sku__wms_code= sku_code,pack_id = pack_id,sku__user = user.id)
                 if pack_obj :
                     pack_obj = pack_obj[0]
                     pack_obj.pack_quantity = pack_quantity
                     pack_obj.save()
                 else:
                     sku_pack['sku'] = sku_obj[0]
                     sku_pack ['pack_id'] = pack_id
                     sku_pack ['pack_quantity'] = pack_quantity
                     try:
                         SKUPackMaster.objects.create(**sku_pack)
                         return 'Success'
                     except Exception as e:
                         import traceback
                         log.debug(traceback.format_exc())
                         log.info('Insert New SKUPACK failed for %s and params are %s and error statement is %s' % (str(user.username), str(request.POST.dict()),str(e)))
                         return 'Failed'


@csrf_exempt
@login_required
@get_admin_user
def block_stock_download(request, user=''):
    returns_file = request.GET['download-file']
    if returns_file:
        return error_file_download(returns_file)
    wb, ws = get_work_sheet('block_stock_form', BLOCK_STOCK_MAPPING.keys())
    return xls_to_response(wb, '%s.block_stock_form.xls' % str(user.id))


@csrf_exempt
def validate_block_stock_form(reader, user, no_of_rows, no_of_cols, fname, file_type=''):
    from stock_locator import get_quantity_data
    block_stock_list = []
    index_status = {}
    blockstock_file_mapping = copy.deepcopy(BLOCK_STOCK_DEF_EXCEL)
    if not blockstock_file_mapping:
        return 'Invalid File'
    warehouse_qs = UserGroups.objects.filter(admin_user=user.id)
    dist_users = warehouse_qs.filter(user__userprofile__warehouse_level=1).values_list('user_id__username', flat=True)
    wh_userids = warehouse_qs.values_list('user_id', flat=True)
    sister_whs = copy.deepcopy(list(wh_userids))
    sister_whs.append(user.id)
    reseller_qs = CustomerUserMapping.objects.filter(customer__user__in=wh_userids)
    reseller_ids_map = dict(reseller_qs.values_list('user_id__username', 'customer__id'))
    reseller_ids = reseller_ids_map.values()
    reseller_users = reseller_ids_map.keys()
    res_corp_qs = CorpResellerMapping.objects.filter(reseller_id__in=reseller_ids).values_list('reseller_id',
                                                                                               'corporate_id')
    sku_codes = SKUMaster.objects.filter(user=user.id).values_list('sku_code', flat=True)
    res_corp_map = {}
    res_corp_names_map = {}
    for res_id, corp_id in res_corp_qs:
        res_corp_map.setdefault(res_id, []).append(corp_id)
    for res_id, corp_ids in res_corp_map.items():
        corp_names = CorporateMaster.objects.filter(corporate_id__in=corp_ids, user__in=sister_whs).values_list('name', flat=True)
        res_corp_names_map.setdefault(res_id, []).extend(corp_names)
    for row_idx in range(1, no_of_rows):
        block_stock_dict = {}
        grouping_key = ''
        for key, value in blockstock_file_mapping.iteritems():
            cell_data = get_cell_data(row_idx, blockstock_file_mapping[key], reader, file_type)
            if key == 'sku_code':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add("SKU Code is missing")
                else:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    block_stock_dict[key] = cell_data
                    if cell_data not in sku_codes:
                        index_status.setdefault(row_idx, set()).add('Invalid SKU Code')
            elif key == 'quantity':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add("Quantity Missing")
                else:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Invalid Quantity Amount')
                    else:
                        sku_code = get_cell_data(row_idx, blockstock_file_mapping['sku_code'], reader, file_type)
                        wh_name = get_cell_data(row_idx, blockstock_file_mapping['warehouse'], reader, file_type)
                        level = get_cell_data(row_idx, blockstock_file_mapping['level'], reader, file_type)
                        usr_obj = User.objects.filter(username=wh_name).values_list('id', flat=True)
                        ret_list = get_quantity_data(usr_obj, [sku_code], asn_true=False)
                        if ret_list:
                            avail_stock = ret_list[0]['available']
                            if level == 1:
                                if avail_stock < cell_data:
                                    index_status.setdefault(row_idx, set()).add('Stock Outage.Pls check stock in WH')
                            elif level == 3:
                                asn_avail_stock = ret_list[0]['asn']
                                if asn_avail_stock < cell_data:
                                    index_status.setdefault(row_idx, set()).add('Stock Outage.Pls check stock in WH')
            elif key == 'reseller_name':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add("Reseller Name is missing")
                else:
                    block_stock_dict[key] = cell_data
                    if cell_data not in reseller_users:
                        index_status.setdefault(row_idx, set()).add("Reseller Name not found")
            elif key == 'corporate_name':
                res_code = get_cell_data(row_idx, blockstock_file_mapping['reseller_name'], reader, file_type)
                res_id = reseller_ids_map.get(res_code, '')
                mapped_corp_names = res_corp_names_map.get(res_id, [])
                if cell_data:
                    block_stock_dict[key] = cell_data
                    if cell_data not in mapped_corp_names:
                        index_status.setdefault(row_idx, set()).add('Corporate Name not mapped with Reseller')
                else:
                    index_status.setdefault(row_idx, set()).add('Corporate Name Missing')
            elif key == 'warehouse':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Warehouse Username is missing.')
                else:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    block_stock_dict[key] = cell_data
                    if cell_data not in dist_users:
                        index_status.setdefault(row_idx, set()).add('Invalid Warehouse Username')
            elif key == 'level':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add("Level Missing")
                else:
                    block_stock_dict[key] = int(cell_data)
          	    if int(cell_data) not in [1, 3]:
          	        index_status.setdefault(row_idx, set()).add('Level must be either 1 or 3')
            else:
                index_status.setdefault(row_idx, set()).add('Invalid Field')
        grouping_key = '%s,%s,%s,%s,%s' % (str(block_stock_dict.get('sku_code', '')),str(block_stock_dict.get('corporate_name', '')),str(block_stock_dict.get('reseller_name', '')),str(block_stock_dict.get('warehouse', '')),str(block_stock_dict.get('level', '')))
        if grouping_key in block_stock_list:
             index_status.setdefault(row_idx, set()).add('Duplicate Record Found')
        else:
            block_stock_list.append(grouping_key)
    if not index_status:
        return 'Success'

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name


def block_stock_xls_upload(request, reader, user, admin_user, no_of_rows, fname, file_type='xls', no_of_cols=0):
    from outbound import block_asn_stock
    log.info("Block Stock upload started")
    enq_limit = get_misc_value('auto_expire_enq_limit', admin_user.id)
    if enq_limit:
        enq_limit = int(enq_limit)
    else:
        enq_limit = 7
    block_stock_file_mapping = copy.deepcopy(BLOCK_STOCK_DEF_EXCEL)
    enquiry_id_map = {}
    for row_idx in range(1, no_of_rows):
        if not block_stock_file_mapping:
            continue
        each_row_map = copy.deepcopy(BLOCK_STOCK_DEF_EXCEL)
        for key, value in block_stock_file_mapping.iteritems():
            each_row_map[key] = get_cell_data(row_idx, value, reader, file_type)

        reseller_code = each_row_map.pop('reseller_name', '')
        corporate_name = each_row_map.pop('corporate_name', '')
        wh_code = each_row_map.pop('warehouse', '')
        level = each_row_map.pop('level', '')
        qty = each_row_map.get('quantity', '')
        levelbase_price = 0
        wh_qs = User.objects.filter(username=wh_code)
        if not wh_qs: continue
        wh_id = wh_qs[0].id

        if not reseller_code and not corporate_name and not wh_code and not level:
            continue
        sku_code = each_row_map.get('sku_code', '')
        cum_obj = CustomerUserMapping.objects.filter(user__username=reseller_code)
        if not cum_obj:
            continue
        customer_user = cum_obj[0]
        cm_id = customer_user.customer_id
        if cm_id not in enquiry_id_map:
            enquiry_id = get_enquiry_id(cm_id)
            enquiry_id_map[cm_id] = enquiry_id
        else:
            enquiry_id = enquiry_id_map[cm_id]
        dist_id = customer_user.customer.user
        price_ranges_map = fetch_unit_price_based_ranges(dist_id, 1, admin_user.id, sku_code)
        if price_ranges_map.has_key('price_ranges'):
            max_unit_ranges = [i['max_unit_range'] for i in price_ranges_map['price_ranges']]
            highest_max = max(max_unit_ranges)
            for index, each_map in enumerate(price_ranges_map['price_ranges']):
                min_qty, max_qty, price = each_map['min_unit_range'], each_map['max_unit_range'], each_map[
                    'price']
                if min_qty <= qty <= max_qty:
                    levelbase_price = price
                    break
                elif max_qty >= highest_max:
                    levelbase_price = price
        if not levelbase_price:
            log.info("Something goes wrong with price ranges..check this.")
            continue
        try:
            customer_details = {}
            if customer_user:
                customer_details['customer_name'] = customer_user.customer.name
                customer_details['telephone'] = customer_user.customer.phone_number
                customer_details['email_id'] = customer_user.customer.email_id
                customer_details['address'] = customer_user.customer.address
                customer_details['customer_id'] = cm_id
                customer_details['user'] = customer_user.customer.user #Distributor ID
            enquiry_map = {'enquiry_id': enquiry_id,
                           'extend_date': datetime.datetime.today() + datetime.timedelta(days=enq_limit)}
            if corporate_name:
                enquiry_map['corporate_name'] = corporate_name
            enquiry_map.update(customer_details)
            enq_master_obj = EnquiryMaster.objects.filter(enquiry_id=enquiry_id,
                                                          user=customer_user.customer.user,
                                                          customer_id=cm_id)
            if enq_master_obj:
                enq_master_obj = enq_master_obj[0]
            else:
                enq_master_obj = EnquiryMaster(**enquiry_map)
                enq_master_obj.save()
            sku_qs = SKUMaster.objects.filter(user=wh_id, sku_code=sku_code)
            if not sku_qs:
                continue
            enq_sku_obj = EnquiredSku()
            enq_sku_obj.sku_id = sku_qs[0].id
            enq_sku_obj.title = sku_qs[0].style_name
            enq_sku_obj.enquiry = enq_master_obj
            enq_sku_obj.quantity = qty
            tot_amt = get_tax_inclusive_invoice_amt(cm_id, levelbase_price, qty,
                                                    user.id, sku_qs[0].sku_code, admin_user)
            enq_sku_obj.invoice_amount = tot_amt
            enq_sku_obj.status = 1
            enq_sku_obj.sku_code = sku_qs[0].sku_code
            enq_sku_obj.levelbase_price = levelbase_price
            enq_sku_obj.warehouse_level = level
            enq_sku_obj.save()
            if int(level) == 3:
                block_asn_stock(sku_qs[0].id, qty, 90, enq_sku_obj, is_enquiry=True) # Default max leadtime is 90days
        except:
            import traceback
            log.debug(traceback.format_exc())
            return 'Failed'
    return 'Success'


@csrf_exempt
@login_required
@get_admin_user
def block_stock_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        price_band_flag = get_misc_value('priceband_sync', user.id)
        if price_band_flag == 'true':
            admin_user = get_admin(user)
        else:
            admin_user = user
        status = validate_block_stock_form(reader, admin_user, no_of_rows, no_of_cols, fname, file_type=file_type)
        if status != 'Success':
            return HttpResponse(status)
        upload_status = block_stock_xls_upload(request, reader, user, admin_user, no_of_rows, fname,file_type=file_type, no_of_cols=no_of_cols)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Block Stock form Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse(" Block Stock Upload Failed")
    if not upload_status == 'Success':
        return HttpResponse(upload_status)
    return HttpResponse('Success')


@csrf_exempt
@login_required
@get_admin_user
def custom_order_download(request, user=''):
    returns_file = request.GET['download-file']
    if returns_file:
        return error_file_download(returns_file)
    wb, ws = get_work_sheet('custom_order_form', CUSTOM_ORDER_MAPPING.keys())
    return xls_to_response(wb, '%s.custom_order_form.xls' % str(user.id))


@csrf_exempt
def validate_custom_order_form(reader, user, no_of_rows, no_of_cols, fname, file_type=''):
    from stock_locator import get_quantity_data
    index_status = {}
    customorder_file_mapping = copy.deepcopy(CUSTOM_ORDER_DEF_EXCEL)
    if not customorder_file_mapping:
        return 'Invalid File'
    cust_types = ['Price Customization', 'Price and Product Customization']
    warehouse_qs = UserGroups.objects.filter(admin_user=user.id)
    dist_users = warehouse_qs.filter(user__userprofile__warehouse_level=1).values_list('user_id__username', flat=True)
    wh_userids = warehouse_qs.values_list('user_id', flat=True)
    reseller_qs = CustomerUserMapping.objects.filter(customer__user__in=wh_userids)
    reseller_ids_map = dict(reseller_qs.values_list('user_id__username', 'customer__id'))
    reseller_ids = reseller_ids_map.values()
    reseller_users = reseller_ids_map.keys()
    res_corp_qs = CorpResellerMapping.objects.filter(reseller_id__in=reseller_ids).values_list('reseller_id',
                                                                                               'corporate_id')
    sku_codes = SKUMaster.objects.filter(user=user.id).values_list('sku_code', flat=True)
    res_corp_map = {}
    res_corp_names_map = {}
    for res_id, corp_id in res_corp_qs:
        res_corp_map.setdefault(res_id, []).append(corp_id)
    for res_id, corp_ids in res_corp_map.items():
        corp_names = CorporateMaster.objects.filter(id__in=corp_ids).values_list('name', flat=True)
        res_corp_names_map.setdefault(res_id, []).extend(corp_names)

    for row_idx in range(1, no_of_rows):
        for key, value in customorder_file_mapping.iteritems():
            cell_data = get_cell_data(row_idx, customorder_file_mapping[key], reader, file_type)
            if key == 'reseller_name':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add("Reseller Name is missing")
                # else:
                #     if cell_data not in reseller_users:
                #         index_status.setdefault(row_idx, set()).add("Reseller Name not found")
            elif key == 'customer_name':
                res_code = get_cell_data(row_idx, customorder_file_mapping['reseller_name'], reader, file_type)
                res_id = reseller_ids_map.get(res_code, '')
                mapped_corp_names = res_corp_names_map.get(res_id, [])
                if cell_data:
                   if cell_data not in mapped_corp_names:
                        index_status.setdefault(row_idx, set()).add('Corporate Name not mapped with Reseller')
                else:
                    index_status.setdefault(row_idx, set()).add('Corporate Name Missing')
            elif key == 'sku_code':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add("SKU Code is missing")
                else:
                    if cell_data not in sku_codes:
                        index_status.setdefault(row_idx, set()).add('Invalid SKU Code')
            elif key == 'customization_type':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add("Customization Type is missing")
                else:
                    if cell_data not in cust_types:
                        index_status.setdefault(row_idx, set()).add('Invalid Customization Type')
            elif key == 'ask_price':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add("Ask Price is missing")
                else:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Invalid Ask Price')
            elif key == 'quantity':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add("Quantity Missing")
                else:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Invalid Quantity Amount')
            elif key == 'client_po_rate':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Client PO Rate is Missing')
                else:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Invalid Client PO Rate')
            elif key == 'expected_date':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Approx Delivery Date is Missing')
                # else:
                #     try:
                #         exp_date = xldate_as_tuple(cell_data, 0)
                #     except:
                #         index_status.setdefault(row_idx, set()).add('Appx Delivery Date is not proper')
            elif key == 'remarks':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Remarks field is Missing')
                # else:
                #     if not isinstance(cell_data, (int, float)):
                #         index_status.setdefault(row_idx, set()).add('Invalid Client PO Rate')
            else:
                index_status.setdefault(row_idx, set()).add('Invalid Field')

    if not index_status:
        return 'Success'

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name


def custom_order_xls_upload(request, reader, user, admin_user, no_of_rows, fname, file_type='xls', no_of_cols=0):
    log.info("Custom Order upload started")
    custom_order_file_mapping = copy.deepcopy(CUSTOM_ORDER_DEF_EXCEL)
    custom_maps = {'Price Customization': 'price_custom', 'Price and Product Customization': 'price_product_custom'}
    user_enq_map = dict(ManualEnquiry.objects.values_list('user', 'enquiry_id'))
    try:
        for row_idx in range(1, no_of_rows):
            if not custom_order_file_mapping:
                continue
            each_row_map = copy.deepcopy(CUSTOM_ORDER_DEF_EXCEL)
            for key, value in custom_order_file_mapping.iteritems():
                each_row_map[key] = get_cell_data(row_idx, value, reader, file_type)

            MANUAL_ENQUIRY_DICT = {'customer_name': '', 'sku_id': '', 'customization_type': '', 'quantity': '',
                                   'client_po_rate': ''}
            MANUAL_ENQUIRY_DETAILS_DICT = {'ask_price': '', 'expected_date': '', 'remarks': ''}
            manual_enquiry = copy.deepcopy(MANUAL_ENQUIRY_DICT)
            manual_enquiry_details = copy.deepcopy(MANUAL_ENQUIRY_DETAILS_DICT)
            for key, value in MANUAL_ENQUIRY_DICT.iteritems():
                value = each_row_map.get(key, '')
                if key == 'sku_id':
                    value = each_row_map.get('sku_code')
                    sku_data = SKUMaster.objects.filter(user=user.id, sku_code=value)
                    if not sku_data:
                        return HttpResponse("Style Not Found")
                    value = sku_data[0].id
                elif key == 'quantity':
                    value = int(value)
                elif key == 'customization_type':
                    value = custom_maps.get(value, '')
                manual_enquiry[key] = value
            manual_enquiry['status'] = 'new_order'
            for key, value in MANUAL_ENQUIRY_DETAILS_DICT.iteritems():
                value = each_row_map.get(key, '')
                if key == 'ask_price' and each_row_map['customization_type'] == 'Price and Product Customization':
                    manual_enquiry_details[key] = 0
                    continue
                if key == 'ask_price':
                    value = float(value)
                elif key == 'expected_date':
                    try:
                        year, month, day, hour, minute, second = xldate_as_tuple(value, 0)
                        value = datetime.datetime(year, month, day, hour, minute, second)
                    except Exception as e:
                        log.info("Expected Date Validation Error in Custom Order Upload")
                manual_enquiry_details[key] = value
            res_id = User.objects.filter(username=each_row_map.get('reseller_name'))
            manual_enquiry['user_id'] = res_id[0].id
            enq_id = user_enq_map.get(res_id[0].id)
            if enq_id:
                enq_id = int(enq_id) + 1
            else:
                enq_id = 10001
            manual_enquiry['enquiry_id'] = enq_id
            enq_data = ManualEnquiry(**manual_enquiry)
            enq_data.save()
            manual_enquiry_details['enquiry_id'] = enq_id
            manual_enquiry_details['order_user_id'] = res_id[0].id
            manual_enquiry_details['remarks_user_id'] = res_id[0].id  # Remarks mentioned by user in order placement
            manual_enq_data = ManualEnquiryDetails(**manual_enquiry_details)
            manual_enq_data.save()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Custom Order Placement failed. User: %s, Params: %s, Error: %s'
                 %(user.username, str(request.POST.dict()), str(e)))
        return HttpResponse("Custom Order Placement failed")
    return HttpResponse("Success")


@csrf_exempt
@login_required
@get_admin_user
def custom_order_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        price_band_flag = get_misc_value('priceband_sync', user.id)
        if price_band_flag == 'true':
            admin_user = get_admin(user)
        else:
            admin_user = user
        status = validate_custom_order_form(reader, admin_user, no_of_rows, no_of_cols, fname, file_type=file_type)
        if status != 'Success':
            return HttpResponse(status)
        upload_status = custom_order_xls_upload(request, reader, user, admin_user, no_of_rows, fname,
                                                file_type=file_type, no_of_cols=no_of_cols)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Custom Order form Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Custom Order Upload Failed")
    if not upload_status == 'Success':
        return HttpResponse(upload_status)
    return HttpResponse('Success')
