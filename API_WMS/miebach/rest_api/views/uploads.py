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
from masters import *
from miebach_utils import *
from django.core import serializers
import csv
from sync_sku import *
from outbound import get_syncedusers_mapped_sku
from rest_api.views.excel_operations import write_excel_col, get_excel_variables
from inbound_common_operations import *
from stockone_integrations.views import Integrations

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
        del excel_headers["Weight"]
    return excel_headers


def get_move_inventory_excel_upload_headers(user):
    excel_headers = copy.deepcopy(MOVE_INVENTORY_EXCEL_MAPPING)
    userprofile = user.userprofile
    if not userprofile.user_type == 'marketplace_user':
        del excel_headers["Seller ID"]
    if not userprofile.industry_type == 'FMCG':
        del excel_headers["Batch Number"]
        del excel_headers["MRP"]
        del excel_headers["Weight"]
    return excel_headers


def get_sku_substitution_excel_headers(user):
    excel_headers = copy.deepcopy(SKU_SUBSTITUTION_EXCEL_MAPPING)
    userprofile = user.userprofile
    if not userprofile.user_type == 'marketplace_user':
        del excel_headers["Seller ID"]
    if not userprofile.industry_type == 'FMCG':
        del excel_headers["Source Batch Number"]
        del excel_headers["Source MRP"]
        del excel_headers["Source Weight"]
        del excel_headers["Destination Batch Number"]
        del excel_headers["Destination MRP"]
        del excel_headers["Destination Weight"]
    return excel_headers


def get_combo_allocate_excel_headers(user):
    excel_headers = copy.deepcopy(COMBO_ALLOCATE_EXCEL_MAPPING)
    userprofile = user.userprofile
    if not userprofile.user_type == 'marketplace_user':
        del excel_headers["Seller ID"]
    if not userprofile.industry_type == 'FMCG':
        del excel_headers["Combo Batch Number"]
        del excel_headers["Combo MRP"]
        del excel_headers["Combo Weight"]
        del excel_headers["Child Batch Number"]
        del excel_headers["Child MRP"]
        del excel_headers["Child Weight"]
    return excel_headers


def get_purchase_order_excel_headers(user):
    excel_headers = copy.deepcopy(PURCHASE_ORDER_UPLOAD_MAPPING)
    misc_detail = MiscDetail.objects.filter(user=user.id, misc_type='po_fields')
    if misc_detail:
        extra_headers = OrderedDict()
        fields = misc_detail[0].misc_value.split(',')
        for field in fields:
            key = field
            value = field.lower()
            extra_headers[key] = value
        excel_headers.update(extra_headers)
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
        del excel_headers["Weight"]
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
    log.info("order upload started for %s" % str(user.username))
    order_code_prefix_check = ['Delivery Challan', 'sample', 'R&D', 'CO', 'Pre Order', 'DC', 'PRE']
    order_code_prefix = get_order_prefix(user.id)
    if order_code_prefix:
        order_code_prefix_check.insert(0, order_code_prefix)
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
                                                      order_code__in=[order_code_prefix, 'Delivery Challan', 'sample', 'R&D', 'CO'])
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
            elif cell_data:
                if isinstance(cell_data, float):
                    cell_data = str(int(cell_data))
                cell_data_code = (''.join(re.findall('\D+', cell_data))).replace("'", "").replace("`", "")
                if cell_data_code and cell_data_code.lower() in map(lambda x: str(x).lower(), order_code_prefix_check):
                    index_status.setdefault(count, set()).add('Order id prefix is a reserved prefix. Please change and upload')
                    break
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
        if order_mapping.has_key('quantity'):
            quantity_check = get_cell_data(row_idx, order_mapping['quantity'], reader, file_type)
            if int(quantity_check) == 0:
                index_status.setdefault(count, set()).add('Quantity is given zero')
            get_decimal_data(quantity_check,index_status,count,user)

        if type(cell_data) == float:
            sku_code = str(int(cell_data))
        #elif isinstance(cell_data, str) and '.' in cell_data:
        #    sku_code = str(int(float(cell_data)))
        else:
            sku_code = str(cell_data).upper()

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
                    order_data['order_code'] = order_code_prefix

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
            elif key == 'ship_to':
                consignee = get_cell_data(row_idx, value, reader, file_type)
                if consignee:
                    order_summary_dict['consignee'] = get_cell_data(row_idx, value, reader, file_type)
            elif key == 'quantity_count':
                if isinstance(value, (list)):
                    try:
                        cell_data = get_cell_data(row_idx, value[0], reader, file_type)
                        order_data['quantity'] = len(cell_data.split(value[1]))
                    except:
                        order_data['quantity'] = 1
            elif key == 'amount':
                cell_data = get_cell_data(row_idx, value, reader, file_type)
                if cell_data:
                    cell_data = float(cell_data)
                else:
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
            order_data['order_code'] = order_code_prefix
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
    log.info("order upload ended for %s" % str(user.username))
    return 'success'


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def order_upload(request, user=''):
    reversion.set_user(request.user)
    reversion.set_comment("upload_order")
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

    return xls_to_response(wb, '%s.order_form.xls' % str(user.username))


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
    if not request.user.is_staff:
        headers = list(filter(('Block For PO').__ne__, headers))
    wb, ws = get_work_sheet('skus', headers)

    return xls_to_response(wb, '%s.sku_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def asset_form(request, user=''):
    asset_file = request.GET['download-sku-file']
    if asset_file:
        return error_file_download(asset_file)
    headers = copy.deepcopy(ASSET_HEADERS)
    wb, ws = get_work_sheet('assets', headers)
    return xls_to_response(wb, '%s.asset_form.xls' % str(user.username))

@csrf_exempt
@get_admin_user
def test_form(request, user=''):
    test_file = request.GET['download-sku-file']
    if test_file:
        return error_file_download(test_file)
    headers = copy.deepcopy(TEST_MASTER_HEADERS)
    wb, ws = get_work_sheet('test', headers)
    return xls_to_response(wb, '%s.test_form.xls' % str(user.username))

@csrf_exempt
@get_admin_user
def machine_form(request, user=''):
    machine_file = request.GET['download-machine-file']
    if machine_file:
        return error_file_download(machine_file)
    headers = copy.deepcopy(MACHINE_MASTER_HEADERS)
    wb, ws = get_work_sheet('machine', headers)
    return xls_to_response(wb, '%s.machine_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def service_form(request, user=''):
    service_file = request.GET['download-sku-file']
    if service_file:
        return error_file_download(service_file)
    headers = copy.deepcopy(SERVICE_HEADERS)
    wb, ws = get_work_sheet('service', headers)
    return xls_to_response(wb, '%s.service_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def otheritems_form(request, user=''):
    otheritems_file = request.GET['download-sku-file']
    if otheritems_file:
        return error_file_download(otheritems_file)
    headers = copy.deepcopy(OTHER_ITEM_HEADERS)
    wb, ws = get_work_sheet('other_items', headers)
    return xls_to_response(wb, '%s.otheritems_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def sales_returns_form(request, user=''):
    returns_file = request.GET['download-sales-returns']
    if returns_file:
        return error_file_download(returns_file)

    sales_retun_mapping = copy.deepcopy(SALES_RETURNS_HEADERS)
    if user.userprofile.user_type == 'marketplace_user':
        sales_retun_mapping.append('SOR ID')
        sales_retun_mapping.append('Seller ID')
    wb, ws = get_work_sheet('returns', sales_retun_mapping)
    return xls_to_response(wb, '%s.returns_form.xls' % str(user.username))


@csrf_exempt
@login_required
@get_admin_user
def inventory_form(request, user=''):
    inventory_file = request.GET['download-file']
    if inventory_file:
        return error_file_download(inventory_file)
    excel_headers = get_inventory_excel_upload_headers(user)
    wb, ws = get_work_sheet('Inventory', excel_headers.keys())
    return xls_to_response(wb, '%s.inventory_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def supplier_form(request, user=''):
    supplier_file = request.GET['download-supplier-file']
    if supplier_file:
        return error_file_download(supplier_file)
    supplier_headers = copy.deepcopy(SUPPLIER_HEADERS)
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        supplier_headers.append('EP Supplier(yes/no)')
    wb, ws = get_work_sheet('supplier', supplier_headers)
    return xls_to_response(wb, '%s.supplier_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def supplier_sku_form(request, user=''):
    supplier_file = request.GET['download-supplier-sku-file']
    if supplier_file:
        return error_file_download(supplier_file)
    headers = copy.deepcopy(SUPPLIER_SKU_HEADERS)
    if user.userprofile.warehouse_level != 0:
        del headers['Warehouse']
    wb, ws = get_work_sheet('supplier', headers)
    return xls_to_response(wb, '%s.supplier_sku_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def location_form(request, user=''):
    loc_file = request.GET['download-loc-file']
    if loc_file:
        return error_file_download(loc_file)

    wb, ws = get_work_sheet('Locations', LOCATION_HEADERS)
    return xls_to_response(wb, '%s.location_form.xls' % str(user.username))


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

    return xls_to_response(wb, '%s.purchase_order_form.xls' % str(user.username))


@csrf_exempt
@login_required
@get_admin_user
def move_inventory_form(request, user=''):
    inventory_file = request.GET['download-move-inventory-file']
    if inventory_file:
        return error_file_download(inventory_file)
    excel_headers = get_move_inventory_excel_upload_headers(user)
    wb, ws = get_work_sheet('Inventory', excel_headers)
    return xls_to_response(wb, '%s.move_inventory_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def marketplace_sku_form(request, user=''):
    market_list = ['SKU Code']
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
    return xls_to_response(wb, '%s.marketplace_sku_form.xls' % str(user.username))


@csrf_exempt
@login_required
@get_admin_user
def bom_form(request, user=''):
    bom_file = request.GET['download-bom-file']
    if bom_file:
        return error_file_download(bom_file)
    wb, ws = get_work_sheet('BOM', BOM_UPLOAD_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.bom_form.xls' % str(user.username))


@csrf_exempt
@login_required
@get_admin_user
def combo_sku_form(request, user=''):
    combo_sku_file = request.GET['download-combo-sku-file']
    if combo_sku_file:
        return error_file_download(combo_sku_file)
    wb, ws = get_work_sheet('COMBO_SKU', COMBO_SKU_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.combo_sku_form.xls' % str(user.username))


@csrf_exempt
@login_required
@get_admin_user
def inventory_adjust_form(request, user=''):
    inventory_file = request.GET['download-inventory-adjust-file']
    if inventory_file:
        return error_file_download(inventory_file)
    excel_headers = get_inventory_adjustment_excel_upload_headers(user)
    wb, ws = get_work_sheet('INVENTORY_ADJUST', excel_headers)
    return xls_to_response(wb, '%s.inventory_adjustment_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def vendor_form(request, user=''):
    vendor_file = request.GET['download-vendor-file']
    if vendor_file:
        return error_file_download(vendor_file)

    wb, ws = get_work_sheet('vendor', VENDOR_HEADERS)
    return xls_to_response(wb, '%s.vendor_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def pricing_master_form(request, user=''):
    returns_file = request.GET['download-pricing-master']
    if returns_file:
        return error_file_download(returns_file)

    wb, ws = get_work_sheet('Prices', PRICING_MASTER_HEADERS)
    return xls_to_response(wb, '%s.pricing_master_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def network_master_form(request, user=''):
    returns_file = request.GET['download-network-master']
    if returns_file:
        return error_file_download(returns_file)

    wb, ws = get_work_sheet('Network', NETWORK_MASTER_HEADERS)
    return xls_to_response(wb, '%s.network_master_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def order_label_mapping_form(request, user=''):
    label_file = request.GET['order-label-mapping-form']
    if label_file:
        return error_file_download(label_file)

    wb, ws = get_work_sheet('Order Labels', ORDER_LABEL_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.order_label_mapping_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def order_serial_mapping_form(request, user=''):
    label_file = request.GET['order-serial-mapping-form']
    if label_file:
        return error_file_download(label_file)

    wb, ws = get_work_sheet('Order Serials', ORDER_SERIAL_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.order_serial_mapping_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def po_serial_mapping_form(request, user=''):
    label_file = request.GET['po-serial-mapping-form']
    if label_file:
        return error_file_download(label_file)

    wb, ws = get_work_sheet('PO Serials', PO_SERIAL_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.po_serial_mapping_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def job_order_form(request, user=''):
    label_file = request.GET['job-order-file']
    if label_file:
        return error_file_download(label_file)

    wb, ws = get_work_sheet('Job Order', JOB_ORDER_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.job_order_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def marketplace_serial_form(request, user=''):
    label_file = request.GET['marketplace-serial-file']
    if label_file:
        return error_file_download(label_file)

    wb, ws = get_work_sheet('Marketplace Serial', MARKETPLACE_SERIAL_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.marketplace_serial_form.xls' % str(user.username))


@csrf_exempt
@get_admin_user
def orderid_awb_mapping_form(request, user=''):
    label_file = request.GET['orderid-awb-map-file']
    if label_file:
        return error_file_download(label_file)

    wb, ws = get_work_sheet('Awb Map', ORDER_ID_AWB_MAP_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.order_id_awb_mapping_form.xls' % str(user.username))


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
def validate_substitutes_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type='xls'):
    index_status = {}
    for row_idx in range(1, no_of_rows):
        cell_data = reader.row_values(row_idx)
        skus = map(lambda sku: str(sku), cell_data)
        for sku in skus:
            if 'invalid' in sku.lower():
                skus.remove(sku)
        skus = ' '.join(skus).split()
        sku_records = SKUMaster.objects.filter(user=user.id, sku_code__in=skus).values('sku_code', 'id')
        error_skus = set(skus) - set(sku_records.values_list('sku_code', flat=True))
        if error_skus:
            index_status.setdefault(row_idx, set()).add('Invalid sku codes %s' % (','.join(str(s) for s in error_skus)))
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
def validate_sku_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type='xls', attributes={},
                        is_asset=False, is_service=False, is_test=False):
    sku_data = []
    wms_data = []
    index_status = {}
    upload_file_skus = []
    ean_duplicate_check = []
    sku_file_mapping = get_sku_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type)
    if is_asset:
        sku_file_mapping = get_asset_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type)
    if is_service:
        sku_file_mapping = get_service_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type)
    if is_test:
        sku_file_mapping = get_test_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type)

    product_types = list(TaxMaster.objects.filter(user_id=user.id).values_list('product_type', flat=True).distinct())
    zones_dict = dict(ZoneMaster.objects.filter(user=user.id).values_list('zone', 'id'))
    zones_list = map(lambda x:x.upper(),zones_dict)
    if not sku_file_mapping:
        return 'Invalid File'

    exist_sku_eans = dict(SKUMaster.objects.filter(user=user.id, status=1).exclude(ean_number='').\
                          only('ean_number', 'sku_code').values_list('ean_number', 'sku_code'))
    exist_ean_list = dict(EANNumbers.objects.filter(sku__user=user.id, sku__status=1).\
                          only('ean_number', 'sku__sku_code').values_list('ean_number', 'sku__sku_code'))
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
                if sku_code in upload_file_skus:
                    index_status.setdefault(row_idx, set()).add('Duplicate SKU Code found in File')
                else:
                    upload_file_skus.append(sku_code)
                # index_status = check_duplicates(data_set, data_type, cell_data, index_status, row_idx)
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('WMS Code missing')
            elif key == 'test_code' and is_test:
                data_set = wms_data
                data_type = 'WMS'
                test_code = cell_data
                # if isinstance(cell_data, float):
                #     sku_code = str(int(cell_data))
                #     test_code = str(int(cell_data))
                #     check_test_master = TestMaster.objects.filter(test_code = cell_data)
                #     if check_test_master.exists():
                #         index_status.setdefault(row_idx, set()).add('Duplicate Test Code found in File')
                #     else:
                #         upload_file_skus.append(str(test_code))
                #     # index_status = check_duplicates(data_set, data_type, cell_data, index_status, row_idx)
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Test Code missing')
            if key == 'test_name' and is_test:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Test Name missing')
            elif key == 'test_type' and is_test:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Test Type missing')
            elif key == 'department_type' and is_test:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Department Type missing')
            elif key == 'status' and is_test:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('status missing')

            elif key == 'sku_group':
                if cell_data:
                    sku_groups = SKUGroups.objects.filter(group__iexact=cell_data, user=user.id)
                    if not sku_groups:
                        index_status.setdefault(row_idx, set()).add("Group doesn't exists")

            elif key == 'zone_id':
                if cell_data:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    #data = ZoneMaster.objects.filter(zone=cell_data.upper(), user=user.id)
                    if not str(cell_data).upper() in zones_list:
                        index_status.setdefault(row_idx, set()).add('Invalid Zone')
                        # else:
                        #    index_status.setdefault(row_idx, set()).add('Zone should not be empty')
            elif key == 'ean_number':
                if cell_data:
                    try:
                        if ',' in str(cell_data):
                            ean_numbers = str(cell_data).split(',')
                        else:
                            if isinstance(cell_data, float):
                                cell_data = int(cell_data)
                            ean_numbers = [cell_data]
                        error_eans = []
                        '''for ean in ean_numbers:
                            ean_status, mapping_check = check_ean_number(sku_code, ean, user)
                            if ean_status:
                                error_eans.append(str(ean))
                        if error_eans:
                            ean_error_msg = '%s EAN Numbers already mapped to Other SKUS' % ','.join(error_eans)
                            index_status.setdefault(row_idx, set()).add(ean_error_msg)'''
                        for temp_ean in ean_numbers:
                            if not temp_ean:
                                continue
                            temp_ean = str(temp_ean)
                            if len(temp_ean) > 20:
                                error_msg = 'EAN Number Length should be less than 20'
                                index_status.setdefault(row_idx, set()).add(error_msg)
                            if temp_ean in ean_duplicate_check:
                                error_msg = 'Duplicate EAN Number Found in File'
                                index_status.setdefault(row_idx, set()).add(error_msg)
                            else:
                                ean_duplicate_check.append(temp_ean)
                            if temp_ean in exist_ean_list:
                                if not str(exist_ean_list[temp_ean]) == str(sku_code):
                                    error_message = str(temp_ean) + ' EAN Number already mapped to SKU ' + str(exist_ean_list[temp_ean])
                                    index_status.setdefault(row_idx, set()).add(error_message)
                            elif temp_ean in exist_sku_eans:
                                if not str(exist_sku_eans[temp_ean]) == str(sku_code):
                                    error_message = str(temp_ean) + ' EAN Number already mapped to SKU ' + str(exist_sku_eans[temp_ean])
                                    index_status.setdefault(row_idx, set()).add(error_msg)
                    except Exception as e:
                        import traceback
                        log.debug(traceback.format_exc())
                        log.info('SKU Master Upload failed for %s and params are %s and error statement is %s' % (
                        str(user.username), str(request.POST.dict()), str(e)))

            elif key == 'hsn_code':
                #if not cell_data:
                #    index_status.setdefault(row_idx, set()).add('hsn Code missing')
                if cell_data:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    # if not len(cell_data) == 8:
                    #     index_status.setdefault(row_idx, set()).add('HSN Code should be 8 digit')

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
            elif key == 'batch_based':
                if cell_data:
                    if not str(cell_data).lower() in ['enable', 'disable']:
                        index_status.setdefault(row_idx, set()).add('Batch Based Should be Enable or Disable')
            elif key == 'enable_serial_based':
                if cell_data:
                    if not str(cell_data).lower() in ['enable', 'disable']:
                        index_status.setdefault(row_idx, set()).add('Enable Serial Number Should be Enable or Disable')
            elif key == 'sequence':
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Sequence should be in number')
            elif key == 'block_options':
                if not cell_data in ['Yes', 'No', '']:
                    index_status.setdefault(row_idx, set()).add('Block For PO should be Yes/No')
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


def get_asset_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type):
    sku_mapping = copy.deepcopy(ASSET_COMMON_MAPPING)
    sku_file_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 sku_mapping)
    return sku_file_mapping


def get_service_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type):
    sku_mapping = copy.deepcopy(SERVICEMASTER_COMMON_MAPPING)
    sku_file_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 sku_mapping)
    return sku_file_mapping

def get_test_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type):
    sku_mapping = copy.deepcopy(TEST_COMMON_MAPPING)
    sku_file_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                sku_mapping)
    return sku_file_mapping


def get_otheritem_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type):
    sku_mapping = copy.deepcopy(OTHERITEMS_COMMON_MAPPING)
    sku_file_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 sku_mapping)
    return sku_file_mapping

def sku_excel_upload(request, reader, user, no_of_rows, no_of_cols, fname, file_type='xls', attributes={},
                        is_asset=False, is_service=False, is_item=False, is_test=False):
    from masters import check_update_size_type
    from masters import check_update_hot_release
    from api_calls.netsuite import netsuite_update_create_sku
    from api_calls.netsuite import netsuite_sku_bulk_create
    from api_calls.netsuite import netsuite_update_create_service, netsuite_update_create_assetmaster, netsuite_update_create_otheritem_master
    all_sku_masters = []
    zone_master = ZoneMaster.objects.filter(user=user.id).values('id', 'zone')
    zones = map(lambda d: str(d['zone']).upper(), zone_master)
    zone_ids = map(lambda d: d['id'], zone_master)
    create_sku_attrs = []
    sku_attr_mapping = []
    instanceName = SKUMaster
    sku_file_mapping = get_sku_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type)
    if is_asset:
        instanceName = AssetMaster
        sku_file_mapping = get_asset_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type)
    if is_service:
        instanceName = ServiceMaster
        sku_file_mapping = get_service_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type)
    if is_test:
        instanceName = TestMaster
        sku_file_mapping = get_test_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type)
    if is_item:
        instanceName = OtherItemsMaster
        sku_file_mapping = get_otheritem_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type)
    new_skus = OrderedDict()
    exist_sku_eans = dict(SKUMaster.objects.filter(user=user.id, status=1).exclude(ean_number='').\
                          only('ean_number', 'sku_code').values_list('ean_number', 'sku_code'))
    exist_ean_list = dict(EANNumbers.objects.filter(sku__user=user.id, sku__status=1).\
                          only('ean_number', 'sku__sku_code').values_list('ean_number', 'sku__sku_code'))
    for row_idx in range(1, no_of_rows):
        if not sku_file_mapping:
            continue

        data_dict = copy.deepcopy(SKU_DATA)
        if is_service:
            data_dict.update(SERVICE_SKU_DATA)
        if is_asset:
            data_dict.update(ASSET_SKU_DATA)
        if is_item:
            data_dict.update(OTHERITEMS_SKU_DATA)
        if is_test:
            data_dict.update(TEST_SKU_DATA)

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

            elif key == 'max_norm_quantity':
                if not cell_data:
                    cell_data = 0
                if sku_data and cell_data:
                    sku_data.max_norm_quantity = cell_data
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
                        if isinstance(cell_data, float):
                            cell_data = int(cell_data)
                        ean_numbers = [str(cell_data)]
            elif key == 'enable_serial_based':
                toggle_value = str(cell_data).lower()
                if toggle_value == "enable":
                    cell_data = 1
                if toggle_value == "disable":
                    cell_data = 0
                if not toggle_value:
                    cell_data = 0
                if toggle_value:
                    setattr(sku_data, key, cell_data)
                    data_dict[key] = cell_data
            elif key == 'batch_based':
                svaed_value = str(cell_data).lower()
                if svaed_value == "enable":
                    cell_data = 1
                if svaed_value == "disable":
                    cell_data = 0
                if not svaed_value:
                    cell_data = 0
                if svaed_value:
                    setattr(sku_data, key, cell_data)
                    data_dict[key] = cell_data
            elif key == 'block_options':
                if cell_data:
                    if str(cell_data).lower() == 'yes':
                        cell_data = 'PO'
                    if str(cell_data).lower() in ['no', '']:
                        cell_data = ''
                    setattr(sku_data, key, cell_data)
                    data_dict[key] = cell_data
            elif key in ['service_start_date', 'service_end_date']:
                if isinstance(cell_data, float):
                    year, month, day, hour, minute, second = xldate_as_tuple(cell_data, 0)
                    reqDate = datetime.datetime(year, month, day, hour, minute, second)
                elif '-' in cell_data:
                    reqDate = datetime.datetime.strptime(cell_data, "%Y-%m-%d")
                else:
                    reqDate = None
                data_dict[key] = reqDate
            elif key == 'hsn_code':
                if cell_data:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                data_dict[key] = cell_data
                if sku_data:
                    setattr(sku_data, key, cell_data)
                data_dict[key] = cell_data
            # elif key == 'asset_number':
            #     if isinstance(cell_data, float):
            #         if sku_data:
            #             setattr(sku_data, key, cell_data)
            #         data_dict[key] = cell_data

            elif cell_data:
                data_dict[key] = cell_data
                if sku_data:
                    setattr(sku_data, key, cell_data)
                data_dict[key] = cell_data
        if is_test:
            data_dict['wms_code'] = str(data_dict['test_code'])
            data_dict['sku_desc'] = str(data_dict['test_name'])

        if instanceName.__name__ in ['AssetMaster', 'ServiceMaster', 'OtherItemsMaster', 'TestMaster'] and not sku_data:
            data_dict['sku_code'] = data_dict['wms_code']
            if instanceName.__name__ in ['AssetMaster', 'ServiceMaster', 'OtherItemsMaster', 'TestMaster']:
                respFields = [f.name for f in instanceName._meta.get_fields()]
                for k, v in data_dict.items():
                    if k not in respFields:
                        data_dict.pop(k)
            if is_test:
                check_sku_data = SKUMaster.objects.get(sku_code=data_dict['wms_code'])
                if check_sku_data:
                    check_sku_data.delete()
            sku_data = instanceName(**data_dict)
            sku_data.save()
        if sku_data:
            sku_data.save()
            upload_netsuite_sku(sku_data, user,instanceName)
            all_sku_masters.append(sku_data)
            if _size_type:
                check_update_size_type(sku_data, _size_type)
            if hot_release:
                hot_release = 1 if (hot_release == 'enable') else 0
                check_update_hot_release(sku_data, hot_release)
            for attr_key, attr_val in attr_dict.iteritems():
                if attr_val:
                    if attributes[attr_key] == 'Multi Input':
                        attr_vals = attr_val.split(',')
                        allow_multiple = True
                    else:
                        attr_vals = [attr_val]
                        allow_multiple = False
                else:
                    attr_vals = []
                for attr_key_val in attr_vals:
                    create_sku_attrs, sku_attr_mapping, remove_attr_ids = update_sku_attributes_data(sku_data, attr_key, attr_key_val, is_bulk_create=True,
                                                            create_sku_attrs=create_sku_attrs, sku_attr_mapping=sku_attr_mapping,
                                                            allow_multiple=allow_multiple)

            if ean_numbers:
                update_ean_sku_mapping(user, ean_numbers, sku_data, remove_existing=True)

        if not sku_data:
            data_dict['sku_code'] = data_dict['wms_code']

            if instanceName.__name__ in ['AssetMaster', 'ServiceMaster', 'OtherItemsMaster', 'TestMaster']:
                respFields = [f.name for f in instanceName._meta.get_fields()]
                for k, v in data_dict.items():
                    if k not in respFields:
                        data_dict.pop(k)
            if is_test:
                data_dict['test_code'] = str(data_dict['test_code'])
                data_dict['test_name'] = str(data_dict['test_name'])
                data_dict['test_type'] = str(data_dict['test_type'])
                data_dict['department_type'] = str(data_dict['department_type'])
                data_dict['sku_code'] = data_dict['test_code']
                data_dict['sku_desc'] = data_dict['test_name']
                test_respone = validate_test_data(data_dict)
                data_dict = test_reponse
            sku_master = instanceName(**data_dict)
            #sku_master = SKUMaster(**data_dict)
            #new_skus.append(sku_master)
            new_skus[data_dict['sku_code']] = {'sku_obj': sku_master}
            if _size_type:
                new_skus[data_dict['sku_code']]['size_type'] = _size_type
            if hot_release:
                new_skus[data_dict['sku_code']]['hot_release'] = hot_release
            if attr_dict:
                new_skus[data_dict['sku_code']]['attr_dict'] = attr_dict
            if ean_numbers:
                new_skus[data_dict['sku_code']]['ean_numbers'] = ean_numbers
            #sku_master.save()
            #all_sku_masters.append(sku_master)
            #sku_data = sku_master
    if new_skus:
        new_ean_objs = []
        new_sku_objs = map(lambda d: d['sku_obj'], new_skus.values())
        bulk_create_in_batches(instanceName, new_sku_objs)
        #SKUMaster.objects.bulk_create(new_sku_objs)
        new_sku_master = SKUMaster.objects.filter(user=user.id, sku_code__in=new_skus.keys())
        all_sku_masters = list(chain(all_sku_masters, new_sku_master))
        sku_key_map = OrderedDict(new_sku_master.values_list('sku_code', 'id'))
        res=upload_bulk_insert_sku(instanceName, sku_key_map, new_skus, user)
        # res= netsuite_sku_bulk_create(instanceName, sku_key_map, new_skus)
        for sku_code, sku_id in sku_key_map.items():
            sku_data = SKUMaster.objects.get(id=sku_id)
            if new_skus[sku_code].get('size_type', ''):
                check_update_size_type(sku_data, new_skus[sku_code].get('size_type', ''))
            if new_skus[sku_code].get('hot_release', '') != '':
                hot_release = new_skus[sku_code].get('size_type', '')
                hot_release = 1 if (hot_release == 'enable') else 0
                check_update_hot_release(sku_data, hot_release)
            for attr_key, attr_val in new_skus[sku_code].get('attr_dict', {}).iteritems():
                if attr_val:
                    if attributes[attr_key] == 'Multi Input':
                        attr_vals = attr_val.split(',')
                        allow_multiple = True
                    else:
                        attr_vals = [attr_val]
                        allow_multiple = False
                else:
                    attr_vals = []
                for attr_key_val in attr_vals:
                    create_sku_attrs, sku_attr_mapping, remove_attr_ids = update_sku_attributes_data(sku_data, attr_key, attr_key_val, is_bulk_create=True,
                                               create_sku_attrs=create_sku_attrs, sku_attr_mapping=sku_attr_mapping, allow_multiple=allow_multiple)

            if new_skus[sku_code].get('ean_numbers', ''):
                ean_numbers = new_skus[sku_code].get('ean_numbers', '')
                sku_data, new_ean_objs, update_sku_obj = prepare_ean_bulk_data(sku_data, ean_numbers, exist_ean_list,
                                                                                exist_sku_eans, new_ean_objs=new_ean_objs)
        if new_ean_objs:
            EANNumbers.objects.bulk_create(new_ean_objs)
    # get_user_sku_data(user)
    insert_update_brands(user)

    #Bulk Create SKU Attributes
    if create_sku_attrs:
        SKUAttributes.objects.bulk_create(create_sku_attrs)

    # Sync sku's with sister warehouses
    sync_sku_switch = get_misc_value('sku_sync', user.id)
    if sync_sku_switch == 'true':
        all_users = get_related_users(user.id)
        create_update_sku(all_sku_masters, all_users)

    return 'success'

def upload_bulk_insert_sku(model_obj,  sku_key_map, new_skus, user):
    try:
        sku_list_dict=[]
        intObj = Integrations(user,'netsuiteIntegration')
        department, plant, subsidary=get_plant_subsidary_and_department(user)
        for sku_code, sku_id in sku_key_map.items():
            sku_master_data=new_skus[sku_code].get('sku_obj', {})
            sku_master_data=intObj.gatherSkuData(sku_master_data)
            sku_attr_dict=new_skus[sku_code].get('attr_dict', {})
            sku_attr_dict.update(sku_master_data)
            sku_attr_dict.update({'department': department, "subsidiary":subsidary, "plant":plant})
            sku_list_dict.append(sku_attr_dict)
        intObj.integrateSkuMaster(sku_list_dict,"sku_code", is_multiple= True)
    except Exception as e:
        print(e)

def upload_netsuite_sku(data, user, instanceName=''):
    try:
        intObj = Integrations(user,'netsuiteIntegration')
        sku_data_dict=intObj.gatherSkuData(data)
        department, plant, subsidary=get_plant_subsidary_and_department(user)
        sku_data_dict.update({'department': department, "subsidiary":subsidary, "plant":plant})
        if instanceName == ServiceMaster:
            sku_data_dict.update({"ServicePurchaseItem":True})
            intObj.integrateServiceMaster(sku_data_dict, "sku_code", is_multiple=False)
        elif instanceName == AssetMaster:
            sku_data_dict.update({"non_inventoryitem":True})
            intObj.integrateAssetMaster(sku_data_dict, "sku_code", is_multiple=False)
        elif instanceName == OtherItemsMaster:
            sku_data_dict.update({"non_inventoryitem":True})
            intObj.integrateOtherItemsMaster(sku_data_dict, "sku_code" , is_multiple=False)
        else:
            # # intObj.initiateAuthentication()
            # sku_data_dict.update(sku_attr_dict)
            intObj.integrateSkuMaster(sku_data_dict, "sku_code" , is_multiple=False)
    except Exception as e:
        print(e)

@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def sku_upload(request, user=''):
    try:
        reversion.set_user(request.user)
        reversion.set_comment("upload_sku")
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        user_attributes = get_user_attributes(user, 'sku')
        attributes = dict(user_attributes.values_list('attribute_name', 'attribute_type'))
        if get_cell_data(0, 0, reader, file_type) == 'Part Number':
            status = update_sku_make_model(request, reader, user, no_of_rows, no_of_cols, fname, file_type=file_type,
                         attributes=attributes)
            return HttpResponse(status)
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


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def asset_upload(request, user=''):
    try:
        reversion.set_user(request.user)
        reversion.set_comment("upload_asset")
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status = validate_sku_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type=file_type)
        if status != 'Success':
            return HttpResponse(status)
        sku_excel_upload(request, reader, user, no_of_rows, no_of_cols, fname, file_type=file_type, is_asset=True)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Asset Master Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Asset Master Upload Failed")

    return HttpResponse('Success')


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def service_upload(request, user=''):
    try:
        reversion.set_user(request.user)
        reversion.set_comment("upload_service")
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status = validate_sku_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type=file_type)
        if status != 'Success':
            return HttpResponse(status)
        sku_excel_upload(request, reader, user, no_of_rows, no_of_cols, fname, file_type=file_type, is_service=True)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Service Master Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Service Master Upload Failed")

    return HttpResponse('Success')

