import datetime
import time
from functools import wraps
from collections import OrderedDict
from django.db import models as django_models
from django.db.models import Sum
import copy
import re
from miebach_admin.models import *
from itertools import chain
from operator import itemgetter
from django.db.models import Q, F, FloatField
from django.db.models.functions import Cast, Concat
from django.db.models.fields import DateField, CharField
from django.db.models import Value
from utils import init_logger, get_currency_format

# from inbound import *

AJAX_DATA = {
    "draw": 0,
    "recordsTotal": 0,
    "recordsFiltered": 0,
    "aaData": [
    ]
}

log = init_logger('logs/miebach_utils.log')

NOW = datetime.datetime.now()

SKU_GROUP_FIELDS = {'group': '', 'user': ''}

#ADJUST_INVENTORY_EXCEL_HEADERS = ['WMS Code', 'Location', 'Physical Quantity', 'Reason']

ADJUST_INVENTORY_EXCEL_MAPPING = OrderedDict((('Seller ID', 'seller_id'), ('WMS Code', 'wms_code'),
                                            ('Location', 'location'),
                                            ('Physical Quantity', 'quantity'), ('Batch Number', 'batch_no'),
                                            ('MRP', 'mrp'), ('Reason', 'reason')))

SUB_CATEGORIES = {'round_neck': 'ROUND NECK', 'v_neck': 'V NECK', 'polo': 'POLO', 'chinese_collar': 'CHINESE COLLAR', 'henley': 'HENLEY', 'bags': 'BAGS',
                  'hoodie': 'HOODIE', 'jackets': 'JACKETS'}

# MANUAL_ENQUIRY_STATUS = {'pending_approval': 'Pending For Approval', 'approved': 'Approved',
#                          'confirm_order': 'Confirm Order', 'hold_order': 'Block Stock', 'order_placed': 'Order Placed',
#                          'pending_artwork': 'Pending ArtWork', 'artwork_submitted': 'ArtWork Submitted'}


MANUAL_ENQUIRY_STATUS = {'new_order': 'New Order', 'marketing_pending': 'Marketing Pending',
                         'design_pending': 'Design Pending', 'purchase_pending': 'Purchase Pending',
                         'pending_approval': 'Admin Pending', 'reseller_pending': 'Reseller Pending',
                         'approved': 'Approved', 'confirm_order': 'Confirm Order', 'order_placed': 'Order Placed',
                         'confirmed_order': 'Confirmed Order', 'hold_order': 'Stock Blocked',
                         'order_cancelled': 'Order Cancelled', 'order_closed': 'Order Closed',
                         'artwork_submitted': 'ArtWork Submitted'}

DECLARATIONS = {
    'default': 'We declare that this invoice shows actual price of the goods described inclusive of taxes and that all particulars are true and correct.',
    'TranceHomeLinen': 'Certify that the particulars given above are true and correct and the amount indicated represents the price actually charged and that there is no flow of additional consideration directly or indirectly.\n Subject to Banglore Jurisdication'}

PERMISSION_KEYS = ['add_qualitycheck', 'add_skustock', 'add_shipmentinfo', 'add_openpo', 'add_orderreturns',
                   'add_openpo', 'add_purchaseorder',
                   'add_joborder', 'add_materialpicklist', 'add_polocation', 'add_stockdetail', 'add_cyclecount',
                   'add_inventoryadjustment',
                   'add_orderdetail', 'add_picklist']
LABEL_KEYS = ["MASTERS_LABEL", "INBOUND_LABEL", "PRODUCTION_LABEL", "STOCK_LABEL", "OUTBOUND_LABEL", "SHIPMENT_LABEL",
              "OTHERS_LABEL",
              "PAYMENT_LABEL"]

SKU_DATA = {'user': '', 'sku_code': '', 'wms_code': '',
            'sku_desc': '', 'sku_group': '', 'sku_type': '', 'mix_sku': '',
            'sku_category': '', 'sku_class': '', 'threshold_quantity': 0, 'color': '', 'mrp': 0,
            'status': 1, 'online_percentage': 0, 'qc_check': 0, 'sku_brand': '', 'sku_size': '', 'style_name': '',
            'price': 0,
            'ean_number': 0, 'load_unit_handle': 'unit', 'zone_id': None, 'hsn_code': 0, 'product_type': '',
            'sub_category': '', 'primary_category': '', 'cost_price': 0, 'sequence': 0, 'image_url': '',
            'measurement_type': '', 'sale_through': '', 'shelf_life': 0, 'enable_serial_based': 0}

STOCK_TRANSFER_FIELDS = {'order_id': '', 'invoice_amount': 0, 'quantity': 0, 'shipment_date': datetime.datetime.now(),
                         'st_po_id': '', 'sku_id': '', 'status': 1}
OPEN_ST_FIELDS = {'warehouse_id': '', 'order_quantity': 0, 'price': 0, 'sku_id': '', 'status': 1,
                  'creation_date': datetime.datetime.now()}

VENDOR_DATA = {'vendor_id': '', 'name': '', 'address': '', 'phone_number': '', 'email_id': '', 'status': 1,
               'creation_date': datetime.datetime.now()}

SKU_STOCK_DATA = {'sku_id': '', 'total_quantity': 0,
                  'online_quantity': 0, 'offline_quantity': 0}

SUPPLIER_DATA = {'name': '', 'address': '', 'phone_number': '', 'email_id': '',
                 'status': 1, 'tax_type': '', 'po_exp_duration': 0,
                 'owner_name': '', 'owner_number': '', 'owner_email_id': '',
                 'spoc_name': '', 'spoc_number': '', 'spoc_email_id': '',
                 'lead_time': 0, 'credit_period': 0, 'bank_name': '', 'ifsc_code': '',
                 'branch_name': '', 'account_number': 0, 'account_holder_name': ''
                 }

SIZE_DATA = {'size_name': '', 'size_value': '', 'creation_date': datetime.datetime.now()}

PRICING_DATA = {'sku': '', 'price_type': '', 'price': 0, 'discount': 0,
                'min_unit_range': 0, 'max_unit_range': 0, 'creation_date': datetime.datetime.now()}

ISSUE_DATA = {'issue_title': '', 'name': '', 'email_id': '',
              'priority': '', 'status': 'Active',
              'issue_description': '', 'creation_date': datetime.datetime.now()}

SUPPLIER_SKU_DATA = {'supplier_id': '', 'supplier_type': '',
                     'sku': '', 'supplier_code': '', 'preference': '', 'moq': '', 'price': ''}

WAREHOUSE_SKU_DATA = {'warehouse': '', 'sku': '', 'priority': '', 'moq': '', 'price': ''}

UPLOAD_ORDER_DATA = {'order_id': '', 'title': '', 'user': '',
                     'sku_id': '', 'status': 1, 'shipment_date': datetime.datetime.now()}

UPLOAD_SALES_ORDER_DATA = {'quantity': 0, 'damaged_quantity': 0, 'return_id': '', 'order_id': '', 'sku_id': '',
                           'return_date': '',
                           'status': 1, 'reason': ''}

LOCATION_GROUP_FIELDS = {'group': '', 'location_id': ''}

LOC_DATA = {'zone_id': '', 'location': '',
            'max_capacity': 0, 'fill_sequence': 0, 'pick_sequence': 0,
            'filled_capacity': 0, 'status': 1}

ZONE_DATA = {'user': '', 'zone': ''}

ORDER_DATA = {'order_id': '', 'sku_id': '', 'title': '',
              'quantity': '', 'status': 1}

ORDER_SUMMARY_REPORT_STATUS = ['Open', 'Picklist generated', 'Partial Picklist generated', 'Picked', 'Partially picked']

ENQUIRY_REPORT_STATUS = ['pending', 'approval', 'rejected']

ZONE_CODES = ['NORTH', 'EAST', 'WEST', 'SOUTH']

RETURN_DATA = {'order_id': '', 'return_id': '', 'return_date': '', 'quantity': '', 'status': 1, 'return_type': '',
               'damaged_quantity': 0}

PALLET_FIELDS = {'pallet_code': '', 'quantity': 0, 'status': 1}

CONFIRM_SALES_RETURN = {'order_id': '', 'sku_id': ''}

CANCEL_ORDER_HEADERS = OrderedDict(
    [('', 'id'), ('Order ID', 'order_id'), ('SKU Code', 'sku__sku_code'), ('Customer ID', 'customer_id')])

PO_SUGGESTIONS_DATA = {'supplier_id': '', 'sku_id': '', 'order_quantity': '', 'order_type': 'SR', 'price': 0,
                       'status': 1}

PO_DATA = {'open_po_id': '', 'status': '', 'received_quantity': 0}

ORDER_SHIPMENT_DATA = {'shipment_number': '','manifest_number':'','shipment_date': '', 'truck_number': '', 'shipment_reference': '',
                       'status': 1, 'courier_name': '','driver_name':'','driver_phone_number':''}

SKU_FIELDS = ((('WMS SKU Code *', 'wms_code', 60), ('Product Description *', 'sku_desc', 256)),
              (('SKU Type', 'sku_type', 60), ('Put Zone *', 'zone_id', 60)),
              (('SKU Class', 'sku_class', 60), ('Threshold Quantity *', 'threshold_quantity')),
              (('SKU Category', 'sku_category', 60), ('Status', 'status', 11)))

QUALITY_CHECK_FIELDS = {'purchase_order_id': '', 'accepted_quantity': 0, 'rejected_quantity': 0, 'putaway_quantity': 0,
                        'status': 'qc_pending', 'reason': ''}

ORDER_PACKAGING_FIELDS = {'order_shipment_id': '', 'package_reference': '', 'status': 1}

SHIPMENT_INFO_FIELDS = {'order_shipment_id': '', 'order_id': '', 'shipping_quantity': '', 'status': 1,
                        'order_packaging_id': ''}

ADD_SKU_FIELDS = ((('WMS SKU Code *', 'wms_code', 60), ('Product Description *', 'sku_desc', 256)),
                  (('SKU Type', 'sku_type', 60), ('Put Zone *', 'zone_id', 60)),
                  (('SKU Class', 'sku_class', 60), ('Threshold Quantity', 'threshold_quantity', 5)),
                  (('SKU Category', 'sku_category', 60), ('Status', 'status', 11)),)

RAISE_ISSUE_FIELDS = (('Issue Title', 'issue_title'), ('User Name', 'name'), ('Email ID', 'email_id'),
                      ('Priority', 'priority'),
                      ('Issue Description', 'issue_description'),)

UPDATE_ISSUE_FIELDS = ((('Issue Title', 'issue_title', 60), ('Name', 'name', 256)),
                       (('Email ID', 'email_id', 64), ('Priority', 'priority', 32)),
                       (('Issue Description', 'issue_description', 256), ('Status', 'status', 11)),
                       (('Resolved Description', 'resolved_description'),),)

RESOLVED_ISSUE_FIELDS = ((('Issue Title', 'issue_title', 60), ('Name', 'name', 256)),
                         (('Email ID', 'email_id', 64), ('Priority', 'priority', 32)),
                         (('Issue Description', 'issue_description', 256),
                          ('Resolved Description', 'resolved_description')),
                         (('Status', 'status', 11),),)

SUPPLIER_FIELDS = ((('Supplier Id *', 'id', 60), ('Supplier Name *', 'name', 256)),
                   (('Email *', 'email_id', 64), ('Phone No. *', 'phone_number', 10)),
                   (('Address *', 'address'), ('Status', 'status', 11)),)

SKU_SUPPLIER_FIELDS = ((('Supplier ID *', 'supplier_id', 60), ('WMS Code *', 'wms_id', '')),
                       (('Supplier Code', 'supplier_code'), ('Priority *', 'preference', 32)),
                       (('MOQ', 'moq', 256, 0), ('Price', 'price'),))

RAISE_PO_FIELDS = ((('Supplier ID', 'supplier_id', 11), ('PO Name', 'po_name', 30)),
                   (('Ship To', 'ship_to', ''),))

RAISE_PO_FIELDS1 = OrderedDict(
    [('WMS Code *', 'wms_code'), ('Supplier Code', 'supplier_code'), ('Quantity *', 'order_quantity'),
     ('Price', 'price')])

MOVE_INVENTORY_FIELDS = ((('WMS Code *', 'wms_code'), ('Source Location *', 'source_loc')),
                         (('Destination Location *', 'dest_loc'), ('Quantity *', 'quantity')),)

ADJUST_INVENTORY_FIELDS = ( (('WMS Code *','wms_code'),('Location *','location')),
                            (('Physical Quantity *','quantity'),('Reason','reason')),
                            (('Pallet Code', 'pallet_no'),) )

#MOVE_INVENTORY_UPLOAD_FIELDS = ['WMS Code', 'Source Location', 'Destination Location', 'Quantity']

MOVE_INVENTORY_EXCEL_MAPPING = OrderedDict((('Seller ID', 'seller_id'), ('WMS Code', 'wms_code'),
                                            ('Source Location', 'source'),
                                            ('Destination Location', 'destination'),
                                            ('Quantity', 'quantity'), ('Batch Number', 'batch_no'),
                                            ('MRP', 'mrp')))

SKU_SUBSTITUTION_EXCEL_MAPPING = OrderedDict((('Seller ID', 'seller_id'), ('Source SKU Code', 'source_sku_code'),
                                              ('Source Location', 'source_location'),
                                              ('Source Batch Number', 'source_batch_no'),
                                              ('Source MRP', 'source_mrp'), ('Source Quantity', 'source_quantity'),
                                              ('Destination SKU Code', 'dest_sku_code'),
                                              ('Destination Location', 'dest_location'),
                                              ('Destination Batch Number', 'dest_batch_no'),
                                              ('Destination MRP', 'dest_mrp'), ('Destination Quantity', 'dest_quantity'),
                                            ))

SUPPLIER_HEADERS = ['Supplier Id', 'Supplier Name', 'Address', 'Email', 'Phone No.', 'GSTIN Number', 'PAN Number',
                    'PIN Code', 'City', 'State', 'Country', 'Days required to supply', 'Fulfillment Amount',
                    'Credibility', 'Tax Type(Options: Inter State, Intra State)', 'PO Expiry Duration',
                    'Owner Name', 'Owner Number', 'Owner Email', 'SPOC Name', 'SPOC Number', 'SPOC Email',
                    'Lead Time', 'Credit Period', 'Bank Name', 'IFSC Code', 'Branch Name',
                    'Account Number', 'Account Holder Name']

VENDOR_HEADERS = ['Vendor Id', 'Vendor Name', 'Address', 'Email', 'Phone No.']

CUSTOMER_HEADERS = ['Customer Id', 'Customer Name', 'Credit Period', 'CST Number', 'TIN Number', 'PAN Number', 'Email',
                    'Phone No.', 'City', 'State', 'Country', 'Pin Code', 'Address', 'Shipping Address', 'Selling Price Type',
                    'Tax Type(Options: Inter State, Intra State)', 'Discount Percentage(%)', 'Markup(%)', 'SPOC Name']

CUSTOMER_EXCEL_MAPPING = OrderedDict(
    (('customer_id', 0), ('name', 1), ('credit_period', 2), ('cst_number', 3), ('tin_number', 4),
     ('pan_number', 5), ('email_id', 6), ('phone_number', 7), ('city', 8), ('state', 9), ('country', 10),
     ('pincode', 11), ('address', 12), ('shipping_address', 13), ('price_type', 14), ('tax_type', 15),
     ('discount_percentage', 16), ('markup', 17), ('spoc_name', 18),
    ))

MARKETPLACE_CUSTOMER_EXCEL_MAPPING = OrderedDict(
    (('customer_id', 0), ('phone', 1), ('name', 2), ('address', 3), ('pincode', 4), ('city', 5), ('tin', 6)
     ))

SALES_RETURN_HEADERS = ['Return ID', 'Return Date', 'SKU Code', 'Product Description', 'Market Place', 'Quantity']

SALES_RETURN_TOGGLE = ['Return ID', 'SKU Code', 'Product Description', 'Shipping Quantity', 'Return Quantity',
                       'Damaged Quantity']

SALES_RETURN_BULK = ['Order ID', 'SKU Code', 'Return Quantity', 'Damaged Quantity', 'Return ID',
                     'Return Date(YYYY-MM-DD)']

RETURN_DATA_FIELDS = ['sales-check', 'order_id', 'sku_code', 'customer_id', 'shipping_quantity', 'return_quantity',
                      'damaged_quantity', 'delete-sales']

SUPPLIER_SKU_HEADERS = ['Supplier Id', 'WMS Code', 'Supplier Code', 'Preference', 'MOQ', 'Price']

MARKETPLACE_SKU_HEADERS = ['WMS Code', 'Flipkart SKU', 'Snapdeal SKU', 'Paytm SKU', 'Amazon SKU', 'HomeShop18 SKU',
                           'Jabong SKU', 'Indiatimes SKU', 'Flipkart Description', 'Snapdeal Description',
                           'Paytm Description', 'HomeShop18 Description', 'Jabong Description',
                           'Indiatimes Description', 'Amazon Description']

PURCHASE_ORDER_HEADERS = ['PO Reference', 'PO Date(MM-DD-YYYY)', 'Supplier ID', 'WMS SKU Code', 'Quantity', 'Price',
                          'Ship TO']

PURCHASE_ORDER_UPLOAD_MAPPING = OrderedDict((('Seller ID', 'seller_id'), ('PO Reference', 'po_name'),
                                            ('PO Date(MM-DD-YYYY)', 'po_date'),
                                            ('PO Delivery Date(MM-DD-YYYY)', 'po_delivery_date'),
                                            ('Supplier ID', 'supplier_id'),
                                            ('WMS SKU Code', 'wms_code'), ('Quantity', 'quantity'),
                                            ('Unit Price', 'price'), ('MRP', 'mrp'), ('CGST(%)', 'cgst_tax'),
                                            ('SGST(%)', 'sgst_tax'), ('IGST(%)', 'igst_tax'),
                                            ('UTGST(%)', 'utgst_tax'), ('CESS(%)', 'cess_tax'),
                                            ('Ship TO', 'ship_to'),
                                            ))

LOCK_FIELDS = ['', 'Inbound', 'Outbound', 'Inbound and Outbound']

LOCATION_FIELDS = ((('Zone ID *', 'zone_id'), ('Location *', 'location')),
                   (('Capacity', 'max_capacity'), ('Put Sequence', 'fill_sequence')),
                   (('Get Sequence', 'pick_sequence'), ('Status', 'status')),
                   (('Location Lock', 'lock_status'),))

USER_FIELDS = ((('User Name *', 'username'), ('Name *', 'first_name')),
               (('Groups', 'groups'),),)

ADD_USER_FIELDS = ((('User Name *', 'username'), ('First Name *', 'first_name')),
                   (('Last Name', 'last_name'), ('Email', 'email')),
                   (('Password *', 'password'), ('Re-type Password', 're_password')),)

ADD_GROUP_FIELDS = ((('Group Name *', 'group'), ('Permissions', 'permissions')),)

SHIPMENT_FIELDS = ((('Shipment Number *', 'shipment_number'), ('Shipment Date *', 'shipment_date')),
                   (('Truck Number *', 'truck_number'), ('Shipment Reference *', 'shipment_reference')),
                   (('Customer ID', 'customer_id'),))

ST_ORDER_FIELDS = {'picklist_id': '', 'stock_transfer_id': ''}

CREATE_ORDER_FIELDS = ((('Customer ID *', 'customer_id'), ('Customer Name', 'customer_name')),
                       (('Telephone', 'telephone'), ('Shipment Date *', 'shipment_date')),
                       (('Address', 'address'), ('Email', 'email_id')))

CREATE_ORDER_FIELDS1 = OrderedDict(
    [('SKU Code/WMS Code *', 'sku_id'), ('Quantity *', 'quantity'), ('Invoice Amount', 'invoice_amount')])

SALES_RETURN_FIELDS = ((('Return Tracking ID', 'return_id'),),)

MARKETPLACE_SKU_FIELDS = {'marketplace_code': '', 'sku_id': '', 'description': '',
                          'sku_type': ''}

MARKET_LIST_HEADERS = ['Market Place', 'SKU', 'Description']

MARKETPLACE_LIST = ['Flipkart', 'Snapdeal', 'Paytm', 'Amazon', 'Shopclues', 'HomeShop18', 'Jabong', 'Indiatimes']

# User Type Order Formats
ORDER_HEADERS = ['Order ID', 'Title', 'SKU Code', 'Quantity', 'Shipment Date(yyyy-mm-dd)', 'Channel Name',
                 'Customer ID', 'Customer Name', 'Email ID', 'Phone Number', 'Shipping Address', 'State', 'City',
                 'PIN Code', 'Invoice Amount(Without Tax and Discount)', 'Total Discount', 'CGST(%)', 'SGST(%)',
                 'IGST(%)', 'CESS Tax(%)', 'Order Type']

MARKETPLACE_ORDER_HEADERS = ['SOR ID', 'UOR ID', 'Seller ID', 'Order Status', 'Title', 'SKU Code', 'Quantity',
                             'Shipment Date(yyyy-mm-dd)', 'Channel Name', 'Customer ID', 'Customer Name', 'Email ID',
                             'Phone Number', 'Shipping Address', 'State', 'City', 'PIN Code', 'MRP',
                             'Invoice Amount(Without Tax and Discount)', 'Total Discount', 'CGST(%)', 'SGST(%)',
                             'IGST(%)', 'CESS Tax(%)']

USER_ORDER_EXCEL_MAPPING = {'warehouse_user': ORDER_HEADERS, 'marketplace_user': MARKETPLACE_ORDER_HEADERS,
                            'customer': ORDER_HEADERS}

# User Type Order Excel Mapping

ORDER_DEF_EXCEL = OrderedDict((('order_id', 0), ('title', 1), ('sku_code', 2), ('quantity', 3), ('shipment_date', 4),
                               ('channel_name', 5), ('shipment_check', 'true'), ('customer_id', 6),
                               ('customer_name', 7), ('email_id', 8),
                               ('telephone', 9), ('address', 10), ('state', 11), ('city', 12), ('pin_code', 13),
                               ('amount', 14), ('amount_discount', 15), ('cgst_tax', 16), ('sgst_tax', 17),
                               ('igst_tax', 18), ('cess_tax', 19), ('order_type', 20)
                               ))

MARKETPLACE_ORDER_DEF_EXCEL = OrderedDict(
    (('sor_id', 0), ('order_id', 1), ('seller', 2), ('order_status', 3), ('title', 4),
     ('sku_code', 5), ('quantity', 6), ('shipment_date', 7), ('channel_name', 8),
     ('shipment_check', 'true'), ('customer_id', 9),
     ('customer_name', 10), ('email_id', 11), ('telephone', 12), ('address', 13),
     ('state', 14), ('city', 15), ('pin_code', 16), ('mrp', 17), ('amount', 18),
     ('amount_discount', 19), ('cgst_tax', 20), ('sgst_tax', 21), ('igst_tax', 22), ('cess_tax', 23)
     ))

SALES_RETURN_FIELDS = ((('Return Tracking ID', 'return_id'),),)

REPORT_FIELDS = ((('From Date', 'from_date'), ('To Date', 'to_date')),
                 (('SKU Code', 'sku_code'), ('SKU Category', 'sku_category')),
                 (('SKU Type', 'sku_type'), ('SKU Class', 'sku_class')))

SKU_LIST_REPORTS_DATA = {('sku_list_form', 'reportsTable', 'SKU List Filters', 'sku-list', 1, 2, 'sku-report'): (
['SKU Code', 'WMS Code', 'SKU Group', 'SKU Type', 'SKU Category', 'SKU Class', 'Put Zone', 'Threshold Quantity'], (
(('SKU Code', 'sku_code'), ('SKU Category', 'sku_category')), (('SKU Type', 'sku_type'), ('SKU Class', 'sku_class')),
(('WMS Code', 'wms_code'),))), }

LOCATION_WISE_FILTER = {
    ('location_wise_form', 'locationTable', 'Location Wise Filters', 'location-wise', 3, 4, 'location-report'): (
    ['Location', 'SKU Code', 'WMS Code', 'Product Description', 'Zone', 'Receipt Number', 'Receipt Date', 'Quantity'], (
    (('SKU Code', 'sku_code'), ('SKU Category', 'sku_category')),
    (('SKU Type', 'sku_type'), ('SKU Class', 'sku_class')), (('Location', 'location'), ('Zone', 'zone_id')),
    (('WMS Code', 'wms_code'),),)), }

SUPPLIER_WISE_POS = {
    ('supplier_wise_form', 'suppliertable', 'Supplier Wise Filters', 'supplier-wise', 1, 2, 'supplier-report'): (
    ['Order Date', 'PO Number', 'WMS Code', 'Design', 'Ordered Quantity', 'Received Quantity'],
    ((('Supplier', 'supplier'),),)), }

GOODS_RECEIPT_NOTE = {
    ('receipt_note_form', 'receiptTable', 'Goods Receipt Filter', 'receipt-note', 11, 12, 'po-report'): (
    ['PO Number', 'Supplier ID', 'Supplier Name', 'Total Quantity'],
    ((('From Date', 'from_date'), ('To Date', 'to_date')), (('PO Number', 'open_po'), ('WMS Code', 'wms_code')),)), }

RECEIPT_SUMMARY = {
    ('receipt_summary_form', 'summaryTable', 'Receipt Summary', 'summary-wise', 5, 6, 'receipt-report'): (
    ['Supplier', 'Receipt Number', 'WMS Code', 'Description', 'Received Quantity'], (
    (('From Date', 'from_date'), ('To Date', 'to_date')), (('WMS Code', 'wms_code'), ('Supplier', 'supplier')),
    (('SKU Code', 'sku_code'),),)), }

DISPATCH_SUMMARY = {
    ('dispatch_summary_form', 'dispatchTable', 'Dispatch Summary', 'dispatch-wise', 13, 14, 'dispatch-report'): (
    ['Order ID', 'WMS Code', 'Description', 'Quantity', 'Date'],
    ((('From Date', 'from_date'), ('To Date', 'to_date')), (('WMS Code', 'wms_code'), ('SKU Code', 'sku_code')))), }

