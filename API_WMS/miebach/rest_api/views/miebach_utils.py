import datetime
import time
from functools import wraps
from collections import OrderedDict
from django.db import models as django_models
from django.db.models import Sum
import copy
import re
import reversion
import zipfile
import StringIO
from reversion.models import Version
from miebach_admin.models import *
from itertools import chain
from operator import itemgetter
from django.db.models import Q, F, FloatField, Case, When
from django.db.models.functions import Cast, Concat
from django.db.models.fields import DateField, CharField
from django.db.models import Value
from utils import init_logger, get_currency_format
from miebach_admin.choices import SELLABLE_CHOICES
from dateutil.relativedelta import *
from django.db.models.functions import ExtractHour, ExtractMinute



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

MILKBASKET_USERS = ['milkbasket_test', 'NOIDA02', 'NOIDA01', 'GGN01', 'HYD01', 'BLR01']

MILKBASKET_BULK_ZONE = 'Bulk Zone'

#ADJUST_INVENTORY_EXCEL_HEADERS = ['WMS Code', 'Location', 'Physical Quantity', 'Reason']

ADJUST_INVENTORY_EXCEL_MAPPING = OrderedDict((('Seller ID', 'seller_id'), ('WMS Code', 'wms_code'),
                                            ('Location', 'location'),
                                            ('Physical Quantity', 'quantity'), ('Batch Number', 'batch_no'),
                                            ('MRP', 'mrp'), ('Weight', 'weight'), ('Reason', 'reason')))

SUB_CATEGORIES = OrderedDict((('mens_polo', 'MENS POLO'), ('ladies_polo', 'LADIES POLO'),
                              ('round_neck', 'ROUND NECK'), ('hoodie', 'HOODIE'), ('jackets', 'JACKETS'),
                              ('henley', 'HENLEY'), ('laptop_bags', 'LAPTOP BAGS'),
                              ('gym_bags', 'GYM BAGS'), ('pant', 'PANT'),
                              ('belts', 'BELTS'), ('ear_phone', 'EAR PHONE'),
                              ('v_neck', 'V NECK'), ('polo', 'POLO'), ('chinese_collar', 'CHINESE COLLAR'),
                              ('bags', 'BAGS')
                            ))

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
LABEL_KEYS = ["NOTIFICATION_LABEL", "MASTERS_LABEL", "INBOUND_LABEL", "PRODUCTION_LABEL", "STOCK_LABEL", "OUTBOUND_LABEL", "SHIPMENT_LABEL",
              "OTHERS_LABEL", "UPLOADS", "REPORTS", "CONFIGURATIONS", "PAYMENT_LABEL"]

SKU_DATA = {'user': '', 'sku_code': '', 'wms_code': '',
            'sku_desc': '', 'sku_group': '', 'sku_type': '', 'mix_sku': '',
            'sku_category': '', 'sku_class': '', 'threshold_quantity': 0, 'max_norm_quantity': 0, 'color': '', 'mrp': 0,
            'status': 1, 'online_percentage': 0, 'qc_check': 0, 'sku_brand': '', 'sku_size': '', 'style_name': '',
            'price': 0,
            'ean_number': 0, 'load_unit_handle': 'unit', 'zone_id': None, 'hsn_code': '', 'product_type': '',
            'sub_category': '', 'primary_category': '', 'cost_price': 0, 'sequence': 0, 'image_url': '',
            'measurement_type': '', 'sale_through': '', 'shelf_life': 0, 'enable_serial_based': 0, 'block_options': ''}

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
        'sku': '', 'supplier_code': '', 'preference': '', 'moq': '', 'price': '', 'costing_type': 'Price Based',
                     'margin_percentage': 0}

SKU_PACK_DATA = {'sku': '','pack_id':'', 'pack_quantity': '','creation_date':datetime.datetime.now()}

REPLENUSHMNENT_DATA = {'classification': '','size':'', 'max_days': 0,'min_days':0, 'creation_date':datetime.datetime.now()}

SKUCLASSIFICATION_DATA = {'sku': '','classification': '','avg_sales_day':'', 'max_units': 0,'min_units':0, 'creation_date':datetime.datetime.now()}

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
                       'status': 1, 'courier_name': '','driver_name':'','driver_phone_number':'', 'ewaybill_number':''}

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
                            (('Physical Quantity *','quantity'),('Reason','reason')),
                            (('Pallet Code', 'pallet_no'),) )

#MOVE_INVENTORY_UPLOAD_FIELDS = ['WMS Code', 'Source Location', 'Destination Location', 'Quantity']

MOVE_INVENTORY_EXCEL_MAPPING = OrderedDict((('Seller ID', 'seller_id'), ('WMS Code', 'wms_code'),
                                            ('Source Location', 'source'),
                                            ('Destination Location', 'destination'),
                                            ('Quantity', 'quantity'), ('Batch Number', 'batch_no'),
                                            ('MRP', 'mrp'), ('Weight', 'weight'),('Reason', 'reason')))

SKU_SUBSTITUTION_EXCEL_MAPPING = OrderedDict((('Seller ID', 'seller_id'), ('Source SKU Code', 'source_sku_code'),
                                              ('Source Location', 'source_location'),
                                              ('Source Batch Number', 'source_batch_no'),
                                              ('Source MRP', 'source_mrp'), ('Source Quantity', 'source_quantity'),
                                              ('Source Weight','source_weight'),
                                              ('Destination SKU Code', 'dest_sku_code'),
                                              ('Destination Location', 'dest_location'),
                                              ('Destination Batch Number', 'dest_batch_no'),
                                              ('Destination MRP', 'dest_mrp'), ('Destination Weight', 'dest_weight'),
                                              ('Destination Quantity', 'dest_quantity'),
                                            ))

COMBO_ALLOCATE_EXCEL_MAPPING = OrderedDict((('Seller ID', 'seller_id'), ('Combo SKU Code', 'combo_sku_code'),
                                              ('Combo Location', 'combo_location'),
                                              ('Combo Batch Number', 'combo_batch_no'),
                                              ('Combo MRP', 'combo_mrp'), ('Combo Weight', 'combo_weight'),
                                              ('Combo Quantity', 'combo_quantity'),
                                              ('Child SKU Code', 'child_sku_code'),
                                              ('Child Location', 'child_location'),
                                              ('Child Batch Number', 'child_batch_no'),
                                              ('Child MRP', 'child_mrp'),
                                              ('Child Weight', 'child_weight'),
                                              ('Child Quantity', 'child_quantity'),
                                            ))

BRAND_LEVEL_PRICING_EXCEL_MAPPING =  OrderedDict((('SKU Attribute Type(Brand, Category)', 'attribute_type'),
                                                  ('SKU Attribute Value', 'attribute_value'),
                                                  ('Selling Price Type', 'price_type'),
                                                  ('Min Range', 'min_unit_range'), ('Max Range', 'max_unit_range'),
                                                  ('Price', 'price'), ('Discount', 'discount')))


SUPPLIER_HEADERS = ['Supplier Id', 'Supplier Name', 'Address', 'Email', 'Phone No.', 'GSTIN Number', 'PAN Number',
                    'PIN Code', 'City', 'State', 'Country', 'Days required to supply', 'Fulfillment Amount',
                    'Credibility', 'Tax Type(Options: Inter State, Intra State)', 'PO Expiry Duration',
                    'Owner Name', 'Owner Number', 'Owner Email', 'SPOC Name', 'SPOC Number', 'SPOC Email',
                    'Lead Time', 'Credit Period', 'Bank Name', 'IFSC Code', 'Branch Name',
                    'Account Number', 'Account Holder Name', 'Secondary Email ID']

VENDOR_HEADERS = ['Vendor Id', 'Vendor Name', 'Address', 'Email', 'Phone No.']

CUSTOMER_HEADERS = ['Customer Id', 'Customer Name', 'Customer Code', 'Credit Period', 'CST Number', 'TIN Number', 'PAN Number', 'Email',
                    'Phone No.', 'City', 'State', 'Country', 'Pin Code', 'Address', 'Shipping Address', 'Selling Price Type',
                    'Tax Type(Options: Inter State, Intra State)', 'Discount Percentage(%)', 'Markup(%)', 'SPOC Name']

CUSTOMER_EXCEL_MAPPING = OrderedDict(
    (('customer_id', 0), ('name', 1), ('customer_code', 2), ('credit_period', 3), ('cst_number', 4), ('tin_number', 5),
     ('pan_number', 6), ('email_id', 7), ('phone_number', 8), ('city', 9), ('state', 10), ('country', 11),
     ('pincode', 12), ('address', 13), ('shipping_address', 14), ('price_type', 15), ('tax_type', 16),
     ('discount_percentage', 17), ('markup', 18), ('spoc_name', 19),
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

SUPPLIER_SKU_HEADERS = ['Supplier Id', 'WMS Code', 'Supplier Code', 'Preference', 'MOQ', 'Price', 'Costing Type (Price Based/Margin Based/Markup Based)', 'MarkDown Percentage','Markup Percentage']

SUPPLIER_SKU_ATTRIBUTE_HEADERS = ['Supplier Id', 'SKU Attribute Type(Brand, Category)', 'SKU Attribute Value', 'Price', 'Costing Type (Price Based/Margin Based/Markup Based)', 'MarkDown Percentage','Markup Percentage']

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
                                            ('APMC(%)', 'apmc_tax'),
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
                 'Customer ID', 'Customer Name', 'Email ID', 'Phone Number', 'Address', 'State', 'City',
                 'PIN Code', 'Invoice Amount(Without Tax and Discount)', 'Total Discount', 'CGST(%)', 'SGST(%)',
                 'IGST(%)', 'CESS Tax(%)', 'Order Type', 'Mode of Transport', 'Vehicle Number', 'Ship To']

MARKETPLACE_ORDER_HEADERS = ['SOR ID', 'UOR ID', 'Seller ID', 'Order Status', 'Title', 'SKU Code', 'Quantity',
                             'Shipment Date(yyyy-mm-dd)', 'Channel Name', 'Customer ID', 'Customer Name', 'Email ID',
                             'Phone Number', 'Shipping Address', 'State', 'City', 'PIN Code', 'MRP',
                             'Invoice Amount(Without Tax and Discount)', 'Total Discount', 'CGST(%)', 'SGST(%)',
                             'IGST(%)', 'CESS Tax(%)', 'Mode of Transport', 'Vehicle Number', 'Ship To']

USER_ORDER_EXCEL_MAPPING = {'warehouse_user': ORDER_HEADERS, 'marketplace_user': MARKETPLACE_ORDER_HEADERS,
                            'customer': ORDER_HEADERS}

# User Type Order Excel Mapping

ORDER_DEF_EXCEL = OrderedDict((('order_id', 0), ('title', 1), ('sku_code', 2), ('quantity', 3), ('shipment_date', 4),
                               ('channel_name', 5), ('shipment_check', 'true'), ('customer_id', 6),
                               ('customer_name', 7), ('email_id', 8),
                               ('telephone', 9), ('address', 10), ('state', 11), ('city', 12), ('pin_code', 13),
                               ('amount', 14), ('amount_discount', 15), ('cgst_tax', 16), ('sgst_tax', 17),
                               ('igst_tax', 18), ('cess_tax', 19), ('order_type', 20), ('mode_of_transport', 21),
                               ('vehicle_number', 22),('ship_to',23)
                               ))

MARKETPLACE_ORDER_DEF_EXCEL = OrderedDict(
    (('sor_id', 0), ('order_id', 1), ('seller', 2), ('order_status', 3), ('title', 4),
     ('sku_code', 5), ('quantity', 6), ('shipment_date', 7), ('channel_name', 8),
     ('shipment_check', 'true'), ('customer_id', 9),
     ('customer_name', 10), ('email_id', 11), ('telephone', 12), ('address', 13),
     ('state', 14), ('city', 15), ('pin_code', 16), ('mrp', 17), ('amount', 18),
     ('amount_discount', 19), ('cgst_tax', 20), ('sgst_tax', 21), ('igst_tax', 22), ('cess_tax', 23),
     ('mode_of_transport', 24), ('vehicle_number', 25),('ship_to',26)
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
    ['PO Number', 'PO Reference','Supplier ID', 'Supplier Name', 'Total Quantity'],
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
                {'label': 'Sister Warehouse', 'name': 'sister_warehouse', 'type': 'select'},
                {'label': 'SKU Brand', 'name': 'brand', 'type': 'input'},
                {'label': 'SKU Class', 'name': 'sku_class', 'type': 'input'},
                {'label': 'SKU Size', 'name': 'sku_size', 'type': 'input'},
                {'label': 'Status', 'name': 'order_report_status', 'type': 'select'},
                {'label': 'Order Reference', 'name': 'order_reference', 'type': 'input'},
                {'label': 'Order ID', 'name': 'order_id', 'type': 'input'}],
    'dt_headers': ['Order Date','Order ID', 'Customer ID','Customer Name', 'SKU Brand', 'SKU Category',
                   'SKU Sub Category', 'SKU Class', 'SKU Size', 'SKU Description', 'SKU Code', 'Vehicle Number',
                   'Order Qty', 'Unit Price', 'Price', 'MRP', 'Discount', 'Order Tax Amt', 'Order Amt(w/o tax)',
                   'Tax Percent', 'City', 'State', 'Marketplace', 'Total Order Amt', 'Cancelled Order Qty',
                   'Cancelled Order Amt', 'Net Order Qty', 'Net Order Amt', 'Status', 'Order Status', 'Remarks',
                   'Customer GST Number', 'Payment Type','Reference Number', 'Payment Received',
                   'HSN Code','Order Reference', 'GST Number'],
    'mk_dt_headers': ['Order Date','Order ID', 'Customer Name', 'SKU Brand', 'SKU Category', 'SKU Sub Category', 'SKU Class', 'SKU Size',
                   'SKU Description', 'SKU Code', 'Manufacturer', 'Searchable', 'Bundle',
                    'Order Qty', 'Unit Price', 'Price', 'MRP', 'Discount', 'Tax Percent', 'Order Amt(w/o tax)', 'City',
                   'State', 'Marketplace', 'Total Order Amt','Status', 'Order Status', 'Remarks','Customer GST Number','Payment Type','Reference Number'],
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
    'dt_headers': ['JO Code', 'Jo Creation Date', 'SKU Brand', 'SKU Category', 'SKU Sub Category', 'SKU Class', 'SKU Code', 'Stage',
                   'Quantity'],
    'mk_dt_headers': ['JO Code', 'Jo Creation Date', 'SKU Brand', 'SKU Category', 'SKU Sub Category', 'SKU Class', 'SKU Code', 'Stage',
                   'Manufacturer', 'Searchable', 'Bundle', 'Quantity'],
    'dt_url': 'get_openjo_report_details', 'excel_name': 'open_jo_report', 'print_url': 'print_open_jo_report',
    }

SKU_WISE_PO_DICT = {'filters': [{'label': 'PO From Date', 'name': 'from_date', 'type': 'date'},
                                {'label': 'PO To Date', 'name': 'to_date', 'type': 'date'},
                                {'label': 'Supplier ID', 'name': 'supplier', 'type': 'supplier_search'},
                                {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
                                {'label': 'SKU Category', 'name': 'sku_category', 'type': 'input'},
                                {'label': 'Sub Category', 'name': 'sub_category', 'type': 'input'},
                                {'label': 'SKU Brand', 'name': 'sku_brand', 'type': 'input'},
                                ],
                    'dt_headers': ['PO Date', 'PO Number', 'Supplier ID', 'Supplier Name', 'SKU Code',
                                      'SKU Description', 'SKU Class', 'SKU Style Name', 'SKU Brand', 'SKU Category',
                                      'Sub Category','PO Qty',  'Unit Price without tax', 'Unit Price with tax', 'MRP',
                                      'Pre-Tax PO Amount', 'Tax', 'After Tax PO Amount',
                                      'Qty received', 'Status', 'Warehouse Name', 'Report Generation Time'],
                    'dt_url': 'get_sku_purchase_filter', 'excel_name': 'sku_wise_purchases',
                    'print_url': 'print_sku_wise_purchase',
                    }


GRN_DICT = {'filters': [{'label': 'PO From Date', 'name': 'from_date', 'type': 'date'},
                        {'label': 'PO To Date', 'name': 'to_date', 'type': 'date'},
                        {'label': 'PO Number', 'name': 'open_po', 'type': 'input'},
                        {'label': 'Invoice Number', 'name': 'invoice_number', 'type': 'input'},
                        {'label': 'Supplier ID', 'name': 'supplier', 'type': 'supplier_search'},
                        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},],
            'dt_headers': ['PO Number', 'PO Reference','Supplier ID', 'Supplier Name', 'Order Quantity', 'Received Quantity'],
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
                        {'label': 'Invoice Number', 'name': 'invoice_number', 'type': 'input'},
                        {'label': 'Supplier ID', 'name': 'supplier', 'type': 'supplier_search'},
                        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
                        {'label': 'SKU Category', 'name': 'sku_category', 'type': 'input'},
                        {'label': 'Sub Category', 'name': 'sub_category', 'type': 'input'},
                        {'label': 'SKU Brand', 'name': 'sku_brand', 'type': 'input'},
            ],
        'dt_headers': ["Received Date", "PO Date", "PO Number", "PO Reference Number", "Supplier ID", "Supplier Name", "Recepient",
                       "SKU Code", "SKU Description", "SKU Category","Sub Category","SKU Brand", "HSN Code", "SKU Class", "SKU Style Name", "SKU Brand",
                       "SKU Category", "Received Qty", "Unit Rate", "MRP", "Pre-Tax Received Value", "CGST(%)",
                       "SGST(%)", "IGST(%)", "UTGST(%)", "CESS(%)", "APMC(%)", "CGST",
                       "SGST", "IGST", "UTGST", "CESS", "APMC", "Post-Tax Received Value", "Invoiced Unit Rate",
                       "Overall Discount",
                       "Invoiced Total Amount", "Invoice Number", "Invoice Date", "Challan Number",
                       "Challan Date", "Remarks", "Updated User", "GST NO","LR-NUMBER"],
        'mk_dt_headers': [ "Received Date", "PO Date", "PO Number", "Supplier ID", "Supplier Name", "Recepient",
                           "SKU Code", "SKU Description", "HSN Code", "SKU Class", "SKU Style Name", "SKU Brand", "SKU Category", "Sub Category",
                           "Manufacturer","Searchable","Bundle",
                           "Received Qty", "Unit Rate", "MRP","Weight", "Pre-Tax Received Value", "CGST(%)", "SGST(%)",
                           "IGST(%)", "UTGST(%)", "CESS(%)", "APMC(%)", "CGST",
                            "SGST", "IGST", "UTGST", "CESS", "APMC", "Post-Tax Received Value", "Margin %",
                           "Margin", "Invoiced Unit Rate","Overall Discount", "Invoiced Total Amount", "Invoice Number", "Invoice Date",
                           "Challan Number", "Challan Date", "Remarks", "Updated User", "GST NO", "LR-NUMBER"],
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
                {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
                {'label': 'SKU Category', 'name': 'sku_category', 'type': 'input'},
                {'label': 'Sub Category', 'name': 'sub_category', 'type': 'input'},
                {'label': 'SKU Brand', 'name': 'sku_brand', 'type': 'input'}],
    'dt_headers': ['Date', 'Supplier', 'Seller ID', 'Seller Name', 'SKU Code', 'SKU Description', 'SKU Class',
                    'SKU Category', 'Sub Category', 'SKU Brand',
                   'SKU Style Name', 'SKU Brand', 'SKU Category', 'Accepted Qty', 'Rejected Qty', 'Total Qty', 'Amount',
                   'Tax', 'Total Amount'],
    'mk_dt_headers': ['Date', 'Supplier', 'Seller ID', 'Seller Name', 'SKU Code', 'SKU Description', 'SKU Class',
                    'SKU Category', 'Sub Category', 'SKU Brand', 'Manufacturer', 'Searchable','Bundle',
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
        {'label': 'SKU Category', 'name': 'sku_category', 'type': 'input'},
        {'label': 'Sub Category', 'name': 'sub_category', 'type': 'input'},
        {'label': 'SKU Brand', 'name': 'sku_brand', 'type': 'input'},
    ],
    'dt_headers': ['Date', 'SKU Code', 'SKU Description', 'Style Name', 'Brand', 'Category', 'Sub Category',
                   'Size', 'Opening Stock', 'Opening Stock Value', 'Receipt Quantity', 'Produced Quantity', 'Dispatch Quantity','RTV Quantity',
                   'Return Quantity', 'Adjustment Quantity', 'Consumed Quantity', 'Closing Stock', 'Closing Stock Value'],
    'mk_dt_headers': ['Date', 'SKU Code', 'SKU Description', 'Style Name', 'Brand', 'Category', 'Sub Category',
                    'Manufacturer', 'Searchable', 'Bundle',
                   'Size', 'Opening Stock', 'Receipt Quantity', 'Produced Quantity', 'Dispatch Quantity',
                   'Return Quantity', 'Adjustment Quantity', 'Consumed Quantity', 'Closing Stock',],
    'dt_url': 'get_stock_ledger_report', 'excel_name': 'stock_ledger_report',
    'print_url': 'print_stock_ledger_report',
}

SHIPMENT_REPORT_DICT = {
    'filters': [
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
        {'label': 'Order ID', 'name': 'order_id', 'type': 'input'},
        {'label': 'SKU Category', 'name': 'sku_category', 'type': 'input'},
        {'label': 'Sub Category', 'name': 'sub_category', 'type': 'input'},
        {'label': 'SKU Brand', 'name': 'sku_brand', 'type': 'input'},
        {'label': 'Customer ID', 'name': 'order_id', 'type': 'customer_search'}
    ],
    'dt_headers': ['Shipment Number' ,'Order ID', 'SKU Code', 'SKU Category', 'Sub Category', 'SKU Brand', 'Title', 'Customer Name', 'Quantity', 'Shipped Quantity', 'Truck Number',
                   'Date', 'Shipment Status', 'Courier Name', 'Payment Status', 'Pack Reference'],
    'mk_dt_headers': ['Shipment Number' ,'Order ID', 'SKU Code', 'SKU Category', 'Sub Category', 'SKU Brand',
                    'Manufacturer','Searchable','Bundle',
                    'Title', 'Customer Name', 'Quantity', 'Shipped Quantity', 'Truck Number',
                   'Date', 'Shipment Status', 'Courier Name', 'Payment Status', 'Pack Reference'],
    'dt_url': 'get_shipment_report', 'excel_name': 'get_shipment_report',
    'print_url': 'print_shipment_report',
}

PO_REPORT_DICT = {
    'filters': [
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
        {'label': 'Sister Warehouse', 'name': 'sister_warehouse', 'type': 'select'},
        {'label': 'SKU Category', 'name': 'sku_category', 'type': 'input'},
        {'label': 'Sub Category', 'name': 'sub_category', 'type': 'input'},
        {'label': 'SKU Brand', 'name': 'sku_brand', 'type': 'input'},
    ],
    'dt_headers': ['SKU Code','Sku Description', 'SKU Category', 'Sub Category', 'SKU Brand', 'Quantity','PO No','Location'],
    'mk_dt_headers': ['SKU Code','Sku Description', 'SKU Category', 'Sub Category', 'SKU Brand', 'Manufacturer', 'Searchable', 'Bundle', 'Quantity','PO No','Location'],
    'dt_url': 'get_po_report', 'excel_name': 'get_po_report',
    'print_url': 'print_po_report',
 }