@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def test_upload(request, user=''):
    try:
        reversion.set_user(request.user)
        reversion.set_comment("upload_test")
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status = validate_sku_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type=file_type, is_test=True)
        if status != 'Success':
            return HttpResponse(status)
        sku_excel_upload(request, reader, user, no_of_rows, no_of_cols, fname, file_type=file_type, is_test=True)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Test Master Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Test Master Upload Failed")

    return HttpResponse('Success')

@csrf_exempt
@login_required
@get_admin_user
def machine_upload(request, user=''):
    try:
        user_id =user.id
        fname = request.FILES['files']
        if (fname.name).split('.')[-1] != 'xls' and (fname.name).split('.')[-1] != 'xlsx':
            return HttpResponse('Invalid File Format')

        try:
            open_book = open_workbook(filename=None, file_contents=fname.read())
            open_sheet = open_book.sheet_by_index(0)
        except:
            return HttpResponse('Invalid File')
        status = validate_machine_form(open_sheet, user_id)
        if status != 'Success':
            return HttpResponse(status)
        machine_excel_upload(request, open_sheet, user)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Machine Master Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Machine Master Upload Failed")

    return HttpResponse('Success')




@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def otheritems_upload(request, user=''):
    try:
        reversion.set_user(request.user)
        reversion.set_comment("upload_item")
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status = validate_sku_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type=file_type)
        if status != 'Success':
            return HttpResponse(status)
        sku_excel_upload(request, reader, user, no_of_rows, no_of_cols, fname, file_type=file_type, is_item=True)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('OtherItems Master Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("OtherItems Master Upload Failed")

    return HttpResponse('Success')


@csrf_exempt
@login_required
@get_admin_user
def sku_substitutes_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status = validate_substitutes_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type=file_type)
        if status != 'Success':
            return HttpResponse(status)
        substitutes_upload(request, reader, user, no_of_rows, no_of_cols, fname, file_type=file_type)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('SKU Master substitutes Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("SKU Master substitutes Upload Failed")

    return HttpResponse('Success')

@csrf_exempt
@login_required
@get_admin_user
def sku_substitutes_form(request, user=''):
    excel_file = request.GET['download-file']
    if excel_file:
        return error_file_download(excel_file)
    excel_headers = copy.deepcopy(SKU_SUBSTITUTES_EXCEL_MAPPING)
    wb, ws = get_work_sheet('SKU substitutes', excel_headers)
    return xls_to_response(wb, '%s.sku_substitutes_form.xls' % str(user.id))

@csrf_exempt
def substitutes_upload(request, reader, user, no_of_rows, no_of_cols, fname, file_type='xls'):
    for row_idx in range(1, no_of_rows):
        cell_data = reader.row_values(row_idx)
        skus = map(lambda sku: str(sku), cell_data)
        for sku in skus:
            if 'invalid' in sku.lower():
                skus.remove(sku)
        skus = ' '.join(skus).split()
        for sku in skus:
            substitutes_list = skus
            sku_obj = SKUMaster.objects.get(user = user.id, sku_code = sku)
            substitutes_list.remove(sku)
            for substitutes in substitutes_list:
                sub_obj = SKUMaster.objects.get(user=user.id, sku_code=substitutes)
                sku_obj.substitutes.add(sub_obj)


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
    location_obj = None
    inv_mapping = get_inventory_excel_upload_headers(user)
    unique_mrp = get_misc_value('unique_mrp_putaway', user.id)
    inv_res = dict(zip(inv_mapping.values(), inv_mapping.keys()))
    excel_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 inv_mapping)
    excel_check_list = ['receipt_date', 'quantity', 'wms_code', 'location', 'price']
    if user.userprofile.user_type == 'marketplace_user':
        excel_check_list.append('seller_id')
    if user.userprofile.industry_type == 'FMCG':
        excel_check_list.append('mrp')
        excel_check_list.append('weight')
    if not set(excel_check_list).issubset(excel_mapping.keys()):
        return 'Invalid File', []
    number_fields = ['quantity']
    optional_fields = ['mrp', 'price']
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
            elif key == 'weight':
                if isinstance(cell_data, float):
                    cell_data = str(int(cell_data))
                if user.username in MILKBASKET_USERS:
                    cell_data = str(cell_data)
                    cell_data = mb_weight_correction(cell_data)
                    if not cell_data:
                        index_status.setdefault(row_idx, set()).add('Weight is Mandatory')
                data_dict['weight'] = cell_data
            elif key == 'mrp':
                data_dict['mrp'] = cell_data
                if user.username in MILKBASKET_USERS and not cell_data:
                    index_status.setdefault(row_idx, set()).add('MRP is Mandatory')
            elif key == 'price':
                if cell_data >= 0:
                    data_dict['unit_price'] = cell_data
                else:
                    if not index_status:
                        custom_price = SKUMaster.objects.filter(id=data_dict['sku_id']).values('cost_price')[0]['cost_price']
                        data_dict['price_type'] = "cost_price"
            elif key in number_fields:
                try:
                    if key == 'quantity':
                        if isinstance(cell_data, float):
                            get_decimal_data(cell_data, index_status, row_idx, user)
                    data_dict[key] = float(cell_data)
                except:
                    if key not in optional_fields:
                        index_status.setdefault(row_idx, set()).add('Invalid Value for %s' % inv_res[key])
                data_dict[key] = cell_data
            else:
                data_dict[key] = cell_data
        if data_dict.has_key('weight') and data_dict.has_key('mrp'):
            sku_master = SKUMaster.objects.filter(id=data_dict['sku_id'])
            if user.username in MILKBASKET_USERS and unique_mrp == 'true' and sku_master and location_obj:
                sku_master = sku_master[0]
                data_dict['sku_code'] = sku_master.sku_code
                data_dict['location'] = location_obj[0].location
                status = validate_mrp_weight(data_dict,user)
                if status:
                    index_status.setdefault(row_idx, set()).add(status)
                if user.userprofile.industry_type == 'FMCG' :
                    if not data_dict.get('manufactured_date', ''):
                        data_dict['manufactured_date'] = datetime.datetime.now()
                    if not data_dict.get('expiry_date', ''):
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
            sku_master = SKUMaster.objects.get(id=inventory_data['sku_id'])
            pallet_number = inventory_data.get('pallet_number', '')
            if 'pallet_number' in inventory_data.keys():
                del inventory_data['pallet_number']
            batch_no = inventory_data.get('batch_no', '')
            if 'batch_no' in inventory_data.keys():
                del inventory_data['batch_no']
            weight = inventory_data.get('weight', '')
            if 'weight' in inventory_data.keys():
                del inventory_data['weight']
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
            unit_price = inventory_data.get('unit_price', 0)
            if unit_price:
                if user.userprofile.industry_type == 'FMCG':
                    stock_query_filter['batch_detail__buy_price'] = unit_price
                else:
                    stock_query_filter['unit_price'] = unit_price
            elif unit_price == '':
                unit_price = sku_master.cost_price
                inventory_data['unit_price'] = unit_price
                inventory_data['price_type'] = 'cost_price'
            if pallet_number:
                pallet_data = {'pallet_code': pallet_number, 'quantity': int(inventory_data['quantity']),
                               'user': user.id,
                               'status': 1, 'creation_date': str(datetime.datetime.now()),
                               'updation_date': str(datetime.datetime.now())}
                pallet_detail = PalletDetail(**pallet_data)
                pallet_detail.save()
                stock_query_filter['pallet_detail_id'] = pallet_detail.id
                inventory_data['pallet_detail_id'] = pallet_detail.id
            if mrp or batch_no or mfg_date or exp_date or weight or unit_price:
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
                if weight:
                    batch_dict['weight'] = weight
                if unit_price:
                    batch_dict["buy_price"] = float(unit_price)
                add_ean_weight_to_batch_detail(sku_master, batch_dict)
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
                if inventory_data.has_key('sku_code'):
                    del inventory_data['sku_code']
                if inventory_data.has_key('location'):
                    del inventory_data['location']
                if not sku_master.zone:
                    location_master = LocationMaster.objects.get(id=inventory_data['location_id'])
                    sku_master.zone_id = location_master.zone_id
                    sku_master.save()
                if 'batch_detail__buy_price' in inventory_data.keys():
                    del inventory_data['batch_detail__buy_price']
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
    user = User.objects.get(id = user_id)
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        mapping_dict['ep_supplier'] = 29
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

            if key == 'supplier_id':
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                if cell_data:
                    supplier_master = SupplierMaster.objects.filter(supplier_id=cell_data, user=user.id)
                    if supplier_master:
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
            elif key == 'secondary_email_id':
                cell_data = cell_data.split(',')
                for val in cell_data:
                    if val and validate_email(val):
                        index_status.setdefault(row_idx, set()).add('Enter Valid Secondary Email address')
            elif key == 'account_number':
                if not len(str(cell_data)) < 20:
                    index_status.setdefault(row_idx, set()).add('Account Number has limit of 19')
            elif key == 'currency_code':
                if cell_data and cell_data not in CURRENCY_CODES:
                    index_status.setdefault(row_idx, set()).add('Invalid Currency Code')
            elif key in number_str_fields:
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Invalid %s' % messages_dict[key])

    if not index_status:
        return 'Success'
    supplier_headers = copy.deepcopy(SUPPLIER_HEADERS)
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        supplier_headers.append('EP Supplier(yes/no)')
    f_name = '%s.supplier_form.xls' % user_id
    write_error_file(f_name, index_status, open_sheet, supplier_headers, 'Supplier')
    return f_name