ORDER_SUMMARY_DICT = {
    'filters': [{'label': 'From Date', 'name': 'from_date', 'type': 'date'}, {'label': 'To Date', 'name': 'to_date',
                                                                              'type': 'date'},
                {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
                {'label': 'Marketplace', 'name': 'marketplace', 'type': 'select'},
                {'label': 'City', 'name': 'city', 'type': 'input'},
                {'label': 'State', 'name': 'state', 'type': 'input'},
                {'label': 'SKU Category', 'name': 'sku_category', 'type': 'select'},
                {'label': 'SKU Brand', 'name': 'brand', 'type': 'input'},
                {'label': 'SKU Class', 'name': 'sku_class', 'type': 'input'},
                {'label': 'SKU Size', 'name': 'sku_size', 'type': 'input'},
                {'label': 'Status', 'name': 'order_report_status', 'type': 'select'},
                {'label': 'Order ID', 'name': 'order_id', 'type': 'input'}],
    'dt_headers': ['Order Date', 'Order ID', 'Customer Name', 'SKU Brand', 'SKU Category', 'SKU Class', 'SKU Size',
                   'SKU Description', 'SKU Code', 'Order Qty', 'Unit Price', 'Price', 'MRP', 'Discount', 'Tax', 'Taxable Amount', 'City',
                   'State', 'Marketplace', 'Invoice Amount', 'Status', 'Order Status', 'Remarks'],
    'dt_url': 'get_order_summary_filter', 'excel_name': 'order_summary_report',
    'print_url': 'print_order_summary_report',
    }

OPEN_JO_REP_DICT = {
    'filters': [{'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'}, {'label': 'SKU Class', 'name': 'class',
                                                                                  'type': 'input'},
                {'label': 'SKU Category', 'name': 'category', 'type': 'select'}, {'label': 'SKU Brand',
                                                                                  'name': 'brand', 'type': 'select'},
                {'label': 'JO Code', 'name': 'job_code', 'type': 'input'},
                {'label': 'Stages', 'name': 'stage', 'type': 'select'}],
    'dt_headers': ['JO Code', 'Jo Creation Date', 'SKU Brand', 'SKU Category', 'SKU Class', 'SKU Code', 'Stage',
                   'Quantity'],
    'dt_url': 'get_openjo_report_details', 'excel_name': 'open_jo_report', 'print_url': 'print_open_jo_report',
    }

SKU_WISE_PO_DICT = {'filters': [{'label': 'From Date', 'name': 'from_date', 'type': 'date'},
                                {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
                                {'label': 'Supplier ID', 'name': 'supplier', 'type': 'supplier_search'},
                                {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},],
                    'dt_headers': ['PO Date', 'Supplier', 'SKU Code', 'Order Quantity', 'Received Quantity',
                                   'Rejected Quantity', 'Receipt Date', 'Status'],
                    'mk_dt_headers': ['PO Date', 'PO Number', 'Supplier ID', 'Supplier Name', 'SKU Code',
                                      'SKU Description', 'SKU Class', 'SKU Style Name', 'SKU Brand', 'SKU Category',
                                      'PO Qty', 'Unit Rate', 'MRP', 'Pre-Tax PO Amount', 'Tax', 'After Tax PO Amount',
                                      'Qty received', 'Status'],
                    'dt_url': 'get_sku_purchase_filter', 'excel_name': 'sku_wise_purchases',
                    'print_url': 'print_sku_wise_purchase',
                    }

GRN_DICT = {'filters': [{'label': 'From Date', 'name': 'from_date', 'type': 'date'},
                        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
                        {'label': 'PO Number', 'name': 'open_po', 'type': 'input'},
                        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'}],
            'dt_headers': ['PO Number', 'Supplier ID', 'Supplier Name', 'Order Quantity', 'Received Quantity'],
            'mk_dt_headers': ['PO Number', 'Supplier ID', 'Supplier Name', 'Order Quantity', 'Received Quantity'],
            # 'mk_dt_headers': ['Received Date', 'PO Date', 'PO Number', 'Supplier ID', 'Supplier Name', 'Recepient',
            #                   'SKU Code',
            #                   'SKU Description', 'SKU Class', 'SKU Style Name', 'SKU Brand', 'SKU Category',
            #                   'Received Qty', 'Unit Rate',
            #                   'Pre-Tax Received Value', 'CGST(%)', 'SGST(%)', 'IGST(%)', 'UTGST(%)',
            #                   'Post-Tax Received Value',
            #                   'Margin %', 'Margin', 'Invoiced Unit Rate', 'Invoiced Total Amount'],
            'dt_url': 'get_po_filter', 'excel_name': 'goods_receipt', 'print_url': '',
            }

GRN_EDIT_DICT = {'filters': [{'label': 'From Date', 'name': 'from_date', 'type': 'date'},
                  {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
                  {'label': 'PO Number', 'name': 'open_po', 'type': 'input'},
                  {'label': 'Invoice Number', 'name': 'invoice_number', 'type': 'input'},
                  {'label': 'Supplier ID', 'name': 'supplier', 'type': 'supplier_search'},
                  ],
      'dt_headers': ['PO Number', 'Supplier ID', 'Supplier Name', 'Order Quantity', 'Received Quantity'],
      'mk_dt_headers': ['PO Number', 'Supplier ID', 'Supplier Name', 'Order Quantity', 'Received Quantity'],
      'dt_url': 'get_grn_edit_filter', 'excel_name': '', 'print_url': ''
    }

SKU_WISE_GRN_DICT = {'filters' : [
			{'label': 'From Date', 'name': 'from_date', 'type': 'date'},
                        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
                        {'label': 'PO Number', 'name': 'open_po', 'type': 'input'},
                        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'}
		    ],
		'dt_headers': ["Received Date", "PO Date", "PO Number", "Supplier ID", "Supplier Name", "Recepient",
                       "SKU Code", "SKU Description", "HSN Code", "SKU Class", "SKU Style Name", "SKU Brand",
                       "SKU Category", "Received Qty", "Unit Rate", "Pre-Tax Received Value", "CGST(%)",
                       "SGST(%)", "IGST(%)", "UTGST(%)", "CESS(%)", "CGST",
                       "SGST", "IGST", "UTGST", "CESS", "Post-Tax Received Value", "Invoiced Unit Rate",
                       "Invoiced Total Amount", "Invoice Number", "Invoice Date", "Challan Number", "Challan Date"],
		'mk_dt_headers': [ "Received Date", "PO Date", "PO Number", "Supplier ID", "Supplier Name", "Recepient",
                           "SKU Code", "SKU Description", "HSN Code", "SKU Class", "SKU Style Name", "SKU Brand", "SKU Category",
                           "Received Qty", "Unit Rate", "Pre-Tax Received Value", "CGST(%)", "SGST(%)",
                           "IGST(%)", "UTGST(%)", "CESS(%)", "CGST",
                            "SGST", "IGST", "UTGST", "CESS", "Post-Tax Received Value", "Margin %",
                           "Margin", "Invoiced Unit Rate", "Invoiced Total Amount", "Invoice Number", "Invoice Date",
                           "Challan Number", "Challan Date"],
		'dt_url': 'get_sku_wise_po_filter', 'excel_name': 'goods_receipt', 'print_url': '',
	   }

SKU_WISE_RTV_DICT = {'filters' : [
                        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
                        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
                        {'label': 'Supplier ID', 'name': 'supplier', 'type': 'supplier_search'},
                        {'label': 'Purchase Order ID', 'name': 'open_po', 'type': 'input'},
                        {'label': 'Invoice Number', 'name': 'invoice_number', 'type': 'input'},
                        {'label': 'RTV Number', 'name': 'rtv_number', 'type': 'input'}
		    ],
		'dt_headers': [ "RTV Number", "RTV Date", "Order ID", "Supplier ID", "Supplier Name", "SKU Code",
                           "SKU Description", "HSN Code", "EAN Number", "MRP", "Quantity", "Unit Price", "CGST(%)", "SGST(%)",
                           "IGST(%)", "UTGST(%)", "CESS(%)", "Total Amount", "Invoice Number",
                           "Invoice Date"],
		'mk_dt_headers': [ "RTV Number", "RTV Date", "Order ID", "Supplier ID", "Supplier Name", "SKU Code",
                           "SKU Description", "HSN Code", "EAN Number", "MRP", "Quantity", "Unit Price", "CGST(%)", "SGST(%)",
                           "IGST(%)", "UTGST(%)", "CESS(%)", "Total Amount", "Invoice Number",
                           "Invoice Date"],
		'dt_url': 'get_sku_wise_rtv_filter', 'excel_name': 'sku_wise_rtv_report', 'print_url': '',
	   }


SELLER_INVOICE_DETAILS_DICT = {
    'filters': [{'label': 'From Date', 'name': 'from_date', 'type': 'date'},
                {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
                {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'}],
    'dt_headers': ['Date', 'Supplier', 'Seller ID', 'Seller Name', 'SKU Code', 'SKU Description', 'SKU Class',
                   'SKU Style Name', 'SKU Brand', 'SKU Category', 'Accepted Qty', 'Rejected Qty', 'Total Qty', 'Amount',
                   'Tax', 'Total Amount'],
    'dt_url': 'get_seller_invoices_filter', 'excel_name': 'seller_invoices_filter',
    'print_url': 'print_seller_invoice_report',
}

RM_PICKLIST_REPORT_DICT = {
    'filters': [
        {'label': 'From JO Creation Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To JO Creation Date', 'name': 'to_date', 'type': 'date'},
        {'label': 'Job Code', 'name': 'job_order_code', 'type': 'input'},
        {'label': 'FG SKU Code', 'name': 'fg_sku_code', 'type': 'input'},
        {'label': 'RM SKU Code', 'name': 'rm_sku_code', 'type': 'input'},
        {'label': 'Location', 'name': 'location', 'type': 'input'},
        {'label': 'Pallet', 'name': 'pallet', 'type': 'input'}
    ],
    'dt_headers': ['Jo Code', 'Jo Creation Date', 'FG SKU Code', 'RM SKU Code', 'Location',
                   'Pallet Code', 'Quantity', 'Processed Date'],
    'dt_url': 'get_rm_picklist_report', 'excel_name': 'rm_picklist_report',
    'print_url': 'print_rm_picklist_report',
}

STOCK_LEDGER_REPORT_DICT = {
    'filters': [
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
    ],
    'dt_headers': ['Date', 'SKU Code', 'SKU Description', 'Style Name', 'Brand', 'Category',
                   'Size', 'Opening Stock', 'Receipt Quantity', 'Produced Quantity', 'Dispatch Quantity',
                   'Return Quantity', 'Adjustment Quantity', 'Consumed Quantity', 'Closing Stock'],
    'dt_url': 'get_stock_ledger_report', 'excel_name': 'stock_ledger_report',
    'print_url': 'print_stock_ledger_report',
}

SHIPMENT_REPORT_DICT = {
    'filters': [
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
        {'label': 'Order ID', 'name': 'order_id', 'type': 'input'},
        {'label': 'Customer ID', 'name': 'order_id', 'type': 'customer_search'}
    ],
    'dt_headers': ['Shipment Number' ,'Order ID', 'SKU Code', 'Title', 'Customer Name', 'Quantity', 'Shipped Quantity', 'Truck Number',
                   'Date', 'Shipment Status', 'Courier Name', 'Payment Status', 'Pack Reference'],
    'dt_url': 'get_shipment_report', 'excel_name': 'get_shipment_report',
    'print_url': 'print_shipment_report',
}

DIST_SALES_REPORT_DICT = {
    'filters': [
        {'label': 'Zone Code', 'name': 'zone_code', 'type': 'select'},
        {'label': 'Distributor Code', 'name': 'distributor_code', 'type': 'distributor_search'},
        {'label': 'Order No', 'name': 'order_id', 'type': 'input'},
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
        {'label': 'Order Status', 'name': 'order_report_status', 'type': 'select'},
        {'label': 'Product Category', 'name': 'sku_category', 'type': 'select'},
        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
    ],
    'dt_headers': ['Zone Code', 'Distributor Code', 'Order No', 'Order Date', 'Product Category',
                   'SKU Code', 'SKU Quantity', 'SKU Price', 'Value Before Tax', 'GST Rate', 'GST Value',
                   'Value After Tax', 'Order Status'],
    'dt_unsort': ['Zone Code', 'Distributor Code', 'SKU Price', 'GST Rate', 'GST Value', 'Value Before Tax', 'Value After Tax', 'Order Status'],
    'dt_url': 'get_dist_sales_report', 'excel_name': 'get_dist_sales_report',
    'print_url': 'print_dist_sales_report',

}

RESELLER_SALES_REPORT_DICT = {
'filters': [
        {'label': 'Zone Code', 'name': 'zone_code', 'type': 'select'},
        {'label': 'Distributor Code', 'name': 'distributor_code', 'type': 'distributor_search'},
        {'label': 'Reseller Code', 'name': 'reseller_code', 'type': 'reseller_search'},
        {'label': 'Corporate Name', 'name': 'corporate_name', 'type': 'corporates_search'},
        {'label': 'Order No', 'name': 'order_id', 'type': 'input'},
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
        {'label': 'Order Status', 'name': 'order_report_status', 'type': 'select'},
        {'label': 'Product Category', 'name': 'sku_category', 'type': 'select'},
        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
    ],
    'dt_headers': ['Zone Code', 'Distributor Code', 'Reseller Code', 'Corporate Name',
                   'Order No', 'Order Date', 'Product Category', 'SKU Code', 'SKU Quantity', 'SKU Price',
                   'Value Before Tax', 'GST Rate', 'GST Value', 'Value After Tax', 'Order Status'],
    'dt_unsort': ['Zone Code', 'Distributor Code', 'Reseller Code', 'GST Rate', 'GST Value', 'Value Before Tax', 'Value After Tax', 'Order Status'],
    'dt_url': 'get_reseller_sales_report', 'excel_name': 'get_reseller_sales_report',
    'print_url': 'print_reseller_sales_report',
}

DIST_TARGET_SUMMARY_REPORT = {
'filters': [
        {'label': 'Distributor Code', 'name': 'distributor_code', 'type': 'distributor_search'},
        {'label': 'Reseller Code', 'name': 'reseller_code', 'type': 'reseller_search'},
        {'label': 'Corporate Name', 'name': 'corporate_name', 'type': 'corporates_search'},
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
    ],
    'dt_headers': ['Distributor Code', 'Distributor Target',
                   'YTD Targets', 'YTD Actual Sale', 'Excess / Shortfall %'
                ],
    'dt_url': 'get_dist_target_summary_report', 'excel_name': 'get_dist_target_summary_report',
    'dt_unsort': ['Distributor Code', 'Distributor Target', 'YTD Targets', 'YTD Actual Sale', 'Excess / Shortfall %'],
    'print_url': 'print_dist_target_summary_report',
}

DIST_TARGET_DETAILED_REPORT = {
'filters': [
        {'label': 'Distributor Code', 'name': 'distributor_code', 'type': 'distributor_search'},
        {'label': 'Reseller Code', 'name': 'reseller_code', 'type': 'reseller_search'},
        {'label': 'Corporate Name', 'name': 'corporate_name', 'type': 'corporates_search'},
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
    ],
    'dt_headers': ['Distributor Code', 'Distributor Target', 'Reseller Code', 'Reseller Target',
                   'Corporate Name', 'Corporate Target', 'YTD Targets', 'YTD Actual Sale', 'Excess / Shortfall %'
                ],
    'dt_url': 'get_dist_target_detailed_report', 'excel_name': 'get_dist_target_detailed_report',
    'dt_unsort': ['Distributor Code', 'Distributor Target', 'Reseller Code', 'Reseller Target',
                   'Corporate Name', 'Corporate Target', 'YTD Targets', 'YTD Actual Sale', 'Excess / Shortfall %'],
    'print_url': 'print_dist_target_detailed_report',
}

RESELLER_TARGET_SUMMARY_REPORT = {
'filters': [
        {'label': 'Reseller Code', 'name': 'reseller_code', 'type': 'reseller_search'},
        {'label': 'Corporate Name', 'name': 'corporate_name', 'type': 'corporates_search'},
    ],
    'dt_headers': ['Reseller Code', 'Reseller Target',
                   'YTD Targets', 'YTD Actual Sale', 'Excess / Shortfall %'
                ],
    'dt_url': 'get_reseller_target_summary_report', 'excel_name': 'get_reseller_target_summary_report',
    'dt_unsort': ['Reseller Code', 'Reseller Target', 'YTD Targets', 'YTD Actual Sale', 'Excess / Shortfall %'],
    'print_url': 'print_reseller_target_summary_report',
}

RESELLER_TARGET_DETAILED_REPORT = {
'filters': [
        {'label': 'Reseller Code', 'name': 'reseller_code', 'type': 'reseller_search'},
        {'label': 'Corporate Name', 'name': 'corporate_name', 'type': 'corporates_search'},
    ],
    'dt_headers': ['Reseller Code', 'Reseller Target', 'Corporate Name', 'Corporate Target', 'YTD Targets',
                   'YTD Actual Sale', 'Excess / Shortfall %'
                ],
    'dt_url': 'get_reseller_target_detailed_report', 'excel_name': 'get_reseller_target_detailed_report',
    'dt_unsort': ['Reseller Code', 'Reseller Target', 'Corporate Name', 'Corporate Target', 'YTD Targets',
                   'YTD Actual Sale', 'Excess / Shortfall %'],
    'print_url': 'print_reseller_target_detailed_report',
}

CORPORATE_TARGET_REPORT = {
'filters': [
        {'label': 'Corporate Name', 'name': 'corporate_name', 'type': 'corporates_search'},
    ],
    'dt_headers': ['Corporate Name', 'Corporate Target', 'YTD Targets', 'YTD Actual Sale', 'Excess / Shortfall %'],
    'dt_url': 'get_corporate_target_report', 'excel_name': 'get_corporate_target_report',
    'print_url': 'print_corporate_target_report',
}

RESELLER_TARGET_REPORT = {
'filters': [
        {'label': 'Zone Code', 'name': 'zone_code', 'type': 'select'},
        {'label': 'Distributor Code', 'name': 'distributor_code', 'type': 'distributor_search'},
        {'label': 'Reseller Code', 'name': 'reseller_code', 'type': 'reseller_search'},
    ],
    'dt_headers': ['Zone Code', 'Distributor Code', 'Reseller Code', 'Reseller Target',
                   'Order Value Before Tax', 'Order Value After Tax', '% Achieved',
                   'Pending Target', '% Pending Target', 'Days Passed',
                   'Days LeftOver', 'Per Day Average done', 'Standard Req Average', 'Average required'
                   ],
    'dt_url': 'get_reseller_target_report', 'excel_name': 'get_reseller_target_report',
    'print_url': 'print_reseller_target_report',
}

ZONE_TARGET_DETAILED_REPORT = {
    'filters': [
        {'label': 'Zone Code', 'name': 'zone_code', 'type': 'select'},
        {'label': 'Distributor Code', 'name': 'distributor_code', 'type': 'distributor_search'},
        {'label': 'Reseller Code', 'name': 'reseller_code', 'type': 'reseller_search'},
        {'label': 'Corporate Name', 'name': 'corporate_name', 'type': 'corporates_search'},
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
    ],
    'dt_headers': ['Zone Code', 'Zone Target', 'Distributor Code', 'Distributor Target', 'Reseller Code',
                   'Reseller Target', 'Corporate Name', 'Corporate Target', 'YTD Targets', 'YTD Actual Sale',
                   'Excess / Shortfall %'
                   ],
    'dt_url': 'get_zone_target_detailed_report', 'excel_name': 'get_zone_target_detailed_report',
    'dt_unsort': ['Zone Code', 'Zone Target', 'Distributor Code', 'Distributor Target', 'Reseller Code',
                   'Reseller Target', 'Corporate Name', 'Corporate Target', 'YTD Targets', 'YTD Actual Sale',
                   'Excess / Shortfall %'
                   ],
    'print_url': 'print_zone_target_detailed_report'
}

ZONE_TARGET_SUMMARY_REPORT = {
'filters': [
        {'label': 'Zone Code', 'name': 'zone_code', 'type': 'select'},
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
    ],
    'dt_headers': ['Zone Code', 'Zone Target', 'YTD Targets', 'YTD Actual Sale', 'Excess / Shortfall %'],
    'dt_url': 'get_zone_target_summary_report', 'excel_name': 'get_zone_target_summary_report',
    'dt_unsort': ['Zone Code', 'Zone Target', 'YTD Targets', 'YTD Actual Sale', 'Excess / Shortfall %'],
    'print_url': 'print_zone_target_summary_report'
}

CORPORATE_RESELLSER_MAPPING_REPORT = {
    'filters': [
        {'label': 'Zone Code', 'name': 'zone_code', 'type': 'select'},
        {'label': 'Distributor Code', 'name': 'distributor_code', 'type': 'distributor_search'},
        {'label': 'Reseller Code', 'name': 'reseller_code', 'type': 'reseller_search'},
        {'label': 'Corporate Name', 'name': 'corporate_name', 'type': 'corporates_search'},
    ],
    'dt_headers': ['Zone Code', 'Distributor Code','Reseller Code', 'Corporate Name'],
    'dt_url': 'get_corporate_reseller_mapping_report', 'excel_name': 'get_corporate_reseller_mapping_report',
    'dt_unsort': ['Zone Code', 'Distributor Code','Reseller Code', 'Corporate Name'],
    'print_url': 'print_corporate_reseller_mapping_report'
}

ENQUIRY_STATUS_REPORT = {
'filters': [
        {'label': 'Zone Code', 'name': 'zone_code', 'type': 'select'},
        {'label': 'Distributor Code', 'name': 'distributor_code', 'type': 'distributor_search'},
        {'label': 'Reseller Code', 'name': 'reseller_code', 'type': 'reseller_search'},
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
        {'label': 'Enquiry No', 'name': 'enquiry_number', 'type': 'input'},
        {'label': 'Aging Period', 'name': 'aging_period', 'type': 'input'},
        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
        {'label': 'Enquiry Status', 'name': 'enquiry_status', 'type': 'select'},
    ],
    'dt_headers': ['Zone Code', 'Distributor Code', 'Reseller Code', 'Product Category', 'SKU Code', 'SKU Quantity',
                   'Enquiry No', 'Enquiry Aging', 'Enquiry Status'],
    'dt_url': 'get_enquiry_status_report', 'excel_name': 'get_enquiry_status_report',
    'dt_unsort': ['Zone Code', 'Distributor Code', 'Reseller Code', 'Product Category', 'SKU Code', 'SKU Quantity',
                   'Enquiry No', 'Enquiry Aging', 'Enquiry Status'],
    'print_url': 'print_enquiry_status_report',
}

RETURN_TO_VENDOR_REPORT = {
    'filters': [
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
        {'label': 'Supplier ID', 'name': 'supplier', 'type': 'supplier_search'},
        {'label': 'Purchase Order ID', 'name': 'open_po', 'type': 'input'},
        {'label': 'Invoice Number', 'name': 'invoice_number', 'type': 'input'},
        {'label': 'RTV Number', 'name': 'rtv_number', 'type': 'input'}
    ],
    'dt_headers': ['RTV Number', 'Supplier ID', 'Supplier Name', 'Order ID', 'Invoice Number', 'Return Date'],
    'dt_url': 'get_rtv_report', 'excel_name': 'get_rtv_report',
    'print_url': 'print_rtv_report',
}

REPORT_DATA_NAMES = {'order_summary_report': ORDER_SUMMARY_DICT, 'open_jo_report': OPEN_JO_REP_DICT,
                     'sku_wise_po_report': SKU_WISE_PO_DICT,
                     'grn_report': GRN_DICT, 'sku_wise_grn_report' : SKU_WISE_GRN_DICT, 'seller_invoice_details': SELLER_INVOICE_DETAILS_DICT,
                     'rm_picklist_report': RM_PICKLIST_REPORT_DICT, 'stock_ledger_report': STOCK_LEDGER_REPORT_DICT,
                     'shipment_report': SHIPMENT_REPORT_DICT, 'dist_sales_report': DIST_SALES_REPORT_DICT,
                     'reseller_sales_report': RESELLER_SALES_REPORT_DICT,
                     'dist_target_summary_report': DIST_TARGET_SUMMARY_REPORT,
                     'dist_target_detailed_report': DIST_TARGET_DETAILED_REPORT,
                     'reseller_target_summary_report': RESELLER_TARGET_SUMMARY_REPORT,
                     'reseller_target_detailed_report': RESELLER_TARGET_DETAILED_REPORT,
                     'rtv_report': RETURN_TO_VENDOR_REPORT, 'sku_wise_rtv_report' : SKU_WISE_RTV_DICT,
                     'zone_target_summary_report': ZONE_TARGET_SUMMARY_REPORT,
                     'zone_target_detailed_report': ZONE_TARGET_DETAILED_REPORT,
                     'corporate_target_report': CORPORATE_TARGET_REPORT,
                     'corporate_reseller_mapping_report': CORPORATE_RESELLSER_MAPPING_REPORT,
                     'enquiry_status_report': ENQUIRY_STATUS_REPORT,
                     'grn_edit': GRN_EDIT_DICT
                     }

SKU_WISE_STOCK = {('sku_wise_form', 'skustockTable', 'SKU Wise Stock Summary', 'sku-wise', 1, 2, 'sku-wise-report'): (
['SKU Code', 'WMS Code', 'Product Description', 'SKU Category', 'Total Quantity'], (
(('SKU Code', 'sku_code'), ('SKU Category', 'sku_category')), (('SKU Type', 'sku_type'), ('SKU Class', 'sku_class')),
(('WMS Code', 'wms_code'),))), }

SKU_WISE_PURCHASES = {('sku_wise_purchase', 'skupurchaseTable', 'SKU Wise Purchase Orders', 'sku-purchase-wise', 1, 2,
                       'sku-wise-purchase-report'): (
['PO Date', 'Supplier', 'SKU Code', 'Order Quantity', 'Received Quantity', 'Receipt Date', 'Status'],
((('WMS SKU Code', 'wms_code'),),)), }

SALES_RETURN_REPORT = {
    ('sales_return_form', 'salesreturnTable', 'Sales Return Reports', 'sales-report', 1, 2, 'sales-return-report'): (
    ['SKU Code', 'Order ID', 'Customer ID', 'Return Date', 'Status', 'Quantity'], (
    (('SKU Code', 'sku_code'), ('WMS Code', 'wms_code')), (('Order ID', 'order_id'), ('Customer ID', 'customer_id')),
    (('Date', 'creation_date'),))), }

LOCATION_HEADERS = ['Zone', 'Location', 'Capacity', 'Put sequence', 'Get sequence', 'SKU Group']

SKU_HEADERS = ['WMS Code', 'SKU Description', 'Product Type', 'SKU Group', 'SKU Type(Options: FG, RM)', 'SKU Category',
               'Primary Category',
               'SKU Class', 'SKU Brand', 'Style Name', 'SKU Size', 'Size Type', 'Put Zone', 'Cost Price', 'Selling Price',
               'MRP Price', 'Sequence', 'Image Url',
               'Threshold Quantity', 'Measurment Type', 'Sale Through', 'Color', 'EAN Number',
               'Load Unit Handling(Options: Enable, Disable)', 'HSN Code', 'Sub Category', 'Hot Release',
               'Mix SKU Attribute(Options: No Mix, Mix within Group)', 'Status']

MARKET_USER_SKU_HEADERS = ['WMS Code', 'SKU Description', 'Product Type', 'SKU Group', 'SKU Type(Options: FG, RM)',
                           'SKU Category',
                           'SKU Class', 'SKU Brand', 'Style Name',
                           'Mix SKU Attribute(Options: No Mix, Mix within Group)', 'Put Zone',
                           'Price', 'MRP Price', 'Sequence', 'Image Url', 'Threshold Quantity', 'Measurment Type',
                           'Sale Through',
                           'Color', 'EAN Number', 'HSN Code', 'Status']

RESTRICTED_SKU_HEADERS = ['WMS Code', 'Put Zone', 'Threshold Quantity', 'Load Unit Handling(Options: Enable, Disable)']

SALES_RETURNS_HEADERS = ['Return ID', 'Order ID', 'SKU Code', 'Return Quantity', 'Damaged Quantity',
                         'Return Date(YYYY-MM-DD)', 'Reason']

INVENTORY_EXCEL_MAPPING = OrderedDict(( ('Seller ID', 'seller_id'), ('Receipt Date(YYYY-MM-DD)', 'receipt_date'), ('WMS SKU', 'wms_code'),
                              ('Location', 'location'), ('Quantity', 'quantity'),
                              ('Receipt Type', 'receipt_type'), ('Pallet Number', 'pallet_number'),
                              ('Batch Number', 'batch_no'), ('MRP', 'mrp'),
                              ('Manufactured Date(YYYY-MM-DD)', 'manufactured_date'),
                              ('Expiry Date(YYYY-MM-DD)', 'expiry_date')
                            ))

SKU_EXCEL = (
'wms_code', 'sku_desc', 'sku_group', 'sku_type', 'sku_category', 'sku_class', 'sku_brand', 'style_name', 'sku_size',
'zone_id',
'threshold_quantity', 'status')

PICKLIST_FIELDS = {'order_id': '', 'picklist_number': '', 'reserved_quantity': '', 'picked_quantity': 0, 'remarks': '',
                   'status': 'open'}
PICKLIST_HEADER = ('ORDER ID', 'WMS Code', 'Title', 'Zone', 'Location', 'Reserved Quantity', 'Picked Quantity')

PRINT_OUTBOUND_PICKLIST_HEADERS = (
'WMS Code', 'Title', 'Category', 'Zone', 'Location', 'Reserved Quantity', 'Picked Quantity')

PRINT_OUTBOUND_PICKLIST_HEADERS_FMCG = (
'WMS Code', 'Title', 'Category', 'Zone', 'Location', 'Batch No', 'MRP','Reserved Quantity', 'Picked Quantity')


PRINT_PICKLIST_HEADERS = (
'WMS Code', 'Title', 'Zone', 'Location', 'Reserved Quantity', 'Picked Quantity', 'Units Of Measurement')

PROCESSING_HEADER = ('WMS Code', 'Title', 'Zone', 'Location', 'Reserved Quantity', 'Picked Quantity', '')

SKU_SUPPLIER_MAPPING = OrderedDict(
    [('Supplier ID', 'supplier__id'), ('SKU CODE', 'sku__wms_code'), ('Supplier Code', 'supplier_code'),
     ('Priority', 'preference'), ('MOQ', 'moq')])

SKU_WH_MAPPING = OrderedDict(
    [('Warehouse Name', 'warehouse__username'), ('SKU CODE', 'sku__wms_code'), ('Priority', 'priority'),
     ('MOQ', 'moq'), ('Price', 'price')])

SUPPLIER_MASTER_HEADERS = OrderedDict(
    [('Supplier ID', 'id'), ('Name', 'name'), ('Address', 'address'), ('Phone Number', 'phone_number'),
     ('Email', 'email_id'), ('Status', 'status')])

STOCK_DET = ([('0', 'receipt_number'), ('1', 'receipt_date'), ('2', 'sku_id__sku_code'), ('3', 'sku_id__wms_code'),
              ('4', 'sku_id__sku_desc'), ('5', 'location_id__zone'), ('6', 'location_id__location'), ('7', 'quantity')])

ORDER_DETAIL_HEADERS = OrderedDict(
    [('Order ID', 'order_id'), ('SKU Code', 'sku_id__sku_code'), ('Title', 'title'), ('Product Quantity', 'quantity'),
     ('Shipment Date', 'shipment_date')])

OPEN_PICK_LIST_HEADERS = OrderedDict(
    [('Picklist ID', 'picklist_number'), ('Customer / Marketplace', 'picklist_number'), ('Picklist Note', 'remarks'),
     ('Reserved Quantity', 'reserved_quantity'), ('Shipment Date', 'order__shipment_date'), ('Date', 'creation_date')])

PICKED_PICK_LIST_HEADERS = OrderedDict(
    [('Picklist ID', 'picklist_number'), ('Customer / Marketplace', 'picklist_number'), ('Picklist Note', 'remarks'),
     ('Reserved Quantity', 'reserved_quantity'), ('Shipment Date', 'order__shipment_date'), ('Date', 'creation_date')])

BATCH_PICK_LIST_HEADERS = OrderedDict(
    [('Picklist ID', 'picklist_number'), ('Picklist Note', 'remarks'), ('Date', 'creation_date')])

PO_SUGGESTIONS = OrderedDict(
    [('0', 'creation_date'), ('1', 'supplier_id'), ('2', 'sku_id'), ('3', 'order_quantity'), ('4', 'price'),
     ('5', 'status')])

RECEIVE_PO_HEADERS = OrderedDict(
    [('Order ID', 'order_id'), ('Order Date', 'creation_date'), ('Supplier ID', 'open_po_id__supplier_id__id'),
     ('Supplier Name', 'open_po_id__supplier_id__name')])

STOCK_DETAIL_HEADERS = OrderedDict(
    [('SKU Code', 'sku_id__sku_code'), ('WMS Code', 'sku_id__wms_code'), ('Product Description', 'sku_id__sku_desc'),
     ('Quantity', 'quantity')])

CYCLE_COUNT_HEADERS = OrderedDict(
    [('WMS Code', 'sku_id__wms_code'), ('Zone', 'location_id__zone'), ('Location', 'location_id__location'),
     ('Quantity', 'quantity')])

BATCH_DATA_HEADERS = OrderedDict([('SKU Code', 'sku__sku_code'), ('Title', 'title'), ('Total Quantity', 'quantity')])

PUT_AWAY = OrderedDict(
    [('PO Number', 'open_po_id'), ('Order Date', 'creation_date'), ('Supplier ID', 'open_po_id__supplier_id__id'),
     ('Supplier Name', 'open_po_id__supplier_id__name')])

SKU_MASTER_HEADERS = OrderedDict(
    [('WMS SKU Code', 'wms_code'), ('EAN Number', 'ean_number'), ('Product Description', 'sku_desc'),
     ('SKU Type', 'sku_type'), ('SKU Category', 'sku_category'), ('SKU Class', 'sku_class'),
     ('Color', 'color'), ('Zone', 'zone_id'), ('Status', 'status')])

PRICING_MASTER_HEADER = OrderedDict(
    [('SKU Code', 'sku__sku_code'), ('SKU Description', 'sku__sku_desc'), ('Selling Price Type', 'price_type'),
     ('Price', 'price'), ('Discount', 'discount')])

TAX_MASTER_HEADER = OrderedDict([('Product Type', 'product_type'), ('Creation Date', 'creation_date')])

SIZE_MASTER_HEADERS = OrderedDict([('Size Name', 'size_name'), ('Sizes', 'size_value')])

QUALITY_CHECK = OrderedDict([('', 'id'), ('Purchase Order ID', 'purchase_order__order_id'),
                             ('Supplier ID', 'purchase_order__open_po__supplier_id'),
                             ('Supplier Name', 'purchase_order__open_po__supplier__name'),
                             ('Total Quantity', 'purchase_order__received_quantity')])

SHIPMENT_INFO = OrderedDict(
    [('', id), ('Customer ID', 'order__customer_id'), ('Customer Name', 'order__customer_name')])

CYCLE_COUNT_FIELDS = {'cycle': '', 'sku_id': '', 'location_id': '',
                      'quantity': '', 'seen_quantity': '',
                      'status': 1, 'creation_date': '', 'updation_date': ''}

INVENTORY_FIELDS = {'cycle_id': '', 'adjusted_location': '',
                    'adjusted_quantity': '', 'reason': 'Moved Successfully',
                    'creation_date': '', 'updation_date': ''}

BACK_ORDER_TABLE = ['WMS Code', 'Ordered Quantity', 'Stock Quantity', 'Transit Quantity', 'Procurement Quantity']

BACK_ORDER_RM_TABLE = ['Job Code', 'WMS Code', 'Ordered Quantity', 'Stock Quantity', 'Transit Quantity',
                       'Procurement Quantity']

BACK_ORDER_HEADER = ['Supplier Name', 'WMS Code', 'Title', 'Quantity', 'Price']

QC_WMS_HEADER = ['Purchase Order', 'Quantity', 'Accepted Quantity', 'Rejected Quantity']

REJECT_REASONS = ['Color Mismatch', 'Price Mismatch', 'Wrong Product', 'Package Damaged', 'Product Damaged', 'Others']

QC_SERIAL_FIELDS = {'quality_check_id': '', 'serial_number_id': '', 'status': '', 'reason': ''}

RAISE_JO_HEADERS = OrderedDict([('Product SKU Code', 'product_code'), ('Product SKU Description', 'description'),
                                ('Product SKU Quantity', 'product_quantity'),
                                ('Material SKU Code', 'material_code'), ('Material SKU Quantity', 'material_quantity'),
                                ('Measurement Type', 'measurement_type')])

JO_PRODUCT_FIELDS = {'product_quantity': 0, 'received_quantity': 0, 'job_code': 0, 'jo_reference': '', 'status': 'open',
                     'product_code_id': ''}

JO_MATERIAL_FIELDS = {'material_code_id': '', 'job_order_id': '', 'material_quantity': '', 'status': 1}

RAISE_JO_TABLE_HEADERS = ['JO Reference', 'Creation Date']

RM_CONFIRMED_HEADERS = ['Job Code ', 'Creation Date']

MATERIAL_PICKLIST_FIELDS = {'jo_material_id': '', 'status': 'open', 'reserved_quantity': 0, 'picked_quantity': 0}

MATERIAL_PICK_LOCATIONS = {'material_picklist_id': '', 'stock_id': '', 'quantity': 0, 'status': 1}

RECEIVE_JO_TABLE = [' Job Code', 'Creation Date', 'Receive Status']

RECEIVE_JO_TABLE_HEADERS = ['WMS CODE', 'JO Quantity', 'Received Quantity', 'Stage']

GRN_HEADERS = ('WMS CODE', 'Order Quantity', 'Received Quantity')

PUTAWAY_JO_TABLE_HEADERS = ['  Job Code', 'Creation Date']

PUTAWAY_HEADERS = ['WMS CODE', 'Location', 'Original Quantity', 'Putaway Quantity', '']

CUSTOMER_MASTER_HEADERS = [' Customer ID', 'Customer Name', 'Email', 'Phone Number', 'Address', 'Status']

CUSTOMER_FIELDS = ((('Customer ID *', 'id', 60), ('Customer Name *', 'name', 256)),
                   (('Email *', 'email_id', 64), ('Phone No. *', 'phone_number', 10)),
                   (('Address *', 'address'), ('Status', 'status', 11)),
                   (('Shipping Address *', 'shipping_address'),),
                   )

CUSTOMER_DATA = {'name': '', 'address': '', 'phone_number': '', 'email_id': '', 'status': 1, 'price_type': '',
                 'tax_type': '', 'lead_time': 0, 'is_distributor': 0, 'spoc_name': '', 'role': '',
                 'shipping_address': ''}

CORPORATE_DATA = {'name': '', 'address': '', 'phone_number': '', 'email_id': '', 'status': 1, 'tax_type': ''}

PRODUCTION_STAGES = {'Apparel': ['Raw Material Inspection', 'Fabric Washing', 'Finishing'],
                     'Default': ['Raw Material Inspection',
                                 'Fabric Washing', 'Finishing']}

STATUS_TRACKING_FIELDS = {'status_id': '', 'status_type': '', 'status_value': ''}

BOM_TABLE_HEADERS = ['Product SKU Code', 'Product Description']

BOM_UPLOAD_EXCEL_HEADERS = ['Product SKU Code', 'Material SKU Code', 'Material Quantity', 'Wastage Percentage',
                            'Unit of Measurement']

ADD_BOM_HEADERS = OrderedDict([('Material SKU Code', 'material_sku'), ('Material Quantity', 'material_quantity'),
                               ('Unit of Measurement', 'unit_of_measurement')])

ADD_BOM_FIELDS = {'product_sku_id': '', 'material_sku_id': '', 'material_quantity': 0, 'unit_of_measurement': ''}

UOM_FIELDS = ['Kgs', 'Units', 'Meters']

PICKLIST_SKIP_LIST = ('sortingTable_length', 'fifo-switch', 'ship_reference', 'selected')

MAIL_REPORTS = {'sku_list': ['SKU List'], 'location_wise_stock': ['Location Wise SKU'],
                'receipt_note': ['Receipt Summary'], 'dispatch_summary': ['Dispatch Summary'],'shipment_report':['Shipment Report'],
                'sku_wise': ['SKU Wise Stock']}

MAIL_REPORTS_DATA = OrderedDict((('Raise PO', 'raise_po'), ('Receive PO', 'receive_po'), ('Orders', 'order'),
                                 ('Dispatch', 'dispatch'), ('Internal Mail', 'internal_mail'),
                                 ('Raise JO', 'raise_jo'), ('Stock Transfer Note', 'stock_transfer_note'),
                                 ('Block Stock', 'enquiry'), ('Central Orders', 'central_orders'),
                                 ))

# Configurations
PICKLIST_OPTIONS = {'Scan SKU': 'scan_sku', 'Scan SKU Location': 'scan_sku_location', 'Scan Serial': 'scan_serial',
                    'Scan Label': 'scan_label',
                    'Scan None': 'scan_none'}

BARCODE_OPTIONS = {'SKU Code': 'sku_code', 'Embedded SKU Code in Serial': 'sku_serial', 'EAN Number': 'sku_ean'}

REPORTS_DATA = {'SKU List': 'sku_list', 'Location Wise SKU': 'location_wise_stock', 'Receipt Summary': 'receipt_note',
                'Dispatch Summary': 'dispatch_summary', 'SKU Wise Stock': 'sku_wise','Shipment Report':'shipment_report'}

SKU_CUSTOMER_FIELDS = (
                        (('Customer ID *', 'customer_id', 60), ('Customer Name *', 'customer_name', 256)),
                        (('SKU Code *', 'sku_code'), ('Price *', 'price'),)
                      )

CUSTOMER_SKU_DATA = {'customer_id': '', 'sku_id': '', 'price': 0, 'customer_sku_code': ''}

CUSTOMER_SKU_MAPPING_HEADERS = OrderedDict(
    [('Customer ID', 'customer__customer_id'), ('Customer Name', 'customer__name'),
     ('SKU Code', 'sku__sku_code'), ('Price', 'price')])

ADD_USER_DICT = {'username': '', 'first_name': '', 'last_name': '', 'password': '', 'email': ''}

ADD_WAREHOUSE_DICT = {'user_id': '', 'city': '', 'is_active': 1, 'country': '', u'state': '', 'pin_code': '',
                      'address': '', 'phone_number': '', 'prefix': '', 'location': '', 'warehouse_type': '',
                      'warehouse_level': 0, 'min_order_val': 0, 'level_name': '', 'zone': ''}

PICKLIST_EXCEL = OrderedDict((
                              ('Order ID', 'original_order_id'), ('Combo SKU', 'parent_sku_code'),
                              ('WMS Code', 'wms_code'), ('Title', 'title'), ('Category', 'category'),
                              ('Zone', 'zone'), ('Location', 'location'), ('Reserved Quantity', 'reserved_quantity'),
                              ('Stock Left', 'stock_left'),('Last Picked Location', 'last_picked_locs')
                            ))

PICKLIST_EXCEL_FMCG = OrderedDict((
                              ('Order ID', 'original_order_id'), ('Combo SKU', 'parent_sku_code'),
                              ('WMS Code', 'wms_code'), ('Title', 'title'), ('Category', 'category'),
                              ('Zone', 'zone'), ('Location', 'location'), ('Batch No', 'batchno'), ('MRP', 'mrp'),
                              ('Reserved Quantity', 'reserved_quantity'),
                              ('Stock Left', 'stock_left'),('Last Picked Location', 'last_picked_locs')
                            ))

# Campus Sutra
SHOPCLUES_EXCEL = {'original_order_id': 0, 'order_id': 0, 'quantity': 14, 'title': 7, 'invoice_amount': 44,
                   'address': 10,
                   'customer_name': 9, 'marketplace': 'Shopclues', 'sku_code': 48}

# SHOPCLUES_EXCEL1 = {'order_id': 0, 'quantity': 13, 'title': 6, 'invoice_amount': 45, 'address': 9, 'customer_name': 8,
#                    'marketplace': 'Shopclues', 'sku_code': 48}

VOONIK_EXCEL = {'order_id': 0, 'sku_code': 1, 'invoice_amount': 4, 'marketplace': 'Voonik'}

FLIPKART_EXCEL = {'order_id': 6, 'quantity': 14, 'title': 2, 'invoice_amount': 17, 'address': 22, 'customer_name': 21,
                  'marketplace': 'Flipkart', 'sku_code': 8}

FLIPKART_EXCEL1 = {'order_id': 6, 'quantity': 14, 'title': 2, 'invoice_amount': 16, 'address': 21, 'customer_name': 20,
                   'marketplace': 'Flipkart', 'sku_code': 8}

# Trance Home
FLIPKART_EXCEL2 = {'original_order_id': 3, 'order_id': 3, 'quantity': 17, 'title': 9, 'invoice_amount': 14,
                   'address': 21, 'customer_name': 19,
                   'marketplace': 'Flipkart', 'sku_code': 8}

# Campus Sutra
FLIPKART_EXCEL3 = {'original_order_id': 2, 'order_id': 2, 'quantity': 17, 'title': 15, 'invoice_amount': 5,
                   'address': 21, 'customer_name': 20,
                   'marketplace': 'Flipkart', 'sku_code': 14}

FLIPKART_EXCEL4 = {'original_order_id': 2, 'order_id': 2, 'quantity': 19, 'title': 17, 'invoice_amount': 7,
                   'address': 23, 'customer_name': 22,
                   'marketplace': 'Flipkart', 'sku_code': 16}

# Campus Sutra
LIMEROAD_EXCEL = {'original_order_id': 0, 'order_id': 0, 'quantity': 9, 'title': 5, 'unit_price': 8, 'address': 12,
                  'customer_name': 10,
                  'marketplace': 'Lime Road', 'sku_code': 3}

FYND_EXCEL = {'original_order_id': 1, 'order_id': 1, 'title': 4, 'unit_price': 7, 'address': 16, 'customer_name': 14,
              'marketplace': 'Fynd', 'sku_code': 9}

# PAYTM_EXCEL2 = {'order_id': 13, 'quantity': 10, 'title': 1, 'invoice_amount': 9, 'address': 22, 'customer_name': 18, 'marketplace': 'Paytm',
#                'sku_code': 3}

FLIPKART_FA_EXCEL = {'original_order_id': 1, 'order_id': 1, 'quantity': 13, 'title': 8, 'invoice_amount': 9,
                     'address': 20, 'customer_name': 29,
                     'marketplace': 'Flipkart FA', 'sku_code': 7}

SNAPDEAL_EXCEL = {'original_order_id': 3, 'order_id': 3, 'title': 1, 'invoice_amount': 13, 'customer_name': 8,
                  'marketplace': 'Snapdeal',
                  'sku_code': 4, 'shipment_date': 17}

SNAPDEAL_EXCEL1 = {'order_id': 3, 'title': 2, 'invoice_amount': 14, 'customer_name': 9, 'marketplace': 'Snapdeal',
                   'sku_code': 5,
                   'shipment_date': 8}

AMAZON_FA_EXCEL = {'title': 4, 'invoice_amount': 14, 'marketplace': 'Amazon FA', 'sku_code': 3, 'quantity': 7}

SNAPDEAL_FA_EXCEL = {'title': 4, 'invoice_amount': 6, 'marketplace': 'Snapdeal FA', 'sku_code': 3, 'quantity': 5}

EASYOPS_ORDER_EXCEL = {'order_id': 1, 'quantity': 9, 'invoice_amount': 3, 'channel_name': 5, 'sku_code': 8, 'title': 7,
                       'status': 4,
                       'split_order_id': 1}

# SKU Master Upload Templates
SKU_COMMON_MAPPING = OrderedDict((('WMS Code', 'wms_code'), ('SKU Description', 'sku_desc'),
                                  ('Product Type', 'product_type'), ('SKU Group', 'sku_group'),
                                  ('SKU Type(Options: FG, RM)', 'sku_type'), ('SKU Category', 'sku_category'),
                                  ('Primary Category', 'primary_category'), ('SKU Class', 'sku_class'),
                                  ('SKU Brand', 'sku_brand'), ('Style Name', 'style_name'),
                                  ('SKU Size', 'sku_size'), ('Size Type', 'size_type'), ('Put Zone', 'zone_id'),
                                  ('Cost Price', 'cost_price'), ('Selling Price', 'price'), ('MRP Price', 'mrp'),
                                  ('Sequence', 'sequence'), ('Image Url', 'image_url'),
                                  ('Threshold Quantity', 'threshold_quantity'),
                                  ('Measurment Type', 'measurement_type'), ('Sale Through', 'sale_through'),
                                  ('Color', 'color'), ('EAN Number', 'ean_number'),
                                  ('Load Unit Handling(Options: Enable, Disable)', 'load_unit_handle'),
                                  ('HSN Code', 'hsn_code'), ('Sub Category', 'sub_category'),
                                  ('Hot Release', 'hot_release'),
                                  ('Mix SKU Attribute(Options: No Mix, Mix within Group)', 'mix_sku'),
                                  ('Status', 'status'), ('Shelf life', 'shelf_life'),
                                  ('Enable Serial Number', 'enable_serial_based')
                                ))

SKU_DEF_EXCEL = OrderedDict((('wms_code', 0), ('sku_desc', 1), ('product_type', 2), ('sku_group', 3), ('sku_type', 4),
                             ('sku_category', 5), ('primary_category', 6), ('sku_class', 7), ('sku_brand', 8),
                             ('style_name', 9),
                             ('sku_size', 10), ('size_type', 11), ('zone_id', 12), ('cost_price', 13), ('price', 14),
                             ('mrp', 15), ('sequence', 16), ('image_url', 17), ('threshold_quantity', 18),
                             ('measurement_type', 19),
                             ('sale_through', 20), ('color', 21), ('ean_number', 22), ('load_unit_handle', 23),
                             ('hsn_code', 24),
                             ('sub_category', 25), ('hot_release', 26), ('mix_sku', 27), ('status', 28)
                             ))

MARKETPLACE_SKU_DEF_EXCEL = OrderedDict(
    (('wms_code', 0), ('sku_desc', 1), ('product_type', 2), ('sku_group', 3), ('sku_type', 4),
     ('sku_category', 5), ('sku_class', 6), ('sku_brand', 7), ('style_name', 8), ('mix_sku', 9),
     ('zone_id', 10), ('price', 11), ('mrp', 12), ('sequence', 13), ('image_url', 14),
     ('threshold_quantity', 15), ('measurement_type', 16), ('sale_through', 17), ('color', 18),
     ('ean_number', 19), ('hsn_code', 20), ('status', 21)
     ))

ITEM_MASTER_EXCEL = OrderedDict(
    (('wms_code', 1), ('sku_desc', 2), ('sku_category', 25), ('image_url', 18), ('sku_size', 14)))

SHOTANG_SKU_MASTER_EXCEL = OrderedDict(
    (('wms_code', 2), ('sku_desc', 3), ('color', 4), ('sku_brand', 7), ('sku_category', 8)))

SM_WH_SKU_MASTER_EXCEL = OrderedDict((('wms_code', 0), ('zone_id', 1), ('threshold_quantity', 2),
                                     ('load_unit_handle', 3)))

# End of SKU Master Upload templates

# Order File Upload Templates
INDIA_TIMES_EXCEL = {'order_id': 2, 'invoice_amount': 16, 'address': 8, 'customer_name': 7,
                     'marketplace': 'Indiatimes', 'sku_code': 15, 'telephone': 12}

HOMESHOP18_EXCEL = {'order_id': 0, 'invoice_amount': 10, 'address': 18, 'customer_name': 4, 'marketplace': 'HomeShop18',
                    'title': 6, 'sku_code': 8, 'quantity': 9, 'telephone': 22}

AMAZON_EXCEL = {'order_id': 1, 'address': [17, 18, 19], 'customer_name': 8, 'marketplace': 'Amazon',
                'title': 11, 'sku_code': 10, 'quantity': 12, 'telephone': 9, 'email_id': 7}

# AMAZON_EXCEL1 = {'order_id': 1, 'invoice_amount': 11, 'address': [17,18,19], 'customer_name': 16, 'marketplace': 'Amazon',
#                        'title': 8, 'sku_code': 7, 'quantity': 9, 'telephone': 6, 'email_id': 4}

ASKMEBAZZAR_EXCEL = {'order_id': 0, 'invoice_amount': 14, 'address': 27, 'customer_name': 9,
                     'marketplace': 'Ask Me Bazzar',
                     'title': 30, 'sku_code': 29, 'quantity': 12, 'telephone': 10}

FLIPKART_FA_EXCEL1 = {'order_id': 16, 'invoice_amount': 15, 'marketplace': 'Flipkart FA', 'title': 0, 'sku_code': 2,
                      'quantity': 9}

CAMPUS_SUTRA_EXCEL = {'order_id': 2, 'invoice_amount': 14, 'marketplace': 'Campus Sutra', 'sku_code': 6, 'quantity': 13,
                      'customer_name': 3,
                      'address': 5, 'telephone': 10, 'email_id': 7, 'shipment_date': 1}

# Campus Sutra
PAYTM_EXCEL = {'original_order_id': 0, 'order_id': 0, 'unit_price': 20, 'marketplace': 'Paytm', 'sku_code': 14,
               'quantity': 21, 'customer_name': 3, 'address': 7, 'telephone': 6, 'shipment_date': 23}

# Craftsvilla
CRAFTSVILLA_EXCEL = OrderedDict(
    (('order_id', 0), ('title', 12), ('sku_code', 17), ('quantity', 13), ('marketplace', 'Craftsvilla'),
     ('customer_name', 3), ('address', 7), ('telephone', 9), ('email_id', 4),
     ('amount', 21), ('amount_discount', 22), ('cgst_tax', 26), ('sgst_tax', 28), ('igst_tax', 30)
     ))

CRAFTSVILLA_AMAZON_EXCEL = OrderedDict(
    (('order_id', 0), ('title', 10), ('sku_code', 11), ('quantity', 14), ('marketplace', 'Amazon'),
     ('unit_price', 16)
     ))

# Adam clothing and Campus Sutra
MYNTRA_EXCEL = {'invoice_amount': 19, 'marketplace': 'Myntra', 'sku_code': 2, 'quantity': 10, 'title': 8,
                'original_order_id': 1,
                'order_id': 1, 'mrp': 13, 'discount': 14, 'unit_price': 12, 'cgst_amt': 16, 'sgst_amt': 18,
                'igst_amt': 15,
                'utgst_amt': 17}

# Adam clothing
JABONG_EXCEL = {'invoice_amount': 14, 'marketplace': 'Jabong', 'sku_code': 2, 'quantity': 9, 'title': 7,
                'original_order_id': 1, 'order_id': 1,
                'vat': [14, 11], 'mrp': 12, 'discount': 13, 'unit_price': 11}

# Adam clothing
UNI_COMMERCE_EXCEL = {'order_id': 12, 'title': 19, 'channel_name': 2, 'sku_code': 17, 'recreate': True}

# ---  Returns Default headers --
GENERIC_RETURN_EXCEL = OrderedDict((('sku_id', 2), ('order_id', 1), ('quantity', 3), ('damaged_quantity', 4),
                                    ('return_id', 0), ('return_date', 5), ('reason', 6)))

# ---  Shotang Returns headers --
SHOTANG_RETURN_EXCEL = OrderedDict(
    (('sku_id', 2), ('order_id', 1), ('quantity', 3), ('return_date', 4), ('seller_order_id', 0),
     ('return_type', 5), ('marketplace', 'Shotang')
     ))

# MYNTRA_RETURN_EXCEL = OrderedDict((('sku_id', [5,7]), ('quantity', 8), ('reason', 13), ('marketplace', "MYNTRA")))

MYNTRA_RETURN_EXCEL = OrderedDict((('sku_id', [5, 7]), ('quantity', 8), ('reason', 13), ('marketplace', "MYNTRA")))

UNIWEAR_RETURN_EXCEL = OrderedDict((('sku_id', 4), ('channel', 14), ('reason', 12),
                                    ('return_id', 5), ('return_date', 8)))

# Adam clothing
MYNTRA_BULK_PO_EXCEL = OrderedDict((('order_id', 0), ('original_order_id', 0), ('sku_code', 1), ('title', 3),
                                    ('marketplace', 'Myntra'), ('mrp', 7), ('quantity', 6), ('invoice_amount', [6, 12]),
                                    ('vat', {'tax': 10, 'quantity': 6, 'tax_value': 11}),
                                    ))

# Alpha Ace
ALPHA_ACE_ORDER_EXCEL = OrderedDict((('order_id', 0), ('title', 9), ('sku_code', 27), ('quantity', 12),
                                     ('marketplace', 'Alpha Ace'), ('customer_name', 25), ('telephone', 26),
                                     ('unit_price', 20), ('invoice_amount', [12, 20]), ('cgst_tax', 16),
                                     ('sgst_tax', 18)
                                     ))

UNI_COMMERCE_EXCEL1 = {'order_id': 8, 'channel_name': 2, 'sku_code': 20, 'customer_name': 9, 'email_id': 10,
                       'telephone': 11,
                       'address': [12, 13, 14], 'state': 15, 'pin_code': 16, 'invoice_amount': 19, 'recreate': True}

UNI_WARE_EXCEL = {'order_id': 12, 'channel_name': 2, 'sku_code': 1, 'quantity': 34}

UNI_WARE_EXCEL1 = {'order_id': 0, 'email_id': 5, 'telephone': 20, 'customer_name': 13, 'address': [14, 15], 'city': 16,
                   'state': 17,
                   'pin_code': 19, 'title': 33, 'channel_name': 37, 'sku_code': 31, 'invoice_amount': 42,
                   'discount': 46}

SHOTANG_ORDER_FILE_EXCEL = {'order_id': 1, 'customer_name': 6, 'customer_id': 5, 'telephone': 7, 'address': 8,
                            'sku_code': 2,
                            'invoice_amount': 16, 'sor_id': 0, 'order_date': 3, 'quantity': 4, 'order_status': 11,
                            'seller': 9,
                            'marketplace': 'Shotang', 'vat': {'tax': 14, 'quantity': 4, 'tot_tax': 15}}

CENTRAL_ORDER_EXCEL = OrderedDict((
                             ('original_order_id', 0), ('batch_number', 1), ('batch_date', 2),
                             ('branch_id', 3), ('branch_name', 4), ('loan_proposal_id', 5),
                             ('loan_proposal_code', 6), ('client_code', 7), ('client_id', 8),
                             ('customer_name', 9), ('address1', 10),
                             ('address2', 11), ('landmark', 12), ('village', 13), ('district', 14),
                             ('state', 15), ('pincode', 16), ('mobile_no', 17), ('alternative_mobile_no', 18),
                             ('sku_code', 19), ('model', 20), ('unit_price', 21),
                             ('cgst', 22), ('sgst', 23), ('igst', 24),
                             ('total_price', 25), ('location', 26)
                           ))

CENTRAL_ORDER_EXCEL_ONE_ASSIST = OrderedDict((
                            ('original_order_id', 0), ('customer_name', 1), ('address', 2),
                            ('city', 3), ('pincode', 4), ('mobile_no', 5), ('email_id', 6),
                            ('sku_code', 7)
                          ))
STOCK_TRANSFER_ORDER_EXCEL = OrderedDict((
                            ('warehouse_name', 0), ('wms_code', 1), ('quantity', 2),
                            ('price', 3)))

CENTRAL_ORDER_XLS_UPLOAD = {'interm_order_id': '', 'sku': '', 'quantity': 1,
              'unit_price': 0, 'tax': 0, 'inter_state': 0, 'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0,
              'utgst_tax': 0, 'status': 0, 'project_name': '', 'remarks': '', 'customer_id': 0,
              'customer_name': '', 'shipment_date': datetime.datetime.now()}

# End of Order File Upload Templates

# Download Excel Report Mapping
EXCEL_REPORT_MAPPING = {'dispatch_summary': 'get_dispatch_data', 'sku_list': 'get_sku_filter_data',
                        'location_wise': 'get_location_stock_data',
                        'goods_receipt': 'get_po_filter_data', 'receipt_summary': 'get_receipt_filter_data',
                        'sku_stock': 'print_sku_wise_data', 'sku_wise_purchases': 'sku_wise_purchase_data',
                        'supplier_wise': 'get_supplier_details_data', 'sales_report': 'get_sales_return_filter_data',
                        'inventory_adjust_report': 'get_adjust_filter_data',
                        'inventory_aging_report': 'get_aging_filter_data',
                        'stock_summary_report': 'get_stock_summary_data',
                        'daily_production_report': 'get_daily_production_data',
                        'order_summary_report': 'get_order_summary_data',
                        'seller_invoices_filter': 'get_seller_invoices_filter_data',
                        'open_jo_report': 'get_openjo_details',
                        'grn_inventory_addition': 'get_grn_inventory_addition_data',
                        'sales_returns_addition': 'get_returns_addition_data',
                        'seller_stock_summary_replace': 'get_seller_stock_summary_replace',
                        'rm_picklist_report': 'get_rm_picklist_data',
                        'stock_ledger_report': 'get_stock_ledger_data',
                        'get_shipment_report': 'get_shipment_report_data',
                        'get_dist_sales_report': 'get_dist_sales_report_data',
                        'get_reseller_sales_report': 'get_reseller_sales_report_data',
                        'get_zone_target_summary_report': 'get_zone_target_summary_report_data',
                        'get_zone_target_detailed_report': 'get_zone_target_detailed_report_data',
                        'get_dist_target_summary_report': 'get_dist_target_summary_report_data',
                        'get_dist_target_detailed_report': 'get_dist_target_detailed_report_data',
                        'get_reseller_target_summary_report': 'get_reseller_target_summary_report_data',
                        'get_reseller_target_detailed_report': 'get_reseller_target_detailed_report_data',
                        'get_corporate_target_report': 'get_corporate_target_report_data',
                        'get_corporate_reseller_mapping_report': 'get_corporate_reseller_mapping_report_data',
                        'get_enquiry_status_report': 'get_enquiry_status_report_data',
                        'sku_wise_goods_receipt' : 'get_sku_wise_po_filter_data',
                        'get_rtv_report': 'get_rtv_report_data',
                        'sku_wise_rtv_report': 'get_sku_wise_rtv_filter_data'
                        }
# End of Download Excel Report Mapping

SHIPMENT_STATUS = ['Dispatched', 'In Transit', 'Out for Delivery', 'Delivered']

RWO_FIELDS = {'vendor_id': '', 'job_order_id': '', 'status': 1}

COMBO_SKU_EXCEL_HEADERS = ['SKU Code', 'Combo SKU']

RWO_PURCHASE_FIELDS = {'purchase_order_id': '', 'rwo_id': ''}

VENDOR_PICKLIST_FIELDS = {'jo_material_id': '', 'status': 'open', 'reserved_quantity': 0, 'picked_quantity': 0}

STAGES_FIELDS = {'stage_name': '', 'user': ''}

SIZES_LIST = ['S', 'M', 'L', 'XL', 'XXL', 'XXXL', 'FREE SIZE']

SKU_FIELD_TYPES = [{'field_name': 'sku_category', 'field_value': 'SKU Category'},
                   {'field_name': 'sku_brand', 'field_value': 'SKU Brand'},
                   {'field_name': 'sku_group', 'field_value': 'SKU Group'}]

PERMISSION_DICT = OrderedDict((
    # Masters
    ("MASTERS_LABEL", (("SKU Master", "add_skumaster"), ("Location Master", "add_locationmaster"),
                       ("Supplier Master", "add_suppliermaster"), ("Supplier SKU Mapping", "add_skusupplier"),
                       ("Customer Master", "add_customermaster"), ("Customer SKU Mapping", "add_customersku"),
                       ("BOM Master", "add_bommaster"), ("Staff Master", "add_staffmaster"),
                       ("Vendor Master", "add_vendormaster"), ("Discount Master", "add_categorydiscount"),
                       ("Custom SKU Template", "add_productproperties"), ("Size Master", "add_sizemaster"),
                       ('Pricing Master', 'add_pricemaster'), ('Network Master', 'add_networkmaster'),
                       ('Tax Master', 'add_taxmaster'), ('T&C Master', 'add_tandcmaster'))),

    # Inbound
    ("INBOUND_LABEL", (("Raise PO", "add_openpo"), ("Confirm PO", "change_openpo"),
                       ("Receive PO", "add_purchaseorder"),
                       ("Quality Check", "add_qualitycheck"),
                       ("Putaway Confirmation", "add_polocation"), ("Sales Returns", "add_orderreturns"),
                       ("Returns Putaway", "add_returnslocation"),
                       ("RTV", "add_returntovendor"))),

    # Production
    ("PRODUCTION_LABEL", (("Raise Job order", "add_jomaterial"), ("RM Picklist", "add_materialpicklist"),
                          ("Receive Job Order", "add_joborder"), ("Job Order Putaway", "add_rmlocation"))),

    # Stock Locator
    ("STOCK_LABEL", (("Stock Detail", "add_stockdetail"), ("Vendor Stock", "add_vendorstock"),
                     ("Cycle Count", "add_cyclecount"), ("Move Inventory", "change_inventoryadjustment"),
                     ("Inventory Adjustment", "add_inventoryadjustment"), ("Stock Summary", "add_skustock"),
                     ("Warehouse Stock", "add_usergroups"), ("IMEI Tracker", "add_poimeimapping"))),

    # Outbound
    ("OUTBOUND_LABEL", (("Create Orders", "add_orderdetail"), ("View Orders", "add_picklist"),
                        ("Pull Confirmation", "add_picklistlocation"), ("Enquiry Orders", "add_enquirymaster"),
                        ("Customer Invoices", "add_sellerordersummary"), ("Manual Orders", "add_manualenquiry"),
                        )),

    # Shipment Info
    ("SHIPMENT_LABEL", (("Shipment Info", "add_shipmentinfo"))),

    # Others
    ("OTHERS_LABEL", (("Raise Stock Transfer", "add_openst"), ("Create Stock Transfer", "add_stocktransfer"))),

    # Payment
    ("PAYMENT_LABEL", (("PAYMENTS", "add_paymentsummary"),)),

    # Uploaded POs
    ("UPLOADPO_LABEL", (("uploadedPOs", "add_orderuploads"),)),

))

ORDERS_TRACK_STATUS = {0: 'Resolved', 1: "Conflict", 2: "Delete"}

# Shotang Integration Mapping Dictionaries

SELLER_ORDER_DETAIL_API_MAPPING = {'id': 'order["itemId"]', 'order_id': 'uorId', 'items': 'orders',
                            'channel': 'orders.get("channel", "Shotang")', 'order_items': 'orders["subOrders"]',
                            'sku': 'sku_item["sku"]',
                            'title': 'sku_item["name"]', 'quantity': 'sku_item["quantity"]',
                            'shipment_date': 'orders.get("orderDate", '')', 'channel_sku': 'sku_item["sku"]',
                            'unit_price': 'sku_item["unitPrice"]', 'seller_id': 'order["sellerId"]',
                            'sor_id': 'order["sorId"]', 'cgst_tax': 'sku_item.get("cgstTax", "0")',
                            'sgst_tax': 'sku_item.get("sgstTax", "0")',
                            'igst_tax': 'sku_item.get("igstTax", "0")', 'order_status': 'sku_item.get("status", "")',
                            'line_items': 'order["lineItems"]', 'customer_id': 'orders.get("retailerId", "")',
                            'customer_name': '(orders.get("retailerAddress", {})).get("name", "")',
                            'telephone': '(orders.get("retailerAddress", {})).get("phoneNo", "")',
                            'address': '(orders.get("retailerAddress", {})).get("address", "")',
                            'city': '(orders.get("retailerAddress", {})).get("city", "")',
                            'seller_item_id': 'sku_item["lineItemId"]',
                            'seller_parent_item_id': 'sku_item["parentLineItemId"]'
                            }

ORDER_DETAIL_API_MAPPING = {'order_id': 'order_id', 'items': 'orders',
                            'channel': 'orders.get("source", "")',
                            'sku': 'sku_item["sku"]',
                            'title': 'sku_item["name"]', 'quantity': 'sku_item["quantity"]',
                            'shipment_date': 'orders.get("orderDate", '')', 'channel_sku': 'sku_item["sku"]',
                            'unit_price': 'sku_item["unitPrice"]', 'seller_id': 'order["sellerId"]',
                            'sor_id': 'order["sorId"]', 'cgst_tax': 'sku_item.get("cgstTax", "0")',
                            'sgst_tax': 'sku_item.get("sgstTax", "0")',
                            'igst_tax': 'sku_item.get("igstTax", "0")', 'order_status': 'orders.get("order_status", "")',
                            'line_items': 'order["lineItems"]', 'customer_id': 'orders.get("billing_address", {}).get("customer_id", "")',
                            'customer_name': 'orders.get("billing_address", {}).get("name", "")',
                            'telephone': '(orders.get("retailerAddress", {})).get("phoneNo", "")',
                            'address': '(orders.get("retailerAddress", {})).get("address", "")',
                            'city': '(orders.get("retailerAddress", {})).get("city", "")',
                            'seller_item_id': 'sku_item["lineItemId"]',
                            'seller_parent_item_id': 'sku_item["parentLineItemId"]'
                            }


ORDER_DETAIL_INGRAM_API_MAPPING = {'order_id': 'order_increment_id', 'order_status': '(orders["order_status"]).upper()',
                                   'items': 'orders',
                                   'channel': 'orders.get("marketplace", "ingram")', 'order_items': 'orders["items"]',
                                   'sku': 'sku_item["sku"]', 'title': 'sku_item["name"]',
                                   'quantity': '(sku_item.get("qty_ordered", "0"))',
                                   'created_at': '(orders.get("created_at", ""))',
                                   'payment_method': '((orders.get("invoice_details", {})).get("payment_method", {}))',
                                   'shipment_date': '(orders.get("invoice_details", {})).get("shipment_date", "")',
                                   'channel_sku': 'sku_item["sku"]',
                                   'unit_price': 'sku_item["price"]',
                                   'total_price': 'sku_item["row_total"]',
                                   'hsn_code': 'sku_item["hs_code"]',
                                   'cgst_tax': '(sku_item.get("tax_percent", {})).get("CGST", "0")',
                                   'sgst_tax': '(sku_item.get("tax_percent", {})).get("SGST", "0")',
                                   'igst_tax': '(sku_item.get("tax_percent", {})).get("IGST", "0")',
                                   'customer_id': '(orders.get("billing_address", {})).get("customer_id", "")',
                                   'customer_name': '(orders.get("billing_address", {})).get("firstname", "")',
                                   'telephone': '(orders.get("billing_address", {})).get("telephone", "")',
                                   'address': '(orders.get("billing_address", {})).get("street", "")',
                                   'city': '(orders.get("billing_address", {})).get("city", "")',
                                   'last_name': '(orders.get("billing_address", {})).get("last_name", "")',
                                   'pin_code': '(orders.get("billing_address", {})).get("post_code", "")',
                                   'country': '(orders.get("billing_address", {})).get("country", "")',
                                   'seller_name': '((orders.get("invoice_details", {})).get("merchant", {})).get("company_name", "")',
                                   'seller_address': '((orders.get("invoice_details", {})).get("merchant", {})).get("company_address", "")',
                                   'seller_city': '((orders.get("invoice_details", {})).get("merchant", {})).get("company_city", "")',
                                   'seller_region': '((orders.get("invoice_details", {})).get("merchant", {})).get("company_region", "")',
                                   'seller_country': '((orders.get("invoice_details", {})).get("merchant", {})).get("company_country", "")',
                                   'seller_postal': '((orders.get("invoice_details", {})).get("merchant", {})).get("company_postal", "")',
                                   'seller_tax_id': '((orders.get("invoice_details", {})).get("merchant", {})).get("company_tax_id", "")',
                                   'shipping_tax': '((orders.get("invoice_details", {})).get("shipping_incl_tax", "0"))',

                                   }

SKU_MASTER_API_MAPPING = OrderedDict((('skus', 'skus'), ('sku_code', 'sku_code'), ('sku_desc', 'sku_desc'),
                                      ('sku_brand', 'sku_brand'), ('sku_category', 'sku_category_name'),
                                      ('price', 'selling_price'), ('sub_category', 'sub_category'),
                                      ('mrp', 'mrp'), ('sku_class', 'sku_class'),
                                      ('style_name', 'style_name'), ('status', 'status'), ('hsn_code', 'hsn_code'),
                                      ('ean_number', 'ean_number'), ('threshold_quantity', 'threshold_quantity'),
                                      ('color', 'color'),
                                      ('measurement_type', 'measurement_type'), ('sku_size', 'sku_size'),
                                      ('size_type', 'size_type'),
                                      ('mix_sku', 'mix_sku'), ('sku_type', 'sku_type'), ('attributes', 'sku_options'),
                                      ('child_skus', 'child_skus'), ('cgst', 'cgst'), ('sgst', 'sgst'),
                                      ('igst', 'igst'), ('cess', 'cess'), ('shelf_life', 'shelf_life'),
                                      ('image_url', 'image_url')))

CUSTOMER_MASTER_API_MAPPING = OrderedDict((('customers', 'customers'), ('customer_id', 'customer_id'), ('name', 'name'),
                                           ('address', 'address'), ('city', 'city'), ('state', 'state'),
                                           ('country', 'country'),
                                           ('pincode', 'pincode'), ('phone_number', 'phone_number'),
                                           ('email_id', 'email_id'),
                                           ('status', 'status'), ('last_name', 'last_name'),
                                           ('credit_period', 'credit_period'),
                                           ('tin_number', 'tin_number'), ('price_type', 'price_type'),
                                           ('tax_type', 'tax_type'),
                                           ('pan_number', 'pan_number')
                                           ))

SELLER_MASTER_API_MAPPING = OrderedDict((('sellers', 'sellers'), ('seller_id', 'seller_id'), ('name', 'name'),
                                         ('phone_number', 'phone_number'), ('address', 'address'),
                                         ('email_id', 'email_id'), ('tin_number', 'gstin_no'),
                                         ('vat_number', 'vat_number'), ('price_type', 'price_type'),
                                         ('margin', 'margin'), ('status', 'status')
                                         ))

# Easyops Integration Mapping Dictionaries
EASYOPS_ORDER_MAPPING = {'id': 'order["itemId"]', 'order_id': 'orderTrackingNumber',
                         'items': 'orders.get("orderItems", [])',
                         'channel': 'orders["channel"]',
                         'sku': 'sku_item["easyopsSku"]',
                         'title': 'sku_item["productTitle"]', 'quantity': 'sku_item["quantity"]',
                         'shipment_date': 'orders["orderDate"]', 'channel_sku': 'sku_item["channelSku"]',
                         'unit_price': 'sku_item["unitPrice"]', 'order_items': 'orders["orderItems"]'}

EASYOPS_SHIPPED_ORDER_MAPPING = {'id': 'order["itemId"]', 'order_id': 'orderTrackingNumber', 'items': 'orderItems',
                                 'channel': 'channel',
                                 'sku': 'order["easyopsSku"]',
                                 'title': 'order["productTitle"]', 'quantity': 'order["quantity"]',
                                 'shipment_date': 'orders["orderDate"]',
                                 'unit_price': 'order["unitPrice"]', 'order_items': 'orders["orderItems"]'}

ORDER_SUMMARY_FIELDS = {'discount': 0, 'creation_date': datetime.datetime.now(), 'issue_type': 'order', 'vat': 0,
                        'tax_value': 0,
                        'order_taken_by': '', 'sgst_tax': 0, 'cgst_tax': 0, 'igst_tax': 0, 'cess_tax': 0}

EASYOPS_STOCK_HEADERS = OrderedDict([('Product Name', 'sku_desc'), ('Sku', 'wms_code'), ('Vendor Sku', 'wms_code'),
                                     ('Stock', 'stock_count'), ('Purchase Price', 'purchase_price')])

EASYOPS_RETURN_ORDER_MAPPING = {'order_id': 'orderId', 'items': 'data', 'return_id': 'rtnId',
                                'return_date': 'returnDate', 'sku': 'order["easyopsSku"]',
                                'damaged_quantity': 'order["badQty"]', 'return_quantity': 'order["goodQty"]',
                                'return_type': 'orders["returnType"]', 'order_items': 'orders["lineItems"]',
                                'marketplace': 'orders["channel"]', 'reason': 'orders["returnReason"]'}

EASYOPS_CANCEL_ORDER_MAPPING = {'id': 'orderId', 'order_id': 'orderTrackingNumber', 'items': 'orderItems',
                                'channel': 'channel',
                                'sku': 'order["easyopsSku"]',
                                'title': 'order["productTitle"]', 'quantity': 'order["quantity"]',
                                'shipment_date': 'orders["orderDate"]',
                                'unit_price': 'order["unitPrice"]', 'order_items': 'orders["orderItems"]'}
# End of Easyops Integration Mapping Dictionaries

ORDER_DETAIL_STATES = {0: 'Picklist generated', 1: 'Newly Created', 2: 'Dispatched', 3: 'Cancelled', 4: 'Returned',
                       5: 'Delivery Reschedule Cancelled'}

SELLER_ORDER_STATES = {0: 'Seller Order Picklist generated', 1: 'Newly Created', 4: 'Returned'}

PAYMENT_MODES = ['Credit Card', 'Debit Card', 'Cash', 'NEFT', 'RTGS', 'IMPS', 'Online Transfer', 'Cash Remittance',
                 'Cheque']

ORDER_HEADERS_d = OrderedDict(
    (('Unit Price', 'unit_price'), ('Amount', 'amount'), ('Tax', 'tax'), ('Total Amount', 'total_amount'),
     ('Remarks', 'remarks'), ('Discount', 'discount'), ('Discount Percentage', 'discount_percentage'),
     ('Price Ranges', 'price_ranges')))

STYLE_DETAIL_HEADERS = OrderedDict((('SKU Code', 'wms_code'), ('SKU Description', 'sku_desc'), ('Size', 'sku_size'),
                                    ('1-Day Stock', 'physical_stock'), ('3-Day Stock', 'all_quantity')
                                    ))

RECEIVE_PO_MANDATORY_FIELDS = OrderedDict((
                      ('Buy Price', 'buy_price'), ('MRP', 'mrp'),
                      ('Weight', 'weight'), ('Batch No', 'batch_no'),
                      ('Mfg Date', 'mfg_date'), ('Exp Date', 'exp_date')
                    ))

STYLE_DETAIL_WITHOUT_STATIC_LEADTIME = OrderedDict((('SKU Code', 'wms_code'), ('SKU Description', 'sku_desc'),
                                                    ('Size', 'sku_size')))

TAX_TYPES = OrderedDict((('DEFAULT', 0), ('VAT', 5.5), ('CST', 2)))
D_TAX_TYPES = OrderedDict((('DEFAULT', 0), ('VAT', 6), ('CST', 2)))

##RETAILONE RELATED
R1_ORDER_MAPPING = {'id': 'id', 'order_id': 'order_id', 'items': 'orders.get("items", [])',
                    'channel': 'orders["channel_sku"]["channel"]["name"]', 'sku': 'sku_item["sku"]',
                    'channel_sku': 'sku_item["mp_id_value"]',
                    'title': 'sku_item["title"]', 'quantity': 'sku_item["quantity"]',
                    'shipment_date': 'order["ship_by"]',
                    'unit_price': '0', 'order_items': ''}

R1_RETURN_ORDER_MAPPING = {'order_id': 'order_id', 'items': 'items', 'return_id': 'return_id',
                           'return_date': 'return_date', 'sku': 'order["sku"]', 'return_type': 'order["return_type"]',
                           'damaged_quantity': '0', 'return_quantity': 'order["quantity"]',
                           'order_items': '', 'reason': 'order["return_reason"]',
                           'marketplace': 'order["channel_sku"]["channel"]["name"]'}

# BARCODE_FORMATS = {'adam_clothing': {'format1': ['sku_master'], 'format2': ['sku_master'], 'format3': ['sku_master']}}

BARCODE_DICT = {
    'format1': {'SKUCode': '', 'SKUDes': '', 'Color': '', 'Size': '', 'SKUPrintQty': '', 'Brand': '', 'Style': ''},
    'format2': {'SKUCode': '', 'SKUDes': '', 'Color': '', 'Size': '', 'SKUPrintQty': '', 'Brand': '', 'Product': '',
                'DesignNo': '', 'Qty': '1', 'Gender': '', 'MRP': '', 'Packed on': '', 'Manufactured By': '',
                'Marketed By': ''},
    'format3': {'SKUCode': '', 'SKUDes': '', 'Color': '', 'Size': '', 'SKUPrintQty': '', 'Brand': '', 'Product': '',
                'DesignNo': '',
                'Qty': '1', 'Gender': '', 'MRP': '', 'MFD': '', 'Manufactured By': '', 'Marketed By': ''},
    'format4': {'SKUCode': '', 'color': '', 'Size': '', 'SKUPrintQty': '',
                'Qty': '1', 'MRP': '', 'Manufactured By': '', 'Marketed By': '', 'Phone': '',
                'Vendor SKU': '', 'PO No': '', 'Email': ''},
    'Bulk Barcode': {'SKUCode': '', 'Color': '', 'SKUPrintQty': '1', 'Qty': '1',
                     'DesignNo': '', 'UOM': '', 'Product': '', 'Company': ''}
    }

BARCODE_KEYS = {'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details', 'format4': 'Details',
                'Bulk Barcode': 'Details'}

BARCODE_ADDRESS_DICT = {'adam_clothing1': 'Adam Exports 401, 4th Floor,\n Pratiek Plazza, S.V.Road,\n Goregaon West, Mumbai - 400062.\n MADE IN INDIA',
                        'scholar_clothing': 'Scholar Clothing Co. <br/> Karnataka - India', 'bcbs_retail': 'Scholar Clothing Co.',
                        'bcgs_retail': 'Scholar Clothing Co.', 'SSRVM_RETAIL': 'Scholar Clothing Co.', 'stjohns_retail': 'Scholar Clothing Co.',
                        'narayana_retail': 'Scholar Clothing Co.', 'vps_retail': 'Scholar Clothing Co.', 'christ_retail': 'Scholar Clothing Co.',
                        'sindhihebbal_retail': 'Scholar Clothing Co.', 'stjosephs_retail': 'Scholar Clothing Co.'}

PRICING_MASTER_HEADERS = ['SKU Code', 'Selling Price type', 'Min Range', 'Max Range', 'Price', 'Discount']

PRICE_DEF_EXCEL = OrderedDict((('sku_id', 0), ('price_type', 1),
                               ('min_unit_range', 2), ('max_unit_range', 3),
                               ('price', 4), ('discount', 5)))

PRICE_MASTER_DATA = {'sku_id': '', 'price_type': '', 'price': 0, 'discount': 0}

NETWORK_MASTER_HEADERS = ['Destination Location Code', 'Source Location Code', 'Lead Time',
                          'Sku Stage', 'Priority', 'Price Type', 'Charge Remarks']
NETWORK_MASTER_HEADER = OrderedDict([('Destination Location Code', 'dest_location_code'),
                                     ('Source Location Code', 'source_location_code'),
                                     ('Lead Time', 'lead_time'), ('Sku Stage', 'sku_stage'),
                                     ('Priority', 'priority')])

NETWORK_DEF_EXCEL = OrderedDict((('dest_location_code', 0), ('source_location_code', 1),
                                 ('lead_time', 2), ('sku_stage', 3), ('priority', 4),
                                 ('price_type', 5), ('charge_remarks', 6)))

NETWORK_MASTER_DATA = {'dest_location_code': '', 'source_location_code': '',
                       'lead_time': '', 'sku_stage': '', 'priority': '',
                       'price_type': '', 'charge_remarks': ''}

SELLER_DATA = {'name': '', 'address': '', 'phone_number': '',
               'email_id': '', 'status': 1, 'price_type': '', 'margin': 0}

USER_SKU_EXCEL = {'warehouse_user': SKU_HEADERS, 'marketplace_user': SKU_HEADERS,
                  'customer': SKU_HEADERS, 'WH': RESTRICTED_SKU_HEADERS, 'DIST': RESTRICTED_SKU_HEADERS}

USER_SKU_EXCEL_MAPPING = {'warehouse_user': SKU_DEF_EXCEL, 'marketplace_user': SKU_DEF_EXCEL,
                          'customer': SKU_DEF_EXCEL}

MIX_SKU_MAPPING = {'no mix': 'no_mix', 'mix within group': 'mix_group'}

RETURNS_TYPE_MAPPING = {'return to origin(rto)': 'rto', 'customer initiated return': 'customer_return'}

# Myntra Invoice Address based on username
MYNTRA_BANGALORE_ADDRESS = 'Myntra Jabong India Pvt Ltd \n Survey Numbers 231, 232 and 233, Soukya Road,\n Samethanahalli Village,\n\
                            Anugondanahalli Hobli, Hoskote Taluk,\n Bangalore;-560087 Karnataka\n GSTIN: 29AAACQ3774A2ZI'

MYNTRA_JABONG_ADDRESS = 'Jabong Marketplace\n DTDC Facility Premise No. 79/2,79/1A & 78/6 Dasanpura Village,\nDasanpura Hobli, Bangalore,\
                         North Taluk,Bangalore,Karnataka,562162\n GSTIN: 29AAACQ3774A2ZI'

MYNTRA_MUMBAI_ADDRESS = 'Myntra jabong India Pvt Ltd.\nKsquare Industrial Park, Warehouse 4\n\
                         Before Padgha Toll naka Nashik-Mumbai Highway \nNear Pushkar Mela Hotel Rahul Narkhede,\n\
                         Padgha Bhiwandi - 421101, Maharashtra\n\
                         TIN:27461499703'
MYNTRA_BULK_ADDRESS = 'MYNTRA DESIGNS PVT LTD\nKsquare Industrial Park, Warehouse 4\n\
                         Before Padgha Toll naka Nashik-Mumbai Highway \nNear Pushkar Mela Hotel Rahul Narkhede,\n\
                         Padgha-Bhiwandi\nTin# 27590747736'

JABONG_ADDRESS = 'Myntra jabong India Pvt Ltd.\nKsquare Industrial Park,\
                         Before Padgha Toll naka Nashik-Mumbai Highway, \nNear Pushkar Mela Hotel Rahul Narkhede,\n\
                         Padgha Bhiwandi - 421101, Maharashtra\n\
                         TIN:27461499703'

USER_CHANNEL_ADDRESS = {'campus_sutra:myntra': MYNTRA_BANGALORE_ADDRESS, 'adam_clothing:myntra': MYNTRA_MUMBAI_ADDRESS,
                        'adam_clothing1:myntra': MYNTRA_MUMBAI_ADDRESS,
                        'adam_clothing1:myntra:bulk': MYNTRA_BULK_ADDRESS,
                        'adam_clothing1:jabong': JABONG_ADDRESS, 'campus_sutra:jabong': MYNTRA_JABONG_ADDRESS
                        }

MYNTRA_BULK_ADDRESS = 'MYNTRA DESIGNS PVT LTD\nKsquare Industrial Park, Warehouse 4\n\
                         Before Padgha Toll naka Nashik-Mumbai Highway \nNear Pushkar Mela Hotel Rahul Narkhede,\n\
                         Padgha-Bhiwandi\nTin# 27590747736'

# End of Myntra Invoice Address based on username

SELLER_ORDER_FIELDS = {'sor_id': '', 'quantity': 0, 'order_status': '', 'order_id': '', 'seller_id': '', 'status': 1,
                       'invoice_no': ''}

SELLER_MARGIN_DICT = {'seller_id': '', 'sku_id': '', 'margin': 0}

RECEIVE_OPTIONS = OrderedDict((('One step Receipt + Qc', 'receipt-qc'), ('Two step Receiving', '2-step-receive')))

PERMISSION_IGNORE_LIST = ['session', 'webhookdata', 'swxmapping', 'userprofile', 'useraccesstokens', 'contenttype',
                          'user',
                          'permission', 'group', 'logentry', 'corsmodel']

# Customer Invoices page headers based on user type
MP_CUSTOMER_INVOICE_HEADERS = ['UOR ID', 'SOR ID', 'Seller ID', 'Customer Name', 'Order Quantity', 'Picked Quantity',
                               'Total Amount', 'Order Date&Time',
                               'Invoice Number']

WH_CUSTOMER_INVOICE_HEADERS = ['Order ID', 'Customer Name', 'Order Quantity', 'Picked Quantity', 'Order Date&Time',
                               'Total Amount']
WH_CUSTOMER_INVOICE_HEADERS_TAB = ['Customer Name', 'Order Quantity', 'Picked Quantity', 'Order Date&Time', 'Total Amount']

STOCK_TRANSFER_INVOICE_HEADERS = ['Stock Transfer ID', 'Warehouse Name', 'Picked Quantity', 'Stock Transfer Date&Time', 'Total Amount']

DIST_CUSTOMER_INVOICE_HEADERS = ['Gen Order Id', 'Order Ids', 'Customer Name', 'Order Quantity', 'Picked Quantity',
                                 'Order Date&Time']

# End of Customer Invoices page headers based on user type

# Supplier Invoices page headers based on user type

WH_SUPPLIER_INVOICE_HEADERS = ['Supplier Name', 'PO Quantity', 'Received Quantity', 'Total Amount']
WH_SUPPLIER_PO_CHALLAN_HEADERS = ['GRN No', 'Supplier Name', 'PO Quantity', 'Received Quantity',
                                  'Order Date', 'Total Amount']

DIST_SUPPLIER_INVOICE_HEADERS = ['Supplier Name', 'PO Quantity', 'Received Quantity', 'Total Amount']

# End of Supplier Invoices page headers based on user type


SUPPLIER_EXCEL_FIELDS = OrderedDict((('id', 0), ('name', 1), ('address', 2), ('email_id', 3), ('phone_number', 4),
                                     ('tin_number', 5), ('pan_number', 6), ('pincode', 7), ('city', 8), ('state', 9),
                                     ('country', 10), ('days_to_supply', 11), ('fulfillment_amt', 12),
                                     ('credibility', 13), ('tax_type', 14), ('po_exp_duration', 15),
                                     ('owner_name', 16), ('owner_number', 17), ('owner_email_id', 18),
                                     ('spoc_name', 19), ('spoc_number', 20), ('spoc_email_id', 21),
                                     ('lead_time', 22), ('credit_period', 23), ('bank_name', 24),
                                     ('ifsc_code', 25), ('branch_name', 26), ('account_number', 27),
                                     ('account_holder_name', 28),
                                     ))
STATUS_DICT = {1: True, 0: False}

PO_RECEIPT_TYPES = ['Purchase Order', 'Buy & Sell', 'Hosted Warehouse']

PO_ORDER_TYPES = {'SR': 'Self Receipt', 'VR': 'Vendor Receipt', 'HW': 'Hosted Warehouse', 'BS': 'Buy & Sell',
                  'SP': 'Sampling'}

LOAD_UNIT_HANDLE_DICT = {'enable': 'pallet', 'disable': 'unit'}

MIX_SKU_ATTRIBUTES = {'no_mix': 'No Mix', 'mix_group': 'Mix within Group'}

TAX_TYPE_ATTRIBUTES = {'inter_state': 'Inter State', 'intra_state': 'Intra State'}

TAX_VALUES = [{'tax_name': 'Inter State', 'tax_value': 'inter_state'},
              {'tax_name': 'Intra State', 'tax_value': 'intra_state'}]

SUMMARY_INTER_STATE_STATUS = {0: 'intra_state', 1: 'inter_state', '2': 'default'}

# ORDER LABEL MAPPING EXCEL (Campus Sutra)

ORDER_LABEL_EXCEL_HEADERS = ['Order ID', 'SKU Code', 'Label']

MYNTRA_LABEL_EXCEL_MAPPING = OrderedDict((('sku_code', 2), ('order_id', 0), ('label', 1), ('vendor_sku', 4),
                                          ('title', 3), ('size', 5), ('color', 6), ('mrp', 7)))

MYNTRA_LABEL_EXCEL_MAPPING1 = OrderedDict((('sku_code', 2), ('order_id', 0), ('label', 1), ('vendor_sku', 4),
                                           ('title', 3), ('size', 5), ('color', 6), ('mrp', 8)))

ORDER_LABEL_EXCEL_MAPPING = OrderedDict((('sku_code', 1), ('order_id', 0), ('label', 2)))

ORDER_SERIAL_EXCEL_HEADERS = ['Seller ID', 'Customer ID', 'Uor ID', 'PO Number', 'SKU Code', 'Quantity', 'Unit Price',
                              'CGST(%)',
                              'SGST(%)', 'IGST(%)', 'Order Type(Options: Normal, Transit)']

ORDER_SERIAL_EXCEL_MAPPING = OrderedDict(
    (('order_id', 2), ('seller_id', 0), ('customer_id', 1), ('sku_code', 4), ('po_number', 3),
     ('quantity', 5), ('unit_price', 6), ('cgst_tax', 7), ('sgst_tax', 8), ('igst_tax', 9),
     ('order_type', 10)))

PO_SERIAL_EXCEL_HEADERS = ['Supplier ID', 'SKU Code', 'Location', 'Unit Price', 'Serial Number']

PO_SERIAL_EXCEL_MAPPING = OrderedDict((('supplier_id', 0), ('sku_code', 1), ('location', 2), ('unit_price', 3),
                                       ('imei_number', 4)))

TARGET_MASTER_HEADERS = ['Distributor Code', 'Reseller Code', 'Corporate Name', 'Target Amount', 'Target Duration (Days)']
TARGET_MASTER_HEADER = OrderedDict([('Distributor Code', 'distributor_id'), ('Reseller Code', 'reseller_id'),
                                    ('Corporate Name', 'corporate_name'), ('Target Amount', 'target_amt'),
                                    ('Target Duration (Days)', 'target_duration')])

TARGET_DEF_EXCEL = OrderedDict((('distributor_id', 0), ('reseller_id', 1), ('corporate_name', 2),
                                ('target_amt', 3), ('target_duration', 4)))

TARGET_MASTER_DATA = {'distributor_id': '', 'reseller_id':'', 'corporate_name': '',
                      'target_amt': '', 'target_duration': ''}

JOB_ORDER_EXCEL_HEADERS = ['Product SKU Code', 'Product SKU Quantity']

JOB_ORDER_EXCEL_MAPPING = OrderedDict((('product_code', 0), ('product_quantity', 1)))

ORDER_ID_AWB_MAP_EXCEL_HEADERS = ['Order ID', 'AWB No', 'Courier Name', 'Marketplace']

ORDER_ID_AWB_EXCEL_MAPPING = OrderedDict((('order_id', 0), ('awb_no', 1), ('courier_name', 2), ('marketplace', 3)))

# Company logo names
COMPANY_LOGO_PATHS = {'TranceHomeLinen': 'trans_logo.jpg', 'Subhas_Publishing': 'book_publications.png',
                      'sm_admin': 'sm-brand.jpg', 'corp_attire': 'corp_attire.jpg',
                      'aidin_technologies': 'aidin_tech.jpg', 'nutricane': 'nutricane.jpg'}

TOP_COMPANY_LOGO_PATHS = {'Konda_foundation': 'dr_reddy_logo.png'}

ISO_COMPANY_LOGO_PATHS = {'aidin_technologies': 'iso_aidin_tech.jpg'}

# Configurtions Mapping
REMAINDER_MAIL_ALERTS = OrderedDict((('po_remainder', 'PO Remainder'),))

CONFIG_SWITCHES_DICT = {'use_imei': 'use_imei', 'tally_config': 'tally_config', 'show_mrp': 'show_mrp',
                        'stock_display_warehouse': 'stock_display_warehouse', 'seller_margin': 'seller_margin',
                        'hsn_summary': 'hsn_summary',
                        'send_message': 'send_message', 'order_management': 'order_manage', 'back_order': 'back_order',
                        'display_customer_sku': 'display_customer_sku', 'pallet_switch': 'pallet_switch',
                        'receive_process': 'receive_process',
                        'no_stock_switch': 'no_stock_switch', 'show_disc_invoice': 'show_disc_invoice',
                        'production_switch': 'production_switch', 'sku_sync': 'sku_sync',
                        'display_remarks_mail': 'display_remarks_mail',
                        'stock_sync': 'stock_sync', 'float_switch': 'float_switch',
                        'automate_invoice': 'automate_invoice',
                        'pos_switch': 'pos_switch', 'create_seller_order': 'create_seller_order',
                        'marketplace_model': 'marketplace_model', 'decimal_limit': 'decimal_limit',
                        'batch_switch': 'batch_switch',
                        'view_order_status': 'view_order_status', 'label_generation': 'label_generation',
                        'grn_scan_option': 'grn_scan_option',
                        'show_imei_invoice': 'show_imei_invoice', 'style_headers': 'style_headers',
                        'picklist_sort_by': 'picklist_sort_by',
                        'barcode_generate_opt': 'barcode_generate_opt', 'online_percentage': 'online_percentage',
                        'mail_alerts': 'mail_alerts',
                        'detailed_invoice': 'detailed_invoice', 'invoice_titles': 'invoice_titles',
                        'show_image': 'show_image',
                        'auto_generate_picklist': 'auto_generate_picklist', 'auto_po_switch': 'auto_po_switch',
                        'fifo_switch': 'fifo_switch',
                        'internal_mails': 'Internal Emails', 'increment_invoice': 'increment_invoice',
                        'create_shipment_type': 'create_shipment_type',
                        'auto_allocate_stock': 'auto_allocate_stock', 'priceband_sync': 'priceband_sync',
                        'auto_confirm_po': 'auto_confirm_po', 'generic_wh_level': 'generic_wh_level',
                        'create_order_po': 'create_order_po', 'calculate_customer_price': 'calculate_customer_price',
                        'shipment_sku_scan': 'shipment_sku_scan', 'disable_brands_view':'disable_brands_view',
                        'sellable_segregation': 'sellable_segregation', 'display_styles_price': 'display_styles_price',
                        'display_sku_cust_mapping': 'display_sku_cust_mapping', 'disable_categories_view': 'disable_categories_view',
                        'is_portal_lite': 'is_portal_lite',
                        'show_purchase_history':'show_purchase_history', 'auto_raise_stock_transfer': 'auto_raise_stock_transfer',
                        'inbound_supplier_invoice': 'inbound_supplier_invoice', 'customer_dc': 'customer_dc',
                        'central_order_mgmt': 'central_order_mgmt',
                        'invoice_based_payment_tracker': 'invoice_based_payment_tracker',
                        'inbound_supplier_invoice': 'inbound_supplier_invoice', 'customer_dc': 'customer_dc',
                        'receive_po_invoice_check': 'receive_po_invoice_check', 'mark_as_delivered': 'mark_as_delivered',
                        'order_exceed_stock': 'order_exceed_stock',
                        }

CONFIG_INPUT_DICT = {'email': 'email', 'report_freq': 'report_frequency',
                     'scan_picklist_option': 'scan_picklist_option',
                     'data_range': 'report_data_range', 'imei_limit': 'imei_limit',
                     'invoice_remarks': 'invoice_remarks',
                     'invoice_marketplaces': 'invoice_marketplaces', 'serial_limit': 'serial_limit',
                     'extra_view_order_status': 'extra_view_order_status',
                     'invoice_types': 'invoice_types',
                     'mode_of_transport': 'mode_of_transport',
                     'shelf_life_ratio': 'shelf_life_ratio',
                     'auto_expire_enq_limit': 'auto_expire_enq_limit',
                     'sales_return_reasons': 'sales_return_reasons',
                     }

CONFIG_DEF_DICT = {'receive_options': dict(RECEIVE_OPTIONS),
                   'mail_options': MAIL_REPORTS_DATA,
                   'mail_reports': MAIL_REPORTS, 'style_detail_headers': STYLE_DETAIL_HEADERS,
                   'picklist_options': PICKLIST_OPTIONS,
                   'order_headers': ORDER_HEADERS_d, 'barcode_generate_options': BARCODE_OPTIONS,
                   'rem_mail_alerts': REMAINDER_MAIL_ALERTS,
                   'receive_po_mandatory_fields': RECEIVE_PO_MANDATORY_FIELDS
                   }

MARKETPLACE_SERIAL_EXCEL_HEADERS = ['Order Reference', 'Marketplace', 'Serial Number']

MARKETPLACE_SERIAL_EXCEL_MAPPING = OrderedDict((('order_reference', 0), ('marketplace', 1), ('serial_number', 2)))

SELLER_TRANSFER_MAPPING = OrderedDict((('SKU Code', 'wms_code'), ('Source Seller ID', 'source_seller'),
                                       ('Source Location', 'source_location'),
                                       ('Destination Seller ID', 'dest_seller'),
                                       ('Destination Location', 'dest_location'), ('MRP', 'mrp'),
                                       ('Quantity', 'quantity'),
                                    ))

CENTRAL_ORDER_MAPPING = OrderedDict((
                                      ('Central Order ID', 'original_order_id'), ('Batch Number', 'batch_number'),
                                      ('Batch Date', 'batch_date'), ('Branch ID', 'branch_id'),
                                      ('Branch Name', 'branch_name'), ('Loan Proposal ID', 'loan_proposal_id'),
                                      ('Loan Proposal Code', 'loan_proposal_code'), ('Client Code', 'client_code'),
                                      ('Client ID', 'client_id'), ('Customer Name', 'customer_name'),
                                      ('Address1', 'address1'), ('Address2', 'address2'),
                                      ('Landmark', 'landmark'), ('Village', 'village'),
                                      ('District', 'district'), ('State1', 'state'),
                                      ('Pincode', 'pincode'), ('Mobile Number', 'mobile_no'),
                                      ('Alternative Mobile Number', 'alternative_mobile_no'), ('SKU Code', 'sku_code'),
                                      ('Model', 'model'), ('Unit Price', 'unit_price'),
                                      ('CGST', 'cgst'), ('SGST', 'sgst'),
                                      ('IGST', 'igst'), ('Total Price', 'total_price'),
                                      ('Location', 'location')
                                   ))
STOCK_TRANSFER_ORDER_MAPPING = OrderedDict((
                                      ('Warehouse Name', 'warehouse_name'), ('WMS Code', 'wms_code'),
                                      ('Quantity', 'quantity'), ('Price', 'price')
                                   ))

CENTRAL_ORDER_ONE_ASSIST_MAPPING = OrderedDict((
                                      ('Courtesy SR Number', 'original_order_id'), ('Customer handset Model', 'sku_code'),
                                      ('Customer Name', 'customer_name'), ('Address', 'address'),
                                      ('City', 'city'), ('Pincode', 'pincode'),
                                      ('Customer primary contact', 'mobile_no'), ('Customer emailId', 'email_id')
                                  ))

#PICKLIST_EXCLUDE_ZONES = ['DAMAGED_ZONE', 'QC_ZONE', 'Non Sellable Zone']

def fn_timer(function):
    @wraps(function)
    def function_timer(*args, **kwargs):
        t0 = time.time()
        result = function(*args, **kwargs)
        t1 = time.time()
        print ('Time taken to run %s: %s seconds' %
               (function.func_name, str(t1 - t0))
               )
        return result

    return function_timer


def create_table_data(headers, data):
    table_data = '<table class="table"><tbody><tr class="active">'
    for header in headers:
        table_data += "<th>%s</th>" % header
    table_data += "</tr>"

    for zone, location in data.iteritems():
        for key, value in location.iteritems():
            table_data += "<tr>"
            table_data += "<td>%s</td>" % zone
            table_data += "<td>%s</td>" % key
            table_data += "<td>%s</td>" % value[0]
            table_data += "<td>%s</td>" % value[1]
            table_data += "</tr>"
    table_data += "</tbody></table>"

    return table_data


def create_reports_table(headers, data):
    table_data = '<table class="table"><tbody><tr class="active">'
    if 'Invoice Amount' in headers:  # For Order Summary Report
        table_data = '<table class="table"><tbody style="font-size:8px"><tr class="active">'

    for header in headers:
        table_data += "<th style='width:20%;word-wrap: break-word;'>" + str(header) + "</th>"
    table_data += "</tr>"

    for item in data:
        table_data += "<tr>"
        if isinstance(item, dict):
            item = item.values()

        for dat in item:
            table_data += "<td style='text-align:center;width:20%;word-wrap: break-word;'>" + str(dat) + "</td>"
        table_data += "</tr>"
    table_data += "</tbody></table>"

    return table_data


def create_po_reports_table(headers, data, user_profile, supplier):
    order_date = (str(datetime.datetime.now()).split(' ')[0]).split('-')
    order_date.reverse()
    table_data = "<center>" + user_profile.company_name + "</center>"
    table_data += "<center>" + user_profile.user.username + "</center>"
    table_data += "<center>" + user_profile.location + "</center>"
    table_data += "<table style='padding-bottom: 10px;text-align:right;'><tr><th>Pending Purchase Orders till date:</th><th>" + "-".join(
        order_date) + "</th></tr>"
    table_data += "<tr><th>Supplier Name:</th><th>" + supplier + "</th></tr></table>"
    table_data += '<table class="table"><tbody><tr class="active">'
    for header in headers:
        table_data += "<th>%s</th>" % header
    table_data += "</tr>"

    for item in data:
        table_data += "<tr>"
        if isinstance(item, dict):
            item = item.values()
        for dat in item:
            table_data += "<td style='text-align:center;'>%s</td>" % dat
        table_data += "</tr>"
    table_data += "</tbody></table>"

    return table_data


def create_mail_table(headers, data):
    table_data = '<table style="border: 1px solid black;border-collapse: collapse;"><tbody><tr>'
    for header in headers:
        table_data += '<th style="border: 1px solid black;">%s</th>' % header
    table_data += '</tr>'

    for item in data:
        table_data += "<tr>"
        for dat in item:
            table_data += "<td style='border: 1px solid black;'>%s</td>" % dat
        table_data += "</tr>"
    table_data += "</tbody></table>"

    return table_data


class BigAutoField(models.fields.AutoField):
    def db_type(self, connection):
        if 'mysql' in connection.__class__.__module__:
            return 'bigint AUTO_INCREMENT'
        return super(BigAutoField, self).db_type(connection)


def get_sku_filter_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master
    temp_data = copy.deepcopy(AJAX_DATA)
    results_data = []
    search_parameters = {}

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    cmp_data = ('sku_code', 'wms_code', 'sku_category', 'sku_type', 'sku_class')
    for data in cmp_data:
        if data in search_params:
            search_parameters['%s__%s' % (data, 'iexact')] = search_params[data]

    search_parameters['user'] = user.id
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    sku_master = sku_master.filter(**search_parameters)

    temp_data['recordsTotal'] = len(sku_master)
    temp_data['recordsFiltered'] = len(sku_master)

    if stop_index:
        sku_master = sku_master[start_index:stop_index]

    zone = ''
    for data in sku_master:
        if data.zone:
            zone = data.zone.zone

        temp_data['aaData'].append(
            OrderedDict((('SKU Code', data.sku_code), ('WMS Code', data.wms_code), ('SKU Group', data.sku_group),
                         ('SKU Type', data.sku_type), ('SKU Category', data.sku_category),
                         ('SKU Class', data.sku_class),
                         ('Put Zone', zone), ('Threshold Quantity', data.threshold_quantity))))

    return temp_data


def get_location_stock_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    results_data = copy.deepcopy(AJAX_DATA)
    total_quantity = 0
    search_parameters = {}
    search_mapping = {'sku_code': 'sku__sku_code__iexact', 'sku_category': 'sku__sku_category__iexact',
                      'sku_type': 'sku__sku_type__iexact', 'sku_class': 'sku__sku_class__iexact',
                      'zone': 'location__zone__zone__iexact',
                      'location': 'location__location__iexact', 'wms_code': 'sku__wms_code', 'ean': 'sku__ean_number__iexact'}
    results_data['draw'] = search_params.get('draw', 1)
    for key, value in search_mapping.iteritems():
        if key in search_params:
            search_parameters[value] = search_params[key]
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    stock_detail = []
    search_parameters['quantity__gt'] = 0
    search_parameters['sku__user'] = user.id
    search_parameters['sku_id__in'] = sku_master_ids
    distinct_list = ['sku__wms_code', 'sku__sku_desc', 'sku__sku_category', 'sku__sku_brand']
    lis = ['location__zone__zone', 'location__location', 'sku__ean_number', 'sku__wms_code', 'sku__sku_desc',
           'tsum', 'tsum', 'tsum']
    order_term = search_params.get('order_term', 0)
    col_num = search_params.get('order_index', 0)
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_parameters:
        stock_detail = StockDetail.objects.exclude(receipt_number=0).filter(**search_parameters)
        total_quantity = stock_detail.aggregate(Sum('quantity'))['quantity__sum']
    if order_term:
        stock_detail = stock_detail.order_by(order_data)
    #stock_detail = stock_detail.annotate(grouped_val=Concat('sku__sku_code', Value('<<>>'),
    #                                                        'location__location',output_field=CharField()))
    stock_detail = OrderedDict(stock_detail.annotate(grouped_val=Concat('sku__sku_code', Value('<<>>'),
                                                                 'location__location',output_field=CharField())).\
                                    values_list('grouped_val').distinct().annotate(tsum=Sum('quantity')))
    results_data['recordsTotal'] = len(stock_detail)
    results_data['recordsFiltered'] = results_data['recordsTotal']
    stock_detail_keys = stock_detail.keys()
    if stop_index:
        stock_detail_keys = stock_detail_keys[start_index:stop_index]
    picklist_reserved = dict(PicklistLocation.objects.filter(status=1, stock__sku__user=user.id).\
                             annotate(grouped_val=Concat('stock__sku__wms_code', Value('<<>>'),
                                                         'stock__location__location',output_field=CharField())).\
                             values_list('grouped_val').distinct().annotate(reserved=Sum('reserved')))
    raw_reserved = dict(RMLocation.objects.filter(status=1, stock__sku__user=user.id).\
                        annotate(grouped_val=Concat('material_picklist__jo_material__material_code__wms_code',
                                                    Value('<<>>'), 'stock__location__location',
                                                    output_field=CharField())).values_list('grouped_val').distinct().\
                        annotate(rm_reserved=Sum('reserved')))
    for stock_detail_key in stock_detail_keys:
        total_stock_value = 0
        reserved = 0
        total = stock_detail[stock_detail_key]
        sku_code, location = stock_detail_key.split('<<>>')
        sku_master = SKUMaster.objects.get(sku_code=sku_code, user=user.id)
        location_master = LocationMaster.objects.get(location=location, zone__user=user.id)
        if stock_detail_key in picklist_reserved.keys():
            reserved += float(picklist_reserved[stock_detail_key])
        if stock_detail_key in raw_reserved.keys():
            reserved += float(raw_reserved[stock_detail_key])
        quantity = total - reserved
        if quantity < 0:
            quantity = 0
        total = reserved + quantity
        ean_num = sku_master.ean_number
        if not ean_num:
            ean_num = ''
        results_data['aaData'].append(OrderedDict((('SKU Code', sku_master.sku_code), ('WMS Code', sku_master.wms_code),
                                                   ('Product Description', sku_master.sku_desc),
                                                   ('Zone', location_master.zone.zone),
                                                   ('Location', location_master.location), ('Total Quantity', total),
                                                   ('Available Quantity', quantity), ('Reserved Quantity', reserved),
                                                   ('EAN', str(ean_num)))))
    return results_data, total_quantity


def get_receipt_filter_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master, get_misc_value, get_local_date
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    search_parameters = {}
    use_imei = get_misc_value('use_imei', user.id)
    query_prefix = ''
    lis = ['open_po__supplier__name', 'order_id', 'open_po__sku__wms_code', 'open_po__sku__sku_desc',
           'received_quantity',
           'updation_date', 'reason']
    model_obj = PurchaseOrder
    if use_imei == 'true':
        lis = ['purchase_order__open_po__supplier__name', 'purchase_order__order_id',
               'purchase_order__open_po__sku__wms_code',
               'purchase_order__open_po__sku__sku_desc', 'imei_number', 'creation_date', 'purchase_order__reason']
        query_prefix = 'purchase_order__'
        model_obj = POIMEIMapping
    temp_data = copy.deepcopy(AJAX_DATA)
    temp_data['draw'] = search_params.get('draw')

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    if 'from_date' in search_params:
        search_parameters[query_prefix + 'creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_parameters[query_prefix + 'creation_date__lt'] = search_params['to_date']

    if 'supplier' in search_params:
        search_parameters[query_prefix + 'open_po__supplier__id__iexact'] = search_params['supplier']
    if 'wms_code' in search_params:
        search_parameters[query_prefix + 'open_po__sku__wms_code__iexact'] = search_params['wms_code']
    if 'sku_code' in search_params:
        search_parameters[query_prefix + 'open_po__sku__sku_code__iexact'] = search_params['sku_code']
    if 'order_id' in search_params:
        temp = re.findall('\d+', search_params['order_id'])
        if temp:
            search_parameters[query_prefix + 'order_id'] = temp[-1]
    if 'imei_number' in search_params:
        search_parameters['imei_number'] = search_params['imei_number']

    purchase_order = []
    search_parameters[query_prefix + 'open_po__sku__user'] = user.id
    search_parameters[query_prefix + 'status__in'] = ['grn-generated', 'location-assigned', 'confirmed-putaway']
    search_parameters[query_prefix + 'open_po__sku_id__in'] = sku_master_ids

    purchase_order = model_obj.objects.filter(**search_parameters)
    if search_params.get('order_term'):
        order_data = lis[search_params['order_index']]
        if search_params['order_term'] == 'desc':
            order_data = "-%s" % order_data

        purchase_order = purchase_order.order_by(order_data)

    temp_data['recordsTotal'] = purchase_order.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    if stop_index:
        purchase_order = purchase_order[start_index:stop_index]
    for data in purchase_order:
        serial_number = ''
        received_date = get_local_date(user, data.updation_date)
        if use_imei == 'true':
            serial_number = data.imei_number
            data = data.purchase_order
            received_date = get_local_date(user, data.creation_date)
        reason = ''
        if data.reason:
            reason = data.reason
        po_reference = '%s%s_%s' % (data.prefix, str(data.creation_date).split(' ')[0].replace('-', ''), data.order_id)
        temp_data['aaData'].append(OrderedDict((('PO Reference', po_reference), ('WMS Code', data.open_po.sku.wms_code),
                                                ('Description', data.open_po.sku.sku_desc),
                                                ('Supplier',
                                                 '%s (%s)' % (data.open_po.supplier.name, data.open_po.supplier_id)),
                                                ('Receipt Number', data.open_po_id),
                                                ('Received Quantity', data.received_quantity),
                                                ('Serial Number', serial_number), ('Received Date', received_date),
                                                ('Closing Reason', reason))))
    return temp_data


def get_dispatch_data(search_params, user, sub_user, serial_view=False, customer_view=False):
    from miebach_admin.models import *
    from miebach_admin.views import *
    from rest_api.views.common import get_sku_master, get_order_detail_objs
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    search_parameters = {}
    if customer_view:
        lis = ['order__customer_id', 'order__customer_name', 'order__sku__wms_code', 'order__sku__sku_desc']#'order__quantity', 'picked_quantity']
        model_obj = Picklist
        param_keys = {'wms_code': 'order__sku__wms_code', 'sku_code': 'order__sku__sku_code'}
        search_parameters.update({'status__in': ['open', 'batch_open', 'picked', 'batch_picked', 'dispatched'],
                                  #'picked_quantity__gt': 0,
                                  'stock__gt': 0,
                                  'order__user': user.id,
                                  'order__sku_id__in': sku_master_ids
                                })
    else:
        if serial_view:
            lis = ['order__order_id', 'order__sku__wms_code', 'order__sku__sku_desc', 'order__customer_name',
                   'po_imei__imei_number',
                   'updation_date', 'updation_date']
            model_obj = OrderIMEIMapping
            param_keys = {'wms_code': 'order__sku__wms_code', 'sku_code': 'order__sku__sku_code'}
            search_parameters['status'] = 1
            search_parameters['order__user'] = user.id
            search_parameters['order__sku_id__in'] = sku_master_ids
        else:
            lis = ['order__order_id', 'order__sku__wms_code', 'order__sku__sku_desc', 'stock__location__location',
                   'picked_quantity', 'picked_quantity', 'updation_date', 'updation_date']
            model_obj = Picklist
            param_keys = {'wms_code': 'order__sku__wms_code', 'sku_code': 'order__sku__sku_code'}
            search_parameters['status__in'] = ['open', 'batch_open', 'picked', 'batch_picked', 'dispatched']
            search_parameters['picked_quantity__gt'] = 0
            #search_parameters['stock__gt'] = 0
            search_parameters['order__user'] = user.id
            search_parameters['order__sku_id__in'] = sku_master_ids

    temp_data = copy.deepcopy(AJAX_DATA)

    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['updation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['updation_date__lt'] = search_params['to_date']
    if 'wms_code' in search_params:
        search_parameters[param_keys['wms_code']] = search_params['wms_code']
    if 'sku_code' in search_params:
        search_parameters[param_keys['sku_code']] = search_params['sku_code']
    if 'customer_id' in search_params:
        search_parameters['order__customer_id'] = search_params['customer_id']
    if 'imei_number' in search_params and serial_view:
        search_parameters['po_imei__imei_number'] = search_params['imei_number']
    if 'order_id' in search_params:
        order_detail = get_order_detail_objs(search_params['order_id'], user, search_params={}, all_order_objs=[])
        if order_detail:
            search_parameters['order_id__in'] = order_detail.values_list('id', flat=True)
        else:
            search_parameters['order_id__in'] = []
        if serial_view:
            order_ids = OrderIMEIMapping.objects.filter(order__user=user.id, status=1,
                                                        order_reference=search_params['order_id']). \
                values_list('order_id', flat=True)
            search_parameters['order_id__in'] = list(chain(search_parameters['order_id__in'], order_ids))

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    model_data = model_obj.objects.filter(**search_parameters)
    if customer_view:
        model_data = model_data.values(*lis).distinct()\
                               .annotate(qty=Sum('order__quantity'), tot_count=Count('order__quantity'))\
                               .annotate(tot_qty=F('qty')/Cast(F('tot_count'), FloatField()))\
                               .annotate(loc_qty=Sum('picklistlocation__quantity'), res_qty=Sum('picklistlocation__reserved'))
    if search_params.get('order_term'):
        order_data = lis[search_params['order_index']]
        if search_params['order_term'] == 'desc':
            order_data = "-%s" % order_data
        model_data = model_data.order_by(order_data)

    temp_data['recordsTotal'] = model_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    if stop_index:
        model_data = model_data[start_index:stop_index]

    for data in model_data:
        if customer_view:
            temp_data['aaData'].append(OrderedDict((('Customer ID', data['order__customer_id']),
                                                    ('Customer Name', data['order__customer_name']),
                                                    ('WMS Code', data['order__sku__wms_code']),
                                                    ('Description', data['order__sku__sku_desc']),
                                                    ('Quantity', data['qty']),
                                                    ('Picked Quantity', data['qty'] - data['res_qty'])
                                                  )))
        else:
            if not serial_view:
                if not data.stock:
                    date = get_local_date(user, data.updation_date).split(' ')
                    order_id = data.order.original_order_id
                    if not order_id:
                        order_id = str(data.order.order_code) + str(data.order.order_id)
                    child_sku_code = ''
                    if data.order_type == 'combo':
                        child_sku_code = data.sku_code
                    temp_data['aaData'].append(OrderedDict((('Order ID', order_id), ('WMS Code', data.order.sku.sku_code),
                                                            ('Child SKU', child_sku_code),
                                                            ('Description', data.order.sku.sku_desc),
                                                            ('Location', 'NO STOCK'),
                                                            ('Quantity', data.order.quantity),
                                                            ('Picked Quantity', data.picked_quantity),
                                                            ('Date', ' '.join(date[0:3])), ('Time', ' '.join(date[3:5])))))
                pick_locs = data.picklistlocation_set.exclude(reserved=0, quantity=0)
                for pick_loc in pick_locs:
                    picked_quantity = float(pick_loc.quantity) - float(pick_loc.reserved)
                    date = get_local_date(user, data.updation_date).split(' ')
                    order_id = data.order.original_order_id
                    if not order_id:
                        order_id = str(data.order.order_code) + str(data.order.order_id)
                    child_sku_code = ''
                    if data.order_type == 'combo':
                        if data.stock:
                            child_sku_code = data.stock.sku.sku_code
                        else:
                            child_sku_code = data.order.sku.sku_code
                    temp_data['aaData'].append(OrderedDict((('Order ID', order_id), ('WMS Code', data.order.sku.sku_code),
                                                            ('Child SKU', child_sku_code),
                                                            ('Description', data.stock.sku.sku_desc),
                                                            ('Location', pick_loc.stock.location.location),
                                                            ('Quantity', data.order.quantity),
                                                            ('Picked Quantity', picked_quantity),
                                                            ('Date', ' '.join(date[0:3])), ('Time', ' '.join(date[3:5])))))
            else:
                order_id = data.order.original_order_id
                if not order_id:
                    order_id = str(data.order.order_code) + str(data.order.order_id)

                # Overriding Order Id with Order Reference
                if data.order_reference:
                    order_id = data.order_reference
                serial_number = ''
                if data.po_imei:
                    serial_number = data.po_imei.imei_number
                date = get_local_date(user, data.updation_date).split(' ')
                temp_data['aaData'].append(OrderedDict((('Order ID', order_id), ('WMS Code', data.order.sku.wms_code),
                                                        ('Description', data.order.sku.sku_desc),
                                                        ('Customer Name', data.order.customer_name),
                                                        ('Serial Number', serial_number),
                                                        ('Date', ' '.join(date[0:3])), ('Time', ' '.join(date[3:5])))))
    return temp_data


def sku_wise_purchase_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from itertools import chain
    from rest_api.views.common import *
    from rest_api.views.inbound import get_purchase_order_data
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    data_list = []
    received_list = []
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    user_profile = UserProfile.objects.get(user_id=user.id)

    if not user_profile.user_type == 'marketplace_user':
        lis = ['po_date', 'open_po__supplier__name', 'open_po__sku__sku_code', 'open_po__order_quantity',
               'received_quantity', 'id', 'updation_date', 'id']
        columns = SKU_WISE_PO_DICT['dt_headers']
    else:
        lis = ['po_date', 'order_id', 'open_po__supplier_id', 'open_po__supplier__name',
               'open_po__sku__sku_code', 'open_po__sku__sku_desc', 'open_po__sku__sku_class',
               'open_po__sku__style_name', 'open_po__sku__sku_brand', 'open_po__sku__sku_category',
               'open_po__order_quantity', 'open_po__price', 'open_po__mrp', 'id', 'id', 'id', 'id', 'id']
        columns = SKU_WISE_PO_DICT['mk_dt_headers']
    if 'sku_code' in search_params:
        search_parameters['open_po__sku__sku_code'] = search_params['sku_code']
    if 'supplier' in search_params:
        supp_search = search_params['supplier'].split(':')
        search_parameters['open_po__supplier_id'] = supp_search[0]
    if 'from_date' in search_params:
        search_parameters['po_date__gte'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['po_date__lte'] = search_params['to_date']

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    search_parameters['open_po__sku__user'] = user.id
    search_parameters['open_po__sku_id__in'] = sku_master_ids
    purchase_orders = PurchaseOrder.objects.filter(**search_parameters)
    temp_data['recordsTotal'] = purchase_orders.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    quality_checks = QualityCheck.objects.filter(po_location__location__zone__user=user.id,
                                                 purchase_order_id__in=purchase_orders.values_list('id', flat=True)). \
        values('purchase_order_id').distinct().annotate(total_rejected=Sum('rejected_quantity'))
    qc_po_ids = map(lambda d: d['purchase_order_id'], quality_checks)
    qc_reject_sums = map(lambda d: d['total_rejected'], quality_checks)

    order_term = search_params.get('order_term', '')
    order_index = search_params.get('order_index', '')

    custom_search = False
    if order_index:
        order_data = lis[order_index]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        purchase_orders = purchase_orders.order_by(order_data)
        if columns[order_index] in ['Status', 'Rejected Quantity', 'Pre-Tax PO Amount', 'Tax',
                                    'After Tax PO Amount']:
            custom_search = True
    if not custom_search:
        if stop_index:
            purchase_orders = purchase_orders[start_index:stop_index]
    for data in purchase_orders:
        total_quantity = 0
        receipt_date = ''
        temp = ''
        if data.received_quantity == 0:
            status = 'Yet to Receive'
        elif int(data.open_po.order_quantity) - int(data.received_quantity) > 0:
            status = 'Partially Received'
            receipt_date = str(data.updation_date).split('+')[0]
        else:
            status = 'Received'
            receipt_date = str(data.updation_date).split('+')[0]

        order_data = get_purchase_order_data(data)
        if not user_profile.user_type == 'marketplace_user':
            temp = OrderedDict((('PO Date', get_local_date(user, data.po_date)), ('Supplier', order_data['supplier_name']),
                                ('SKU Code', order_data['wms_code']), ('Order Quantity', order_data['order_quantity']),
                                ('Received Quantity', data.received_quantity), ('Receipt Date', receipt_date),
                                ('Status', status)))
            temp['Rejected Quantity'] = 0
            if int(data.id) in qc_po_ids:
                temp['Rejected Quantity'] = qc_reject_sums[qc_po_ids.index(int(data.id))]
            if status == 'Received':
                received_list.append(temp)
            else:
                data_list.append(temp)
        else:
            po_number = '%s%s_%s' % (data.prefix, str(data.creation_date).split(' ')[0].replace('-', ''), data.order_id)
            tax = 0
            price = order_data['price']
            if data.open_po:
                tax = float(data.open_po.cgst_tax) + float(data.open_po.sgst_tax) + float(data.open_po.igst_tax)
                aft_price = price + ((price / 100) * tax)
            pre_amount = float(order_data['order_quantity']) * float(price)
            aft_amount = float(order_data['order_quantity']) * float(aft_price)
            temp = OrderedDict((('PO Date', get_local_date(user, data.po_date)), ('PO Number', po_number),
                                ('Supplier ID', order_data['supplier_id']),
                                ('Supplier Name', order_data['supplier_name']),
                                ('SKU Code', order_data['sku_code']),
                                ('SKU Description', order_data['sku_desc']),
                                ('SKU Class', order_data['sku'].sku_class),
                                ('SKU Style Name', order_data['sku'].style_name),
                                ('SKU Brand', order_data['sku'].sku_brand),
                                ('SKU Category', order_data['sku'].sku_category),
                                ('PO Qty', order_data['order_quantity']), ('Unit Rate', order_data['price']),
                                ('MRP', order_data['mrp']),
                                ('Pre-Tax PO Amount', pre_amount), ('Tax', tax), ('After Tax PO Amount', aft_amount),
                                ('Qty received', data.received_quantity), ('Status', status)
                                ))
            if status == 'Received':
                received_list.append(temp)
            else:
                data_list.append(temp)

    data_list = list(chain(data_list, received_list))
    if custom_search:
        data_list = apply_search_sort(columns, data_list, order_term, '', order_index)
        if stop_index:
            data_list = data_list[start_index:stop_index]
    temp_data['aaData'] = list(chain(temp_data['aaData'], data_list))

    return temp_data

def get_sku_wise_po_filter_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master, get_local_date, apply_search_sort, truncate_float
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    user_profile = UserProfile.objects.get(user_id=user.id)
    is_market_user = False
    if user_profile.user_type == 'marketplace_user':
        is_market_user = True
    if is_market_user:
        unsorted_dict = {15: 'Pre-Tax Received Value', 26: 'Post-Tax Received Value', 28: 'Margin',
                         29: 'Invoiced Unit Rate',
                         30: 'Invoiced Total Amount'}
        lis = ['purchase_order__updation_date', 'purchase_order__creation_date', 'purchase_order__order_id',
     	       'purchase_order__open_po__supplier_id', 'purchase_order__open_po__supplier__name', 'id',
               'purchase_order__open_po__sku__sku_code', 'purchase_order__open_po__sku__sku_desc',
               'purchase_order__open_po__sku__hsn_code',
               'purchase_order__open_po__sku__sku_class',
               'purchase_order__open_po__sku__style_name', 'purchase_order__open_po__sku__sku_brand',
               'purchase_order__open_po__sku__sku_category', 'total_received', 'purchase_order__open_po__price', 'id',
               'purchase_order__open_po__cgst_tax', 'purchase_order__open_po__sgst_tax',
               'purchase_order__open_po__igst_tax', 'purchase_order__open_po__utgst_tax',
               'purchase_order__open_po__cess_tax', 'purchase_order__open_po__cgst_tax', 'purchase_order__open_po__sgst_tax',
               'purchase_order__open_po__igst_tax', 'purchase_order__open_po__utgst_tax',
               'purchase_order__open_po__cess_tax','id', 'seller_po__margin_percent', 'id', 'id', 'id',
               'invoice_number', 'invoice_date', 'challan_number', 'challan_date']
        model_name = SellerPOSummary
        field_mapping = {'from_date': 'creation_date', 'to_date': 'creation_date',
                         'order_id': 'purchase_order__order_id',
                         'wms_code': 'purchase_order__open_po__sku__wms_code__iexact',
                         'user': 'purchase_order__open_po__sku__user',
                         'sku_id__in': 'purchase_order__open_po__sku_id__in',
                         'prefix': 'purchase_order__prefix', 'supplier_id': 'purchase_order__open_po__supplier_id',
                         'supplier_name': 'purchase_order__open_po__supplier__name',
                         'receipt_type': 'seller_po__receipt_type'}
        result_values = ['purchase_order__order_id', 'purchase_order__open_po__supplier_id',
                         'purchase_order__open_po__supplier__name', 'purchase_order__open_po__supplier__tax_type',
                         'purchase_order__open_po__sku__sku_code', 'purchase_order__open_po__sku__sku_desc',
                         'purchase_order__open_po__sku__hsn_code',
                         'purchase_order__open_po__sku__sku_class', 'purchase_order__open_po__sku__style_name',
                         'purchase_order__open_po__sku__sku_brand', 'purchase_order__open_po__sku__sku_category',
                         'purchase_order__received_quantity', 'purchase_order__open_po__price',
                         'purchase_order__open_po__cgst_tax',
                         'purchase_order__open_po__sgst_tax', 'purchase_order__open_po__igst_tax',
                         'purchase_order__open_po__utgst_tax', 'purchase_order__open_po__cess_tax',
                         'seller_po__margin_percent', 'purchase_order__prefix', 'seller_po__unit_price', 'id',
                         'seller_po__receipt_type', 'receipt_number', 'batch_detail__buy_price',
                         'batch_detail__tax_percent', 'invoice_number', 'invoice_date', 'challan_number',
                         'challan_date', 'discount_percent', 'cess_tax']
    else:
        unsorted_dict = {15: 'Pre-Tax Received Value', 26: 'Post-Tax Received Value',
                         27: 'Invoiced Unit Rate',
                         28: 'Invoiced Total Amount'}
        model_name = SellerPOSummary
        lis = ['purchase_order__updation_date', 'purchase_order__creation_date', 'purchase_order__order_id',
               'purchase_order__open_po__supplier_id', 'purchase_order__open_po__supplier__name', 'id',
               'purchase_order__open_po__sku__sku_code', 'purchase_order__open_po__sku__sku_desc',
               'purchase_order__open_po__sku__hsn_code', 'purchase_order__open_po__sku__sku_class',
               'purchase_order__open_po__sku__style_name', 'purchase_order__open_po__sku__sku_brand',
               'purchase_order__open_po__sku__sku_category', 'total_received', 'purchase_order__open_po__price', 'id',
               'purchase_order__open_po__cgst_tax', 'purchase_order__open_po__sgst_tax',
               'purchase_order__open_po__igst_tax', 'purchase_order__open_po__utgst_tax',
               'purchase_order__open_po__cess_tax',
               'purchase_order__open_po__cgst_tax', 'purchase_order__open_po__sgst_tax',
               'purchase_order__open_po__igst_tax', 'purchase_order__open_po__utgst_tax',
               'purchase_order__open_po__cess_tax',
               'id', 'seller_po__margin_percent', 'id', 'id', 'id',
               'invoice_number', 'invoice_date', 'challan_number', 'challan_date']
        field_mapping = {'from_date': 'creation_date', 'to_date': 'creation_date',
                         'order_id': 'purchase_order__order_id',
                         'wms_code': 'purchase_order__open_po__sku__wms_code__iexact',
                         'user': 'purchase_order__open_po__sku__user',
                         'sku_id__in': 'purchase_order__open_po__sku_id__in',
                         'prefix': 'purchase_order__prefix', 'supplier_id': 'purchase_order__open_po__supplier_id',
                         'supplier_name': 'purchase_order__open_po__supplier__name',
                         'receipt_type': 'seller_po__receipt_type'}
        result_values = ['purchase_order__order_id', 'purchase_order__open_po__supplier_id',
                         'purchase_order__open_po__supplier__name',
                         'purchase_order__open_po__sku__sku_code', 'purchase_order__open_po__sku__sku_desc',
                         'purchase_order__open_po__sku__hsn_code',
                         'purchase_order__open_po__sku__sku_class', 'purchase_order__open_po__sku__style_name',
                         'purchase_order__open_po__sku__sku_brand', 'purchase_order__open_po__sku__sku_category',
                         'purchase_order__received_quantity', 'purchase_order__open_po__price',
                         'purchase_order__open_po__cgst_tax',
                         'purchase_order__open_po__sgst_tax', 'purchase_order__open_po__igst_tax',
                         'purchase_order__open_po__utgst_tax', 'purchase_order__open_po__cess_tax',
                         'seller_po__margin_percent', 'purchase_order__prefix', 'seller_po__unit_price', 'id',
                         'seller_po__receipt_type', 'receipt_number', 'batch_detail__buy_price',
                         'batch_detail__tax_percent', 'invoice_number', 'invoice_date', 'challan_number',
                         'challan_date', 'discount_percent', 'cess_tax'
                         ]
    excl_status = {'purchase_order__status': ''}
    ord_quan = 'quantity'
    rec_quan = 'quantity'
    rec_quan1 = 'quantity'


    search_parameters = {}
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    temp_data = copy.deepcopy(AJAX_DATA)
    temp_data['draw'] = search_params.get('draw')
    if 'from_date' in search_params:
        search_parameters[field_mapping['from_date'] + '__gte'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters[field_mapping['to_date'] + '__lte'] = search_params['to_date']
    if 'open_po' in search_params and search_params['open_po']:
        temp = re.findall('\d+', search_params['open_po'])
        if temp:
            search_parameters[field_mapping['order_id']] = temp[-1]
    if 'sku_code' in search_params:
        search_parameters[field_mapping['wms_code']] = search_params['sku_code']
    search_parameters[field_mapping['user']] = user.id
    search_parameters[field_mapping['sku_id__in']] = sku_master_ids
    query_data = model_name.objects.exclude(**excl_status).filter(**search_parameters)
    model_data = query_data.values(*result_values).distinct().annotate(ordered_qty=Sum(ord_quan), total_received=Sum(rec_quan), grn_rec=Sum(rec_quan1))
    col_num = search_params.get('order_index', 0)
    order_term = search_params.get('order_term', 'asc')
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = "-%s" % order_data
        model_data = model_data.order_by(order_data)
    temp_data['recordsTotal'] = model_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    custom_search = False
    if col_num in unsorted_dict.keys():
        custom_search = True
    if stop_index and not custom_search:
        model_data = model_data[start_index:stop_index]
    purchase_orders = PurchaseOrder.objects.filter(open_po__sku__user=user.id)
    for data in model_data:
        result = purchase_orders.filter(order_id=data[field_mapping['order_id']], open_po__sku__user=user.id)[0]
        receipt_no = data['receipt_number']
        if not receipt_no:
            receipt_no = ''
        po_number = '%s%s_%s/%s' % (data[field_mapping['prefix']],
                                 str(result.creation_date).split(' ')[0].replace('-', ''),
                                 data[field_mapping['order_id']], str(receipt_no))
        price = data['purchase_order__open_po__price']
        if data.get('batch_detail__buy_price', 0):
            price = data['batch_detail__buy_price']
        #if data.get('batch_detail__tax_percent', 0):
        try:
            temp_tax_percent = data['batch_detail__tax_percent']
            if data['purchase_order__open_po__supplier__tax_type'] == 'intra_state':
                temp_tax_percent = temp_tax_percent / 2
                data['purchase_order__open_po__cgst_tax'] = truncate_float(temp_tax_percent, 1)
                data['purchase_order__open_po__sgst_tax'] = truncate_float(temp_tax_percent, 1)
                data['purchase_order__open_po__igst_tax'] = 0
                data['purchase_order__open_po__utgst_tax'] = 0
            else:
                data['purchase_order__open_po__igst_tax'] = temp_tax_percent
                data['purchase_order__open_po__cgst_tax'] = 0
                data['purchase_order__open_po__sgst_tax'] = 0
                data['purchase_order__open_po__utgst_tax'] = 0
        except Exception:
            pass
        if not data['purchase_order__open_po__cgst_tax']:
            data['purchase_order__open_po__cgst_tax'] = 0
        if not data['purchase_order__open_po__sgst_tax']:
            data['purchase_order__open_po__sgst_tax'] = 0
        if not data['purchase_order__open_po__igst_tax']:
            data['purchase_order__open_po__igst_tax'] = 0
        if not data['purchase_order__open_po__utgst_tax']:
            data['purchase_order__open_po__utgst_tax'] = 0
        if not data['purchase_order__open_po__cess_tax']:
            data['purchase_order__open_po__cess_tax'] = 0
        if data['cess_tax']:
            data['purchase_order__open_po__cess_tax'] = data['cess_tax']
        amount = float(data['total_received'] * price)
        if data['discount_percent']:
            amount = amount - (amount * float(data['discount_percent'])/100)
        tot_tax = float(data['purchase_order__open_po__cgst_tax']) + float(data['purchase_order__open_po__sgst_tax']) +\
                  float(data['purchase_order__open_po__igst_tax']) + float(data['purchase_order__open_po__utgst_tax'])\
                    + float(data['purchase_order__open_po__cess_tax'])
        aft_unit_price = float(price) + (float(price / 100) * tot_tax)
        if data['discount_percent']:
            aft_unit_price = aft_unit_price - (aft_unit_price * float(data['discount_percent'])/100)
        post_amount = aft_unit_price * float(data['total_received'])
        #seller_po_unit_price = data['seller_po__unit_price']
        #if not data['seller_po__unit_price']:
        #    seller_po_unit_price = 0
        margin_price = 0
        # margin_price = seller_po_unit_price - aft_unit_price
        # margin_price = float(abs(margin_price))
        # if margin_price < 0:
        #     margin_price = 0
        # margin_price = "%.2f" % (margin_price * float(data['total_received']))
        final_price = aft_unit_price
        invoice_total_amount = float(final_price) * float(data['total_received'])
        #invoice_total_amount = truncate_float(invoice_total_amount, 2)
        hsn_code = ''
        if data['purchase_order__open_po__sku__hsn_code']:
            hsn_code = str(data['purchase_order__open_po__sku__hsn_code'])
        invoice_date, challan_date = '', ''
        if data['invoice_date']:
            invoice_date = data['invoice_date'].strftime("%d %b, %Y")
        if data['challan_date']:
            challan_date = data['challan_date'].strftime("%d %b, %Y")
        temp_data['aaData'].append(OrderedDict((('Received Date', get_local_date(user, result.creation_date)),
                            ('PO Date', get_local_date(user, result.creation_date)),
                            ('PO Number', po_number),
                            ('Supplier ID', data[field_mapping['supplier_id']]),
                            ('Supplier Name', data[field_mapping['supplier_name']]),
                            ('Recepient', user.userprofile.company_name),
                            ('SKU Code', data['purchase_order__open_po__sku__sku_code']),
                            ('SKU Description', data['purchase_order__open_po__sku__sku_desc']),
                            ('HSN Code', hsn_code),
                            ('SKU Class', data['purchase_order__open_po__sku__sku_class']),
                            ('SKU Style Name', data['purchase_order__open_po__sku__style_name']),
                            ('SKU Brand', data['purchase_order__open_po__sku__sku_brand']),
                            ('SKU Category', data['purchase_order__open_po__sku__sku_category']),
                            ('Received Qty', data['total_received']),
                            ('Unit Rate', price),
                            ('Pre-Tax Received Value', amount),
                            ('CGST(%)', data['purchase_order__open_po__cgst_tax']),
                            ('SGST(%)', data['purchase_order__open_po__sgst_tax']),
                            ('IGST(%)', data['purchase_order__open_po__igst_tax']),
                            ('UTGST(%)', data['purchase_order__open_po__utgst_tax']),
                            ('CESS(%)', data['purchase_order__open_po__cess_tax']),
                            ('CGST', truncate_float((amount/100)* data['purchase_order__open_po__cgst_tax'], 2)),
                            ('SGST', truncate_float((amount/100)* data['purchase_order__open_po__sgst_tax'], 2)),
                            ('IGST', truncate_float((amount/100)* data['purchase_order__open_po__igst_tax'], 2)),
                            ('UTGST', truncate_float((amount/100)* data['purchase_order__open_po__utgst_tax'], 2)),
                            ('CESS', truncate_float((amount/100)* data['purchase_order__open_po__cess_tax'], 2)),
                            ('Post-Tax Received Value', post_amount),
                            ('Margin %', data['seller_po__margin_percent']),
                            ('Margin', margin_price),
                            ('Invoiced Unit Rate', final_price),
                            ('Invoiced Total Amount', invoice_total_amount),
                            ('Invoice Number', data['invoice_number']),
                            ('Invoice Date', invoice_date),
                            ('Challan Number', data['challan_number']),
                            ('Challan Date', challan_date),
                            ('DT_RowAttr', {'data-id': data['id']}), ('key', 'po_summary_id'),
                            ('receipt_type', data['seller_po__receipt_type']),
                            ('receipt_no', 'receipt_no')
	)))
    if stop_index and custom_search:
        if temp_data['aaData']:
            temp_data['aaData'] = apply_search_sort(temp_data['aaData'][0].keys(), temp_data['aaData'], order_term, '', col_num, exact=False)
            temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


def get_po_filter_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master, get_local_date, apply_search_sort
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    user_profile = UserProfile.objects.get(user_id=user.id)
    lis = ['order_id', 'open_po__supplier_id', 'open_po__supplier__name', 'ordered_qty']
    unsorted_dict = {}
    model_name = PurchaseOrder
    field_mapping = {'from_date': 'creation_date', 'to_date': 'creation_date', 'order_id': 'order_id', 'wms_code': 'open_po__sku__wms_code__iexact', 'user': 'open_po__sku__user', 'sku_id__in': 'open_po__sku_id__in', 'prefix': 'prefix', 'supplier_id': 'open_po__supplier_id', 'supplier_name': 'open_po__supplier__name'}
    result_values = ['order_id', 'open_po__supplier_id', 'open_po__supplier__name', 'prefix',
					 'sellerposummary__receipt_number']
    excl_status = {'status': ''}
    ord_quan = 'open_po__order_quantity'
    rec_quan = 'received_quantity'
    rec_quan1 = 'sellerposummary__quantity'
    search_parameters = {}
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    temp_data = copy.deepcopy(AJAX_DATA)
    temp_data['draw'] = search_params.get('draw')
    if 'from_date' in search_params:
        search_parameters[field_mapping['from_date'] + '__gte'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                         datetime.time())
        search_parameters[field_mapping['to_date'] + '__lte'] = search_params['to_date']
    if 'open_po' in search_params and search_params['open_po']:
        temp = re.findall('\d+', search_params['open_po'])
        if temp:
            search_parameters[field_mapping['order_id']] = temp[-1]
    if 'sku_code' in search_params:
        search_parameters[field_mapping['wms_code']] = search_params['sku_code']
    search_parameters[field_mapping['user']] = user.id
    search_parameters[field_mapping['sku_id__in']] = sku_master_ids
    search_parameters['received_quantity__gt'] = 0
    query_data = model_name.objects.prefetch_related('open_po__sku','open_po__supplier').select_related('open_po', 'open_po__sku','open_po__supplier').exclude(**excl_status).filter(**search_parameters)
    model_data = query_data.values(*result_values).distinct().annotate(ordered_qty=Sum(ord_quan),
                                                                   total_received=Sum(rec_quan),
                                                                   grn_rec=Sum(rec_quan1))
    col_num = search_params.get('order_index', 0)
    order_term = search_params.get('order_term', 'asc')
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
                order_data = "-%s" % order_data
        model_data = model_data.order_by(order_data)
    temp_data['recordsTotal'] = model_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    custom_search = False
    if col_num in unsorted_dict.keys():
        custom_search = True
    if stop_index and not custom_search:
        model_data = model_data[start_index:stop_index]
    purchase_orders = PurchaseOrder.objects.filter(open_po__sku__user=user.id)
    for data in model_data:
        po_result = purchase_orders.filter(order_id=data[field_mapping['order_id']], open_po__sku__user=user.id)
        result = po_result[0]
        total_ordered = po_result.aggregate(Sum('open_po__order_quantity'))['open_po__order_quantity__sum']
        if not total_ordered:
            total_ordered = 0
        po_number = '%s%s_%s' % (data[field_mapping['prefix']], str(result.creation_date).split(' ')[0].replace('-', ''),
                                    data[field_mapping['order_id']])
        receipt_no = data['sellerposummary__receipt_number']
        if not receipt_no:
            receipt_no = ''
        else:
            po_number = '%s/%s' % (po_number, receipt_no)
        received_qty = data['total_received']
        if data['grn_rec']:
            received_qty = data['grn_rec']
        temp_data['aaData'].append(OrderedDict((('PO Number', po_number),
                                                ('Supplier ID', data[field_mapping['supplier_id']]),
                                                ('Supplier Name', data[field_mapping['supplier_name']]),
                                                ('Order Quantity', total_ordered),
                                                ('Received Quantity', received_qty),
                                                ('DT_RowClass', 'results'), ('DT_RowAttr', {'data-id': data[field_mapping['order_id']]}),
                                                ('key', 'po_id'), ('receipt_type', 'Purchase Order'), ('receipt_no', receipt_no),
                                            )))
    if stop_index and custom_search:
        if temp_data['aaData']:
            temp_data['aaData'] = apply_search_sort(temp_data['aaData'][0].keys(), temp_data['aaData'], order_term, '', col_num, exact=False)
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


def get_stock_summary_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    search_stage = search_params.get('stage', '')
    stage_filter = {'user': user.id}
    if search_stage:
        stage_filter['stage_name'] = search_stage
    extra_headers = list(
        ProductionStages.objects.filter(**stage_filter).order_by('order').values_list('stage_name', flat=True))
    job_order = JobOrder.objects.filter(product_code__user=user.id,
                                        status__in=['grn-generated', 'pick_confirm', 'partial_pick'])

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    cmp_data = ('sku_code', 'sku_brand')
    job_filter = {}
    for data in cmp_data:
        if data in search_params:
            search_parameters['%s__%s__%s' % ('sku', data, 'iexact')] = search_params[data]
            job_filter['%s__%s__%s' % ('product_code', data, 'iexact')] = search_params[data]

    search_parameters['sku__user'] = user.id
    search_parameters['sku_id__in'] = sku_master_ids

    sku_master = StockDetail.objects.exclude(receipt_number=0).values_list('sku_id', 'sku__sku_code', 'sku__sku_desc',
                                                                           'sku__sku_brand',
                                                                           'sku__sku_category').distinct().annotate(
        total=Sum('quantity')).filter(quantity__gt=0,
                                      **search_parameters)
    if search_stage and not search_stage == 'In Stock':
        sku_master = []
    wms_codes = map(lambda d: d[0], sku_master)
    sku_master1 = job_order.exclude(product_code_id__in=wms_codes).filter(**job_filter).values_list('product_code_id',
                                                                                                    'product_code__sku_code',
                                                                                                    'product_code__sku_desc',
                                                                                                    'product_code__sku_brand',
                                                                                                    'product_code__sku_category').distinct()
    sku_master = list(chain(sku_master, sku_master1))

    purchase_orders = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']).filter(
        open_po__sku__user=user.id). \
        values('open_po__sku_id').annotate(total_order=Sum('open_po__order_quantity'),
                                           total_received=Sum('received_quantity'))
    if search_stage and not search_stage == 'In Transit':
        purchase_orders = []

    status_filter = {'status_type': 'JO', 'status_value__in': extra_headers}
    status_tracking = StatusTracking.objects.filter(**status_filter)

    intransit_skus = map(lambda d: d['open_po__sku_id'], purchase_orders)
    intransit_ordered = map(lambda d: d['total_order'], purchase_orders)
    intransit_received = map(lambda d: d['total_received'], purchase_orders)
    sku_master_list = []
    for ind, sku in enumerate(sku_master):
        sku_stages_dict = {}
        intransit_quantity = 0
        if len(list(sku)) == 6:
            sku_stages_dict['In Stock'] = sku[5]
        if sku[0] in intransit_skus:
            total_ordered = map(lambda d: d['total_order'], purchase_orders)[intransit_skus.index(sku[0])]
            total_received = map(lambda d: d['total_received'], purchase_orders)[intransit_skus.index(sku[0])]
            diff_quantity = float(total_ordered) - float(total_received)
            if diff_quantity > 0:
                intransit_quantity = diff_quantity
        if intransit_quantity:
            sku_stages_dict['In Transit'] = intransit_quantity
        job_ids = job_order.filter(product_code_id=sku[0]).values_list('id', flat=True)
        status_track = status_tracking.filter(status_id__in=job_ids).values('status_value').distinct().annotate(
            total=Sum('quantity'))

        tracking = dict(zip(map(lambda d: d.get('status_value', ''), status_track),
                            map(lambda d: d.get('total', '0'), status_track)))
        for head in extra_headers:
            quantity = tracking.get(head, 0)
            if quantity:
                sku_stages_dict[head] = tracking.get(head, 0)
        for key, value in sku_stages_dict.iteritems():
            sku_master_list.append(OrderedDict((('SKU Code', sku[1]), ('Description', sku[2]),
                                                ('Brand', sku[3]), ('Category', sku[4]),
                                                ('Stage', key), ('Stage Quantity', value))))

    temp_data['recordsTotal'] = len(sku_master_list)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    order_term = search_params.get('order_term', '')
    order_index = search_params.get('order_index', '')

    if order_term == 'asc' and sku_master_list and order_index:
        sku_master_list = sorted(sku_master_list, key=itemgetter(sku_master_list[0].keys()[order_index]))
    elif sku_master_list and order_index:
        sku_master_list = sorted(sku_master_list, key=itemgetter(sku_master_list[0].keys()[order_index]), reverse=True)

    if stop_index:
        sku_master_list = sku_master_list[start_index:stop_index]

    temp_data['aaData'] = sku_master_list

    return temp_data


def get_daily_production_data(search_params, user, sub_user):
    from miebach_admin.models import JobOrder, ProductionStages, StatusTrackingSummary
    from rest_api.views.common import get_local_date
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    #all_data = OrderedDict()
    sort_keys = OrderedDict((('Date', 'creation_date'), ('Job Order', 'job_code'),('JO Creation Date', 'creation_date'),
                            ('SKU Class', 'product_code__sku_class'), ('SKU Code', 'product_code__sku_code'),
                            ('Brand', 'product_code__sku_brand'), ('SKU Category', 'product_code__sku_category'),
                            ('Total JO Quantity', 'product_quantity'),
                            ('Reduced Quantity', 'quantity'),
                            ('Stage', 'processed_stage')))
    order_term = search_params.get('order_term', '')
    order_index = search_params.get('order_index', '')
    cmp_data = ('sku_code', 'sku_brand', 'sku_class', 'sku_category')
    job_filter = {}
    for data in cmp_data:
        if data in search_params:
            search_parameters['%s__%s__%s' % ('product_code', data, 'iexact')] = search_params[data]
    search_stage = search_params.get('stage', '')
    stage_filter = {'user': user.id}
    if search_stage:
        stage_filter['stage_name'] = search_stage
    search_parameters['product_code_id__in'] = sku_master_ids
    jo_code = search_params.get('jo_code', '')
    if jo_code:
        search_parameters['job_code'] = jo_code
    extra_headers = list(
        ProductionStages.objects.filter(**stage_filter).order_by('order').values_list('stage_name', flat=True))
    job_orders = JobOrder.objects.filter(product_code__user=user.id,
                                         status__in=['grn-generated', 'pick_confirm', 'partial_pick',
                                                     'location-assigned', 'confirmed-putaway'], **search_parameters)
    job_code_ids = job_orders.values('job_code', 'id').distinct()
    job_ids = map(lambda d: d['id'], job_code_ids)
    status_filter = {'status_tracking__status_type': 'JO', 'processed_stage__in': extra_headers,
                     'status_tracking__status_id__in': job_ids}
    if 'from_date' in search_params:
        status_filter['creation_date__gte'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
    if 'to_date' in search_params:
        status_filter['creation_date__lte'] = datetime.datetime.combine(
            search_params['to_date'] + datetime.timedelta(1), datetime.time())
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    status_tracking_objs = StatusTrackingSummary.objects.filter(**status_filter)
    col_sorted = False
    if not isinstance(order_index, int):
        order_index = 0
    if sort_keys.keys()[order_index] in ['Date', 'Reduced Quantity', 'Stage']:
        order_data = sort_keys.values()[order_index]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        status_tracking_objs = status_tracking_objs.order_by(order_data)
    status_summary = status_tracking_objs.annotate(grouping_val=Concat('status_tracking__status_id',
                                                                             Value('<<>>'), 'processed_stage',
                                                                             output_field=CharField())).\
                                                values('grouping_val').distinct().\
                                                    annotate(tsum=Sum('processed_quantity'))

    temp_data['recordsTotal'] = status_summary.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    if sort_keys.keys()[order_index] in ['Date', 'Reduced Quantity', 'Stage']:
        col_sorted = True
        if stop_index:
            status_summary = status_summary[start_index:stop_index]
    data = []
    for summary_dict in status_summary:
        temp_val = summary_dict['grouping_val'].split('<<>>')
        summary = StatusTrackingSummary.objects.filter(status_tracking__status_id=temp_val[0],
                                                       processed_stage=temp_val[1])[0]
        job_order = job_orders.get(id=summary.status_tracking.status_id)
        summary_date = get_local_date(user, summary.creation_date).split(' ')
        summary_date = ' '.join(summary_date[0:3])
        jo_creation_date = get_local_date(user, job_order.creation_date).split(' ')
        jo_creation_date = ' '.join(jo_creation_date[0:3])
        # cond = (summary_date, job_order.job_code, jo_creation_date, job_order.product_code.sku_class,
        #         job_order.product_code.sku_code,
        #         job_order.product_code.sku_brand, job_order.product_code.sku_category, job_order.product_quantity,
        #         summary.processed_stage)
        data.append(OrderedDict((('Date', summary_date), ('Job Order', job_order.job_code),
                                               ('JO Creation Date', jo_creation_date),
                                               ('SKU Class', job_order.product_code.sku_class),
                                               ('SKU Code', job_order.product_code.sku_code),
                                               ('Brand', job_order.product_code.sku_brand),
                                               ('SKU Category', job_order.product_code.sku_category),
                                               ('Total JO Quantity', job_order.product_quantity),
                                               ('Reduced Quantity', summary_dict['tsum']),
                                               ('Stage', summary.processed_stage)
                         )))
        #all_data[cond]['Reduced Quantity'] += float(summary.processed_quantity)
        # job_code = filter(lambda job_code_ids: job_code_ids['id'] == summary.status_tracking.status_id, job_code_ids)

    #data = all_data.values()
    # for key in all_data_keys:
    #     data.append(
    #         OrderedDict((('Date', key[0]), ('Job Order', key[1]), ('JO Creation Date', key[2]), ('SKU Class', key[3]),
    #                      ('SKU Code', key[4]), ('Brand', key[5]), ('SKU Category', key[6]),
    #                      ('Total JO Quantity', key[7]),
    #                      ('Reduced Quantity', all_data[key]), ('Stage', key[8])
    #                      )))

    if data and not col_sorted:
        if order_term == 'asc' and order_index:
            data = sorted(data, key=itemgetter(data[0].keys()[order_index]))
        elif order_index or (order_index == 0 and order_term == 'desc'):
            data = sorted(data, key=itemgetter(data[0].keys()[order_index]), reverse=True)

    temp_data['aaData'] = data
    # if stop_index:
    #     temp_data['aaData'] = data[start_index:stop_index]

    return temp_data


def get_openjo_details(search_params, user, sub_user):
    from miebach_admin.models import *
    from miebach_admin.views import *
    from rest_api.views.common import get_sku_master
    from rest_api.views.production import get_user_stages
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    lis = ['jo_id', 'jo_creation_date', 'sku__brand', 'sku__sku_category', 'sku__sku_class', 'sku__sku_code', 'stage',
           'quantity']
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    final_data = []

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    search_parameters['product_code__id__in'] = list(sku_master_ids)
    if 'sku_code' in search_params:
        search_parameters['product_code__sku_code'] = search_params['sku_code']
    if 'sku_class' in search_params:
        search_parameters['product_code__sku_class'] = search_params['sku_class']
    if 'sku_category' in search_params:
        search_parameters['product_code__sku_category'] = search_params['sku_category']
    if 'sku_brand' in search_params:
        search_parameters['product_code__sku_brand'] = search_params['sku_brand']
    if 'job_code' in search_params:
        search_parameters['job_code'] = int(search_params['job_code'])
    if 'stage' in search_params:
        jos = JobOrder.objects.filter(**search_parameters).exclude(status='confirmed-putaway')
        if search_params['stage'] == 'Putaway pending':
            jos = jos.filter(status__in=['location-assigned', 'grn-generated'])
        elif search_params['stage'] == 'Picklist Generated':
            jos = jos.filter(status='picklist_gen')
        elif search_params['stage'] == 'Created':
            jos = jos.filter(status__in=['open', 'order-confirmed'])
        elif search_params['stage'] == 'Partially Picked':
            jos = jos.filter(status='partial_pick')
        elif search_params['stage'] == 'Picked':
            jos = jos.filter(status='pick_confirm')
        else:
            # jos = jos.filter(status = 'pick_confirm')
            jos = list(jos.filter(**search_parameters).values_list('id', flat=True))
            jos = StatusTracking.objects.filter(status_id__in=jos, status_value=search_params['stage'],
                                                status_type='JO').values_list('status_id', flat=True)
            jos = JobOrder.objects.filter(id__in=jos)
    else:
        jos = JobOrder.objects.filter(**search_parameters).exclude(status='confirmed-putaway')

    putaway_qtys = dict(
        POLocation.objects.filter(status=1, quantity__gt=0, job_order__product_code__user=user.id).values_list(
            'job_order_id'). \
        distinct().annotate(tsum=Sum('quantity')))
    all_stages = get_user_stages(user, user)
    for data in jos:
        stage_filter = {}
        if search_params.get('stage', '') in all_stages:
            stage_filter['status_value'] = search_params.get('stage', '')
        elif (data.status == 'open') or (data.status == 'order-confirmed'):
            stage = 'Created'
            quantity = data.product_quantity
            final_data.append({'stage': stage, 'quantity': quantity, 'data': data})
        elif data.status == 'picklist_gen':
            stage = 'Picklist Generated'
            quantity = data.product_quantity
            final_data.append({'stage': stage, 'quantity': quantity, 'data': data})
        elif (data.status == 'location-assigned') or (data.status == 'grn-generated'):
            stage = 'Putaway pending'
            quantity = putaway_qtys.get(data.id, 0)
            final_data.append({'stage': stage, 'quantity': quantity, 'data': data})
        # elif (data.status == 'pick_confirm'):
        elif (data.status == 'partial_pick'):
            MaterialPicklist.objects.filter(jo_material__job_order__job_code=data.id)
            stage = 'Partially Picked'
            quantity = data.product_quantity
            final_data.append({'stage': stage, 'quantity': quantity, 'data': data})
        # else:
        #    stage = 'Picked'
        #    quantity = data.product_quantity
        #    final_data.append({'stage': stage, 'quantity': quantity, 'data': data})
        stages_list = StatusTracking.objects.filter(status_id=data.id).values_list('original_quantity', 'status_value')
        if 'stage' in search_params:
            stages_list = StatusTracking.objects.filter(status_id=data.id, **stage_filter).values_list(
                'original_quantity', 'status_value')
        if stages_list and search_params.get('stage', '') in ([''] + all_stages):
            for sing_stage in stages_list:
                stage = sing_stage[1]
                quantity = sing_stage[0]
                if quantity == 0:
                    continue
                final_data.append({'stage': stage, 'quantity': quantity, 'data': data})

    temp_data['recordsTotal'] = len(final_data)
    temp_data['recordsFiltered'] = len(final_data)

    order_term = search_params.get('order_term', '')
    order_index = search_params.get('order_index', '')

    last_data = []
    for one_data in final_data:
        date = get_local_date(user, one_data['data'].creation_date).split(' ')
        last_data.append(OrderedDict((('JO Code', one_data['data'].job_code), ('Jo Creation Date', ' '.join(date[0:3])),
                                      ('SKU Brand', one_data['data'].product_code.sku_brand),
                                      ('SKU Category', one_data['data'].product_code.sku_category),
                                      ('SKU Class', one_data['data'].product_code.sku_class),
                                      ('SKU Code', one_data['data'].product_code.sku_code),
                                      ('Stage', one_data['stage']), ('Quantity', one_data['quantity']))))

    if order_term == 'asc' and order_index:
        last_data = sorted(last_data, key=itemgetter(last_data[0].keys()[order_index]))
        temp_data['aaData'] = last_data[start_index:stop_index]
        return temp_data
    elif order_index or (order_index == 0 and order_term == 'desc'):
        last_data = sorted(last_data, key=itemgetter(last_data[0].keys()[order_index]), reverse=True)
        temp_data['aaData'] = last_data[start_index:stop_index]
        return temp_data
    temp_data['aaData'] = last_data
    if stop_index:
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


def get_order_summary_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from miebach_admin.views import *
    from rest_api.views.common import get_sku_master, get_order_detail_objs, get_local_date
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    lis = ['creation_date', 'order_id', 'customer_name', 'sku__sku_brand', 'sku__sku_category', 'sku__sku_class',
           'sku__sku_size', 'sku__sku_desc', 'sku_code', 'quantity', 'sku__mrp', 'sku__mrp', 'sku__mrp',
           'sku__discount_percentage', 'city', 'state', 'marketplace', 'invoice_amount','order_id', 'order_id','order_id','order_id','order_id','order_id','invoice_number','quantity','creation_date'];
    # lis = ['order_id', 'customer_name', 'sku__sku_code', 'sku__sku_desc', 'quantity', 'updation_date', 'updation_date', 'marketplace']
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lt'] = search_params['to_date']
    if 'sku_code' in search_params:
        search_parameters['sku__sku_code'] = search_params['sku_code']
    if 'marketplace' in search_params:
        search_parameters['marketplace'] = search_params['marketplace']
    if 'sku_category' in search_params:
        search_parameters['sku__sku_category'] = search_params['sku_category']
    if 'sku_brand' in search_params:
        search_parameters['sku__sku_brand'] = search_params['sku_brand']
    if 'sku_size' in search_params:
        search_parameters['sku__sku_size'] = search_params['sku_size']
    if 'sku_class' in search_params:
        search_parameters['sku__sku_class'] = search_params['sku_class']
    if 'city' in search_params:
        search_parameters['city'] = search_params['city']
    if 'city' in search_params:
        search_parameters['state'] = search_params['state']
    if 'order_id' in search_params:
        order_detail = get_order_detail_objs(search_params['order_id'], user, search_params={}, all_order_objs=[])
        search_parameters['id__in'] = order_detail.values_list('id', flat=True)

    status_search = search_params.get('order_report_status', "")

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    search_parameters['quantity__gt'] = 0
    search_parameters['user'] = user.id
    search_parameters['sku_id__in'] = sku_master_ids

    if 'invoice_number' in search_params :
        orders = OrderDetail.objects.filter(sellerordersummary__invoice_number = search_params['invoice_number'])
    else:
        orders = OrderDetail.objects.filter(**search_parameters)
    pick_filters = {}
    for key, value in search_parameters.iteritems():
        pick_filters['order__%s' % key] = value
    order_id_status = dict(OrderDetail.objects.select_related('order_id', 'status').filter(**search_parameters).\
                                        only('id', 'status').values_list('id', 'status').distinct())

    picklist_generated = Picklist.objects.select_related('order').filter(status__icontains='open',picked_quantity=0,
                                                 **pick_filters).only('order_id').values_list('order_id', flat=True).distinct()

    partially_picked = Picklist.objects.filter(status__icontains='open', picked_quantity__gt=0,
                                               reserved_quantity__gt=0, **pick_filters).values_list('order_id',
                                                                                    flat=True).distinct()

    picked_orders = Picklist.objects.filter(status__icontains='picked', picked_quantity__gt=0,
                                            reserved_quantity=0, **pick_filters).values_list('order_id', flat=True).distinct()

    #order_ids = OrderDetail.objects.filter(status=1, user=user.id).values_list('order_id', flat=True).distinct()
    pos_order_ids = OrderDetail.objects.filter(Q(order_code__icontains="PRE")|
                    Q(order_code__icontains="DC"), status=1, **search_parameters).values_list('id', flat=True).distinct()
    partial_generated = Picklist.objects.filter(**pick_filters)\
                                .exclude(order_id__in=pos_order_ids).values_list(\
                                'order_id', flat=True).distinct()
    #dispatched = OrderDetail.objects.filter(status=2, **search_parameters).values_list('order_id', flat=True).distinct()
    #reschedule_cancelled = OrderDetail.objects.filter(status=5, **search_parameters).values_list('order_id',
    #                                                                                     flat=True).distinct()

    _status = ""
    if status_search:
        # ['Open', 'Picklist generated', 'Partial Picklist generated', 'Picked', 'Partially picked']
        ord_ids = ""
        if status_search == 'Open':
            ord_ids = OrderDetail.objects.filter(status=1, **search_parameters).\
                                            values_list('id', flat=True).distinct()
        elif status_search == 'Picklist generated':
            ord_ids = picklist_generated
        elif status_search == 'Partial Picklist generated':
            ord_ids = partially_picked
        elif status_search == 'Picked':
            ord_ids = picked_orders
        elif status_search == 'Partially picked':
            ord_ids = partial_generated

        orders = orders.filter(id__in=ord_ids)
        _status = status_search

    if search_params.get('order_term'):
        order_data = lis[search_params['order_index']]
        if search_params['order_term'] == 'desc':
            order_data = "-%s" % order_data
            if order_data == '-invoice_number':
                orders = orders.order_by('-sellerordersummary__invoice_number')
            elif order_data == '-quantity' :
                orders = orders.order_by('-sellerordersummary__quantity')
            elif  order_data == '-creation_date' :
                orders = orders.order_by('-creation_date')
            else:
                orders = orders.order_by(order_data)

    temp_data['recordsTotal'] = orders.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    try:
        temp_data['totalOrderQuantity'] = int(orders.aggregate(Sum('quantity'))['quantity__sum'])
    except:
        temp_data['totalOrderQuantity'] = 0
    try:
        temp_data['totalSellingPrice'] = int(orders.aggregate(Sum('invoice_amount'))['invoice_amount__sum'])
    except:
        temp_data['totalSellingPrice'] = 0
    try:
        temp_data['totalMRP'] = int(orders.aggregate(Sum('sku__mrp'))['sku__mrp__sum'])
    except:
        temp_data['totalMRP'] = 0
    if stop_index:
        orders = orders[start_index:stop_index]
    status = ''
    count = 1
    extra_fields = []
    extra_fields_obj = MiscDetail.objects.filter(user=user.id, misc_type__icontains="pos_extra_fields")
    for field in extra_fields_obj:
        tmp = field.misc_value.split(',')
        for i in tmp:
            extra_fields.append(str(i))
    for data in orders.iterator():
        count = count + 1
        is_gst_invoice = False
        invoice_date = get_local_date(user, data.creation_date, send_date='true')
        if datetime.datetime.strptime('2017-07-01', '%Y-%m-%d').date() <= invoice_date.date():
            is_gst_invoice = True
        date = get_local_date(user, data.creation_date).split(' ')
        order_id = str(data.order_code) + str(data.order_id)
        if data.original_order_id:
            order_id = data.original_order_id

        # ['Open', 'Picklist generated', 'Partial Picklist generated', 'Picked', 'Partially picked']
        if not _status:
            if order_id_status.get(data.id, '') == '1':
                status = ORDER_SUMMARY_REPORT_STATUS[0]
            elif data.id in picklist_generated:
                status = ORDER_SUMMARY_REPORT_STATUS[1]
            elif data.id in partially_picked:
                status = ORDER_SUMMARY_REPORT_STATUS[2]
            elif data.id in picked_orders:
                status = ORDER_SUMMARY_REPORT_STATUS[3]
            elif data.id in partial_generated:
                status = ORDER_SUMMARY_REPORT_STATUS[4]
            if order_id_status.get(data.id, '') == '2':
                status = ORDER_DETAIL_STATES.get(2, '')
            if order_id_status.get(data.id, '') == '5':
                status = ORDER_DETAIL_STATES.get(5, '')
        else:
            status = _status

        tax = 0
        vat = 5.5
        discount = 0
        mrp_price = data.sku.mrp
        order_status = ''
        remarks = ''
        order_taken_by = ''
        payment_card, payment_cash = 0, 0
        order_summary = data.customerordersummary_set.filter()#CustomerOrderSummary.objects.filter(order__user=user.id, order_id=data.id)
        unit_price, unit_price_inclusive_tax = [data.unit_price] * 2
        if order_summary:
            mrp_price = order_summary[0].mrp
            discount = order_summary[0].discount
            order_status = order_summary[0].status
            remarks = order_summary[0].central_remarks
            order_taken_by = order_summary[0].order_taken_by
            #unit_price_inclusive_tax = ((float(data.invoice_amount) / float(data.quantity)))
            if not is_gst_invoice:
                tax = order_summary[0].tax_value
                vat = order_summary[0].vat
                #if not unit_price:
            else:
                amt = unit_price_inclusive_tax * float(data.quantity)
                cgst_amt = float(order_summary[0].cgst_tax) * (float(amt) / 100)
                sgst_amt = float(order_summary[0].sgst_tax) * (float(amt) / 100)
                igst_amt = float(order_summary[0].igst_tax) * (float(amt) / 100)
                utgst_amt = float(order_summary[0].utgst_tax) * (float(amt) / 100)
                tax = cgst_amt + sgst_amt + igst_amt + utgst_amt
            #unit_price = unit_price_inclusive_tax - (tax / float(data.quantity))
        else:
            tax = float(float(data.invoice_amount) / 100) * vat
        if order_status == 'None':
            order_status = ''
        invoice_amount = "%.2f" % ((float(unit_price) * float(data.quantity)) + tax - discount)
        taxable_amount = "%.2f" % abs(float(invoice_amount) - float(tax))
        unit_price = "%.2f" % unit_price

        #payment mode
        payment_obj = OrderFields.objects.filter(user=user.id, name__icontains="payment_",\
                                      original_order_id=data.original_order_id).values_list('name', 'value')
        if payment_obj:
            for pay in payment_obj:
                exec("%s = %s" % (pay[0],pay[1]))
        #pos extra fields
        pos_extra = {}
        extra_vals = OrderFields.objects.filter(user=user.id,\
                       original_order_id=data.original_order_id).values('name', 'value')
        for field in extra_fields:
            pos_extra[field] = ''
            for val in extra_vals:
                if field == val['name']:
                    pos_extra[str(val['name'])] = str(val['value'])
        invoice_number_obj = SellerOrderSummary.objects.filter(order_id = data.id)
        if invoice_number_obj :
            invoice_number = invoice_number_obj[0].invoice_number
            quantity = invoice_number_obj[0].quantity
            invoice_date = get_local_date(user,invoice_number_obj[0].creation_date)
        else:
            invoice_number = 0
            quantity = 0
            invoice_date = 0


        aaData = OrderedDict((('Order Date', ''.join(date[0:3])), ('Order ID', order_id),
                                                ('Customer Name', data.customer_name),
                                                ('Order Number' ,data.order_reference),
                                                ('SKU Brand', data.sku.sku_brand),
                                                ('SKU Category', data.sku.sku_category),
                                                ('SKU Class', data.sku.sku_class),
                                                ('SKU Size', data.sku.sku_size), ('SKU Description', data.sku.sku_desc),
                                                ('SKU Code', data.sku.sku_code), ('Order Qty', int(data.quantity)),
                                                ('MRP', int(data.sku.mrp)), ('Unit Price', float(unit_price_inclusive_tax)),
                                                ('Discount', discount),
                                                ('Invoice Number',invoice_number),
                                                ('Quantity',quantity),
                                                ('Taxable Amount', float(taxable_amount)), ('Tax', tax),
                                                ('City', data.city), ('State', data.state), ('Marketplace', data.marketplace),
                                                ('Invoice Amount', float(invoice_amount)), ('Price', data.sku.price),
                                                ('Status', status), ('Order Status', order_status),
                                                ('Remarks', remarks), ('Order Taken By', order_taken_by),
                                                ('Invoice Date',invoice_date),
                                                ('Payment Cash', payment_cash), ('Payment Card', payment_card)))
        aaData.update(OrderedDict(pos_extra))
        temp_data['aaData'].append(aaData)
    return temp_data


def html_excel_data(data, fname):
    from miebach_admin.views import *
    tree = html.fromstring(data)
    rows = tree.xpath('//tr')
    file_name = "rewrite_" + fname.name
    for index, row in enumerate(rows):
        cols = row.xpath('./td//text()')
        if index == 0:
            wb, ws = get_work_sheet('skus', cols)
            continue
        for ind, col in enumerate(cols):
            ws.write(index, ind, col)
    wb.save(file_name)
    open_book = open_workbook(file_name)
    open_sheet = open_book.sheet_by_index(0)
    os.remove(file_name)
    return open_book, open_sheet


def get_seller_invoices_filter_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master, get_local_date, apply_search_sort
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    lis = ['open_po__creation_date', 'open_po__supplier__name', 'seller__seller_id', 'seller__name',
           'open_po__sku__sku_code', 'open_po__sku__sku_desc', 'open_po__sku__sku_class',
           'open_po__sku__style_name', 'open_po__sku__sku_brand', 'open_po__sku__sku_category',
           'id', 'id', 'open_po__order_quantity', 'id', 'open_po__tax', 'id']

    unsorted_dict = {10: 'Accepted Qty', 11: 'Rejected Qty', 13: 'Amount', 15: 'Total Amount'}
    search_parameters = {}
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    temp_data = copy.deepcopy(AJAX_DATA)
    temp_data['draw'] = search_params.get('draw')

    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['open_po__creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['open_po__creation_date__lt'] = search_params['to_date']

    if 'sku_code' in search_params:
        search_parameters['open_po__sku__sku_code__iexact'] = search_params['sku_code']

    search_parameters['open_po__sku__user'] = user.id
    search_parameters['open_po__sku_id__in'] = sku_master_ids
    exc_po_ids = PurchaseOrder.objects.filter(open_po__sku__user=user.id, status='').values_list('open_po_id',
                                                                                                 flat=True)
    seller_pos = SellerPO.objects.exclude(open_po_id__in=exc_po_ids).filter(**search_parameters)
    quality_checks = QualityCheck.objects.filter(po_location__location__zone__user=user.id,
                                                 purchase_order__open_po_id__in=seller_pos.values_list('open_po_id',
                                                                                                       flat=True)). \
        values('purchase_order__open_po_id').distinct().annotate(total_rejected=Sum('rejected_quantity'),
                                                                 total_accepted=Sum('accepted_quantity'))
    qc_po_ids = map(lambda d: d['purchase_order__open_po_id'], quality_checks)
    qc_reject_sums = map(lambda d: d['total_rejected'], quality_checks)
    qc_accept_sums = map(lambda d: d['total_accepted'], quality_checks)
    if 'order_term' not in search_params:
        search_params['order_term'] = 0
    if search_params['order_term']:
        order_data = lis[search_params['order_index']]
        if search_params['order_term'] == 'desc':
            order_data = "-%s" % order_data
        seller_pos = seller_pos.order_by(order_data)

    temp_data['recordsTotal'] = seller_pos.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    col_num = search_params.get('order_index', 0)
    order_term = search_params.get('order_term', 'asc')

    custom_search = False
    if col_num in unsorted_dict.keys():
        custom_search = True

    if stop_index and not custom_search:
        seller_pos = seller_pos[start_index:stop_index]

    for data in seller_pos:
        accepted_quan = 0
        rejected_quan = 0
        final_price = float(data.open_po.price)
        if data.unit_price:
            final_price = float(data.unit_price)
        if data.open_po.tax:
            final_price = float('%.2f' % ((final_price * 100) / (100 + float(data.open_po.tax))))
        amount = final_price * float(data.open_po.order_quantity)
        total_amount = amount
        if data.open_po.tax:
            total_amount = amount + (amount / 100) * float(data.open_po.tax)
        if int(data.open_po_id) in qc_po_ids:
            rejected_quan = qc_reject_sums[qc_po_ids.index(int(data.open_po_id))]
        if int(data.open_po_id) in qc_po_ids:
            accepted_quan = qc_accept_sums[qc_po_ids.index(int(data.open_po_id))]
        temp_data['aaData'].append(
            OrderedDict((('Date', get_local_date(user, data.creation_date)), ('Supplier', data.open_po.supplier.name),
                         ('Seller ID', data.seller.seller_id), ('Seller Name', data.seller.name),
                         ('SKU Code', data.open_po.sku.sku_code), ('SKU Description', data.open_po.sku.sku_desc),
                         ('SKU Class', data.open_po.sku.sku_class), ('SKU Style Name', data.open_po.sku.style_name),
                         ('SKU Brand', data.open_po.sku.sku_brand), ('SKU Category', data.open_po.sku.sku_category),
                         ('Accepted Qty', accepted_quan), ('Rejected Qty', rejected_quan),
                         ('Total Qty', data.open_po.order_quantity), ('Amount', '%.2f' % amount),
                         ('Tax', data.open_po.tax), ('Total Amount', '%.2f' % total_amount),
                         ('DT_RowClass', 'results'), ('DT_RowAttr', {'data-id': data.id}))))

    if stop_index and custom_search:
        if temp_data['aaData']:
            temp_data['aaData'] = apply_search_sort(temp_data['aaData'][0].keys(), temp_data['aaData'], order_term, '',
                                                    col_num, exact=False)
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


def get_grn_inventory_addition_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master, get_local_date, apply_search_sort
    sku_master, sku_master_ids = get_sku_master(user, sub_user)

    search_parameters = {}
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    temp_data = copy.deepcopy(AJAX_DATA)
    temp_data['draw'] = search_params.get('draw')
    result_values = ['purchase_order__order_id', 'receipt_number', 'purchase_order__open_po__sku__sku_code',
                     'seller_po__seller__seller_id',
                     'purchase_order__received_quantity', 'purchase_order__open_po__price',
                     'purchase_order__open_po__sgst_tax',
                     'purchase_order__open_po__cgst_tax', 'purchase_order__open_po__igst_tax',
                     'purchase_order__open_po__utgst_tax',
                     'seller_po__margin_percent', 'purchase_order__prefix', 'seller_po__unit_price']

    if 'from_date' in search_params:
        search_parameters['creation_date__gte'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lte'] = search_params['to_date']

    if 'open_po' in search_params and search_params['open_po']:
        temp = re.findall('\d+', search_params['open_po'])
        if temp:
            search_parameters['purchase_order__order_id'] = temp[-1]

    if 'sku_code' in search_params:
        search_parameters['seller_po__open_po__sku__wms_code'] = search_params['sku_code']

    search_parameters['seller_po__seller__user'] = user.id
    search_parameters['seller_po__open_po__sku_id__in'] = sku_master_ids
    damaged_ids = SellerStock.objects.filter(stock__location__zone__zone='DAMAGED_ZONE', seller__user=user.id,
                                             seller_po_summary__isnull=False). \
        values_list('seller_po_summary_id', flat=True)
    query_data = SellerPOSummary.objects.filter(**search_parameters).exclude(id__in=damaged_ids)
    model_data = query_data.values(*result_values).distinct().annotate(total_received=Sum('quantity'))

    temp_data['recordsTotal'] = model_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    purchase_orders = PurchaseOrder.objects.filter(open_po__sku__user=user.id)
    for data in model_data:
        result = purchase_orders.filter(order_id=data['purchase_order__order_id'], open_po__sku__user=user.id)[0]
        po_number = '%s%s_%s' % (
        data['purchase_order__prefix'], str(result.creation_date).split(' ')[0].replace('-', ''),
        data['purchase_order__order_id'])
        amount = float(data['total_received'] * data['purchase_order__open_po__price'])
        tax = float(data['purchase_order__open_po__sgst_tax']) + float(
            data['purchase_order__open_po__cgst_tax']) + float(data['purchase_order__open_po__igst_tax']) + float(
            data['purchase_order__open_po__utgst_tax'])
        aft_unit_price = float(data['purchase_order__open_po__price']) + (
        float(data['purchase_order__open_po__price'] / 100) * tax)
        post_amount = aft_unit_price * float(data['total_received'])
        margin_price = float(data['seller_po__unit_price'] - aft_unit_price)
        if margin_price < 0:
            margin_price = 0
        margin_price = "%.2f" % (margin_price * float(data['total_received']))
        final_price = data['seller_po__unit_price']
        if not final_price:
            final_price = aft_unit_price
        invoice_total_amount = float(final_price) * float(data['total_received'])
        sku_code = data['purchase_order__open_po__sku__sku_code']
        temp_data['aaData'].append(
            OrderedDict((('Transaction ID', po_number + '-' + str(sku_code) + '/' + str(data['receipt_number'])),
                         ('Product Code', sku_code),
                         ('Seller ID', data['seller_po__seller__seller_id']),
                         ('Quantity', data['total_received']),
                         ('Price', invoice_total_amount), ('Type', 'ADD'),
                         )))
    return temp_data


def get_returns_addition_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master, get_local_date, apply_search_sort, get_dictionary_query
    sku_master, sku_master_ids = get_sku_master(user, sub_user)

    search_parameters = {}
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    temp_data = copy.deepcopy(AJAX_DATA)
    temp_data['draw'] = search_params.get('draw')
    result_values = ['return_id', 'sku__sku_code', 'return_type']

    query_filter = {}
    if 'creation_date' in search_params and search_params['creation_date']:
        search_parameters['creation_date__gte'] = search_params['creation_date']
        to_date = datetime.datetime.combine(search_params['creation_date'] + datetime.timedelta(1), datetime.time())
        search_parameters['creation_date__lte'] = to_date

    if 'sku_code' in search_params and search_params['sku_code']:
        search_parameters['sku__sku_code'] = search_params['sku_code']

    if 'wms_code' in search_params and search_params['wms_code']:
        search_parameters['sku__wms_code'] = search_params['wms_code']
    if 'order_id' in search_params and search_params['order_id']:
        order_id = re.findall('\d+', search_params['order_id'])
        search_parameters['order__order_id'] = ''.join(order_id)
    if 'marketplace' in search_params and search_params['marketplace']:
        query_filter['marketplace'] = search_params['marketplace']
        query_filter['order__marketplace'] = search_params['marketplace']

    search_parameters['sku__user'] = user.id
    search_parameters['sku_id__in'] = sku_master_ids
    query_data = OrderReturns.objects.filter(get_dictionary_query(query_filter), quantity__gt=0, **search_parameters)
    model_data = query_data.values(*result_values).distinct().annotate(total_received=Sum('quantity'))

    temp_data['recordsTotal'] = model_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    order_returns = OrderReturns.objects.filter(sku__user=user.id)
    for data in model_data:
        sku_code = data['sku__sku_code']
        return_id = data['return_id']
        seller_id = ''
        order_return = order_returns.filter(return_id=data['return_id'], sku__sku_code=data['sku__sku_code'])
        invoice_amount = 0
        date_str = order_return[0].return_date.strftime('%d/%m/%H/%M')
        transaction_id = ('%s-%s-%s-%s') % (return_id, str(sku_code), str(order_return[0].return_type[:3]), date_str)
        if order_return and order_return[0].seller_order:
            seller_order = order_return[0].seller_order
            seller_id = seller_order.seller.seller_id
            order = order_return[0].seller_order.order
            invoice_amount = (order.invoice_amount / order.quantity) * data['total_received']
            transaction_id = ('%s-%s-%s') % (str(order.order_id), str(seller_order.sor_id), transaction_id)
        elif order_return and order_return[0].order:
            order = order_return[0].order
            invoice_amount = (order.invoice_amount / order.quantity) * data['total_received']
            transaction_id = ('%s-%s') % (str(order.order_id), transaction_id)
        temp_data['aaData'].append(OrderedDict((('Transaction ID', transaction_id),
                                                ('Product Code', sku_code),
                                                ('Seller ID', seller_id),
                                                ('Quantity', data['total_received']),
                                                ('Price', invoice_amount), ('Type', 'ADD'),
                                                )))
    return temp_data


def get_seller_stock_summary_replace(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master, get_local_date, apply_search_sort, get_seller_reserved_stocks
    sku_master, sku_master_ids = get_sku_master(user, sub_user)

    search_parameters = {}
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    temp_data = copy.deepcopy(AJAX_DATA)
    temp_data['draw'] = search_params.get('draw')

    if 'seller_id' in search_params:
        search_parameters['seller__seller_id'] = search_params['seller_id']

    search_parameters['seller__user'] = user.id
    search_parameters['stock__sku_id__in'] = sku_master_ids
    query_data = SellerStock.objects.filter(**search_parameters).exclude(stock__location__zone__zone='DAMAGED_ZONE')
    model_data = query_data.values('seller__seller_id', 'stock__sku__sku_code').distinct().annotate(
        total_received=Sum('quantity'))

    dis_seller_ids = query_data.values_list('seller__seller_id', flat=True).distinct()
    sell_stock_ids = query_data.values('seller__seller_id', 'stock_id')
    reserved_dict, raw_reserved_dict = get_seller_reserved_stocks(dis_seller_ids, sell_stock_ids, user)

    temp_data['recordsTotal'] = model_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    for data in model_data:
        reserved = 0
        current_time = get_local_date(user, datetime.datetime.now(), send_date=True)
        date_time = current_time.strftime('%Y%m%d_%H%M')
        if data['seller__seller_id'] in reserved_dict.keys():
            if data['stock__sku__sku_code'] in reserved_dict[data['seller__seller_id']].keys():
                reserved = reserved_dict[data['seller__seller_id']][data['stock__sku__sku_code']]
        if data['seller__seller_id'] in raw_reserved_dict.keys():
            if data['stock__sku__sku_code'] in raw_reserved_dict[data['seller__seller_id']].keys():
                reserved += raw_reserved_dict[data['seller__seller_id']][data['stock__sku__sku_code']]
        quantity = data['total_received'] - reserved
        if quantity < 0:
            quantity = 0
        sku_code = str(data['stock__sku__sku_code'])
        transaction_id = 'REPLACE_%s_%s_%s' % (str(data['seller__seller_id']), sku_code, date_time)
        temp_data['aaData'].append(OrderedDict((('Transaction ID', transaction_id),
                                                ('Product Code', sku_code),
                                                ('Seller ID', data['seller__seller_id']),
                                                ('Quantity', quantity),
                                                ('Price', 0), ('Type', 'REPLACE'),
                                                )))
    return temp_data


from oauth2_provider.decorators import protected_resource
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse


@csrf_exempt
@protected_resource()
def test_sam(request):
    return JsonResponse({'data': 'Data', 'status': 'Success'})


@csrf_exempt
def demo_fun(request):
    status = {'code': '', 'status': ''}
    try:
        obj = test_sam(request)
        status.update({'code': obj.status_code, 'status': obj.reason_phrase})
    except:
        print "Error Message"

    return JsonResponse(status)


def get_rm_picklist_data(search_params, user, sub_user):
    from rest_api.views.common import get_local_date
    from django.db.models import F
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    status_filter = {}
    all_data = OrderedDict()
    lis = {}
    rm_picklist = RMLocation.objects.filter(material_picklist__jo_material__material_code__user=user.id)
    if 'from_date' in search_params:
        status_filter['material_picklist__jo_material__job_order__creation_date__gte'] = datetime.datetime.combine(
            search_params['from_date'], datetime.time())
    if 'to_date' in search_params:
        status_filter['material_picklist__jo_material__job_order__creation_date__lte'] = datetime.datetime.combine(
            search_params['to_date'] + datetime.timedelta(1), datetime.time())
    if 'job_order_code' in search_params:
        status_filter['material_picklist__jo_material__job_order__job_code__iexact'] = search_params['job_order_code']
    if 'fg_sku_code' in search_params:
        status_filter['material_picklist__jo_material__job_order__product_code__sku_code__iexact'] = search_params[
            'fg_sku_code']
    if 'rm_sku_code' in search_params:
        status_filter['material_picklist__jo_material__material_code__sku_code__iexact'] = search_params['rm_sku_code']
    if 'location' in search_params:
        if search_params['location'] == 'NO STOCK':
            status_filter['stock__isnull'] = True
        else:
            status_filter['stock__location__location__iexact'] = search_params['location']
    if 'pallet' in search_params:
        status_filter['stock__pallet_detail__pallet_code__iexact'] = search_params['pallet']
    lis = [
        'material_picklist__jo_material__job_order__job_code',
        'material_picklist__jo_material__job_order__creation_date',
        'material_picklist__jo_material__job_order__product_code__sku_code',
        'material_picklist__jo_material__material_code__sku_code',
        'stock__location__location',
        'stock__pallet_detail__pallet_code',
        'mod_quantity',
        'updation_date'
    ]
    if len(status_filter):
        rm_picklist = rm_picklist.filter(**status_filter)
    rm_picklist = rm_picklist.annotate(mod_quantity=F('quantity') - F('reserved'))
    rm_picklist = rm_picklist.filter(mod_quantity__gt=0)
    if search_params.get('order_term'):
        order_data = lis[search_params['order_index']]
        if search_params['order_term'] == 'desc':
            order_data = "-%s" % order_data
        rm_picklist = rm_picklist.order_by(order_data)
    temp_data['recordsTotal'] = rm_picklist.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    data = []
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    if stop_index:
        rm_picklist = rm_picklist[start_index:stop_index]
    for obj in rm_picklist:
        location = 'NO STOCK'
        pallet_code = ''
        if obj.stock:
            location = obj.stock.location.location
            pallet_code = obj.stock.pallet_detail.pallet_code if obj.stock.pallet_detail else ''
        data.append(OrderedDict((('Jo Code', obj.material_picklist.jo_material.job_order.job_code),
                                 ('Jo Creation Date',
                                  get_local_date(user, obj.material_picklist.jo_material.job_order.creation_date)),
                                 ('FG SKU Code', obj.material_picklist.jo_material.job_order.product_code.sku_code),
                                 ('RM SKU Code', obj.material_picklist.jo_material.material_code.sku_code),
                                 ('Location', location), ('Pallet Code', pallet_code), ('Quantity', obj.mod_quantity),
                                 ('Processed Date', get_local_date(user, obj.updation_date)),)))
    temp_data['aaData'] = data
    return temp_data


def get_stock_ledger_data(search_params, user, sub_user):
    from rest_api.views.common import get_local_date
    from django.db.models import F
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    status_filter = {}
    all_data = OrderedDict()
    lis = {}
    stock_stats = StockStats.objects.filter(sku__user=user.id)
    if 'from_date' in search_params:
        status_filter['creation_date__gte'] = datetime.datetime.combine(
            search_params['from_date'], datetime.time())
    if 'to_date' in search_params:
        status_filter['creation_date__lte'] = datetime.datetime.combine(
            search_params['to_date'] + datetime.timedelta(1), datetime.time())
    if 'sku_code' in search_params:
        status_filter['sku__sku_code__iexact'] = search_params['sku_code']
    lis = [
            'creation_date', 'sku__sku_code', 'sku__sku_desc', 'sku__style_name', 'sku__sku_brand', 'sku__sku_category',
            'sku__sku_size', 'opening_stock', 'receipt_qty', 'produced_qty', 'dispatch_qty', 'return_qty',
            'adjustment_qty', 'closing_stock'
          ]
    if len(status_filter):
        stock_stats = stock_stats.filter(**status_filter)
    if search_params.get('order_term'):
        order_data = lis[search_params['order_index']]
        if search_params['order_term'] == 'desc':
            order_data = "-%s" % order_data
        stock_stats = stock_stats.order_by(order_data)
    temp_data['recordsTotal'] = stock_stats.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    data = []
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    if stop_index:
        stock_stats = stock_stats[start_index:stop_index]
    for obj in stock_stats:
        date = get_local_date(user, obj.creation_date, send_date=True).strftime('%d %b %Y')
        data.append(OrderedDict((('Date', date),
                                 ('SKU Code', obj.sku.sku_code), ('SKU Description', obj.sku.sku_desc),
                                 ('Style Name', obj.sku.style_name),
                                 ('Brand', obj.sku.sku_brand), ('Category', obj.sku.sku_category),
                                 ('Size', obj.sku.sku_size), ('Opening Stock', obj.opening_stock),
                                 ('Receipt Quantity', obj.receipt_qty + obj.uploaded_qty),
                                 ('Produced Quantity', obj.produced_qty),
                                 ('Dispatch Quantity', obj.dispatch_qty), ('Return Quantity', obj.return_qty),
                                 ('Consumed Quantity', obj.consumed_qty),
                                 ('Adjustment Quantity', obj.adjustment_qty), ('Closing Stock', obj.closing_stock)
                                 )))
    temp_data['aaData'] = data
    return temp_data


def get_rtv_report_data(search_params, user, sub_user, serial_view=False):
    from miebach_admin.models import *
    from miebach_admin.views import *
    from rest_api.views.common import get_sku_master, get_po_reference
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    search_parameters = {}
    lis = ['rtv_number', 'seller_po_summary__purchase_order__open_po__supplier_id',
           'seller_po_summary__purchase_order__open_po__supplier__name', 'seller_po_summary__purchase_order__order_id',
           'seller_po_summary__invoice_number', 'return_date']
    search_parameters['seller_po_summary__purchase_order__open_po__sku__user'] = user.id
    search_parameters['quantity__gt'] = 0
    search_parameters['seller_po_summary__purchase_order__open_po__sku_id__in'] = sku_master_ids
    search_parameters['status'] = 0
    temp_data = copy.deepcopy(AJAX_DATA)

    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lt'] = search_params['to_date']
    if 'supplier' in search_params:
        if search_params['supplier'] and ':' in search_params['supplier']:
            search_parameters['seller_po_summary__purchase_order__open_po__supplier__id__iexact'] = \
                                search_params['supplier'].split(':')[0]
    if 'open_po' in search_params and search_params['open_po']:
        temp = re.findall('\d+', search_params['open_po'])
        if temp:
            search_parameters['seller_po_summary__purchase_order__order_id'] = temp[-1]
    if 'invoice_number' in search_params:
        search_parameters['seller_po_summary__invoice_number'] = search_params['invoice_number']
    if 'rtv_number' in search_params:
        search_parameters['rtv_number'] = search_params['rtv_number']
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    model_data = ReturnToVendor.objects.filter(**search_parameters).\
                                    values('rtv_number', 'seller_po_summary__purchase_order__open_po__supplier_id',
           'seller_po_summary__purchase_order__open_po__supplier__name', 'seller_po_summary__purchase_order__order_id',
           'seller_po_summary__invoice_number').distinct().\
            annotate(return_date=Cast('creation_date', DateField()))

    if search_params.get('order_term'):
        order_data = lis[search_params['order_index']]
        if search_params['order_term'] == 'desc':
            order_data = "-%s" % order_data
        model_data = model_data.order_by(order_data)

    temp_data['recordsTotal'] = model_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    if stop_index:
        model_data = model_data[start_index:stop_index]

    for data in model_data:
        rtv = ReturnToVendor.objects.filter(seller_po_summary__purchase_order__open_po__sku__user=user.id, status=0,
                                            rtv_number=data['rtv_number'])
        order_id = get_po_reference(rtv[0].seller_po_summary.purchase_order)
        date = get_local_date(user, rtv[0].creation_date)
        temp_data['aaData'].append(OrderedDict((('RTV Number', data['rtv_number']),
                                    ('Supplier ID', data['seller_po_summary__purchase_order__open_po__supplier_id']),
                                    ('Supplier Name', data['seller_po_summary__purchase_order__open_po__supplier__name']),
                                    ('Order ID', order_id),
                                    ('Invoice Number', data['seller_po_summary__invoice_number']),
                                    ('Return Date', date)
                                )))
    return temp_data


def get_dist_sales_report_data(search_params, user, sub_user):
    """

        :param search_params:
        :param user:
        :param sub_user:
        :return:
        1. Fetch Orders placed by Distributor in Customer Portal.
        2. Orders of resellers which are placed to L1 WHS. (Excluding the orders placed to Direct distributors.)
    """
    from rest_api.views.outbound import get_same_level_warehouses
    from miebach_admin.models import OrderDetail
    search_parameters = {}
    lis = ['id', '', 'order_id', 'creation_date', 'sku__sku_category', 'sku__sku_code', 'quantity']
    if user.userprofile.warehouse_type != 'DIST':
        distributors = get_same_level_warehouses(2, user)
        if sub_user.userprofile.zone:
            zone_id = sub_user.userprofile.zone
            distributors = UserProfile.objects.filter(user__in=distributors,
                                                      zone__icontains=zone_id).values_list('user_id', flat=True)
    else:
        distributors = [user.id]
    zone_code = search_params.get('zone_code', '')
    if zone_code:
        distributors = UserProfile.objects.filter(user__in=distributors,
                                                  zone__icontains=zone_code).values_list('user_id', flat=True)
    dist_code = search_params.get('distributor_code', '')
    if dist_code:
        distributors = UserProfile.objects.filter(user__in=distributors,
                                                  user__first_name__icontains=dist_code).values_list('user_id', flat=True)
    dist_resellers_qs = CustomerMaster.objects.filter(user__in=distributors).\
        values_list('user', 'customerusermapping__customer')
    resellers = []
    res_dist_map = {}
    ord_res_map = {}
    for dist, res in dist_resellers_qs:
        res_dist_map[res] = dist
        resellers.append(res)
    dist_cust_ids_qs = WarehouseCustomerMapping.objects.filter(warehouse__in=distributors).values_list('customer_id',
                                                                                                       'warehouse_id')
    dist_cust_ids_map = dict(dist_cust_ids_qs)
    dist_customers = dist_cust_ids_map.keys()

    orderdetail_objs = dict(GenericOrderDetailMapping.objects.filter(customer_id__in=dist_customers).
                            values_list('orderdetail_id', 'customer_id'))
    orderdetail_ids = orderdetail_objs.keys()
    for reseller in resellers:
        dist = res_dist_map.get(reseller, '')
        if not dist:
            continue
        res_ord_objs = GenericOrderDetailMapping.objects.filter(customer_id=reseller).exclude(cust_wh_id=dist)
        res_orders = list(res_ord_objs.values_list('orderdetail_id', flat=True))
        for ord_id in res_orders:
            ord_res_map[ord_id] = reseller
        orderdetail_ids.extend(res_orders)
    search_parameters['id__in'] = orderdetail_ids
    search_parameters['quantity__gt'] = 0
    temp_data = copy.deepcopy(AJAX_DATA)
    zones_map = dict(UserProfile.objects.filter(user__in=distributors).values_list('user_id', 'zone'))
    names_map = dict(UserProfile.objects.filter(user__in=distributors).
                     values_list('user_id', Concat('user__username', Value(' - '), 'user__first_name')))

    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lt'] = search_params['to_date']
    if 'sku_code' in search_params:
        search_parameters['sku__sku_code'] = search_params['sku_code']
    if 'sku_category' in search_params:
        search_parameters['sku__sku_category__icontains'] = search_params['sku_category']
    if 'order_id' in search_params:
        order_id = search_params['order_id']
        order_id_search = ''.join(re.findall('\d+', order_id))
        order_code_search = ''.join(re.findall('\D+', order_id))
        order_detail_objs = OrderDetail.objects.filter(Q(order_id=order_id_search, order_code=order_code_search) |
                                                       Q(original_order_id=order_id), **search_parameters)
        if order_detail_objs:
            search_parameters['id__in'] = order_detail_objs.values_list('id', flat=True)
        else:
            search_parameters['id__in'] = []
    status_search = search_params.get('order_report_status', "")

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    order_qs = OrderDetail.objects.filter(**search_parameters)

    ##Orders Status Functionality
    pick_filters = {}
    for key, value in search_parameters.iteritems():
        pick_filters['order__%s' % key] = value
    order_id_status = dict(OrderDetail.objects.select_related('order_id', 'status').filter(**search_parameters). \
                           only('order_id', 'status').values_list('order_id', 'status').distinct())

    picklist_generated = Picklist.objects.select_related('order').filter(status__icontains='open', picked_quantity=0,
                                                                         **pick_filters).only(
        'order__order_id').values_list('order__order_id', flat=True).distinct()

    partially_picked = Picklist.objects.filter(status__icontains='open', picked_quantity__gt=0,
                                               reserved_quantity__gt=0, **pick_filters).values_list('order__order_id',
                                                                                                    flat=True).distinct()

    picked_orders = Picklist.objects.filter(status__icontains='picked', picked_quantity__gt=0,
                                            reserved_quantity=0, **pick_filters).values_list('order__order_id',
                                                                                             flat=True).distinct()
    _status = ""
    if status_search:
        # ['Open', 'Picklist generated', 'Partial Picklist generated', 'Picked', 'Partially picked']
        ord_ids = ""
        if status_search == 'Open':
            ord_ids = OrderDetail.objects.filter(status=1, **search_parameters). \
                values_list('order_id', flat=True).distinct()
        elif status_search == 'Picklist generated':
            ord_ids = picklist_generated
        elif status_search == 'Partial Picklist generated':
            ord_ids = partially_picked
        elif status_search == 'Picked':
            ord_ids = picked_orders

        order_qs = order_qs.filter(order_id__in=ord_ids)
        _status = status_search

    model_data = order_qs.values('id', 'order_code', 'user', 'creation_date', 'order_id',
                                 'original_order_id', 'sku__sku_code', 'sku__sku_category',
                                 'quantity', 'creation_date', 'status', 'unit_price', 'invoice_amount',
                                 'customerordersummary__sgst_tax', 'customerordersummary__igst_tax',
                                 'customerordersummary__cgst_tax', 'customerordersummary__utgst_tax')
    if search_params.get('order_term'):
        order_data = lis[search_params['order_index']]
        if search_params['order_term'] == 'desc':
            order_data = "-%s" % order_data
        model_data = model_data.order_by(order_data)

    temp_data['recordsTotal'] = model_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    status = ""
    totals_map = {}
    for data in model_data:
        order_id = data['order_id']
        org_order_id = data['original_order_id']
        if not org_order_id:
            org_order_id = data['order_code'] + str(data['order_id'])
        reseller_id = ord_res_map.get(data['id'], '')
        if not reseller_id:
            reseller_id = orderdetail_objs.get(data['id'], '')
        dist_id = res_dist_map.get(reseller_id, '')
        if not dist_id:
            dist_id = dist_cust_ids_map.get(reseller_id, '')
        dist_code = names_map.get(dist_id, '')
        prod_catg = data['sku__sku_category']
        net_amt = round(data['quantity'] * data['unit_price'], 2)
        zone_code = zones_map.get(dist_id, '')
        order_date = data['creation_date'].strftime("%d-%m-%Y")
        cgst_tax = data['customerordersummary__cgst_tax']
        sgst_tax = data['customerordersummary__sgst_tax']
        igst_tax = data['customerordersummary__igst_tax']
        utgst_tax = data['customerordersummary__utgst_tax']
        if not cgst_tax: cgst_tax = 0
        if not sgst_tax: sgst_tax = 0
        if not igst_tax: igst_tax = 0
        if not utgst_tax: utgst_tax = 0
        gst_rate = (cgst_tax + sgst_tax + igst_tax + utgst_tax)
        gross_amt = round(net_amt + (net_amt * gst_rate/100), 2)
        gst_value = round(gross_amt - net_amt, 2)

        if not _status:
            if order_id_status.get(order_id, '') == '1':
                status = ORDER_SUMMARY_REPORT_STATUS[0]
            elif order_id in picklist_generated:
                status = ORDER_SUMMARY_REPORT_STATUS[1]
            elif order_id in partially_picked:
                status = ORDER_SUMMARY_REPORT_STATUS[2]
            elif order_id in picked_orders:
                status = ORDER_SUMMARY_REPORT_STATUS[3]
            if order_id_status.get(order_id, '') == '2':
                status = ORDER_DETAIL_STATES.get(2, '')
            if order_id_status.get(order_id, '') == '5':
                status = ORDER_DETAIL_STATES.get(5, '')
        else:
            status = _status
        if 'Value Before Tax' not in totals_map:
            totals_map['Value Before Tax'] = net_amt
        else:
            totals_map['Value Before Tax'] += net_amt
        if 'Value After Tax' not in totals_map:
            totals_map['Value After Tax'] = gross_amt
        else:
            totals_map['Value After Tax'] += gross_amt
        if 'GST Value' not in totals_map:
            totals_map['GST Value'] = round(gst_value, 2)
        else:
            totals_map['GST Value'] += round(gst_value, 2)

        ord_dict = OrderedDict((('Zone Code', zone_code), ('Distributor Code', dist_code),
                                ('Order No', org_order_id),
                                ('Order Date', order_date),
                                ('Product Category', prod_catg),
                                ('SKU Code', data['sku__sku_code']),
                                ('SKU Quantity', data['quantity']),
                                ('SKU Price', data['unit_price']),
                                ('Value Before Tax', net_amt),
                                ('GST Rate', gst_rate),
                                ('GST Value', gst_value),
                                ('Value After Tax', gross_amt),
                                ('Order Status', status),
                                ('Id', data['id']),
                                ))
        temp_data['aaData'].append(ord_dict)
    for i, j in totals_map.items():
        totals_map[i] = get_currency_format(j)
    temp_data['totals'] = totals_map
    if stop_index:
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


def get_reseller_sales_report_data(search_params, user, sub_user):
    from rest_api.views.outbound import get_same_level_warehouses
    search_parameters = {}
    lis = ['id', '', '', 'client_name', 'orderdetail__order_id', 'creation_date', 'orderdetail__sku__sku_category',
           'orderdetail__sku__sku_code', 'orderdetail__quantity', 'orderdetail__sku__price']
    # distributors = get_same_level_warehouses(2, user)
    if user.userprofile.warehouse_type != 'DIST':
        distributors = get_same_level_warehouses(2, user)
        if sub_user.userprofile.zone:
            zone_id = sub_user.userprofile.zone
            distributors = UserProfile.objects.filter(user__in=distributors,
                                                      zone__icontains=zone_id).values_list('user_id', flat=True)
    else:
        distributors = [user.id]
    zone_code = search_params.get('zone_code', '')
    if zone_code:
        distributors = UserProfile.objects.filter(user__in=distributors,
                                                  zone__icontains=zone_code).values_list('user_id', flat=True)
    dist_code = search_params.get('distributor_code', '')
    if dist_code:
        distributors = UserProfile.objects.filter(user__in=distributors,
                                                  user__first_name__icontains=dist_code).values_list('user_id', flat=True)
    search_parameters['quantity__gt'] = 0
    temp_data = copy.deepcopy(AJAX_DATA)
    zones_map = dict(UserProfile.objects.filter(user__in=distributors).values_list('user_id', 'zone'))
    dist_names_map = dict(UserProfile.objects.filter(user__in=distributors).
                          values_list('user_id', Concat('user__username', Value(' - '), 'user__first_name')))
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lt'] = search_params['to_date']
    if 'sku_code' in search_params:
        search_parameters['orderdetail__sku__sku_code'] = search_params['sku_code']
    if 'sku_category' in search_params:
        search_parameters['orderdetail__sku__sku_category__icontains'] = search_params['sku_category']
    if 'order_id' in search_params:
        order_id = search_params['order_id']
        order_id_search = ''.join(re.findall('\d+', order_id))
        order_code_search = ''.join(re.findall('\D+', order_id))
        order_detail_objs = OrderDetail.objects.filter(Q(order_id=order_id_search, order_code=order_code_search) |
                                                       Q(original_order_id=order_id), **search_parameters)
        if order_detail_objs:
            search_parameters['orderdetail__id__in'] = order_detail_objs.values_list('id', flat=True)
        else:
            search_parameters['orderdetail__id__in'] = []
    if 'reseller_code' in search_params:
        res_ids = CustomerMaster.objects.filter(name__contains=search_params['reseller_code']).\
            values_list('id', flat=True)
        search_parameters['customer_id__in'] = res_ids
    if 'corporate_name' in search_params:
        search_parameters['client_name__icontains'] = search_params['corporate_name']

    status_search = search_params.get('order_report_status', "")

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    search_parameters['cust_wh_id__in'] = distributors
    generic_order_qs = GenericOrderDetailMapping.objects.filter(**search_parameters)

    ##Orders Status Functionality
    orderdetail_ids = generic_order_qs.values_list('orderdetail_id', flat=True)
    order_id_status = dict(OrderDetail.objects.select_related('order_id', 'status').filter(id__in=orderdetail_ids). \
                           only('order_id', 'status').values_list('order_id', 'status').distinct())

    picklist_generated = Picklist.objects.select_related('order').filter(status__icontains='open',
                                                                         picked_quantity=0,
                                                                         order__id__in=orderdetail_ids).only(
        'order__order_id').values_list('order__order_id', flat=True).distinct()

    partially_picked = Picklist.objects.filter(status__icontains='open', picked_quantity__gt=0,
                                               reserved_quantity__gt=0, order__id__in=orderdetail_ids).values_list(
        'order__order_id',
        flat=True).distinct()

    picked_orders = Picklist.objects.filter(status__icontains='picked', picked_quantity__gt=0,
                                            reserved_quantity=0, order__id__in=orderdetail_ids).\
        values_list('order__order_id', flat=True).distinct()
    _status = ""
    if status_search:
        # ['Open', 'Picklist generated', 'Partial Picklist generated', 'Picked', 'Partially picked']
        ord_ids = ""
        if status_search == 'Open':
            ord_ids = OrderDetail.objects.filter(status=1, id__in=orderdetail_ids). \
                values_list('order_id', flat=True).distinct()
        elif status_search == 'Picklist generated':
            ord_ids = picklist_generated
        elif status_search == 'Partial Picklist generated':
            ord_ids = partially_picked
        elif status_search == 'Picked':
            ord_ids = picked_orders
        generic_order_qs = generic_order_qs.filter(orderdetail__order_id__in=ord_ids)
        _status = status_search

    model_data = generic_order_qs.values('generic_order_id', 'orderdetail__order_id', 'orderdetail__order_code',
                                         'cust_wh_id', 'creation_date', 'orderdetail__original_order_id',
                                         'orderdetail__sku__sku_code', 'orderdetail__sku__sku_category', 'quantity',
                                         'creation_date', 'orderdetail__status', 'unit_price',
                                         'orderdetail__invoice_amount', 'orderdetail__customerordersummary__sgst_tax',
                                         'orderdetail__customerordersummary__igst_tax',
                                         'orderdetail__customerordersummary__cgst_tax',
                                         'orderdetail__customerordersummary__utgst_tax',
                                         'client_name', 'customer_id', 'orderdetail_id'
                                         )
    customer_ids = generic_order_qs.values_list('customer_id', flat=True)
    cust_id_names_map = dict(CustomerUserMapping.objects.filter(customer_id__in=customer_ids).
                             values_list('customer_id', Concat('user__username', Value(' - '), 'customer__name')))
    if search_params.get('order_term'):
        order_data = lis[search_params['order_index']]
        if search_params['order_term'] == 'desc':
            order_data = "-%s" % order_data
        model_data = model_data.order_by(order_data)

    temp_data['recordsTotal'] = model_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    totals_map = {}
    for data in model_data:
        order_id = data['orderdetail__order_id']
        org_order_id = data['orderdetail__original_order_id']
        if not org_order_id:
            org_order_id = data['orderdetail__order_code'] + str(data['orderdetail__order_id'])
        dist_code = dist_names_map.get(data['cust_wh_id'], '')
        prod_catg = data['orderdetail__sku__sku_category']
        net_amt = round(data['quantity'] * data['unit_price'], 2)
        zone_code = zones_map.get(data['cust_wh_id'], '')
        order_date = data['creation_date'].strftime("%d-%m-%Y")
        reseller_code = cust_id_names_map[data['customer_id']]
        corp_name = data['client_name']
        cgst_tax = data['orderdetail__customerordersummary__cgst_tax'] or 0
        sgst_tax = data['orderdetail__customerordersummary__sgst_tax'] or 0
        igst_tax = data['orderdetail__customerordersummary__igst_tax'] or 0
        utgst_tax = data['orderdetail__customerordersummary__utgst_tax'] or 0
        gst_rate = (cgst_tax + sgst_tax + igst_tax + utgst_tax)
        gross_amt = round(net_amt + (net_amt * gst_rate / 100), 2)
        gst_value = round(gross_amt - net_amt, 2)
        if not _status:
            if order_id_status.get(order_id, '') == '1':
                status = ORDER_SUMMARY_REPORT_STATUS[0]
            elif order_id in picklist_generated:
                status = ORDER_SUMMARY_REPORT_STATUS[1]
            elif order_id in partially_picked:
                status = ORDER_SUMMARY_REPORT_STATUS[2]
            elif order_id in picked_orders:
                status = ORDER_SUMMARY_REPORT_STATUS[3]
            if order_id_status.get(order_id, '') == '2':
                status = ORDER_DETAIL_STATES.get(2, '')
            if order_id_status.get(order_id, '') == '5':
                status = ORDER_DETAIL_STATES.get(5, '')
        else:
            status = _status
        if 'Value Before Tax' not in totals_map:
            totals_map['Value Before Tax'] = net_amt
        else:
            totals_map['Value Before Tax'] += net_amt
        if 'Value After Tax' not in totals_map:
            totals_map['Value After Tax'] = gross_amt
        else:
            totals_map['Value After Tax'] += gross_amt
        if 'GST Value' not in totals_map:
            totals_map['GST Value'] = round(gst_value, 2)
        else:
            totals_map['GST Value'] += round(gst_value, 2)
        temp_data['aaData'].append(OrderedDict((('Zone Code', zone_code), ('Distributor Code', dist_code),
                                                ('Reseller Code', reseller_code),
                                                ('Corporate Name', corp_name),
                                                ('Order No', org_order_id), ('Product Category', prod_catg),
                                                ('Order Date', order_date),
                                                ('SKU Code', data['orderdetail__sku__sku_code']),
                                                ('SKU Quantity', data['quantity']),
                                                ('SKU Price', data['unit_price']),
                                                ('Value Before Tax', net_amt),
                                                ('GST Rate', gst_rate),
                                                ('GST Value', gst_value),
                                                ('Value After Tax', gross_amt),
                                                ('Order Status', status),
                                                )))
    for i, j in totals_map.items():
        totals_map[i] = get_currency_format(j)
    temp_data['totals'] = totals_map
    if stop_index:
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


def get_zone_target_summary_report_data(search_params, user, sub_user):
    from rest_api.views.outbound import get_same_level_warehouses
    from miebach_admin.models import OrderDetail
    search_parameters = {}
    lis = ['id', 'user']
    distributors = get_same_level_warehouses(2, user)
    if sub_user.userprofile.zone:
        zone_id = sub_user.userprofile.zone
        distributors = UserProfile.objects.filter(user__in=distributors,
                                                  zone__icontains=zone_id).values_list('user_id', flat=True)
    zone_code = search_params.get('zone_code', '')
    if zone_code:
        distributors = UserProfile.objects.filter(user__in=distributors, zone=zone_code).values_list('user_id',
                                                                                                     flat=True)
    dist_code = search_params.get('distributor_code', '')
    if dist_code:
        distributors = UserProfile.objects.filter(user__in=distributors,
                                                  user__first_name__icontains=dist_code).values_list('user_id', flat=True)
    dist_resellers_qs = CustomerMaster.objects.filter(user__in=distributors). \
        values_list('user', 'customerusermapping__customer')
    resellers = []
    res_dist_map = {}
    ord_res_map = {}
    for dist, res in dist_resellers_qs:
        res_dist_map[res] = dist
        resellers.append(res)
    dist_cust_ids_qs = WarehouseCustomerMapping.objects.filter(warehouse__in=distributors).values_list('warehouse_id',
                                                                                                       'customer_id')
    dist_cust_ids_map = dict(dist_cust_ids_qs)
    dist_customers = dist_cust_ids_map.values()
    if 'reseller_code' in search_params:
        res_ids = CustomerMaster.objects.filter(name__contains=search_params['reseller_code']).\
            values_list('id', flat=True)
        search_parameters['customer_id__in'] = res_ids
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lt'] = search_params['to_date']
    days_range = 0
    if search_params.get('from_date', '') and search_params.get('to_date', ''):
        from_date = search_params['from_date']
        to_date = search_params['to_date']
        days_range = (to_date - from_date).days
    orderdetail_objs = GenericOrderDetailMapping.objects.filter(customer_id__in=dist_customers)
    orderdetail_ids = list(orderdetail_objs.values_list('orderdetail_id', flat=True))
    for reseller in resellers:
        dist = res_dist_map.get(reseller, '')
        if not dist:
            continue
        res_ord_objs = GenericOrderDetailMapping.objects.filter(customer_id=reseller).exclude(cust_wh_id=dist)
        res_orders = list(res_ord_objs.values_list('orderdetail_id', flat=True))
        for ord_id in res_orders:
            ord_res_map[ord_id] = reseller
        orderdetail_ids.extend(res_orders)
    search_parameters['id__in'] = orderdetail_ids
    search_parameters['quantity__gt'] = 0
    temp_data = copy.deepcopy(AJAX_DATA)
    zones_map = dict(UserProfile.objects.filter(user__in=distributors).values_list('user__username', 'zone'))
    names_map = dict(UserProfile.objects.filter(user__in=distributors).values_list('user_id', 'user__username'))
    target_qs = TargetMaster.objects.filter(distributor__in=distributors)
    zone_targets = dict(target_qs.values_list('distributor__userprofile__zone').annotate(Sum('target_amt')))
    order_qs = OrderDetail.objects.filter(**search_parameters)
    model_data = order_qs.values('id', 'user', 'quantity', 'unit_price', 'invoice_amount')
    dist_totals_map = {}
    for data in model_data:
        reseller_id = ord_res_map.get(data['id'], '')
        if not reseller_id:
            try:
                reseller_id = orderdetail_objs.get(data['id'], '')
            except:
                continue
        dist_id = res_dist_map.get(reseller_id, '')
        if not dist_id:
            dist_id = dist_cust_ids_map.get(reseller_id, '')
        dist_code = names_map.get(dist_id, '')
        net_amt = round(data['quantity'] * data['unit_price'], 2)
        gross_amt = round(data['invoice_amount'], 2)
        if dist_code not in dist_totals_map:
            dist_totals_map[dist_code] = {"net_amt": net_amt, "gross_amt": gross_amt}
        else:
            dist_totals_map[dist_code]["net_amt"] += net_amt
            dist_totals_map[dist_code]["gross_amt"] += gross_amt
    achieved_map = {}
    for dist_code, achieved_data in dist_totals_map.items():
        if dist_code in zones_map.keys():
            zone = zones_map.get(dist_code, '')
            if zone not in achieved_map:
                achieved_map[zone] = achieved_data
            else:
                achieved_map[zone]["net_amt"] += achieved_data["net_amt"]
                achieved_map[zone]["gross_amt"] += achieved_data["gross_amt"]

    temp_data['recordsTotal'] = len(zone_targets)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    todays_date = datetime.datetime.today()
    current_year = todays_date.year
    start_date = datetime.datetime.strptime('Apr-1-%s' % current_year, '%b-%d-%Y')
    days_passed = (todays_date - start_date).days
    totals_map = {}
    for zone_code, target in zone_targets.items():
        ytd_target = round((target/365) * days_passed, 2)
        zone_net_amt = achieved_map.get(zone_code, '')
        if zone_net_amt:
            ytd_act_sale = round(zone_net_amt["net_amt"], 2)
        else:
            ytd_act_sale = 0
        exc_short = ((ytd_act_sale - ytd_target)/ytd_target) * 100
        excess_shortfall = round(exc_short, 2)
        if 'Zone Target' not in totals_map:
            totals_map['Zone Target'] = target
        else:
            totals_map['Zone Target'] += target
        if 'YTD Targets' not in totals_map:
            totals_map['YTD Targets'] = ytd_target
        else:
            totals_map['YTD Targets'] += ytd_target
        if 'YTD Actual Sale' not in totals_map:
            totals_map['YTD Actual Sale'] = round(ytd_act_sale, 2)
        else:
            totals_map['YTD Actual Sale'] += round(ytd_act_sale, 2)
        if days_range:
            target = round(target/365 * days_range, 2)
        ord_dict = OrderedDict((('Zone Code', zone_code),
                                ('Zone Target', target),
                                ('YTD Targets', ytd_target),
                                ('YTD Actual Sale', ytd_act_sale),
                                ('Excess / Shortfall %', excess_shortfall),
                                ))
        temp_data['aaData'].append(ord_dict)
    for i, j in totals_map.items():
        totals_map[i] = get_currency_format(j)
    temp_data['totals'] = totals_map
    return temp_data


def get_zone_target_detailed_report_data(search_params, user, sub_user):
    from rest_api.views.outbound import get_same_level_warehouses
    search_parameters = {}
    date_filters = {}
    lis = ['id', 'user']
    distributors = get_same_level_warehouses(2, user)
    if sub_user.userprofile.zone:
        zone_id = sub_user.userprofile.zone
        distributors = UserProfile.objects.filter(user__in=distributors,
                                                  zone__icontains=zone_id).values_list('user_id', flat=True)
    zone_code = search_params.get('zone_code', '')
    if zone_code:
        distributors = UserProfile.objects.filter(user__in=distributors, zone=zone_code).values_list('user_id',
                                                                                                     flat=True)
    dist_code = search_params.get('distributor_code', '')
    if dist_code:
        distributors = UserProfile.objects.filter(user__in=distributors,
                                                  user__first_name__icontains=dist_code).values_list('user_id', flat=True)
    dist_resellers_qs = CustomerMaster.objects.filter(user__in=distributors). \
        values_list('user', 'customerusermapping__customer')
    resellers = []
    res_dist_map = {}
    ord_res_map = {}
    for dist, res in dist_resellers_qs:
        res_dist_map[res] = dist
        resellers.append(res)
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gt'] = search_params['from_date']
        date_filters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lt'] = search_params['to_date']
        date_filters['creation_date__lt'] = search_params['to_date']
    days_range = 0
    if search_params.get('from_date', '') and search_params.get('to_date', ''):
        from_date = search_params['from_date']
        to_date = search_params['to_date']
        days_range = (to_date - from_date).days
    # if 'reseller_code' in search_params:
    #     res_ids = CustomerMaster.objects.filter(name__contains=search_params['reseller_code']).\
    #         values_list('id', flat=True)
    #     search_parameters['customer_id__in'] = res_ids
    dist_cust_ids_qs = WarehouseCustomerMapping.objects.filter(warehouse__in=distributors).values_list('warehouse_id',
                                                                                                       'customer_id')
    dist_cust_ids_map = dict(dist_cust_ids_qs)
    dist_customers = dist_cust_ids_map.values()
    orderdetail_objs = GenericOrderDetailMapping.objects.filter(customer_id__in=dist_customers)
    orderdetail_ids = list(orderdetail_objs.values_list('orderdetail_id', flat=True))
    for reseller in resellers:
        dist = res_dist_map.get(reseller, '')
        if not dist:
            continue
        res_ord_objs = GenericOrderDetailMapping.objects.filter(customer_id=reseller).exclude(cust_wh_id=dist)
        res_orders = list(res_ord_objs.values_list('orderdetail_id', flat=True))
        for ord_id in res_orders:
            ord_res_map[ord_id] = reseller
        orderdetail_ids.extend(res_orders)
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    search_parameters['id__in'] = orderdetail_ids
    search_parameters['quantity__gt'] = 0
    temp_data = copy.deepcopy(AJAX_DATA)
    tgt_filters = {'distributor__in': distributors}
    if 'reseller_code' in search_params:
        res_qs = CustomerUserMapping.objects.filter(customer__name__icontains=search_params['reseller_code'])
        tgt_filters['reseller__id__in'] = res_qs.values_list('user__id', flat=True)
    if 'corporate_name' in search_params:
        corp_qs = CorporateMaster.objects.filter(name__icontains=search_params['corporate_name'])
        corp_ids = corp_qs.values_list('id', flat=True)
        tgt_filters['corporate_id__in'] = corp_ids
    target_qs = TargetMaster.objects.filter(**tgt_filters)
    # target_qs = TargetMaster.objects.filter(distributor__in=distributors)
    zone_targets = dict(target_qs.values_list('distributor__userprofile__zone').annotate(Sum('target_amt')))
    dist_targets = dict(target_qs.values_list('distributor__username').annotate(Sum('target_amt')))
    res_targets = dict(target_qs.values_list('reseller__username').annotate(Sum('target_amt')))
    target_vals = target_qs.values('distributor__userprofile__zone', 'distributor__username', 'distributor__first_name',
                                   'reseller__username', 'reseller__first_name',
                                   'corporate_id', 'target_amt', 'reseller_id')

    temp_data['recordsTotal'] = len(target_vals)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    todays_date = datetime.datetime.today()
    current_year = todays_date.year
    start_date = datetime.datetime.strptime('Apr-1-%s' % current_year, '%b-%d-%Y')
    days_passed = (todays_date - start_date).days

    totals_map = {}
    all_zones = set()
    all_dists = set()
    all_resellers = set()
    for target in target_vals:
        zone_code = target['distributor__userprofile__zone']
        zone_target = zone_targets[zone_code]
        dist_code = target['distributor__username']
        dist_target = dist_targets[dist_code]
        dist_name = dist_code + ' - ' + target['distributor__first_name']
        reseller_code = target['reseller__username']
        reseller_usr_id = target['reseller_id']
        reseller_name = reseller_code + ' - ' + target['reseller__first_name']
        res_target = res_targets[reseller_code]
        res_cm_id = CustomerUserMapping.objects.filter(user_id=reseller_usr_id)
        if res_cm_id:
            res_cm_id = res_cm_id[0].customer_id
        else:
            continue
        corp_id = target['corporate_id']
        corp_name = CorporateMaster.objects.get(id=corp_id).name
        achieved_tgt_obj = GenericOrderDetailMapping.objects.filter(customer_id=res_cm_id,
                                                                    client_name=corp_name).filter(**date_filters)
        if achieved_tgt_obj:
            achieved_tgt = achieved_tgt_obj.values('customer_id', 'client_name').\
                annotate(net_amt=Sum(F('unit_price')*F('quantity')))
            reached_tgt = achieved_tgt[0]["net_amt"]
        else:
            reached_tgt = 0
        corp_target = target['target_amt']
        ytd_target = round((corp_target / 365) * days_passed, 2)
        ytd_act_sale = round(reached_tgt, 2)
        exc_short = ((ytd_act_sale - ytd_target) / ytd_target) * 100
        excess_shortfall = round(exc_short, 2)
        if 'Zone Target' not in totals_map:
            totals_map['Zone Target'] = zone_target
        else:
            if zone_code not in all_zones:
                totals_map['Zone Target'] += zone_target
        if 'Distributor Target' not in totals_map:
            totals_map['Distributor Target'] = dist_target
        else:
            if dist_code not in all_dists:
                totals_map['Distributor Target'] += dist_target
        if 'Reseller Target' not in totals_map:
            totals_map['Reseller Target'] = res_target
        else:
            if reseller_code not in all_resellers:
                totals_map['Reseller Target'] += res_target
        if 'Corporate Target' not in totals_map:
            totals_map['Corporate Target'] = corp_target
        else:
            totals_map['Corporate Target'] += corp_target
        if 'YTD Targets' not in totals_map:
            totals_map['YTD Targets'] = ytd_target
        else:
            totals_map['YTD Targets'] += ytd_target
        if 'YTD Actual Sale' not in totals_map:
            totals_map['YTD Actual Sale'] = round(ytd_act_sale, 2)
        else:
            totals_map['YTD Actual Sale'] += round(ytd_act_sale, 2)
        all_zones.add(zone_code)
        all_dists.add(dist_code)
        all_resellers.add(reseller_code)
        if days_range:
            zone_target = round(zone_target/365 * days_range, 2)
            dist_target = round(dist_target/365 * days_range, 2)
            res_target = round(res_target/365 * days_range, 2)
            corp_target = round(corp_target/365 * days_range, 2)
        ord_dict = OrderedDict((('Zone Code', zone_code),
                                ('Zone Target', zone_target),
                                ('Distributor Code', dist_name),
                                ('Distributor Target', dist_target),
                                ('Reseller Code', reseller_name),
                                ('Reseller Target', res_target),
                                ('Corporate Name', corp_name),
                                ('Corporate Target', corp_target),
                                ('YTD Targets', ytd_target),
                                ('YTD Actual Sale', ytd_act_sale),
                                ('Excess / Shortfall %', excess_shortfall),
                                ))
        temp_data['aaData'].append(ord_dict)
    for i, j in totals_map.items():
        totals_map[i] = get_currency_format(j)
    temp_data['totals'] = totals_map
    if stop_index:
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


def get_dist_target_summary_report_data(search_params, user, sub_user):
    from rest_api.views.outbound import get_same_level_warehouses
    from miebach_admin.models import OrderDetail
    search_parameters = {}
    lis = ['id', 'user']
    # distributors = get_same_level_warehouses(2, user)
    if user.userprofile.warehouse_type != 'DIST':
        distributors = get_same_level_warehouses(2, user)
        if sub_user.userprofile.zone:
            zone_id = sub_user.userprofile.zone
            distributors = UserProfile.objects.filter(user__in=distributors,
                                                      zone__icontains=zone_id).values_list('user_id', flat=True)
    else:
        distributors = [user.id]
    zone_code = search_params.get('zone_code', '')
    if zone_code:
        distributors = UserProfile.objects.filter(user__in=distributors, zone=zone_code).values_list('user_id',
                                                                                                     flat=True)
    dist_code = search_params.get('distributor_code', '')
    if dist_code:
        distributors = UserProfile.objects.filter(user__in=distributors,
                                                  user__first_name__icontains=dist_code).values_list('user_id', flat=True)
    dist_resellers_qs = CustomerMaster.objects.filter(user__in=distributors). \
        values_list('user', 'customerusermapping__customer')
    resellers = []
    res_dist_map = {}
    ord_res_map = {}
    for dist, res in dist_resellers_qs:
        res_dist_map[res] = dist
        resellers.append(res)
    dist_cust_ids_qs = WarehouseCustomerMapping.objects.filter(warehouse__in=distributors).values_list('warehouse_id',
                                                                                                       'customer_id')
    dist_cust_ids_map = dict(dist_cust_ids_qs)
    dist_customers = dist_cust_ids_map.values()
    orderdetail_objs = GenericOrderDetailMapping.objects.filter(customer_id__in=dist_customers)
    orderdetail_ids = list(orderdetail_objs.values_list('orderdetail_id', flat=True))
    for reseller in resellers:
        dist = res_dist_map.get(reseller, '')
        if not dist:
            continue
        res_ord_objs = GenericOrderDetailMapping.objects.filter(customer_id=reseller).exclude(cust_wh_id=dist)
        res_orders = list(res_ord_objs.values_list('orderdetail_id', flat=True))
        for ord_id in res_orders:
            ord_res_map[ord_id] = reseller
        orderdetail_ids.extend(res_orders)
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lt'] = search_params['to_date']
    days_range = 0
    if search_params.get('from_date', '') and search_params.get('to_date', ''):
        from_date = search_params['from_date']
        to_date = search_params['to_date']
        days_range = (to_date - from_date).days
    if 'corporate_name' in search_params:
        corp_filtered_order_objs = GenericOrderDetailMapping.objects.\
            filter(client_name__icontains=search_params['corporate_name'], orderdetail_id__in=orderdetail_ids)
        orderdetail_ids = list(corp_filtered_order_objs.values_list('orderdetail_id', flat=True))
    search_parameters['id__in'] = orderdetail_ids
    search_parameters['quantity__gt'] = 0
    temp_data = copy.deepcopy(AJAX_DATA)
    names_map = dict(UserProfile.objects.filter(user__in=distributors).
                     values_list('user_id', Concat('user__username', Value(' - '), 'user__first_name')))
    target_qs = TargetMaster.objects.filter(distributor__in=distributors)
    dist_targets = dict(target_qs.values_list(Concat('distributor__username', Value(' - '), 'distributor__first_name')).annotate(Sum('target_amt')))
    order_qs = OrderDetail.objects.filter(**search_parameters)
    model_data = order_qs.values('id', 'user', 'quantity', 'unit_price', 'invoice_amount')
    tgt_totals_map = {}
    for data in model_data:
        reseller_id = ord_res_map.get(data['id'], '')
        if not reseller_id:
            try:
                reseller_id = orderdetail_objs.get(data['id'], '')
            except:
                continue
        dist_id = res_dist_map.get(reseller_id, '')
        if not dist_id:
            dist_id = dist_cust_ids_map.get(reseller_id, '')
        dist_code = names_map.get(dist_id, '')
        net_amt = round(data['quantity'] * data['unit_price'], 2)
        gross_amt = round(data['invoice_amount'], 2)
        if dist_code not in tgt_totals_map:
            tgt_totals_map[dist_code] = {"net_amt": net_amt, "gross_amt": gross_amt}
        else:
            tgt_totals_map[dist_code]["net_amt"] += net_amt
            tgt_totals_map[dist_code]["gross_amt"] += gross_amt
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    temp_data['recordsTotal'] = len(tgt_totals_map)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    todays_date = datetime.datetime.today()
    current_year = todays_date.year
    start_date = datetime.datetime.strptime('Apr-1-%s' % current_year, '%b-%d-%Y')
    days_passed = (todays_date - start_date).days
    totals_map = {}
    for dist_code, target in tgt_totals_map.items():
        dist_tgt = dist_targets.get(dist_code, '')
        if not dist_tgt:
            dist_tgt = 0
        ytd_target = round((dist_tgt / 365) * days_passed, 2)
        ytd_act_sale = round(target["net_amt"], 2)
        if ytd_target:
            exc_short = ((ytd_act_sale - ytd_target) / ytd_target) * 100
        else:
            exc_short = 0
        excess_shortfall = round(exc_short, 2)
        if 'Distributor Target' not in totals_map:
            totals_map['Distributor Target'] = dist_tgt
        else:
            totals_map['Distributor Target'] += dist_tgt
        if 'YTD Targets' not in totals_map:
            totals_map['YTD Targets'] = ytd_target
        else:
            totals_map['YTD Targets'] += ytd_target
        if 'YTD Actual Sale' not in totals_map:
            totals_map['YTD Actual Sale'] = round(ytd_act_sale, 2)
        else:
            totals_map['YTD Actual Sale'] += round(ytd_act_sale, 2)
        if days_range:
            dist_tgt = round(dist_tgt/365 * days_range, 2)
        ord_dict = OrderedDict((('Distributor Code', dist_code),
                                ('Distributor Target', dist_tgt),
                                ('YTD Targets', ytd_target),
                                ('YTD Actual Sale', ytd_act_sale),
                                ('Excess / Shortfall %', excess_shortfall),
                                ))
        temp_data['aaData'].append(ord_dict)
    for i, j in totals_map.items():
        totals_map[i] = get_currency_format(j)
    temp_data['totals'] = totals_map
    if stop_index:
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


def get_dist_target_detailed_report_data(search_params, user, sub_user):
    from rest_api.views.outbound import get_same_level_warehouses
    from miebach_admin.models import OrderDetail
    search_parameters = {}
    date_filters = {}
    lis = ['id', 'user']
    if user.userprofile.warehouse_type != 'DIST':
        distributors = get_same_level_warehouses(2, user)
        if sub_user.userprofile.zone:
            zone_id = sub_user.userprofile.zone
            distributors = UserProfile.objects.filter(user__in=distributors,
                                                      zone__icontains=zone_id).values_list('user_id', flat=True)
    else:
        distributors = [user.id]
    zone_code = search_params.get('zone_code', '')
    if zone_code:
        distributors = UserProfile.objects.filter(user__in=distributors, zone=zone_code).values_list('user_id',
                                                                                                     flat=True)
    dist_code = search_params.get('distributor_code', '')
    if dist_code:
        distributors = UserProfile.objects.filter(user__in=distributors,
                                                  user__first_name__icontains=dist_code).values_list('user_id', flat=True)
    dist_resellers_qs = CustomerMaster.objects.filter(user__in=distributors). \
        values_list('user', 'customerusermapping__customer')
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gt'] = search_params['from_date']
        date_filters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lt'] = search_params['to_date']
        date_filters['creation_date__lt'] = search_params['to_date']
    days_range = 0
    if search_params.get('from_date', '') and search_params.get('to_date', ''):
        from_date = search_params['from_date']
        to_date = search_params['to_date']
        days_range = (to_date - from_date).days
    resellers = []
    res_dist_map = {}
    ord_res_map = {}
    for dist, res in dist_resellers_qs:
        res_dist_map[res] = dist
        resellers.append(res)
    dist_cust_ids_qs = WarehouseCustomerMapping.objects.filter(warehouse__in=distributors).values_list('warehouse_id',
                                                                                                       'customer_id')
    dist_cust_ids_map = dict(dist_cust_ids_qs)
    dist_customers = dist_cust_ids_map.values()
    orderdetail_objs = GenericOrderDetailMapping.objects.filter(customer_id__in=dist_customers)
    orderdetail_ids = list(orderdetail_objs.values_list('orderdetail_id', flat=True))
    for reseller in resellers:
        dist = res_dist_map.get(reseller, '')
        if not dist:
            continue
        res_ord_objs = GenericOrderDetailMapping.objects.filter(customer_id=reseller).exclude(cust_wh_id=dist)
        res_orders = list(res_ord_objs.values_list('orderdetail_id', flat=True))
        for ord_id in res_orders:
            ord_res_map[ord_id] = reseller
        orderdetail_ids.extend(res_orders)
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    search_parameters['id__in'] = orderdetail_ids
    search_parameters['quantity__gt'] = 0
    temp_data = copy.deepcopy(AJAX_DATA)
    zones_map = dict(UserProfile.objects.filter(user__in=distributors).values_list('user__username', 'zone'))
    names_map = dict(UserProfile.objects.filter(user__in=distributors).
                     values_list('user_id', Concat('user__username', Value(' - '), 'user__first_name')))
    tgt_filters = {'distributor__in': distributors}
    if 'reseller_code' in search_params:
        res_qs = CustomerUserMapping.objects.filter(customer__name__icontains=search_params['reseller_code'])
        tgt_filters['reseller__id__in'] = res_qs.values_list('user__id', flat=True)
    if 'corporate_name' in search_params:
        corp_qs = CorporateMaster.objects.filter(name__icontains=search_params['corporate_name'])
        corp_ids = corp_qs.values_list('id', flat=True)
        tgt_filters['corporate_id__in'] = corp_ids
    target_qs = TargetMaster.objects.filter(**tgt_filters)
    dist_targets = dict(target_qs.values_list('distributor__username').annotate(Sum('target_amt')))
    res_targets = dict(target_qs.values_list('reseller__username').annotate(Sum('target_amt')))
    target_vals = target_qs.values('distributor__userprofile__zone', 'distributor__username', 'distributor__first_name',
                                   'reseller__username', 'reseller__first_name',
                                   'corporate_id', 'target_amt', 'reseller_id')
    order_qs = OrderDetail.objects.filter(**search_parameters)
    model_data = order_qs.values('id', 'user', 'quantity', 'unit_price', 'invoice_amount')
    totals_map = {}
    for data in model_data:
        reseller_id = ord_res_map.get(data['id'], '')
        if not reseller_id:
            try:
                reseller_id = orderdetail_objs.get(data['id'], '')
            except:
                continue
        dist_id = res_dist_map.get(reseller_id, '')
        if not dist_id:
            dist_id = dist_cust_ids_map.get(reseller_id, '')
        dist_code = names_map.get(dist_id, '')
        net_amt = round(data['quantity'] * data['unit_price'], 2)
        gross_amt = round(data['invoice_amount'], 2)
        if dist_code not in totals_map:
            totals_map[dist_code] = {"net_amt": net_amt, "gross_amt": gross_amt}
        else:
            totals_map[dist_code]["net_amt"] += net_amt
            totals_map[dist_code]["gross_amt"] += gross_amt
    achieved_map = {}
    for dist_code, achieved_data in totals_map.items():
        if dist_code in zones_map.keys():
            zone = zones_map.get(dist_code, '')
            if zone not in achieved_map:
                achieved_map[zone] = achieved_data
            else:
                achieved_map[zone]["net_amt"] += achieved_data["net_amt"]
                achieved_map[zone]["gross_amt"] += achieved_data["gross_amt"]

    temp_data['recordsTotal'] = len(target_vals)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    todays_date = datetime.datetime.today()
    current_year = todays_date.year
    start_date = datetime.datetime.strptime('Apr-1-%s' % current_year, '%b-%d-%Y')
    days_passed = (todays_date - start_date).days

    totals_map = {}
    all_dists = set()
    all_resellers = set()
    for target in target_vals:
        dist_code = target['distributor__username']
        dist_target = dist_targets[dist_code]
        dist_name = dist_code + ' - ' + target['distributor__first_name']
        reseller_code = target['reseller__username']
        reseller_usr_id = target['reseller_id']
        res_target = res_targets[reseller_code]
        reseller_name = reseller_code + ' - ' + target['reseller__first_name']
        res_cm_id = CustomerUserMapping.objects.filter(user_id=reseller_usr_id)
        if res_cm_id:
            res_cm_id = res_cm_id[0].customer_id
        else:
            print "No res_cm_id: ", target
        corp_id = target['corporate_id']
        corp_name = CorporateMaster.objects.get(id=corp_id).name
        corp_target = target['target_amt']
        ytd_target = round((corp_target / 365) * days_passed, 2)
        achieved_tgt_obj = GenericOrderDetailMapping.objects.filter(customer_id=res_cm_id,
                                                                    client_name=corp_name).filter(**date_filters)
        if achieved_tgt_obj:
            achieved_tgt = achieved_tgt_obj.values('customer_id', 'client_name'). \
                annotate(net_amt=Sum(F('unit_price') * F('quantity')))
            ytd_act_sale = round(achieved_tgt[0]["net_amt"], 2)
        else:
            ytd_act_sale = 0

        exc_short = ((ytd_act_sale - ytd_target) / ytd_target) * 100
        excess_shortfall = round(exc_short, 2)
        if 'Distributor Target' not in totals_map:
            totals_map['Distributor Target'] = dist_target
        else:
            if dist_code not in all_dists:
                totals_map['Distributor Target'] += dist_target
        if 'Reseller Target' not in totals_map:
            totals_map['Reseller Target'] = res_target
        else:
            if reseller_code not in all_resellers:
                totals_map['Reseller Target'] += res_target
        if 'Corporate Target' not in totals_map:
            totals_map['Corporate Target'] = corp_target
        else:
            totals_map['Corporate Target'] += corp_target
        if 'YTD Targets' not in totals_map:
            totals_map['YTD Targets'] = ytd_target
        else:
            totals_map['YTD Targets'] += ytd_target
        if 'YTD Actual Sale' not in totals_map:
            totals_map['YTD Actual Sale'] = round(ytd_act_sale, 2)
        else:
            totals_map['YTD Actual Sale'] += round(ytd_act_sale, 2)
        all_dists.add(dist_code)
        all_resellers.add(reseller_code)
        if days_range:
            dist_target = round(dist_target/365 * days_range, 2)
            res_target = round(res_target/365 * days_range, 2)
            corp_target = round(corp_target/365 * days_range, 2)
        ord_dict = OrderedDict((('Distributor Code', dist_name),
                                ('Distributor Target', dist_target),
                                ('Reseller Code', reseller_name),
                                ('Reseller Target', res_target),
                                ('Corporate Name', corp_name),
                                ('Corporate Target', corp_target),
                                ('YTD Targets', ytd_target),
                                ('YTD Actual Sale', ytd_act_sale),
                                ('Excess / Shortfall %', excess_shortfall),
                                ))
        temp_data['aaData'].append(ord_dict)
    for i, j in totals_map.items():
        totals_map[i] = get_currency_format(j)
    temp_data['totals'] = totals_map
    if stop_index:
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


def get_reseller_target_summary_report_data(search_params, user, sub_user):
    from rest_api.views.outbound import get_same_level_warehouses
    search_parameters = {}
    lis = ['id', 'user']
    if user.userprofile.warehouse_type != 'DIST':
        distributors = get_same_level_warehouses(2, user)
        if sub_user.userprofile.zone:
            zone_id = sub_user.userprofile.zone
            distributors = UserProfile.objects.filter(user__in=distributors,
                                                      zone__icontains=zone_id).values_list('user_id', flat=True)
    else:
        distributors = [user.id]
    zone_code = search_params.get('zone_code', '')
    if zone_code:
        distributors = UserProfile.objects.filter(user__in=distributors,
                                                  zone__icontains=zone_code).values_list('user_id', flat=True)
    dist_code = search_params.get('distributor_code', '')
    if dist_code:
        distributors = UserProfile.objects.filter(user__in=distributors,
                                                  user__first_name__icontains=dist_code).values_list('user_id', flat=True)
    search_parameters['cust_wh_id__in'] = distributors
    search_parameters['quantity__gt'] = 0
    temp_data = copy.deepcopy(AJAX_DATA)

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    model_data = GenericOrderDetailMapping.objects.filter(**search_parameters). \
        values('generic_order_id', 'orderdetail__order_id', 'orderdetail__order_code', 'cust_wh_id',
               'quantity', 'creation_date', 'orderdetail__status', 'unit_price', 'orderdetail__invoice_amount',
               'client_name', 'customer_id'
               )
    totals_map = {}
    resellers_qs = CustomerUserMapping.objects.filter(customer__user__in=distributors)
    resellers = resellers_qs.values_list('user_id', flat=True)
    resellers_names_map = dict(resellers_qs.values_list('customer_id', 'user__username'))
    tgt_filters = {'reseller__in': resellers}
    if 'reseller_code' in search_params:
        res_qs = CustomerUserMapping.objects.filter(customer__name__icontains=search_params['reseller_code'])
        tgt_filters['reseller__id__in'] = res_qs.values_list('user__id', flat=True)
    if 'corporate_name' in search_params:
        corp_qs = CorporateMaster.objects.filter(name__icontains=search_params['corporate_name'])
        corp_ids = corp_qs.values_list('id', flat=True)
        tgt_filters['corporate_id__in'] = corp_ids
    target_qs = TargetMaster.objects.filter(**tgt_filters)
    reseller_targets = dict(target_qs.values_list('reseller__username').annotate(Sum('target_amt')))
    resellers_names = dict(target_qs.values_list('reseller__username',
                                                 Concat('reseller__username', Value(' - '), 'reseller__first_name')))

    for data in model_data:
        customer_id = data['customer_id']
        reseller_code = resellers_names_map.get(customer_id, '')
        net_amt = round(data['quantity'] * data['unit_price'], 2)
        gross_amt = round(data['orderdetail__invoice_amount'], 2)
        if reseller_code not in totals_map:
            totals_map[reseller_code] = {"net_amt": net_amt, "gross_amt": gross_amt, "id": customer_id}
        else:
            totals_map[reseller_code]["net_amt"] += net_amt
            totals_map[reseller_code]["gross_amt"] += gross_amt

    temp_data['recordsTotal'] = len(reseller_targets)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    todays_date = datetime.datetime.today()
    current_year = todays_date.year
    start_date = datetime.datetime.strptime('Apr-1-%s' % current_year, '%b-%d-%Y')
    days_passed = (todays_date - start_date).days

    totals_map = {}
    for reseller_code, target in reseller_targets.items():
        achieved_tgt_map = totals_map.get(reseller_code, '')
        if not achieved_tgt_map:
            achieved_tgt = 0
        else:
            achieved_tgt = achieved_tgt_map["net_amt"]
        ytd_target = round((target / 365) * days_passed, 2)
        ytd_act_sale = round(achieved_tgt, 2)
        exc_short = ((ytd_act_sale - ytd_target) / ytd_target) * 100
        excess_shortfall = round(exc_short, 2)
        reseller_name = resellers_names.get(reseller_code, '')
        if not reseller_name:
            log.info('Reseller Name %s not present in %s' %(reseller_name, resellers_names))
            continue
        if 'Reseller Target' not in totals_map:
            totals_map['Reseller Target'] = target
        else:
            totals_map['Reseller Target'] += target
        if 'YTD Targets' not in totals_map:
            totals_map['YTD Targets'] = ytd_target
        else:
            totals_map['YTD Targets'] += ytd_target
        if 'YTD Actual Sale' not in totals_map:
            totals_map['YTD Actual Sale'] = round(ytd_act_sale, 2)
        else:
            totals_map['YTD Actual Sale'] += round(ytd_act_sale, 2)
        ord_dict = OrderedDict((('Reseller Code', reseller_name),
                                ('Reseller Target', target),
                                ('YTD Targets', ytd_target),
                                ('YTD Actual Sale', ytd_act_sale),
                                ('Excess / Shortfall %', excess_shortfall),
                                ))
        temp_data['aaData'].append(ord_dict)
    for i, j in totals_map.items():
        totals_map[i] = get_currency_format(j)
    temp_data['totals'] = totals_map
    if stop_index:
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


def get_reseller_target_detailed_report_data(search_params, user, sub_user):
    from rest_api.views.outbound import get_same_level_warehouses
    search_parameters = {}
    lis = ['id', 'user']
    if user.userprofile.warehouse_type != 'DIST':
        distributors = get_same_level_warehouses(2, user)
        if sub_user.userprofile.zone:
            zone_id = sub_user.userprofile.zone
            distributors = UserProfile.objects.filter(user__in=distributors,
                                                      zone__icontains=zone_id).values_list('user_id', flat=True)
    else:
        distributors = [user.id]
    search_parameters['quantity__gt'] = 0
    temp_data = copy.deepcopy(AJAX_DATA)

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    resellers_qs = CustomerUserMapping.objects.filter(customer__user__in=distributors)
    resellers = resellers_qs.values_list('user_id', flat=True)
    tgt_filters = {'reseller__in': resellers}
    if 'reseller_code' in search_params:
        res_qs = CustomerUserMapping.objects.filter(customer__name__iexact=search_params['reseller_code'])
        tgt_filters['reseller__id__in'] = res_qs.values_list('user__id', flat=True)
    if 'corporate_name' in search_params:
        corp_qs = CorporateMaster.objects.filter(name__iexact=search_params['corporate_name'])
        corp_ids = corp_qs.values_list('id', flat=True)
        tgt_filters['corporate_id__in'] = corp_ids
    target_qs = TargetMaster.objects.filter(**tgt_filters)
    res_targets = dict(target_qs.values_list('reseller__username').annotate(Sum('target_amt')))
    resellers_names = dict(target_qs.values_list('reseller__username',
                                                 Concat('reseller__username', Value(' - '), 'reseller__first_name')))
    target_vals = target_qs.values('reseller__username', 'corporate_id', 'target_amt', 'reseller_id')
    temp_data['recordsTotal'] = len(target_vals)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    todays_date = datetime.datetime.today()
    current_year = todays_date.year
    start_date = datetime.datetime.strptime('Apr-1-%s' % current_year, '%b-%d-%Y')
    days_passed = (todays_date - start_date).days


    totals_map = {}
    all_resellers = set()
    for target in target_vals:
        reseller_code = target['reseller__username']
        reseller_usr_id = target['reseller_id']
        res_target = res_targets[reseller_code]
        res_cm_id = CustomerUserMapping.objects.filter(user_id=reseller_usr_id)
        if res_cm_id:
            res_cm_id = res_cm_id[0].customer_id
        else:
            continue
        corp_id = target['corporate_id']
        corp_name = CorporateMaster.objects.get(id=corp_id).name
        corp_target = target['target_amt']
        ytd_target = round((corp_target / 365) * days_passed, 2)
        achieved_tgt_obj = GenericOrderDetailMapping.objects.filter(customer_id=res_cm_id, client_name=corp_name)
        if achieved_tgt_obj:
            achieved_tgt = achieved_tgt_obj.values('customer_id', 'client_name'). \
                annotate(net_amt=Sum(F('unit_price') * F('quantity')))
            ytd_act_sale = round(achieved_tgt[0]["net_amt"], 2)
        else:
            ytd_act_sale = 0

        exc_short = ((ytd_act_sale - ytd_target) / ytd_target) * 100
        excess_shortfall = round(exc_short, 2)
        reseller_name = resellers_names.get(reseller_code, '')
        if not reseller_name:
            log.info('Reseller Name %s not present in %s' % (reseller_name, resellers_names))
            continue
        if 'Reseller Target' not in totals_map:
            totals_map['Reseller Target'] = res_target
        else:
            if reseller_code not in all_resellers:
                totals_map['Reseller Target'] += res_target
        if 'Corporate Target' not in totals_map:
            totals_map['Corporate Target'] = corp_target
        else:
            totals_map['Corporate Target'] += corp_target
        if 'YTD Targets' not in totals_map:
            totals_map['YTD Targets'] = ytd_target
        else:
            totals_map['YTD Targets'] += ytd_target
        if 'YTD Actual Sale' not in totals_map:
            totals_map['YTD Actual Sale'] = round(ytd_act_sale, 2)
        else:
            totals_map['YTD Actual Sale'] += round(ytd_act_sale, 2)
        all_resellers.add(reseller_code)

        ord_dict = OrderedDict((('Reseller Code', reseller_name),
                                ('Reseller Target', res_target),
                                ('Corporate Name', corp_name),
                                ('Corporate Target', corp_target),
                                ('YTD Targets', ytd_target),
                                ('YTD Actual Sale', ytd_act_sale),
                                ('Excess / Shortfall %', excess_shortfall),
                                ))
        temp_data['aaData'].append(ord_dict)
    for i, j in totals_map.items():
        totals_map[i] = get_currency_format(j)
    temp_data['totals'] = totals_map
    if stop_index:
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


def get_corporate_target_report_data(search_params, user, sub_user):
    from rest_api.views.outbound import get_same_level_warehouses
    search_parameters = {}
    lis = ['id', 'user']
    if user.userprofile.warehouse_type != 'DIST':
        distributors = get_same_level_warehouses(2, user)
        if sub_user.userprofile.zone:
            zone_id = sub_user.userprofile.zone
            distributors = UserProfile.objects.filter(user__in=distributors,
                                                      zone__icontains=zone_id).values_list('user_id', flat=True)
    else:
        distributors = [user.id]
    search_parameters['quantity__gt'] = 0
    temp_data = copy.deepcopy(AJAX_DATA)

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    resellers_qs = CustomerUserMapping.objects.filter(customer__user__in=distributors)
    resellers = resellers_qs.values_list('user_id', flat=True)
    tgt_filters = {'reseller__in': resellers}
    if 'corporate_name' in search_params:
        corp_qs = CorporateMaster.objects.filter(name__iexact=search_params['corporate_name'])
        corp_ids = corp_qs.values_list('id', flat=True)
        tgt_filters['corporate_id__in'] = corp_ids
    target_qs = TargetMaster.objects.filter(**tgt_filters)
    corp_targets = dict(target_qs.values_list('corporate_id').annotate(Sum('target_amt')))
    achieved_tgt_map = dict(GenericOrderDetailMapping.objects.values_list('client_name').
                            annotate(net_amt=Sum(F('unit_price') * F('quantity'))))
    temp_data['recordsTotal'] = len(corp_targets)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    todays_date = datetime.datetime.today()
    current_year = todays_date.year
    start_date = datetime.datetime.strptime('Apr-1-%s' % current_year, '%b-%d-%Y')
    days_passed = (todays_date - start_date).days

    totals_map = {}
    for corp_id, corp_target in corp_targets.items():
        corp_name = CorporateMaster.objects.get(id=corp_id).name
        ytd_target = round((corp_target / 365) * days_passed, 2)
        ytd_act_sale = achieved_tgt_map.get(corp_name, 0)
        exc_short = ((ytd_act_sale - ytd_target) / ytd_target) * 100
        excess_shortfall = round(exc_short, 2)
        if 'Corporate Target' not in totals_map:
            totals_map['Corporate Target'] = corp_target
        else:
            totals_map['Corporate Target'] += corp_target
        if 'YTD Targets' not in totals_map:
            totals_map['YTD Targets'] = ytd_target
        else:
            totals_map['YTD Targets'] += ytd_target
        if 'YTD Actual Sale' not in totals_map:
            totals_map['YTD Actual Sale'] = round(ytd_act_sale, 2)
        else:
            totals_map['YTD Actual Sale'] += round(ytd_act_sale, 2)
        ord_dict = OrderedDict((('Corporate Name', corp_name),
                                ('Corporate Target', corp_target),
                                ('YTD Targets', ytd_target),
                                ('YTD Actual Sale', ytd_act_sale),
                                ('Excess / Shortfall %', excess_shortfall),
                                ))
        temp_data['aaData'].append(ord_dict)
    for i, j in totals_map.items():
        totals_map[i] = get_currency_format(j)
    temp_data['totals'] = totals_map
    if stop_index:
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


def get_corporate_reseller_mapping_report_data(search_params, user, sub_user):
    from rest_api.views.outbound import get_same_level_warehouses
    lis = ['id', 'user']
    if user.userprofile.warehouse_type != 'DIST':
        distributors = get_same_level_warehouses(2, user)
        if sub_user.userprofile.zone:
            zone_id = sub_user.userprofile.zone
            distributors = UserProfile.objects.filter(user__in=distributors,
                                                      zone__icontains=zone_id).values_list('user_id', flat=True)
    else:
        distributors = [user.id]
    temp_data = copy.deepcopy(AJAX_DATA)
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    zone_code = search_params.get('zone_code', '')
    if zone_code:
        distributors = UserProfile.objects.filter(user__in=distributors, zone__icontains=zone_code).\
            values_list('user_id', flat=True)
    dist_code = search_params.get('distributor_code', '')
    if dist_code:
        distributors = UserProfile.objects.filter(user__in=distributors,
                                                  user__first_name__icontains=dist_code).values_list('user_id', flat=True)
    zones_map = dict(UserProfile.objects.filter(user__in=distributors).values_list('user_id', 'zone'))
    names_map = dict(UserProfile.objects.filter(user__in=distributors).
                     values_list('user_id', Concat('user__username', Value(' - '), 'user__first_name')))
    resellers_qs = CustomerUserMapping.objects.filter(customer__user__in=distributors)
    resellers = resellers_qs.values_list('customer_id', flat=True)
    res_dist_ids_map = dict(resellers_qs.values_list('customer_id', 'customer__user'))
    resellers_names_map = dict(resellers_qs.values_list('customer_id',
                                                        Concat('user__username', Value(' - '), 'user__first_name')))
    res_corp_filters = {'reseller_id__in': resellers}
    if 'reseller_code' in search_params:
        res_qs = CustomerUserMapping.objects.filter(customer__name__iexact=search_params['reseller_code'])
        res_corp_filters['reseller_id__in'] = res_qs.values_list('customer__id', flat=True)
    if 'corporate_name' in search_params:
        corp_qs = CorporateMaster.objects.filter(name__iexact=search_params['corporate_name'])
        corp_ids = corp_qs.values_list('id', flat=True)
        res_corp_filters['corporate_id__in'] = corp_ids
    res_corp_qs = CorpResellerMapping.objects.filter(**res_corp_filters).\
        exclude(status=0).values_list('reseller_id', 'corporate_id')
    corp_id_names = dict(CorporateMaster.objects.values_list('id', 'name'))
    temp_data['recordsTotal'] = len(res_corp_qs)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    if stop_index:
        res_corp_qs = res_corp_qs[start_index:stop_index]
    for res_id, corp_id in res_corp_qs:
        dist_id = res_dist_ids_map[res_id]
        dist_code = names_map[dist_id]
        zone_code = zones_map[dist_id]
        corp_name = corp_id_names.get(corp_id)
        res_code = resellers_names_map.get(res_id)
        ord_dict = OrderedDict((('Zone Code', zone_code),
                                ('Distributor Code', dist_code),
                                ('Reseller Code', res_code),
                                ('Corporate Name', corp_name)))
        temp_data['aaData'].append(ord_dict)
    return temp_data


def get_enquiry_status_report_data(search_params, user, sub_user):
    from rest_api.views.outbound import get_same_level_warehouses
    lis = ['id', 'user']
    if user.userprofile.warehouse_type != 'DIST':
        distributors = get_same_level_warehouses(2, user)
        if sub_user.userprofile.zone:
            zone_id = sub_user.userprofile.zone
            distributors = UserProfile.objects.filter(user__in=distributors,
                                                      zone__icontains=zone_id).values_list('user_id', flat=True)
    else:
        distributors = [user.id]
    temp_data = copy.deepcopy(AJAX_DATA)
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    search_parameters = {}
    zone_code = search_params.get('zone_code', '')
    if zone_code:
        distributors = UserProfile.objects.filter(user__in=distributors, zone__icontains=zone_code).\
            values_list('user_id', flat=True)
    dist_code = search_params.get('distributor_code', '')
    if dist_code:
        distributors = UserProfile.objects.filter(user__in=distributors,
                                                  user__first_name__icontains=dist_code).values_list('user_id', flat=True)
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['enquiry__creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['enquiry__creation_date__lt'] = search_params['to_date']

    search_parameters['enquiry__user__in'] = distributors
    if 'reseller_code' in search_params:
        res_ids = CustomerMaster.objects.filter(name__icontains=search_params['reseller_code']). \
            values_list('id', flat=True)
        search_parameters['enquiry__customer_id__in'] = res_ids
    if 'enquiry_status' in search_params:
        search_parameters['enquiry__extend_status__icontains'] = search_params['enquiry_status']
    if 'enquiry_number' in search_params:
        search_parameters['enquiry__enquiry_id__contains'] = search_params['enquiry_number']
    if 'sku_code' in search_params:
        search_parameters['sku__sku_code'] = search_params['sku_code']
    if 'aging_period' in search_params:
        try:
            aging_period = int(search_params['aging_period'])
        except:
            aging_period = 0
        extend_date = datetime.datetime.today() + datetime.timedelta(days=aging_period)
        search_parameters['enquiry__extend_date'] = extend_date

    resellers_qs = CustomerUserMapping.objects.filter(customer__user__in=distributors)
    resellers_names_map = dict(resellers_qs.values_list('customer_id',
                                                        Concat('user__username', Value(' - '), 'user__first_name')))

    enquired_sku_qs = EnquiredSku.objects.filter(**search_parameters)
    temp_data['recordsTotal'] = enquired_sku_qs.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    if stop_index:
        enquired_sku_qs = enquired_sku_qs[start_index:stop_index]

    for en_obj in enquired_sku_qs:
        em_obj = en_obj.enquiry
        enq_id = int(em_obj.enquiry_id)
        extend_status = em_obj.extend_status
        if em_obj.extend_date:
            days_left_obj = em_obj.extend_date - datetime.datetime.today().date()
            days_left = days_left_obj.days
        else:
            days_left = 0
        customer_name = resellers_names_map.get(em_obj.customer_id, '')
        dist_obj = User.objects.get(id=em_obj.user)
        distributor_name = dist_obj.username + ' - ' + dist_obj.first_name
        zone = dist_obj.userprofile.zone
        sku_code = en_obj.sku.sku_code
        quantity = en_obj.quantity
        prod_catg = en_obj.sku.sku_category
        ord_dict = OrderedDict((('Zone Code', zone),
                                ('Distributor Code', distributor_name),
                                ('Reseller Code', customer_name),
                                ('Product Category', prod_catg),
                                ('SKU Code', sku_code),
                                ('SKU Quantity', quantity),
                                ('Enquiry No', enq_id),
                                ('Enquiry Aging', days_left),
                                ('Enquiry Status', extend_status)))
        temp_data['aaData'].append(ord_dict)
    return temp_data

def get_shipment_report_data(search_params, user, sub_user, serial_view=False):
    from miebach_admin.models import *
    from miebach_admin.views import *
    from common import get_admin
    from rest_api.views.common import get_sku_master, get_order_detail_objs
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    search_parameters = {}
    lis = ['order_shipment__shipment_number', 'order__original_order_id', 'order__sku__sku_code', 'order__title',
           'order__customer_name',
           'order__quantity', 'shipping_quantity', 'order_shipment__truck_number','creation_date', 'id', 'id',
           'order__customerordersummary__payment_status', 'order_packaging__package_reference']
    search_parameters['order__user'] = user.id
    search_parameters['shipping_quantity__gt'] = 0
    search_parameters['order__sku_id__in'] = sku_master_ids
    temp_data = copy.deepcopy(AJAX_DATA)

    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lt'] = search_params['to_date']
    if 'sku_code' in search_params:
        search_parameters['order__sku__sku_code'] = search_params['sku_code']
    if 'customer_id' in search_params:
        search_parameters['order__customer_id'] = search_params['customer_id']
    if 'order_id' in search_params:
        order_detail = get_order_detail_objs(search_params['order_id'], user, search_params={}, all_order_objs=[])
        if order_detail:
            search_parameters['order_id__in'] = order_detail.values_list('id', flat=True)
        else:
            search_parameters['order_id__in'] = []

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    model_data = ShipmentInfo.objects.filter(**search_parameters).\
                                    values('order_shipment__shipment_number', 'order__order_id', 'id',
                                           'order__original_order_id', 'order__id','order__order_code', 'order__sku__sku_code',
                                           'order__title', 'order__customer_name', 'order__quantity', 'shipping_quantity',
                                           'order_shipment__truck_number', 'creation_date',
                                           'order_shipment__courier_name',
                                           'order__customerordersummary__payment_status',
                                           'order_packaging__package_reference')

    ship_search_params  = {}
    for key, value in search_parameters.iteritems():
        ship_search_params['shipment__%s' % key] = value
    ship_status = dict(ShipmentTracking.objects.filter(**ship_search_params).values_list('shipment_id', 'ship_status').\
                       distinct().order_by('creation_date'))
    if search_params.get('order_term'):
        order_data = lis[search_params['order_index']]
        if search_params['order_term'] == 'desc':
            order_data = "-%s" % order_data
        model_data = model_data.order_by(order_data)

    temp_data['recordsTotal'] = model_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    if stop_index:
        model_data = model_data[start_index:stop_index]

    admin_user = get_admin(user)
    result = ''
    for data in model_data:
        order_id = data['order__original_order_id']
        if not order_id:
            order_id = data['order__order_code'] + str(data['order__order_id'])
        date = get_local_date(user, data['creation_date']).split(' ')

        shipment_status = ship_status.get(data['id'], '')

        if admin_user.get_username().lower() == '72Networks'.lower() :
            try:
                from firebase import firebase
                firebase = firebase.FirebaseApplication('https://pod-stockone.firebaseio.com/', None)
                result = firebase.get('/OrderDetails/'+order_id, None)
            except Exception as e:
                result = 0
                import traceback
                log.debug(traceback.format_exc())
                log.info('Firebase query  failed for %s and params are %s and error statement is %s' % (
                str(user.username), str(request.POST.dict()), str(e)))

        if result :
            try:
                signed_invoice_copy = result['signed_invoice_copy']
            except:
                signed_invoice_copy = ''
            try :
                id_type = result['id_type']
            except:
                id_type = ''
            try :
                id_card = result['id_card']
            except :
                id_card = ''
            try :
                id_proof_number = result['id_proof_number']
            except:
                id_proof_number = ''
            try :
                pod_status = result['pod_status']
            except:
                pod_status = False
        else:
            signed_invoice_copy =''
            id_type =''
            id_card =''
            id_proof_number = ''
            pod_status = False

        if pod_status :
            shipment_status = 'Delivered'
        else:
            shipment_status = shipment_status


        serial_number = OrderIMEIMapping.objects.filter(po_imei__sku__wms_code =data['order__sku__sku_code'],order_id=data['order__id'],po_imei__sku__user=user.id)
        if serial_number :
            serial_number = serial_number[0].po_imei.imei_number
        else:
            serial_number = 0


        temp_data['aaData'].append(OrderedDict((('Shipment Number', data['order_shipment__shipment_number']),
                                                ('Order ID', order_id), ('SKU Code', data['order__sku__sku_code']),
                                                ('Title', data['order__title']),
                                                ('Customer Name', data['order__customer_name']),
                                                ('Quantity', data['order__quantity']),
                                                ('Shipped Quantity', data['shipping_quantity']),
                                                ('Truck Number', data['order_shipment__truck_number']),
                                                ('Date', ' '.join(date)),
                                                ('Signed Invoice Copy',signed_invoice_copy),
                                                ('ID Type',id_type),
                                                ('ID Card' , id_card),
                                                ('Serial Number' ,serial_number),
                                                ('ID Proof Number' , id_proof_number),
                                                ('Shipment Status',shipment_status ),
                                                ('Courier Name', data['order_shipment__courier_name']),
                                                ('Payment Status', data['order__customerordersummary__payment_status']),
                                                ('Pack Reference', data['order_packaging__package_reference']))))
    return temp_data


def get_sku_wise_rtv_filter_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master, get_local_date, apply_search_sort,\
                                      truncate_float, get_sku_ean_list
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    unsorted_dict = {17: 'Total Amount'}
    lis = ['rtv_number', 'creation_date', 'seller_po_summary__purchase_order__order_id',
           'seller_po_summary__purchase_order__open_po__supplier_id',
           'seller_po_summary__purchase_order__open_po__supplier__name',
           'seller_po_summary__purchase_order__open_po__sku__sku_code',
           'seller_po_summary__purchase_order__open_po__sku__sku_desc',
           'seller_po_summary__purchase_order__open_po__sku__hsn_code',
           'seller_po_summary__purchase_order__open_po__sku__ean_number',
           'seller_po_summary__purchase_order__open_po__mrp',
           'quantity', 'seller_po_summary__purchase_order__open_po__price',
           'seller_po_summary__purchase_order__open_po__cgst_tax', 'seller_po_summary__purchase_order__open_po__sgst_tax',
           'seller_po_summary__purchase_order__open_po__igst_tax', 'seller_po_summary__purchase_order__open_po__utgst_tax',
           'seller_po_summary__purchase_order__open_po__cess_tax', 'id', 'seller_po_summary__invoice_number',
           'seller_po_summary__invoice_date']
    model_name = ReturnToVendor
    search_parameters = {}
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    temp_data = copy.deepcopy(AJAX_DATA)
    temp_data['draw'] = search_params.get('draw')
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lt'] = search_params['to_date']
    if 'supplier' in search_params:
        if search_params['supplier'] and ':' in search_params['supplier']:
            search_parameters['seller_po_summary__purchase_order__open_po__supplier__id__iexact'] = \
                                search_params['supplier'].split(':')[0]
    if 'open_po' in search_params and search_params['open_po']:
        temp = re.findall('\d+', search_params['open_po'])
        if temp:
            search_parameters['seller_po_summary__purchase_order__order_id'] = temp[-1]
    if 'invoice_number' in search_params:
        search_parameters['seller_po_summary__invoice_number'] = search_params['invoice_number']
    if 'rtv_number' in search_params:
        search_parameters['rtv_number'] = search_params['rtv_number']
    search_parameters['seller_po_summary__purchase_order__open_po__sku__user'] = user.id
    search_parameters['seller_po_summary__purchase_order__open_po__sku_id__in'] = sku_master_ids
    model_data = model_name.objects.filter(**search_parameters)
    col_num = search_params.get('order_index', 0)
    order_term = search_params.get('order_term', 'asc')
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = "-%s" % order_data
        model_data = model_data.order_by(order_data)
    temp_data['recordsTotal'] = model_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    custom_search = False
    if col_num in unsorted_dict.keys():
        custom_search = True
    if stop_index and not custom_search:
        model_data = model_data[start_index:stop_index]
    for rtv in model_data:
        data = OrderedDict()
        seller_po_summary = rtv.seller_po_summary
        purchase_order = seller_po_summary.purchase_order
        open_po = purchase_order.open_po
        receipt_no = seller_po_summary.receipt_number
        if not receipt_no:
            receipt_no = ''
        po_number = '%s%s_%s/%s' % (purchase_order.prefix,
                                 str(purchase_order.creation_date).split(' ')[0].replace('-', ''),
                                 str(purchase_order.order_id), str(receipt_no))
        price = open_po.price
        mrp = open_po.mrp
        data['total_received'] = rtv.quantity
        batch_detail = seller_po_summary.batch_detail
        data['cgst_tax'] = open_po.cgst_tax
        data['sgst_tax'] = open_po.sgst_tax
        data['igst_tax'] = open_po.igst_tax
        data['utgst_tax'] = open_po.utgst_tax
        data['cess_tax'] = open_po.cess_tax
        data['invoice_number'] = seller_po_summary.invoice_number
        if batch_detail:
            price = batch_detail.buy_price
            mrp = batch_detail.mrp
            if batch_detail.tax_percent:
                temp_tax_percent = batch_detail.tax_percent
                if open_po.supplier.tax_type == 'intra_state':
                    temp_tax_percent = temp_tax_percent / 2
                    data['cgst_tax'] = truncate_float(temp_tax_percent, 1)
                    data['sgst_tax'] = truncate_float(temp_tax_percent, 1)
                    data['igst_tax'] = 0
                else:
                    data['igst_tax'] = temp_tax_percent
                    data['cgst_tax'] = 0
                    data['sgst_tax'] = 0
        amount = float(data['total_received'] * price)
        tot_tax = float(data['cgst_tax']) + float(data['sgst_tax']) +\
                  float(data['igst_tax']) + float(data['utgst_tax'])\
                    + float(data['cess_tax'])
        aft_unit_price = float(price) + (float(price / 100) * tot_tax)
        final_price = aft_unit_price
        invoice_total_amount = float(final_price) * float(data['total_received'])
        invoice_total_amount = truncate_float(invoice_total_amount, 2)
        hsn_code = ''
        if open_po.sku.hsn_code:
            hsn_code = str(open_po.sku.hsn_code)
        invoice_date = ''
        data['invoice_date'] = seller_po_summary.invoice_date
        if data['invoice_date']:
            invoice_date = data['invoice_date'].strftime("%d %b, %Y")
        ean_numbers = get_sku_ean_list(open_po.sku)
        ean_numbers = ','.join(ean_numbers)
        temp_data['aaData'].append(OrderedDict((('RTV Number', rtv.rtv_number),
                            ('RTV Date', get_local_date(user, rtv.creation_date)),
                            ('Order ID', po_number),
                            ('Supplier ID', open_po.supplier_id),
                            ('Supplier Name', open_po.supplier.name),
                            ('SKU Code', open_po.sku.sku_code),
                            ('SKU Description', open_po.sku.sku_desc),
                            ('HSN Code', hsn_code),
                            ('EAN Number', ean_numbers),
                            ('MRP', mrp),
                            ('Quantity', data['total_received']),
                            ('Unit Price', price),
                            ('Pre-Tax Received Value', amount),
                            ('CGST(%)', data['cgst_tax']),
                            ('SGST(%)', data['sgst_tax']),
                            ('IGST(%)', data['igst_tax']),
                            ('UTGST(%)', data['utgst_tax']),
                            ('CESS(%)', data['cess_tax']),
                            ('Total Amount', invoice_total_amount),
                            ('Invoice Number', data['invoice_number']),
                            ('Invoice Date', invoice_date),
                            ('DT_RowAttr', {'data-id': rtv.id}), ('key', 'po_summary_id'),
	)))
    if stop_index and custom_search:
        if temp_data['aaData']:
            temp_data['aaData'] = apply_search_sort(temp_data['aaData'][0].keys(), temp_data['aaData'], order_term, '', col_num, exact=False)
            temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


def get_grn_edit_filter_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master, get_local_date, apply_search_sort
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    user_profile = UserProfile.objects.get(user_id=user.id)
    lis = ['order_id', 'open_po__supplier_id', 'open_po__supplier__name', 'ordered_qty']
    unsorted_dict = {}
    model_name = PurchaseOrder
    field_mapping = {'from_date': 'creation_date', 'to_date': 'creation_date', 'order_id': 'order_id', 'wms_code': 'open_po__sku__wms_code__iexact', 'user': 'open_po__sku__user', 'sku_id__in': 'open_po__sku_id__in', 'prefix': 'prefix', 'supplier_id': 'open_po__supplier_id', 'supplier_name': 'open_po__supplier__name'}
    result_values = ['order_id', 'open_po__supplier_id', 'open_po__supplier__name', 'prefix',
           'sellerposummary__receipt_number']
    excl_status = {'status': ''}
    ord_quan = 'open_po__order_quantity'
    rec_quan = 'received_quantity'
    rec_quan1 = 'sellerposummary__quantity'
    search_parameters = {}
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    temp_data = copy.deepcopy(AJAX_DATA)
    temp_data['draw'] = search_params.get('draw')
    if 'from_date' in search_params:
        search_parameters[field_mapping['from_date'] + '__gte'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                         datetime.time())
        search_parameters[field_mapping['to_date'] + '__lte'] = search_params['to_date']
    if 'open_po' in search_params and search_params['open_po']:
        temp = re.findall('\d+', search_params['open_po'])
        if temp:
            search_parameters[field_mapping['order_id']] = temp[-1]
    if 'sku_code' in search_params:
        search_parameters[field_mapping['wms_code']] = search_params['sku_code']
    search_parameters[field_mapping['user']] = user.id
    search_parameters[field_mapping['sku_id__in']] = sku_master_ids
    search_parameters['received_quantity__gt'] = 0
    query_data = model_name.objects.prefetch_related('open_po__sku','open_po__supplier').select_related('open_po', 'open_po__sku','open_po__supplier').exclude(**excl_status).filter(**search_parameters)
    model_data = query_data.values(*result_values).distinct().annotate(ordered_qty=Sum(ord_quan),
                                                                   total_received=Sum(rec_quan),
                                                                   grn_rec=Sum(rec_quan1))
    col_num = search_params.get('order_index', 0)
    order_term = search_params.get('order_term', 'asc')
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
                order_data = "-%s" % order_data
        model_data = model_data.order_by(order_data)
    temp_data['recordsTotal'] = model_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    custom_search = False
    if col_num in unsorted_dict.keys():
        custom_search = True
    if stop_index and not custom_search:
        model_data = model_data[start_index:stop_index]
    purchase_orders = PurchaseOrder.objects.filter(open_po__sku__user=user.id)
    for data in model_data:
        po_result = purchase_orders.filter(order_id=data[field_mapping['order_id']], open_po__sku__user=user.id)
        result = po_result[0]
        total_ordered = po_result.aggregate(Sum('open_po__order_quantity'))['open_po__order_quantity__sum']
        if not total_ordered:
            total_ordered = 0
        po_number = '%s%s_%s' % (data[field_mapping['prefix']], str(result.creation_date).split(' ')[0].replace('-', ''),
                                    data[field_mapping['order_id']])
        receipt_no = data['sellerposummary__receipt_number']
        if not receipt_no:
            receipt_no = ''
        else:
            po_number = '%s/%s' % (po_number, receipt_no)
        received_qty = data['total_received']
        if data['grn_rec']:
            received_qty = data['grn_rec']
        temp_data['aaData'].append(OrderedDict((('PO Number', po_number),
                                                ('Supplier ID', data[field_mapping['supplier_id']]),
                                                ('Supplier Name', data[field_mapping['supplier_name']]),
                                                ('Order Quantity', total_ordered),
                                                ('Received Quantity', received_qty),
                                                ('DT_RowClass', 'results'), ('DT_RowAttr', {'data-id': data[field_mapping['order_id']]}),
                                                ('key', 'po_id'), ('receipt_type', 'Purchase Order'), ('receipt_no', receipt_no),
                                            )))
    if stop_index and custom_search:
        if temp_data['aaData']:
            temp_data['aaData'] = apply_search_sort(temp_data['aaData'][0].keys(), temp_data['aaData'], order_term, '', col_num, exact=False)
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


def print_sku_wise_data(search_params, user, sub_user):
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    cmp_data = ('sku_code', 'wms_code', 'sku_category', 'sku_type', 'sku_class')
    for data in cmp_data:
        if data in search_params:
            search_parameters['%s__%s' % (data, 'icontains')] = search_params[data]

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    search_parameters['user'] = user.id

    sku_master = sku_master.filter(**search_parameters)
    temp_data['recordsTotal'] = sku_master.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    if stop_index:
        sku_master = sku_master[start_index:stop_index]

    stock_dict = dict(StockDetail.objects.exclude(receipt_number=0).filter(sku__user=user.id).\
                      values_list('sku_id').distinct().annotate(tsum=Sum('quantity')))
    for data in sku_master:
        total_quantity = stock_dict.get(data.id, 0)
        # stock_data = StockDetail.objects.exclude(location__zone__zone='DEFAULT').filter(sku_id=data.id)
        # for stock in stock_data:
        #     total_quantity += int(stock.quantity)

        temp_data['aaData'].append(OrderedDict((('SKU Code', data.sku_code), ('WMS Code', data.wms_code),
                                                ('Product Description', data.sku_desc),
                                                ('SKU Category', data.sku_category),
                                                ('Total Quantity', total_quantity))))
    return temp_data