OPEN_ORDER_REPORT_DICT = {
     'filters': [
         {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
         {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
         {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
         {'label': 'Sister Warehouse', 'name': 'sister_warehouse', 'type': 'select'},
     ],
     'dt_headers': [
             'Central Order ID','Batch Number',
             'Batch Date','Branch ID',
             'Branch Name','Loan Proposal ID',
             'Loan Proposal Code','Client Code',
             'Client ID', 'Customer Name',
             'Address1','Address2',
             'Landmark','Village',
             'District','State1',
             'Pincode','Mobile Number',
             'Alternative Mobile Number','SKU Code',
             'Model','Unit Price',
             'CGST', 'SGST',
             'IGST','Total Price',
             'Location'],
     'dt_url': 'get_open_order_report', 'excel_name': 'get_open_order_report',
     'print_url': 'print_open_order_report',
  }
ORDER_FLOW_REPORT_DICT = {
     'filters': [
         {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
         {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
         {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
         {'label': 'Order ID/SR Number', 'name': 'order_id', 'type': 'input'},
         {'label': 'Central Order ID', 'name': 'central_order_id', 'type': 'input'},
         {'label': 'Project Name', 'name': 'project_name', 'type': 'input'},
     ],
     'dt_url': 'get_order_flow_report', 'excel_name': 'get_order_flow_report',
     'print_url': 'print_order_flow_report',
  }
STOCK_COVER_REPORT_DICT = {
       'filters': [
           {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
           {'label': 'SKU Category', 'name': 'sku_category', 'type': 'select'},
           {'label': 'SKU Class', 'name': 'sku_class', 'type': 'input'},
           {'label': 'SKU Type', 'name': 'sku_type', 'type': 'input'},
           {'label': 'Sub category', 'name': 'sub_category', 'type': 'input'},
           {'label': 'SKU Brand', 'name': 'sku_brand', 'type': 'input'},],
       'dt_headers': ['SKU', 'SKU Description','SKU Category','Sub Category','SKU Brand', 'SKU Type', 'SKU class','Current Stock In Hand','PO Pending','Total Stock including PO','Avg Last 30days','Avg Last 7 days','Stock Cover Days (30-day)','Stock Cover Days including PO stock (30-day)','Stock Cover Days (7-day)','Stock Cover Days including PO stock (7-day)'],
       'mk_dt_headers': ['SKU', 'SKU Description','SKU Category','Sub Category','SKU Brand','Manufacturer', 'Searchable', 'Bundle', 'SKU Type', 'SKU class','Current Stock In Hand','PO Pending','Total Stock including PO','Avg Last 30days','Avg Last 7 days','Stock Cover Days (30-day)','Stock Cover Days including PO stock (30-day)','Stock Cover Days (7-day)','Stock Cover Days including PO stock (7-day)'],
       'dt_url': 'get_stock_cover_report', 'excel_name': 'get_stock_cover_report',
       'print_url': 'print_stock_cover_report',
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
        {'label': 'Level', 'name': 'level', 'type': 'input'},
        {'label': 'Aging Period', 'name': 'aging_period', 'type': 'input'},
        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
        {'label': 'Warehouse Level', 'name': 'warehouse_level', 'type': 'input'},
        {'label': 'Enquiry Status', 'name': 'enquiry_status', 'type': 'select'},
        {'label': 'Corporate Name', 'name': 'corporate_name', 'type': 'input'},
    ],
    'dt_headers': ['Zone Code', 'Distributor Code', 'Reseller Code', 'Product Category', 'SKU Code', 'SKU Quantity',
                   'Level','Warehouse', 'Enquiry No', 'Enquiry Aging', 'Enquiry Status', 'Corporate Name', 'Remarks'],
    'dt_url': 'get_enquiry_status_report', 'excel_name': 'get_enquiry_status_report',
    'dt_unsort': ['Zone Code', 'Distributor Code', 'Reseller Code', 'Product Category', 'SKU Code', 'SKU Quantity',
                   'Enquiry No', 'Level', 'Warehouse', 'Enquiry Aging', 'Enquiry Status', 'Corporate Name', 'Remarks'],
    'print_url': 'print_enquiry_status_report',
}

RETURN_TO_VENDOR_REPORT = {
    'filters': [
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
        {'label': 'Supplier ID', 'name': 'supplier', 'type': 'supplier_search'},
        {'label': 'Purchase Order ID', 'name': 'open_po', 'type': 'input'},
        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
        {'label': 'Invoice Number', 'name': 'invoice_number', 'type': 'input'},
        {'label': 'RTV Number', 'name': 'rtv_number', 'type': 'input'}
    ],
    'dt_headers': ['RTV Number', 'Supplier ID', 'Supplier Name', 'Order ID', 'Invoice Number', 'Return Date', 'Reason', 'Updated User'],
    'dt_url': 'get_rtv_report', 'excel_name': 'get_rtv_report',
    'print_url': 'print_rtv_report',
}

STOCK_TRANSFER_REPORT_DICT = {
    'filters': [
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
        {'label': 'Sku Code', 'name': 'sku_code', 'type': 'input'},
    ],
    'dt_headers': ['Date', 'Invoice Number', 'Source Location', 'Destination', 'SKU Code', 'SKU Description','Quantity','Price','Net Value','CGST','SGST','IGST','Total Value','Status'],
    'mk_dt_headers': ['Date', 'Invoice Number', 'Source Location', 'Destination', 'SKU Code', 'SKU Description', 'Manufacturer', 'Searchable', 'Bundle', 'Quantity','Price','Net Value','CGST','SGST','IGST','Total Value','Status'],
    'dt_url': 'get_stock_transfer_report', 'excel_name': 'get_stock_transfer_report',
    'print_url': 'print_stock_transfer_report',
}

MARGIN_REPORT_DICT = {
  'filters': [
      {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
      {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
      {'label': 'SKU Code', 'name': 'sku_code', 'type': 'input'},
      {'label': 'SKU Sub Category', 'name': 'sub_category', 'type': 'input'},
      {'label': 'SKU Category', 'name': 'sku_category', 'type': 'input'},
      {'label': 'SKU Brand', 'name': 'sku_brand', 'type': 'input'},
      {'label': 'Manufacturer', 'name': 'manufacturer', 'type': 'input'},
      {'label': 'Searchable', 'name': 'searchable', 'type': 'input'},
      {'label': 'Bundle', 'name': 'bundle', 'type': 'input'},
  ],
  'dt_headers': ['Seller','SKU Code','Searchable','Bundle','SKU Desc','Weight','MRP','Manufacturer','Vendor Name','Sheet', 'Brand', 'Category', 'Sub Category','Customer','Marketplace', 'QTY', 'Weighted Avg Cost', 'Weighted Avg Selling Price','Total Cost','Total Sale','Margin Amount','Margin Percentage'],
  'dt_url': 'get_margin_report', 'excel_name': 'get_margin_report',
  'print_url': 'print_margin_report',
}

FINANCIAL_REPORT_DICT =  {
  'filters': [
      {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
      {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
      {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
      {'label': 'SKU Category', 'name': 'sku_category', 'type': 'input'},
      {'label': 'Sub Category', 'name': 'sub_category', 'type': 'input'},
      {'label': 'SKU Brand', 'name': 'sku_brand', 'type': 'input'},
  ],
  'dt_headers': ['SKU Code','SKU NAME','Category', 'Sub Category', 'SKU Brand','Manufacturer','Searchable','Bundle', 'City',
                 'Hub','Vendor Name','HSN Code','Weight', 'MRP', 'GST No', 'IGST Tax Rate','CESS Rate','Opening Qty',
                 'Opening Price Per Unit( Before Taxes)','Opening Value before Tax', 'Opening Tax', 'Opening CESS',
                 'Opening Value after Tax', 'Purchase Qty', 'Purchase Price Per Unit(Before Taxes)','Purchase Value before Tax',
                 'Purchase Tax', 'Purchase CESS', 'Purchase Value after Tax', 'Purchase Return Qty',
                 'Purchase Return Price Per Unit(Before Taxes)','Purchase Return Value before Tax',
                 'Purchase Return Tax', 'Purchase Return CESS',
                 'Purchase Return Value after Tax', 'Sale to Drsc Qty','Sale to Drsc Price Per Unit( Before Taxes)',
                 'Sale to Drsc Value before Tax', 'Sale to Drsc Tax', 'Sale to Drsc CESS',
                 'Sale to Drsc Value after Tax', 'Sale to othr Qty','Sale to othr Price Per Unit( Before Taxes)',
                 'Sale to othr Value before Tax', 'Sale to othr Tax', 'Sale to othr CESS',
                 'Sale to othr Value after Tax', 'Stock Transfers Qty','Stock Transfers Price Per Unit(Before Taxes)',
                 'Stock Transfers Value before Tax', 'Stock Transfers Tax', 'Stock Transfers CESS',
                 'Stock Transfers Value after Tax', 'Sale Return Qty',
                 'Sale Return Price Per Unit(Before Taxes)','Sale Return Value before Tax',
                 'Sale Return Tax', 'Sale Return CESS', 'Sale Return Value after Tax',
                 'Closing Qty', 'Closing Price Per Unit(Before Taxes)','Closing Value before Tax',
                 'Closing Tax', 'Closing CESS', 'Closing Value after Tax','Physical Qty', 'Adjustment Qty',
                 'Adjustment Price Per Unit(Before Taxes)', 'Adjustment Value', 'Margin', 'Margin Percentage'],
  'dt_url': 'get_financial_report', 'excel_name': 'get_financial_report',
  'print_url': 'print_financial_report',
}

BASA_REPORT_DICT = {
  'filters': [
      {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
      {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
      {'label': 'SKU Code', 'name': 'sku_code', 'type': 'input'},
      {'label': 'SKU Category', 'name': 'sku_category', 'type': 'input'},
      {'label': 'Sub Category', 'name': 'sub_category', 'type': 'input'},
      {'label': 'SKU Brand', 'name': 'sku_brand', 'type': 'input'},
  ],
  'dt_headers': ['SKU Code','SKU Desc','Weight','MRP','Brand', 'Category', 'Sub Category','Sub Category Type',
                 'Manufacturer', 'Searchable', 'Bundle',
                 'Sheet','Stock( Only BA and SA)','Avg CP','Latest GRN Qty','Latest GRN CP'],
  'dt_url': 'get_basa_report', 'excel_name': 'get_basa_report',
  'print_url': 'print_basa_report',
}

CURRENT_STOCK_REPORT_DICT = {
    'filters': [
        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
        {'label': 'SKU Category', 'name': 'sku_category', 'type': 'input'},
        {'label': 'Sub Category', 'name': 'sub_category', 'type': 'input'},
        {'label': 'SKU Brand', 'name': 'brand', 'type': 'input'},
        {'label': 'SKU Class', 'name': 'sku_class', 'type': 'input'}
    ],
    'dt_headers': ['Seller ID', 'Seller Name', 'SKU Code', 'SKU Description','Manufacturer', 'Searchable', 'Bundle', 'Brand', 'Category',
    'Sub Category', 'Sub Category type','Sheet','Vendor','Location', 'Weight', 'MRP', 'Available Quantity',
    'Reserved Quantity', 'Total Quantity','Tax %','Avg CP with Tax','Amount with Tax','Cost Price W/O Tax',
    'Amount W/O tax','Warehouse Name','Report Generation Time'],
    'dt_url': 'get_current_stock_report', 'excel_name': 'get_current_stock_report',
    'print_url': 'print_current_stock_report',
}

STOCK_RECONCILIATION_REPORT_DICT = {
  'filters': [
      {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
      {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
      {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
      {'label': 'SKU Category', 'name': 'sku_category', 'type': 'input'},
      {'label': 'Sub Category', 'name': 'sub_category', 'type': 'input'},
      {'label': 'SKU Brand', 'name': 'brand', 'type': 'input'},
  ],
  'dt_headers': ['Created Date', 'SKU Code', 'SKU Desc', 'MRP', 'Weight', 'Vendor Name', 'Brand', 'Category',
                 'Sub Category', 'Sub Category Type', 'Sheet', 'Opening Qty', 'Opening Avg Rate', 'Opening Amount After Tax',
                 'Opening Qty Damaged', 'Opening Damaged Amount After Tax',
                 'Purchases Qty', 'Purchases Avg Rate', 'Purchases Amount After Tax', 'Purchase Qty Damaged',
                 'Purchase Damaged Amount After Tax',
                 'RTV Qty', 'RTV Avg Rate', 'RTV Amount After Tax', 'RTV Qty Damaged', 'RTV Damaged Amount After Tax',
                 'Customer Sales Qty', 'Customer Sales Avg Rate', 'Customer Sales Amount After Tax', 'Customer Sales Qty Damaged',
                 'Customer Sales Damaged Amount After Tax',
                 'Internal Sales Qty', 'Internal Sales Avg Rate', 'Internal Sales Amount After Tax', 'Internal Sales Qty Damaged',
                 'Internal Sales Damaged Amount After Tax',
                 'Stock Transfer Qty', 'Stock Transfer Avg Rate', 'Stock Transfer Amount After Tax', 'Stock Transfer Qty Damaged',
                 'Stock Transfer Damaged Amount After Tax',
                 'Returns Qty', 'Returns Avg Rate', 'Returns Amount After Tax', 'Returns Qty Damaged', 'Returns Damaged Amount After Tax',
                 'Adjustment Qty', 'Adjustment Avg Rate', 'Adjustment Amount After Tax', 'Adjustment Qty Damaged',
                 'Adjustment Damaged Amount After Tax',
                 'Closing Qty', 'Closing Avg Rate', 'Closing Amount After Tax', 'Closing Qty Damaged',
                 'Closing Damaged Amount After Tax', 'Warehouse Name', 'Report Generation Time'],
  'dt_url': 'get_stock_reconciliation_report', 'excel_name': 'get_stock_reconciliation_report',
  'print_url': 'print_stock_reconciliation_report',
}

INVENTORY_VALUE_REPORT_DICT = {
    'filters': [
        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
        {'label': 'SKU Category', 'name': 'sku_category', 'type': 'input'},
        {'label': 'Sub Category', 'name': 'sub_category', 'type': 'input'},
        {'label': 'SKU Brand', 'name': 'brand', 'type': 'input'},
        {'label': 'SKU Class', 'name': 'sku_class', 'type': 'input'}
    ],
    'dt_headers': ['Seller ID', 'Seller Name','SKU Code', 'SKU Description', 'Category', 'Sub Category', 'Brand', 'Manufacturer',
                    'Searchable', 'Bundle', 'Weight', 'MRP', 'Batch Number', 'Ean Number', 'Manufactured Date', 'Expiry Date',
                    'Quantity with Damaged', 'Value with Damaged(with Tax)', 'Average Cost Price with Damaged',
                    'Quantity without Damaged', 'Value without Damaged(with Tax)', 'Average Cost Price without Damaged',
                    'Warehouse Name','Report Generation Time'],
    'dt_url': 'get_inventory_value_report', 'excel_name': 'get_inventory_value_report',
    'print_url': 'print_inventory_value_report',
}

BULK_TO_RETAIL_REPORT_DICT = {
    'filters': [
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
        {'label': 'Source SKU Code', 'name': 'source_sku_code', 'type': 'source_sku_search'},
        {'label': 'Source SKU Category', 'name': 'source_sku_category', 'type': 'input'},
        {'label': 'Source SKU Sub Category', 'name': 'source_sku_sub_category', 'type': 'input'},
        {'label': 'Source SKU Brand', 'name': 'source_sku_brand', 'type': 'input'},
        {'label': 'Destination SKU Code', 'name': 'destination_sku_code', 'type': 'destination_sku_search'},
        {'label': 'Destination SKU Category', 'name': 'destination_sku_category', 'type': 'input'},
        {'label': 'Destination SKU Sub Category', 'name': 'destination_sku_sub_category', 'type': 'input'},
        {'label': 'Destination SKU Brand', 'name': 'destination_sku_brand', 'type': 'input'},
    ],
    'dt_headers': ['Transaction ID', 'Date', 'Seller ID', 'Seller Name', 'Source SKU Code', 'Source SKU Description',
                    'Source Sku Manufacturer', 'Source Sku Searchable', 'Source Sku Bundle',
                   'Source SKU Category',  'Source SKU Sub Category',  'Source SKU Brand', 'Source Location',
                   'Source Weight', 'Source MRP', 'Source Quantity', 'Destination SKU Code',
                   'Destination SKU Description', 'Destination SKU Category', 'Destination SKU Sub Category',  'Destination SKU Brand', 'Destination Location',
                   'Destination Weight', 'Destination MRP', 'Destination Quantity', 'Warehouse Name',
                   'Report Generation Time'],
    'dt_url': 'get_bulk_to_retail_report', 'excel_name': 'get_bulk_to_retail_report',
    'print_url': 'print_bulk_to_retail_report',
}

MOVE_TO_INVENTORY_REPORT_DICT = {
    'filters': [
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
        {'label': 'Source Location', 'name': 'source_location', 'type': 'input'},
        {'label': 'Destination Location', 'name': 'destination_location', 'type': 'input'},
        {'label': 'SKU Category', 'name': 'sku_category', 'type': 'input'},
        {'label': 'Sub Category', 'name': 'sub_category', 'type': 'input'},
        {'label': 'SKU Brand', 'name': 'sku_brand', 'type': 'input'},
    ],
    'dt_headers': ['SKU Code', 'SKU Description','Source Location', 'SKU Category',
                   'Sub Category', 'SKU Brand',
                   'Destination Location','Quantity','Transaction Date', 'Updated User','Reason'],
    'dt_url': 'get_move_inventory_report', 'excel_name': 'get_move_inventory_report',
    'print_url': 'print_move_inventory_report',
}

BULK_STOCK_UPDATE = {
  'filters': [
        {'label': 'From Date', 'name': 'from_date', 'type': 'date'},
        {'label': 'To Date', 'name': 'to_date', 'type': 'date'},
        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'},
        {'label': 'Source Location', 'name': 'source_location', 'type': 'input'},
        {'label': 'Destination Location', 'name': 'destination_location', 'type': 'input'},
    ],
    'dt_headers': ['SKU Code', 'SKU Description', 'MRP', 'Weight', 'Source Location',
                    'Destination Location', 'Quantity','Transaction Date'],
    'dt_url': 'get_bulk_stock_update', 'excel_name': 'get_bulk_stock_update',
    'print_url': 'print_bulk_stock_update',
}
REPORT_DATA_NAMES = {'order_summary_report': ORDER_SUMMARY_DICT, 'open_jo_report': OPEN_JO_REP_DICT,
                     'sku_wise_po_report': SKU_WISE_PO_DICT,
                     'grn_report': GRN_DICT, 'sku_wise_grn_report' : SKU_WISE_GRN_DICT, 'seller_invoice_details': SELLER_INVOICE_DETAILS_DICT,
                     'rm_picklist_report': RM_PICKLIST_REPORT_DICT, 'stock_ledger_report': STOCK_LEDGER_REPORT_DICT,
                     'shipment_report': SHIPMENT_REPORT_DICT, 'dist_sales_report': DIST_SALES_REPORT_DICT,
                     'po_report':PO_REPORT_DICT,
                     'open_order_report':OPEN_ORDER_REPORT_DICT,
                     'order_flow_report':ORDER_FLOW_REPORT_DICT,
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
                     'grn_edit': GRN_EDIT_DICT, 'current_stock_report': CURRENT_STOCK_REPORT_DICT,
                     'inventory_value_report':INVENTORY_VALUE_REPORT_DICT,
                     'bulk_to_retail_report': BULK_TO_RETAIL_REPORT_DICT,
                     'stock_transfer_report':STOCK_TRANSFER_REPORT_DICT,
                     'stock_reconsiliation_report':STOCK_RECONCILIATION_REPORT_DICT,
                     'margin_report':MARGIN_REPORT_DICT,
                     'stock_cover_report':STOCK_COVER_REPORT_DICT,
                     'basa_report':BASA_REPORT_DICT,
                     'move_inventory_report' : MOVE_TO_INVENTORY_REPORT_DICT,
                     'financial_report': FINANCIAL_REPORT_DICT,
                     'bulk_stock_update': BULK_STOCK_UPDATE,
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
               'Threshold Quantity', 'Max Norm Quantity', 'Measurment Type', 'Sale Through', 'Color', 'EAN Number',
               'Load Unit Handling(Options: Enable, Disable)', 'HSN Code', 'Sub Category', 'Hot Release',
               'Mix SKU Attribute(Options: No Mix, Mix within Group)', 'Combo Flag', 'Block For PO', 'Status']

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
                              ('Expiry Date(YYYY-MM-DD)', 'expiry_date'),
                              ('Weight', 'weight')
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
'WMS Code', 'Title', 'Category', 'Zone', 'Location', 'Batch No','MRP','Reserved Quantity', 'Picked Quantity')


PRINT_PICKLIST_HEADERS = (
'WMS Code', 'Title', 'Zone', 'Location', 'Reserved Quantity', 'Picked Quantity', 'Units Of Measurement')

PROCESSING_HEADER = ('WMS Code', 'Title', 'Zone', 'Location', 'Reserved Quantity', 'Picked Quantity', '')

SKU_SUPPLIER_MAPPING = OrderedDict(
    [('Supplier ID', 'supplier__id'), ('SKU CODE', 'sku__wms_code'), ('Supplier Code', 'supplier_code'),
     ('Priority', 'preference'), ('MOQ', 'moq'), ('Costing Type', 'costing_type'), ('Margin Percentage', 'margin_percentage'), ('MRP', 'mrp')])

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
     ('Color', 'color'), ('Zone', 'zone_id'), ('Creation Date', 'creation_date'), ('Updation Date', 'updation_date'),
     ('Combo Flag', 'relation_type'), ('Status', 'status'), ('MRP', 'mrp'), ('HSN Code', 'hsn_code'), ('Tax Type', 'product_type')])

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
                                 ('GRN Approval', 'grn_approval'),('Allow Secondary Emails', 'allow_secondary_emails'),('RTV Mail','rtv_mail'),
                                 ))

# Configurations
PICKLIST_OPTIONS = {'Scan SKU': 'scan_sku', 'Scan SKU Location': 'scan_sku_location', 'Scan Serial': 'scan_serial',
                    'Scan Label': 'scan_label',
                    'Scan None': 'scan_none'}

BARCODE_OPTIONS = {'SKU Code': 'sku_code', 'Embedded SKU Code in Serial': 'sku_serial', 'EAN Number': 'sku_ean','SKU PACK':'sku_pack'}

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
                              ('Reserved Quantity', 'reserved_quantity'),('Mfg Date','manufactured_date'),
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
                                  ('Max Norm Quantity', 'max_norm_quantity'),
                                  ('Measurment Type', 'measurement_type'), ('Sale Through', 'sale_through'),
                                  ('Color', 'color'), ('EAN Number', 'ean_number'),
                                  ('Load Unit Handling(Options: Enable, Disable)', 'load_unit_handle'),
                                  ('HSN Code', 'hsn_code'), ('Sub Category', 'sub_category'),
                                  ('Hot Release', 'hot_release'),
                                  ('Mix SKU Attribute(Options: No Mix, Mix within Group)', 'mix_sku'),
                                  ('Status', 'status'), ('Shelf life', 'shelf_life'),
                                  ('Enable Serial Number', 'enable_serial_based'), ('Block For PO', 'block_options')
                                ))

SKU_DEF_EXCEL = OrderedDict((('wms_code', 0), ('sku_desc', 1), ('product_type', 2), ('sku_group', 3), ('sku_type', 4),
                             ('sku_category', 5), ('primary_category', 6), ('sku_class', 7), ('sku_brand', 8),
                             ('style_name', 9),
                             ('sku_size', 10), ('size_type', 11), ('zone_id', 12), ('cost_price', 13), ('price', 14),
                             ('mrp', 15), ('sequence', 16), ('image_url', 17), ('threshold_quantity', 18),('max_norm_quantity', 19),
                             ('measurement_type', 20),
                             ('sale_through', 21), ('color', 22), ('ean_number', 23), ('load_unit_handle', 24),
                             ('hsn_code', 25),
                             ('sub_category', 26), ('hot_release', 27), ('mix_sku', 28), ('combo_flag', 29), ('block_options', 30), ('status', 31)
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
                            ('price', 3),('cgst_tax',4),('sgst_tax',5),('igst_tax',6)))

CENTRAL_ORDER_XLS_UPLOAD = {'interm_order_id': '', 'sku': '', 'quantity': 1,
              'unit_price': 0, 'tax': 0, 'inter_state': 0, 'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0,
              'utgst_tax': 0, 'status': 0, 'project_name': '', 'remarks': '', 'customer_id': 0,
              'customer_name': '', 'shipment_date': datetime.datetime.now()}

SKU_PACK_EXCEL =OrderedDict((('sku_code', 0), ('pack_id', 1), ('pack_quantity', 2)))

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
                        'get_po_report':'get_po_report_data',
                        'get_open_order_report':'get_open_order_report_data',
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
                        'sku_wise_rtv_report': 'get_sku_wise_rtv_filter_data',
                        'get_current_stock_report': 'get_current_stock_report_data',
                        'get_inventory_value_report':'get_inventory_value_report_data',
                        'get_bulk_to_retail_report':'get_bulk_to_retail_report_data',
                        'get_stock_reconciliation_report': 'get_stock_reconciliation_report_data',
                        'get_margin_report':'get_margin_report_data',
                        'get_stock_cover_report':'get_stock_cover_report_data',
                        'get_order_flow_report':'get_orderflow_data',
                        'get_basa_report':'get_basa_report_data',
                        'get_move_inventory_report':'get_move_inventory_report_data',
                        'get_financial_report':'get_financial_report_data',
                        'get_bulk_stock_update':'get_bulk_stock_update_data',
                        }
# End of Download Excel Report Mapping

SHIPMENT_STATUS = ['Dispatched', 'In Transit', 'Out for Delivery', 'Delivered']

RWO_FIELDS = {'vendor_id': '', 'job_order_id': '', 'status': 1}

COMBO_SKU_EXCEL_HEADERS = ['SKU Code', 'Combo SKU', 'Combo Quantity']

RWO_PURCHASE_FIELDS = {'purchase_order_id': '', 'rwo_id': ''}

VENDOR_PICKLIST_FIELDS = {'jo_material_id': '', 'status': 'open', 'reserved_quantity': 0, 'picked_quantity': 0}

STAGES_FIELDS = {'stage_name': '', 'user': ''}

SIZES_LIST = ['S', 'M', 'L', 'XL', 'XXL', 'XXXL', 'FREE SIZE']

SKU_FIELD_TYPES = [{'field_name': 'sku_category', 'field_value': 'SKU Category'},
                   {'field_name': 'sku_brand', 'field_value': 'SKU Brand'},
                   {'field_name': 'sku_group', 'field_value': 'SKU Group'}]

PERMISSION_DICT = OrderedDict((
    # Notifications
    ("NOTIFICATION_LABEL", (("Notifications", "view_pushnotifications"), )),
    # Masters
    ("MASTERS_LABEL", (("SKU Master", "add_skumaster"), ("Location Master", "add_locationmaster"),
                       ("Supplier Master", "add_suppliermaster"), ("Source SKU Mapping", "add_skusupplier"),
                       ("Project Master", "add_corporatemaster"),
                       ("Reseller Corporate Mapping", "add_corpresellermapping"),
                       ("Customer Master", "add_customermaster"), ("Customer SKU Mapping", "add_customersku"),
                       ("BOM Master", "add_bommaster"), ("Staff Master", "add_staffmaster"),
                       ("Vendor Master", "add_vendormaster"), ("Discount Master", "add_categorydiscount"),
                       ("Custom SKU Template", "add_productproperties"), ("Size Master", "add_sizemaster"),
                       ('Pricing Master', 'add_pricemaster'), ('Network Master', 'add_networkmaster'),
                       ('Tax Master', 'add_taxmaster'), ('T&C Master', 'add_tandcmaster'),
                       ('Seller Master', 'add_sellermaster'), ('Seller Margin Mapping', 'add_sellermarginmapping'),
                       ('Staff Master', 'add_staffmaster'), ('Notification Master', 'add_pushnotifications'),
                       ('Cluster SKU Mapping', 'add_clusterskumapping'),
                       )),

    # Inbound
    ("INBOUND_LABEL", (("Raise PO", "add_openpo"), ("Confirm PO", "change_openpo"),
                       ("Receive PO", "add_purchaseorder"), ("Generate GRN", "change_purchaseorder"),
                       ("Quality Check", "add_qualitycheck"), ("Primary Segregation", "add_primarysegregation"),
                       ("Putaway Confirmation", "add_polocation"), ("Sales Returns", "add_orderreturns"),
                       ("Returns Putaway", "add_returnslocation"),
                       ("RTV", "add_returntovendor"), ("Seller Invoices", "add_sellerpo"),
                       ("Supplier Invoices", "change_sellerposummary"), ("GRN Edit", "delete_sellerposummary"),
                       )),

    # Production
    ("PRODUCTION_LABEL", (("Raise Job order", "add_jomaterial"), ("RM Picklist", "add_materialpicklist"),
                          ("Receive Job Order", "add_joborder"), ("Job Order Putaway", "add_rmlocation"))),

    # Stock Locator
    ("STOCK_LABEL", (("Stock Summary", "add_skustock"), ("Stock Detail", "add_stockdetail"),
                     ("Vendor Stock", "add_vendorstock"),
                     ("Cycle Count", "add_cyclecount"), ("Move Inventory", "change_inventoryadjustment"),
                     ("Inventory Adjustment", "add_inventoryadjustment"),
                     ("Warehouse Stock", "add_usergroups"), ("IMEI Tracker", "add_poimeimapping"),
                     ("Seller Stock", "add_sellerstock"), ("View BA to SA", "view_skuclassification"),
                     ("Calculate BA to SA", "add_skuclassification"), ("Confirm BA to SA", "change_skuclassification"))),

    # Outbound
    ("OUTBOUND_LABEL", (("Create Orders", "add_orderdetail"), ("View Orders", "add_picklist"),
                        ("Pull Confirmation", "add_picklistlocation"), ("Enquiry Orders", "add_enquirymaster"),
                        ("Customer Invoices", "add_sellerordersummary"), ("Manual Orders", "add_manualenquiry"),
                        ("Shipment Info", "add_shipmentinfo"), ("Create Stock Transfer", "add_stocktransfer"),
                        )),

    # Shipment Info
    ("SHIPMENT_LABEL", ("Shipment Info", "add_shipmentinfo")),

    # Others
    ("OTHERS_LABEL", (("Raise Stock Transfer", "add_openst"), ("Create Stock Transfer", "add_stocktransfer"))),

    # Payment
    ("PAYMENT_LABEL", (("PAYMENTS", "add_paymentsummary"),)),

    # Uploads
    ("UPLOADS", (('Create Orders', 'add_orderdetail'), ('SKU Master', 'add_skumaster'),
                                    ('Stock Detail', 'add_stockdetail'), ('Supplier Master', 'add_suppliermaster'),
                                    ('add_skusupplier', 'add_skusupplier'), ('add_locationmaster', 'add_locationmaster'),
                                    ('Raise PO', 'add_openpo'),
                                    ('change_inventoryadjustment', 'change_inventoryadjustment'),
                                    ('add_bommaster', 'add_bommaster'),
                                    ('add_inventoryadjustment', 'add_inventoryadjustment'),
                                    ('add_vendormaster', 'add_vendormaster'),
                                    ('add_customermaster', 'add_customermaster'),
                                    ('add_orderreturns', 'add_orderreturns'), ('add_pricemaster', 'add_pricemaster'),
                                    ('add_networkmaster', 'add_networkmaster'), ('add_orderlabels', 'add_orderlabels'),
                                    ('add_jomaterial', 'add_jomaterial'),
                                    ('Intermediate Orders', 'add_intermediateorders'),
                                    ('add_sellerstocktransfer', 'add_sellerstocktransfer'),
                                    ('add_substitutionsummary', 'add_substitutionsummary'),
                                    ('add_targetmaster', 'add_targetmaster'),
                                    ('add_enquirymaster', 'add_enquirymaster'),
                                    ('add_clusterskumapping', 'add_clusterskumapping'),
                 )),
    ("REPORTS", (('SKU List Report', 'view_skumaster'),('Location Wise Filter Report', 'view_locationmaster'),
                 ('Goods Receipt Note Report', 'view_sellerposummary'), ('Receipt Summary Report', 'view_polocation'),
                 ('Dispatch Summary Report', 'view_picklist'), ('SKU Wise Stock Report', 'view_stockdetail'),
                 ('SKU Wise PO Report', 'view_openpo'), ('Supplier Wise PO Report', 'view_purchaseorder'),
                 ('Sales Return Report', 'view_orderreturns'),
                 ('Inventory Adjustment Report', 'view_inventoryadjustment'),
                 ('Inventory Aging Report', 'view_cyclecount'), ('Stock Summary Report', 'change_stockdetail'),
                 ('Daily Production Report', 'view_statustracking'), ('Order Summary Report', 'view_orderdetail'),
                 ('Open JO Report', 'view_openjo'), ('Seller Invoice Detail Report', 'view_sellerpo'),
                 ('RM Picklist Report', 'view_materialpicklist'), ('Stock Ledger Report', 'view_stockstats'),
                 ('Shipment Report', 'view_ordershipment'), ('RTV Report', 'view_returntovendor'),
                 ('Current Stock Report', 'view_skudetailstats'),
                 ('Inventory Value Report', 'delete_skudetailstats'),
                 ('Stock Cover Report' ,'add_skudetailstats'),
                 ('MoveInventory Report','view_moveinventory'),
                 ('Bulk To Retail Report', 'view_substitutionsummary'))),

    # Uploaded POs
    ("UPLOADPO_LABEL", (("uploadedPOs", "add_orderuploads"),)),
     #Configurations
    ("CONFIGURATIONS", (("Configutaions", "add_miscdetail"),)),

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
                                      ('color', 'color'), ('cost_price', 'cost_price'),
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

ORDER_SUMMARY_FIELDS = OrderedDict((('discount', 0), ('creation_date', datetime.datetime.now()), ('issue_type', 'order'),
                                    ('tax_value', 0),
                                    ('order_taken_by', ''), ('sgst_tax', 0), ('cgst_tax', 0), ('igst_tax', 0), ('cess_tax', 0),
                                    ('mrp', 0), ('inter_state', 0), ('consignee', ''), ('utgst_tax', 0), ('vat', 0)))

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

SELLER_ORDER_FIELDS = OrderedDict((('sor_id', ''), ('quantity', 0), ('order_status', ''), ('order_id', ''), ('seller_id', ''), ('status', 1),
                                   ('invoice_no', '')))

SELLER_MARGIN_DICT = {'seller_id': '', 'sku_id': '', 'margin': 0}

RECEIVE_OPTIONS = OrderedDict((('One step Receipt + Qc', 'receipt-qc'), ('Two step Receiving', '2-step-receive')))

PERMISSION_IGNORE_LIST = ['session', 'webhookdata', 'swxmapping', 'userprofile', 'useraccesstokens', 'contenttype',
                          'user',
                          'permission', 'group', 'logentry', 'corsmodel', 'subzonemapping']

# Customer Invoices page headers based on user type
MP_CUSTOMER_INVOICE_HEADERS = ['UOR ID', 'SOR ID', 'Seller ID', 'Customer Name', 'Order Quantity', 'Picked Quantity',
                               'Total Amount', 'Order Date&Time',
                               'Invoice Number']

WH_CUSTOMER_INVOICE_HEADERS = ['Order ID', 'Customer Name', 'Order Quantity', 'Picked Quantity', 'Order Date&Time',
                               'Total Amount']
WH_CUSTOMER_INVOICE_HEADERS_TAB = ['Financial Year', 'Customer Name', 'Order Quantity', 'Picked Quantity', 'Invoice Date&Time', 'Total Amount']

STOCK_TRANSFER_INVOICE_HEADERS = ['Stock Transfer ID', 'Warehouse Name', 'Picked Quantity', 'Stock Transfer Date&Time','Invoice Number','Total Amount']

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
                                     ('account_holder_name', 28), ('secondary_email_id', 29),
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

PO_SERIAL_EXCEL_HEADERS = ['Supplier ID', 'Processed Date(yyyy-mm-dd)', 'Location', 'SKU Code', 'Po Reference Number', 'Unit Price', 'Serial Number', 'LR Number', 'Invoice No', 'IGST(%)', 'CGST(%)', 'SGST(%)']

PO_SERIAL_EXCEL_MAPPING = OrderedDict((('supplier_id', 0), ('process_date', 1), ('location', 2), ('sku_code', 3), ('po_reference_no', 4), ('unit_price', 5),
                                       ('imei_number', 6), ('lr_number', 7), ('invoice_num', 8),  ('igst_tax', 9), ('cgst_tax', 10), ('sgst_tax', 11) ))

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
                      'aidin_technologies': 'aidin_tech.jpg', 'nutricane': 'nutricane.jpg',
                      '72Networks':'72networks.png'}

TOP_COMPANY_LOGO_PATHS = {'Konda_foundation': 'dr_reddy_logo.png', 'acecraft':'acecraft.jpg'}

ISO_COMPANY_LOGO_PATHS = {'aidin_technologies': 'iso_aidin_tech.jpg'}

LEFT_SIDE_COMPNAY_LOGO = {'Skinstore': 'skin_store.png'}

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
                        'batch_switch': 'batch_switch', 'decimal_limit_price':'decimal_limit_price',
                        'view_order_status': 'view_order_status', 'label_generation': 'label_generation',
                        'grn_scan_option': 'grn_scan_option',
                        'show_imei_invoice': 'show_imei_invoice', 'style_headers': 'style_headers',
                        'picklist_sort_by': 'picklist_sort_by',
                        'barcode_generate_opt': 'barcode_generate_opt', 'online_percentage': 'online_percentage',
                        'mail_alerts': 'mail_alerts',
                        'detailed_invoice': 'detailed_invoice', 'invoice_titles': 'invoice_titles',
                        'show_image': 'show_image','repeat_po':'repeat_po',
                        'auto_generate_picklist': 'auto_generate_picklist', 'auto_po_switch': 'auto_po_switch',
                        'fifo_switch': 'fifo_switch',
                        'loc_serial_mapping_switch':'loc_serial_mapping_switch',
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
                        'order_exceed_stock': 'order_exceed_stock', 'sku_pack_config': 'sku_pack_config',
                        'central_order_reassigning':'central_order_reassigning',
                        'po_sub_user_prefix': 'po_sub_user_prefix',
                        'combo_allocate_stock': 'combo_allocate_stock',
                        'dispatch_qc_check': 'dispatch_qc_check',
                        'unique_mrp_putaway': 'unique_mrp_putaway',
                        'sku_less_than_threshold':'sku_less_than_threshold',
                        'block_expired_batches_picklist': 'block_expired_batches_picklist',
                        'generate_delivery_challan_before_pullConfiramation':'generate_delivery_challan_before_pullConfiramation',
                        'non_transacted_skus':'non_transacted_skus',
                        'allow_rejected_serials':'allow_rejected_serials',
                        'update_mrp_on_grn': 'update_mrp_on_grn',
                        'mandate_sku_supplier':'mandate_sku_supplier',
                        'brand_categorization':'brand_categorization',
                        'purchase_order_preview':'purchase_order_preview',
                        'picklist_sort_by_sku_sequence': 'picklist_sort_by_sku_sequence',
                        'stop_default_tax':'stop_default_tax',
                        'supplier_mapping':'supplier_mapping',
                        'show_mrp_grn': 'show_mrp_grn',
                        'display_dc_invoice': 'display_dc_invoice',
                        'display_order_reference': 'display_order_reference',
                        'mandate_invoice_number':'mandate_invoice_number',
                        }

CONFIG_INPUT_DICT = {'email': 'email', 'report_freq': 'report_frequency',
                     'scan_picklist_option': 'scan_picklist_option',
                     'data_range': 'report_data_range', 'imei_limit': 'imei_limit',
                     'invoice_remarks': 'invoice_remarks',
                     'invoice_declaration':'invoice_declaration',
                     'pos_remarks':'pos_remarks',
                     'raisepo_terms_conditions':'raisepo_terms_conditions',
                     'invoice_marketplaces': 'invoice_marketplaces', 'serial_limit': 'serial_limit',
                     'extra_view_order_status': 'extra_view_order_status',
                     'bank_option_fields':'bank_option_fields',
                     'invoice_types': 'invoice_types',
                     'mode_of_transport': 'mode_of_transport',
                     'shelf_life_ratio': 'shelf_life_ratio',
                     'auto_expire_enq_limit': 'auto_expire_enq_limit',
                     'sales_return_reasons': 'sales_return_reasons',
                     'rtv_prefix_code': 'rtv_prefix_code',
                     'weight_integration_name': 'weight_integration_name',
                     'delivery_challan_terms_condtions': 'delivery_challan_terms_condtions',
                     'order_prefix': 'order_prefix',
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
                                      ('Quantity', 'quantity'), ('Price', 'price'),('Cgst(%)','cgst_tax'),('Sgst(%)','sgst_tax'),('Igst(%)','igst_tax')
                                   ))

CENTRAL_ORDER_ONE_ASSIST_MAPPING = OrderedDict((
                                      ('Main SR Number', 'original_order_id'),
                                      ('Customer Name', 'customer_name'), ('Address', 'address'),
                                      ('City', 'city'), ('Pincode', 'pincode'),
                                      ('Customer primary contact', 'mobile_no'), ('Customer emailId', 'email_id'),
                                      ('Customer handset Model', 'sku_code')))
SKU_PACK_MAPPING = OrderedDict((('Sku Code', 'sku_code'), ('Pack ID', 'pack_id'),
                                      ('Pack Quantity', 'pack_quantity')))
# SKU_PACK_MAPPING = OrderedDict((('Sku Code', 'sku_code'), ('Pack ID', 'pack_id'), ('Pack Quantity', 'pack_quantity')))
BLOCK_STOCK_MAPPING = OrderedDict((
    ('Sku Code', 'sku_code'), ('Quantity', 'quantity'), ('Client Name', 'corporate_name'),
    ('Reseller Name', 'reseller_name'), ('Warehouse Name', 'warehouse'), ('Level', 'level')
    ))

BLOCK_STOCK_DEF_EXCEL = OrderedDict((
    ('sku_code', 0), ('quantity', 1), ('corporate_name', 2), ('reseller_name', 3), ('warehouse', 4), ('level', 5)))

PO_TEMP_JSON_DEF = {"scan_sku": "", "weight": "", "lr_number": "", "display_approval_button": "false",
                         "remainder_mail": "0", "exp_date": "", "carrier_name": "", "id": "", "unit": "",
                         "supplier_id": "", "expected_date": "", "discount_percentage": "", "buy_price": "0",
                         "cess_percent": "0", "price": "0", "sku_index": "0", "invoice_date": "",
                         "po_quantity": "0", "new_sku": "", "wms_code": "", "remarks": "", "invoice_number": "",
                         "tax_percent": "0", "invoice_value": "", "mrp": "0", "mfg_date": "", "batch_no": "",
                         "quantity": "0", "apmc_percent": "0"}


CUSTOM_ORDER_MAPPING = OrderedDict((
    ('Reseller Name', 'reseller_name'), ('Client Name', 'customer_name'), ('Sku Code', 'sku_code'),
    ('Customization Type', 'customization_type'), ('Ask Price Per Unit', 'ask_price'), ('Quantity', 'quantity'),
    ('Apprx Client PO Rate', 'client_po_rate'), ('Approximate Delivery Date', 'expected_date'),
    ('Remarks', 'remarks')
    ))

CUSTOM_ORDER_DEF_EXCEL = OrderedDict((
    ('reseller_name', 0), ('customer_name', 1), ('sku_code', 2), ('customization_type', 3), ('ask_price', 4),
    ('quantity', 5), ('client_po_rate', 6), ('expected_date', 7), ('remarks', 8)))

CLUSTER_SKU_MAPPING = OrderedDict((
                                  ('Cluster Name', 0),
                                  ('Sku Code', 1), ('Sequence', 2)))

BATCH_DETAIL_HEADERS = ['Receipt Number', 'Receipt Date', 'WMS Code', 'Product Description', 'SKU Category', 'Batch Number', 'MRP', 'Weight',
                        'Price', 'Tax Percent', 'Manufactured Date', 'Expiry Date', 'Zone', 'Location', 'Quantity', 'Receipt Type']

SKU_NAME_FIELDS_MAPPING = OrderedDict((('Brand', 'sku_brand'), ('Category', 'sku_category')))

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

    cmp_data = ('sku_code', 'wms_code', 'sku_category', 'sku_type', 'sku_class','sub_category','sku_brand')
    for data in cmp_data:
        if data in search_params:
            search_parameters['%s__%s' % (data, 'iexact')] = search_params[data]
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['skuattributes__attribute_value'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['skuattributes__attribute_value'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['skuattributes__attribute_value'] = search_params['bundle']

    search_parameters['user'] = user.id
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    sku_master = sku_master.filter(**search_parameters)

    temp_data['recordsTotal'] = len(sku_master)
    temp_data['recordsFiltered'] = len(sku_master)

    if stop_index:
        sku_master = sku_master[start_index:stop_index]

    zone = ''
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for data in sku_master:
        manufacturer,searchable,bundle = '','',''
        if data.zone:
            zone = data.zone.zone
        attributes_obj = SKUAttributes.objects.filter(sku_id=data.id, attribute_name__in= attributes_list)

        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value

        ord_dict = OrderedDict((('SKU Code', data.sku_code), ('WMS Code', data.wms_code), ('SKU Group', data.sku_group),
                     ('SKU Type', data.sku_type), ('SKU Category', data.sku_category),
                     ('Sub Category', data.sub_category),('SKU Brand', data.sku_brand),
                     ('SKU Class', data.sku_class),
                     ('Put Zone', zone), ('Threshold Quantity', data.threshold_quantity)))
        if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            ord_dict['Manufacturer'] = manufacturer
            ord_dict['Searchable'] = searchable
            ord_dict['Bundle'] = bundle

        temp_data['aaData'].append(ord_dict)

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
                      'sub_category': 'sku__sub_category__iexact', 'sku_brand': 'sku__sku_brand__iexact',
                      'zone': 'location__zone__zone__iexact',
                      'location': 'location__location__iexact', 'wms_code': 'sku__wms_code', 'ean': 'sku__ean_number__iexact'}
    results_data['draw'] = search_params.get('draw', 1)
    for key, value in search_mapping.iteritems():
        if key in search_params:
            search_parameters[value] = search_params[key]
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['sku__skuattributes__attribute_value'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['sku__skuattributes__attribute_value'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['sku__skuattributes__attribute_value'] = search_params['bundle']
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    stock_detail = []
    search_parameters['quantity__gt'] = 0
    search_parameters['sku__user'] = user.id
    search_parameters['sku_id__in'] = sku_master_ids
    distinct_list = ['sku__wms_code', 'sku__sku_desc', 'sku__sku_category', 'sku__sku_brand']
    lis = ['sku__wms_code', 'sku__sku_category', 'sku__sub_category', 'sku__sku_brand', 'sku__sku_desc', 'sku__ean_number', 'batch_detail__mrp', 'location__zone__zone', 'location__location',
           'tsum', 'tsum', 'tsum','tsum', 'tsum', 'tsum']
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

    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        stock_detail = OrderedDict(stock_detail.annotate(grouped_val=Concat('sku__sku_code', Value('<<>>'), 'location__location', Value('<<>>'), 'batch_detail__mrp', Value('<<>>'),'batch_detail__weight', output_field=CharField())).values_list('grouped_val').distinct().annotate(tsum=Sum('quantity')))
    else:
        stock_detail = OrderedDict(stock_detail.annotate(grouped_val=Concat('sku__sku_code', Value('<<>>'), 'location__location', output_field=CharField())).values_list('grouped_val').distinct().annotate(tsum=Sum('quantity')))

    results_data['recordsTotal'] = len(stock_detail)
    results_data['recordsFiltered'] = results_data['recordsTotal']
    stock_detail_keys = stock_detail.keys()
    if stop_index:
        stock_detail_keys = stock_detail_keys[start_index:stop_index]
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        picklist_reserved = dict(PicklistLocation.objects.filter(status=1, stock__sku__user=user.id).\
                             annotate(grouped_val=Concat('stock__sku__wms_code', Value('<<>>'),
                             'stock__location__location', Value('<<>>'), 'stock__batch_detail__mrp', output_field=CharField())).\
                             values_list('grouped_val').distinct().annotate(reserved=Sum('reserved')))
        raw_reserved = dict(RMLocation.objects.filter(status=1, stock__sku__user=user.id).\
                        annotate(grouped_val=Concat('material_picklist__jo_material__material_code__wms_code',
                        Value('<<>>'), 'stock__location__location', Value('<<>>'), 'stock__batch_detail__mrp',
                        output_field=CharField())).values_list('grouped_val').distinct().\
                        annotate(rm_reserved=Sum('reserved')))
    else:
        picklist_reserved = dict(PicklistLocation.objects.filter(status=1, stock__sku__user=user.id).\
                             annotate(grouped_val=Concat('stock__sku__wms_code', Value('<<>>'),
                             'stock__location__location', output_field=CharField())).\
                             values_list('grouped_val').distinct().annotate(reserved=Sum('reserved')))
        raw_reserved = dict(RMLocation.objects.filter(status=1, stock__sku__user=user.id).\
                        annotate(grouped_val=Concat('material_picklist__jo_material__material_code__wms_code',
                        Value('<<>>'), 'stock__location__location',
                        output_field=CharField())).values_list('grouped_val').distinct().\
                        annotate(rm_reserved=Sum('reserved')))
    for stock_detail_key in stock_detail_keys:
        total_stock_value = 0
        reserved = 0
        mrp = 0
        weight = 0
        total = stock_detail[stock_detail_key]
        if  user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            sku_code, location, mrp, weight = stock_detail_key.split('<<>>')
        else:
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
        attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
        manufacturer,searchable,bundle = '','',''
        attributes_obj = SKUAttributes.objects.filter(sku_id=sku_master.id, attribute_name__in= attributes_list)
        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value

        ord_dict = OrderedDict((('SKU Code', sku_master.sku_code), ('WMS Code', sku_master.wms_code),
                                                   ('SKU Category', sku_master.sku_category),
                                                   ('SKU Sub Category', sku_master.sub_category),
                                                   ('SKU Brand', sku_master.sku_brand),
                                                   ('Product Description', sku_master.sku_desc),
                                                   ('EAN', str(ean_num)),
                                                   ('MRP', mrp),
                                                   ('Weight', weight),
                                                   ('Zone', location_master.zone.zone),
                                                   ('Location', location_master.location), ('Total Quantity', total),
                                                   ('Available Quantity', quantity), ('Reserved Quantity', reserved),
                                                 ))

        if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            ord_dict['Manufacturer'] = manufacturer
            ord_dict['Searchable'] = searchable
            ord_dict['Bundle'] = bundle
        results_data['aaData'].append(ord_dict)
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
           'updation_date', 'reason', 'order_id', 'order_id', 'order_id', 'order_id', 'order_id', 'order_id', 'order_id']
    model_obj = PurchaseOrder
    if use_imei == 'true':
        lis = ['purchase_order__open_po__supplier__name', 'purchase_order__order_id',
               'purchase_order__open_po__sku__wms_code',
               'purchase_order__open_po__sku__sku_desc', 'imei_number', 'creation_date', 'purchase_order__reason', 'purchase_order__reason', 'purchase_order__reason', 'purchase_order__reason', 'purchase_order__reason']
        query_prefix = 'purchase_order__'
        model_obj = POIMEIMapping
        if 'from_date' in search_params:
            search_parameters[query_prefix + 'creation_date__gte'] = search_params['from_date']
        else:
            search_parameters[query_prefix + 'creation_date__gte'] = date.today()+relativedelta(months=-1)
        if 'to_date' in search_params:
            search_parameters[query_prefix + 'creation_date__lt'] = search_params['to_date']
    else:
        if 'from_date' in search_params:
            search_parameters[query_prefix + 'updation_date__gte'] = search_params['from_date']
        else:
            search_parameters[query_prefix + 'updation_date__gte'] = date.today()+relativedelta(months=-1)
        if 'to_date' in search_params:
            search_parameters[query_prefix + 'updation_date__lt'] = search_params['to_date']
    temp_data = copy.deepcopy(AJAX_DATA)
    temp_data['draw'] = search_params.get('draw')

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    if 'supplier' in search_params:
        search_parameters[query_prefix + 'open_po__supplier__id__iexact'] = search_params['supplier']
    if 'wms_code' in search_params:
        search_parameters[query_prefix + 'open_po__sku__wms_code__iexact'] = search_params['wms_code']
    if 'sku_code' in search_params:
        search_parameters[query_prefix + 'open_po__sku__sku_code__iexact'] = search_params['sku_code']
    if 'sku_category' in search_params:
        search_parameters[query_prefix + 'open_po__sku__sku_category__iexact'] = search_params['sku_category']
    if 'sub_category' in search_params:
        search_parameters[query_prefix + 'open_po__sku__sub_category__iexact'] = search_params['sub_category']
    if 'sku_brand' in search_params:
        search_parameters[query_prefix + 'open_po__sku__sku_brand__iexact'] = search_params['sku_brand']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters[query_prefix + 'open_po__sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters[query_prefix + 'open_po__sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters[query_prefix + 'open_po__sku__skuattributes__attribute_value__iexact'] = search_params['bundle']
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
        updated_user_name = user.username
        version_obj = Version.objects.get_for_object(data)
        if version_obj.exists():
            updated_user_name = version_obj.order_by('-revision__date_created')[0].revision.user.username
        attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
        manufacturer,searchable,bundle = '','',''
        attributes_obj = SKUAttributes.objects.filter(sku_id=data.open_po.sku.id, attribute_name__in= attributes_list)
        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value
        ord_dict = OrderedDict((('PO Number', po_reference), ('WMS Code', data.open_po.sku.wms_code),
                                                ('SKU Category', data.open_po.sku.sku_category),
                                                ('SKU Sub Category', data.open_po.sku.sub_category),
                                                ('Sku Brand', data.open_po.sku.sku_brand),
                                                ('Description', data.open_po.sku.sku_desc),
                                                ('Supplier',
                                                 '%s (%s)' % (data.open_po.supplier.name, data.open_po.supplier_id)),
                                                ('Receipt Number', data.open_po_id),
                                                ('Received Quantity', data.received_quantity),
                                                ('Serial Number', serial_number), ('Received Date', received_date),
                                                ('Closing Reason', reason), ('Updated User', updated_user_name)))
        if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            ord_dict['Manufacturer'] = manufacturer
            ord_dict['Searchable'] = searchable
            ord_dict['Bundle'] = bundle

        temp_data['aaData'].append(ord_dict)
    return temp_data


def get_dispatch_data(search_params, user, sub_user, serial_view=False, customer_view=False):
    from miebach_admin.models import *
    from miebach_admin.views import *
    from rest_api.views.common import get_sku_master, get_order_detail_objs, get_utc_start_date
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    search_parameters = {}
    warehouse_users = {}
    central_order_mgmt = get_misc_value('central_order_mgmt', user.id)
    if customer_view:
        lis = ['order__customer_id', 'order__customer_name', 'order__sku__wms_code', 'order__sku__sku_desc',
               'order__sku__sku_category', 'order__sku__sub_category','order__sku__sku_brand', 'order__sku__user',
               'order__sku__sub_category','order__sku__sku_brand', 'order__sku__user']#'order__quantity', 'picked_quantity']
        model_obj = Picklist
        param_keys = {'wms_code': 'order__sku__wms_code', 'sku_code': 'order__sku__sku_code','manufacturer':'order__sku__skuattributes__attribute_value__iexact'}
        search_parameters.update({'status__in': ['open', 'batch_open', 'picked', 'batch_picked', 'dispatched'],
                                  #'picked_quantity__gt': 0,
                                  'stock__gt': 0,
                                  # 'order__user': user.id,
                                  # 'order__sku_id__in': sku_master_ids
                                })
    else:
        if serial_view:
            lis = ['order__order_id', 'order__sku__wms_code', 'order__sku__sku_desc', 'order__sku__sku_category', 'order__sku__sub_category','order__sku__sku_brand', 'order__customer_name',
                   'po_imei__imei_number','updation_date', 'updation_date','updation_date', 'updation_date',
                   'updation_date', 'updation_date']
            model_obj = OrderIMEIMapping
            param_keys = {'wms_code': 'order__sku__wms_code', 'sku_code': 'order__sku__sku_code','manufacturer':'order__sku__skuattributes__attribute_value__iexact'}
            search_parameters['status'] = 1
            # search_parameters['order__user'] = user.id
            # search_parameters['order__sku_id__in'] = sku_master_ids
        else:
            lis = ['order__order_id', 'order__sku__wms_code', 'order__sku__wms_code', 'order__sku__wms_code',
                   'order__sku__wms_code', 'order__sku__wms_code', 'order__sku__sku_desc', 'order__sku__sku_category','order__sku__sub_category','order__sku__sku_brand',
                   'stock__location__location', 'picked_quantity', 'picked_quantity', 'order__unit_price', 'order_id',
                   'stock__batch_detail__buy_price', 'stock__batch_detail__tax_percent', 'stock_id', 'updation_date', 'updation_date',
                   'order__customer_name', 'stock__batch_detail__batch_no', 'stock__batch_detail__mrp',
                   'stock__batch_detail__manufactured_date', 'stock__batch_detail__expiry_date',
                   'stock__batch_detail__manufactured_date', 'stock__batch_detail__expiry_date',
                   'stock__batch_detail__manufactured_date', 'stock__batch_detail__expiry_date']
            model_obj = Picklist
            param_keys = {'wms_code': 'order__sku__wms_code', 'sku_code': 'order__sku__sku_code','manufacturer':'order__sku__skuattributes__attribute_value__iexact'}
            search_parameters['status__in'] = ['open', 'batch_open', 'picked', 'batch_picked', 'dispatched']
            search_parameters['picked_quantity__gt'] = 0
            #search_parameters['stock__gt'] = 0

    temp_data = copy.deepcopy(AJAX_DATA)

    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_params['from_date'] = get_utc_start_date(search_params['from_date'])
        search_parameters['updation_date__gte'] = search_params['from_date']
    else:
        search_parameters['updation_date__gte'] = date.today()+relativedelta(months=-1)
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_params['to_date'] = get_utc_start_date(search_params['to_date'])
        search_parameters['updation_date__lt'] = search_params['to_date']
    if 'wms_code' in search_params:
        search_parameters[param_keys['wms_code']] = search_params['wms_code']
    if 'sku_code' in search_params:
        search_parameters[param_keys['sku_code']] = search_params['sku_code']
    if 'customer_id' in search_params:
        search_parameters['order__customer_id'] = search_params['customer_id']
    if 'imei_number' in search_params and serial_view:
        search_parameters['po_imei__imei_number'] = search_params['imei_number']
    if 'sku_category' in search_params:
        search_parameters['order__sku__sku_category'] = search_params['sku_category']
    if 'sub_category' in search_params:
        search_parameters['order__sku__sub_category'] = search_params['sub_category']
    if 'sku_brand' in search_params:
        search_parameters['order__sku__sku_brand'] = search_params['sku_brand']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['order__sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['order__sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['order__sku__skuattributes__attribute_value__iexact'] = search_params['bundle']

    if user.userprofile.warehouse_type == 'admin':
        if 'sister_warehouse' in search_params:
            sister_warehouse_name = search_params['sister_warehouse']
            user = User.objects.get(username=sister_warehouse_name)
            warehouses = UserGroups.objects.filter(user_id=user.id)
        else:
            warehouses = UserGroups.objects.filter(admin_user_id=user.id)
        warehouse_users = dict(warehouses.values_list('user_id', 'user__username'))
        sku_master = SKUMaster.objects.filter(user__in=warehouse_users.keys())
        sku_master_ids = sku_master.values_list('id', flat=True)
    else:
        search_parameters['order__user'] = user.id
    search_parameters['order__sku_id__in'] = sku_master_ids
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
                               .annotate(qty=Sum('order__original_quantity'), tot_count=Count('order__original_quantity'))\
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

    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for data in model_data:
        if customer_view:
            manufacturer,searchable,bundle = '','',''
            if data['order__sku__wms_code']:
                sku_code_attr = data['order__sku__wms_code']
            if sku_code_attr:
                attributes_obj = SKUAttributes.objects.filter(sku__sku_code=sku_code_attr, attribute_name__in= attributes_list)
                if attributes_obj.exists():
                    for attribute in attributes_obj:
                        if attribute.attribute_name == 'Manufacturer':
                            manufacturer = attribute.attribute_value
                        if attribute.attribute_name == 'Searchable':
                            searchable = attribute.attribute_value
                        if attribute.attribute_name == 'Bundle':
                            bundle = attribute.attribute_value

            ord_dict = OrderedDict((('Customer ID', data['order__customer_id']),
                                                    ('Customer Name', data['order__customer_name']),
                                                    ('WMS Code', data['order__sku__wms_code']),
                                                    ('Description', data['order__sku__sku_desc']),
                                                    ('SKU Category', data['order__sku__sku_category']),
                                                    ('Sub Category', data['order__sku__sub_category']),
                                                    ('SKU Brand', data['order__sku__sku_brand']),
                                                    ('Quantity', data['qty']),
                                                    ('Picked Quantity', data['loc_qty'] - data['res_qty']),
                                                    ('Warehouse', warehouse_users.get(data['order__sku__user']))
                                                  ))
            if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
                ord_dict['Manufacturer'] = manufacturer
                ord_dict['Searchable'] = searchable
                ord_dict['Bundle'] = bundle
            temp_data['aaData'].append(ord_dict)
        else:
            manufacturer,searchable,bundle = '','',''
            if data.order.sku.sku_code:
                sku_code_attr = data.order.sku.sku_code
            if sku_code_attr:
                attributes_obj = SKUAttributes.objects.filter(sku__user=user.id, sku__sku_code=sku_code_attr, attribute_name__in= attributes_list)
                if attributes_obj.exists():
                    for attribute in attributes_obj:
                        if attribute.attribute_name == 'Manufacturer':
                            manufacturer = attribute.attribute_value
                        if attribute.attribute_name == 'Searchable':
                            searchable = attribute.attribute_value
                        if attribute.attribute_name == 'Bundle':
                            bundle = attribute.attribute_value

            if not serial_view:
                child_sku_weight = ''
                child_sku_code = ''
                child_sku_mrp = ''
                wms_code_mrp = 0
                cost_price = 0
                tax_percent = 0
                cost_tax_percent = 0
                cod = data.order.customerordersummary_set.filter()
                if cod:
                    cod = cod[0]
                    if cod.cgst_tax:
                        tax_percent = cod.cgst_tax + cod.sgst_tax
                    else:
                        tax_percent = cod.igst_tax
                customer_name = data.order.customer_name if data.order.customer_name else ''
                if data.stock and data.stock.batch_detail:
                    batch_number = data.stock.batch_detail.batch_no
                    batchDetail_mrp = data.stock.batch_detail.mrp
                    child_sku_weight = data.stock.batch_detail.weight
                    batchDetail_mfgdate = data.stock.batch_detail.manufactured_date.strftime("%d %b %Y") if data.stock.batch_detail.manufactured_date else ''
                    batchDetail_expdate = data.stock.batch_detail.expiry_date.strftime("%d %b %Y") if data.stock.batch_detail.expiry_date else ''
                else:
                    batch_number = batchDetail_mrp = batchDetail_mfgdate = batchDetail_expdate = ''
                if not data.stock:
                    date = get_local_date(user, data.updation_date).split(' ')
                    order_id = data.order.original_order_id
                    if not order_id:
                        order_id = str(data.order.order_code) + str(data.order.order_id)
                    if data.order.sku.mrp:
                        wms_code_mrp = data.order.sku.mrp
                    if data.order_type == 'combo':
                        child_sku_code = data.sku_code
                        child_sku_mrp = SKUMaster.objects.filter(user=user.id, sku_code = data.sku_code).values('mrp')[0]['mrp']
                    ord_dict = OrderedDict((('Order ID', order_id), ('WMS Code', data.order.sku.sku_code),
                                                            ('WMS MRP', wms_code_mrp),('Child SKU', child_sku_code),
                                                            ('Child SKU MRP', child_sku_mrp),('Child SKU Weight', child_sku_weight),
                                                            ('Description', data.order.sku.sku_desc),
                                                            ('SKU Category', data.order.sku.sku_category),
                                                            ('Sub Category',data.order.sku.sub_category),
                                                            ('SKU Brand', data.order.sku.sku_brand),
                                                            ('Location', 'NO STOCK'),
                                                            ('Quantity', data.order.original_quantity),
                                                            ('Picked Quantity', data.picked_quantity),
                                                            ('Selling Price', data.order.unit_price), ('Sale Tax Percent', tax_percent),
                                                            ('Cost Price', cost_price), ('Cost Tax Percent', cost_tax_percent),
                                                            ('Date', ' '.join(date[0:3])), ('Time', ' '.join(date[3:5])), ('Customer Name', customer_name),
                                            ))
                    if user.userprofile.industry_type == 'FMCG':
                        ord_dict['Batch Number'] = batch_number
                        ord_dict['MRP'] = batchDetail_mrp
                        ord_dict['Manufactured Date'] = batchDetail_mfgdate
                        ord_dict['Expiry Date'] = batchDetail_expdate
                    ord_dict['Warehouse'] = warehouse_users.get(data.order.user)
                    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
                        ord_dict['Manufacturer'] = manufacturer
                        ord_dict['Searchable'] = searchable
                        ord_dict['Bundle'] = bundle
                    temp_data['aaData'].append(ord_dict)
                pick_locs = data.picklistlocation_set.exclude(reserved=0, quantity=0)
                for pick_loc in pick_locs:
                    picked_quantity = float(pick_loc.quantity) - float(pick_loc.reserved)
                    date = get_local_date(user, data.updation_date).split(' ')
                    order_id = data.order.original_order_id
                    if not order_id:
                        order_id = str(data.order.order_code) + str(data.order.order_id)
                    if data.order_type == 'combo':
                        if data.stock:
                            if data.stock and data.stock.batch_detail:
                                child_sku_weight = data.stock.batch_detail.weight
                            child_sku_code = data.stock.sku.sku_code
                            child_sku_mrp = SKUMaster.objects.filter(user=user.id, sku_code = data.stock.sku.sku_code).values('mrp')[0]['mrp']
                        else:
                            child_sku_code = data.order.sku.sku_code
                            child_sku_mrp = SKUMaster.objects.filter(user=user.id, sku_code = data.order.sku.sku_code).values('mrp')[0]['mrp']
                    cost_price = 0
                    if data.stock and data.stock.batch_detail:
                        cost_price = '%.2f' %(data.stock.batch_detail.buy_price)
                        cost_tax_percent = data.stock.batch_detail.tax_percent
                    wms_code_mrp = data.order.sku.mrp
                    ord_dict = OrderedDict((('Order ID', order_id), ('WMS Code', data.order.sku.sku_code),
                                                            ('WMS MRP', wms_code_mrp),('Child SKU', child_sku_code),
                                                            ('Child SKU MRP', child_sku_mrp),('Child SKU Weight', child_sku_weight),
                                                            ('Description', data.order.sku.sku_desc),
                                                            ('SKU Category', data.order.sku.sku_category),
                                                            ('Sub Category',data.order.sku.sub_category),
                                                            ('SKU Brand', data.order.sku.sku_brand),
                                                            ('Location', pick_loc.stock.location.location),
                                                            ('Quantity', data.order.original_quantity),
                                                            ('Picked Quantity', picked_quantity),
                                                            ('Date', ' '.join(date[0:3])), ('Time', ' '.join(date[3:5])),
                                                            ('Selling Price', data.order.unit_price), ('Sale Tax Percent', tax_percent),
                                                            ('Cost Price', cost_price), ('Cost Tax Percent', cost_tax_percent),
                                                            ('Customer Name', customer_name),
                                                            ('Batch Number', batch_number), ('MRP', batchDetail_mrp),
                                                            ('Manufactured Date', batchDetail_mfgdate), ('Expiry Date', batchDetail_expdate),
                                                            ('Warehouse', warehouse_users.get(data.order.user))))
                    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
                        ord_dict['Manufacturer'] = manufacturer
                        ord_dict['Searchable'] = searchable
                        ord_dict['Bundle'] = bundle
                    temp_data['aaData'].append(ord_dict)
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
                ord_dict = OrderedDict((('Order ID', order_id), ('WMS Code', data.order.sku.wms_code),
                                                        ('Description', data.order.sku.sku_desc),
                                                        ('SKU Category', data.order.sku.sku_category),
                                                        ('Sub Category',data.order.sku.sub_category),
                                                        ('SKU Brand', data.order.sku.sku_brand),
                                                        ('Customer Name', data.order.customer_name),
                                                        ('Serial Number', serial_number),
                                                        ('Date', ' '.join(date[0:3])), ('Time', ' '.join(date[3:5])),
                                                        ('Warehouse', warehouse_users.get(data.order.user))))
                if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
                    ord_dict['Manufacturer'] = manufacturer
                    ord_dict['Searchable'] = searchable
                    ord_dict['Bundle'] = bundle
                temp_data['aaData'].append(ord_dict)

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
    fmcg_marketplace = False
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        fmcg_marketplace = True
    search_parameters = {}
    user_profile = UserProfile.objects.get(user_id=user.id)
    lis = ['po_date', 'order_id', 'open_po__supplier_id', 'open_po__supplier__name',
           'open_po__sku__sku_code', 'open_po__sku__sku_desc', 'open_po__sku__sku_class',
           'open_po__sku__style_name', 'open_po__sku__sku_brand', 'open_po__sku__sku_category',
           'open_po__sku__sub_category',
           'open_po__order_quantity', 'open_po__price', 'open_po__price', 'open_po__mrp', 'id', 'id', 'id',
           'received_quantity', 'id', 'id', 'id', 'id', 'id', 'id']

    columns = SKU_WISE_PO_DICT['dt_headers']
    if fmcg_marketplace:
        lis+=['id']*3
    if 'sku_code' in search_params:
        search_parameters['open_po__sku__sku_code'] = search_params['sku_code']
    if 'sku_category' in search_params:
        search_parameters['open_po__sku__sku_category'] = search_params['sku_category']
    if 'sub_category' in search_params:
        search_parameters['open_po__sku__sub_category'] = search_params['sub_category']
    if 'sku_brand' in search_params:
        search_parameters['open_po__sku__sku_brand'] = search_params['sku_brand']
    if 'supplier' in search_params:
        supp_search = search_params['supplier'].split(':')
        search_parameters['open_po__supplier_id'] = supp_search[0]
    if 'from_date' in search_params:
        search_parameters['creation_date__gte'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lte'] = search_params['to_date']
    if fmcg_marketplace:
        if 'manufacturer' in search_params:
            search_parameters['open_po__sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['open_po__sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['open_po__sku__skuattributes__attribute_value__iexact'] = search_params['bundle']

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
    order_index = search_params.get('order_index', 0)

    custom_search = False
    order_data = lis[order_index]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    purchase_orders = purchase_orders.order_by(order_data)
    if len(columns) > order_index :
        if columns[order_index] in ['Status', 'Rejected Quantity', 'Pre-Tax PO Amount', 'Tax',
                                'After Tax PO Amount']:
            custom_search = True
    if not custom_search:
        if stop_index:
            purchase_orders = purchase_orders[start_index:stop_index]
    time = get_local_date(user, datetime.datetime.now())
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
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
        if data.status in ['confirmed-putaway', 'location-assigned'] and (data.received_quantity < data.open_po.order_quantity):
            status = 'Closed PO'
        order_data = get_purchase_order_data(data)
        manufacturer,searchable,bundle = '','',''
        attributes_obj = SKUAttributes.objects.filter(sku_id=order_data['sku'].id, attribute_name__in= attributes_list)
        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value

        po_number = '%s%s_%s' % (data.prefix, str(data.creation_date).split(' ')[0].replace('-', ''), data.order_id)
        tax = 0
        price = order_data['price']
        if data.open_po:
            tax = float(data.open_po.cgst_tax) + float(data.open_po.sgst_tax) + float(data.open_po.igst_tax) + \
                  float(data.open_po.cess_tax) + float(data.open_po.apmc_tax)
            aft_price = price + ((price / 100) * tax)
        pre_amount = float(order_data['order_quantity']) * float(price)
        aft_amount = float(order_data['order_quantity']) * float(aft_price)
        temp = OrderedDict((('PO Date', get_local_date(user, data.creation_date)), ('PO Number', po_number),
                            ('Supplier ID', order_data['supplier_id']),
                            ('Supplier Name', order_data['supplier_name']),
                            ('SKU Code', order_data['sku_code']),
                            ('SKU Description', order_data['sku_desc']),
                            ('SKU Class', order_data['sku'].sku_class),
                            ('SKU Style Name', order_data['sku'].style_name),
                            ('SKU Brand', order_data['sku'].sku_brand),
                            ('SKU Category', order_data['sku'].sku_category),
                            ('Sub Category', order_data['sku'].sub_category),
                            ('PO Qty', order_data['order_quantity']),
                            ('Unit Price without tax', order_data['price']),
                            ('Unit Price with tax', "%.2f" % aft_price),
                            ('MRP', order_data['mrp']),
                            ('Pre-Tax PO Amount', "%.2f" % pre_amount), ('Tax', tax),
                            ('After Tax PO Amount', "%.2f" % aft_amount),
                            ('Qty received', data.received_quantity), ('Status', status),
                            ('Warehouse Name', user.username),
                            ('Report Generation Time', time)
                            ))
        if fmcg_marketplace:
            temp['Manufacturer'] = manufacturer
            temp['Searchable'] = searchable
            temp['Bundle'] = bundle
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
        unsorted_dict = {16: 'Pre-Tax Received Value', 29: 'Post-Tax Received Value', 31: 'Margin',
                         32: 'Invoiced Unit Rate',
                         34: 'Invoiced Total Amount'}
        lis = ['purchase_order__updation_date', 'purchase_order__creation_date', 'purchase_order__order_id',
               'purchase_order__open_po__po_name',
               'purchase_order__open_po__supplier_id', 'purchase_order__open_po__supplier__name', 'id',
               'purchase_order__open_po__sku__sku_code', 'purchase_order__open_po__sku__sku_desc',
               'purchase_order__open_po__sku__hsn_code',
               'purchase_order__open_po__sku__sku_class',
               'purchase_order__open_po__sku__style_name', 'purchase_order__open_po__sku__sku_brand',
               'purchase_order__open_po__sku__sku_category', 'total_received', 'purchase_order__open_po__price',
               'purchase_order__open_po__mrp', 'id',
               'purchase_order__open_po__cgst_tax', 'purchase_order__open_po__sgst_tax',
               'purchase_order__open_po__igst_tax', 'purchase_order__open_po__utgst_tax',
               'purchase_order__open_po__cess_tax', 'purchase_order__open_po__apmc_tax',
               'purchase_order__open_po__cgst_tax', 'purchase_order__open_po__sgst_tax',
               'purchase_order__open_po__igst_tax', 'purchase_order__open_po__utgst_tax',
               'purchase_order__open_po__cess_tax', 'purchase_order__open_po__apmc_tax', 'id',
               'seller_po__margin_percent', 'seller_po__margin_percent',
               'id', 'overall_discount', 'id','id','id','id','id','id','id','id',
               'invoice_number', 'invoice_date', 'challan_number', 'challan_date', 'remarks', 'id','purchase_order__id', 'id']
        model_name = SellerPOSummary
        field_mapping = {'from_date': 'creation_date', 'to_date': 'creation_date',
                         'order_id': 'purchase_order__order_id',
                         'wms_code': 'purchase_order__open_po__sku__wms_code__iexact',
                         'manufacturer':'purchase_order__open_po__sku__skuattributes__attribute_value__iexact',
                         'searchable':'purchase_order__open_po__sku__skuattributes__attribute_value__iexact',
                         'bundle':'purchase_order__open_po__sku__skuattributes__attribute_value__iexact',
                         'sku_category': 'purchase_order__open_po__sku__sku_category__iexact',
                         'sub_category': 'purchase_order__open_po__sku__sub_category__iexact',
                         'sku_brand': 'purchase_order__open_po__sku__sku_brand__iexact',
                         'user': 'purchase_order__open_po__sku__user',
                         'sku_id__in': 'purchase_order__open_po__sku_id__in',
                         'prefix': 'purchase_order__prefix', 'supplier_id': 'purchase_order__open_po__supplier_id',
                         'supplier_name': 'purchase_order__open_po__supplier__name',
                         'receipt_type': 'seller_po__receipt_type', 'invoice_number': 'invoice_number', 'gst_num': 'purchase_order__open_po__supplier__tin_number'}
        result_values = ['purchase_order__order_id', 'purchase_order__open_po__supplier_id',
                         'purchase_order__open_po__supplier__name', 'purchase_order__open_po__supplier__tax_type',
                         'purchase_order__open_po__sku__sku_code', 'purchase_order__open_po__sku__sku_desc','purchase_order__open_po__sku_id',
                         'purchase_order__open_po__sku__hsn_code', 'purchase_order__open_po__po_name','purchase_order__open_po__sku__sub_category',
                         'purchase_order__open_po__sku__sku_class', 'purchase_order__open_po__sku__style_name',
                         'purchase_order__open_po__sku__sku_brand', 'purchase_order__open_po__sku__sku_category',
                         'purchase_order__received_quantity', 'purchase_order__open_po__price',
                         'purchase_order__open_po__mrp', 'purchase_order__open_po__cgst_tax',
                         'purchase_order__open_po__sgst_tax', 'purchase_order__open_po__igst_tax',
                         'purchase_order__open_po__utgst_tax', 'purchase_order__open_po__cess_tax',
                         'purchase_order__open_po__apmc_tax','batch_detail__weight',
                         'seller_po__margin_percent', 'purchase_order__prefix', 'seller_po__unit_price', 'id',
                         'seller_po__receipt_type', 'receipt_number', 'batch_detail__buy_price',
                         'batch_detail__tax_percent', 'invoice_number', 'invoice_date', 'challan_number','overall_discount',
                         'challan_date', 'discount_percent', 'cess_tax', 'batch_detail__mrp', 'remarks','purchase_order__open_po__supplier__tin_number','purchase_order__id','price']
    else:
        unsorted_dict = {16: 'Pre-Tax Received Value', 29: 'Post-Tax Received Value',
                         30: 'Invoiced Unit Rate',
                         32: 'Invoiced Total Amount'}
        model_name = SellerPOSummary
        lis = ['purchase_order__updation_date', 'purchase_order__creation_date', 'purchase_order__order_id',
               'purchase_order__open_po__po_name',
               'purchase_order__open_po__supplier_id', 'purchase_order__open_po__supplier__name', 'id',
               'purchase_order__open_po__sku__sku_code', 'purchase_order__open_po__sku__sku_desc',
               'purchase_order__open_po__sku__hsn_code', 'purchase_order__open_po__sku__sku_class',
               'purchase_order__open_po__sku__style_name', 'purchase_order__open_po__sku__sku_brand',
               'purchase_order__open_po__sku__sku_category', 'total_received', 'purchase_order__open_po__price',
               'purchase_order__open_po__mrp', 'id',
               'purchase_order__open_po__cgst_tax', 'purchase_order__open_po__sgst_tax',
               'purchase_order__open_po__igst_tax', 'purchase_order__open_po__utgst_tax',
               'purchase_order__open_po__cess_tax', 'purchase_order__open_po__apmc_tax',
               'purchase_order__open_po__cgst_tax', 'purchase_order__open_po__sgst_tax',
               'purchase_order__open_po__igst_tax', 'purchase_order__open_po__utgst_tax',
               'purchase_order__open_po__cess_tax', 'purchase_order__open_po__apmc_tax',
               'id', 'seller_po__margin_percent', 'overall_discount', 'id','id','id','id','id','id','id','id','id',
               'invoice_number', 'invoice_date', 'challan_number', 'challan_date', 'remarks', 'id','purchase_order__id', 'id']

        field_mapping = {'from_date': 'creation_date', 'to_date': 'creation_date',
                         'order_id': 'purchase_order__order_id',
                         'wms_code': 'purchase_order__open_po__sku__wms_code__iexact',
                         'sku_category': 'purchase_order__open_po__sku__sku_category__iexact',
                         'sub_category': 'purchase_order__open_po__sku__sub_category__iexact',
                         'sku_brand': 'purchase_order__open_po__sku__sku_brand__iexact',
                         'user': 'purchase_order__open_po__sku__user',
                         'sku_id__in': 'purchase_order__open_po__sku_id__in',
                         'prefix': 'purchase_order__prefix', 'supplier_id': 'purchase_order__open_po__supplier_id',
                         'supplier_name': 'purchase_order__open_po__supplier__name',
                         'receipt_type': 'seller_po__receipt_type', 'invoice_number': 'invoice_number', 'gst_num': 'purchase_order__open_po__supplier__tin_number'}
        result_values = ['purchase_order__order_id', 'purchase_order__open_po__supplier_id',
                         'purchase_order__open_po__supplier__name','purchase_order__open_po__sku_id',
                         'purchase_order__open_po__sku__sku_code', 'purchase_order__open_po__sku__sku_desc',
                         'purchase_order__open_po__sku__hsn_code', 'purchase_order__open_po__po_name',
                         'purchase_order__open_po__sku__sku_class', 'purchase_order__open_po__sku__style_name',
                         'purchase_order__open_po__sku__sku_brand', 'purchase_order__open_po__sku__sku_category','purchase_order__open_po__sku__sub_category',
                         'purchase_order__received_quantity', 'purchase_order__open_po__price',
                         'purchase_order__open_po__mrp', 'purchase_order__open_po__cgst_tax',
                         'purchase_order__open_po__sgst_tax', 'purchase_order__open_po__igst_tax',
                         'purchase_order__open_po__utgst_tax', 'purchase_order__open_po__cess_tax',
                         'purchase_order__open_po__apmc_tax','batch_detail__weight',
                         'seller_po__margin_percent', 'seller_po__margin_percent', 'purchase_order__prefix', 'seller_po__unit_price', 'id',
                         'seller_po__receipt_type', 'receipt_number', 'batch_detail__buy_price','overall_discount',
                         'batch_detail__tax_percent', 'invoice_number', 'invoice_date', 'challan_number',
                         'challan_date', 'discount_percent', 'cess_tax', 'batch_detail__mrp', 'remarks', 'purchase_order__open_po__supplier__tin_number','purchase_order__id','price']
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
    if 'sku_category' in search_params:
        search_parameters[field_mapping['sku_category']] = search_params['sku_category']
    if 'sub_category' in search_params:
        search_parameters[field_mapping['sub_category']] = search_params['sub_category']
    if 'sku_brand' in search_params:
        search_parameters[field_mapping['sku_brand']] = search_params['sku_brand']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters[field_mapping['manufacturer']] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters[field_mapping['searchable']] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters[field_mapping['bundle']] = search_params['bundle']

    if 'invoice_number' in search_params:
        search_parameters[field_mapping['invoice_number']] = search_params['invoice_number']
    if 'supplier' in search_params and ':' in search_params['supplier']:
        search_parameters[field_mapping['supplier_id']] = \
            search_params['supplier'].split(':')[0]
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
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for data in model_data:
        manufacturer,searchable,bundle = '','',''
        if data['purchase_order__open_po__sku_id']:
            attributes_obj = SKUAttributes.objects.filter(sku_id=data['purchase_order__open_po__sku_id'], attribute_name__in= attributes_list)
            if attributes_obj.exists():
                for attribute in attributes_obj:
                    if attribute.attribute_name == 'Manufacturer':
                        manufacturer = attribute.attribute_value
                    if attribute.attribute_name == 'Searchable':
                        searchable = attribute.attribute_value
                    if attribute.attribute_name == 'Bundle':
                        bundle = attribute.attribute_value
        result = purchase_orders.filter(order_id=data[field_mapping['order_id']], open_po__sku__user=user.id)[0]
        receipt_no = data['receipt_number']
        if not receipt_no:
            receipt_no = ''
        po_number = '%s%s_%s/%s' % (data[field_mapping['prefix']],
                                 str(result.creation_date).split(' ')[0].replace('-', ''),
                                 data[field_mapping['order_id']], str(receipt_no))
        price = data['price']
        if data.get('batch_detail__buy_price', 0):
            price = data['batch_detail__buy_price']
        mrp = data['purchase_order__open_po__mrp']
        if data.get('batch_detail__mrp', 0):
            mrp = data['batch_detail__mrp']
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
        amount = float('%.2f' % (float(data['total_received'] * price)))
        if data['discount_percent']:
            amount = float('%.2f' % (amount - (amount * float(data['discount_percent']) / 100)))
        tot_tax = float(data['purchase_order__open_po__cgst_tax']) + float(data['purchase_order__open_po__sgst_tax']) +\
                  float(data['purchase_order__open_po__igst_tax']) + float(data['purchase_order__open_po__utgst_tax'])\
                    + float(data['purchase_order__open_po__cess_tax'])
        aft_unit_price = (float(price) + (float(price / 100) * tot_tax))
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
        final_price = '%.2f'% (aft_unit_price)
        post_amount = '%2f'% (post_amount)
        invoice_total_amount = float(final_price) * float(data['total_received'])
        #invoice_total_amount = truncate_float(invoice_total_amount, 2)
        hsn_code = ''
        if data['purchase_order__open_po__sku__hsn_code']:
            hsn_code = data['purchase_order__open_po__sku__hsn_code']
        invoice_date, challan_date = '', ''
        if data['invoice_date']:
            invoice_date = data['invoice_date'].strftime("%d %b, %Y")
        if data['challan_date']:
            challan_date = data['challan_date'].strftime("%d %b, %Y")
        updated_user_name = user.username
        version_obj = Version.objects.get_for_object(SellerPOSummary.objects.get(id=data['id']))
        if version_obj.exists():
            updated_user_name = version_obj.order_by('-revision__date_created')[0].revision.user.username
        seller_po_summary = SellerPOSummary.objects.get(id=data['id'])
        lr_detail_no = ''
        if data['purchase_order__id']:
            lr_detail = LRDetail.objects.filter(purchase_order = data['purchase_order__id'], purchase_order__open_po__sku__user = user.id )
            if lr_detail.exists():
                lr_detail_no = lr_detail[0].lr_number
        remarks = ''
        if data['remarks']:
            custom_remarks = []
            remarks_list = data['remarks'].split(',')
            if 'mrp_change' in remarks_list:
                custom_remarks.append('MRP Change')
            if 'offer_applied' in remarks_list:
                custom_remarks.append('Offer Applied')
            remarks = ','.join(custom_remarks)
        if not remarks and result.remarks:
            remarks = result.remarks
        ord_dict = OrderedDict((('Received Date', get_local_date(user, seller_po_summary.creation_date)),
                            ('PO Date', get_local_date(user, result.creation_date)),
                            ('PO Number', po_number),
                            ('PO Reference Number',data['purchase_order__open_po__po_name']),
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
                            ('Sub Category', data['purchase_order__open_po__sku__sub_category']),
                            ('Received Qty', data['total_received']),
                            ('Unit Rate', price), ('MRP', mrp),
                            ('Pre-Tax Received Value', amount),
                            ('CGST(%)', data['purchase_order__open_po__cgst_tax']),
                            ('SGST(%)', data['purchase_order__open_po__sgst_tax']),
                            ('IGST(%)', data['purchase_order__open_po__igst_tax']),
                            ('UTGST(%)', data['purchase_order__open_po__utgst_tax']),
                            ('CESS(%)', data['purchase_order__open_po__cess_tax']),
                            ('APMC(%)', data['purchase_order__open_po__apmc_tax']),
                            ('CGST', truncate_float((amount/100)* data['purchase_order__open_po__cgst_tax'], 2)),
                            ('SGST', truncate_float((amount/100)* data['purchase_order__open_po__sgst_tax'], 2)),
                            ('IGST', truncate_float((amount/100)* data['purchase_order__open_po__igst_tax'], 2)),
                            ('UTGST', truncate_float((amount/100)* data['purchase_order__open_po__utgst_tax'], 2)),
                            ('CESS', truncate_float((amount/100)* data['purchase_order__open_po__cess_tax'], 2)),
                            ('APMC', truncate_float((amount / 100) * data['purchase_order__open_po__apmc_tax'], 2)),
                            ('Post-Tax Received Value', post_amount),
                            ('Margin %', data['seller_po__margin_percent']),
                            ('Margin', margin_price),
                            ('Invoiced Unit Rate', final_price),
                            ('Invoiced Total Amount', invoice_total_amount),
                            ('Invoice Number', data['invoice_number']),
                            ('Overall Discount',data['overall_discount']),
                            ('Invoice Date', invoice_date),
                            ('Challan Number', data['challan_number']),
                            ('Challan Date', challan_date),
                            ('DT_RowAttr', {'data-id': data['id']}), ('key', 'po_summary_id'),
                            ('receipt_type', data['seller_po__receipt_type']),
                            ('receipt_no', 'receipt_no'),
                            ('Remarks', remarks),
                            ('Weight', data['batch_detail__weight']),
                            ('Updated User', updated_user_name),
                            ('GST NO', data[field_mapping['gst_num']]),
                            ('LR-NUMBER', lr_detail_no)))
        if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            ord_dict['Manufacturer'] = manufacturer
            ord_dict['Searchable'] = searchable
            ord_dict['Bundle'] = bundle
        temp_data['aaData'].append(ord_dict)

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
    lis = ['order_id', 'open_po__po_name','open_po__supplier_id', 'open_po__supplier__name', 'ordered_qty', 'received_quantity']
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
    if 'invoice_number' in search_params:
        search_parameters['sellerposummary__invoice_number'] = search_params['invoice_number']
    if 'supplier' in search_params and ':' in search_params['supplier']:
        search_parameters['sellerposummary__purchase_order__open_po__supplier__id__iexact'] = \
            search_params['supplier'].split(':')[0]
    search_parameters[field_mapping['user']] = user.id
    search_parameters[field_mapping['sku_id__in']] = sku_master_ids
    search_parameters['received_quantity__gt'] = 0
    query_data = model_name.objects.prefetch_related('open_po__sku','open_po__supplier').select_related('open_po', 'open_po__sku','open_po__supplier').exclude(**excl_status).filter(**search_parameters)
    model_data = query_data.values(*result_values).distinct().annotate(ordered_qty=Sum(ord_quan),
                                                                   total_received=Sum(rec_quan))
                                                                   #grn_rec=Sum(rec_quan1))
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
        po_reference_name = result.open_po.po_name
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
        if data.get('sellerposummary__receipt_number', ''):
            received_qty =  po_result.filter(sellerposummary__receipt_number=data['sellerposummary__receipt_number']).aggregate(
                Sum(rec_quan1))[rec_quan1 + '__sum']
            if not received_qty:
                received_qty = 0
        #if data['grn_rec']:
        #    received_qty = data['grn_rec']
        temp_data['aaData'].append(OrderedDict((('PO Number', po_number),
                                                ('Supplier ID', data[field_mapping['supplier_id']]),
                                                ('PO Reference', po_reference_name),
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
    from common import get_misc_value
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    temp_data = copy.deepcopy(AJAX_DATA)
    central_order_mgmt = get_misc_value('central_order_mgmt', user.id)
    warehouse_users = {}
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
    if 'sku_category' in search_params:
        search_parameters['sku__sku_category'] = search_params['sku_category']
    if 'sub_category' in search_params:
        search_parameters['sku__sub_category'] = search_params['sub_category']
    if 'sku_brand' in search_params:
        search_parameters['sku__sku_brand'] = search_params['sku_brand']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['bundle']

    if user.userprofile.warehouse_type == 'admin':
        if 'sister_warehouse' in search_params:
            sister_warehouse_name = search_params['sister_warehouse']
            user = User.objects.get(username=sister_warehouse_name)
            warehouses = UserGroups.objects.filter(user_id=user.id)
        else:
            warehouses = UserGroups.objects.filter(admin_user_id=user.id)
        warehouse_users = dict(warehouses.values_list('user_id', 'user__username'))
        sku_master = SKUMaster.objects.filter(user__in=warehouse_users.keys())
        sku_master_ids = sku_master.values_list('id', flat=True)
    else:
        search_parameters['sku__user'] = user.id
    search_parameters['sku_id__in'] = sku_master_ids
    sku_master = StockDetail.objects.exclude(receipt_number=0).values_list('sku_id', 'sku__sku_code', 'sku__sku_desc',
                                                                           'sku__sku_brand',
                                                                           'sku__sku_category',
                                                                           'sku__sub_category','sku__user').distinct().annotate(
        total=Sum('quantity'), stock_value=Sum(F('quantity') * F('unit_price'))).filter(quantity__gt=0,
                                      **search_parameters)
    if search_stage and not search_stage == 'In Stock':
        sku_master = []
    wms_codes = map(lambda d: d[0], sku_master)
    sku_master1 = job_order.exclude(product_code_id__in=wms_codes).filter(**job_filter).values_list('product_code_id',
                                                                                                    'product_code__sku_code',
                                                                                                    'product_code__sku_desc',
                                                                                                    'product_code__sku_brand',
                                                                                                    'product_code__sku_category',
                                                                                                    'product_code__sub_category',
                                                                                                    ).distinct()
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
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for ind, sku in enumerate(sku_master):
        sku_stages_dict = {}
        total_stock_value = 0
        intransit_quantity = 0
        manufacturer,searchable,bundle = '','',''
        attributes_obj = SKUAttributes.objects.filter(sku_id=sku[0], attribute_name__in= attributes_list)
        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value
        if len(list(sku)) >= 7:
            sku_stages_dict['In Stock'] = sku[7]
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
            warehouse = 0
            stock_value = 0
            if len(list(sku)) >= 7:
              if sku[6]:
                  warehouse = warehouse_users.get(sku[6])
              if sku[8]:
                 stock_value = sku[8]
            ord_dict = OrderedDict((('SKU Code', sku[1]), ('Description', sku[2]),
                                                ('Brand', sku[3]), ('Category', sku[4]),('SKU Sub Category', sku[5]),
                                                ('Stage', key), ('Stage Quantity', value), ('Stock Value', stock_value),  ('Warehouse Name', warehouse)))
            if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
                ord_dict['Manufacturer'] = manufacturer
                ord_dict['Searchable'] = searchable
                ord_dict['Bundle'] = bundle
            sku_master_list.append(ord_dict)

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
    cmp_data = ('sku_code', 'sku_brand', 'sku_class', 'sku_category', 'sub_category')
    job_filter = {}
    for data in cmp_data:
        if data in search_params:
            search_parameters['%s__%s__%s' % ('product_code', data, 'iexact')] = search_params[data]
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['product_code__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['product_code__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['product_code__skuattributes__attribute_value__iexact'] = search_params['bundle']

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
    else:
        status_filter['creation_date__gte'] = date.today()+relativedelta(months=-1)
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
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
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
        manufacturer,searchable,bundle = '','',''
        attributes_obj = SKUAttributes.objects.filter(sku_id=job_order.product_code.id, attribute_name__in= attributes_list)
        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value
        ord_dict = OrderedDict((('Date', summary_date), ('Job Order', job_order.job_code),
                                               ('JO Creation Date', jo_creation_date),
                                               ('SKU Class', job_order.product_code.sku_class),
                                               ('SKU Code', job_order.product_code.sku_code),
                                               ('Brand', job_order.product_code.sku_brand),
                                               ('SKU Category', job_order.product_code.sku_category),
                                               ('SKU Sub Category', job_order.product_code.sub_category),
                                               ('Total JO Quantity', job_order.product_quantity),
                                               ('Reduced Quantity', summary_dict['tsum']),
                                               ('Stage', summary.processed_stage)
                         ))
        if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            ord_dict['Manufacturer'] = manufacturer
            ord_dict['Searchable'] = searchable
            ord_dict['Bundle'] = bundle
        data.append(ord_dict)
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
    lis = ['jo_id', 'jo_creation_date', 'sku__brand', 'sku__sku_category', 'sku__sub_category', 'sku__sku_class', 'sku__sku_code', 'stage',
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
    if 'sub_category' in search_params:
        search_parameters['product_code__sub_category'] = search_params['sub_category']
    if 'sku_brand' in search_params:
        search_parameters['product_code__sku_brand'] = search_params['sku_brand']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['product_code__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['product_code__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['product_code__skuattributes__attribute_value__iexact'] = search_params['bundle']

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
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for one_data in final_data:
        manufacturer,searchable,bundle = '','',''
        attributes_obj = SKUAttributes.objects.filter(sku_id=one_data['data'].product_code.id, attribute_name__in= attributes_list)
        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value
        date = get_local_date(user, one_data['data'].creation_date).split(' ')
        last_data.append(OrderedDict((('JO Code', one_data['data'].job_code), ('Jo Creation Date', ' '.join(date[0:3])),
                                      ('SKU Brand', one_data['data'].product_code.sku_brand),
                                      ('SKU Category', one_data['data'].product_code.sku_category),
                                      ('SKU Sub Category', one_data['data'].product_code.sub_category),
                                      ('SKU Class', one_data['data'].product_code.sku_class),
                                      ('SKU Code', one_data['data'].product_code.sku_code),
                                      ('Stage', one_data['stage']), ('Quantity', one_data['quantity']))))
        if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            last_data['Manufacturer'] = manufacturer
            last_data['Searchable'] = searchable
            last_data['Bundle'] = bundle

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


def get_financial_group_dict(fields_parameters1, data_objs=None, send_last_day=False, stock_rec_data=None,
                            send_damaged=True, opening_stock_date=None, used_damage_qtys=None):
    data_dict = {'quantity': 0, 'tax_amount': 0, 'cess_amount': 0,
                     'value_before_tax': 0, 'value_after_tax': 0, 'price_before_tax': 0}
    if not data_objs:
        purchase_data = []
        if not send_last_day:
            fields_parameters2 = copy.deepcopy(fields_parameters1)
            if opening_stock_date:
                fields_parameters2['stock_reconciliation__creation_date__regex'] = opening_stock_date
            fields_parameters2['stock_reconciliation__%s_quantity__gt' % fields_parameters1['field_type']] = 0
            purchase_data = StockReconciliationFields.objects.annotate(tax_percent=Sum(F('cgst_tax')+F('sgst_tax')+F('igst_tax'))).\
                                            filter(**fields_parameters2)
            #if purchase_data.exists() and send_first_day:
            #    first_date = purchase_data.first().stock_reconciliation.creation_date.date()
            #    purchase_data = purchase_data.filter(stock_reconciliation__creation_date__regex=first_date)
        damaged_field = '%s_qty_damaged' % fields_parameters1['field_type']
    else:
        purchase_data = data_objs
        damaged_field = 'closing_qty_damaged'
    if purchase_data:
        for data in purchase_data:
            quantity = data.quantity
            if not send_damaged:
                if data.stock_reconciliation.id not in used_damage_qtys.get(fields_parameters1['field_type'], []) \
                                                and quantity >= getattr(data.stock_reconciliation, damaged_field):
                    quantity = data.quantity - getattr(data.stock_reconciliation, damaged_field)
                    used_damage_qtys.setdefault(fields_parameters1['field_type'], [])
                    used_damage_qtys[fields_parameters1['field_type']].append(data.stock_reconciliation.id)
            amount = quantity * data.price_before_tax
            data_dict['quantity'] += quantity
            value_before_tax = data.value_before_tax
            value_after_tax = data.value_after_tax
            if not send_damaged and data.quantity:
                value_after_tax = (data.value_after_tax/data.quantity) * quantity
                value_before_tax = (data.value_before_tax/data.quantity) * quantity
            data_dict['value_before_tax'] += value_before_tax
            data_dict['value_after_tax'] += value_after_tax
            tax_percent = data.cgst_tax + data.sgst_tax + data.igst_tax
            data_dict['tax_amount'] += (amount/100) * tax_percent
            if data.cess_tax:
                data_dict['cess_amount'] += (amount/100) * data.cess_tax
            #data_dict['value_after_tax'] = data_dict['value_before_tax'] + data_dict['cgst_amount'] + \
            #                                data_dict['sgst_amount'] + data_dict['igst_amount'] + data_dict['cess_amount']
        if data_dict['quantity']:
            data_dict['price_before_tax'] = data_dict['value_before_tax'] / data_dict['quantity']
    elif stock_rec_data:

        if opening_stock_date:
            stock_reconciliation_objs = StockReconciliation.objects.filter(sku_id=stock_rec_data.sku_id, mrp=stock_rec_data.mrp,
                                                                            weight=stock_rec_data.weight,
                                                                            creation_date__regex=opening_stock_date)
        else:
            stock_rec_extra_filter = {'sku_id': stock_rec_data.sku_id, 'mrp': stock_rec_data.mrp,
                                      'weight': stock_rec_data.weight,
                                      'creation_date__gte': fields_parameters1['stock_reconciliation__creation_date__gte']}
            if fields_parameters1.get('stock_reconciliation__creation_date__lte', ''):
                stock_rec_extra_filter['creation_date__lte'] = fields_parameters1['stock_reconciliation__creation_date__lte']
            stock_reconciliation_objs = StockReconciliation.objects.filter(**stock_rec_extra_filter)
        if send_last_day:
            last_date = stock_reconciliation_objs.latest('creation_date').creation_date.date()
            stock_reconciliation_objs = stock_reconciliation_objs.filter(creation_date__regex=last_date)
        for stock_reconciliation_obj in stock_reconciliation_objs:
            data_dict['quantity'] += getattr(stock_reconciliation_obj, '%s_quantity' % fields_parameters1['field_type'])
            data_dict['value_after_tax'] += getattr(stock_reconciliation_obj, '%s_amount' % fields_parameters1['field_type'])
    return data_dict, used_damage_qtys


def get_financial_report_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from miebach_admin.views import *
    milkbasket_user = False
    milkbasket_users = copy.deepcopy(MILKBASKET_USERS)
    if user.username in milkbasket_users :
        milkbasket_user = True

    lis = ['']
    start_index = search_params.get('start', 0)
    stop_index = None
    if search_params.get('length', 0):
        stop_index = start_index + search_params.get('length', 0)
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    fields_parameters = OrderedDict()
    stats_params = {}
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gte'] = search_params['from_date']
        fields_parameters['stock_reconciliation__creation_date__gte'] = search_params['from_date']
        stats_params['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lte'] = search_params['to_date']
        fields_parameters['stock_reconciliation__creation_date__lte'] = search_params['to_date']
        stats_params['creation_date__lt'] = search_params['to_date']
    if 'sku_code' in search_params:
        search_parameters['sku__sku_code'] = search_params['sku_code']
        fields_parameters['stock_reconciliation__sku__sku_code'] = search_params['sku_code']
    if 'sku_category' in search_params:
        search_parameters['sku__sku_category'] = search_params['sku_category']
        fields_parameters['stock_reconciliation__sku__sku_category'] = search_params['sku_category']
    if 'sub_category' in search_params:
        search_parameters['sku__sub_category'] = search_params['sub_category']
        fields_parameters['stock_reconciliation__sku__sub_category'] = search_params['sub_category']
    if 'sku_brand' in search_params:
        search_parameters['sku__sku_brand'] = search_params['sku_brand']
        fields_parameters['stock_reconciliation__sku__sku_brand'] = search_params['sku_brand']
    if 'manufacturer' in search_params:
        search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        fields_parameters['stock_reconciliation__sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
    if 'searchable' in search_params:
        search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        fields_parameters['stock_reconciliation__sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
    if 'bundle' in search_params:
        search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['bundle']
        fields_parameters['stock_reconciliation__sku__skuattributes__attribute_value__iexact'] = search_params['bundle']

    search_parameters['sku__user'] = user.id
    fields_parameters['stock_reconciliation__sku__user'] = user.id
    if 'from_date' in search_params:
        stock_recs = StockReconciliation.objects.filter(**search_parameters).only('creation_date')
        if stock_recs.exists():
            if not stop_index:
                manufacturer_dict = dict(SKUAttributes.objects.filter(sku__user=user.id,
                                                                   attribute_name='Manufacturer').values_list(
                'sku_id', 'attribute_value'))
                searchable_dict = dict(SKUAttributes.objects.filter(sku__user=user.id,
                                                                   attribute_name='Searchable').values_list(
                'sku_id', 'attribute_value'))
                bundle_dict = dict(SKUAttributes.objects.filter(sku__user=user.id,
                                                                attribute_name='Bundle').values_list('sku_id', 'attribute_value'))
                hub_dict = dict(SKUAttributes.objects.filter(sku__user=user.id,
                                                                attribute_name='Hub').values_list('sku_id', 'attribute_value'))
                vendor_dict = dict(SKUAttributes.objects.filter(sku__user=user.id,
                                                                attribute_name='Vendor').values_list('sku_id', 'attribute_value'))
            opening_stock_date = stock_recs[0].creation_date.date()
            closing_stock_date = stock_recs.latest('creation_date').creation_date.date()
            opening_stock_filter = {'stock_reconciliation__creation_date__regex': opening_stock_date,
                                    'stock_reconciliation__sku__user': user.id,
                                    'field_type': 'opening'}
            if 'stock_reconciliation__sku__sku_code' in fields_parameters:
                opening_stock_filter['stock_reconciliation__sku__sku_code'] = fields_parameters['stock_reconciliation__sku__sku_code']
            stock_rec_distinct_data = stock_recs.values('sku_id', 'mrp', 'weight').distinct()
            temp_data['recordsTotal'] = stock_rec_distinct_data.count()
            temp_data['recordsFiltered'] = temp_data['recordsTotal']
            counter = 1
            attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
            for stock_rec_data_dict in stock_rec_distinct_data[start_index:stop_index]:
                print counter
                counter += 1
                stock_rec_data = stock_recs.filter(sku_id=stock_rec_data_dict['sku_id'], mrp=stock_rec_data_dict['mrp'],
                                                    weight=stock_rec_data_dict['weight'])[0]
                opening_stock_query = StockReconciliationFields.objects.filter(stock_reconciliation__sku_id=stock_rec_data_dict['sku_id'],
                                                                                stock_reconciliation__mrp=stock_rec_data_dict['mrp'],
                                                                                stock_reconciliation__weight=stock_rec_data_dict['weight'],
                                                                            creation_date__gte=opening_stock_date,
                                                                            creation_date__lt=closing_stock_date+datetime.timedelta(1))
                opening_stock_data = opening_stock_query.annotate(tax_percent=Sum(F('cgst_tax')+F('sgst_tax')+F('igst_tax'))).\
                                                    values('stock_reconciliation__sku__sku_code', 'stock_reconciliation__sku__sku_desc',
                                                            'stock_reconciliation__sku_id',
                                                            'stock_reconciliation__sku__sku_category', 'stock_reconciliation__sku__sub_category',
                                                            'stock_reconciliation__sku_id','stock_reconciliation__sku__sku_brand',
                                                            'stock_reconciliation__sku__hsn_code', 'stock_reconciliation__mrp',
                                                            'stock_reconciliation__weight','tax_percent').distinct()
                closing_objs = StockReconciliationFields.objects.filter(stock_reconciliation__creation_date__regex=closing_stock_date,
                                                                        stock_reconciliation__sku__user=user.id,
                                                                        field_type='closing')
                manufacturer, searchable, bundle = '', '', ''
                sku_id = stock_rec_data.sku_id
                if not stop_index:
                    manufacturer = manufacturer_dict.get(sku_id, '')
                    searchable = searchable_dict.get(sku_id, '')
                    bundle = bundle_dict.get(sku_id, '')
                else:
                    attributes_obj = SKUAttributes.objects.filter(sku_id=sku_id, attribute_name__in=attributes_list)
                    if attributes_obj.exists():
                        for attribute in attributes_obj:
                            if attribute.attribute_name == 'Manufacturer':
                                manufacturer = attribute.attribute_value
                            if attribute.attribute_name == 'Searchable':
                                searchable = attribute.attribute_value
                            if attribute.attribute_name == 'Bundle':
                                bundle = attribute.attribute_value
                rows_data = []
                used_damage_qtys = {}
                if opening_stock_data.exists():
                    for opening_stock in opening_stock_data:
                        rows_data.append({'table': 'stock_rec_field', 'data': opening_stock})
                else:
                    rows_data.append({'table': 'stock_rec', 'data': stock_rec_data})
                for row_data in rows_data:
                    fields_parameters1 = copy.deepcopy(fields_parameters)
                    stock_rec_data1 = stock_rec_data
                    if row_data['table'] == 'stock_rec_field':
                        opening_stock = row_data['data']
                        tax_rate = opening_stock['tax_percent']
                        mrp = opening_stock['stock_reconciliation__mrp']
                        weight = opening_stock['stock_reconciliation__weight']
                        cess_tax = 0#opening_stock['cess_tax']
                        stock_rec_data1 = None
                    else:
                        tax_rate = 0
                        mrp = stock_rec_data.mrp
                        weight = stock_rec_data.weight
                        cess_tax = 0
                    # Closing Stock Calculation
                    closing_obj_filter = OrderedDict((('stock_reconciliation__sku_id', sku_id),
                                          ('stock_reconciliation__mrp', mrp),
                                          ('stock_reconciliation__weight', weight),
                                        ))
                    if row_data['table'] == 'stock_rec_field':
                        closing_obj_filter['tax_percent'] = opening_stock['tax_percent']
                    #fields_parameters1 = copy.deepcopy(fields_parameters)
                    fields_parameters1.update(closing_obj_filter)
                    closing_stock_objs = closing_objs.annotate(tax_percent=Sum(F('cgst_tax')+F('sgst_tax')+F('igst_tax'))).filter(**closing_obj_filter)
                    fields_parameters1['field_type'] = 'closing'
                    closing_damaged_flag = True
                    if closing_stock_date < datetime.datetime.strptime('2019-12-23', '%Y-%M-%d').date():
                        closing_damaged_flag = False
                    closing_dict, used_damage_qtys = get_financial_group_dict(fields_parameters1, data_objs=closing_stock_objs, send_last_day=True,
                                                            stock_rec_data=stock_rec_data1, send_damaged=closing_damaged_flag, used_damage_qtys=used_damage_qtys)
                    fields_parameters1['field_type'] = 'opening'
                    opening_damaged_flag = True
                    if closing_stock_date < datetime.datetime.strptime('2019-12-24', '%Y-%M-%d').date():
                        opening_damaged_flag = False
                    opening_dict, used_damage_qtys = get_financial_group_dict(fields_parameters1, send_damaged=opening_damaged_flag, stock_rec_data=stock_rec_data1,
                                                            opening_stock_date=opening_stock_date, used_damage_qtys=used_damage_qtys)
                    fields_parameters1['field_type'] = 'purchase'
                    purchase_dict, used_damage_qtys = get_financial_group_dict(fields_parameters1, stock_rec_data=stock_rec_data1,
                                                                                used_damage_qtys=used_damage_qtys)
                    fields_parameters1['field_type'] = 'rtv'
                    rtv_dict, used_damage_qtys = get_financial_group_dict(fields_parameters1, stock_rec_data=stock_rec_data1,
                                                                            used_damage_qtys=used_damage_qtys)
                    fields_parameters1['field_type'] = 'returns'
                    returns_dict, used_damage_qtys = get_financial_group_dict(fields_parameters1, stock_rec_data=stock_rec_data1,
                                                                                used_damage_qtys=used_damage_qtys)
                    fields_parameters1['field_type'] = 'customer_sales'
                    csd, used_damage_qtys = get_financial_group_dict(fields_parameters1, stock_rec_data=stock_rec_data1,
                                                                    used_damage_qtys=used_damage_qtys)
                    margin_percentage = 0
                    fields_parameters1['field_type'] = 'internal_sales'
                    isd, used_damage_qtys = get_financial_group_dict(fields_parameters1, stock_rec_data=stock_rec_data1,
                                                                    used_damage_qtys=used_damage_qtys)
                    fields_parameters1['field_type'] = 'stock_transfer'
                    std, used_damage_qtys = get_financial_group_dict(fields_parameters1, stock_rec_data=stock_rec_data1,
                                                used_damage_qtys=used_damage_qtys)
                    margin = 0
                    if csd['quantity']:
                        margin = (rtv_dict['value_after_tax'] + csd['value_after_tax'] + isd['value_after_tax'] +\
                                    std['value_after_tax'] + closing_dict['value_after_tax']) - \
                                    (opening_dict['value_after_tax'] + purchase_dict['value_after_tax'] + returns_dict['value_after_tax'])
                        if margin and csd['value_after_tax']:
                            margin_percentage = float('%.2f' % ((margin / float(csd['value_after_tax'])) * 100))
                    fields_parameters1['field_type'] = 'adjustment'
                    adjustment_dict, used_damage_qtys = get_financial_group_dict(fields_parameters1, stock_rec_data=stock_rec_data1,
                                                                                used_damage_qtys=used_damage_qtys)
                    physical_qty = StockDetail.objects.filter(sku_id=sku_id, batch_detail__mrp=mrp,
                                                              batch_detail__weight=weight,
                                                              batch_detail__tax_percent=tax_rate).distinct().\
                                                        aggregate(Sum('quantity'))['quantity__sum']
                    if not physical_qty:
                        physical_qty = 0
                    hub = ''
                    vendor = ''
                    if not stop_index:
                        hub = hub_dict.get(sku_id, '')
                        vendor = vendor_dict.get(sku_id, '')
                    else:
                        hub_obj = SKUAttributes.objects.filter(sku_id=sku_id, attribute_name='Hub')
                        if hub_obj.exists():
                            hub = hub_obj[0].attribute_value
                        vendor_obj = SKUAttributes.objects.filter(sku_id=sku_id, attribute_name='Vendor')
                        if vendor_obj.exists():
                            vendor = vendor_obj[0].attribute_value
                    #price_before_tax = 0
                    #if opening_dict['quantity']:
                    #    price_before_tax = float(value_after_tax)/opening_stock['quantity']
                    temp_data['aaData'].append(OrderedDict((('SKU Code', stock_rec_data.sku.sku_code),
                                                            ('SKU NAME', stock_rec_data.sku.sku_desc),
                                                            ('Category', stock_rec_data.sku.sku_category),
                                                            ('Sub Category', stock_rec_data.sku.sub_category),
                                                            ('SKU Brand', stock_rec_data.sku.sku_brand),
                                                            ('Manufacturer',manufacturer ),
                                                            ('Searchable',searchable ),
                                                            ('Bundle', bundle),
                                                            ('City',''), ('Hub', hub),('Vendor Name', vendor),
                                                            ('HSN Code', str(stock_rec_data.sku.hsn_code)),
                                                            ('MRP', mrp), ('Weight', weight), ('GST No', ''),
                                                            ('IGST Tax Rate', tax_rate),
                                                            ('CESS Rate', cess_tax),
                                                            ('Opening Qty', opening_dict['quantity']),
                                                            ('Opening Price Per Unit( Before Taxes)', '%.2f' % opening_dict['price_before_tax']),
                                                            ('Opening Value before Tax', float('%.2f' % opening_dict['value_before_tax'])),
                                                            ('Opening Tax', '%.2f' % opening_dict['tax_amount']),
                                                            ('Opening CESS', '%.2f' % opening_dict['cess_amount']),
                                                            ('Opening Value after Tax', float('%.2f' % opening_dict['value_after_tax'])),
                                                            ('Purchase Qty', purchase_dict['quantity']),
                                                            ('Purchase Price Per Unit(Before Taxes)', float('%.2f' % purchase_dict['price_before_tax'])),
                                                            ('Purchase Value before Tax', '%.2f' % purchase_dict['value_before_tax']),
                                                            ('Purchase Tax', '%.2f' % purchase_dict['tax_amount']),
                                                            ('Purchase CESS', '%.2f' % purchase_dict['cess_amount']),
                                                            ('Purchase Value after Tax', float('%.2f' % purchase_dict['value_after_tax'])),
                                                            ('Purchase Return Qty', rtv_dict['quantity']),
                                                            ('Purchase Return Price Per Unit(Before Taxes)', '%.2f' % rtv_dict['price_before_tax']),
                                                            ('Purchase Return Value before Tax', float('%.2f' % rtv_dict['value_before_tax'])),
                                                            ('Purchase Return Tax', '%.2f' % rtv_dict['tax_amount']),
                                                            ('Purchase Return CESS', '%.2f' % rtv_dict['cess_amount']),
                                                            ('Purchase Return Value after Tax', float('%.2f' % rtv_dict['value_after_tax'])),
                                                            ('Sale to Drsc Qty', csd['quantity']),
                                                            ('Sale to Drsc Price Per Unit( Before Taxes)', float('%.2f' % csd['price_before_tax'])),
                                                            ('Sale to Drsc Value before Tax', float('%.2f' % csd['value_before_tax'])),
                                                            ('Sale to Drsc Tax', '%.2f' % csd['tax_amount']),
                                                            ('Sale to Drsc CESS', '%.2f' % csd['cess_amount']),
                                                            ('Sale to Drsc Value after Tax', float('%.2f' % csd['value_after_tax'])),
                                                            ('Sale to othr Qty', isd['quantity']),
                                                            ('Sale to othr Price Per Unit( Before Taxes)', '%.2f' % isd['price_before_tax']),
                                                            ('Sale to othr Value before Tax', float('%.2f' % isd['value_before_tax'])),
                                                            ('Sale to othr Tax', '%.2f' % isd['tax_amount']),
                                                            ('Sale to othr CESS', '%.2f' % isd['cess_amount']),
                                                            ('Sale to othr Value after Tax', float('%.2f' % isd['value_after_tax'])),
                                                            ('Stock Transfers Qty', std['quantity']),
                                                            ('Stock Transfers Price Per Unit(Before Taxes)', '%.2f' % std['price_before_tax']),
                                                            ('Stock Transfers Value before Tax', float('%.2f' % std['value_before_tax'])),
                                                            ('Stock Transfers Tax', '%.2f' % std['tax_amount']),
                                                            ('Stock Transfers CESS', '%.2f' % std['cess_amount']),
                                                            ('Stock Transfers Value after Tax', float('%.2f' % std['value_after_tax'])),
                                                            ('Sale Return Qty', returns_dict['quantity']),
                                                            ('Sale Return Price Per Unit(Before Taxes)', '%.2f' % returns_dict['price_before_tax']),
                                                            ('Sale Return Value before Tax', float('%.2f' % returns_dict['value_before_tax'])),
                                                            ('Sale Return Tax', '%.2f' % returns_dict['tax_amount']),
                                                            ('Sale Return CESS', '%.2f' % returns_dict['cess_amount']),
                                                            ('Sale Return Value after Tax', float('%.2f' % returns_dict['value_after_tax'])),
                                                            ('Closing Qty', closing_dict['quantity']),
                                                            ('Closing Price Per Unit(Before Taxes)', '%.2f' % closing_dict['price_before_tax']),
                                                            ('Closing Value before Tax', float('%.2f' % closing_dict['value_before_tax'])),
                                                            ('Closing Tax', '%.2f' % closing_dict['tax_amount']),
                                                            ('Closing CESS', '%.2f' % closing_dict['cess_amount']),
                                                            ('Closing Value after Tax', float('%.2f' % closing_dict['value_after_tax'])),
                                                            ('Physical Qty', physical_qty),
                                                            ('Adjustment Qty', adjustment_dict['quantity']),
                                                            ('Adjustment Price Per Unit(Before Taxes)', '%.2f' % adjustment_dict['price_before_tax']),
                                                            ('Adjustment Value', '%.2f' % adjustment_dict['value_before_tax']),
                                                            ('Margin', margin),
                                                            ('Margin Percentage', margin_percentage)
                                                            )))
    return temp_data


def get_order_summary_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from miebach_admin.views import *
    from common import get_misc_value, get_admin
    from rest_api.views.common import get_sku_master, get_order_detail_objs, get_local_date, get_utc_start_date
    milkbasket_user = False
    milkbasket_users = copy.deepcopy(MILKBASKET_USERS)
    admin_user = get_admin(user)
    if user.username in milkbasket_users :
        milkbasket_user = True
    user_gst_number = ''
    if user.userprofile:
        user_gst_number = user.userprofile.gst_number
    lis = ['creation_date', 'order_id', 'customer_id','customer_name', 'sku__sku_brand', 'sku__sku_category', 'sku_n_sku_class',
           'sku__sku_size', 'sku__sku_desc', 'sku__sub_category', 'sku_code', 'sku_code', 'original_quantity', 'sku__mrp', 'sku__mrp', 'sku__mrp',
           'sku__discount_percentage', 'city', 'state', 'marketplace', 'invoice_amount','order_id', 'order_id','order_id',
           'quantity', 'quantity', 'quantity', 'quantity','order_id',
           'order_id','order_id','order_id','order_id','order_id','order_id','order_id','order_id','order_id','order_id','order_id','full_invoice_number', 'order_id', 'quantity','creation_date', 'order_id', 'order_id', 'order_id','order_id','order_id']
    if milkbasket_user :
        lis.append('order_id')
    # lis = ['order_id', 'customer_name', 'sku__sku_code', 'sku__sku_desc', 'quantity', 'updation_date', 'updation_date', 'marketplace']
    temp_data = copy.deepcopy(AJAX_DATA)
    extra_order_fields = get_misc_value('extra_order_fields', user.id)
    if extra_order_fields == 'false':
        extra_order_fields = []
    else:
        extra_order_fields = extra_order_fields.split(',')
    lis+= ['order_id']*len(extra_order_fields)
    search_parameters = {}
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_params['from_date'] = get_utc_start_date(search_params['from_date'])
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_params['to_date'] = get_utc_start_date(search_params['to_date'])
        search_parameters['creation_date__lt'] = search_params['to_date']
    filter_dict = {'sku_code':'sku__sku_code', 'marketplace':'marketplace','sku_category':'sku__sku_category',
                    'sub_category': 'sku__sub_category','sku_brand':'sku__sku_brand','sku_size':'sku__sku_size',
                    'sku_class':'sku__sku_class','city':'city', 'state':'state','order_reference':'order_reference',
                     'invoice_date': 'sellerordersummary__creation_date__icontains','customer_id':'customer_id',
                    'invoice_number': 'sellerordersummary__full_invoice_number', 'manufacturer':'sku__skuattributes__attribute_value__iexact',
                    'searchable': 'sku__skuattributes__attribute_value__iexact', 'bundle': 'sku__skuattributes__attribute_value__iexact',
                   }
    filter_parameter_list = list(set(filter_dict.keys()).intersection(set(search_params.keys())))
    for param in filter_parameter_list:
        search_parameters[filter_dict[param]] = search_params[param]
    if 'order_id' in search_params:
        order_detail = get_order_detail_objs(search_params['order_id'], user, search_params={}, all_order_objs=[])
        search_parameters['id__in'] = order_detail.values_list('id', flat=True)

    status_search = search_params.get('order_report_status', "")

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    search_parameters['quantity__gt'] = 0
    #central_order_reassigning =  get_misc_value('central_order_reassigning', user.id)
    #if central_order_reassigning == 'true':
    if 'sister_warehouse' in search_params and search_params['sister_warehouse']:
        sister_warehouse_name = search_params['sister_warehouse']
        user = User.objects.get(username=sister_warehouse_name)
        user = user
        sub_user = user
    else:
        pass

    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    search_parameters['user'] = user.id
    search_parameters['sku_id__in'] = sku_master_ids
    if search_params.get('invoice','') == 'true':
        orders = OrderDetail.objects.filter(**search_parameters).values('id','order_id','status','creation_date','order_code','unit_price',
                                                                    'invoice_amount','sku__sku_code','sku__sku_class','sku__sku_size','order_code',
                                                                    'sku__sku_desc','sku__price','sellerordersummary__full_invoice_number','sellerordersummary__challan_number','address',
                                                                    'quantity', 'original_quantity', 'original_order_id','order_reference','sku__sku_brand','customer_name','customer_id',
                                                                    'sku__mrp','customer_name','sku__sku_category','sku__mrp','city','state','marketplace','payment_received','sku_id','sku__sub_category','sku__hsn_code').distinct().annotate(sellerordersummary__creation_date=Cast('sellerordersummary__creation_date', DateField()))
    else:
        orders = OrderDetail.objects.filter(**search_parameters).values('id','order_id','status','creation_date','order_code','unit_price',
                                                                    'invoice_amount','sku__sku_code','sku__sku_class','sku__sku_size',
                                                                    'sku__sku_desc','sku__price','address','order_code','payment_mode',
                                                                    'quantity', 'original_quantity', 'original_order_id','order_reference','sku__sku_brand','customer_name','customer_id',
                                                                    'sku__mrp','customer_name','sku__sku_category','sku__mrp','city','state','marketplace','payment_received','sku_id','sku__sub_category','sku__hsn_code').distinct()
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
    if not search_params.has_key('tally_report'):
        try:
            temp_data['totalOrderQuantity'] = int(orders.values('id').distinct().aggregate(Sum('original_quantity', distinct=True))['original_quantity__sum'])
        except:
            temp_data['totalOrderQuantity'] = 0
        try:
            temp_data['totalSellingPrice'] = int(orders.values('id').distinct().aggregate(Sum('invoice_amount', distinct=True))['invoice_amount__sum'])
        except:
            temp_data['totalSellingPrice'] = 0
        try:
            temp_data['totalMRP'] = int(orders.aggregate(Sum('sku__mrp'))['sku__mrp__sum'])
        except:
            temp_data['totalMRP'] = 0
        total_row = {}
        total_row = OrderedDict((('Order Date', ''), ('Order ID', ""), ("Customer ID", ""), ('Customer Name', ""),('Order Reference' ,""),
        ('SKU Brand', ""),('SKU Category', ''),('SKU Class', ''),('SKU Size', ''), ('SKU Description', ''),('SKU Sub Category', ''),
        ('SKU Code', 'TotalQuantity='), ('Vehicle Number', ''),('Order Qty',temp_data['totalOrderQuantity']),('MRP', ''), ('Unit Price',''),('Discount', ''), ('Order Tax Amt',''),('Order Amt(w/o tax)', ''),
        ('Serial Number',''),('Invoice Number',''),('Challan Number', ''),('Invoice Qty',''),('Payment Type' ,''),('Reference Number',''),('Total Order Amt', ''),('Cancelled Order Qty', ''),('Cancelled Order Amt', ''),
        ('Order Amt(w/o tax)',''), ('Tax Percent',''), ('HSN Code', ''), ('Tax', ''),('City', ''), ('State', ''), ('Marketplace', 'TotalOrderAmount='),('Invoice Amount',''),('Order Amount', temp_data['totalSellingPrice']),
        ('Price', ''),('Status', ''), ('Order Status', ''),('Invoice Tax', ''),('Customer GST Number',''),('Remarks', ''), ('Order Taken By', ''),('Net Order Qty', ''), ('Net Order Amt', ''),
        ('Invoice Date',''),('Billing Address',''),('Shipping Address',''),('Payment Cash', ''),('Payment Card', ''),('Payment PhonePe',''),('Payment GooglePay',''),('Payment Paytm',''),('Payment Received', ''),('GST Number', ''),
        ('Procurement Price',''), ('Total Procurement Price','') , ('Margin',''), ('Invoice Amt(w/o tax)',''), ('Invoice Tax Amt',''), ('EwayBill Number','')))
        if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            total_row['Manufacturer'] = ''
            total_row['Searchable'] = ''
            total_row['Bundle'] = ''
        temp_data['aaData'].append(total_row)
        order_extra_fields ={}
        for extra in extra_order_fields :
            order_extra_fields[extra] = ''
        if  milkbasket_user :
            cost_price_dict = {'Cost Price': ''}
            temp_data['aaData'][0].update(OrderedDict(cost_price_dict))
        temp_data['aaData'][0].update(OrderedDict(order_extra_fields))
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
    invoice_no_gen = MiscDetail.objects.filter(user=user.id, misc_type='increment_invoice')
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for data in orders.iterator():
        cancelled_qty, cancelled_amt, net_qty, net_amt = 0, 0, 0, 0
        count = count + 1
        is_gst_invoice = False
        invoice_date = get_local_date(user, data['creation_date'], send_date='true')
        if datetime.datetime.strptime('2017-07-01', '%Y-%m-%d').date() <= invoice_date.date():
            is_gst_invoice = True
        date = get_local_date(user, data['creation_date']).split(' ')
        order_id = str(data['order_code']) + str(data['order_id'])
        if data['original_order_id']:
            order_id = data['original_order_id']
        payment_type = ''
        reference_number = ''
        manufacturer,searchable,bundle = '','',''
        attributes_obj = SKUAttributes.objects.filter(sku_id=data['sku_id'], attribute_name__in= attributes_list)
        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value

        if  'DC'  in data['order_code'] or 'PRE' in data['order_code']:
            payment_obj = OrderFields.objects.filter(original_order_id=data['original_order_id'], \
                                   name__contains='payment', user=user.id)
            if payment_obj.exists():
                payment_obj = payment_obj[0]
                payment_type = payment_obj.name.replace("payment_","")
            reference_obj = OrderFields.objects.filter(original_order_id=data['original_order_id'], \
                                   name='reference_number', user=user.id)
            if reference_obj.exists():
                reference_obj = reference_obj[0]
                reference_number = reference_obj.value
        cost_price = 0
        cost_price_dict = {}
        if milkbasket_user :
            picklist_obj = Picklist.objects.filter(order_id = data['id'] ,order__user = user.id, picked_quantity__gt=0)
            qty_price = dict(picklist_obj.values_list('order__sku__wms_code').distinct()\
            .annotate(weighted_cost=Sum(F('stock__batch_detail__buy_price') * F('picked_quantity'))))
            sku_quantity = dict(picklist_obj.values_list('order__sku__wms_code').distinct().annotate(count_qty=Sum('picked_quantity')))
            if sku_quantity and qty_price :
                sku_quantity = sku_quantity.values()[0]
                qty_price = qty_price.values()[0]
                if sku_quantity > 0 and qty_price > 0 :
                    cost_price = float(qty_price / sku_quantity)

            cost_price_dict['Cost Price']  = '%.2f'% cost_price


        # ['Open', 'Picklist generated', 'Partial Picklist generated', 'Picked', 'Partially picked']
        if not _status:
            if order_id_status.get(data['id'], '') == '1':
                status = ORDER_SUMMARY_REPORT_STATUS[0]
            elif data['id'] in picklist_generated:
                status = ORDER_SUMMARY_REPORT_STATUS[1]
            elif data['id'] in partially_picked:
                status = ORDER_SUMMARY_REPORT_STATUS[2]
            elif data['id'] in picked_orders:
                status = ORDER_SUMMARY_REPORT_STATUS[3]
            elif data['id'] in partial_generated:
                status = ORDER_SUMMARY_REPORT_STATUS[4]
            if order_id_status.get(data['id'], '') == '2':
                status = ORDER_DETAIL_STATES.get(2, '')
            if order_id_status.get(data['id'], '') == '5':
                status = ORDER_DETAIL_STATES.get(5, '')
        else:
            status = _status

        tax = 0
        vat = 5.5
        discount = 0
        unit_discount = 0
        mrp_price = data['sku__mrp']
        order_status = ''
        remarks = ''
        order_taken_by = ''
        vehicle_number = ''
        ewaybill_number = ''
        payment_card, payment_cash ,payment_PhonePe,payment_Paytm,payment_GooglePay = 0, 0,0,0,0
        order_summary = CustomerOrderSummary.objects.filter(order__user=user.id, order_id=data['id'])
        unit_price, unit_price_inclusive_tax = [data['unit_price']] * 2
        tax_percent = 0
        if order_summary.exists():
            mrp_price = order_summary[0].mrp
            discount = order_summary[0].discount
            if data['original_quantity']:
                unit_discount = float(discount)/float(data['original_quantity'])
            order_status = order_summary[0].status
            remarks = order_summary[0].central_remarks
            order_taken_by = order_summary[0].order_taken_by
            vehicle_number = order_summary[0].vehicle_number
            #unit_price_inclusive_tax = ((float(data.invoice_amount) / float(data.quantity)))
            if not is_gst_invoice:
                tax = order_summary[0].tax_value
                vat = order_summary[0].vat
                #if not unit_price:
                tax_percent = tax * (100/(data['original_quantity'] * data['unit_price']))
            else:
                amt = unit_price_inclusive_tax * float(data['original_quantity']) - discount
                tax_percent = order_summary[0].cgst_tax + order_summary[0].sgst_tax + order_summary[0].igst_tax + order_summary[0].utgst_tax
                cgst_amt = float(order_summary[0].cgst_tax) * (float(amt) / 100)
                sgst_amt = float(order_summary[0].sgst_tax) * (float(amt) / 100)
                igst_amt = float(order_summary[0].igst_tax) * (float(amt) / 100)
                utgst_amt = float(order_summary[0].utgst_tax) * (float(amt) / 100)
                tax = cgst_amt + sgst_amt + igst_amt + utgst_amt
            #unit_price = unit_price_inclusive_tax - (tax / float(data.quantity))
        else:
            tax = float(float(data['invoice_amount']) / 100) * vat
        if order_status == 'None':
            order_status = ''
        invoice_amount = float("%.2f" % ((float(unit_price) * float(data['original_quantity'])) + tax - discount))
        unit_invoice_amt = invoice_amount/data['original_quantity']
        taxable_amount = "%.2f" % abs(float(invoice_amount) - float(tax))
        unit_price = "%.2f" % unit_price

        #otherordercharges
        order_charges_obj = OrderCharges.objects.filter(user=user.id,order_id = data['original_order_id'])
        if order_charges_obj.exists():
            total_charge_amount = order_charges_obj.aggregate(Sum('charge_amount'))['charge_amount__sum']
            total_charge_tax = order_charges_obj.aggregate(Sum('charge_tax_value'))['charge_tax_value__sum']
            invoice_amount = '%.2f' %(float(invoice_amount)+float(total_charge_amount)+float(total_charge_tax))

        #payment mode
        payment_obj = OrderFields.objects.filter(user=user.id, name__icontains="payment_",\
                                      original_order_id=data['original_order_id']).values_list('name', 'value')
        if payment_obj.exists():
            for pay in payment_obj:
                if  'order_' in  pay[0] :
                    payment_type += pay[0].replace("order_payment_","")+"-"+pay[1]+","
                elif  'DC'  in data['order_code'] or 'PRE' in data['order_code']:
                   exec("%s = %s" % (pay[0],pay[1]))

        #pos extra fields
        pos_extra = {}
        extra_vals = OrderFields.objects.filter(user=user.id,\
                       original_order_id=data['original_order_id']).values('name', 'value')
        for field in extra_fields:
            pos_extra[field] = ''
            for val in extra_vals:
                if field == val['name']:
                    pos_extra[str(val['name'])] = str(val['value'])
        invoice_number,invoice_date,quantity,challan_number= '','',0,''
        if search_params.get('invoice','') == 'true':
            invoice_number = data['sellerordersummary__full_invoice_number']
            challan_number = data['sellerordersummary__challan_number']
            if not invoice_number :
                invoice_number_obj = SellerOrderSummary.objects.filter(order_id = data['id'])
                if invoice_number_obj.exists() :
                    challan_number = invoice_number_obj[0].challan_number
                    if not invoice_no_gen.exists() or (invoice_no_gen and invoice_no_gen[0].creation_date >= invoice_number_obj[0].creation_date):
                        if invoice_number_obj[0].order:
                            invoice_number = str(invoice_number_obj[0].order.order_id)
                        else:
                            invoice_number = str(invoice_number_obj[0].seller_order.order.order_id)
            if invoice_number:
                shipment_info = ShipmentInfo.objects.filter(order__user=user.id,order__original_order_id=data['original_order_id'],
                                                            invoice_number__endswith='/'+invoice_number)
                if shipment_info.exists():
                    ewaybill_number = str(shipment_info[0].order_shipment.ewaybill_number)

            if data['sellerordersummary__creation_date'] :
                invoice_date = data['sellerordersummary__creation_date'].strftime('%d %b %Y')
            else:
                invoice_date =''
            user_profile = UserProfile.objects.get(user_id=user.id)
            invoice_qty_filter = {}
            if user_profile.user_type == 'marketplace_user':
                invoice_qty_filter['seller_order__order_id'] = data['id']
                if data['sellerordersummary__full_invoice_number']:
                    invoice_qty_filter['full_invoice_number'] = data['sellerordersummary__full_invoice_number']
                quantity = SellerOrderSummary.objects.filter(**invoice_qty_filter).aggregate(Sum('quantity'))['quantity__sum']
            else:
                invoice_qty_filter['order_id'] = data['id']
                if data['sellerordersummary__full_invoice_number']:
                    invoice_qty_filter['full_invoice_number'] = data['sellerordersummary__full_invoice_number']
                else:
                    invoice_qty_filter['full_invoice_number'] = ''
                    invoice_date = ''
                quantity = SellerOrderSummary.objects.filter(**invoice_qty_filter).aggregate(Sum('quantity'))['quantity__sum']

        try:
            #serial_number = OrderIMEIMapping.objects.filter(po_imei__sku__wms_code =data.sku.sku_code,order__original_order_id=order_id,po_imei__sku__user=user.id)
            serial_number = OrderIMEIMapping.objects.filter(order__id=data['id'])
        except:
            serial_number =''
        if serial_number and serial_number[0].po_imei:
            serial_number = serial_number[0].po_imei.imei_number
        else:
            serial_number = ''
        customer_name = data['customer_name']
        billing_address = shipping_address =  ''
        if order_summary.exists():
            shipping_address = order_summary[0].consignee
        customer_master_obj = CustomerMaster.objects.filter(user = user.id, customer_id  = data['customer_id'])
        gst_number = ''
        if customer_master_obj.exists():
            gst_number = customer_master_obj[0].tin_number
            billing_address = customer_master_obj[0].address
            if not shipping_address :
                shipping_address = customer_master_obj[0].shipping_address
        if not billing_address :
            billing_address = data['address']
        if not shipping_address :
            shipping_address = billing_address

        if not quantity:
            quantity = 0

        amount = (float(unit_price) * float(quantity)) - (unit_discount * float(quantity))
        invoice_tax = "%.2f" % ((amount/100)*(tax_percent))

        invoice_amount_picked = "%.2f" % (amount + float(invoice_tax))

        if data['status'] and int(data['status']) == 3:
            cancelled_qty = data['quantity']
            cancelled_amt = cancelled_qty * unit_invoice_amt
        net_qty = data['original_quantity'] - cancelled_qty
        net_amt = invoice_amount - cancelled_amt

        order_extra_fields ={}
        for extra in extra_order_fields :
            order_field_obj = OrderFields.objects.filter(original_order_id=data['original_order_id'],user=user.id ,name = extra)
            order_extra_fields[extra] = ''
            if order_field_obj.exists():
                order_extra_fields[order_field_obj[0].name] = order_field_obj[0].value
        if search_params.get('invoice','') == 'true' and invoice_qty_filter:
            total_procurement_price, procurement_price, margin = get_margin_price_details(invoice_qty_filter, data, float(unit_price_inclusive_tax), quantity)
        else:
            total_procurement_price, procurement_price, margin = 0, 0, 0
        aaData = OrderedDict((('Order Date', ''.join(date[0:3])), ('Order ID', order_id),
                                                    ('Customer ID', data['customer_id']),
                                                    ('Customer Name', customer_name),
                                                    ('Order Reference' ,data['order_reference']),
                                                    ('SKU Brand', data['sku__sku_brand']),
                                                    ('SKU Category', data['sku__sku_category']),
                                                    ('SKU Sub Category', data['sku__sub_category']),
                                                    ('SKU Class', data['sku__sku_class']),
                                                    ('SKU Size', data['sku__sku_size']), ('SKU Description', data['sku__sku_desc']),
                                                    ('SKU Code', data['sku__sku_code']), ('Order Qty', int(data['original_quantity'])),
                                                    ('MRP', mrp_price), ('Unit Price', float(unit_price_inclusive_tax)),
                                                    ('Discount', discount),
                                                    ('Serial Number',serial_number),
                                                    ('Invoice Number',invoice_number),
                                                    ('Challan Number', challan_number),
                                                    ('Invoice Qty',quantity),('HSN Code', data['sku__hsn_code']),
                                                    ('Payment Type' ,payment_type),
                                                    ('Reference Number',reference_number),
                                                    ('Order Amt(w/o tax)', float(taxable_amount)),
                                                    ('Invoice Amt(w/o tax)', ("%.2f"%amount)),
                                                    ('Tax Percent', tax_percent),
                                                    ('Invoice Tax Amt', invoice_tax),
                                                    ('Order Tax Amt',("%.2f"%tax)),('Invoice Amount', invoice_amount_picked),
                                                    ('City', data['city']), ('State', data['state']), ('Marketplace', data['marketplace']),
                                                    ('Total Order Amt', float(invoice_amount)),('EwayBill Number', ewaybill_number),
                                                    ('Cancelled Order Qty', cancelled_qty),
                                                    ('Cancelled Order Amt', cancelled_amt),
                                                    ('Net Order Qty', net_qty), ('Net Order Amt', net_amt),
                                                    ('Price', data['sku__price']),
                                                    ('Status', status), ('Order Status', order_status),('Customer GST Number',gst_number),
                                                    ('Remarks', remarks), ('Order Taken By', order_taken_by),
                                                    ('Invoice Date',invoice_date),("Billing Address",billing_address),("Shipping Address",shipping_address),
                                                    ('Payment Cash', payment_cash), ('Payment Card', payment_card),('Payment PhonePe', payment_PhonePe),
                                                    ('Payment Paytm', payment_Paytm),('Payment GooglePay', payment_GooglePay), ('Payment Received', data['payment_received']), ('Vehicle Number', vehicle_number),
                                                    ('GST Number', user_gst_number), ('Procurement Price',procurement_price), ('Total Procurement Price',total_procurement_price), ('Margin',margin)))
        if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            aaData['Manufacturer'] = manufacturer
            aaData['Searchable'] = searchable
            aaData['Bundle'] = bundle
        aaData.update(OrderedDict(pos_extra))
        if milkbasket_user :
            aaData.update(OrderedDict(cost_price_dict))
        aaData.update(OrderedDict(order_extra_fields))
        if admin_user.username.lower() == 'gomechanic_admin' and search_params.has_key('tally_report'):
            tally_report = tally_dump(user,order_id,invoice_amount_picked,unit_price_inclusive_tax, gst_number,unit_discount,discount, taxable_amount, tax_percent, mrp_price, data,billing_address,customer_name,invoice_number, invoice_date, quantity, order_summary)
            if tally_report:
              temp_data['aaData'].append(tally_report)
        else:
            temp_data['aaData'].append(aaData)
    return temp_data

def tally_dump(user,order_id,invoice_amount_picked,unit_price_inclusive_tax, gst_number,unit_discount,discount, taxable_amount, tax_percent, mrp_price, data,billing_address,customer_name,invoice_number, invoice_date, quantity, order_summary):
    discount_percent, selling_price = 0, 0
    cgst_amount, sgst_amount, igst_amount = 0,0,0
    tally_Data = OrderedDict()
    discount = unit_discount*quantity
    unit_min_dis = float(data['unit_price']) - unit_discount
    selling_price = (unit_min_dis)+((unit_min_dis)*(tax_percent/100))
    try:
        discount_percent = (discount*100)/(quantity*float(data['unit_price']))
    except:
        discount_percent= 0
    amt = unit_price_inclusive_tax * float(quantity) - discount
    if order_summary:
      cgst_amount = float(order_summary[0].cgst_tax) * (float(amt) / 100)
      sgst_amount = float(order_summary[0].sgst_tax) * (float(amt) / 100)
      igst_amount = float(order_summary[0].igst_tax) * (float(amt) / 100)
      utgst_amount = float(order_summary[0].utgst_tax) * (float(amt) / 100)
    if invoice_number:
        tally_Data = OrderedDict((('Voucher Type', 'SPARE PARTS'),
                              ('Invoice Number', invoice_number),
                              ('Invoice Date', invoice_date),
                              ('Party Name',customer_name),
                              ('Address1', billing_address),
                              ('Address2', billing_address),
                              ('Address3', billing_address),
                              ('State Name', data['state']),
                              ('GSTIN', gst_number),
                              ('Main Location', 'Main Location'),
                              ('Stock item', data['sku__sku_desc']),
                              ('Qty', quantity),
                              ('Rate', float(data['unit_price'])),
                              ('Disc%', round(discount_percent)),
                              ('Sales Ledger', 'Sales'),
                              ('Sales Amount', float(taxable_amount)),
                              ('Sgst Ledger', 'SGST'),
                              ('SGST Amt', sgst_amount),
                              ('CGST Ledger', 'CGST'),
                              ('CGST Amount',cgst_amount),
                              ('Igst Ledger', 'IGST'),
                              ('IGST Amount', igst_amount),
                              ('Part Number', data['sku__sku_code']),
                              ('Unit', 'PC'),
                              ('Group', 'Roche'),
                              ('MRP', mrp_price),
                              ('Selling price(inc Tax)', round(selling_price)),
                              ('Cost price (Inc Tax)', 0),
                              ('Invoice Amount', invoice_amount_picked),
                              ('HSN Code', data['sku__hsn_code']),
                              ('GST', tax_percent)))
    return tally_Data

def get_margin_price_details(invoice_qty_filter, order_data, unit_price, inv_quantity):
    total_procurement_price, procurement_price, margin = 0, 0, 0
    pick_obj = SellerOrderSummary.objects.filter(**invoice_qty_filter).values('picklist__stock__unit_price', 'quantity')
    if pick_obj:
        for picklist in pick_obj:
            if picklist.get('picklist__stock__unit_price','') and picklist.has_key('quantity'):
                total_procurement_price += (picklist['picklist__stock__unit_price'] * picklist['quantity'])
            else:
                total_procurement_price += 0
        if total_procurement_price > 0 and inv_quantity > 0:  
            procurement_price = total_procurement_price/inv_quantity
            margin = (unit_price * inv_quantity) - total_procurement_price  
    else:
        total_procurement_price, procurement_price, margin = 0, 0, 0
    return round(total_procurement_price, 2), round(procurement_price, 2), round(margin, 2)

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
           'open_po__sku__sku_category','open_po__sku__sub_category','open_po__sku__sku_brand',
           'open_po__sku__sku_category','open_po__sku__sub_category','open_po__sku__sku_brand',
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
    if 'sku_category' in search_params:
        search_parameters['open_po__sku__sku_category'] = search_params['sku_category']
    if 'sub_category' in search_params:
        search_parameters['open_po__sku__sub_category'] = search_params['sub_category']
    if 'sku_brand' in search_params:
        search_parameters['open_po__sku__sku_brand'] = search_params['sku_brand']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['open_po__sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['open_po__sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['open_po__sku__skuattributes__attribute_value__iexact'] = search_params['bundle']


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
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for data in seller_pos:
        accepted_quan = 0
        rejected_quan = 0
        manufacturer,searchable,bundle = '','',''
        attributes_obj = SKUAttributes.objects.filter(sku_id=data.open_po.sku.id, attribute_name__in= attributes_list)
        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value
        final_price = '%.2f' %(float(data.open_po.price))
        if data.unit_price:
            final_price = '%.2f' % (float(data.unit_price))
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
        ord_dict = OrderedDict((('Date', get_local_date(user, data.creation_date)), ('Supplier', data.open_po.supplier.name),
                     ('Seller ID', data.seller.seller_id), ('Seller Name', data.seller.name),
                     ('SKU Code', data.open_po.sku.sku_code), ('SKU Description', data.open_po.sku.sku_desc),
                     ('SKU category', data.open_po.sku.sku_category),('Sub category', data.open_po.sku.sub_category),
                     ('SKU Class', data.open_po.sku.sku_class), ('SKU Style Name', data.open_po.sku.style_name),
                     ('SKU Brand', data.open_po.sku.sku_brand), ('SKU Category', data.open_po.sku.sku_category),
                     ('Accepted Qty', accepted_quan), ('Rejected Qty', rejected_quan),
                     ('Total Qty', data.open_po.order_quantity), ('Amount', '%.2f' % amount),
                     ('Tax', data.open_po.tax), ('Total Amount', '%.2f' % total_amount),
                     ('DT_RowClass', 'results'), ('DT_RowAttr', {'data-id': data.id})))
        if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            ord_dict['Manufacturer'] = manufacturer
            ord_dict['Searchable'] = searchable
            ord_dict['Bundle'] = bundle
        temp_data['aaData'].append(ord_dict)

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
        transaction_id = '%s-%s-%s-%s' % (return_id, str(sku_code), str(order_return[0].return_type[:3]), date_str)
        if order_return and order_return[0].seller_order:
            seller_order = order_return[0].seller_order
            seller_id = seller_order.seller.seller_id
            order = order_return[0].seller_order.order
            invoice_amount = (order.invoice_amount / order.quantity) * data['total_received']
            transaction_id = '%s-%s-%s' % (str(order.order_id), str(seller_order.sor_id), transaction_id)
        elif order_return and order_return[0].order:
            order = order_return[0].order
            invoice_amount = (order.invoice_amount / order.quantity) * data['total_received']
            transaction_id = '%s-%s' % (str(order.order_id), transaction_id)
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
    if 'sku_category' in search_params:
        status_filter['sku__sku_category'] = search_params['sku_category']
    if 'sub_category' in search_params:
        status_filter['sku__sub_category'] = search_params['sub_category']
    if 'sku_brand' in search_params:
        status_filter['sku__sku_brand'] = search_params['sku_brand']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            status_filter['sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            status_filter['sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            status_filter['sku__skuattributes__attribute_value__iexact'] = search_params['bundle']

    lis = [
            'creation_date', 'sku__sku_code', 'sku__sku_desc', 'sku__style_name', 'sku__sku_brand', 'sku__sku_category','sku__sub_category',
            'sku__sku_size', 'opening_stock', 'opening_stock_value','receipt_qty', 'produced_qty', 'dispatch_qty', 'return_qty',
            'adjustment_qty', 'closing_stock','adjustment_qty', 'closing_stock', 'closing_stock_value', 'creation_date'
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
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for obj in stock_stats:
        manufacturer,searchable,bundle = '','',''
        attributes_obj = SKUAttributes.objects.filter(sku_id=obj.sku.id, attribute_name__in= attributes_list)
        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value
        date = get_local_date(user, obj.creation_date, send_date=True).strftime('%d %b %Y')
        ord_dict = OrderedDict((('Date', date),
                                 ('SKU Code', obj.sku.sku_code), ('SKU Description', obj.sku.sku_desc),
                                 ('Style Name', obj.sku.style_name),
                                 ('Brand', obj.sku.sku_brand), ('Category', obj.sku.sku_category),
                                 ('Sub Category', obj.sku.sub_category),
                                 ('Size', obj.sku.sku_size), ('Opening Stock', obj.opening_stock), ('Opening Stock Value', obj.opening_stock_value),
                                 ('Receipt Quantity', obj.receipt_qty + obj.uploaded_qty),
                                 ('Produced Quantity', obj.produced_qty),
                                 ('Dispatch Quantity', obj.dispatch_qty), ('Return Quantity', obj.return_qty),
                                 ('Consumed Quantity', obj.consumed_qty),('RTV Quantity',obj.rtv_quantity),
                                 ('Adjustment Quantity', obj.adjustment_qty), ('Closing Stock', obj.closing_stock), ('Closing Stock Value', obj.closing_stock_value)
                                 ))
        if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            ord_dict['Manufacturer'] = manufacturer
            ord_dict['Searchable'] = searchable
            ord_dict['Bundle'] = bundle
        data.append(ord_dict)
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
           'seller_po_summary__invoice_number', 'return_date', 'return_reason' ,'rtv_number']
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
    if 'sku_code' in search_params:
        search_parameters['seller_po_summary__purchase_order__open_po__sku__wms_code'] = search_params['sku_code']
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
        rtv_reason ,updated_user_name = '' ,''
        rtv = ReturnToVendor.objects.filter(seller_po_summary__purchase_order__open_po__sku__user=user.id, status=0,
                                            rtv_number=data['rtv_number'])
        if rtv.exists():
            rtv_reason = rtv[0].return_reason
            version_obj = Version.objects.get_for_object(rtv[0])
            if version_obj.exists():
                updated_user_name = version_obj.order_by('-revision__date_created')[0].revision.user.username

        order_id = get_po_reference(rtv[0].seller_po_summary.purchase_order)
        date = get_local_date(user, rtv[0].creation_date)
        temp_data['aaData'].append(OrderedDict((('RTV Number', data['rtv_number']),
                                    ('Supplier ID', data['seller_po_summary__purchase_order__open_po__supplier_id']),
                                    ('Supplier Name', data['seller_po_summary__purchase_order__open_po__supplier__name']),
                                    ('Order ID', order_id),
                                    ('Invoice Number', data['seller_po_summary__invoice_number']),
                                    ('Return Date', date), ('Reason',rtv_reason) ,
                                    ('Updated User', updated_user_name)
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

    totals_map = {}
    for data in model_data:
        status = ""
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
    reseller_dist_mapping = dict(CustomerMaster.objects.filter(user__in=distributors).values_list('id', 'user'))
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

    #search_parameters['cust_wh_id__in'] = distributors
    search_parameters['customer_id__in'] = CustomerMaster.objects.filter(user__in=distributors).values_list('id', flat=True)
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
        zone_code = ''
        reseller_dist_code = reseller_dist_mapping.get(data['customer_id'], '')
        if reseller_dist_code:
            zone_code = zones_map.get(reseller_dist_code, '')
            dist_code = dist_names_map.get(reseller_dist_code, '')
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
        status = ''
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
        # if sub_user.userprofile.zone:
        #     zone_id = sub_user.userprofile.zone
        #     distributors = UserProfile.objects.filter(user__in=distributors,
        #                                               zone__icontains=zone_id).values_list('user_id', flat=True)
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
    # if 'enquiry_number' in search_params:
    #     search_parameters['enquiry__enquiry_id__contains'] = search_params['enquiry_number']
    if 'sku_code' in search_params:
        search_parameters['sku__sku_code'] = search_params['sku_code']
    if 'warehouse_level' in search_params:
        search_parameters['warehouse_level'] = search_params['warehouse_level']
    if 'aging_period' in search_params:
        try:
            aging_period = int(search_params['aging_period'])
        except:
            aging_period = 0
        extend_date = datetime.datetime.today() + datetime.timedelta(days=aging_period)
        search_parameters['enquiry__extend_date'] = extend_date
    if 'corporate_name' in search_params:
        search_parameters['enquiry__customer_name'] = search_params['corporate_name']

    resellers_qs = CustomerUserMapping.objects.filter(customer__user__in=distributors)
    resellers_names_map = dict(resellers_qs.values_list('customer_id',
                                                        Concat('user__username', Value(' - '), 'user__first_name')))

    enquired_sku_qs = EnquiredSku.objects.filter(**search_parameters)
    enq_ids = enquired_sku_qs.values_list('id', flat=True)
    asn_res_qs = ASNReserveDetail.objects.filter(enquirydetail_id__in=enq_ids, enquirydetail__warehouse_level=1, reserved_qty__gt=0)
    temp_data['recordsTotal'] = enquired_sku_qs.count() + asn_res_qs.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    if stop_index:
        enquired_sku_qs = enquired_sku_qs[start_index:stop_index]

    totals_map = {}
    for asn_obj in asn_res_qs:
        en_obj = asn_obj.enquirydetail
        em_obj = en_obj.enquiry
        uniq_enq_id = str(em_obj.customer_id) + str(em_obj.enquiry_id)
        if 'enquiry_number' in search_params:
            if search_params['enquiry_number'] not in uniq_enq_id:
                continue
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
        user_name = en_obj.sku.user
        warehouse = ''
        if user_name:
            user = User.objects.get(id=user_name)
            warehouse = user.username
        sku_code = en_obj.sku.sku_code
        quantity = asn_obj.reserved_qty
        warehouse_level = 3
        corporate_name = en_obj.enquiry.corporate_name
        remarks = en_obj.enquiry.remarks
        if 'Total Qty' not in totals_map:
            totals_map['Total Qty'] = quantity
        else:
            totals_map['Total Qty'] += quantity
        prod_catg = en_obj.sku.sku_category
        ord_dict = OrderedDict((('Zone Code', zone),
                                ('Distributor Code', distributor_name),
                                ('Reseller Code', customer_name),
                                ('Product Category', prod_catg),
                                ('SKU Code', sku_code),
                                ('SKU Quantity', quantity),
                                ('Warehouse Level', warehouse_level),
                                ('Enquiry No', uniq_enq_id),
                                ('Level', warehouse_level),
                                ('Warehouse', warehouse),
                                ('Enquiry Aging', days_left),
                                ('Enquiry Status', extend_status),
                                ('Corporate Name', corporate_name),
                                ('Remarks', remarks),
                                ))
        temp_data['aaData'].append(ord_dict)
    for en_obj in enquired_sku_qs:
        em_obj = en_obj.enquiry
        uniq_enq_id = str(em_obj.customer_id) + str(em_obj.enquiry_id)
        if 'enquiry_number' in search_params:
            if search_params['enquiry_number'] not in uniq_enq_id:
                continue
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
        user_name = en_obj.sku.user
        warehouse = ''
        if user_name:
            user = User.objects.get(id = user_name)
            warehouse = user.username
        sku_code = en_obj.sku.sku_code
        quantity = en_obj.quantity
        warehouse_level = en_obj.warehouse_level
        corporate_name = en_obj.enquiry.corporate_name
        remarks = en_obj.enquiry.remarks
        if 'Total Qty' not in totals_map:
            totals_map['Total Qty'] = quantity
        else:
            totals_map['Total Qty'] += quantity
        prod_catg = en_obj.sku.sku_category
        ord_dict = OrderedDict((('Zone Code', zone),
                                ('Distributor Code', distributor_name),
                                ('Reseller Code', customer_name),
                                ('Product Category', prod_catg),
                                ('SKU Code', sku_code),
                                ('SKU Quantity', quantity),
                                ('Warehouse Level',warehouse_level),
                                ('Enquiry No', uniq_enq_id),
                                ('Level', warehouse_level),
                                ('Warehouse', warehouse),
                                ('Enquiry Aging', days_left),
                                ('Enquiry Status', extend_status),
                                ('Corporate Name', corporate_name),
                                ('Remarks', remarks),
                               ))
        temp_data['aaData'].append(ord_dict)
    temp_data['totals'] = totals_map
    return temp_data


def get_shipment_report_data(search_params, user, sub_user, serial_view=False, firebase_response=None):
    from common import get_admin ,get_full_invoice_number
    from rest_api.views.common import get_sku_master, get_order_detail_objs, get_linked_user_objs, get_misc_value, \
        get_local_date
    #sku_master, sku_master_ids = get_sku_master(user, sub_user)
    admin_user = get_admin(user)
    invoice_date = ''
    payment_status = ''
    central_order_reassigning =  get_misc_value('central_order_reassigning', user.id)
    increment_invoice = get_misc_value('increment_invoice', user.id)
    search_parameters = {}
    sister_whs = [user.id]
    if user.userprofile.warehouse_type == 'admin':
        sister_whs = list(User.objects.filter(username__in=get_linked_user_objs(user, user)).values_list('id', flat=True))
        sister_whs.append(user.id)
    if not firebase_response:
        firebase_response = {}

    lis = ['order_shipment__shipment_number', 'order__original_order_id', 'order__sku__sku_code', 'order__title',
           'order__sku__sku_category', 'order__sku__sub_category','order__sku__sku_brand',
           'order__customer_name', 'order__quantity', 'shipping_quantity', 'order_shipment__truck_number', 'creation_date',
           'id', 'id', 'order__customerordersummary__payment_status', 'order_packaging__package_reference',
           'order__original_order_id', 'order__original_order_id']
    search_parameters['order__user__in'] = sister_whs
    search_parameters['shipping_quantity__gt'] = 0
    #search_parameters['order__sku_id__in'] = sku_master_ids
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
    if 'sku_category' in search_params:
        search_parameters['order__sku__sku_category'] = search_params['sku_category']
    if 'sub_category' in search_params:
        search_parameters['order__sku__sub_category'] = search_params['sub_category']
    if 'sku_brand' in search_params:
        search_parameters['order__sku__sku_brand'] = search_params['sku_brand']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['order__sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['order__sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['order__sku__skuattributes__attribute_value__iexact'] = search_params['bundle']

    if 'customer_id' in search_params:
        search_parameters['order__customer_id'] = search_params['customer_id']
    if 'order_id' in search_params:
        order_detail = get_order_detail_objs(search_params['order_id'], user, search_params={'user__in': sister_whs}, all_order_objs=[])
        if order_detail:
            search_parameters['order_id__in'] = order_detail.exclude(status=3).values_list('id', flat=True)
        else:
            search_parameters['order_id__in'] = []
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    model_data = ShipmentInfo.objects.filter(**search_parameters)\
                                    .values('order_shipment__shipment_number', 'order__order_id', 'id','order__status',
                                           'order__original_order_id', 'order__id','order__order_code', 'order__sku__sku_code','order__sku_id',
                                           'order__sku__sku_category','order__sku__sub_category','order__sku__sku_brand',
                                           'order__title', 'order__customer_name', 'order__quantity', 'shipping_quantity',
                                           'order_shipment__truck_number', 'creation_date',
                                           'order_shipment__courier_name',
                                           'order_shipment__manifest_number',
                                           'order_shipment__creation_date',
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

    seventytwo_networks = False
    ord_det_ids = [i['order__id'] for i in model_data]
    ord_invoice_map = dict(SellerOrderSummary.objects.filter(order_id__in=ord_det_ids).values_list('order_id', 'invoice_number'))
    ord_serialnum_map = dict(OrderIMEIMapping.objects.filter(order_id__in=ord_det_ids).values_list('order_id', 'po_imei__imei_number'))
    ord_inv_dates_map = dict(OrderIMEIMapping.objects.filter(order_id__in=ord_det_ids).values_list('order_id', 'creation_date'))
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for data in model_data:
        sku_id = data['order__sku_id']
        manufacturer,searchable,bundle = '','',''
        attributes_obj = SKUAttributes.objects.filter(sku_id=sku_id, attribute_name__in= attributes_list)
        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value
        order_id = data['order__original_order_id']
        result = firebase_response.get(order_id, '')
        if not order_id:
            order_id = data['order__order_code'] + str(data['order__order_id'])
        try:
            date = get_local_date(user, data['creation_date']).split(' ')
        except Exception as e:
            import traceback
            log.info('Error in Get Local Date:%s:%s' %(order_id, data['creation_date']))
            log.info(traceback.format_exc())

        shipment_status = ship_status.get(data['id'], '')

        if admin_user.get_username().lower() == '72Networks'.lower() :
            seventytwo_networks = True
            if not firebase_response:
                try:
                    from firebase import firebase
                    firebase = firebase.FirebaseApplication('https://pod-stockone.firebaseio.com/', None)
                    result = firebase.get('/OrderDetails/'+order_id, None)
                except Exception as e:
                    result = 0
                    import traceback
                    log.debug(traceback.format_exc())
                    log.info('Firebase query  failed for %s and params are  and error statement is %s' % (
                    str(user.username),str(e)))
        delivered_time =''
        if data['order__original_order_id'] :
            order = OrderDetail.objects.filter(original_order_id = data['order__original_order_id'] ,user = user.id)
            payment_status = order.values('customerordersummary__payment_status')[0].get('customerordersummary__payment_status','')
        if ord_invoice_map and central_order_reassigning == 'true':
            creation_date = ord_inv_dates_map.get(data['order__id'], '')
            if creation_date:
                invoice_date = get_local_date(user, creation_date)
                invoice_number = ord_invoice_map.get(data['order__id'], '')
                if order.exists():
                    invoice_number = get_full_invoice_number(user,invoice_number,order[0],creation_date ,'')
            else:
                invoice_number = '%s' % data['order__original_order_id']
        else:
            if data['order__id'] in ord_invoice_map and increment_invoice == 'true':
                invoice_number = ord_invoice_map.get(data['order__id'], '')
                creation_date = ord_inv_dates_map.get(data['order__id'], '')
                if creation_date:
                    invoice_date = get_local_date(user, creation_date)
                    invoice_number = get_full_invoice_number(user,invoice_number,order[0], invoice_date)
                else:
                    invoice_number = get_full_invoice_number(user,invoice_number,order[0])
            elif increment_invoice == 'false':
                invoice_number =  int(data['order__order_id'])
                if data['order__id'] in ord_invoice_map:
                    creation_date = ord_inv_dates_map.get(data['order__id'], '')
                    if creation_date:
                        invoice_date = get_local_date(user, creation_date)
                        invoice_number = get_full_invoice_number(user,invoice_number,order[0], invoice_date)
                    else:
                        invoice_number = get_full_invoice_number(user,invoice_number,order[0])
            else:
                invoice_number = ''
        if result :
           signed_invoice_copy = result.get('signed_invoice_copy','')
           id_type = result.get('id_type','')
           id_card = result.get('id_card','')
           id_proof_number = result.get('id_proof_number','')
           try :
               pod_status = result['pod_status']
           except:
               pod_status = False
           delivered_time = result.get('time','')
           refusal =  result.get('refusal',False)
           refusal_reason = result.get('refusal_reason','')
        else:
            signed_invoice_copy =''
            id_type =''
            id_card =''
            id_proof_number = ''
            pod_status = False
            refusal = False
            refusal_reason =''
        if seventytwo_networks :
            shipment_status = 'Dispatched'
        if pod_status :
            shipment_status = 'Delivered'
        if refusal :
            shipment_status =  'Refused'
        order_return_obj = OrderReturns.objects.filter(order__original_order_id = order_id,sku__wms_code = data['order__sku__sku_code'],sku__user=user.id)
        if order_return_obj.exists() and central_order_reassigning == 'true' :
            shipment_status = 'Returned'
        if id_proof_number and shipment_status == 'Returned':
            shipment_status = 'Delivered'
        serial_number = ''
        # serial_number_qs = OrderIMEIMapping.objects.filter(order_id=data['order__id'])
        # if serial_number_qs:
        #     if serial_number_qs[0].po_imei:
        #         serial_number = serial_number_qs[0].po_imei.imei_number
        serial_number = ord_serialnum_map.get(data['order__id'], '')
        dispatched_date =  data['order_shipment__creation_date'].strftime("%d %b, %Y")

        if delivered_time :
            delivered_time = int(delivered_time)
            delivered_time = time.strftime('%d %b %Y %I:%M %p', time.localtime(delivered_time/1e3))

        manifest_number = int(data['order_shipment__manifest_number'])

        ord_dict = OrderedDict((('Shipment Number', data['order_shipment__shipment_number']),
                                                ('Order ID', order_id), ('SKU Code', data['order__sku__sku_code']),
                                                ('SKU Category', data['order__sku__sku_category']),
                                                ('Sub Category', data['order__sku__sub_category']),
                                                ('SKU Brand', data['order__sku__sku_brand']),
                                                ('Title', data['order__title']),
                                                ('Customer Name', data['order__customer_name']),
                                                ('Quantity', data['order__quantity']),
                                                ('Shipped Quantity', data['shipping_quantity']),
                                                ('Truck Number', data['order_shipment__truck_number']),
                                                ('Date', ' '.join(date)),
                                                ('Signed Invoice Copy',signed_invoice_copy),
                                                ('ID Type',id_type),
                                                ('Manifest Number',manifest_number),
                                                ('ID Card' , id_card),
                                                ('Serial Number' ,serial_number),
                                                ('ID Proof Number' , id_proof_number),
                                                ('Shipment Status',shipment_status ),
                                                ('Dispatched Date',dispatched_date),
                                                ('Delivered Date', delivered_time),
                                                ('Refusal Reason',refusal_reason),
                                                ('Invoice Number',invoice_number),
                                                ('Invoice Date', invoice_date),
                                                ('Courier Name', data['order_shipment__courier_name']),
                                                ('Payment Status', payment_status),
                                                ('Pack Reference', data['order_packaging__package_reference'])))
        if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            ord_dict['Manufacturer'] = manufacturer
            ord_dict['Searchable'] = searchable
            ord_dict['Bundle'] = bundle
        temp_data['aaData'].append(ord_dict)
    return temp_data

def get_po_report_data(search_params, user, sub_user, serial_view=False):
    from miebach_admin.models import *
    from miebach_admin.views import *
    from common import get_admin
    from rest_api.views.common import  get_order_detail_objs,get_purchase_order_data
    oneassist_condition = get_misc_value('dispatch_qc_check', user.id)
    lis = ['open_po__sku__sku_code', 'open_po__sku__sku_desc', 'open_po__sku__sku_category', 'open_po__sku__sub_category',
            'open_po__sku__sku_brand','open_po__order_quantity','order_id',
            'open_po__sku__user']
    order_data=lis[1]
    if search_params.get('order_term'):
        order_data = lis[search_params['order_index']]
        if search_params['order_term'] == 'desc':
            order_data = "-%s" % order_data

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
        search_parameters['open_po__sku__sku_code'] = search_params['sku_code']
    if 'sku_category' in search_params:
        search_parameters['open_po__sku__sku_category'] = search_params['sku_category']
    if 'sub_category' in search_params:
        search_parameters['open_po__sku__sub_category'] = search_params['sub_category']
    if 'sku_brand' in search_params:
        search_parameters['open_po__sku__sku_brand'] = search_params['sku_brand']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['open_po__sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['open_po__sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['open_po__sku__skuattributes__attribute_value__iexact'] = search_params['bundle']


    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    if 'sister_warehouse' in search_params:
        sister_warehouse_name = search_params['sister_warehouse']
        user = User.objects.get(username=sister_warehouse_name)
        warehouses = UserGroups.objects.filter(user_id=user.id)
    else:
        warehouses = UserGroups.objects.filter(admin_user_id=user.id)
    warehouse_users = dict(warehouses.values_list('user_id', 'user__username'))
    warehouse_users[user.id] = user.username
    purchase_orders = PurchaseOrder.objects.filter(open_po__sku__user__in=warehouse_users.keys(),
                                                   received_quantity__lt=F('open_po__order_quantity')).\
                    exclude(status='location-assigned').filter(**search_parameters).order_by(order_data)
    # if not purchase_orders:
    #     rw_orders = RWPurchase.objects.filter(rwo__vendor__user=user.id,
    #                                           rwo__job_order__product_code_id__in=sku_master_ids). \
    #         exclude(purchase_order__status__in=['location-assigned', 'stock-transfer']). \
    #         values_list('purchase_order_id', flat=True)
    #     purchase_orders = PurchaseOrder.objects.filter(id__in=rw_orders)

    temp_data['recordsTotal'] = purchase_orders.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    ship_search_params  = {}
    if stop_index:
        purchase_orders = purchase_orders[start_index:stop_index]
    po_reference_no = ''
    admin_user = get_admin(user)
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for order in purchase_orders:
        manufacturer,searchable,bundle = '','',''
        attributes_obj = SKUAttributes.objects.filter(sku_id=order.open_po.sku_id, attribute_name__in= attributes_list)
        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value
        po_reference_no = '%s%s_%s' % (
        order.prefix, str(order.creation_date).split(' ')[0].replace('-', ''), order.order_id)
        customer_name, sr_number = '', ''
        if oneassist_condition == 'true':
            customer_data = OrderMapping.objects.filter(mapping_id=order.id, mapping_type='PO')
            if customer_data:
                customer_name = customer_data[0].order.customer_name
                interorder_data = IntermediateOrders.objects.filter(order_id=customer_data[0].order_id, user_id=admin_user.id)
                if interorder_data:
                    inter_order_id  = interorder_data[0].interm_order_id
                    courtesy_sr_number = OrderFields.objects.filter(original_order_id = inter_order_id, user = admin_user.id, name = 'original_order_id')
                    if courtesy_sr_number:
                        sr_number = courtesy_sr_number[0].value
        po_quantity = float(order.open_po.order_quantity) - float(order.received_quantity)
        warehouse_location = warehouse_users[order.open_po.sku.user]
        ord_dict = OrderedDict((('SKU Code',order.open_po.sku.wms_code),('PO No',po_reference_no),
                                                ('SKU Category',order.open_po.sku.sku_category),('Sub Category',order.open_po.sku.sub_category),
                                                ('SKU Brand',order.open_po.sku.sku_brand),
                                                ('Quantity',po_quantity ), ('Sku Description', order.open_po.sku.sku_desc),
                                                ('Location',warehouse_location), ('Customer Name', customer_name),
                                ('SR Number', sr_number)))
        if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            ord_dict['Manufacturer'] = manufacturer
            ord_dict['Searchable'] = searchable
            ord_dict['Bundle'] = bundle
        temp_data['aaData'].append(ord_dict)

    return temp_data


def get_open_order_report_data(search_params, user, sub_user, serial_view=False):
    from miebach_admin.views import get_misc_value
    from common import get_admin
    lis = ['open_po__sku__sku_code', 'open_po__sku__sku_desc', 'open_po__order_quantity','open_po__sku__sku_code']
    if search_params.get('order_term'):
        order_data = lis[search_params['order_index']]
        if search_params['order_term'] == 'desc':
            order_data = "-%s" % order_data

    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    serach_picked ={}
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lt'] = search_params['to_date']
    if 'sku_code' in search_params:
        search_parameters['sku__sku_code'] = search_params['sku_code']
        serach_picked['order__sku__sku_code'] = search_params['sku_code']

    central_order_reassigning =  get_misc_value('central_order_reassigning', user.id)

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    if 'sister_warehouse' in search_params:
        sister_warehouse_name = search_params['sister_warehouse']
        user = User.objects.get(username=sister_warehouse_name)
        warehouses = UserGroups.objects.filter(user_id=user.id)
    else:
        warehouses = UserGroups.objects.filter(admin_user_id=user.id)
    for warehouse in warehouses:
        view_orders = OrderDetail.objects.filter(user= warehouse.user_id, status =1,quantity__gt=0).filter(**search_parameters)
        picked_orders = Picklist.objects.filter(status__contains='open', order__user= warehouse.user_id, reserved_quantity__gt=0).filter(**serach_picked).select_related('order')
        temp_data['recordsTotal'] += view_orders.count() + picked_orders.count()
        temp_data['recordsFiltered'] += temp_data['recordsTotal']

        if stop_index:
            view_orders = view_orders[start_index:stop_index]
        for order in view_orders:
            try :
                interm_obj = IntermediateOrders.objects.filter(order_id=str(order.id))
                if interm_obj.exists() :
                    orderfield_obj = OrderFields.objects.filter(original_order_id=str(order.original_order_id), order_type='intermediate_order',user=str(interm_obj[0].user.id)).values('name','value')
                    if orderfield_obj:
                        checking_dict = {}
                        for order_field in orderfield_obj :
                            var_name = order_field.get('name')
                            var_value  = order_field.get('value')
                            checking_dict[var_name] = var_value
                    unit_price = order.unit_price
                    cgst = interm_obj[0].cgst_tax
                    sgst = interm_obj[0].sgst_tax
                    igst = interm_obj[0].igst_tax
                    location = interm_obj[0].order_assigned_wh

                    temp_data['aaData'].append(OrderedDict((('Central Order ID', order.original_order_id),('Batch Number',checking_dict.get('batch_number','')),\
                                                    ('Batch Date',checking_dict.get('batch_date','')),('Branch ID',checking_dict.get('branch_id','')),('Branch Name',checking_dict.get('branch_name','')),\
                                                    ('Loan Proposal ID',order.original_order_id),('Loan Proposal Code',checking_dict.get('loan_proposal_code','')),('Client Code',checking_dict.get('client_code','')),\
                                                    ('Client ID',checking_dict.get('client_id','')),('Customer Name',order.customer_name),('Address1',checking_dict.get('address1','')),('Address2',checking_dict.get('address2','')),\
                                                    ('Landmark',checking_dict.get('landmark','')),('Village',checking_dict.get('village','')),('District',checking_dict.get('district','')),('State1',checking_dict.get('state','')),('Pincode',checking_dict.get('pincode','')),\
                                                    ('Mobile Number',checking_dict.get('mobile_no','')),('Alternative Mobile Number',checking_dict.get('alternative_mobile_no','')),('SKU Code',order.sku.sku_code),('Model',checking_dict.get('model','')),
                                                    ('Unit Price',unit_price),('CGST',cgst),('SGST',sgst),('IGST',igst),('Total Price',checking_dict.get('total_price','')),('Location',location.username))))
            except Exception as e:
                import traceback
                log.debug(traceback.format_exc())
                log.info(' open order report  failed for %s and params are  and error statement is %s' % (
                str(user.username), str(e)))

        if stop_index:
            picked_orders = picked_orders[start_index:stop_index]
        for picked_order in picked_orders :
            try :
                interm_obj = IntermediateOrders.objects.filter(order_id=str(picked_order.order.id))
                if interm_obj.exists() :
                    orderfield_obj = OrderFields.objects.filter(original_order_id=str(picked_order.order.original_order_id), order_type='intermediate_order',user=str(interm_obj[0].user.id)).values('name','value')
                    if orderfield_obj :
                        for order_field in orderfield_obj :
                            checking_dict = {}
                            for order_field in orderfield_obj :
                                var_name = order_field.get('name')
                                var_value  = order_field.get('value')
                                checking_dict[var_name] = var_value
                    unit_price = order.unit_price
                    cgst = interm_obj[0].cgst_tax
                    sgst = interm_obj[0].sgst_tax
                    igst = interm_obj[0].igst_tax
                    location = interm_obj[0].order_assigned_wh

                    temp_data['aaData'].append(OrderedDict((('Central Order ID', picked_order.order.original_order_id),('Batch Number',checking_dict.get('batch_number','')),\
                                                    ('Batch Date',checking_dict.get('batch_date','')),('Branch ID',checking_dict.get('branch_id','')),('Branch Name',checking_dict.get('branch_name','')),\
                                                    ('Loan Proposal ID',order.original_order_id),('Loan Proposal Code',picked_order.order.original_order_id),('Client Code',checking_dict.get('client_code','')),\
                                                    ('Client ID',checking_dict.get('client_id','')),('Customer Name',picked_order.order.customer_name),('Address1',checking_dict.get('address1','')),('Address2',checking_dict.get('address2','')),\
                                                    ('Landmark',checking_dict.get('landmark','')),('Village',checking_dict.get('village','')),('District',checking_dict.get('district','')),('State1',checking_dict.get('state','')),('Pincode',checking_dict.get('pincode','')),\
                                                    ('Mobile Number',checking_dict.get('mobile_no','')),('Alternative Mobile Number',checking_dict.get('alternative_mobile_no','')),('SKU Code',picked_order.order.sku.sku_code),('Model',checking_dict.get('model','')),
                                                    ('Unit Price',unit_price),('CGST',cgst),('SGST',sgst),('IGST',igst),('Total Price',checking_dict.get('total_price','')),('Location',location.username))))

            except Exception as e:
                import traceback
                log.debug(traceback.format_exc())
                log.info(' open order report   failed for %s and params are and error statement is %s' % (str(user.username),str(e)))
    return temp_data

def get_stock_cover_report_data(search_params, user, sub_user, serial_view=False):
    from miebach_admin.models import *
    from miebach_admin.views import *
    from common import get_decimal_limit
    lis = ['sku_code', 'sku_desc', 'sku_category','sku_type','sku_class','sku_code','sku_code','sku_code','sku_code','sku_code','sku_code',
            'sku_code','sku_code','sku_code','sub_category']

    try:
        temp_data = copy.deepcopy(AJAX_DATA)
        search_parameters = {}
        if 'sku_code' in search_params:
            search_parameters['wms_code'] = search_params['sku_code']
        if 'sku_category' in search_params:
            search_parameters['sku_category'] = search_params['sku_category']
        if 'sku_class' in search_params:
            search_parameters['sku_class'] = search_params['sku_class']
        if 'sku_type' in search_params :
            search_parameters['sku_type'] = search_params['sku_type']
        if 'sub_category' in search_params:
            search_parameters['sub_category'] = search_params['sub_category']
        if 'sku_brand' in search_params:
            search_parameters['sku_brand'] = search_params['sku_brand']
        if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            if 'manufacturer' in search_params:
                search_parameters['skuattributes__attribute_value__iexact'] = search_params['manufacturer']
            if 'searchable' in search_params:
                search_parameters['skuattributes__attribute_value__iexact'] = search_params['searchable']
            if 'bundle' in search_params:
                search_parameters['skuattributes__attribute_value__iexact'] = search_params['bundle']


        start_index = search_params.get('start', 0)
        stop_index = start_index + search_params.get('length', 0)

        sku_masters = SKUMaster.objects.filter(user=user.id ,**search_parameters)
        if search_params.get('order_term'):
            order_data = lis[search_params['order_index']]
            if search_params['order_term'] == 'desc':
                order_data = "-%s" % order_data
            sku_masters = sku_masters.order_by(order_data)

        temp_data['recordsTotal'] = len(sku_masters)
        temp_data['recordsFiltered'] = temp_data['recordsTotal']
        if stop_index:
            sku_masters = sku_masters[start_index:stop_index]
        attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
        for sku in sku_masters:
            manufacturer,searchable,bundle = '','',''
            attributes_obj = SKUAttributes.objects.filter(sku_id=sku.id, attribute_name__in= attributes_list)
            if attributes_obj.exists():
                for attribute in attributes_obj:
                    if attribute.attribute_name == 'Manufacturer':
                        manufacturer = attribute.attribute_value
                    if attribute.attribute_name == 'Searchable':
                        searchable = attribute.attribute_value
                    if attribute.attribute_name == 'Bundle':
                        bundle = attribute.attribute_value
            wms_code = sku.wms_code
            stock_quantity = StockDetail.objects.filter(sku__wms_code = wms_code,sku__user = user.id).exclude(location__zone__zone = 'DAMAGED_ZONE').aggregate(Sum('quantity'))['quantity__sum']
            purchase_order = PurchaseOrder.objects.exclude(status__in=['confirmed-putaway', 'location-assigned']). \
                filter(open_po__sku__user=sku.user, open_po__sku_id=sku.id, open_po__vendor_id__isnull=True). \
                values('open_po__sku_id').annotate(total_order=Sum('open_po__order_quantity'),
                                                   total_received=Sum('received_quantity'))

            qc_pending = POLocation.objects.filter(purchase_order__open_po__sku__user=sku.user, purchase_order__open_po__sku_id=sku.id,
                                                    qualitycheck__status='qc_pending', status=2).\
                                            only('quantity').aggregate(Sum('quantity'))['quantity__sum']
            putaway_pending = POLocation.objects.filter(purchase_order__open_po__sku__user=sku.user, purchase_order__open_po__sku_id=sku.id,
                                                   status=1).only('quantity').aggregate(Sum('quantity'))['quantity__sum']
            if not stock_quantity :
               stock_quantity = 0
            if not qc_pending:
                qc_pending = 0
            if not putaway_pending:
                putaway_pending = 0
            po_quantity = 0
            total_stock_available = 0
            if purchase_order.exists():
                purchase_order = purchase_order[0]
                diff_quantity = float(purchase_order['total_order']) - float(purchase_order['total_received'])
                if diff_quantity > 0:
                    po_quantity = diff_quantity

            total_stock_available = stock_quantity + qc_pending + putaway_pending

            total_with_po = total_stock_available + po_quantity
            picked_quantity_thirty_days = SKUDetailStats.objects.filter(sku_id=sku.id, transact_type='picklist',creation_date__lte=datetime.datetime.today(), creation_date__gt=datetime.datetime.today()-datetime.timedelta(days=30)).aggregate(Sum('quantity'))['quantity__sum']
            picked_quantity_seven_days = SKUDetailStats.objects.filter(sku_id=sku.id, transact_type='picklist',creation_date__lte=datetime.datetime.today(), creation_date__gt=datetime.datetime.today()-datetime.timedelta(days=7)).aggregate(Sum('quantity'))['quantity__sum']
            if not picked_quantity_thirty_days :
                picked_quantity_thirty_days = 0
                avg_thirty = 0
                avg_thirty_po = 0

            else:
                picked_quantity_thirty_days = picked_quantity_thirty_days/30
                avg_thirty = total_stock_available / picked_quantity_thirty_days
                avg_thirty_po = total_with_po / picked_quantity_thirty_days

            if not picked_quantity_seven_days :
                picked_quantity_seven_days = 0
                avg_seven = 0
                avg_seven_po = 0

            else:
                picked_quantity_seven_days = picked_quantity_seven_days/7
                avg_seven = total_stock_available / picked_quantity_seven_days
                avg_seven_po = total_with_po / picked_quantity_seven_days

            ord_dict = OrderedDict((('SKU',wms_code ),('SKU Description',sku.sku_desc),('SKU Category',sku.sku_category),
                                                   ('Sub Category',sku.sub_category),('SKU Brand',sku.sku_brand),
                                                   ('SKU Type',sku.sku_type),('SKU class',sku.sku_class),
                                                   ('Current Stock In Hand',total_stock_available),('PO Pending',po_quantity),
                                                   ('Total Stock including PO',total_with_po),('Avg Last 30days',"%.0f" % picked_quantity_thirty_days),
                                                   ('Avg Last 7 days',"%.0f" %picked_quantity_seven_days),('Stock Cover Days (30-day)',"%.0f"%avg_thirty),
                                                   ('Stock Cover Days including PO stock (30-day)',"%.0f"%avg_thirty_po),('Stock Cover Days (7-day)',"%.0f"%avg_seven),
                                                   ('Stock Cover Days including PO stock (7-day)',"%.0f"%avg_seven_po)))

            if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
                ord_dict['Manufacturer'] = manufacturer
                ord_dict['Searchable'] = searchable
                ord_dict['Bundle'] = bundle
            temp_data['aaData'].append(ord_dict)

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(' Stock Cover report    failed for %s and params are and error statement is %s' % (str(user.username),str(e)))


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
            hsn_code = open_po.sku.hsn_code
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
    cmp_data = ('sku_code', 'wms_code', 'sku_category', 'sku_type', 'sku_class', 'sub_category', 'sku_brand')
    for data in cmp_data:
        if data in search_params:
            search_parameters['%s__%s' % (data, 'icontains')] = search_params[data]
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['skuattributes__attribute_value__iexact'] = search_params['bundle']
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
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for data in sku_master:
        total_quantity = stock_dict.get(data.id, 0)
        # stock_data = StockDetail.objects.exclude(location__zone__zone='DEFAULT').filter(sku_id=data.id)
        # for stock in stock_data:
        #     total_quantity += int(stock.quantity)
        manufacturer,searchable,bundle = '','',''
        attributes_obj = SKUAttributes.objects.filter(sku_id=data.id, attribute_name__in= attributes_list)
        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value
        ord_dict = OrderedDict((('SKU Code', data.sku_code), ('WMS Code', data.wms_code),
                                                ('Product Description', data.sku_desc),
                                                ('SKU Category', data.sku_category),
                                                ('SKU Sub Category', data.sub_category),
                                                ('Sku Brand', data.sku_brand),
                                                ('Total Quantity', total_quantity)))
        if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            ord_dict['Manufacturer'] = manufacturer
            ord_dict['Searchable'] = searchable
            ord_dict['Bundle'] = bundle
        temp_data['aaData'].append(ord_dict)
    return temp_data


def get_stock_transfer_report_data(search_params, user, sub_user):
    from rest_api.views.common import get_sku_master, get_filtered_params ,get_local_date
    temp_data = copy.deepcopy(AJAX_DATA)
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    lis = ['creation_date','st_po__open_st__sku__user','st_po__open_st__sku__user','st_po__open_st__sku__user','sku__sku_code','sku__sku_desc',\
           'quantity', 'st_po__open_st__price','st_po__open_st__sku__user','st_po__open_st__cgst_tax','st_po__open_st__sgst_tax',
           'st_po__open_st__igst_tax','st_po__open_st__price','status','st_po__open_st__igst_tax','st_po__open_st__price','status']
    status_map = ['Pick List Generated','Pending','Accepted']
    order_term = search_params.get('order_term', 'asc')
    start_index = search_params.get('start', 0)
    col_num = search_params.get('order_index', 0)
    if search_params.get('length', 0):
        stop_index = start_index + search_params.get('length', 0)
    else:
        stop_index = None
    search_parameters = {}
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if 'from_date' in search_params:
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_parameters['creation_date__lt'] = search_params['to_date']
    if 'sku_code' in search_params:
        if search_params['sku_code']:
            search_parameters['sku__sku_code'] = search_params['sku_code']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['bundle']

    search_parameters['sku_id__in'] = sku_master_ids
    search_parameters['sku__user'] = user.id
    stock_transfer_data = StockTransfer.objects.filter(**search_parameters).\
                                            order_by(order_data).select_related('sku','st_po__open_st__sku')
    temp_data['recordsTotal'] = stock_transfer_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    time = str(datetime.datetime.now())
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for data in  (stock_transfer_data[start_index:stop_index]):
        date = get_local_date(user, data.creation_date)
        destination = User.objects.get(id = data.st_po.open_st.sku.user)
        status = status_map[data.status]
        destination = destination.username
        cgst = data.st_po.open_st.cgst_tax
        sgst = data.st_po.open_st.sgst_tax
        igst = data.st_po.open_st.igst_tax
        price = data.st_po.open_st.price
        quantity = data.quantity
        net_value = quantity * price
        total = (quantity * price) +cgst+sgst+igst

        manufacturer,searchable,bundle = '','',''
        attributes_obj = SKUAttributes.objects.filter(sku_id=data.sku.id, attribute_name__in= attributes_list)
        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value
        invoice_number = ''
        if data.stocktransfersummary_set.filter():
            invoice_number = data.stocktransfersummary_set.filter()[0].full_invoice_number

        ord_dict = OrderedDict((('Date',date),('SKU Code', data.sku.sku_code), ('SKU Description',data.sku.sku_desc),('Invoice Number',invoice_number),\
                                                ('Quantity',quantity ),('Status',status),('Net Value',net_value),\
                                                ('CGST',cgst),('SGST',sgst),('IGST',igst),('Price',price),('Total Value',total),\
                                                ('Source Location',user.username),('Destination',destination)))
        if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            ord_dict['Manufacturer'] = manufacturer
            ord_dict['Searchable'] = searchable
            ord_dict['Bundle'] = bundle
        temp_data['aaData'].append(ord_dict)
    return temp_data

def get_orderflow_data(search_params, user, sub_user):
    from rest_api.views.common import get_local_date
    temp_data = copy.deepcopy(AJAX_DATA)
    from common import get_misc_value
    isprava_permission = get_misc_value('order_exceed_stock', user.id)
    lis = ['interm_order_id','order_assigned_wh__username','customer_name', 'order__customer_name','status','remarks','sku__sku_desc',
          'sku__wms_code','alt_sku__wms_code','order__original_order_id','order__status','order__id','order__picklist__status',
           'project_name','sku__sku_category','sku__cost_price', 'order__creation_date', 'order__shipment_date', 'interm_order_id', 'interm_order_id','interm_order_id', 'interm_order_id']
    status_map = ['Pick List Generated','Pending','Accepted']
    order_term = search_params.get('order_term', 'asc')
    start_index = search_params.get('start', 0)
    col_num = search_params.get('order_index', 0)

    order_status_dict = {'1' :'Open','0' :'Picklist Confirmed','2':'Picklist Confirmed','3':'Cancelled'}
    central_order_status = {'1':'Accepted','0':'Rejected','2':'Pending'}
    if search_params.get('length', 0):
        stop_index = start_index + search_params.get('length', 0)
    else:
        stop_index = None
    search_parameters = {}
    order_fields_dict = {}
    order_data = lis[col_num]
    interm_order_id = ''
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if 'from_date' in search_params:
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_parameters['creation_date__lt'] = search_params['to_date']
    #for one one_assist
    if 'order_id' in search_params:
        orderfield_obj = OrderFields.objects.filter(order_type='intermediate_order', name='original_order_id',user = user.id,
                                             value = search_params['order_id'])
        if orderfield_obj.exists():
            interm_order_id = orderfield_obj[0].original_order_id

    if 'sku_code' in search_params:
        search_parameters['sku__wms_code'] = search_params['sku_code']
    if 'central_order_id' in search_params :
        search_parameters['interm_order_id'] = search_params['central_order_id']
    if 'project_name' in search_params:
        search_parameters['project_name'] = search_params['project_name']
    if interm_order_id :
        search_parameters['interm_order_id'] = interm_order_id

    search_parameters['user'] = user.id
    order_flow_data = IntermediateOrders.objects.filter(**search_parameters).\
                                            order_by(order_data).select_related('order','sku','alt_sku').values('interm_order_id','order_assigned_wh__username','customer_name','status','remarks','order__customer_name','customer_user__first_name',
                                                                                                                'sku__wms_code','alt_sku__wms_code','order__original_order_id','order__status','order__id','order__picklist__status', 'sku__sku_desc','project_name','sku__sku_category','sku__cost_price', 'order__creation_date', 'order__shipment_date')
    temp_data['recordsTotal'] = order_flow_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for data in  (order_flow_data[start_index:stop_index]):
        outbound_qc,inbound_qc,serial_number ,shipment_status  = '','','','open'
        po_status,po_cancel_reason,acknowledgement_status = '' ,'','No'
        sku_damaze_remarks ,central_order_remarks,order_status = '','',''
        order_date,expected_date = '', ''
        if data['order__creation_date']:
            order_date = get_local_date(user, data['order__creation_date'])
        if data['order__shipment_date']:
            expected_date = get_local_date(user, data['order__shipment_date'])
        order_fields_dict = dict(OrderFields.objects.filter(original_order_id =data['interm_order_id'],user = user.id).values_list('name','value'))
        if data['order__id'] :
           if isprava_permission == 'false':
               singned_invoice = MasterDocs.objects.filter(master_id =data['order__id'], master_type='OneAssistSignedCopies')
               if singned_invoice.exists():
                   acknowledgement_status = 'Yes'

               outbound_dispatch_imei = DispatchIMEIChecklist.objects.filter(order_id =data['order__id'],qc_type = 'sales_order')
               if outbound_dispatch_imei.exists():
                   serial_number = outbound_dispatch_imei[0].po_imei_num.imei_number
                   outbound_qc = ','.join(filter(None,outbound_dispatch_imei.values_list('remarks',flat = True)))
               shipment = ShipmentInfo.objects.filter(order_id = data['order__id'])
               if shipment.exists():
                   shipment_status = 'Dispatched'

               po_obj = OrderMapping.objects.filter(order_id = data['order__id'], mapping_type = 'PO')
               if po_obj.exists():
                  inbound_dispatch_imei = DispatchIMEIChecklist.objects.filter(order_id =po_obj[0].mapping_id,qc_type = 'purchase_order').exclude(remarks = '')
                  purchase_order_obj = PurchaseOrder.objects.filter(id =po_obj[0].mapping_id )
                  if purchase_order_obj.exists():
                      po_status = purchase_order_obj[0].status
                      po_cancel_reason  = purchase_order_obj[0].reason
                      sku_damaze_remarks = purchase_order_obj[0].remarks

                  if inbound_dispatch_imei.exists():
                      inbound_qc = ','.join(filter(None,inbound_dispatch_imei.values_list('remarks',flat = True)))
           if data['order__picklist__status'] :
               if data['order__picklist__status'] == 'open':
                   order_status = 'Picklist Generated'
               if data['order__picklist__status'] == 'picked':
                   order_status = 'Picklist Confirmed'
                   if isprava_permission == 'true':
                       order_status = 'Dispatched'
               if data['order__picklist__status'] == 'dispatched':
                   order_status = 'Picklist Confirmed'
                   if not po_status :
                       po_status = 'Open'

           else:
               order_status =  order_status_dict.get(data['order__status'],'')
        if data['status'] == '3':
           central_order_remarks = data['remarks']
           shipment_status,acknowledgement_status = '',''
        if isprava_permission == 'true':
           data['customer_name'] = data['order__customer_name']
           if not data['order_assigned_wh__username']:
              data['customer_name'] = data['customer_user__first_name']
        if order_fields_dict.get('original_order_id',''):
           original_order_id = order_fields_dict.get('original_order_id')
        else:
           original_order_id = data['order__original_order_id']

        temp_data['aaData'].append(OrderedDict((('Main SR Number',original_order_id),('Order Id', str(data['interm_order_id'])),('SKU Code', data['sku__wms_code']),
                                                ('SKU Description',data['sku__sku_desc']), ('Project Name', data['project_name']), ('Category', data['sku__sku_category']),('Customer Name',data['customer_name']),\
                                                ('Address',order_fields_dict.get('address','')),('Phone No',order_fields_dict.get('mobile_no','')),('Email Id',order_fields_dict.get('email_id','')),\
                                                ('Alt SKU',data['alt_sku__wms_code']),('Central order status',central_order_status.get(data['status'],'')),('Central Order cancellation remarks',central_order_remarks),
                                                ('Hub location',data['order_assigned_wh__username']),('Hub location order status',order_status), ('Price',data['sku__cost_price']),\
                                                ('Order cancellation remarks',''),('Outbound Qc params',outbound_qc),('Serial Number',serial_number),
                                                ('Shipment Status',shipment_status),('Acknowledgement status',acknowledgement_status),('Receive PO status',po_status),('Inbound Qc params',inbound_qc),
                                                ('PO cancellation remarks',po_cancel_reason), ('Order Date',order_date), ('Expected Date',expected_date),('SKU damage payment remarks',sku_damaze_remarks))))
    return temp_data

def get_current_stock_report_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from miebach_admin.views import *
    from rest_api.views.common import get_sku_master, get_filtered_params, get_local_date
    temp_data = copy.deepcopy(AJAX_DATA)
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    lis = ['seller__seller_id', 'seller__name', 'stock__sku__sku_code','stock__sku__sku_desc',
           'stock__sku__sku_category', 'stock__location__location',
           'stock__batch_detail__weight', 'stock__batch_detail__mrp', 'total', 'total', 'total',
           'seller__seller_id','seller__seller_id','seller__seller_id','seller__seller_id','seller__seller_id','seller__seller_id',
           'seller__seller_id','seller__seller_id','seller__seller_id','seller__seller_id','seller__seller_id',
           'seller__seller_id','seller__seller_id','seller__seller_id',
           'seller__seller_id','seller__seller_id','seller__seller_id']
    sort_cols = ['Seller ID', 'Seller Name', 'SKU Code', 'SKU Description', 'Location', 'Weight', 'MRP', 'Available Quantity',
                   'Reserved Quantity', 'Total Quantity']
    col_num = search_params.get('order_index', 0)
    order_term = search_params.get('order_term', 'asc')
    start_index = search_params.get('start', 0)
    if search_params.get('length', 0):
        stop_index = start_index + search_params.get('length', 0)
    else:
        stop_index = None
    search_parameters = {}
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if 'sku_code' in search_params:
        if search_params['sku_code']:
            search_parameters['stock__sku__sku_code'] = search_params['sku_code']
    if 'sku_brand' in search_params:
        if search_params['sku_brand']:
            search_parameters['stock__sku__sku_brand__icontains'] = search_params['sku_brand']
    if 'sku_category' in search_params:
        if search_params['sku_category']:
            search_parameters['stock__sku__sku_category__icontains'] = search_params['sku_category']
    if 'sub_category' in search_params:
        if search_params['sub_category']:
            search_parameters['stock__sku__sub_category__icontains'] = search_params['sub_category']
    if 'sku_class' in search_params:
        if search_params['sku_class']:
            search_parameters['stock__sku__sku_class__icontains'] = search_params['sku_class']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['stock__sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['stock__sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['stock__sku__skuattributes__attribute_value__iexact'] = search_params['bundle']
    search_parameters['stock__sku_id__in'] = sku_master_ids
    search_parameters['stock__quantity__gt'] = 0
    master_data = SellerStock.objects.filter(stock__sku__user=user.id, **search_parameters).\
                                        exclude(stock__receipt_number=0).\
                                            values('seller__seller_id', 'seller__name', 'stock__sku__wms_code',
                                                 'stock__location__location', 'stock__batch_detail__weight',
                                                 'stock__batch_detail__mrp',
                                                 'stock__sku__sku_desc', 'stock__sku__sku_category',).\
                                            annotate(total=Sum('quantity'),avg_buy_price = Sum(F('stock__batch_detail__buy_price')*F('quantity')),avg_tax_price = (Sum(F('stock__batch_detail__buy_price')*F('quantity')*(F('stock__batch_detail__tax_percent')/100)))).\
                                            order_by(order_data)
    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    if 'stock__quantity__gt' in search_parameters.keys():
        del search_parameters['stock__quantity__gt']

    all_pick_res = PicklistLocation.objects.filter(status=1, stock__sku__user=user.id, reserved__gt=0, **search_parameters)
    all_raw_res = RMLocation.objects.filter(status=1, stock__sku__user=user.id, reserved__gt=0, **search_parameters)
    time = get_local_date(user, datetime.datetime.now())
    for ind, sku_data in enumerate(master_data[start_index:stop_index]):
        sku_code = sku_data.get('stock__sku__wms_code','')
        if sku_code:
            sku_details_obj = SKUMaster.objects.filter(sku_code = sku_code , user = user.id)[0]
            brand = sku_details_obj.sku_brand
            sub_category = sku_details_obj.sub_category
            attributes_data = dict(sku_details_obj.skuattributes_set.filter().values_list('attribute_name', 'attribute_value'))
        seller_id = sku_data['seller__seller_id']
        reserved = 0
        res_filters = {'stock__sku__sku_code': sku_data['stock__sku__wms_code'],
                       'stock__location__location': sku_data['stock__location__location'],
                       'stock__sellerstock__seller__seller_id': seller_id}
        weight = ''
        mrp = 0
        avg_tax_price = 0
        avg_buy_price = 0
        tax = 0
        if sku_data['stock__batch_detail__mrp']:
            res_filters['stock__batch_detail__mrp'] = sku_data['stock__batch_detail__mrp']
            mrp = sku_data['stock__batch_detail__mrp']
        if sku_data['stock__batch_detail__weight']:
            res_filters['stock__batch_detail__weight'] = sku_data['stock__batch_detail__weight']
            weight = sku_data['stock__batch_detail__weight']
        if sku_data['avg_buy_price']:
            avg_buy_price = sku_data['avg_buy_price']
        if sku_data['avg_tax_price']:
            avg_tax_price = sku_data['avg_tax_price']

        picklist_reserved = all_pick_res.filter(**res_filters).aggregate(Sum('reserved'))['reserved__sum']
        raw_reserved = all_raw_res.filter(**res_filters).aggregate(Sum('reserved'))['reserved__sum']
        if picklist_reserved:
            reserved = picklist_reserved
        if raw_reserved:
            reserved += raw_reserved
        total_quantity = sku_data['total']
        quantity = total_quantity - reserved
        if quantity < 0:
            quantity = 0

        total_amt = avg_buy_price+avg_tax_price
        avg_cp_w_tax = float(total_amt)/total_quantity
        avg_cp_wo_tax = float(avg_buy_price)/total_quantity
        if total_amt and avg_buy_price:
            tax = (total_amt - avg_buy_price)/avg_buy_price*100
        temp_data['aaData'].append(OrderedDict((('Seller ID', sku_data['seller__seller_id']),
                                                ('Seller Name', sku_data['seller__name']),
                                                ('SKU Code', sku_data['stock__sku__wms_code']),
                                                ('SKU Description', sku_data['stock__sku__sku_desc']),
                                                ('Manufacturer',attributes_data.get('Manufacturer','')),
                                                ('Searchable',attributes_data.get('Searchable','')),
                                                ('Bundle',attributes_data.get('Bundle','')),
                                                ('Brand',brand),
                                                ('Category', sku_data['stock__sku__sku_category']),
                                                ('Sub Category',sub_category),
                                                ('Sub Category type',attributes_data.get('Sub Category type','')),
                                                ('Sheet',attributes_data.get('Sheet','')),
                                                ('Vendor',attributes_data.get('Vendor','')),
                                                ('Location', sku_data['stock__location__location']),
                                                ('Weight', weight), ('MRP', mrp),
                                                ('Available Quantity', quantity),
                                                ('Reserved Quantity', reserved), ('Total Quantity', total_quantity),
                                                ('Tax %',tax),('Avg CP with Tax',avg_cp_w_tax),
                                                ('Amount with Tax', '%.2f' % total_amt),
                                                ('Cost Price W/O Tax', '%.2f' % avg_cp_wo_tax),('Amount W/O tax', '%.2f' % avg_buy_price),
                                                ('Warehouse Name',user.username), ('Report Generation Time', time))))
    return temp_data


def get_inventory_value_report_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from miebach_admin.views import *
    from rest_api.views.common import get_sku_master, get_filtered_params, get_local_date
    temp_data = copy.deepcopy(AJAX_DATA)
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    lis = ['seller__seller_id', 'seller__name','stock__sku__sku_code','stock__sku__sku_desc','stock__sku__sku_category',
           'stock__batch_detail__weight', 'stock__batch_detail__mrp','stock__batch_detail__batch_no','stock__batch_detail__ean_number',
           'stock__batch_detail__manufactured_date', 'stock__batch_detail__expiry_date','total', 'total','total',
           'total', 'total', 'total','total', 'total', 'total', 'total','total', 'total', 'total']
    sort_cols = ['Seller ID', 'Seller Name', 'SKU Code', 'SKU Description', 'Location', 'Weight', 'MRP', 'Available Quantity',
                   'Reserved Quantity', 'Total Quantity']
    col_num = search_params.get('order_index', 0)
    order_term = search_params.get('order_term', 'asc')
    start_index = search_params.get('start', 0)
    if search_params.get('length', 0):
        stop_index = start_index + search_params.get('length', 0)
    else:
        stop_index = None
    search_parameters = {}
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if 'sku_code' in search_params:
        if search_params['sku_code']:
            search_parameters['stock__sku__sku_code'] = search_params['sku_code']
    if 'sku_brand' in search_params:
        if search_params['sku_brand']:
            search_parameters['stock__sku__sku_brand__icontains'] = search_params['sku_brand']
    if 'sku_category' in search_params:
        if search_params['sku_category']:
            search_parameters['stock__sku__sku_category__icontains'] = search_params['sku_category']
    if 'sub_category' in search_params:
        if search_params['sub_category']:
            search_parameters['stock__sku__sub_category__icontains'] = search_params['sub_category']
    if 'sku_class' in search_params:
        if search_params['sku_class']:
            search_parameters['stock__sku__sku_class__icontains'] = search_params['sku_class']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['stock__sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['stock__sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['stock__sku__skuattributes__attribute_value__iexact'] = search_params['bundle']

    search_parameters['stock__sku_id__in'] = sku_master_ids
    search_parameters['stock__quantity__gt'] = 0
    master_data = SellerStock.objects.filter(stock__sku__user=user.id, **search_parameters).\
                                        exclude(stock__receipt_number=0).\
                                            values('seller__seller_id', 'seller__name', 'stock__sku__wms_code','stock__sku__id',
                                                 'stock__batch_detail__weight', 'stock__batch_detail__batch_no',
                                                 'stock__batch_detail__ean_number',
                                                 'stock__batch_detail__manufactured_date',
                                                 'stock__batch_detail__expiry_date',
                                                 'stock__batch_detail__mrp',
                                                 'stock__batch_detail__buy_price',
                                                 'stock__sku__sku_desc',
                                                 'stock__sku__sku_category',
                                                 'stock__sku__sub_category','stock__sku__sku_brand').distinct().\
                                            annotate(total=Sum('quantity')).\
                                            order_by(order_data)
    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    if 'stock__quantity__gt' in search_parameters.keys():
        del search_parameters['stock__quantity__gt']
    time = get_local_date(user, datetime.datetime.now())
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for ind, sku_data in enumerate(master_data[start_index:stop_index]):
        quantity = sku_data['total']
        quantity_wod, average_cost_price, average_cost_price_wod, total_stock_value, total_stock_value_wod = 0, 0, 0, 0, 0
        sku_data1 = copy.deepcopy(sku_data)
        del sku_data1['total']
        seller_stocks = SellerStock.objects.filter(**sku_data1)
        for seller_stock in seller_stocks:
            price = seller_stock.stock.unit_price
            tax = 0
            if seller_stock.stock.batch_detail:
                price = seller_stock.stock.batch_detail.buy_price
                tax = seller_stock.stock.batch_detail.tax_percent
            amount = seller_stock.quantity * price
            total_amount = amount + ((amount/100) * tax)
            total_stock_value += float("%.2f" % total_amount)
            if seller_stock.stock.location.zone.zone not in ['DAMAGED_ZONE']:
                quantity_wod += seller_stock.quantity
                total_stock_value_wod += float("%.2f" % total_amount)

        if total_stock_value and quantity:
            average_cost_price = "%.2f" % (total_stock_value/quantity)
        if total_stock_value_wod and quantity_wod:
            average_cost_price_wod = "%.2f" % (total_stock_value_wod/quantity_wod)
        manufactured_date = ''
        expiry_date = ''
        weight = ''
        mrp = 0
        ean_number = ''
        if sku_data['stock__sku__id']:
            manufacturer,searchable,bundle = '','',''
            attributes_obj = SKUAttributes.objects.filter(sku_id=sku_data['stock__sku__id'], attribute_name__in= attributes_list)
            if attributes_obj.exists():
                for attribute in attributes_obj:
                    if attribute.attribute_name == 'Manufacturer':
                        manufacturer = attribute.attribute_value
                    if attribute.attribute_name == 'Searchable':
                        searchable = attribute.attribute_value
                    if attribute.attribute_name == 'Bundle':
                        bundle = attribute.attribute_value
        if sku_data['stock__batch_detail__manufactured_date']:
            manufactured_date = str(sku_data['stock__batch_detail__manufactured_date'])
        if sku_data['stock__batch_detail__expiry_date']:
            expiry_date = str(sku_data['stock__batch_detail__expiry_date'])
        if sku_data['stock__batch_detail__weight']:
            weight = sku_data['stock__batch_detail__weight']
        if sku_data['stock__batch_detail__mrp']:
            mrp = sku_data['stock__batch_detail__mrp']
        if sku_data['stock__batch_detail__ean_number']:
            ean_number = str(sku_data['stock__batch_detail__ean_number'])
        temp_data['aaData'].append(OrderedDict((('Seller ID', sku_data['seller__seller_id']),
                                                ('Seller Name', sku_data['seller__name']),
                                                ('SKU Code', sku_data['stock__sku__wms_code']),
                                                ('SKU Description', sku_data['stock__sku__sku_desc']),
                                                ('Category', sku_data['stock__sku__sku_category']),
                                                ('Sub Category', sku_data['stock__sku__sub_category']),
                                                ('Brand', sku_data['stock__sku__sku_brand']),
                                                ('Manufacturer', manufacturer),
                                                ('Searchable', searchable),
                                                ('Bundle', bundle),
                                                ('Weight', weight), ('MRP', mrp),
                                                ('Batch Number', sku_data['stock__batch_detail__batch_no']),
                                                ('Ean Number', ean_number), ('Manufactured Date', manufactured_date),
                                                ('Expiry Date',expiry_date), ('Quantity with Damaged', quantity),
                                                ('Value with Damaged(with Tax)', total_stock_value),
                                                ('Average Cost Price with Damaged', average_cost_price),
                                                ('Quantity without Damaged', quantity_wod),
                                                ('Value without Damaged(with Tax)', total_stock_value_wod),
                                                ('Average Cost Price without Damaged', average_cost_price_wod),
                                                ('Warehouse Name',user.username),
                                                ('Report Generation Time', time))))
    return temp_data


def get_bulk_to_retail_report_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from miebach_admin.views import *
    from rest_api.views.common import get_sku_master, get_filtered_params, get_local_date
    temp_data = copy.deepcopy(AJAX_DATA)
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    lis = ['transact_number', 'date_only', 'seller__seller_id', 'seller__name', 'source_sku_code__sku_code',
           'source_sku_code__sku_desc', 'source_sku_code__sku_category', 'source_location',
           'source_batch__weight', 'source_batch__mrp','source_quantity', 'destination_sku_code__sku_code',
           'destination_sku_code__sku_desc', 'destination_sku_code__sku_category', 'destination_location',
           'dest_batch__weight', 'dest_batch__mrp', 'destination_quantity', 'seller__seller_id', 'seller__seller_id']
    col_num = search_params.get('order_index', 0)
    order_term = search_params.get('order_term', 'asc')
    start_index = search_params.get('start', 0)
    if search_params.get('length', 0):
        stop_index = start_index + search_params.get('length', 0)
    else:
        stop_index = None
    search_parameters = {}
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_parameters['creation_date__lt'] = datetime.datetime.combine(search_params['to_date'] + \
                                                                           datetime.timedelta(1),
                                                             datetime.time())
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['source_sku_code__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['source_sku_code__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['source_sku_code__skuattributes__attribute_value__iexact'] = search_params['bundle']

    if 'source_sku_code' in search_params:
        if search_params['source_sku_code']:
            search_parameters['source_sku_code__sku_code'] = search_params['source_sku_code']
    if 'source_sku_category' in search_params:
        if search_params['source_sku_category']:
            search_parameters['source_sku_code__sku_category__icontains'] = search_params['source_sku_category']
    if 'source_sku_sub_category' in search_params:
        if search_params['source_sku_sub_category']:
            search_parameters['source_sku_code__sub_category__icontains'] = search_params['source_sku_sub_category']
    if 'source_sku_brand' in search_params:
        if search_params['source_sku_brand']:
            search_parameters['source_sku_code__sku_brand__icontains'] = search_params['source_sku_brand']
    if 'destination_sku_code' in search_params:
        if search_params['destination_sku_code']:
            search_parameters['destination_sku_code__sku_code'] = search_params['destination_sku_code']
    if 'destination_sku_category' in search_params:
        if search_params['destination_sku_category']:
            search_parameters['destination_sku_code__sku_category__icontains'] = search_params['destination_sku_category']
    if 'destination_sku_sub_category' in search_params:
        if search_params['destination_sku_sub_category']:
            search_parameters['destination_sku_code__sub_category__icontains'] = search_params['destination_sku_sub _category']
    if 'destination_sku_brand' in search_params:
        if search_params['destination_sku_brand']:
            search_parameters['destination_sku_code__sku_brand__icontains'] = search_params['destination_sku_brand']
    search_parameters['source_sku_code__id__in'] = sku_master_ids
    search_parameters['seller__isnull'] = False
    search_parameters['source_sku_code__user'] = user.id
    search_parameters['summary_type'] = 'substitute'
    master_data = SubstitutionSummary.objects.filter(**search_parameters).\
                                            values('seller__seller_id', 'seller__name', 'source_sku_code__sku_code','source_sku_code_id',
                                                   'source_sku_code__sku_desc', 'source_sku_code__sku_category',
                                                   'source_sku_code__sub_category', 'source_sku_code__sku_brand',
                                                   'source_location', 'source_batch__weight', 'source_batch__mrp',
                                                   'source_quantity', 'destination_sku_code__sku_code',
                                                   'destination_sku_code__sku_desc',
                                                   'destination_sku_code__sku_category',
                                                   'destination_sku_code__sub_category', 'destination_sku_code__sku_brand',
                                                   'destination_location', 'dest_batch__weight', 'dest_batch__mrp',
                                                   'destination_quantity', 'transact_number').\
                                            annotate(date_only=Cast('creation_date', DateField())).\
                                            order_by(order_data)
    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    time = get_local_date(user, datetime.datetime.now())
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for ind, sku_data in enumerate(master_data[start_index:stop_index]):
        source_weight, dest_weight = '', ''
        source_mrp, dest_mrp = 0, 0
        manufacturer,searchable,bundle = '','',''
        attributes_obj = SKUAttributes.objects.filter(sku_id=sku_data['source_sku_code_id'], attribute_name__in= attributes_list)
        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value
        if sku_data['source_batch__weight']:
            source_weight = sku_data['source_batch__weight']
        if sku_data['source_batch__mrp']:
            source_mrp = sku_data['source_batch__mrp']
        if sku_data['dest_batch__weight']:
            source_weight = sku_data['dest_batch__weight']
        if sku_data['dest_batch__mrp']:
            dest_mrp = sku_data['dest_batch__mrp']
        temp_data['aaData'].append(OrderedDict((('Transaction ID', sku_data['transact_number']),
                                                ('Date', str(sku_data['date_only'])),
                                                ('Seller ID', sku_data['seller__seller_id']),
                                                ('Seller Name', sku_data['seller__name']),
                                                ('Source SKU Code', sku_data['source_sku_code__sku_code']),
                                                ('Source SKU Description', sku_data['source_sku_code__sku_desc']),
                                                ('Source Sku Searchable', searchable),
                                                ('Source Sku Manufacturer', manufacturer),
                                                ('Source Sku Bundle', bundle),
                                                ('Source SKU Category', sku_data['source_sku_code__sku_category']),
                                                ('Source SKU Sub Category', sku_data['source_sku_code__sub_category']),
                                                ('Source SKU Brand', sku_data['source_sku_code__sku_brand']),
                                                ('Source Location', sku_data['source_location']),
                                                ('Source Weight', source_weight), ('Source MRP', source_mrp),
                                                ('Source Quantity', sku_data['source_quantity']),
                                                ('Destination SKU Code', sku_data['destination_sku_code__sku_code']),
                                                ('Destination SKU Description', sku_data['destination_sku_code__sku_desc']),
                                                ('Destination SKU Category', sku_data['destination_sku_code__sku_category']),
                                                ('Destination SKU Sub Category', sku_data['destination_sku_code__sub_category']),
                                                ('Destination SKU Brand', sku_data['destination_sku_code__sku_brand']),
                                                ('Destination Location', sku_data['destination_location']),
                                                ('Destination Weight', dest_weight), ('Destination MRP', dest_mrp),
                                                ('Destination Quantity', sku_data['destination_quantity']),
                                                ('Warehouse Name',user.username),
                                                ('Report Generation Time', time))))
    return temp_data


def get_margin_report_data(search_params, user, sub_user):
    from rest_api.views.common import get_sku_master, get_filtered_params ,get_local_date
    from django.db.models import Count
    temp_data = copy.deepcopy(AJAX_DATA)
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    lis = ['order__sellerorder__seller__name','order__sku__sku_code','order__sku__sku_code','stock__batch_detail__weight',
            'stock__batch_detail__mrp','vendor_name', 'order__sku__sku_brand', 'order__sku__sku_category', 'order__sku__sub_category', 'quantity','order__sku__sub_category','quantity','quantity']
    col_num = search_params.get('order_index', 0)
    order_term = search_params.get('order_term', 'asc')
    start_index = search_params.get('start', 0)
    grouping_data = OrderedDict()
    if search_params.get('length', 0):
        stop_index = start_index + search_params.get('length', 0)
    else:
        stop_index = None
    search_parameters = {}
    sort_data = lis[col_num]
    if order_term == 'desc':
        sort_data = '-%s' % sort_data
    if 'sku_code' in search_params:
        if search_params['sku_code']:
            search_parameters['order__sku__sku_code'] = search_params['sku_code']
    search_parameters['order__sku_id__in'] = sku_master_ids
    if 'from_date' in search_params:
        search_parameters['order__creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_parameters['order__creation_date__lt'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1), datetime.time())
    if 'sku_category' in search_params:
        search_parameters['order__sku__sku_category'] = search_params['sku_category']
    if 'sub_category' in search_params:
        search_parameters['order__sku__sub_category'] = search_params['sub_category']
    if 'sku_brand' in search_params:
        search_parameters['order__sku__sku_brand'] = search_params['sku_brand']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['order__sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['order__sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['order__sku__skuattributes__attribute_value__iexact'] = search_params['bundle']

    search_parameters['status__in'] = ['picked', 'batch_picked', 'dispatched']
    search_parameters['order__user'] = user.id
    order_data = Picklist.objects.filter(**search_parameters).exclude(order__sellerorder__seller__name =None).values('order__sku__sku_code','order__sku__sku_desc','stock__batch_detail__mrp',\
                                                                     'stock__batch_detail__weight','order__sellerorder__seller__name','order__customer_name','order__sku__id',
                                                                     'order__sku__sku_brand','order__sku__sku_category','order__sku__sub_category','order__marketplace').annotate(weighted_cost=Sum(F('picked_quantity') * F('stock__batch_detail__buy_price')),weighted_sell=Sum(F('picked_quantity') * F('order__unit_price')),
                                                                                                                                                                                  total_quantity=Sum('picked_quantity', distinct=True))
    for data in order_data :
        group_key = (data['order__sku__sku_code'],data['stock__batch_detail__mrp'], data['stock__batch_detail__weight'],
                     data['order__customer_name'],data['order__sellerorder__seller__name'],data['order__marketplace'])

        grouping_data.setdefault(group_key, {
                                             'wms_code':data['order__sku__sku_code'],
                                             'brand': data['order__sku__sku_brand'],
                                             'sku_desc':data['order__sku__sku_desc'],
                                             'weight':data['stock__batch_detail__weight'],
                                             'mrp': data['stock__batch_detail__mrp'],
                                             'category':data['order__sku__sku_category'],
                                             'sub_category':data['order__sku__sub_category'],
                                             'seller':data['order__sellerorder__seller__name'],
                                             'customer':data['order__customer_name'],
                                             'marketplace':data['order__marketplace'],
                                             'sku_id':data['order__sku__id'],
                                             'quantity':0,
                                             'average_cost_price':0,
                                             'average_selling_price':0,
                                               })
        grouping_data[group_key]['quantity'] +=data['total_quantity']
        if data['weighted_cost']:
            grouping_data[group_key]['average_cost_price'] +=data['weighted_cost']
        if data['weighted_sell'] :
            grouping_data[group_key]['average_selling_price'] += data['weighted_sell']

    order_data_loop = grouping_data.values()
    temp_data['recordsTotal'] =len(order_data_loop)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    time = str(datetime.datetime.now())
    weighted_avg_cost_value = 0
    weighted_avg_selling_price_value = 0
    quantity = 0
    for data in (order_data_loop[start_index:stop_index]):
        consolidated_margin = 0
        quantity = data['quantity']
        sku_attribute_dict = {}
        sku_attribute_dict = dict(SKUAttributes.objects.filter(sku__id=data['sku_id'],attribute_name__in=['Manufacturer', 'Sub Category Type','Sheet', 'Vendor','Searchable','Bundle']).values_list('attribute_name','attribute_value'))
        total_cost = 0
        total_sale = 0
        margin_amount = 0
        margin_percentage = 0
        if quantity :
            weighted_avg_cost_value = float(data['average_cost_price']/quantity)
            weighted_avg_selling_price_value = float(data['average_selling_price']/quantity)
            total_cost = float(data['average_cost_price'])*float(quantity)
            total_sale = float(data['average_selling_price'])*float(quantity)
            margin_amount = total_sale - total_cost
            if total_sale :
                margin_percentage = (margin_amount / float(total_sale))*100

        temp_data['aaData'].append(OrderedDict((
                                                 ('SKU Code', data['wms_code']),('SKU Desc',data['sku_desc']), ('Vendor Name',sku_attribute_dict.get('Vendor','')),('Seller',data['seller']),
                                                 ('Searchable',sku_attribute_dict.get('Searchable','')),('Bundle',sku_attribute_dict.get('Bundle','')),
                                                 ('Brand',data['brand']), ('Category',data['category']),('Manufacturer',sku_attribute_dict.get('Manufacturer','')),('Sheet',sku_attribute_dict.get('Sheet','')),('Sub Category Type',sku_attribute_dict.get('Sub Category Type','')),
                                                 ('Sub Category', data['sub_category']), ('QTY', quantity),('Weight',data['weight']),('MRP',data['mrp']),('Customer',data['customer']),('Marketplace',data['marketplace']),
                                                 ('Weighted Avg Cost', "%.2f" % weighted_avg_cost_value), ('Weighted Avg Selling Price', "%.2f" % weighted_avg_selling_price_value),('Total Cost',"%.2f" %total_cost),('Total Sale',"%.2f" %total_sale),
                                                 ('Margin Amount',"%.2f" % margin_amount),('Margin Percentage',"%.2f" % margin_percentage))))
    return temp_data



def get_basa_report_data(search_params, user, sub_user):
    from rest_api.views.common import get_sku_master, get_filtered_params ,get_local_date,get_all_sellable_zones, get_all_zones
    from django.db.models import Count
    temp_data = copy.deepcopy(AJAX_DATA)
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    lis = ['sku__sku_code','sku__sku_desc','batch_detail__weight','batch_detail__mrp','sku__sku_brand', 'sku__sku_category',
           'sku__sub_category', 'sku__sub_category', 'sku__sku_code', 'quantity', 'sku__sku_code', 'sku__sku_code', 'sku__sku_code',
           'sku__sku_code', 'sku__sku_code', 'sku__sku_code']
    col_num = search_params.get('order_index', 0)
    order_term = search_params.get('order_term', 'asc')
    start_index = search_params.get('start', 0)
    grouping_data = OrderedDict()
    if search_params.get('length', 0):
        stop_index = start_index + search_params.get('length', 0)
    else:
        stop_index = None
    search_parameters = {}
    search_parameters_sku = {}
    sort_data = lis[col_num]
    zones  = get_all_sellable_zones(user)
    locations = []
    bulk_zone_name = MILKBASKET_BULK_ZONE
    bulk_zones = get_all_zones(user, zones=[bulk_zone_name])
    zones = list(chain(zones, bulk_zones))
    locations = list(LocationMaster.objects.filter(zone__zone__in = zones,zone__user =user.id).values_list('location',flat=True))
    if order_term == 'desc':
        sort_data = '-%s' % sort_data
    if 'sku_code' in search_params:
        if search_params['sku_code']:
            search_parameters['sku__sku_code'] = search_params['sku_code']
            search_parameters_sku['sku_code'] = search_params['sku_code']
    if 'sku_category' in search_params:
        search_parameters['sku__sku_category'] = search_params['sku_category']
        search_parameters_sku['sku_category'] = search_params['sku_category']
    if 'sub_category' in search_params:
        search_parameters['sku__sub_category'] = search_params['sub_category']
        search_parameters_sku['sub_category'] = search_params['sub_category']
    if 'sku_brand' in search_params:
        search_parameters['sku__sku_brand'] = search_params['sku_brand']
        search_parameters_sku['sku_brand'] = search_params['sku_brand']
    if 'manufacturer' in search_params:
        search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        search_parameters_sku['skuattributes__attribute_value__iexact'] = search_params['manufacturer']
    if 'searchable' in search_params:
        search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        search_parameters_sku['skuattributes__attribute_value__iexact'] = search_params['searchable']
    if 'bundle' in search_params:
        search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['bundle']
        search_parameters_sku['skuattributes__attribute_value__iexact'] = search_params['bundle']


    search_parameters['sku_id__in'] = sku_master_ids
    search_params['location__location__in'] = locations
    search_parameters['quantity__gt'] = 0
    #if 'from_date' in search_params:
    #    search_parameters['creation_date__gt'] = search_params['from_date']
    #if 'to_date' in search_params:
    #    search_parameters['creation_date__lt'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1), datetime.time())
    stock_data = StockDetail.objects.filter(**search_parameters).values('sku__sku_code','sku__sku_desc','batch_detail__mrp',\
                                                                     'batch_detail__weight','sku__id',
                                                                     'sku__sku_brand','sku__sku_category','sku__sub_category').distinct().annotate(total_quantity=Sum('quantity'),average_cp = Sum(F('quantity')*F('batch_detail__buy_price'))).order_by(sort_data)

    quantity = 0
    mrp = 0
    avearage_cost_price = 0
    grn_quantity = 0
    grn_price = 0
    stock_data1 = stock_data[start_index:stop_index]
    if not stop_index:
        stock_sku_ids = list(stock_data1.values_list('sku_id', flat=True))
        grn_data = SellerPOSummary.objects.prefetch_related('purchase_order__open_po__sku').filter(batch_detail__isnull=False, purchase_order__open_po__sku_id__in=stock_sku_ids)
        sku_grn_price = OrderedDict(grn_data.values_list('purchase_order__open_po__sku__sku_code', 'batch_detail__buy_price').order_by('id'))
        sku_grn_quantity = OrderedDict(grn_data.values_list('purchase_order__open_po__sku__sku_code', 'quantity').order_by('id'))
    skumaster_data = SKUMaster.objects.filter(user=user.id,**search_parameters_sku).exclude(id__in=list(stock_data.values_list('sku_id', flat=True))).values('sku_code','sku_desc','sku_category','sku_brand','mrp','id','sub_category')
    chaining = list(chain(stock_data, skumaster_data))
    temp_data['recordsTotal'] = len(chaining)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    chaining = chaining[start_index:stop_index]
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for data in chaining:
        if data.get('sku__sku_code',''):
            sku_code = data['sku__sku_code']
            sku_id = data['sku__id']
            sku_desc = data['sku__sku_desc']
            sku_category = data['sku__sku_category']
            mrp = data['batch_detail__mrp']
            sku_brand = data['sku__sku_brand']
            sub_category = data['sku__sub_category']
            quantity = data['total_quantity']
            weight = data['batch_detail__weight']
        else:
            sku_code = data['sku_code']
            sku_id = data['id']
            sku_desc = data['sku_desc']
            sku_category = data['sku_category']
            mrp = data['mrp']
            sku_brand = data['sku_brand']
            sub_category = data['sub_category']
            quantity = 0

        if not stop_index:
            grn_price = sku_grn_price.get(sku_code, 0)
            grn_quantity = sku_grn_quantity.get(sku_code, 0)
        else:
            try:
                seller_po = SellerPOSummary.objects.filter(location__zone__user=user.id, purchase_order__open_po__sku__sku_code=sku_code).latest('id')
                grn_quantity = seller_po.quantity
                if seller_po.batch_detail:
                    grn_price = seller_po.batch_detail.buy_price
            except:
                grn_price = 0
        if quantity and data.get('average_cp',''):
            average_cost_price = data['average_cp']/quantity
        else:
            average_cost_price = 0
        sku_attribute_dict = dict(SKUAttributes.objects.filter(sku__id=sku_id,attribute_name__in=['Manufacturer', 'Sub Category Type','Sheet', 'Vendor','Weight', 'Searchable', 'Bundle']).values_list('attribute_name','attribute_value'))
        sheet = sku_attribute_dict.get('Sheet','')
        sub_category_type = sku_attribute_dict.get('Sub Category Type','')
        if not data.get('sku__sku_code',''):
           weight = sku_attribute_dict.get('Weight','')
        temp_data['aaData'].append(OrderedDict(( ('SKU Code', sku_code),('SKU Desc',sku_desc),
                                                 ('Manufacturer',sku_attribute_dict.get('Manufacturer','')),('Searchable',sku_attribute_dict.get('Searchable','')),('Bundle',sku_attribute_dict.get('Bundle','')),
                                                 ('Brand',sku_brand), ('Category',sku_category),('Sheet',sheet),('Sub Category Type',sub_category_type),
                                                 ('Sub Category', sub_category), ('Stock( Only BA and SA)', quantity),('Weight',weight),('MRP',mrp),('Avg CP',"%.2f" %average_cost_price),('Latest GRN Qty',grn_quantity),('Latest GRN CP', "%.2f" % grn_price))))
    return temp_data

def stock_rec_damaged_amount(stock_rec_obj):
    damaged_amount_dict = {}
    field_names = ['opening', 'purchase', 'rtv', 'customer_sales', 'internal_sales', 'stock_transfer',
                    'returns', 'adjustment', 'closing']
    for field_name in field_names:
        damaged_qty = getattr(stock_rec_obj, '%s_qty_damaged' % field_name)
        field_qty = getattr(stock_rec_obj, '%s_quantity' % field_name)
        field_amount = getattr(stock_rec_obj, '%s_amount' % field_name)
        damaged_amount_dict[field_name] = 0
        if damaged_qty and field_amount:
            damaged_amount_dict[field_name] = (field_amount/field_qty) * damaged_qty
    return damaged_amount_dict

def get_stock_reconciliation_report_data(search_params, user, sub_user):
    from rest_api.views.common import get_sku_master, get_filtered_params, get_local_date, get_utc_start_date
    temp_data = copy.deepcopy(AJAX_DATA)
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    lis = ['creation_date', 'sku__sku_code', 'sku__sku_desc', 'mrp', 'weight', 'sku__sku_code',
           'sku__sku_brand', 'sku__sku_category', 'sku__sub_category', 'sku__sku_code', 'sku__sku_code',
           'opening_quantity', 'opening_avg_rate', 'opening_amount', 'opening_qty_damaged', 'opening_qty_damaged',
           'purchase_quantity', 'purchase_avg_rate', 'purchase_amount', 'purchase_qty_damaged', 'purchase_qty_damaged',
           'rtv_quantity', 'rtv_avg_rate', 'rtv_amount', 'rtv_qty_damaged', 'rtv_qty_damaged',
           'customer_sales_quantity', 'customer_sales_avg_rate', 'customer_sales_amount', 'customer_sales_qty_damaged',
           'customer_sales_qty_damaged', 'internal_sales_quantity', 'internal_sales_avg_rate', 'internal_sales_amount',
           'internal_sales_qty_damaged', 'internal_sales_qty_damaged', 'stock_transfer_quantity', 'stock_transfer_avg_rate',
           'stock_transfer_amount', 'stock_transfer_qty_damaged', 'stock_transfer_qty_damaged',
           'returns_quantity', 'returns_avg_rate', 'returns_amount', 'returns_qty_damaged', 'returns_qty_damaged',
           'adjustment_quantity', 'adjustment_avg_rate', 'adjustment_amount', 'adjustment_qty_damaged', 'adjustment_qty_damaged',
           'closing_quantity', 'closing_avg_rate', 'closing_amount', 'closing_qty_damaged', 'closing_qty_damaged', 'id', 'id']
    col_num = search_params.get('order_index', 0)
    order_term = search_params.get('order_term', 'asc')
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    start_index = search_params.get('start', 0)
    if search_params.get('length', 0):
        stop_index = start_index + search_params.get('length', 0)
    else:
        stop_index = None
    search_parameters = {}
    if 'sku_code' in search_params:
        if search_params['sku_code']:
            search_parameters['sku__sku_code'] = search_params['sku_code']
    search_parameters['sku_id__in'] = sku_master_ids
    if 'sku_category' in search_params:
        if search_params['sku_category']:
            search_parameters['sku__sku_category'] = search_params['sku_category']
    if 'sub_category' in search_params:
        if search_params['sub_category']:
            search_parameters['sku__sub_category'] = search_params['sub_category']
    if 'sku_brand' in search_params:
        if search_params['sku_brand']:
            search_parameters['sku__sku_brand'] = search_params['sku_brand']
    #if 'from_date' in search_params:
    #    search_parameters['creation_date__gt'] = search_params['from_date']
    #if 'to_date' in search_params:
    #    search_parameters['creation_date__lt'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1), datetime.time())
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gte'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lte'] = search_params['to_date']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['bundle']

    search_parameters['sku__user'] = user.id
    stock_rec_objs = StockReconciliation.objects.filter(**search_parameters).order_by(order_data)
    temp_data['recordsTotal'] = stock_rec_objs.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    if stop_index:
        stock_rec_objs = stock_rec_objs[start_index:stop_index]
    for stock_rec_obj in stock_rec_objs:
        creation_date = stock_rec_obj.creation_date
        if creation_date.strftime('%H') in ['23']:
            creation_date = creation_date - datetime.timedelta(1)
        creation_date = get_local_date(user, creation_date, send_date=True).strftime('%d %b %Y')
        sku = stock_rec_obj.sku
        sku_attr_data = dict(sku.skuattributes_set.filter(attribute_name__in=['Manufacturer', 'Sub Category Type',
                                                                              'Sheet', 'Vendor', 'Searchable', 'Bundle']).\
                                                values_list('attribute_name', 'attribute_value'))
        damaged_amount_dict = stock_rec_damaged_amount(stock_rec_obj)
        temp_data['aaData'].append(OrderedDict(( ('Created Date', creation_date),
                                                 ('SKU Code', sku.sku_code), ('SKU Desc', sku.sku_desc),
                                                 ('MRP', stock_rec_obj.mrp), ('Weight', stock_rec_obj.weight),
                                                 ('Vendor Name', sku_attr_data.get('Vendor', '')),
                                                 ('Brand', sku.sku_brand),
                                                 ('Category', sku.sku_category),
                                                 ('Sub Category', sku.sub_category),
                                                 ('Sub Category Type', sku_attr_data.get('Sub Category Type', '')),
                                                 ('Manufacturer', sku_attr_data.get('Manufacturer', '')),
                                                 ('Searchable', sku_attr_data.get('Searchable', '')),
                                                 ('Bundle', sku_attr_data.get('Bundle', '')),
                                                 ('Sheet', sku_attr_data.get('Sheet', '')),
                                                 ('Opening Qty',  stock_rec_obj.opening_quantity),
                                                 ('Opening Avg Rate', "%.2f" % stock_rec_obj.opening_avg_rate),
                                                 ('Opening Amount After Tax', "%.2f" % stock_rec_obj.opening_amount),
                                                 ('Opening Qty Damaged', stock_rec_obj.opening_qty_damaged),
                                                 ('Opening Damaged Amount After Tax', damaged_amount_dict['opening']),
                                                 ('Purchases Qty',  stock_rec_obj.purchase_quantity),
                                                 ('Purchases Avg Rate', "%.2f" % stock_rec_obj.purchase_avg_rate),
                                                 ('Purchases Amount After Tax', "%.2f" % stock_rec_obj.purchase_amount),
                                                 ('Purchase Qty Damaged', stock_rec_obj.purchase_qty_damaged),
                                                 ('Purchase Damaged Amount After Tax', damaged_amount_dict['purchase']),
                                                 ('RTV Qty', stock_rec_obj.rtv_quantity),
                                                 ('RTV Avg Rate', "%.2f" % stock_rec_obj.rtv_avg_rate),
                                                 ('RTV Amount After Tax', "%.2f" % stock_rec_obj.rtv_amount),
                                                 ('RTV Qty Damaged', stock_rec_obj.rtv_qty_damaged),
                                                 ('RTV Damaged Amount After Tax', damaged_amount_dict['rtv']),
                                                 ('Customer Sales Qty', stock_rec_obj.customer_sales_quantity),
                                                 ('Customer Sales Avg Rate', "%.2f" % stock_rec_obj.customer_sales_avg_rate),
                                                 ('Customer Sales Amount After Tax',
                                                  "%.2f" % stock_rec_obj.customer_sales_amount),
                                                 ('Customer Sales Qty Damaged', stock_rec_obj.customer_sales_qty_damaged),
                                                 ('Customer Sales Damaged Amount After Tax', damaged_amount_dict['customer_sales']),
                                                 ('Internal Sales Qty',  stock_rec_obj.internal_sales_quantity),
                                                 ('Internal Sales Avg Rate', "%.2f" % stock_rec_obj.internal_sales_avg_rate),
                                                 ('Internal Sales Amount After Tax', "%.2f" % stock_rec_obj.internal_sales_amount),
                                                 ('Internal Sales Qty Damaged', stock_rec_obj.internal_sales_qty_damaged),
                                                 ('Internal Sales Damaged Amount After Tax', damaged_amount_dict['internal_sales']),
                                                 ('Stock Transfer Qty', stock_rec_obj.stock_transfer_quantity),
                                                 ('Stock Transfer Avg Rate',
                                                  "%.2f" % stock_rec_obj.stock_transfer_avg_rate),
                                                 ('Stock Transfer Amount After Tax',
                                                  "%.2f" % stock_rec_obj.stock_transfer_amount),
                                                 ('Stock Transfer Qty Damaged', stock_rec_obj.stock_transfer_qty_damaged),
                                                 ('Stock Transfer Damaged Amount After Tax', damaged_amount_dict['stock_transfer']),
                                                 ('Returns Qty', stock_rec_obj.returns_quantity),
                                                 ('Returns Avg Rate',
                                                  "%.2f" % stock_rec_obj.returns_avg_rate),
                                                 ('Returns Amount After Tax',
                                                  "%.2f" % stock_rec_obj.returns_amount),
                                                 ('Returns Qty Damaged', stock_rec_obj.returns_qty_damaged),
                                                 ('Returns Damaged Amount After Tax', damaged_amount_dict['returns']),
                                                 ('Adjustment Qty', stock_rec_obj.adjustment_quantity),
                                                 ('Adjustment Avg Rate',
                                                  "%.2f" % stock_rec_obj.adjustment_avg_rate),
                                                 ('Adjustment Amount After Tax',
                                                  "%.2f" % stock_rec_obj.adjustment_amount),
                                                 ('Adjustment Qty Damaged', stock_rec_obj.adjustment_qty_damaged),
                                                 ('Adjustment Damaged Amount After Tax', damaged_amount_dict['adjustment']),
                                                 ('Closing Qty',  stock_rec_obj.closing_quantity),
                                                 ('Closing Avg Rate', "%.2f" % stock_rec_obj.closing_avg_rate),
                                                 ('Closing Amount After Tax', "%.2f" % stock_rec_obj.closing_amount),
                                                 ('Closing Qty Damaged', stock_rec_obj.closing_qty_damaged),
                         ('Closing Damaged Amount After Tax', damaged_amount_dict['closing']),
                                                 ('Warehouse Name', user.username),
                                                 ('Report Generation Time', str(datetime.datetime.now()))
                                              )))
    return temp_data



    # create_data_dict = {}
    # stock_reconciliation = StockReconciliation.objects.filter(**search_parameters)
    # temp_data['recordsTotal'] = len(stock_reconciliation)
    # temp_data['recordsFiltered'] = temp_data['recordsTotal']
    # empty_sub_dict = {}
    # empty_sub_dict['quantity'] = 0
    # empty_sub_dict['avg_rate'] = 0
    # empty_sub_dict['amount_before_tax'] = 0
    # empty_sub_dict['tax_rate'] = 0
    # empty_sub_dict['cess_rate'] = 0
    # empty_sub_dict['amount_after_tax'] = 0
    # time = get_local_date(user, datetime.datetime.now())
    # dict_formation = {}
    # dict_formation = {'po': empty_sub_dict, 'picklist': empty_sub_dict, 'opening_stock': empty_sub_dict, 'closing_stock': empty_sub_dict}
    # for obj in stock_reconciliation:
    #     report_type = obj.report_type
    #     if not str(obj.sku.sku_code) + '<<>>' + str(obj.created_date) in create_data_dict.keys():
    #         dict_formation = {}
    #         dict_formation = {'po': empty_sub_dict, 'picklist': empty_sub_dict, 'opening_stock': empty_sub_dict, 'closing_stock': empty_sub_dict}
    #         sub_dict = {}
    #         sub_dict['quantity'] = obj.quantity
    #         sub_dict['avg_rate'] = obj.avg_rate
    #         sub_dict['amount_before_tax'] = obj.amount_before_tax
    #         sub_dict['tax_rate'] = obj.tax_rate
    #         sub_dict['cess_rate'] = obj.cess_rate
    #         sub_dict['amount_after_tax'] = obj.amount_after_tax
    #         sku_det_dict = {}
    #         sku_det_dict['sku'] = str(obj.sku.sku_code)
    #         sku_det_dict['vendor_name'] = ''
    #         sku_det_dict['brand'] = str(obj.sku.sku_brand)
    #         sku_det_dict['category'] = str(obj.sku.sku_category)
    #         sku_det_dict['sub_category'] = str(obj.sku.sub_category)
    #         dict_formation.update({'sku_details':sku_det_dict})
    #         dict_formation[report_type] = sub_dict
    #         create_data_dict[str(obj.sku.sku_code) + '<<>>' + str(obj.created_date)] = dict_formation
    #     else:
    #         sub_dict = {}
    #         sub_dict['quantity'] = obj.quantity
    #         sub_dict['avg_rate'] = obj.avg_rate
    #         sub_dict['amount_before_tax'] = obj.amount_before_tax
    #         sub_dict['tax_rate'] = obj.tax_rate
    #         sub_dict['cess_rate'] = obj.cess_rate
    #         sub_dict['amount_after_tax'] = obj.amount_after_tax
    #         sku_det_dict = {}
    #         sku_det_dict['sku'] = str(obj.sku.sku_code)
    #         sku_det_dict['vendor_name'] = ''
    #         sku_det_dict['brand'] = str(obj.sku.sku_brand)
    #         sku_det_dict['category'] = str(obj.sku.sku_category)
    #         sku_det_dict['sub_category'] = str(obj.sku.sub_category)
    #         create_data_dict[str(obj.sku.sku_code) + '<<>>' + str(obj.created_date)].update({'sku_details':sku_det_dict})
    #         create_data_dict[str(obj.sku.sku_code) + '<<>>' + str(obj.created_date)].update({report_type:sub_dict})
    # for key, value in create_data_dict.iteritems():
    #     wms_code, creation_date = key.split('<<>>')
    #     temp_data['aaData'].append(OrderedDict((
    #                                              ('SKU', wms_code), ('Vendor Name', ''),
    #                                              ('Brand', value['sku_details']['brand']), ('Category', value['sku_details']['category']),
    #                                              ('Sub Category', value['sku_details']['sub_category'] ), ('Opening Qty',  value['opening_stock']['quantity']),
    #                                              ('Opening Avg Rate', "%.2f" % value['opening_stock']['avg_rate']), ('Opening Amount Before Tax', "%.2f" % value['opening_stock']['avg_rate']), ('Opening Tax Rate', "%.2f" % value['opening_stock']['tax_rate']),
    #                                              ('Opening Cess Rate', "%.2f" % value['opening_stock']['cess_rate']), ('Opening Amount After Tax', "%.2f" % value['opening_stock']['amount_after_tax']),
    #                                              ('Purchases Qty',  value['po']['quantity']), ('Purchases Avg Rate', "%.2f" % value['po']['avg_rate']), ('Purchases Amount Before Tax', "%.2f" % value['po']['amount_before_tax']), ('Purchases Tax Rate', "%.2f" % value['po']['tax_rate']),
    #                                              ('Purchases Cess Rate', "%.2f" % value['po']['cess_rate']), ('Purchases Amount After Tax', "%.2f" % value['po']['amount_after_tax']),
    #                                              ('Sales Qty',  value['picklist']['quantity']), ('Sales Avg Rate', "%.2f" % value['picklist']['avg_rate']), ('Sales Amount Before Tax', "%.2f" % value['picklist']['amount_before_tax']), ('Sales Tax Rate', "%.2f" % value['picklist']['tax_rate']),
    #                                              ('Sales Cess Rate', "%.2f" % value['picklist']['cess_rate']), ('Sales Amount After Tax', "%.2f" % value['picklist']['amount_after_tax']),
    #                                              ('Closing Qty',  value['closing_stock']['quantity']), ('Closing Avg Rate', "%.2f" % value['closing_stock']['avg_rate']), ('Closing Amount Before Tax', "%.2f" % value['closing_stock']['avg_rate']),
    #                                              ('Closing Tax Rate', "%.2f" % value['closing_stock']['tax_rate']),
    #                                              ('Closing Cess Rate', "%.2f" % value['closing_stock']['cess_rate']), ('Closing Amount After Tax', "%.2f" % value['closing_stock']['amount_after_tax']),
    #                                              ('Created Date', creation_date), ('Warehouse Name', user.username), ('Report Generation Time', time)
    #                                           ))
    #                               )
    # lis = ['Created Date', 'SKU', 'Vendor Name', 'Brand', 'Category', 'Sub Category', 'Opening Qty', 'Opening Avg Rate', 'Opening Amount Before Tax', 'Opening Tax Rate', 'Opening Cess Rate', 'Opening Amount After Tax', 'Purchases Qty', 'Purchases Avg Rate', 'Purchases Amount Before Tax', 'Purchases Tax Rate', 'Purchases Cess Rate', 'Purchases Amount After Tax', 'Sales Qty', 'Sales Avg Rate', 'Sales Amount Before Tax', 'Sales Tax Rate', 'Sales Cess Rate', 'Sales Amount After Tax', 'Closing Qty', 'Closing Avg Rate', 'Closing Amount Before Tax', 'Closing Tax Rate', 'Closing Cess Rate', 'Closing Amount After Tax', 'Warehouse Name', 'Report Generation Time']
    # sort_col = lis[col_num]
    # if order_term == 'asc':
    #     temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col))
    # else:
    #     temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col), reverse=True)
    # if stop_index:
    #     temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    # return temp_data


def get_move_inventory_report_data(search_params, user, sub_user):
    from rest_api.views.common import get_sku_master, get_local_date, get_utc_start_date
    temp_data = copy.deepcopy(AJAX_DATA)
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    lis = ['sku__sku_code','sku__sku_desc','source_location__location','dest_location__location','quantity',
            'sku__sku_category','sku__sub_category','sku__sku_brand','sku__sku_category','sku__sub_category','sku__sku_brand',
           'creation_date', 'sku__sku_code', 'batch_detail__weight','batch_detail__mrp', 'seller__name']
    col_num = search_params.get('order_index', 0)
    order_term = search_params.get('order_term', 'asc')
    start_index = search_params.get('start', 0)
    if search_params.get('length', 0):
        stop_index = start_index + search_params.get('length', 0)
    else:
        stop_index = None
    search_parameters = {}
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_params['from_date'] = get_utc_start_date(search_params['from_date'])
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_parameters['creation_date__lt'] = get_utc_start_date(datetime.datetime.combine(search_params['to_date'] + \
                                                                           datetime.timedelta(1),
                                                             datetime.time()))
    if 'sku_code' in search_params:
        search_parameters['sku__wms_code'] = search_params['sku_code']
    if 'sku_category' in search_params:
        search_parameters['sku__sku_category'] = search_params['sku_category']
    if 'sub_category' in search_params:
        search_parameters['sku__sub_category'] = search_params['sub_category']
    if 'sku_brand' in search_params:
        search_parameters['sku__sku_brand'] = search_params['sku_brand']
    if 'source_location' in search_params :
        search_parameters['source_location__location'] = search_params['source_location']
    if 'destination_location' in search_params :
        search_parameters['dest_location__location'] = search_params['destination_location']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['bundle']


    search_parameters['sku__id__in'] = sku_master_ids
    master_data = MoveInventory.objects.filter(**search_parameters).order_by(order_data)
    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for ind, sku_data in enumerate(master_data[start_index:stop_index]):
        weight = ''
        mrp = 0
        manufacturer,searchable,bundle = '','',''
        attributes_obj = SKUAttributes.objects.filter(sku_id=sku_data.sku.id, attribute_name__in= attributes_list)
        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value
        date = get_local_date(user, sku_data.creation_date)
        if sku_data.batch_detail:
            mrp = sku_data.batch_detail.mrp
            weight = sku_data.batch_detail.weight
        seller_name = ''
        if sku_data.seller:
            seller_name = sku_data.seller.name
        version_obj = Version.objects.get_for_object(sku_data)
        updated_user_name = ''
        if version_obj.exists():
            updated_user_name = version_obj.order_by('-revision__date_created')[0].revision.user.username
        temp_data['aaData'].append(OrderedDict((('SKU Code', sku_data.sku.wms_code),
                                                ('SKU Description', sku_data.sku.sku_desc),
                                                ('SKU Category', sku_data.sku.sku_category),
                                                ('Sub Category', sku_data.sku.sub_category),
                                                ('SKU Brand', sku_data.sku.sku_brand),
                                                ('Manufacturer', manufacturer),
                                                ('Searchable', searchable),
                                                ('Bundle', bundle),
                                                ('Reason', sku_data.reason),
                                                ('Source Location',sku_data.source_location.location),
                                                ('Destination Location',sku_data.dest_location.location),
                                                ('Quantity',sku_data.quantity),('Weight',weight),('MRP',mrp),
                                                ('Seller', seller_name),
                                                ('Transaction Date',date),
                                                ('Updated User', updated_user_name))))
    return temp_data


def get_bulk_stock_update_data(search_params, user, sub_user):
  from rest_api.views.common import get_sku_master, get_local_date, get_utc_start_date
  temp_data = copy.deepcopy(AJAX_DATA)
  lis = ['source_sku_code__sku_code', 'source_sku_code__sku_code', 'source_sku_code__sku_code', 'source_sku_code__sku_code', 'source_location', 'destination_location', 'source_quantity', 'creation_date']
  col_num = search_params.get('order_index',7)
  order_term = search_params.get('order_term', 'asc')
  start_index = search_params.get('start', 0)
  if search_params.get('length', 0):
      stop_index = start_index + search_params.get('length', 0)
  else:
      stop_index = None
  search_parameters = {}
  order_data = lis[col_num]
  if order_term == 'desc':
      order_data = '-%s' % order_data
  if 'from_date' in search_params:
      search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
      search_params['from_date'] = get_utc_start_date(search_params['from_date'])
      search_parameters['creation_date__gte'] = search_params['from_date']
  if 'to_date' in search_params:
      search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                           datetime.time())
      search_params['to_date'] = get_utc_start_date(search_params['to_date'])
      search_parameters['creation_date__lte'] = search_params['to_date']
  if 'sku_code' in search_params:
      search_parameters['source_sku_code__sku_code'] = search_params['sku_code']
  if 'source_location' in search_params :
      search_parameters['source_location'] = search_params['source_location']
  if 'destination_location' in search_params :
      search_parameters['destination_location'] = search_params['destination_location']
  search_parameters['summary_type'] = 'bulk_stock_update'
  search_parameters['source_sku_code__user'] = user.id
  master_data = SubstitutionSummary.objects.filter(**search_parameters).order_by(order_data)
  temp_data['recordsTotal'] = master_data.count()
  temp_data['recordsFiltered'] = temp_data['recordsTotal']
  for data in master_data[start_index:stop_index]:
    mrp, weight = '', ''
    date = get_local_date(user, data.creation_date)
    if data.dest_batch:
      mrp = data.dest_batch.mrp
      weight = data.dest_batch.weight
    temp_data['aaData'].append(OrderedDict((('SKU Code', data.source_sku_code.sku_code),
                                            ('SKU Description', data.source_sku_code.sku_desc),
                                            ('MRP', mrp),
                                            ('Weight', weight),
                                            ('Source Location',data.source_location),
                                            ('Destination Location',data.destination_location),
                                            ('Quantity',data.source_quantity),
                                            ('Transaction Date', date))))
  return temp_data