def supplier_excel_upload(request, open_sheet, user, demo_data=False):
    mapping_dict = copy.deepcopy(SUPPLIER_EXCEL_FIELDS)
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        mapping_dict['ep_supplier'] = 30
    number_str_fields = ['pincode', 'phone_number', 'days_to_supply', 'fulfillment_amt', 'po_exp_duration',
                         'owner_number', 'spoc_number', 'lead_time', 'credit_period', 'account_number']
    rev_tax_types = dict(zip(TAX_TYPE_ATTRIBUTES.values(), TAX_TYPE_ATTRIBUTES.keys()))
    for row_idx in range(1, open_sheet.nrows):
        sku_code = ''
        wms_code = ''
        secondary_email_ids = []
        supplier_data = copy.deepcopy(SUPPLIER_DATA)
        supplier_master = None
        for key, value in mapping_dict.iteritems():
            cell_data = open_sheet.cell(row_idx, mapping_dict[key]).value
            if key == 'supplier_id':
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                supplier_data['supplier_id'] = cell_data
                supplier_obj = SupplierMaster.objects.filter(supplier_id=cell_data, user=user.id)
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
            elif key == "secondary_email_id":
                if cell_data:
                    secondary_email_ids = cell_data.split(',')
            elif key in number_str_fields:
                if cell_data:
                    cell_data = int(float(cell_data))
                    supplier_data[key] = cell_data
                    if supplier_master:
                        setattr(supplier_master, key, cell_data)
            elif key == 'ep_supplier':
                if cell_data.lower() =='yes':
                    supplier_data[key] = 1
                elif cell_data.lower() == 'no' :
                    supplier_data[key] = 0
                if supplier_master and cell_data.lower() in ['yes','no'] :
                    setattr(supplier_master, key, supplier_data[key])
            else:
                if key != "secondary_email_id":
                    supplier_data[key] = cell_data
                    if supplier_master and cell_data:
                        setattr(supplier_master, key, cell_data)
        if not supplier_master:
            supplier = SupplierMaster.objects.filter(supplier_id=supplier_data['supplier_id'], user=user.id)
            if not supplier:
                supplier_data['creation_date'] = datetime.datetime.now()
                #supplier_data['user'] = user.id
                supplier_id = supplier_data['supplier_id']
                del supplier_data['supplier_id']
                filter_dict = {'supplier_id': supplier_id}
                master_objs = sync_supplier_master(request, user, supplier_data, filter_dict,
                                                   secondary_email_id=secondary_email_ids)
                #supplier_master = create_new_supplier(user, supplier_id, supplier_data)
                # supplier = SupplierMaster(**supplier_data)
                # supplier.save()
        else:
            master_objs = sync_supplier_master(request, user, supplier_data, filter_dict,
                                               secondary_email_id=secondary_email_ids)
        # if secondary_email_ids:
        #     master_data_dict = {}
        #     master_data_dict['user_id'] = user.id
        #     master_data_dict['master_type'] = 'supplier'
        #     master_data_dict['master_id'] = supplier_master.id
        #     master_email_map = MasterEmailMapping.objects.filter(**master_data_dict)
        #     if master_email_map:
        #         master_email_map.delete()
        #     for mail in secondary_email_ids:
        #         master_data_dict = {}
        #         master_data_dict['user_id'] = user.id
        #         master_data_dict['email_id'] = mail
        #         master_data_dict['master_id'] = supplier_master.id
        #         master_data_dict['master_type'] = 'supplier'
        #         MasterEmailMapping.objects.create(**master_data_dict)
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
def validate_supplier_sku_form(open_sheet, user, headers, file_mapping):
    index_status = {}
    supplier_ids = []
    temp1 = ''
    supplier_list = SupplierMaster.objects.filter(user=user.id).values_list('supplier_id', flat=True)
    auto_po_switch = get_misc_value('auto_po_switch', user.id)
    if supplier_list:
        for i in supplier_list:
            supplier_ids.append(i)
    for row_idx in range(1, open_sheet.nrows):
        wms_code1 = ''
        preference1 = ''
        supplier_id = ''
        for key, col_idx in file_mapping.items():
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if key == 'warehouse':
                warehouse = cell_data
                if warehouse:
                    all_users = get_related_user_objs(user.id)
                    user_obj = all_users.filter(username=warehouse)
                    if not user_obj:
                        index_status.setdefault(index + 1, set()).add('Invalid Warehouse')
                    else:
                        user = user_obj[0]
                        supplier_list = SupplierMaster.objects.filter(user=user.id).values_list('supplier_id',
                                                                                                flat=True)
            elif key == 'supplier_id':
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                supplier_id = cell_data
                if cell_data and cell_data not in supplier_ids:
                    index_status.setdefault(row_idx, set()).add('Supplier ID Not Found')
                    for index, data in enumerate(supplier_ids):
                        if data == cell_data:
                            index_status.setdefault(index + 1, set()).add('Supplier ID Not Found')
                supplier_ids.append(cell_data)

            elif key == 'sku_code':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing SKU Code')
                else:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    wms_check = SKUMaster.objects.filter(user=user.id, sku_code=cell_data)
                    if not wms_check:
                        index_status.setdefault(row_idx, set()).add('Invalid SKU Code')
                    wms_code1 = cell_data
            elif key == 'preference':
                if auto_po_switch == 'true':
                    if not cell_data:
                        index_status.setdefault(row_idx, set()).add('Missing Preference')
                    else:
                        preference1 = int(cell_data)
            if key == 'costing_type':
                if cell_data :
                    if not cell_data in ['Price Based', 'Margin Based','Markup Based']:
                        index_status.setdefault(row_idx, set()).add('Costing Type should be "Price Based/Margin Based/Markup Based"')
                    if cell_data == 'Price Based' :
                        cell_data_price = open_sheet.cell(row_idx, 5).value
                        if not cell_data_price :
                            index_status.setdefault(row_idx, set()).add('Price is Mandatory For Price Based')
                        else:
                            if isinstance(cell_data_price, (int, float)) :
                                if cell_data_price > wms_check [0].mrp :
                                    index_status.setdefault(row_idx, set()).add('Price Should be Less than or Equal to MRP')
                            else:
                                index_status.setdefault(row_idx, set()).add('Price Should be Number')
                    elif cell_data == 'Margin Based' :
                        cell_data_margin = open_sheet.cell(row_idx, 7).value
                        if not cell_data_margin :
                            index_status.setdefault(row_idx, set()).add('MarkDown Percentage is Mandatory For Margin Based')
                        elif not isinstance(cell_data_margin, (int, float)):
                            index_status.setdefault(row_idx, set()).add('MarkDown % Should be in integer or float')
                        elif  float(cell_data_margin) < 0  or float(cell_data_margin) >  100:
                            index_status.setdefault(row_idx, set()).add('MarkDown % Should be in between 0 and 100')

                    elif cell_data == 'Markup Based' :
                        cell_data_markup = open_sheet.cell(row_idx, 8).value
                        if not cell_data_markup :
                            index_status.setdefault(row_idx, set()).add('Markup Percentage is Mandatory For Markup Based')
                        elif not isinstance(cell_data_markup, (int, float)):
                            index_status.setdefault(row_idx, set()).add('Markup % Should be in integer or float')
                        elif  float(cell_data_markup) < 0 or float(cell_data_markup) > 100:
                            index_status.setdefault(row_idx, set()).add('Markup % Should be in between 0 and 100')
            elif key == 'lead_time':
                if cell_data:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    else:
                        index_status.setdefault(row_idx, set()).add('Lead Time should be Number')


        if wms_code1 and preference1 and row_idx > 0 and  auto_po_switch == 'true':
            supp_val = SKUMaster.objects.filter(wms_code=wms_code1, user=user.id)
            if supp_val:
                temp1 = SKUSupplier.objects.filter(Q(sku_id=supp_val[0].id) & Q(preference=preference1),
                                                   sku__user=user.id)
                sku_supplier = SKUSupplier.objects.filter(sku_id=supp_val[0].id, supplier_id=supplier_id,
                                                          sku__user=user.id)
                if sku_supplier:
                    temp1 = []
            if temp1:
                index_status.setdefault(row_idx, set()).add('Preference matched with existing WMS Code')

    if not index_status:
        return 'Success'

    f_name = '%s.supplier_sku_form.xls' % user.username
    write_error_file(f_name, index_status, open_sheet, headers, 'Supplier')
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

        mapping = copy.deepcopy(SUPPLIER_SKU_HEADERS)
        if user.userprofile.warehouse_level != 0:
            del mapping['Warehouse']
        headers = mapping.keys()
        file_mapping = OrderedDict(zip(mapping.values(), range(0, len(mapping))))
        for col_idx in range(0, open_sheet.ncols):
            cell_data = open_sheet.cell(0, col_idx).value
            if headers[col_idx] != cell_data:
                return 'Invalid File'
        status = validate_supplier_sku_form(open_sheet, user, headers, file_mapping)
        if status != 'Success':
            return HttpResponse(status)
        supplier_sku_instance = None
        try:
            for row_idx in range(1, open_sheet.nrows):
                sku_code = ''
                wms_code = ''
                supplier_data = copy.deepcopy(SUPPLIER_SKU_DATA)
                for key, col_idx in file_mapping.items():
                    cell_data = open_sheet.cell(row_idx, col_idx).value
                    if key == 'warehouse':
                        warehouse = cell_data
                        if warehouse:
                            all_users = get_related_user_objs(user.id)
                            user_obj = all_users.filter(username=warehouse)
                            if not user_obj:
                                index_status.setdefault(index + 1, set()).add('Invalid Warehouse')
                            else:
                                user = user_obj[0]
                    elif key == 'supplier_id':
                        if isinstance(cell_data, (int, float)):
                            cell_data = str(int(cell_data))
                        supplier_data['supplier_id'] = SupplierMaster.objects.get(supplier_id=cell_data, user=user.id).id
                    elif key == 'sku_code':
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
                    elif key == 'supplier_code':
                        if isinstance(cell_data, (int, float)):
                            cell_data = str(int(cell_data))
                        supplier_data['supplier_code'] = cell_data
                        if cell_data and supplier_sku_instance:
                            supplier_sku_instance.supplier_code = cell_data
                    elif key == 'preference':
                        if not cell_data:
                            cell_data = 0
                        supplier_data['preference'] = str(int(cell_data))
                        if supplier_data['preference'] and supplier_sku_instance:
                            supplier_sku_instance.preference = supplier_data['preference']
                    elif key == 'moq':
                        if not cell_data:
                            cell_data = 0
                        cell_data = int(cell_data)
                        supplier_data['moq'] = cell_data
                        if cell_data and supplier_sku_instance:
                            supplier_sku_instance.moq = cell_data
                    elif key == 'price':
                        if not cell_data:
                            cell_data = 0
                        cell_data = float(cell_data)
                        supplier_data['price'] = cell_data
                        if cell_data and supplier_sku_instance:
                            supplier_sku_instance.price = cell_data
                    elif key == 'costing_type':
                        if not cell_data :
                            cell_data = 'Price Based'
                        supplier_data['costing_type'] = cell_data
                        if cell_data and supplier_sku_instance:
                            supplier_sku_instance.costing_type = cell_data
                    elif key == 'margin_percentage':
                        if not cell_data :
                            cell_data = 0
                        supplier_data['margin_percentage'] = cell_data
                        if cell_data and supplier_sku_instance:
                            supplier_sku_instance.margin_percentage = cell_data
                    elif key == 'markup_percentage':
                        if not cell_data :
                            cell_data = 0
                        supplier_data['markup_percentage'] = cell_data
                        if cell_data and supplier_sku_instance:
                            supplier_sku_instance.markup_percentage = cell_data
                    elif key == 'lead_time':
                        if not cell_data :
                            cell_data = 0
                        cell_data = int(cell_data)
                        supplier_data['lead_time'] = cell_data
                        if cell_data and supplier_sku_instance:
                            supplier_sku_instance.lead_time = cell_data
                supplier_sku = SupplierMaster.objects.filter(id=supplier_data['supplier_id'], user=user.id)
                if supplier_sku and not supplier_sku_obj:
                    supplier_sku = SKUSupplier(**supplier_data)
                    supplier_sku.save()
                elif supplier_sku_instance:
                    supplier_sku_instance.save()
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Supplier Sku Mapping Failed for  %s' % (
            str(user.username), str(request.POST.dict()), str(e)))
            return HttpResponse('Failed')
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
def validate_machine_form(open_sheet, user_id):
    index_status = {}
    machine_codes = []
    mapping_dict = copy.deepcopy(MACHINE_MASTER_EXCEL_FIELDS)
    user = User.objects.get(id=user_id)
    messages_dict = {'machine_code': 'Machine Code', 'machine_name': 'Machine Name',
                     'model_number': 'Model Number', 'serial_number': 'Serial Number',
                     'brand': 'Brand', 'status': 'Status'}
    number_str_fields = ['machine_code', 'machine_name', 'model_number', 'serial_number', 'brand']
    for row_idx in range(0, open_sheet.nrows):
        for key, value in mapping_dict.iteritems():
            cell_data = open_sheet.cell(row_idx, mapping_dict[key]).value
            if row_idx == 0:
                if open_sheet.cell(row_idx, 0).value != 'Machine Code':
                    return 'Invalid File'
                break
            if key == 'serial_number':
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                if cell_data:
                    machine_master = MachineMaster.objects.filter(serial_number=cell_data, user=user.id)
                    if machine_master:
                        index_status.setdefault(row_idx, set()).add('Serial Number Already exists')
                if cell_data and cell_data in machine_codes:
                    index_status.setdefault(row_idx, set()).add('Serial Number Already exists')
                    for index, data in enumerate(machine_codes):
                        if data == cell_data:
                            index_status.setdefault(index + 1, set()).add('Serial Number Already exists')
                machine_codes.append(cell_data)
            elif key == 'machine_code':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Machine Code is Missing')
                else:
                    machine_codes.append(cell_data)
            elif key == 'machine_name':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing Machine Name')
                else:
                    machine_codes.append(cell_data)
            elif key == 'brand':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing Brand')
                else:
                    machine_codes.append(cell_data)
            elif key == 'model_number':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing Model Number')
                else:
                    machine_codes.append(cell_data)

    if not index_status:
        return 'Success'
    machine_headers = copy.deepcopy(MACHINE_HEADERS)
    f_name = '%s.machine_form.xls' % user
    write_error_file(f_name, index_status, open_sheet, machine_headers, 'Machine')
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

def machine_excel_upload(request,open_sheet, user =''):
    import pandas as pd
    for row_idx in range(1, open_sheet.nrows):
        machine_data = copy.deepcopy(MACHINE_DATA)
        # for col_idx in range(0, len(MACHINE_MASTER_HEADERS)):

        index_dict = {0: 'machine_code', 1: 'machine_name', 2: 'model_number', 3: 'serial_number', 4: 'brand', 5:'status'}
        for col_idx in index_dict:
            cell_data = str(open_sheet.cell(row_idx, col_idx).value)
            if cell_data.endswith('.0'):
                cell_data = cell_data.replace('.0', '')
            if index_dict[col_idx] == 'serial_number':
                cell_data = pd.to_numeric(cell_data, errors="coerce")
                cell_data = cell_data.astype(int)
            machine_data[index_dict[col_idx]] = cell_data

        machine_dic = MachineMaster.objects.filter(machine_code = machine_data['machine_code'], user = user.id)
        if not machine_dic:
            if machine_data['status'] =='active' or 'Active':
                machine_data['status'] = 1
            else:
                machine_data['status'] = 0
            final_machine_dict = MachineMaster(user=user,**machine_data)
            final_machine_dict.save()
            status_msg = "Success"
        else:
            machine_dic[0].machine_code = machine_dic[0].machine_code = machine_data['machine_code']
            machine_dic[0].machine_name = machine_data['machine_name']
            machine_dic[0].brand = machine_data['brand']
            serial_check = MachineMaster.objects.filter(serial_number=machine_data['serial_number'])
            if not serial_check:
                machine_dic[0].serial_number = machine_data['serial_number']
            else:
                if machine_data['serial_number'] == machine_dic[0].serial_number:
                    machine_dic[0].serial_number = machine_data['serial_number']
                else:
                    status_msg = "Serial Number already exists"
                    break;
            if machine_data['status'] == 'Active' or "active" or 1:
                machine_dic[0].status = 1
            else:
                machine_dic[0].status = 0
            machine_dic[0].save()
            status_msg = "Success"
    return HttpResponse(status_msg)

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
    misc_detail = MiscDetail.objects.filter(user=user.id, misc_type='po_fields')
    fields = []
    margin_check = get_misc_value('enable_margin_price_check', user.id, number=False, boolean=True)
    if misc_detail.exists():
        fields = misc_detail[0].misc_value.lower().split(',')
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
    if user_profile.user_type == 'marketplace_user' :
        if 'seller_id' not in excel_mapping.keys() :
            return 'Invalid File seller id is Mandatory', []
    for row_idx in range(1, no_of_rows):
        data_dict = {}
        print excel_mapping
        for key, value in excel_mapping.iteritems():
            cell_data = get_cell_data(row_idx, value, reader, file_type)
            if key == 'supplier_id':
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                if demo_data:
                    cell_data = user_profile.prefix + '_' + cell_data
                ep_supplier = 0
                if cell_data:
                    supplier = SupplierMaster.objects.filter(user=user.id, supplier_id=cell_data.upper())
                    if not supplier:
                        index_status.setdefault(row_idx, set()).add("Supplier ID doesn't exist")
                    else:
                        data_dict['supplier_id'] = supplier[0].id
                        ep_supplier = int(supplier[0].ep_supplier)
                        data_dict['supplier_tax_type'] = supplier[0].tax_type
                else:
                    index_status.setdefault(row_idx, set()).add('Missing Supplier ID')
            elif key in ['po_date', 'po_delivery_date']:
                if cell_data:
                    try:
                        if isinstance(cell_data, float):
                            year, month, day, hour, minute, second = xldate_as_tuple(cell_data, 0)
                            data_dict[key] = str(datetime.datetime(year, month, day, hour, minute, second))
                        elif '-' in cell_data:
                            data_dict[key] = str(datetime.datetime.strptime(cell_data, "%m-%d-%Y"))
                        else:
                            index_status.setdefault(row_idx, set()).add('Check the date format for %s' %
                                                                        mapping_fields[key])
                    except:
                        index_status.setdefault(row_idx, set()).add('Check the date format for %s' %
                                                                    mapping_fields[key])
                elif key == 'po_date':
                    index_status.setdefault(row_idx, set()).add('%s is Mandatory' %
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
                        if not ep_supplier:
                            if sku_master[0].block_options == 'PO':
                                index_status.setdefault(row_idx, set()).add("WMS Code is blocked for PO")
                        if  margin_check and sku_master and supplier :
                            status = check_margin_percentage(sku_master[0].id, supplier[0].id, user)
                            if status:
                                index_status.setdefault(row_idx, set()).add(status)
                        data_dict['sku_id'] = sku_master[0].id
                        data_dict['wms_code'] = sku_master[0].wms_code
                        data_dict['sku_product_type'] = sku_master[0].product_type
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
                            data_dict['seller_id'] = seller_master[0].id
            elif key == 'quantity':
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Quantity should be integer')
                    elif isinstance(cell_data, float):
                        get_decimal_data(cell_data, index_status, row_idx, user)
                        data_dict[key] = float(cell_data)
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
                    data_dict[key] = ''
                    if data_dict.get('sku', '') and data_dict.get('supplier', ''):
                        sku_supplier = SKUSupplier.objects.filter(sku_id=data_dict['sku_id'], supplier_id=data_dict['supplier_id'], sku__user=user.id)
                        if not sku_supplier.exists() :
                            mandate_supplier = get_misc_value('mandate_sku_supplier', user.id)
                            if mandate_supplier == 'true' and not ep_supplier:
                                index_status.setdefault(row_idx, set()).add('Please Create Sku Supplier Mapping')

            elif key in ['po_name', 'ship_to']:
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                data_dict[key] = cell_data

            # elif key == 'mrp' and user.username in MILKBASKET_USERS :
            #     if not cell_data :
            #         index_status.setdefault(row_idx, set()).add('MRP is mandatory')
            #     data_dict[key] = cell_data
            elif key in fields:
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
            elif cell_data == '':
                if key in number_fields:
                    data_dict[key] = cell_data
        if not index_status:
            for data in data_list:
                if data['sku_id']== data_dict['sku_id'] and data['supplier_id'] == data_dict['supplier_id'] and \
                    data.get('po_name', '') == data_dict.get('po_name', ''):
                    index_status.setdefault(row_idx, set()).add('SKU added in multiple rows for same supplier')

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
    wms_codes_list = list(set(map(lambda d: d['wms_code'], data_list)))
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
                         'SGST (%)', 'CGST (%)', 'IGST (%)', 'UTGST (%)', 'Total(with tax)']
        if user.username in MILKBASKET_USERS:
            table_headers.insert(4, 'Weight')
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
    ids_dict = {}
    send_mail_data = OrderedDict()
    check_prefix = ''
    for final_dict in data_list:
        final_dict['sku'] = SKUMaster.objects.get(id=final_dict['sku_id'], user=user.id)
        final_dict['supplier'] = SupplierMaster.objects.get(id=final_dict['supplier_id'], user=user.id)
        if final_dict.get('seller_id', ''):
            final_dict['seller'] = SellerMaster.objects.get(id=final_dict['seller_id'], user=user.id)
        final_dict['po_date'] = datetime.datetime.strptime(final_dict.get('po_date', ''), '%Y-%m-%d %H:%M:%S')
        if final_dict.get('po_delivery_date', '') != '':
            final_dict['po_delivery_date'] = datetime.datetime.strptime(final_dict.get('po_delivery_date', ''), '%Y-%m-%d %H:%M:%S')
        total_qty = 0
        total = 0
        order_data = copy.deepcopy(PO_SUGGESTIONS_DATA)
        data = copy.deepcopy(PO_DATA)
        order_data['supplier_id'] = final_dict['supplier'].id
        order_data['sku_id'] = final_dict['sku'].id
        order_data['order_quantity'] = final_dict['quantity']
        order_data['price'] = final_dict.get('price', 0)
        if order_data['price'] == '':
            mapping_data = get_mapping_values_po(final_dict['sku'].wms_code ,final_dict['supplier'].id ,user)
            order_data['price'] = mapping_data.get('price',0)
        order_data['po_name'] = final_dict['po_name']
        order_data['mrp'] = final_dict.get('mrp', 0)
        order_data['cgst_tax'] = final_dict.get('cgst_tax', 0)
        order_data['sgst_tax'] = final_dict.get('sgst_tax', 0)
        order_data['igst_tax'] = final_dict.get('igst_tax', 0)
        order_data['utgst_tax'] = final_dict.get('utgst_tax', 0)
        order_data['cess_tax'] = final_dict.get('cess_tax', 0)
        order_data['apmc_tax'] = final_dict.get('apmc_tax', 0)
        if order_data['mrp'] == '':
            order_data['mrp'] = final_dict['sku'].mrp
        taxes = {'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0, 'utgst_tax': 0 ,'cess_tax':0,'apmc_tax':0}
        if order_data['cgst_tax'] == '' and order_data['sgst_tax'] == '' and order_data['igst_tax'] == '' :
            price = order_data['price']
            inter_state_dict = dict(zip(SUMMARY_INTER_STATE_STATUS.values(), SUMMARY_INTER_STATE_STATUS.keys()))
            inter_state = inter_state_dict.get(final_dict['supplier'].tax_type, 2)
            tax_master = TaxMaster.objects.filter(user_id=user, inter_state=inter_state,
                                                  product_type=final_dict['sku'].product_type,
                                                  min_amt__lte=price, max_amt__gte=price).\
                values('cgst_tax', 'sgst_tax', 'igst_tax', 'utgst_tax','cess_tax','apmc_tax')
            if tax_master.exists():
                taxes = copy.deepcopy(tax_master[0])
            order_data['cgst_tax'] = taxes.get('cgst_tax',0)
            order_data['sgst_tax'] = taxes.get('sgst_tax' ,0)
            order_data['igst_tax'] = taxes.get('igst_tax',0)
            if not order_data['utgst_tax'] :
                order_data['utgst_tax'] = taxes.get('utgst_tax',0)
            if not order_data['cess_tax'] :
                order_data['cess_tax'] = taxes.get('cess_tax',0)
            if not order_data['apmc_tax'] :
                order_data['apmc_tax'] = taxes.get('apmc_tax',0)
        else:
            for key,value in taxes.iteritems():
                if not order_data[key] :
                    order_data[key] = value
        order_data['measurement_unit'] = final_dict['sku'].measurement_type
        order_data['creation_date'] = creation_date
        if final_dict.get('po_delivery_date', ''):
            order_data['delivery_date'] = final_dict['po_delivery_date']
        data['po_date'] = final_dict['po_date']
        data['ship_to'] = final_dict['ship_to']
        order_data['ship_to'] = final_dict['ship_to']
        data['creation_date'] = creation_date
        seller_id = ''
        excel_seller_id = ''
        if final_dict.get('seller', ''):
            seller_id = final_dict['seller'].id
            excel_seller_id = final_dict['seller'].seller_id
        group_key = (order_data['po_name'], order_data['supplier_id'], data['po_date'], seller_id)
        if group_key not in order_ids.keys():
            # po_id = get_purchase_order_id(user)+1
            # if po_sub_user_prefix == 'true':
            #     po_id = update_po_order_prefix(request.user, po_id)
            sku_code = final_dict['sku'].sku_code
            po_id, prefix, po_number, check_prefix, inc_status = get_user_prefix_incremental(user, 'po_prefix', sku_code)
            if inc_status:
                return HttpResponse("Prefix not defined")
            order_ids[group_key] = {'po_id': po_id, 'prefix': prefix, 'po_number': po_number}
        else:
            po_id = order_ids[group_key]['po_id']
            prefix = order_ids[group_key]['prefix']
            po_number = order_ids[group_key]['po_number']
        order_data['status'] = 0
        data1 = OpenPO(**order_data)
        data1.save()
        misc_detail = MiscDetail.objects.filter(user=user.id, misc_type='po_fields')
        seller_receipt_id = 0
        if misc_detail:
            fields = misc_detail[0].misc_value.lower().split(',')
            if set(final_dict.keys()).issuperset(fields):
                for field in fields:
                    value = final_dict[field]
                    Pofields.objects.create(user= user.id,po_number = po_id,receipt_no= seller_receipt_id,name=field,value=value,field_type='po_field')
        if seller_id:
            SellerPO.objects.create(seller_id=seller_id, open_po_id=data1.id,
                                    seller_quantity=order_data['order_quantity'], unit_price=order_data['price'],
                                    creation_date=creation_date)
        purchase_order = OpenPO.objects.get(id=data1.id, sku__user=user.id)
        sup_id = purchase_order.id
        supplier = purchase_order.supplier_id
        if supplier not in ids_dict:
            ids_dict[supplier] = po_id
        data['open_po_id'] = sup_id
        data['order_id'] = po_id
        data['prefix'] = prefix
        data['po_number'] = po_number
        order = PurchaseOrder(**data)
        order.save()
        order.po_date = data['po_date']
        order.save()
        amount = data1.order_quantity * data1.price
        total_qty += data1.order_quantity
        total_tax_amt = (data1.utgst_tax + data1.sgst_tax + data1.cgst_tax + data1.igst_tax + data1.cess_tax + data1.apmc_tax + data1.utgst_tax) * (
                                    amount / 100)
        total_sku_amt = total_tax_amt + amount
        total += total_sku_amt
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
            if user.username in MILKBASKET_USERS:
                weight_obj = data1.sku.skuattributes_set.filter(attribute_name='weight'). \
                    only('attribute_value')
                weight = ''
                if weight_obj.exists():
                    weight = weight_obj[0].attribute_value
                po_temp_data.insert(4, weight)
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
            ean_number = ''
            eans = get_sku_ean_list(data1.sku, order_by_val='desc')
            if eans:
                ean_number = eans[0]
            po_temp_data.insert(1, ean_number)
        if show_cess_tax:
            po_temp_data.insert(table_headers.index('CESS (%)'), data1.cess_tax)
        if show_apmc_tax:
            po_temp_data.insert(table_headers.index('APMC (%)'), data1.apmc_tax)
        po_data.append(po_temp_data)
        send_mail_data.setdefault(str(order.order_id), {'purchase_order': order, 'po_data': [],
                                  'data1': data1, 'total_qty': 0, 'total': 0,'seller_id':excel_seller_id})
        send_mail_data[str(order.order_id)]['po_data'].append(po_temp_data)
        send_mail_data[str(order.order_id)]['total_qty'] += total_qty
        send_mail_data[str(order.order_id)]['total'] += total

        #mail_result_data = purchase_order_dict(data1, data_req, purchase_order, user, order)
    excel_headers = ['Seller ID' , 'PO Reference' , 'PO Date', 'Supplier ID']+table_headers
    for key, send_mail_dat in send_mail_data.iteritems():
        try:
            purchase_order = send_mail_dat['data1']
            po_data = send_mail_dat['po_data']
            total_qty = send_mail_dat['total_qty']
            total = send_mail_dat['total']
            address = purchase_order.supplier.address
            address = '\n'.join(address.split(','))
            if purchase_order.ship_to:
                ship_to_address = purchase_order.ship_to
                if user.userprofile.wh_address:
                    company_address = user.userprofile.wh_address
                    if user.username in MILKBASKET_USERS:
                        if user.userprofile.user.email:
                            company_address = "%s, Email:%s" % (company_address, user.userprofile.user.email)
                        if user.userprofile.phone_number:
                            company_address = "%s, Phone:%s" % (company_address, user.userprofile.phone_number)
                        if user.userprofile.gst_number:
                            company_address = "%s, GSTINo:%s" % (company_address, user.userprofile.gst_number)
                else:
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
            supplier = purchase_order.supplier_id
            order_id = po_id
            supplier_email = purchase_order.supplier.email_id
            secondary_supplier_email = list(MasterEmailMapping.objects.filter(master_id=supplier, user=user.id, master_type='supplier').values_list('email_id',flat=True).distinct())
            supplier_email_id =[]
            supplier_email_id.insert(0,supplier_email)
            supplier_email_id.extend(secondary_supplier_email)
            phone_no = purchase_order.supplier.phone_number
            gstin_no = purchase_order.supplier.tin_number
            po_exp_duration = purchase_order.supplier.po_exp_duration
            order_date = get_local_date(request.user, order.creation_date)
            if po_exp_duration:
                expiry_date = order.creation_date + datetime.timedelta(days=po_exp_duration)
            else:
                expiry_date = ''
            po_reference = order.po_number
            report_file_names = []
            if user.username in MILKBASKET_USERS:
                wb, ws, path, file_name = get_excel_variables(po_reference+' '+'Purchase Order Form', 'purchase_order_sheet', excel_headers)

                excel_common_list = [send_mail_dat['seller_id'], purchase_order.po_name,
                                     purchase_order.creation_date.strftime("%d-%m-%Y"), purchase_order.supplier_id]
                for i in range(len(po_data)):
                    row_count=i+1
                    column_count=0
                    excel_data = excel_common_list+po_data[i]
                    for value in excel_data:
                        ws, column_count = write_excel_col(ws, row_count, column_count, value, bold=False)
                wb.save(path)
                report_file_names.append({'name': file_name, 'path': path})
            profile = UserProfile.objects.get(user=user.id)
            company_name = profile.company.company_name
            title = 'Purchase Order'
            receipt_type = request.GET.get('receipt_type', '')
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
                data_dict_po = {'contact_no': profile.wh_phone_number, 'contact_email': user.email,
                                'gst_no': profile.gst_number, 'supplier_name':purchase_order.supplier.name,
                                'billing_address': profile.address, 'shipping_address': ship_to_address,
                                'table_headers': table_headers}
                if get_misc_value('allow_secondary_emails', user.id) == 'true':
                    write_and_mail_pdf(po_reference, rendered, request, user, supplier_email_id, phone_no, po_data,
                                       str(order_date).split(' ')[0], ean_flag=ean_flag, data_dict_po=data_dict_po,
                                       full_order_date=str(order_date) ,mail_attachments=report_file_names)
                elif get_misc_value('raise_po', user.id) == 'true':
                    write_and_mail_pdf(po_reference, rendered, request, user, supplier_email, phone_no, po_data,
                                       str(order_date).split(' ')[0], ean_flag=ean_flag,
                                       data_dict_po=data_dict_po, full_order_date=str(order_date), mail_attachments=report_file_names)
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Purchase Order send mail failed for %s and params are %s and error statement is %s' % (
            str(user.username), str(request.POST.dict()), str(e)))
    for key, value in order_ids.iteritems():
        if value.get('po_id'):
            check_purchase_order_created(user, value['po_id'], check_prefix)
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
                           'company_name': profile.company.company_name, 'location': profile.location,
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
@reversion.create_revision(atomic=False, using='reversion')
def purchase_order_upload(request, user=''):
    reversion.set_user(request.user)
    reversion.set_comment("upload_po")
    purchase_order_view = get_misc_value('purchase_order_preview', user.id)
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
    if purchase_order_view == 'true':
        content = purchase_order_preview_generation(request, user, data_list)
        return HttpResponse(json.dumps(content))
    else:
        purchase_order_excel_upload(request, user, data_list)
    return HttpResponse('Success')

@login_required
@get_admin_user
@csrf_exempt
@reversion.create_revision(atomic=False, using='reversion')
def purchase_order_upload_preview(request, user=''):
    reversion.set_user(request.user)
    reversion.set_comment("upload_po")
    data_list = json.loads(request.POST.get('data_list', ''))
    purchase_order_excel_upload(request, user, data_list)
    return HttpResponse('Success')

def purchase_order_preview_generation(request, user, data_list):
    profile = UserProfile.objects.get(user_id=user.id)
    if profile.industry_type == 'FMCG':
        table_headers = ['WMS Code', 'Supplier Code', 'Desc', 'Qty', 'Unit Price', 'MRP', 'Amt',
                                                  'SGST (%)', 'CGST (%)', 'IGST (%)', 'UTGST (%)', 'CESS (%)', 'APMC (%)', 'Total']
    else:
        table_headers = ['WMS Code', 'Supplier Code', 'Desc', 'Qty', 'Unit Price', 'MRP', 'Amt',
                             'SGST (%)', 'CGST (%)', 'IGST (%)', 'UTGST (%)', 'Total']
    if user.username in MILKBASKET_USERS:
        table_headers.insert(4, 'Weight')
    data_preview, templete_data = {}, {}
    supplier_list = [data['supplier_id'] for data in data_list]
    unique_sippliers = list(set(supplier_list))
    data_dict = []
    for sup_id in unique_sippliers:
        po_data, total_amt, total_qty =[], 0, 0
        for data in data_list:
            if sup_id == data['supplier_id']:
                sku = SKUMaster.objects.get(id=data['sku_id'], user=user.id)
                supplier = SupplierMaster.objects.get(id=data['supplier_id'], user=user.id)
                if data['price'] == '':
                    mapping_data = get_mapping_values_po(data['wms_code'], data['supplier_id'] ,user)
                    data['price'] = mapping_data.get('price',0)
                unit_price = data['price']
                taxes = {'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0, 'utgst_tax': 0 ,'cess_tax':0,'apmc_tax':0}
                if data.get('cgst_tax', 0) == data.get('sgst_tax', 0) == data.get('igst_tax', 0) == data.get('utgst_tax', 0) =='':
                    inter_state_dict = dict(zip(SUMMARY_INTER_STATE_STATUS.values(), SUMMARY_INTER_STATE_STATUS.keys()))
                    inter_state = inter_state_dict.get(data['supplier_tax_type'], 2)
                    tax_master = TaxMaster.objects.filter(user_id=user, inter_state=inter_state,product_type=data['sku_product_type'],
                                                            min_amt__lte=unit_price, max_amt__gte=unit_price).\
                                                            values('cgst_tax', 'sgst_tax', 'igst_tax', 'utgst_tax','cess_tax','apmc_tax')
                    if tax_master.exists():
                        taxes = copy.deepcopy(tax_master[0])
                else:
                    for tax_name in taxes.keys():
                        try:
                            taxes[tax_name] = float(data.get(tax_name, 0))
                        except:
                            taxes[tax_name] = 0
                if data.get('cess_tax', 0) != '':
                    taxes['cess_tax'] = data.get('cess_tax', 0)
                if data.get('apmc_tax', 0) != '':
                    taxes['apmc_tax'] = data.get('apmc_tax', 0)
                total, amount, company_address, ship_to_address = tax_calculation_master(data, user, profile, taxes)
                total_amt += total
                total_qty += data['quantity']
                if data['mrp'] == '':
                    data['mrp'] = sku.mrp
                if profile.industry_type == 'FMCG':
                    po_temp_data = [sku.sku_code, data['supplier_id'], sku.sku_desc, data['quantity'], data['price'],
                                data['mrp'], amount, taxes['sgst_tax'], taxes['cgst_tax'], taxes['igst_tax'],
                                taxes['utgst_tax'], taxes['cess_tax'], taxes['apmc_tax'], total
                               ]
                else:
                    po_temp_data = [sku.sku_code, data['supplier_id'], sku.sku_desc, data['quantity'], data['price'],
                                 data['mrp'], amount, taxes['sgst_tax'], taxes['cgst_tax'], taxes['igst_tax'],
                                 taxes['utgst_tax'], total
                                ]
                if user.username in MILKBASKET_USERS:
                    weight = get_sku_weight(sku)
                    po_temp_data.insert(4, weight)
                po_data.append(po_temp_data)
        data_dict.append({'table_headers': table_headers,
                        'data':po_data,
                        'address': supplier.address,
                        'order_id': '',
                        'telephone': supplier.phone_number,
                        'ship_to_address': ship_to_address,
                        'name': supplier.name,
                        'order_date': get_local_date(request.user, datetime.datetime.now()),
                        'total': round(total_amt),
                        'po_reference': '',
                        'user_name': '',
                        'total_amt_in_words': number_in_words(round(total_amt)) + ' ONLY',
                        'total_qty': total_qty,
                        'location': '',
                        'w_address': ship_to_address,
                        'vendor_name': '',
                        'vendor_address': '',
                        'vendor_telephone': '',
                        'receipt_type': '',
                        'title': '',
                        'gstin_no': supplier.tin_number,
                        'industry_type': '',
                        'expiry_date': '',
                        'wh_telephone': user.userprofile.wh_phone_number,
                        'wh_gstin': profile.gst_number,
                        'wh_pan': profile.pan_number,
                        'terms_condition': '',
                        'supplier_pan':supplier.pan_number,
                        'company_name': profile.company.company_name,
                        'company_address': company_address
                    })
    templete_data['data'] = data_dict
    t = loader.get_template('templates/toggle/upload_po_preview.html')
    data = t.render(templete_data)
    data_preview['data_preview'] = data
    data_preview['data_list'] = data_list
    return data_preview

@csrf_exempt
def tax_calculation_master(data, user, profile, taxes):
    total, amount, company_address = 0, 0, ''
    unit_price = data.get('price', 0)
    quantity = data.get('quantity', 0)
    tax = sum(taxes.values())
    amount = unit_price * quantity
    total += amount + ((amount / 100) * float(tax))
    if user.userprofile.wh_address:
        company_address = user.userprofile.wh_address
        if user.username in MILKBASKET_USERS:
            if user.userprofile.user.email:
                company_address = ("%s, Email:%s") % (company_address, user.userprofile.user.email)
            if user.userprofile.phone_number:
                company_address = ("%s, Phone:%s") % (company_address, user.userprofile.phone_number)
            if user.userprofile.gst_number:
                company_address = ("%s, GSTINo:%s") % (company_address, user.userprofile.gst_number)
    else:
        company_address = user.userprofile.address
    if profile.wh_address:
        address = profile.wh_address
    else:
        address = profile.address
    if not (address and company_address):
        company_address, address = '', ''
    if profile.user.email:
        address = ("%s, Email:%s") % (address, profile.user.email)
    return total, amount, company_address, address

@csrf_exempt
def validate_move_inventory_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type):
    mapping_dict = {}
    index_status = {}
    location = {}
    data_list = []
    dest_location = None
    try:
        inv_mapping = get_move_inventory_excel_upload_headers(user)
        unique_mrp = get_misc_value('unique_mrp_putaway', user.id)
        inv_res = dict(zip(inv_mapping.values(), inv_mapping.keys()))
        excel_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                     inv_mapping)
        excel_check_list = ['wms_code', 'source', 'destination', 'quantity','price']
        if user.userprofile.user_type == 'marketplace_user':
            excel_check_list.append('seller_id')
        if user.userprofile.industry_type == 'FMCG':
            excel_check_list.append('mrp')
            excel_check_list.append('weight')
        if not set(excel_check_list).issubset(excel_mapping.keys()):
            return 'Invalid File', None
        fields_mapping = {'quantity': 'Quantity', 'mrp': 'MRP'}
        number_fields = ['quantity']
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
                elif key == 'weight':
                    if isinstance(cell_data, float):
                        cell_data = str(int(cell_data))

                    if user.username in MILKBASKET_USERS :
                        if not cell_data:
                            index_status.setdefault(row_idx, set()).add('Weight is Mandatory')
                        cell_data = mb_weight_correction(cell_data)
                    data_dict[key] = cell_data

                elif key == 'mrp':
                    if not isinstance(cell_data, (int, float)):
                       index_status.setdefault(row_idx, set()).add('Invalid Entry for MRP Value')
                    else:
                        data_dict[key] = cell_data
                    if user.username in MILKBASKET_USERS and not cell_data:
                        index_status.setdefault(row_idx, set()).add('MRP is Mandatory')
                elif key == 'price':
                    if isinstance(cell_data, float):
                        cell_data = float(cell_data)
                    data_dict[key] = cell_data
                elif key == 'reason':
                    move_inventory_reasons = get_misc_value('move_inventory_reasons', user.id)
                    if move_inventory_reasons != 'false':
                        move_inventory_reasons = move_inventory_reasons.split(',')
                    else:
                        move_inventory_reasons = []
                    move_inventory_reasons = [str(x).lower() for x in move_inventory_reasons]
                    if len(move_inventory_reasons) > 0 and str(cell_data).lower() not in map(str.lower,
                                                                                             move_inventory_reasons):
                        index_status.setdefault(row_idx, set()).add('Enter only Configured Move Inventory Reasons')
                    else:
                        data_dict[key] = cell_data
                elif key in number_fields:
                    if isinstance(cell_data, float):
                        get_decimal_data(cell_data, index_status, row_idx, user)
                    if cell_data and (not isinstance(cell_data, (int, float)) or int(cell_data) < 0):
                        index_status.setdefault(row_idx, set()).add('Invalid %s' % fields_mapping[key])
                    else:
                        data_dict[key] = cell_data
            if data_dict.has_key('weight') and data_dict.has_key('mrp'):
                if user.username in MILKBASKET_USERS and unique_mrp == 'true' and data_dict.has_key('wms_code') and dest_location:
                    data_dict['sku_code'] = data_dict['wms_code']
                    data_dict['location'] = dest_location[0].location
                    status = validate_mrp_weight(data_dict,user)
                    if status:
                        index_status.setdefault(row_idx, set()).add(status)

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
                if data_dict.get('weight', ''):
                    weight = data_dict['weight']
                    stock_dict["batch_detail__weight"] = weight
                    reserved_dict["stock__batch_detail__weight"] = weight
                    raw_reserved_dict["stock__batch_detail__weight"] = weight
                if data_dict.get('seller_master_id', ''):
                    stock_dict['sellerstock__seller_id'] = data_dict['seller_master_id']
                    stock_dict['sellerstock__quantity__gt'] = 0
                    reserved_dict["stock__sellerstock__seller_id"] = data_dict['seller_master_id']
                    raw_reserved_dict["stock__sellerstock__seller_id"] = data_dict['seller_master_id']
                if data_dict.get('price','') != '':
                    price = float(data_dict['price'])
                    if user.userprofile.industry_type == 'FMCG':
                        stock_dict['batch_detail__buy_price'] = price
                        reserved_dict["stock__batch_detail__buy_price"] = price
                        raw_reserved_dict['stock__batch_detail__buy_price'] = price
                    else:
                        stock_dict['unit_price'] = price
                        reserved_dict["stock__unit_price"] = price
                        raw_reserved_dict['stock__unit_price'] = price

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
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('validation of move inventory failed for %s and params are %s and error statement is %s' % (
            str(user.username), str(request.POST.dict()), str(e)))


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def move_inventory_upload(request, user=''):
    reversion.set_user(request.user)
    reversion.set_comment("upload_move_inv")
    fname = request.FILES['files']
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
    except:
        return HttpResponse('Invalid File')
    try:
        status, data_list = validate_move_inventory_form(request, reader, user, no_of_rows,
                                                         no_of_cols, fname, file_type)
        if status != 'Success':
            return HttpResponse(status)
        # cycle_count = CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
        # if not cycle_count:
        #     cycle_id = 1
        # else:
        #     cycle_id = cycle_count[0].cycle + 1
        mod_locations = []
        seller_receipt_dict = {}
        sku_codes = []
        receipt_number = get_stock_receipt_number(user)
        count=0
        for data_dict in data_list:
            extra_dict = OrderedDict()
            wms_code = data_dict['wms_code']
            sku_codes.append(wms_code)
            source_loc = data_dict['source']
            dest_loc = data_dict['destination']
            quantity = data_dict['quantity']
            reason = data_dict.get('reason', '')
            seller_id = ''
            if data_dict.get('seller_id', ''):
                extra_dict['seller_id'] = data_dict['seller_id']
                seller_id = data_dict['seller_id']
            if data_dict.get('batch_no', ''):
                extra_dict['batch_no'] = data_dict['batch_no']
            if data_dict.get('mrp', ''):
                extra_dict['mrp'] = data_dict['mrp']
            if data_dict.get('weight', ''):
                extra_dict['weight'] = data_dict['weight']
            if data_dict.get('price', ''):
                extra_dict['price'] = data_dict['price']
            if user.userprofile.user_type == 'marketplace_user':
                if str(seller_id) in seller_receipt_dict.keys():
                    receipt_number = seller_receipt_dict[str(seller_id)]
                else:
                    receipt_number = get_stock_receipt_number(user)
                    seller_receipt_dict[str(seller_id)] = receipt_number
            extra_dict['receipt_type'] = 'move-inventory'
            extra_dict['receipt_number'] = receipt_number
            extra_dict['reason'] = reason
            response=move_stock_location(wms_code, source_loc, dest_loc, quantity, user, **extra_dict)
            if response == 'Added Successfully':
                count+=1
            mod_locations.append(source_loc)
            mod_locations.append(dest_loc)
        update_filled_capacity(list(set(mod_locations)), user.id)
        if user.username in MILKBASKET_USERS: check_and_update_marketplace_stock(sku_codes, user)
        return HttpResponse('Successfully moved {} items'.format(count))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('move inventory failed for %s  and error statement is %s' % (
            str(user.username), str(e)))
        return HttpResponse('Failed to Upload')



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
                sku_code = SKUMaster.objects.filter(sku_code=product_sku, user=user.id)
                if not sku_code:
                    index_status.setdefault(row_idx, set()).add('Invalid SKU Code %s' % product_sku)
            if key == 'material_sku':
                material_sku = open_sheet.cell(row_idx, bom_excel[key]).value
                if isinstance(material_sku, (int, float)):
                    material_sku = int(material_sku)
                sku_code = SKUMaster.objects.filter(sku_code=material_sku, user=user.id)
                if not sku_code:
                    index_status.setdefault(row_idx, set()).add('Invalid SKU Code %s' % material_sku)
            elif key == 'material_quantity':
                cell_data = open_sheet.cell(row_idx, bom_excel[key]).value
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Quantity Should be in integer or float')
                        # else:
                        #    index_status.setdefault(row_idx, set()).add('Quantity Should not be empty')
                    if isinstance(cell_data, float):
                        get_decimal_data(cell_data, index_status, row_idx, user)
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

    f_name = '%s.bom_form.xls' % user.id
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
    status = validate_bom_form(open_sheet, user, bom_excel)

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
                if isinstance(cell_data, float):
                    get_decimal_data(cell_data, index_status, row_idx, user)
            else:
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(cell_data)
                sku_master = MarketplaceMapping.objects.filter(marketplace_code=cell_data, sku__user=user.id)
                if not sku_master:
                    sku_master = SKUMaster.objects.filter(sku_code=cell_data, user=user.id)
                if not sku_master:
                    if col_idx == 0:
                        message = 'Invalid SKU Code'
                    else:
                        message = 'Invalid Combo SKU'
                    index_status.setdefault(row_idx, set()).add(message)

    if not index_status:
        return 'Success'

    f_name = '%s.combo_sku_form.xls' % user.id
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

    status = validate_combo_sku_form(open_sheet, user)
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
    location_master = None
    sku_master = None
    unique_mrp = get_misc_value('unique_mrp_putaway', user.id)
    inv_mapping = get_inventory_adjustment_excel_upload_headers(user)
    excel_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 inv_mapping)
    excel_check_list = ['wms_code', 'location', 'quantity', 'reason', 'unit_price']
    if user.userprofile.user_type == 'marketplace_user':
        excel_check_list.append('seller_id')
    if user.userprofile.industry_type == 'FMCG':
        excel_check_list.append('mrp')
        excel_check_list.append('weight')
    if not set(excel_check_list).issubset(excel_mapping.keys()):
        return 'Invalid File', None
    for row_idx in range(1, no_of_rows):
        print row_idx
        data_dict = {}
        for key, value in excel_mapping.iteritems():
            cell_data = get_cell_data(row_idx, value, reader, file_type)
            if key == 'wms_code':
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(xcode(cell_data))
                sku_master = SKUMaster.objects.filter(user=user.id, sku_code=cell_data)
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
                    if isinstance(cell_data, float):
                        get_decimal_data(cell_data, index_status, row_idx, user)
                    data_dict['quantity'] = float(cell_data)
                    if data_dict['quantity'] < 0:
                        index_status.setdefault(row_idx, set()).add('Invalid Quantity')
                except:
                    index_status.setdefault(row_idx, set()).add('Invalid Quantity')
            elif key == 'mrp':
                if user.username in MILKBASKET_USERS and not cell_data:
                    index_status.setdefault(row_idx, set()).add('MRP is Mandatory')
                if cell_data:
                    try:
                        data_dict['mrp'] = float(cell_data)
                        if data_dict['mrp'] < 0:
                            index_status.setdefault(row_idx, set()).add('Invalid MRP')
                    except:
                        index_status.setdefault(row_idx, set()).add('Invalid MRP')
            elif key == 'weight' :
                if user.username in MILKBASKET_USERS:
                    if isinstance(cell_data, (float)):
                        cell_data = str(int(cell_data))
                    cell_data = mb_weight_correction(cell_data)
                data_dict[key] = cell_data

                #    index_status.setdefault(row_idx, set()).add('Weight is Mandatory')
            elif key == 'unit_price':
                try:
                    data_dict[key] = float(cell_data)
                except:
                    data_dict[key] = ''
            else:
                #if isinstance(cell_data, (int, float)):
                #    data_dict[key] = cell_data
                data_dict[key] = cell_data
        if data_dict.has_key('weight') and data_dict.has_key('mrp'):
            if user.username in MILKBASKET_USERS and unique_mrp == 'true' and sku_master and location_master:
                data_dict['sku_code'] = sku_master[0].sku_code
                data_dict['location'] = location_master[0].location
                status = validate_mrp_weight(data_dict,user)
                if status:
                    index_status.setdefault(row_idx, set()).add(status)
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
@reversion.create_revision(atomic=False, using='reversion')
def inventory_adjust_upload(request, user=''):
    reversion.set_user(request.user)
    reversion.set_comment("upload_inv_adj")
    count = 0
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
    cycle_count = CycleCount.objects.filter(sku__user=user.id).only('cycle').aggregate(Max('cycle'))['cycle__max']
    #CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
    if not cycle_count:
        cycle_id = 1
    else:
        cycle_id = cycle_count + 1

    receipt_number = get_stock_receipt_number(user)
    seller_receipt_dict = {}
    stock_stats_objs = []
    for final_dict in data_list:
        # location_data = ''
        wms_code = final_dict['sku_master'].wms_code
        sku_codes.append(wms_code)
        loc = final_dict['location_master'].location
        quantity = final_dict['quantity']
        reason = final_dict['reason']
        seller_master_id, batch_no, mrp, weight, price, price_type = '', '', 0, '', '', ''
        if final_dict.get('seller_master', ''):
            seller_master_id = final_dict['seller_master'].id
        if final_dict.get('batch_no', ''):
            batch_no = final_dict['batch_no']
        if final_dict.get('mrp', 0):
            mrp = final_dict['mrp']
        if final_dict.get('weight', ''):
            weight = final_dict['weight']
        if final_dict.get('unit_price', 0) != '':
            price = final_dict['unit_price']
        # else:
        #     price = final_dict['sku_master'].cost_price
        #     price_type = "cost_price"

        if str(seller_master_id) in seller_receipt_dict.keys():
            receipt_number = seller_receipt_dict[str(seller_master_id)]
        else:
            receipt_number = get_stock_receipt_number(user)
            seller_receipt_dict[str(seller_master_id)] = receipt_number
        adj_status, stock_stats_objs = adjust_location_stock(cycle_id, wms_code, loc, quantity, reason, user, stock_stats_objs, batch_no=batch_no, mrp=mrp,
                              seller_master_id=seller_master_id, weight=weight, receipt_number=receipt_number,
                              price = price, receipt_type='inventory-adjustment')
        if adj_status == 'Added Successfully':
            count+=1

    if stock_stats_objs:
        SKUDetailStats.objects.bulk_create(stock_stats_objs)
    check_and_update_stock(sku_codes, user)
    if user.username in MILKBASKET_USERS: check_and_update_marketplace_stock(sku_codes, user)
    return HttpResponse('Adjusted {} Entries got Success'.format(count))


@csrf_exempt
@get_admin_user
def customer_form(request, user=''):
    customer_file = request.GET['download-customer-file']
    if customer_file:
        return error_file_download(customer_file)

    wb, ws = get_work_sheet('customer', CUSTOMER_HEADERS)
    return xls_to_response(wb, '%s.customer_form.xls' % str(user.username))


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
        order_detail = ''
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
                    else:
                        order_detail = order_detail[0]
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
                if isinstance(cell_data, float):
                    get_decimal_data(cell_data, index_status, row_idx, user)
                    quantity = cell_data
            elif key == 'damaged_quantity':
                if not isinstance(cell_data, (int, float)) and cell_data:
                    if not cell_data.isdigit():
                        index_status.setdefault(row_idx, set()).add('Invalid Damaged Quantity')

                if cell_data and isinstance(cell_data, (int, float)):
                    if int(cell_data) < 0:
                        index_status.setdefault(row_idx, set()).add('Damaged Quantity should not be in negative')
                if isinstance(cell_data, float):
                    get_decimal_data(cell_data, index_status, row_idx, user)

            elif key in ['mrp', 'buy_price']:
                if cell_data and isinstance(cell_data, (int, float)):
                    if int(cell_data) < 0:
                        index_status.setdefault(row_idx, set()).add(key + ' should not be in negative')
                if isinstance(cell_data, float):
                    get_decimal_data(cell_data, index_status, row_idx, user)

            elif key in ['manufactured_date', 'expiry_date']:
                if cell_data:
                    try:
                        if isinstance(cell_data, str):
                            datetime.datetime.strptime(cell_data, "%Y-%m-%d")
                        else:
                            xldate_as_tuple(cell_data, 0)
                    except:
                        index_status.setdefault(row_idx, set()).add(key + ' in wrong format')

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
                filter_params ={}
                if order_id:
                    filter_params = {Q(order__order_id=order_id_search, order__order_code=order_code_search) |
                                     Q(order__original_order_id=order_id)}

                if sor_id:
                    seller_order = SellerOrder.objects.filter(sor_id=sor_id,
                        order__sku__sku_code=sku_code, order__user=user.id,**filter_params)
                    if not seller_order:
                        index_status.setdefault(row_idx, set()).add('Invalid Sor ID')
                    if not order_detail and seller_order.exists() :
                        order_detail = seller_order[0].order
            elif key == 'seller_id':
                seller_id = get_cell_data(row_idx, order_mapping[key], reader, file_type)
                if seller_id:
                    seller = SellerMaster.objects.filter(user=user.id,seller_id = seller_id)
                    if not seller.exists():
                        index_status.setdefault(row_idx, set()).add('Invalid Seller ID')
                    else:
                       orders =  OrderDetail.objects.exclude(status=1).filter(sku__user=user.id,sellerorder__seller__seller_id=seller_id,sku__wms_code=sku_code). \
                            annotate(ret=Sum(F('orderreturns__quantity')),
                                     dam=Sum(F('orderreturns__damaged_quantity'))).annotate(tot=F('ret') + F('dam')). \
                            filter(Q(tot__isnull=True) | Q(original_quantity__gt=F('tot')))
                       if not orders:
                           index_status.setdefault(row_idx, set()).add('No Order Data Found to Return or Returned Completly')

        if not index_status:
            if not order_detail:
                continue
            return_quantity = OrderReturns.objects.filter(order_id=order_detail.id).aggregate(qt=Sum('quantity'))[
                'qt']
            if not return_quantity:
                return_quantity = 0
            order_quantity = order_detail.original_quantity
            if order_detail.status == 3:
                order_quantity = order_quantity - order_detail.quantity
            if order_quantity  < return_quantity + float(quantity):
                index_status.setdefault(row_idx, set()).add(
                    'Returned Quantity is more than Order Quantity  Quantity Already Returned '+str(return_quantity))

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
    returns_list  = []

    for row_idx in range(1, no_of_rows):
        all_data = []
        order_data = copy.deepcopy(UPLOAD_SALES_ORDER_DATA)
        order_detail = []
        seller_order,seller = '',''
        batch_data = {}
        if not order_mapping:
            break
        order_object = ''
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
                    order_detail = OrderDetail.objects.exclude(status=1).filter(Q(original_order_id=cell_data) | Q(**order_filter),
                                                              sku_id__sku_code=sku_code, user=user.id)
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
            elif key in ['manufactured_date', 'expiry_date']:
                cell_data = get_cell_data(row_idx, order_mapping[key], reader, file_type)
                if cell_data:
                    if isinstance(cell_data, str):
                        try:
                            batch_data[key] = datetime.datetime.strptime(cell_data, "%d-%m-%Y %H:%M")
                        except:
                            batch_data[key] = datetime.datetime.now()
                    else:
                        year, month, day, hour, minute, second = xldate_as_tuple(cell_data, 0)
                        batch_data[key] = (datetime.datetime(year, month, day, hour, minute, second)).strftime("%m/%d/%Y")
            elif key in ['batch_no', 'mrp', 'weight', 'buy_price']:
                cell_data = get_cell_data(row_idx, order_mapping[key], reader, file_type)
                if cell_data:
                    batch_data[key] = cell_data
            elif key == 'marketplace':
                order_data[key] = value
            elif key == 'channel':
                order_data["marketplace"] = get_cell_data(row_idx, order_mapping[key], reader, file_type)
            elif key == 'seller_order_id':
                sor_id = get_cell_data(row_idx, order_mapping[key], reader, file_type)
                if isinstance(sor_id, float):
                    sor_id = str(int(sor_id))
                if sor_id:
                    seller_order = get_returns_seller_order_id(order_data['order_id'], sku_code, user, sor_id=sor_id)
                if seller_order:
                    order_data[key] = seller_order.id
                    order_data['seller_id'] = seller_order.seller_id
            elif key == 'seller_id':
                seller_id = get_cell_data(row_idx, order_mapping[key], reader, file_type)
                if get_misc_value('auto_allocate_sale_order',user.id,number=True,boolean=True):
                    order_detail = OrderDetail.objects.exclude(status=1).filter(sku__user=user.id,
                                                                      sellerorder__seller__seller_id=seller_id,
                                                                      sku__wms_code=sku_code). \
                        annotate(ret=Sum(F('orderreturns__quantity')),
                                dam=Sum(F('orderreturns__damaged_quantity'))).annotate(tot=F('ret') + F('dam')). \
                        filter(Q(tot__isnull=True) | Q(quantity__gt=F('tot')))
                    if user.username in MILKBASKET_USERS:
                        order_detail = order_detail.order_by('-creation_date')

            else:
                cell_data = get_cell_data(row_idx, order_mapping[key], reader, file_type)
                if cell_data:
                    order_data[key] = cell_data

            if "quantity" not in order_mapping.keys():
                order_data['quantity'] = 1
        if seller_order:
            order_detail = OrderDetail.objects.filter(id=seller_order.order.id)

        if not order_data['return_date']:
            order_data['return_date'] = datetime.datetime.now()

        if order_data.get('return_type', '') == 'DAMAGED_MISSING':
            order_data['damaged_quantity'] = order_data['quantity']
        if (order_data['quantity'] or order_data['damaged_quantity']) and sku_id:
            # if order_data.get('seller_order_id', '') and 'order_id' in order_data.keys():
            #    del order_data['order_id']
            order_quantity = float(order_data['quantity'])
            for order in  order_detail:
                if order_quantity <= 0 :
                    continue
                order_object = order
                original_quantity = order_object.original_quantity
                if order_object.status==3:
                    original_quantity = original_quantity - order_object.quantity
                if original_quantity >= order_quantity:
                    order_data['quantity'] = order_quantity
                    order_quantity = 0
                else:
                    order_data['quantity'] = original_quantity
                    order_quantity -= original_quantity
                order_data['order_id'] = order.id
                order_object.status = 4
                order_object.save()
                returns = OrderReturns.objects.create(**order_data)
                if not returns.return_id:
                    returns.return_id = 'MN%s' % returns.id
                returns.save()
                returns_list.append(returns)
                order_tracking = OrderTracking.objects.filter(order_id=order_object.id, status='returned')
                if order_tracking.exists():
                    order_tracking = order_tracking[0]
                    order_tracking.quantity = float(order_tracking.quantity) + order_data['quantity']
                    order_tracking.save()
                else:
                    OrderTracking.objects.create(order_id=order_object.id, status='returned', quantity=order_data['quantity'],
                                         creation_date=datetime.datetime.now(),
                                         updation_date=datetime.datetime.now())
            if order_quantity:
                del order_data['order_id']
                order_data['quantity'] = order_quantity
                returns = OrderReturns.objects.create(**order_data)
                if not returns.return_id:
                    returns.return_id = 'MN%s' % returns.id
                returns.save()
                returns_list.append(returns)

            if order_data.get('seller_order_id', ''):
                SellerOrder.objects.filter(id=order_data['seller_order_id']).update(status=4)


            if not batch_data:
                if order_detail:
                    if order_detail[0].picklist_set.filter():
                        if order_detail[0].picklist_set.filter()[0].stock:
                            batch_detail = order_detail[0].picklist_set.filter()[0].stock.batch_detail
                            batch_data = batch_detail.__dict__
                            del batch_data['_state']
                            del batch_data['id']
            save_return_locations(returns_list, all_data, order_data['damaged_quantity'], request, user, batch_dict = batch_data, upload=True)
    return 'Success'


def get_sales_returns_mapping(reader, file_type, user):
    order_mapping = {}
    if get_cell_data(0, 0, reader, file_type) == 'Return ID':
        order_mapping = copy.deepcopy(GENERIC_RETURN_EXCEL)
        if user.userprofile.user_type == 'marketplace_user':
            order_mapping['seller_order_id'] = 13
            order_mapping['seller_id'] = 14
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
                elif isinstance(value, float):
                    get_decimal_data(value, index_status, row_idx, user)
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
        po_reference_no = ''
        unit_price = 0
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
                    supplier_master = SupplierMaster.objects.filter(user=user.id, supplier_id=supplier_id)
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
                unit_price = value
            elif key == 'po_reference_no':
                try:
                    if isinstance(value, float):
                        value = str(int(value))
                    po_reference_no = value
                except:
                    value = ''
                po_details['po_reference_no'] = value
            elif key == 'invoice_num':
                try:
                    if isinstance(value, float):
                        value = str(int(value))
                except:
                    value = ''
                po_details['invoice_num'] = value
            elif key == 'lr_number':
                try:
                    if isinstance(value, float):
                        value = str(int(value))
                except:
                    value = ''
                po_details['lr_number'] = value
            elif key in ['cgst_tax', 'sgst_tax', 'igst_tax']:
                try:
                    po_details[key] = float(value)
                except:
                    po_details[key] = 0
            elif key == 'process_date':
                try:
                    year, month, day, hour, minute, second = xldate_as_tuple(value, 0)
                    po_details['process_date'] = datetime.datetime(year, month, day, hour, minute, second)
                except:
                    po_details['process_date'] = datetime.datetime.now()
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

        group_key = (str(supplier_id) + ':' + str(sku_code) + ':' + str(po_reference_no) + ':' + str(unit_price))
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
    lr_number, invoice_num = '', ''
    check_prefix = ''
    receipt_number = get_stock_receipt_number(user)
    NOW = datetime.datetime.now()
    user_profile = UserProfile.objects.get(user_id=user.id)
    log.info('PO Serial Mapping data for ' + user.username + ' is ' + str(final_data_dict))
    mod_locations = []
    po_sub_user_prefix = get_misc_value('po_sub_user_prefix', user.id)
    lr_number,invoice_num = '',''
    for key, value in final_data_dict.iteritems():
        quantity = len(value['imei_list'])
        po_details = value['po_details']
        if po_details['process_date']:
            NOW = po_details['process_date']
        if po_details['invoice_num']:
            invoice_num = po_details['invoice_num']
        if po_details['lr_number']:
            lr_number = po_details['lr_number']
        location_master = LocationMaster.objects.get(id=po_details['location_id'], zone__user=user.id)
        sku = SKUMaster.objects.get(id=po_details['sku_id'], user=user.id)
        open_po_dict = {'creation_date': NOW, 'order_quantity': quantity, 'po_name': po_details['po_reference_no'],
                        'price': po_details['unit_price'], 'status': 0, 'sku_id': po_details['sku_id'],
                        'supplier_id': po_details['supplier_id'],'igst_tax': po_details['igst_tax'],
                        'cgst_tax': po_details['cgst_tax'],'sgst_tax': po_details['sgst_tax'],
                         'measurement_unit': sku.measurement_type}
        open_po_obj = OpenPO(**open_po_dict)
        open_po_obj.save()
        group_key = (str(po_details['supplier_id']) + ':' + str(po_details['po_reference_no']))
        if group_key in order_id_dict:
            order_id = order_id_dict[group_key]['order_id']
            prefix = order_id_dict[group_key]['prefix']
            po_number = order_id_dict[group_key]['po_number']
        else:
            sku_code = open_po_obj.sku.sku_code
            order_id, prefix, po_number, check_prefix, inc_status = get_user_prefix_incremental(user, 'po_prefix', sku_code)
            if inc_status:
                return HttpResponse("Prefix not defined")
            order_id_dict[group_key]['order_id'] = order_id
            order_id_dict[group_key]['prefix'] = prefix
            order_id_dict[group_key]['po_number'] = po_number
        purchase_order_dict = {'open_po_id': open_po_obj.id, 'received_quantity': quantity, 'saved_quantity': 0,
                               'po_date': NOW, 'status': po_details['status'], 'prefix': prefix,
                               'order_id': order_id, 'creation_date': NOW,'updation_date':NOW,
                               'po_number': po_number}
        purchase_order = PurchaseOrder(**purchase_order_dict)
        purchase_order.po_number = get_po_reference(purchase_order)
        purchase_order.save()
        if lr_number:
            lr_details = LRDetail(lr_number=lr_number, quantity=quantity,
                                  creation_date=NOW, updation_date=NOW,
                                  purchase_order_id=purchase_order.id)
            lr_details.save()
        if invoice_num:
            seller_po_summary = SellerPOSummary.objects.create(quantity=quantity,
                                                                invoice_number = invoice_num,
                                                                invoice_date = NOW,
                                                                receipt_number=1,
                                                                putaway_quantity=quantity,
                                                                location_id=None,
                                                                purchase_order_id=purchase_order.id,
                                                                creation_date=NOW)


        po_location_dict = {'creation_date': NOW, 'status': 0, 'quantity': 0, 'original_quantity': quantity,
                            'location_id': po_details['location_id'], 'purchase_order_id': purchase_order.id, 'updation_date':NOW}
        po_location = POLocation(**po_location_dict)
        po_location.save()
        stock_dict = StockDetail.objects.create(receipt_number=receipt_number, receipt_date=NOW, quantity=quantity,
                                                status=1, location_id=po_details['location_id'],
                                                sku_id=po_details['sku_id'], unit_price = po_details['unit_price'],
                                                receipt_type='purchase order', creation_date=NOW, updation_date=NOW)

        loc_serial_mapping_switch = get_misc_value('loc_serial_mapping_switch', user.id)
        if loc_serial_mapping_switch == 'true':
            imei_nos = ','.join(value['imei_list'])
            insert_po_mapping(imei_nos, purchase_order, user.id, stock_dict)
        else:
            imei_nos = ','.join(value['imei_list'])
            insert_po_mapping(imei_nos, purchase_order, user.id)

        # SKU Stats
        save_sku_stats(user, stock_dict.sku_id, purchase_order.id, 'po', quantity, stock_dict)
        mod_locations.append(location_master.location)

    for key, value in order_id_dict.iteritems():
        if value.get('order_id'):
            check_purchase_order_created(user, value['order_id'], check_prefix)
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
                    if value:
                        if isinstance(value, float):
                            get_decimal_data(value, index_status, row_idx, user)
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
    return xls_to_response(wb, '%s.seller_transfer_form.xls' % str(user.username))


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
                    if isinstance(cell_data, float):
                        get_decimal_data(cell_data, index_status, row_idx, user)
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
                avail_qty = check_stock_available_quantity(stocks, user, stock_ids=stock_ids,
                                                           seller_master_id=data_dict['source_seller'])
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
    receipt_number = get_stock_receipt_number(user)
    for data_dict in data_list:
        update_stocks_data(data_dict['src_stocks'], data_dict['quantity'], data_dict.get('dest_stocks', ''),
                           data_dict['quantity'], user, data_dict['dest_location'], data_dict['sku_id'],
                           src_seller_id=data_dict['source_seller'], dest_seller_id=data_dict['dest_seller'],
                           receipt_type='seller-seller transfer', receipt_number=receipt_number)
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
    number_fields = ['source_quantity','dest_quantity','source_mrp','dest_mrp']
    if user.userprofile.user_type == 'marketplace_user':
        if 'seller_id' not in excel_mapping.keys():
            return 'Invalid File', None
    number_fields = ['source_quantity', 'source_mrp','dest_quantity', 'dest_mrp']
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
            elif key in ['source_weight','dest_weight'] :
                if user.username in MILKBASKET_USERS and not cell_data:
                    index_status.setdefault(row_idx, set()).add('Weight is Mandatory')
                if isinstance(cell_data, (int, float)):
                    data_dict[key] = str(int(cell_data))
                else:
                    data_dict[key] = str(cell_data)
            elif key in number_fields:
                if key in ['source_mrp','dest_mrp'] :
                    if user.username in MILKBASKET_USERS and not cell_data:
                        index_status.setdefault(row_idx, set()).add('MRP is Mandatory')
                if cell_data and (not isinstance(cell_data, (int, float)) or int(cell_data) < 0):
                    index_status.setdefault(row_idx, set()).add('Invalid %s' % inv_res[key])
                elif 'source' in key and prev_data_dict.get(key, ''):
                    data_dict[key] = prev_data_dict[key]
                    data_dict['source_updated'] = True
                else:
                    data_dict[key] = cell_data
                if key in ['source_quantity', 'dest_quantity']:
                    if cell_data:
                        if isinstance(cell_data, float):
                            get_decimal_data(cell_data, index_status, row_idx, user)
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
            if data_dict.get('source_weight', ''):
                weight = data_dict.get('source_weight' ,'')
                stock_dict["batch_detail__weight"] = weight
                reserved_dict["stock__batch_detail__weight"] = weight
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
        if data_dict.get('dest_weight','') :
            dest_filter['batch_detail__weight'] = data_dict['dest_weight']
            mrp_dict['weight'] = data_dict['dest_weight']
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
def cluster_sku_form(request, user=''):
    cluster_sku_file = request.GET['download-file']
    if cluster_sku_file:
        return error_file_download(cluster_sku_file)
    wb, ws = get_work_sheet('cluster_sku_form', CLUSTER_SKU_MAPPING.keys())
    return xls_to_response(wb, '%s.cluster_sku_form.xls' % str(user.id))

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
    headers = copy.deepcopy(STOCK_TRANSFER_ORDER_MAPPING.keys())
    if user.userprofile.user_type != 'marketplace_user':
        headers.remove('Source Warehouse Seller ID')
        headers.remove('Destination Warehouse Seller ID')
    if user.userprofile.industry_type != 'FMCG':
        headers.remove('MRP')
    wb, ws = get_work_sheet('stock_transfer_order_form', headers)
    return xls_to_response(wb, '%s.stock_transfer_order_form.xls' % str(user.username))

def create_order_fields_entry(interm_order_id, name, value, user, is_bulk_create=False,
                              order_fields_objs=None):
    if not order_fields_objs:
        order_fields_objs = []
    order_fields_data = {'original_order_id': interm_order_id, 'name': name, 'value': value, 'user': user.id,
                         'order_type': 'intermediate_order'}
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
                                                   user__in=sister_wh_names.values()).exclude(status = 3)
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
        if order_mapping.has_key('address1'):
            address1 = str(get_cell_data(row_idx, order_mapping['address1'], reader, file_type))
            if len(address1) > 255 :
                index_status.setdefault(count, set()).add('Address1 exceeding the 255 characters')
            address2 = str(get_cell_data(row_idx, order_mapping['address2'], reader, file_type))
            if len(address2) > 255 :
                index_status.setdefault(count, set()).add('Address2 exceeding the 255 characters')


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
                'original_order_id': order_id, 'user':order_data['order_assigned_wh_id'],'status':1})
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
    main_sr_numbers = []
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
            courtesy_check = OrderFields.objects.filter(user=user.id, order_type='intermediate_order', name='original_order_id', value=original_order_id)
            if not original_order_id or courtesy_check or original_order_id in main_sr_numbers:
                index_status.setdefault(count, set()).add('Main SR Number is Invalid')
            else:
                main_sr_numbers.append(original_order_id)
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
                sku_data = SKUMaster.objects.filter(sku_code=value, user=user.id)
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
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('OneAssist Central Order Upload failed. error statement is %s'%str(e))
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
    st_mapping = copy.deepcopy(STOCK_TRANSFER_ORDER_MAPPING)
    st_res = dict(zip(st_mapping.values(), st_mapping.keys()))
    order_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 st_mapping)
    if user.userprofile.user_type != 'marketplace_user':
        del st_mapping['Source Warehouse Seller ID']
        del st_mapping['Destination Warehouse Seller ID']
    if set(st_mapping.keys()).\
            issubset(order_mapping.keys()):
        return "Headers not matching"
    count = 0
    exclude_rows = []
    sku_masters_dict = {}
    order_id_order_type = {}
    order_data = {}
    log.info("Validation Started %s" % datetime.datetime.now())
    log.info("Order data Processing Started %s" % (datetime.datetime.now()))
    source_seller = ''
    dest_seller = ''
    for row_idx in range(1, no_of_rows):
        print 'Validation : %s' % str(row_idx)
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
                    admin_user = get_admin(user)
                    sister_wh = get_sister_warehouse(admin_user)
                    if (admin_user.username).lower() == str(warehouse_name).lower():
                        user_obj = admin_user
                    else:
                        user_obj = sister_wh.filter(user__username=warehouse_name)
                        if user_obj:
                            user_obj = user_obj[0].user
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
                    wh_id = user_obj.id
                    sku_master_id = sku_master[0].id
                    sku_id = get_syncedusers_mapped_sku(wh=wh_id, sku_id=sku_master_id)
                    if not sku_id:
                        index_status.setdefault(count, set()).add('SKU Code Not found in mentioned Location')
        if order_mapping.has_key('source_seller_id') and user_obj:
            cell_data = get_cell_data(row_idx, order_mapping['source_seller_id'], reader, file_type)
            if isinstance(cell_data, float):
                cell_data = str(int(cell_data))
            status, source_seller = validate_st_seller(user, cell_data, error_name='Source')
            if status:
                index_status.setdefault(count, set()).add(status)
        if order_mapping.has_key('dest_seller_id') and user_obj:
            cell_data = get_cell_data(row_idx, order_mapping['dest_seller_id'], reader, file_type)
            if isinstance(cell_data, float):
                cell_data = str(int(cell_data))
            status, dest_seller = validate_st_seller(user_obj, cell_data, error_name='Destination')
            if status:
                index_status.setdefault(count, set()).add(status)
        number_fields = {'quantity': 'Quantity', 'price': 'Price', 'cgst_tax': 'CGST Tax', 'sgst_tax': 'SGST Tax',
                         'igst_tax': 'IGST Tax', 'mrp': 'MRP'}
        for key, value in number_fields.iteritems():
            if order_mapping.has_key(key):
                cell_data = get_cell_data(row_idx, order_mapping[key], reader, file_type)
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(count, set()).add('Invalid %s' % number_fields[key])
                    if key == 'quantity':
                        if isinstance(cell_data, float):
                            get_decimal_data(cell_data, index_status, row_idx, user)
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
    all_data = {}
    for row_idx in range(1, no_of_rows):
        print 'Saving : %s' % str(row_idx)
        mrp =0
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
                try:
                    price = float(get_cell_data(row_idx, value, reader, file_type))
                except:
                    price = 0
            elif key == 'mrp':
                try:
                    mrp = float(get_cell_data(row_idx, value, reader, file_type))
                except:
                    mrp = 0
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
            elif key == 'cess_tax':
                try:
                    cess_tax = str(int(get_cell_data(row_idx, value, reader, file_type)))
                except:
                    cess_tax = str(get_cell_data(row_idx, value, reader, file_type))
                if cess_tax == '':
                    cess_tax = 0

        warehouse = User.objects.get(username=warehouse)
        cond = (user.username, warehouse.id, source_seller, dest_seller)
        all_data.setdefault(cond, [])
        all_data[cond].append([wms_code, quantity, price,cgst_tax,sgst_tax,igst_tax,cess_tax, 0, mrp])
    all_data = insert_st_gst(all_data, warehouse)
    status = confirm_stock_transfer_gst(all_data, user.username)

    if status.status_code == 200:
        return 'Success'
    else:
        return 'Failed'

@csrf_exempt
@login_required
@get_admin_user
def skupack_master_download(request, user=''):
    sku_file = request.GET['download-file']
    if sku_file:
        return error_file_download(sku_file)
    wb, ws = get_work_sheet('sku_pack_form', SKU_PACK_MAPPING.keys())
    return xls_to_response(wb, '%s.sku_pack_form.xls' % str(user.username))


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
    data_list = []
    for row_idx in range(1, no_of_rows):
        user_obj = ''
        data_dict = {}
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
                    else:
                        data_dict['sku_obj'] = sku_obj[0]
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
            data_dict['pack_id'] = pack_id
            if redundent_sku_obj :
                if redundent_sku_obj[0].pack_id != pack_id :
                    index_status.setdefault(count, set()).add('SKU Code is already mapped to other pack_id')
        if order_mapping.has_key('pack_quantity'):
            pack_quantity = 0
            try:
                pack_quantity = int(get_cell_data(row_idx, order_mapping['pack_quantity'], reader, file_type))
            except:
                index_status.setdefault(count, set()).add('Invalid pack quantity')
            data_dict['pack_quantity'] = pack_quantity

        data_list.append(data_dict)

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

    for data_dict in data_list:
        sku_obj = data_dict['sku_obj']
        sku_code = sku_obj.sku_code
        pack_id = data_dict['pack_id']
        pack_quantity = data_dict['pack_quantity']
        sku_pack = copy.deepcopy(SKU_PACK_DATA)
        pack_obj = SKUPackMaster.objects.filter(sku__wms_code= sku_code,pack_id = pack_id,sku__user = user.id)
        if pack_obj:
            pack_obj = pack_obj[0]
            pack_obj.pack_quantity = pack_quantity
            pack_obj.save()
        else:
            sku_pack['sku'] = sku_obj
            sku_pack['pack_id'] = pack_id
            sku_pack['pack_quantity'] = pack_quantity
            try:
                SKUPackMaster.objects.create(**sku_pack)
            except Exception as e:
                import traceback
                log.debug(traceback.format_exc())
                log.info('Insert New SKUPACK failed for %s and params are %s and error statement is %s' % (str(user.username), str(request.POST.dict()),str(e)))
    return 'Success'


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
                    if not isinstance(cell_data, (int, float)) and cell_data < 0:
                        index_status.setdefault(row_idx, set()).add('Invalid Quantity Amount')
                    elif isinstance(cell_data, float):
                        get_decimal_data(cell_data, index_status, row_idx, user)
                    else:
                        sku_code = get_cell_data(row_idx, blockstock_file_mapping['sku_code'], reader, file_type)
                        wh_name = get_cell_data(row_idx, blockstock_file_mapping['warehouse'], reader, file_type)
                        level = get_cell_data(row_idx, blockstock_file_mapping['level'], reader, file_type)
                        usr_obj = User.objects.filter(username=wh_name).values_list('id', flat=True)
                        ret_list = get_quantity_data(usr_obj, [sku_code], asn_true=False)
                        if ret_list:
                            avail_stock = ret_list[0]['available'] - ret_list[0]['non_kitted'] - ret_list[0]['reserved'] - ret_list[0]['blocked']
                            if level == 1:
                                if avail_stock < cell_data:
                                    index_status.setdefault(row_idx, set()).add('Stock Outage.Pls check stock in WH')
                            elif level == 3:
                                asn_avail_stock = ret_list[0]['asn'] + ret_list[0]['non_kitted'] - ret_list[0]['asn_res'] - ret_list[0]['asn_blocked']
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
                    if isinstance(cell_data, float):
                        get_decimal_data(cell_data, index_status, row_idx, user)
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

@csrf_exempt
@login_required
@get_admin_user
def cluster_sku_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status = validate_cluster_sku_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type=file_type)
        if status != 'Success':
            return HttpResponse(status)
        else:
            return HttpResponse(status)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Cluster sku form Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Cluster Sku Upload Failed")

def validate_cluster_sku_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type='xls'):
    cluster_sku_list = []
    count = 0
    st_time = datetime.datetime.now()
    index_status = {}
    cluster_skus_mapping = OrderedDict((('Cluster Name', 0),
                                        ('Sku Code', 1),
                                        ('Sequence', 2)
                                       ))
    for row_idx in range(1, no_of_rows):
        cluster_sku_dict = {}
        count += 1
        for key, value in cluster_skus_mapping.iteritems():
            cell_data = get_cell_data(row_idx, cluster_skus_mapping[key], reader, file_type)
            if key == 'Cluster Name':
                if not cell_data:
                    index_status.setdefault(count, set()).add('Input Mismatch')
                else:
                    cluster_sku_dict[key] = cell_data
            elif key == 'Sku Code':
                if not cell_data:
                    index_status.setdefault(count, set()).add('Input Mismatch')
                else:
                    if isinstance(cell_data, float):
                        cluster_sku_dict[key] = int(cell_data)
                    else:
                        cluster_sku_dict[key] = cell_data
                    sku_data = SKUMaster.objects.filter(user=user.id, sku_code=cell_data)
                    if not sku_data:
                        index_status.setdefault(count, set()).add('SKU Not Found')
            elif key == 'Sequence':
                if not cell_data:
                    index_status.setdefault(count, set()).add('Input Mismatch')
                else:
                    if isinstance(cell_data, float) or  isinstance(cell_data, int):
                        cluster_sku_dict[key] = int(cell_data)
                    else:
                        index_status.setdefault(count, set()).add('Input Mismatch')
        cluster_sku_list.append(cluster_sku_dict)
    try:
        if not index_status and cluster_sku_list:
            for data in cluster_sku_list:
                status = 'cluster Upload Failed'
                cluster_skus = {'cluster_name': '', 'sku_id': '', 'sequence': ''}
                cluster_skus['cluster_name'] = data['Cluster Name']
                cluster_skus['sequence'] = data['Sequence']
                if data['Sku Code']:
                    sku_data = SKUMaster.objects.filter(user=user.id, sku_code=data['Sku Code'])
                    if not sku_data:
                        return 'SKU Not Found'
                    else:
                        cluster_skus['sku_id'] = sku_data[0].id
                        clust_obj = ClusterSkuMapping.objects.filter(cluster_name = cluster_skus['cluster_name'], sku_id = cluster_skus['sku_id'])
                        cluster_obj_image = ClusterSkuMapping.objects.filter(cluster_name = cluster_skus['cluster_name'], sku__user= user.id)
                        if clust_obj:
                            clust_obj.update(sequence = cluster_skus['sequence'])
                            if cluster_obj_image:
                                cluster_skus['image_url'] = cluster_obj_image[0].image_url
                            status = 'Success'
                        else:
                            if cluster_obj_image:
                                cluster_skus['image_url'] = cluster_obj_image[0].image_url
                            final_data = ClusterSkuMapping(**cluster_skus)
                            final_data.save()
                            status = 'Success'
            return status
        elif index_status and file_type == 'xls':
            f_name = fname.name.replace(' ', '_')
            file_path = rewrite_excel_file(f_name, index_status, reader)
            if file_path:
                f_name = file_path
            return f_name
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Cluster sku form Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Cluster sku Upload Failed")


@csrf_exempt
@login_required
@get_admin_user
def combo_allocate_form(request, user=''):
    excel_file = request.GET['download-file']
    if excel_file:
        return error_file_download(excel_file)
    excel_headers = get_combo_allocate_excel_headers(user)
    wb, ws = get_work_sheet('Combo Allocate', excel_headers)
    return xls_to_response(wb, '%s.combo_allocate_form.xls' % str(user.id))


@csrf_exempt
def validate_combo_allocate_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type):
    mapping_dict = {}
    index_status = {}
    location = {}
    data_list = []
    inv_mapping = get_combo_allocate_excel_headers(user)
    inv_res = dict(zip(inv_mapping.values(), inv_mapping.keys()))
    excel_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 inv_mapping)
    if not set(['combo_sku_code', 'combo_location', 'combo_quantity', 'child_sku_code',
                'child_location', 'child_quantity']).issubset(excel_mapping.keys()):
        return 'Invalid File', None
    if user.userprofile.industry_type == 'FMCG':
        if not set(['combo_batch_no', 'combo_mrp', 'child_quantity', 'child_batch_no',
                    'child_mrp', 'child_weight']).issubset(excel_mapping.keys()):
            return 'Invalid File', None
    if user.userprofile.user_type == 'marketplace_user':
        if 'seller_id' not in excel_mapping.keys():
            return 'Invalid File', None
    number_fields = ['combo_quantity', 'combo_mrp', 'child_quantity', 'child_mrp']
    prev_data_dict = {}
    final_data = OrderedDict()
    for row_idx in range(1, no_of_rows):
        data_dict = {'combo_updated': False}
        for key, value in excel_mapping.iteritems():
            cell_data = get_cell_data(row_idx, value, reader, file_type)
            if key in ['combo_sku_code', 'child_sku_code']:
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
                elif 'child' in key and prev_data_dict.get(key, ''):
                    data_dict['%s_obj' % key] = prev_data_dict['%s_obj' % key]
                    data_dict[key] = prev_data_dict[key]
                    data_dict['source_updated'] = True
                else:
                    index_status.setdefault(row_idx, set()).add('Invalid %s' % inv_res[key])
            elif key in ['combo_location', 'child_location']:
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
                elif 'child' in key and prev_data_dict.get(key, ''):
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
            elif key in ['combo_batch_no', 'child_batch_no']:
                if 'combo' in key and not cell_data and prev_data_dict.get(key, ''):
                    data_dict[key] = prev_data_dict[key]
                    data_dict['source_updated'] = True
                    continue
                if isinstance(cell_data, float):
                    cell_data = str(int(cell_data))
                    data_dict[key] = cell_data
            elif key in ['combo_weight','child_weight'] :
                if user.username in MILKBASKET_USERS and not cell_data:
                    index_status.setdefault(row_idx, set()).add('Weight is Mandatory')
                if isinstance(cell_data, (int, float)):
                    data_dict[key] = str(int(cell_data))
                else:
                    data_dict[key] = str(cell_data)
            elif key in number_fields:
                if key in ['combo_mrp','child_mrp'] :
                    if user.username in MILKBASKET_USERS and not cell_data:
                        index_status.setdefault(row_idx, set()).add('MRP is Mandatory')
                if cell_data and (not isinstance(cell_data, (int, float)) or int(cell_data) < 0):
                    index_status.setdefault(row_idx, set()).add('Invalid %s' % inv_res[key])
                elif 'child' in key and prev_data_dict.get(key, ''):
                    data_dict[key] = prev_data_dict[key]
                    data_dict['source_updated'] = True
                else:
                    data_dict[key] = cell_data
                if key in ['combo_quantity','child_quantity']:
                    if not cell_data:
                        index_status.setdefault(row_idx, set()).add('Quantity should not be zero')
                    if cell_data:
                        if isinstance(cell_data, float):
                            get_decimal_data(cell_data, index_status, row_idx, user)
                        data_dict[key] = float(cell_data)

        if row_idx not in index_status:
            prev_data_dict = copy.deepcopy(data_dict)
            stock_dict = {"sku_id": data_dict['child_sku_code_obj'].id,
                          "location_id": data_dict['child_location_obj'].id,
                          "sku__user": user.id, "quantity__gt": 0}
            reserved_dict = {'stock__sku_id': data_dict['child_sku_code_obj'].id, 'stock__sku__user': user.id,
                             'status': 1,'stock__location_id': data_dict['child_location_obj'].id}
            child_batch_no = data_dict.get('child_batch_no', '')
            stock_dict["batch_detail__batch_no"] = child_batch_no
            reserved_dict["stock__batch_detail__batch_no"] = child_batch_no
            child_mrp = data_dict.get('child_mrp', '')
            stock_dict["batch_detail__mrp"] = child_mrp
            reserved_dict["stock__batch_detail__mrp"] = child_mrp
            child_weight = data_dict.get('child_weight' ,'')
            stock_dict["batch_detail__weight"] = child_weight
            reserved_dict["stock__batch_detail__weight"] = child_weight
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
                    if (stock_count - reserved_quantity) < float(data_dict['child_quantity']):
                        index_status.setdefault(row_idx, set()).add('Source Quantity reserved for Picklist')
            combo_filter = {'sku_id': data_dict['combo_sku_code_obj'].id, 'location_id': data_dict['combo_location_obj'].id,
                           'sku__user': user.id}
            mrp_dict = {}
            combo_batch_no = data_dict.get('combo_batch_no','')
            mrp_dict['batch_no'] = combo_batch_no
            combo_filter['batch_detail__batch_no'] = combo_batch_no
            combo_mrp  = data_dict.get('combo_mrp','')
            mrp_dict['mrp'] = combo_mrp
            combo_filter['batch_detail__mrp'] = combo_mrp
            combo_weight = data_dict.get('combo_weight','')
            mrp_dict['weight'] = combo_weight
            combo_filter['batch_detail__weight'] = combo_weight
            add_ean_weight_to_batch_detail(data_dict['combo_sku_code_obj'], mrp_dict)
            if seller_id:
                combo_filter['sellerstock__seller_id'] = seller_id
            combo_stocks = StockDetail.objects.filter(**combo_filter)
            group_key = '%s<<>>%s<<>>%s<<>>%s<<>>%s' % (str(data_dict['combo_sku_code_obj'].sku_code), str(data_dict['combo_location_obj'].location),
                                                  str(combo_batch_no), str(combo_mrp), str(combo_weight))
            final_data.setdefault(group_key, {'combo_sku': data_dict['combo_sku_code_obj'], 'combo_loc': data_dict['combo_location_obj'],
                                              'combo_batch_no': combo_batch_no, 'combo_mrp': combo_mrp,'seller_id':data_dict.get('seller_master_id', ''),
                                              'combo_qty': data_dict.get('combo_quantity',0), 'combo_mrp_dict': mrp_dict,
                                              'combo_stocks': combo_stocks, 'combo_weight': combo_weight,
                                              'childs': []})
            final_data[group_key]['childs'].append({'child_sku': data_dict['child_sku_code_obj'], 'child_loc': data_dict.get('child_location_obj'),
                                                    'child_batch_no': child_batch_no, 'child_mrp': child_mrp,
                                                    'child_qty': data_dict.get('child_quantity',0), 'child_stocks': stocks,
                                                    'child_mrp': child_mrp})
    final_data = final_data.values()
    if not index_status:
        return 'Success', final_data
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
def combo_allocate_upload(request, user=''):
    fname = request.FILES['files']
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
    except:
        return HttpResponse('Invalid File')
    status, final_data = validate_combo_allocate_form(request, reader, user, no_of_rows,
                                                     no_of_cols, fname, file_type)
    if status != 'Success':
        return HttpResponse(status)
    source_updated=False
    try:
        for row_data in final_data:
            transact_number = get_max_combo_allocation_id(user)
            seller_id = row_data['seller_id']
            dest_updated = False
            for data in row_data['childs']:
                desc_batch_obj = update_stocks_data(data['child_stocks'], float(data['child_qty']), row_data['combo_stocks'],
                                                    float(row_data['combo_qty']), user, [row_data['combo_loc']],
                                                    row_data['combo_sku'].id,
                                                    src_seller_id=seller_id, dest_seller_id=seller_id,
                                                    source_updated=source_updated,
                                                    mrp_dict=row_data['combo_mrp_dict'], dest_updated=dest_updated)
                sub_data = {'source_sku_code_id': data['child_sku'].id, 'source_location': data['child_loc'].location, 'source_quantity': data['child_qty'],
                            'destination_sku_code_id': row_data['combo_sku'].id, 'destination_location': row_data['combo_loc'].location,
                            'destination_quantity': row_data['combo_qty'], 'summary_type': 'combo_allocation'}
                if data['child_stocks'] and data['child_stocks'][0].batch_detail:
                    sub_data['source_batch_id'] = data['child_stocks'][0].batch_detail_id
                if desc_batch_obj:
                    sub_data['dest_batch_id'] = desc_batch_obj.id
                if seller_id:
                    sub_data['seller_id'] = seller_id
                sub_data['transact_number'] = transact_number
                SubstitutionSummary.objects.create(**sub_data)
                dest_updated = True
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Combo allocate stock failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(data_dict), str(e)))
    return HttpResponse('Success')


@csrf_exempt
@login_required
@get_admin_user
def brand_level_pricing_form(request, user=''):
    excel_file = request.GET['download-file']
    if excel_file:
        return error_file_download(excel_file)
    excel_headers = copy.deepcopy(BRAND_LEVEL_PRICING_EXCEL_MAPPING)
    wb, ws = get_work_sheet('Brand Level Pricing', excel_headers)
    return xls_to_response(wb, '%s.brand_level_pricing_form.xls' % str(user.username))


@csrf_exempt
def validate_brand_level_pricing_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type):
    index_status = {}
    price_mapping = copy.deepcopy(BRAND_LEVEL_PRICING_EXCEL_MAPPING)
    price_mapping_res = dict(zip(price_mapping.values(), price_mapping.keys()))
    excel_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 price_mapping)
    excel_check_list = price_mapping.values()
    if not set(excel_check_list).issubset(excel_mapping.keys()):
        return 'Invalid File', []
    attr_mapping = copy.deepcopy(SKU_NAME_FIELDS_MAPPING)
    number_fields = ['min_range', 'max_range', 'price', 'discount']
    data_list = []
    for row_idx in range(1, no_of_rows):
        row_data = OrderedDict()
        for key, value in excel_mapping.items():
            cell_data = get_cell_data(row_idx, value, reader, file_type)
            if key == 'attribute_type':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing SKU Attribute Name')
                elif cell_data not in ['Brand', 'Category']:
                    index_status.setdefault(row_idx, set()).add('Invalid SKU Attribute Name')
                else:
                    row_data[key] = cell_data
            elif key == 'attribute_value':
                if not index_status:
                    sku_filter_dict = {'user': user.id,
                                       attr_mapping[row_data['attribute_type']]: cell_data}
                    sku_master = SKUMaster.objects.filter(**sku_filter_dict)
                    if not sku_master.exists():
                        index_status.setdefault(row_idx, set()).add('Invalid SKU Attribute Value')
                    else:
                        row_data[key] = cell_data
            elif key in number_fields:
                try:
                    row_data[key] = float(cell_data)
                except:
                    index_status.setdefault(row_idx, set()).add('%s should be number' % price_mapping_res[key])
            else:
                row_data[key] = cell_data
        data_list.append(row_data)
    if not index_status:
        return 'Success', data_list

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name, []

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name, []

@csrf_exempt
@login_required
@get_admin_user
def brand_level_pricing_upload(request, user=''):
    fname = request.FILES['files']
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
    except:
        return HttpResponse('Invalid File')
    status, final_data = validate_brand_level_pricing_form(request, reader, user, no_of_rows,
                                                     no_of_cols, fname, file_type)
    if status != 'Success':
        return HttpResponse(status)
    for data_dict in final_data:
        pricing_master = PriceMaster.objects.filter(user=user.id, price_type=data_dict['price_type'],
                                                    min_unit_range=data_dict['min_unit_range'],
                                                    max_unit_range=data_dict['max_unit_range'],
                                                    attribute_type=data_dict['attribute_type'],
                                                    attribute_value=data_dict['attribute_value'])
        if pricing_master.exists():
            pricing_master.update(price=data_dict['price'], discount=data_dict['discount'])
        else:
            data_dict['user'] = user.id
            PriceMaster.objects.create(**data_dict)
    return HttpResponse("Success")


@csrf_exempt
@login_required
@get_admin_user
def brand_level_barcode_configuration_form(request, user=''):
    excel_file = request.GET['download-file']
    if excel_file:
        return error_file_download(excel_file)
    excel_headers = copy.deepcopy(BRAND_LEVEL_BARCODE_CONFIGURATION_MAPPING)
    wb, ws = get_work_sheet('barcode configuration', excel_headers)
    return xls_to_response(wb, '%s.brand_level_barcode_configuration_form.xls' % str(user.id))


def validate_brand_level_brand_configuration_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type):
    index_status = {}
    brandMapping = copy.deepcopy(BRAND_LEVEL_BARCODE_CONFIGURATION_MAPPING)
    excel_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type, brandMapping)
    excel_check_list = brandMapping.values()
    if not set(excel_check_list).issubset(excel_mapping.keys()):
        return 'Invalid File', []
    existingConfigs = list(MiscDetail.objects.filter(user=user.id, misc_type__contains='barcode_configuration').values_list('misc_value', flat=True))
    existingBrands = list(SKUMaster.objects.filter(user=user.id).values_list('sku_brand', flat=True).distinct())
    existingBrandMappings = dict(BarCodeBrandMappingMaster.objects.filter(user=user).values_list('sku_brand', 'configName'))
    data_list = []
    for row_idx in range(1, no_of_rows):
        row_data = OrderedDict()
        for key, value in excel_mapping.items():
            cell_data = get_cell_data(row_idx, value, reader, file_type)
            if key == 'configName':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing Configuration Name')
                elif cell_data not in existingConfigs:
                    index_status.setdefault(row_idx, set()).add('Invalid Configuration Name')
                else:
                    row_data[key] = cell_data
            elif key == 'sku_brand':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing SKU Brand')
                elif cell_data not in existingBrands:
                    index_status.setdefault(row_idx, set()).add('Invalid SKU Attribute Value')
                elif cell_data in existingBrandMappings.keys():
                    index_status.setdefault(row_idx, set()).add('%s is already mapped to config %s'
                                                %(cell_data, existingBrandMappings[cell_data]))
                else:
                    row_data[key] = cell_data
        data_list.append(row_data)
    if not index_status:
        return 'Success', data_list

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name, []

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name, []


@csrf_exempt
@login_required
@get_admin_user
def brand_level_barcode_configuration_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status, final_data = validate_brand_level_brand_configuration_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type)
        if status != 'Success':
            return HttpResponse(status)
    except:
        return HttpResponse('Invalid File')

    for data_dict in final_data:
        brandmappingObj = BarCodeBrandMappingMaster.objects.filter(user=user,
                                                                 configName=data_dict['configName'],
                                                                 sku_brand=data_dict['sku_brand'])
        if not brandmappingObj.exists():
            data_dict['user'] = user
            BarCodeBrandMappingMaster.objects.create(**data_dict)
    return HttpResponse("Success")


@csrf_exempt
@get_admin_user
def supplier_sku_attributes_form(request, user=''):
    supplier_file = request.GET['download-supplier-sku-attributes-file']
    if supplier_file:
        return error_file_download(supplier_file)
    wb, ws = get_work_sheet('supplier', SUPPLIER_SKU_ATTRIBUTE_HEADERS)
    return xls_to_response(wb, '%s.supplier_sku_attributes_form.xls' % str(user.username))

@csrf_exempt
def validate_supplier_sku_attributes_form(open_sheet, user_id):
    index_status = {}
    supplier_ids = []
    final_data = []
    attr_mapping = copy.deepcopy(SKU_NAME_FIELDS_MAPPING)
    supplier_list = SupplierMaster.objects.filter(user=user_id).values_list('supplier_id', flat=True)
    if supplier_list:
        for i in supplier_list:
            supplier_ids.append(i)
    for row_idx in range(1, open_sheet.nrows):
        row_data = OrderedDict()
        for col_idx in range(0, len(SUPPLIER_SKU_ATTRIBUTE_HEADERS)):
            key = open_sheet.cell(0, col_idx).value
            cell_data = open_sheet.cell(row_idx, col_idx).value
            # if row_idx == 0:
            #     if col_idx == 0 and cell_data != 'Supplier Id':
            #         return 'Invalid File'
            if key == 'Supplier Id':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Enter Supplier ID')
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                if cell_data and cell_data in supplier_ids:
                    row_data['supplier_id'] = SupplierMaster.objects.get(supplier_id=cell_data, user=user_id).id
                else:
                    index_status.setdefault(row_idx, set()).add('Supplier ID Not Found')

            if key == 'SKU Attribute Type(Brand, Category)':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing SKU Attribute Name')
                elif cell_data not in ['Brand', 'Category']:
                    index_status.setdefault(row_idx, set()).add('Invalid SKU Attribute Name')
                else:
                    row_data['attribute_type'] = cell_data

            elif key == 'SKU Attribute Value':
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing SKU Attribute Value')
                elif row_data['attribute_type']:
                    sku_filter_dict = {'user': user_id,
                                       attr_mapping[row_data['attribute_type']]: cell_data}
                    sku_master = SKUMaster.objects.filter(**sku_filter_dict)
                    if not sku_master.exists():
                        index_status.setdefault(row_idx, set()).add('Invalid SKU Attribute Value')
                    else:
                        row_data['attribute_value'] = cell_data

            if key == 'Price':
                if not isinstance(cell_data, (int, float)) and cell_data:
                    index_status.setdefault(row_idx, set()).add('Price Must be Integer or Float')
                elif cell_data:
                    row_data['price'] = cell_data

            if key == 'Costing Type (Price Based/Margin Based/Markup Based)':
                if cell_data :
                    if not cell_data in ['Price Based', 'Margin Based','Markup Based']:
                        index_status.setdefault(row_idx, set()).add('Costing Type should be "Price Based/Margin Based/Markup Based"')
                    if cell_data == 'Price Based' :
                        cell_data_price = open_sheet.cell(row_idx, 3).value
                        if not cell_data_price :
                            index_status.setdefault(row_idx, set()).add('Price is Mandatory For Price Based')
                        else:
                            if not isinstance(cell_data_price, (int, float)) :
                                index_status.setdefault(row_idx, set()).add('Price Should be Number')
                            else:
                                row_data['costing_type'] = cell_data
                    elif cell_data == 'Margin Based' :
                        cell_data_margin = open_sheet.cell(row_idx, 5).value
                        if not cell_data_margin :
                            index_status.setdefault(row_idx, set()).add('MarkDown Percentage is Mandatory For Margin Based')
                        elif not isinstance(cell_data_margin, (int, float)):
                            index_status.setdefault(row_idx, set()).add('MarkDown % Should be in integer or float')
                        elif  float(cell_data_margin) < 0  or float(cell_data_margin) >  100:
                            index_status.setdefault(row_idx, set()).add('MarkDown % Should be in between 0 and 100')
                        else:
                            row_data['costing_type'] = cell_data
                    elif cell_data == 'Markup Based' :
                        cell_data_markup = open_sheet.cell(row_idx, 6).value
                        if not cell_data_markup :
                            index_status.setdefault(row_idx, set()).add('Markup Percentage is Mandatory For Markup Based')
                        elif not isinstance(cell_data_markup, (int, float)):
                            index_status.setdefault(row_idx, set()).add('Markup % Should be in integer or float')
                        elif  float(cell_data_markup) < 0 or float(cell_data_markup) > 100:
                            index_status.setdefault(row_idx, set()).add('Markup % Should be in between 0 and 100')
                        else:
                            row_data['costing_type'] = cell_data

            if key == 'MarkDown Percentage':
                if not isinstance(cell_data, (int, float)) and cell_data:
                    index_status.setdefault(row_idx, set()).add('MarkDown Percentage Must be Integer or Float')
                elif cell_data:
                    row_data['margin_percentage'] = cell_data

            if key == 'Markup Percentage':
                if not isinstance(cell_data, (int, float)) and cell_data:
                    index_status.setdefault(row_idx, set()).add('Markup Percentage Must be Integer or Float')
                elif cell_data:
                    row_data['markup_percentage'] = cell_data

        final_data.append(row_data)
    if not index_status:
        return 'Success', final_data

    f_name = '%s.supplier_sku_attributes_form.xls' % user_id
    write_error_file(f_name, index_status, open_sheet, SUPPLIER_SKU_ATTRIBUTE_HEADERS, 'Supplier')
    return f_name, []


@csrf_exempt
@login_required
@get_admin_user
def supplier_sku_attributes_upload(request, user=''):
    fname = request.FILES['files']
    if fname.name.split('.')[-1] == 'xls' or fname.name.split('.')[-1] == 'xlsx':
        try:
            open_book = open_workbook(filename=None, file_contents=fname.read())
            open_sheet = open_book.sheet_by_index(0)
        except:
            return HttpResponse('Invalid File')
    status, final_data = validate_supplier_sku_attributes_form(open_sheet, str(user.id))
    if status != 'Success':
        return HttpResponse(status)
    for data_dict in final_data:
        supplier_sku = SKUSupplier.objects.filter(user=user.id,
                                                    supplier_id=data_dict['supplier_id'],
                                                    attribute_type=data_dict['attribute_type'],
                                                    attribute_value=data_dict['attribute_value'])
        if supplier_sku.exists():
            supplier_sku.update(**data_dict)
        else:
            data_dict['user'] = user.id
            SKUSupplier.objects.create(**data_dict)
    return HttpResponse("Success")


@csrf_exempt
@login_required
@get_admin_user
def order_allocation_form(request, user=''):
    label_file = request.GET['download-file']
    if label_file:
        return error_file_download(label_file)

    wb, ws = get_work_sheet('Order Labels', ORDER_ALLOCATION_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.order_label_mapping_form.xls' % str(user.username))



@csrf_exempt
@get_admin_user
def vehiclemaster_form(request, user=''):
    customer_file = request.GET['download-vehiclemaster-file']
    if customer_file:
        return error_file_download(customer_file)

    excel_keys = copy.deepcopy(VEHICLE_EXCEL_MAPPING.keys())
    customer_attributes = get_user_attributes(user, 'customer')
    attribute_names = list(customer_attributes.values_list('attribute_name').distinct())
    excel_keys = list(chain(excel_keys, attribute_names))
    wb, ws = get_work_sheet('customer', excel_keys)
    return xls_to_response(wb, '%s.customer_form.xls' % str(user.username))


def get_vehiclemaster_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type):
    excel_mapping = copy.deepcopy(VEHICLE_EXCEL_MAPPING)
    user_attributes = get_user_attributes(user, 'customer')
    attributes = user_attributes.values_list('attribute_name', flat=True)
    excel_mapping.update(dict(zip(attributes, attributes)))
    excel_file_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 excel_mapping)
    return excel_file_mapping


@csrf_exempt
def validate_vehiclemaster_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type='xls'):
    index_status = {}
    customer_names = []
    mapping_dict = get_vehiclemaster_file_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type)
    if not mapping_dict:
        return "Headers not Matching", {}
    number_fields = {}
    data_list = []
    customer_attributes = get_user_attributes(user, 'customer')
    attr_names = list(customer_attributes.values_list('attribute_name', flat=True).distinct())
    for row_idx in range(1, no_of_rows):
        if not mapping_dict:
            break
        customer_master = None
        data_dict = {}
        for key, value in mapping_dict.iteritems():
            cell_data = get_cell_data(row_idx, mapping_dict[key], reader, file_type)
            if key == 'name':
                if not cell_data and not customer_master:
                    index_status.setdefault(row_idx, set()).add('Missing Perm Registration No.')
                elif cell_data:
                    if str(cell_data).lower() in customer_names:
                        index_status.setdefault(row_idx, set()).add('Duplicate Perm Registration No.')
                    customer_master_obj = CustomerMaster.objects.filter(user=user.id, name=cell_data)
                    if customer_master_obj:
                        customer_master = customer_master_obj[0]
                        data_dict['id'] = customer_master.id
                    else:
                        data_dict['name'] = cell_data
                    customer_names.append(str(cell_data).lower())
            elif key in attr_names:
                try:
                    cell_data = int(cell_data)
                except:
                    pass
                data_dict.setdefault('attr_dict', {})
                data_dict['attr_dict'].setdefault(key, '')
                data_dict['attr_dict'][key] = cell_data
            elif cell_data:
                data_dict[key] = cell_data
        data_list.append(data_dict)

    if not index_status:
        return 'Success', data_list

    if index_status and file_type == 'csv':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_csv_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name, []

    elif index_status and file_type == 'xls':
        f_name = fname.name.replace(' ', '_')
        file_path = rewrite_excel_file(f_name, index_status, reader)
        if file_path:
            f_name = file_path
        return f_name, {}


def vehiclemaster_excel_upload(request, user, data_list):
    for final_data in data_list:
        if final_data.get('id'):
            customer_master = [CustomerMaster.objects.get(id=final_data['id'])]
        else:
            customer_master = CustomerMaster.objects.filter(user=user.id, name=final_data['name'])
        customer_data = copy.deepcopy(final_data)
        del customer_data['attr_dict']
        if customer_master:
            customer_master = customer_master[0]
            for key, value in customer_data.items():
                if key == 'id':
                    continue
                setattr(customer_master, key, value)
            customer_master.save()
        else:
            temp_data = json.loads(get_customer_master_id(request).content)
            customer_data['customer_id'] = temp_data['customer_id']
            customer_data['user'] = user.id
            customer_master = CustomerMaster(**customer_data)
            customer_master.save()
        for attr_key, attr_val in final_data['attr_dict'].iteritems():
            update_master_attributes_data(user, customer_master, attr_key, attr_val, 'customer')

    return 'success'


@csrf_exempt
@login_required
@get_admin_user
def vehiclemaster_upload(request, user=''):
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
        status, data_list = validate_vehiclemaster_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type)
        if status != 'Success':
            return HttpResponse(status)

        vehiclemaster_excel_upload(request, user, data_list)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Vehicle Master Upload failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Vehicle Master Upload Failed")

    return HttpResponse('Success')


def update_sku_make_model(request, reader, user, no_of_rows, no_of_cols, fname, file_type='xls', attributes=None):
    make_model_headers = []
    index_status = {}
    data_list = []
    attr_grouping_key = get_misc_value('sku_attribute_grouping_key', user.id)
    for col_idx in range(1, no_of_cols):
        header = get_cell_data(0, col_idx, reader, file_type)
        try:
            if isinstance(header, unicode):
                header = unicodedata.normalize('NFKD', header).encode('ascii', 'ignore')
            else:
                header = str(header)
        except Exception as e:
            header = ''
            import traceback
            log.debug(traceback.format_exc())
            log.info("Attribute Grouping Failed for user %s " % str(user.username))
        make_model_headers.append(header)
    for row_idx in range(1, no_of_rows):
        data_dict = {}
        sku_code = get_cell_data(row_idx, 0, reader, file_type)
        make_model_map = []
        for col_idx in range(1, no_of_cols):
            if get_cell_data(row_idx, col_idx, reader, file_type):
                header_name = make_model_headers[col_idx - 1]
                if header_name == 'Status':
                    continue
                temp_header_name = header_name.split('<>')
                if len(temp_header_name) != len(attr_grouping_key.split('<>')):
                    index_status.setdefault(row_idx, set()).add('Attribute Grouping Key not matching with headers')
                make_model_map.append(header_name)
        if isinstance(sku_code, float):
            sku_code = str(int(sku_code))
        sku_master = SKUMaster.objects.filter(user=user.id, sku_code=sku_code)
        if not sku_master.exists():
            index_status.setdefault(row_idx, set()).add('Invalid SKU Code')
        else:
            sku_master = sku_master[0]
            data_dict['sku_master'] = sku_master
        data_dict['sku_attribute_grouping_key'] = make_model_map
        data_list.append(data_dict)
    if index_status:
        f_name = generate_error_excel(index_status, fname, reader, file_type)
        return f_name
    create_sku_attrs = []
    sku_attr_mapping = []
    for final_data in data_list:
        exist_make_model_map = list(SKUAttributes.objects.filter(sku_id=final_data['sku_master'].id,
                                                                 attribute_name='sku_attribute_grouping_key'). \
                                    values_list('attribute_value', flat=True))
        rem_list = set(exist_make_model_map) - set(final_data['sku_attribute_grouping_key'])
        if rem_list:
            SKUAttributes.objects.filter(sku_id=final_data['sku_master'].id, attribute_name='sku_attribute_grouping_key',
                                         attribute_value__in=rem_list).delete()
            for rem_val in rem_list:
                attr_names = attr_grouping_key.split('<>')
                for attr_index, attr_name in enumerate(attr_names):
                    make_check = SKUAttributes.objects.filter(sku_id=final_data['sku_master'].id, attribute_name='sku_attribute_grouping_key',
                                                              attribute_value__regex=rem_val.split('<>')[attr_index])
                    if not make_check.exists():
                        SKUAttributes.objects.filter(sku_id=final_data['sku_master'].id, attribute_name=attr_name,
                                                     attribute_value=rem_val.split('<>')[attr_index]).delete()
        for attr_value in final_data.get('sku_attribute_grouping_key', ''):
            temp_data = attr_value.split('<>')
            attr_names = attr_grouping_key.split('<>')
            attr_dict = {'sku_attribute_grouping_key': attr_value}
            for attr_ind in range(0, len(attr_names)):
                if not temp_data[attr_ind]:
                    continue
                attr_dict[attr_names[attr_ind]] = temp_data[attr_ind]
            for attr_key, attr_val in attr_dict.items():
                create_sku_attrs, sku_attr_mapping, remove_attr_ids = update_sku_attributes_data(final_data['sku_master'], attr_key,
                                                                                attr_val,
                                                                                is_bulk_create=True,
                                                                                create_sku_attrs=create_sku_attrs,
                                                                                sku_attr_mapping=sku_attr_mapping,
                                                                                allow_multiple=True)
    #Bulk Create SKU Attributes
    if create_sku_attrs:
        SKUAttributes.objects.bulk_create(create_sku_attrs)
    return 'Success'


@csrf_exempt
@login_required
@get_admin_user
def user_prefixes_form(request, user=''):
    excel_file = request.GET['download-file']
    if excel_file:
        return error_file_download(excel_file)
    excel_mapping = copy.deepcopy(USER_PREFIXES_MAPPING)
    excel_headers = excel_mapping.keys()
    wb, ws = get_work_sheet('User Prefixes', excel_headers)
    return xls_to_response(wb, '%s.user_prefixes_form.xls' % str(user.username))


@csrf_exempt
@login_required
@get_admin_user
def user_prefixes_upload(request, user=''):
    fname = request.FILES['files']
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
    except:
        return HttpResponse('Invalid File')
    status, data_list = validate_user_prefixes_form(request, reader, user, no_of_rows,
                                                     no_of_cols, fname, file_type)
    if status != 'Success':
        return HttpResponse(status)
    save_user_prefixes(data_list)
    return HttpResponse('Success')


@csrf_exempt
def validate_user_prefixes_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type):
    index_status = {}
    data_list = []
    inv_mapping = copy.deepcopy(USER_PREFIXES_MAPPING)
    inv_res = dict(zip(inv_mapping.values(), inv_mapping.keys()))
    excel_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 inv_mapping)
    if not set(['warehouse', 'product_category', 'sku_category', 'pr_prefix', 'po_prefix',
                'grn_prefix', 'invoice_prefix']).issubset(excel_mapping.keys()):
        return 'Invalid File'

    category_list = list(SKUMaster.objects.filter(user=user.id).exclude(sku_category=''). \
                      values_list('sku_category', flat=True).distinct())
    for row_idx in range(1, no_of_rows):
        data_dict = {}
        for key, value in excel_mapping.iteritems():
            cell_data = get_cell_data(row_idx, value, reader, file_type)
            if key == 'warehouse':
                if cell_data:
                    if isinstance(cell_data, (int, float)):
                        cell_data = int(cell_data)
                    all_users = get_related_users(user.id)
                    all_user_objs = User.objects.filter(id__in=all_users)
                    warehouse = all_user_objs.filter(username=cell_data)
                    if not warehouse:
                        index_status.setdefault(row_idx, set()).add('Invalid Warehouse')
                    else:
                        data_dict['user'] = warehouse[0]
                        user = warehouse[0]
                else:
                    index_status.setdefault(row_idx, set()).add('Warehouse is Mandatory')
            elif key == 'product_category':
                if cell_data:
                    if cell_data not in PRODUCT_CATEGORIES:
                        index_status.setdefault(row_idx, set()).add('Invalid Product Category')
                    else:
                        data_dict['product_category'] = cell_data
                else:
                    index_status.setdefault(row_idx, set()).add('Product Category is Mandatory')
            elif key == 'sku_category':
                if cell_data:
                    if cell_data not in category_list and not cell_data.lower() == 'default':
                        index_status.setdefault(row_idx, set()).add('Invalid Category')
                    else:
                        data_dict['sku_category'] = cell_data
                else:
                    index_status.setdefault(row_idx, set()).add('Category is Mandatory')
            elif key in ['pr_prefix', 'po_prefix', 'grn_prefix', 'invoice_prefix']:
                if cell_data:
                    if isinstance(cell_data, float):
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


def save_user_prefixes(data_list):
    final_data = copy.deepcopy(data_list)
    for data in final_data:
        user = data['user']
        product_category = data['product_category']
        sku_category = data['sku_category']
        for key, val in data.items():
            if 'prefix' in key:
                prefix_dict = {'user_id': user.id, 'product_category': product_category,
                                'sku_category': sku_category, 'type_name': key}
                exist_obj = UserPrefixes.objects.filter(**prefix_dict)
                if exist_obj:
                    exist_obj.update(prefix=val)
                else:
                    prefix_dict['prefix'] = val
                    new_obj = UserPrefixes(**prefix_dict)
                    new_obj.save()


@csrf_exempt
@login_required
@get_admin_user
def staff_master_form(request, user=''):
    excel_file = request.GET['download-file']
    if excel_file:
        return error_file_download(excel_file)
    excel_mapping = copy.deepcopy(STAFF_MASTER_MAPPING)
    excel_headers = excel_mapping.keys()
    wb, ws = get_work_sheet('Staff Master', excel_headers)
    return xls_to_response(wb, '%s.staff_master_form.xls' % str(user.username))


@csrf_exempt
def validate_staff_master_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type):
    index_status = {}
    data_list = []
    inv_mapping = copy.deepcopy(STAFF_MASTER_MAPPING)
    inv_res = dict(zip(inv_mapping.values(), inv_mapping.keys()))
    excel_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 inv_mapping)
    if not set(['warehouse', 'plant', 'department_type', 'staff_code', 'name', 'email_id', 'reportingto_email_id', 'password', 'phone_number', 'position', 'status']).\
            issubset(excel_mapping.keys()):
        return 'Invalid File'
    company_id = get_company_id(user)
    company_list = get_companies_list(user, send_parent=True)
    company_list = map(lambda d: d['id'], company_list)
    dept_mapping = copy.deepcopy(DEPARTMENT_TYPES_MAPPING)
    dept_mapping = dict(zip(dept_mapping.values(), dept_mapping.keys()))
    # all_staff_codes = list(StaffMaster.objects.filter(company_id__in=company_list).values_list('staff_code', flat=True))
    # all_staff_codes = map(lambda d: str(d).lower(), all_staff_codes)
    company_id = get_company_id(user)
    roles_list = list(CompanyRoles.objects.filter(company_id=company_id, group__isnull=False).\
                                    values_list('role_name', flat=True))
    for row_idx in range(1, no_of_rows):
        data_dict = {}
        staff_master = None
        for key, value in excel_mapping.iteritems():
            cell_data = get_cell_data(row_idx, value, reader, file_type)
            if key == 'warehouse':
                if cell_data:
                    if isinstance(cell_data, (int, float)):
                        cell_data = int(cell_data)
                    all_users = get_related_users(user.id)
                    all_user_objs = User.objects.filter(id__in=all_users)
                    warehouse = all_user_objs.filter(username=cell_data)
                    if not warehouse:
                        index_status.setdefault(row_idx, set()).add('Invalid Warehouse')
                    else:
                        data_dict['user'] = warehouse[0]
                        user = warehouse[0]
                else:
                    index_status.setdefault(row_idx, set()).add('Warehouse is Mandatory')
            elif key == 'staff_code':
                if cell_data:
                    if isinstance(cell_data, float):
                        cell_data = str(int(cell_data))
                    exist_obj = StaffMaster.objects.filter(company_id__in=company_list, staff_code=cell_data)
                    if exist_obj:
                        staff_master = exist_obj[0]
                    else:
                        data_dict['staff_code'] = cell_data
                else:
                    index_status.setdefault(row_idx, set()).add('Staff Code is Mandatory')
            elif key == 'name':
                if cell_data:
                    data_dict[key] = cell_data
                    if staff_master:
                        setattr(staff_master, key, cell_data)
                else:
                    index_status.setdefault(row_idx, set()).add('Staff Name is Mandatory')
            elif key == 'plant':
                if cell_data:
                    data_dict[key] = cell_data
            elif key == 'department_type':
                if cell_data:
                    if cell_data not in dept_mapping.keys():
                        index_status.setdefault(row_idx, set()).add('Invalid Department Type')
                    else:
                        data_dict[key] = dept_mapping[cell_data]
            elif key == 'email_id':
                data_dict[key] = cell_data
                if cell_data and not staff_master:
                    all_sub_users = get_company_sub_users(user, company_id=company_id)
                    sub_user_email = all_sub_users.filter(email=cell_data)
                    if sub_user_email.exists():
                        index_status.setdefault(row_idx, set()).add('Email exists already')
                elif not staff_master:
                    index_status.setdefault(row_idx, set()).add('Email ID is Mandatory')
            elif key == 'password':
                if cell_data:
                    if isinstance(cell_data, float):
                        cell_data = str(int(cell_data))
                    data_dict[key] = cell_data
                elif not staff_master:
                    index_status.setdefault(row_idx, set()).add('Password is Mandatory')
            elif key == 'phone_number':
                if cell_data:
                    if isinstance(cell_data, float):
                        cell_data = str(int(cell_data))
                    data_dict[key] = cell_data
                    if staff_master:
                        setattr(staff_master, key, cell_data)
            elif key == 'position':
                if cell_data:
                    if cell_data not in roles_list:
                        index_status.setdefault(row_idx, set()).add('Invalid Position')
                    data_dict[key] = cell_data
                    if staff_master:
                        setattr(staff_master, key, cell_data)
                elif not staff_master:
                    index_status.setdefault(row_idx, set()).add('Position is Mandatory')
            elif key == 'reportingto_email_id':
                if cell_data:
                    data_dict[key] = cell_data
                    if staff_master:
                        setattr(staff_master, key, cell_data)
            elif key == 'status':
                if cell_data:
                    if str(cell_data).lower() == 'inactive':
                        cell_data = 0
                    else:
                        cell_data = 1
                    data_dict[key] = cell_data
                    if staff_master:
                        setattr(staff_master, key, cell_data)
        data_dict['staff_master'] = staff_master
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
def staff_master_upload(request, user=''):
    fname = request.FILES['files']
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
    except:
        return HttpResponse('Invalid File')
    status, data_list = validate_staff_master_form(request, reader, user, no_of_rows,
                                                     no_of_cols, fname, file_type)
    if status != 'Success':
        return HttpResponse(status)
    try:
        for final_data in data_list:
            if final_data['staff_master']:
                data = final_data['staff_master']
                old_position = data.position
                position = final_data.get('position', '')
                if position:
                    if old_position != position:
                        sub_user = User.objects.get(username=data.email_id)
                        update_user_role(user, sub_user, position, old_position=old_position)
                final_data['staff_master'].save()
            else:
                staff_code = final_data['staff_code']
                email = final_data['email_id']
                reportingto_email = final_data.get('reportingto_email_id', '')
                staff_name = final_data['name']
                password = final_data['password']
                phone = final_data.get('phone_number', '')
                staff_status = final_data.get('status', 1)
                position = final_data.get('position', '')
                user_dict = {'username': email, 'first_name': staff_name, 'password': password, 'email': email}
                parent_username = final_data['user'].username
                plant = final_data.get('plant', '')
                plants = []
                if plant:
                    plants = plant.split(',')
                warehouse_type = final_data['user'].userprofile.warehouse_type
                main_company_id = get_company_id(user)
                company_id = final_data['user'].userprofile.company_id
                department_type = final_data.get('department_type', '')
                if final_data['user'].userprofile.warehouse_type == 'DEPT':
                    department_type = final_data['user'].userprofile.stockone_code
                wh_user_obj = User.objects.get(username=parent_username)
                add_user_status = add_warehouse_sub_user(user_dict, wh_user_obj)
                if 'Added' not in add_user_status:
                    log.info(add_user_status)
                staff_obj = StaffMaster.objects.create(company_id=company_id, staff_name=staff_name, \
                                           phone_number=phone, email_id=email, status=staff_status,
                                           position=position, department_type=department_type,
                                           user_id=wh_user_obj.id, warehouse_type=warehouse_type,
                                           staff_code=staff_code, reportingto_email_id=reportingto_email)
                sub_user = User.objects.get(username=email)
                update_user_role(user, sub_user, position, old_position='')
                update_staff_plants_list(staff_obj, plants)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Save Staff Master failed for %s and params are %s and error statement is %s' % (
            str(user.username), str(data_list), str(e)))
    return HttpResponse('Success')


@csrf_exempt
@login_required
@get_admin_user
def uom_master_form(request, user=''):
    excel_file = request.GET['download-file']
    if excel_file:
        return error_file_download(excel_file)
    excel_mapping = copy.deepcopy(UOM_MASTER_MAPPING)
    excel_headers = excel_mapping.keys()
    wb, ws = get_work_sheet('UOM Master', excel_headers)
    return xls_to_response(wb, '%s.uom_master_form.xls' % str(user.username))


@csrf_exempt
@login_required
@get_admin_user
def uom_master_upload(request, user=''):
    fname = request.FILES['files']
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
    except:
        return HttpResponse('Invalid File')
    status, data_list = validate_uom_master_form(request, reader, user, no_of_rows,
                                                     no_of_cols, fname, file_type)
    if status != 'Success':
        return HttpResponse(status)
    company_id = get_company_id(user)
    for final_data in data_list:
        name = '%s-%s' % (final_data['uom'], str(int(final_data['conversion'])))
        final_data['name'] = name
        final_data['company_id'] = company_id
        uom_obj = UOMMaster.objects.filter(**final_data)
        if not uom_obj:
            UOMMaster.objects.create(**final_data)
    return HttpResponse('Success')


@csrf_exempt
def validate_uom_master_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type):
    index_status = {}
    data_list = []
    inv_mapping = copy.deepcopy(UOM_MASTER_MAPPING)
    inv_res = dict(zip(inv_mapping.values(), inv_mapping.keys()))
    excel_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 inv_mapping)
    if not set(['sku_code', 'base_uom', 'uom_type', 'uom', 'conversion']).issubset(excel_mapping.keys()):
        return 'Invalid File'

    for row_idx in range(1, no_of_rows):
        data_dict = {}
        for key, value in excel_mapping.iteritems():
            cell_data = get_cell_data(row_idx, value, reader, file_type)
            if key == 'sku_code':
                if cell_data:
                    if isinstance(cell_data, float):
                        cell_data = str(int(cell_data))
                    sku_master = SKUMaster.objects.filter(user=user.id, sku_code=cell_data)
                    if not sku_master:
                        index_status.setdefault(row_idx, set()).add('Invalid SKU Code')
                    else:
                        data_dict[key] = sku_master[0].sku_code
                else:
                    index_status.setdefault(row_idx, set()).add('SKU Code is Mandatory')
            elif key == 'conversion':
                try:
                    cell_data = float(cell_data)
                except:
                    cell_data = 0
                    index_status.setdefault(row_idx, set()).add('Invalid Conversion')
                data_dict[key] = cell_data
            elif key in ['base_uom', 'uom_type', 'uom']:
                if cell_data:
                    if key == 'uom_type':
                        if cell_data.lower() not in ['purchase', 'storage', 'consumption']:
                            index_status.setdefault(row_idx, set()).add('%s is Invalid' % inv_res[key])
                    data_dict[key] = cell_data
                else:
                    index_status.setdefault(row_idx, set()).add('%s is Mandatory' % inv_res[key])
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
def pending_pr_form(request, user=''):
    excel_file = request.GET['download-file']
    if excel_file:
        return error_file_download(excel_file)
    excel_mapping = copy.deepcopy(PENDING_PR_MAPPING)
    excel_headers = excel_mapping.keys()
    wb, ws = get_work_sheet('Purchase Request', excel_headers)
    return xls_to_response(wb, '%s.purchase_request_form.xls' % str(user.username))



@csrf_exempt
@login_required
@get_admin_user
def pending_pr_upload(request, user=''):
    fname = request.FILES['files']
    try:
        fname = request.FILES['files']
        reader, no_of_rows, no_of_cols, file_type, ex_status = check_return_excel(fname)
        if ex_status:
            return HttpResponse(ex_status)
    except:
        return HttpResponse('Invalid File')
    status, data_list = validate_pending_pr_form(request, reader, user, no_of_rows,
                                                     no_of_cols, fname, file_type)
    if status != 'Success':
        return HttpResponse(status)
    sku_code = data_list[0]['sku_code']
    priority_type = data_list[0]['priority_type']
    pr_delivery_date = data_list[0]['delivery_date']
    pr_number, prefix, full_pr_number, check_prefix, inc_status = get_user_prefix_incremental(user, 
                                                                        'pr_prefix', sku_code)
    purchaseMap = {
            'requested_user': request.user,
            'wh_user': user,
            'delivery_date': pr_delivery_date,
            'pending_level': 'level0',
            'final_status': 'saved',
            'priority_type': priority_type,
            'full_pr_number': full_pr_number,
            'prefix': prefix,
            'pr_number': pr_number,
            'sku_category': 'All',
            'product_category': 'Kits&Consumables'
        }
    pendingPurchaseObj = PendingPR.objects.create(**purchaseMap)
    for lineItem in data_list:
        sku_code = lineItem['sku_code']
        quantity = lineItem['quantity']
        sku_id = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
        pendingLineItems = {
                'pending_pr': pendingPurchaseObj,
                'purchase_type': 'PR',
                'sku_id': sku_id[0].id,
            }
        try:
            pendingLineItems['quantity'] = float(quantity)
        except:
            pendingLineItems['quantity'] = 0
        lineObj, created = PendingLineItems.objects.update_or_create(**pendingLineItems)
    
    return HttpResponse('Success')


@csrf_exempt
def validate_pending_pr_form(request, reader, user, no_of_rows, no_of_cols, fname, file_type):
    index_status = {}
    data_list = []
    inv_mapping = copy.deepcopy(PENDING_PR_MAPPING)
    inv_res = dict(zip(inv_mapping.values(), inv_mapping.keys()))
    excel_mapping = get_excel_upload_mapping(reader, user, no_of_rows, no_of_cols, fname, file_type,
                                                 inv_mapping)

    for row_idx in range(1, no_of_rows):
        data_dict = {}
        for key, value in excel_mapping.iteritems():
            cell_data = get_cell_data(row_idx, value, reader, file_type)
            if key == 'sku_code':
                if cell_data:
                    if isinstance(cell_data, float):
                        cell_data = str(int(cell_data))
                    sku_master = SKUMaster.objects.filter(user=user.id, sku_code=cell_data)
                    if not sku_master:
                        index_status.setdefault(row_idx, set()).add('Invalid SKU Code')
                    else:
                        data_dict[key] = sku_master[0].sku_code
                else:
                    index_status.setdefault(row_idx, set()).add('SKU Code is Mandatory')
            elif key == 'quantity':
                if cell_data:
                    if isinstance(cell_data, float):
                        cell_data = int(cell_data)
                        if cell_data == 0:
                            index_status.setdefault(count, set()).add('Quantity is given zero')
                        else:
                            data_dict[key] = cell_data
                    else:
                        index_status.setdefault(row_idx, set()).add('Quantity is Mandatory')
            elif key == 'delivery_date':
                if isinstance(cell_data, float):
                    year, month, day, hour, minute, second = xldate_as_tuple(cell_data, 0)
                    reqDate = datetime.datetime(year, month, day, hour, minute, second)
                elif '-' in cell_data:
                    reqDate = datetime.datetime.strptime(cell_data, "%d-%m-%Y")
                else:
                    reqDate = None
                    index_status.setdefault(row_idx, set()).add('Wrong format for Need by Date')
                data_dict[key] = reqDate
            elif key == 'priority_type':
                if cell_data:
                    cell_data = str(cell_data)
                    if cell_data not in ['normal', 'urgent']:
                        index_status.setdefault(row_idx, set()).add('Priority Type should be urgent/normal')
                    else:
                        data_dict[key] = cell_data
                else:
                    data_dict[key] = 'normal'

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
