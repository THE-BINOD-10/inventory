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
#from inbound import *

AJAX_DATA = {
  "draw": 0,
  "recordsTotal": 0,
  "recordsFiltered": 0,
  "aaData": [
  ]
}

NOW = datetime.datetime.now()

SKU_GROUP_FIELDS = {'group': '', 'user': ''}

ADJUST_INVENTORY_EXCEL_HEADERS = ['WMS Code', 'Location', 'Physical Quantity', 'Reason']

PERMISSION_KEYS =['add_qualitycheck', 'add_skustock', 'add_shipmentinfo', 'add_openpo', 'add_orderreturns', 'add_openpo', 'add_purchaseorder',
                  'add_joborder', 'add_materialpicklist', 'add_polocation', 'add_stockdetail', 'add_cyclecount', 'add_inventoryadjustment',
                  'add_orderdetail', 'add_picklist']
LABEL_KEYS = ["MASTERS_LABEL", "INBOUND_LABEL", "PRODUCTION_LABEL", "STOCK_LABEL", "OUTBOUND_LABEL", "SHIPMENT_LABEL", "OTHERS_LABEL",
                "PAYMENT_LABEL"]

SKU_DATA = {'user': '', 'sku_code': '', 'wms_code': '',
            'sku_desc': '', 'sku_group': '', 'sku_type': '', 'mix_sku': '',
            'sku_category': '', 'sku_class': '', 'threshold_quantity': 0, 'color': '', 'mrp': 0,
            'status': 1, 'online_percentage': 0, 'qc_check': 0, 'sku_brand': '', 'sku_size': '', 'style_name': '', 'price': 0}

STOCK_TRANSFER_FIELDS = {'order_id': '', 'invoice_amount': 0, 'quantity': 0, 'shipment_date': datetime.datetime.now(), 'st_po_id': '', 'sku_id': '', 'status': 1}
OPEN_ST_FIELDS = {'warehouse_id': '', 'order_quantity': 0, 'price': 0, 'sku_id': '', 'status': 1, 'creation_date': datetime.datetime.now()}

VENDOR_DATA = {'vendor_id': '', 'name': '', 'address': '', 'phone_number': '', 'email_id': '', 'status': 1, 'creation_date': datetime.datetime.now()}

SKU_STOCK_DATA = {'sku_id': '', 'total_quantity': 0,
            'online_quantity': 0, 'offline_quantity': 0}

SUPPLIER_DATA = {'name': '', 'address': '',
            'phone_number': '', 'email_id': '',
            'status': 1}

SIZE_DATA = {'size_name':'', 'size_value': '', 'creation_date': datetime.datetime.now()}

PRICING_DATA = {'sku': '', 'price_type': '', 'price': 0, 'discount': 0, 'creation_date': datetime.datetime.now()}

ISSUE_DATA = {'issue_title': '', 'name': '', 'email_id': '',
            'priority': '', 'status': 'Active',
            'issue_description': '', 'creation_date': datetime.datetime.now()}

SUPPLIER_SKU_DATA = {'supplier_id': '', 'supplier_type': '',
                     'sku': '','supplier_code':'', 'preference': '','moq': '', 'price': ''}

UPLOAD_ORDER_DATA = {'order_id': '', 'title': '','user': '',
             'sku_id': '', 'status': 1, 'shipment_date': datetime.datetime.now()}

UPLOAD_SALES_ORDER_DATA = {'quantity': 0, 'damaged_quantity': 0, 'return_id': '', 'order_id': '', 'sku_id': '', 'return_date': '',
                            'status': 1}

LOCATION_GROUP_FIELDS = {'group': '', 'location_id': ''}

LOC_DATA = {'zone_id': '', 'location': '',
            'max_capacity': 0, 'fill_sequence': 0, 'pick_sequence': 0,
            'filled_capacity': 0, 'status': 1}

ZONE_DATA = {'user': '', 'zone': ''}

ORDER_DATA = {'order_id': '', 'sku_id': '', 'title': '',
              'quantity': '', 'status': 1}

ORDER_SUMMARY_REPORT_STATUS = ['Open', 'Picklist generated', 'Partial Picklist generated', 'Picked', 'Partially picked']

RETURN_DATA = {'order_id': '', 'return_id': '', 'return_date': '', 'quantity': '', 'status': 1, 'return_type': '', 'damaged_quantity': 0}


PALLET_FIELDS = {'pallet_code': '', 'quantity': 0, 'status': 1}

CONFIRM_SALES_RETURN = {'order_id':'','sku_id':''}

CANCEL_ORDER_HEADERS = OrderedDict([('','id'),('Order ID','order_id'),('SKU Code','sku__sku_code'),('Customer ID','customer_id')])

PO_SUGGESTIONS_DATA = {'supplier_id': '', 'sku_id':'', 'order_quantity': '', 'order_type': 'SR', 'price': 0, 'status': 1}

PO_DATA = {'open_po_id': '', 'status': '', 'received_quantity': 0}

ORDER_SHIPMENT_DATA = {'shipment_number': '', 'shipment_date': '', 'truck_number': '', 'shipment_reference': '', 'status': 1}

SKU_FIELDS = ( (('WMS SKU Code *', 'wms_code',60), ('Product Description *', 'sku_desc',256)),
               (('SKU Type', 'sku_type',60), ('Put Zone *', 'zone_id',60)),
               (('SKU Class', 'sku_class',60), ('Threshold Quantity *', 'threshold_quantity')),
               (('SKU Category', 'sku_category',60), ('Status', 'status',11))   )

QUALITY_CHECK_FIELDS = {'purchase_order_id': '', 'accepted_quantity': 0,'rejected_quantity': 0, 'putaway_quantity': 0, 'status': 'qc_pending', 'reason': ''}

ORDER_PACKAGING_FIELDS = {'order_shipment_id':'', 'package_reference': '', 'status': 1}

SHIPMENT_INFO_FIELDS = {'order_shipment_id':'', 'order_id': '', 'shipping_quantity': '', 'status': 1,'order_packaging_id': ''}

ADD_SKU_FIELDS = ( (('WMS SKU Code *', 'wms_code',60), ('Product Description *', 'sku_desc',256)),
               (('SKU Type', 'sku_type',60), ('Put Zone *', 'zone_id',60)),
               (('SKU Class', 'sku_class',60), ('Threshold Quantity', 'threshold_quantity',5)),
               (('SKU Category', 'sku_category',60), ('Status', 'status',11)), )


RAISE_ISSUE_FIELDS = ( ('Issue Title', 'issue_title'), ('User Name', 'name'), ('Email ID', 'email_id'),
               ('Priority', 'priority'),
               ('Issue Description', 'issue_description'), )

UPDATE_ISSUE_FIELDS = ( (('Issue Title', 'issue_title',60), ('Name', 'name',256)),
                    (('Email ID', 'email_id',64), ('Priority', 'priority',32)),
                    (('Issue Description', 'issue_description',256), ('Status', 'status',11)),
                      (('Resolved Description', 'resolved_description'),),   )


RESOLVED_ISSUE_FIELDS = ( (('Issue Title', 'issue_title',60), ('Name', 'name',256)),
                    (('Email ID', 'email_id',64), ('Priority', 'priority',32)),
                    (('Issue Description', 'issue_description',256), ('Resolved Description', 'resolved_description')),
                      (('Status', 'status',11),),   )



SUPPLIER_FIELDS = ( (('Supplier Id *', 'id',60), ('Supplier Name *', 'name',256)),
                    (('Email *', 'email_id',64), ('Phone No. *', 'phone_number',10)),
                    (('Address *', 'address'), ('Status', 'status',11)), )

SKU_SUPPLIER_FIELDS = ( (('Supplier ID *', 'supplier_id',60), ('WMS Code *', 'wms_id','')),
                        (('Supplier Code','supplier_code'), ('Priority *', 'preference',32) ), 
                        (('MOQ', 'moq',256,0), ('Price', 'price'), ) )

RAISE_PO_FIELDS = ( (('Supplier ID', 'supplier_id',11), ('PO Name', 'po_name',30)),
                    (('Ship To', 'ship_to',''), ) )


CUSTOM_ORDER_STATUS = {'Cleared': 'clear', 'Blocked': 'block', 'PO Raised - Yet to Recieve': 'po_rais',
                        'In Production Stage': 'prdctn', 'In Printing Stage': 'prnt', 'In Embroidery Stage': 'embrdry',
                        'Completed': 'cmpltd'}


RAISE_PO_FIELDS1 = OrderedDict([('WMS Code *','wms_code'), ('Supplier Code', 'supplier_code'), ('Quantity *','order_quantity'),('Price','price')])

MOVE_INVENTORY_FIELDS = ( (('WMS Code *','wms_code'),('Source Location *','source_loc')),
                          (('Destination Location *','dest_loc'),('Quantity *','quantity')), )

ADJUST_INVENTORY_FIELDS = ( (('WMS Code *','wms_code'),('Location *','location')),
                            (('Physical Quantity *','quantity'),('Reason','reason')),)

MOVE_INVENTORY_UPLOAD_FIELDS = ['WMS Code', 'Source Location', 'Destination Location', 'Quantity']

SUPPLIER_HEADERS = ['Supplier Id', 'Supplier Name', 'Address', 'Email', 'Phone No.']

VENDOR_HEADERS = ['Vendor Id', 'Vendor Name', 'Address', 'Email', 'Phone No.']

CUSTOMER_HEADERS = ['Customer Id', 'Customer Name', 'Credit Period', 'Tin Number', 'Email', 'Phone No.', 'City', 'State', 'Pin Code',
                    'Address', 'Selling Price Type']

SALES_RETURN_HEADERS = ['Return ID', 'Return Date', 'SKU Code', 'Product Description', 'Market Place', 'Quantity']

SALES_RETURN_TOGGLE = ['Return ID', 'SKU Code', 'Product Description', 'Shipping Quantity', 'Return Quantity', 'Damaged Quantity' ]

SALES_RETURN_BULK = ['Order ID', 'SKU Code', 'Return Quantity', 'Damaged Quantity', 'Return ID', 'Return Date(YYYY-MM-DD)' ]

RETURN_DATA_FIELDS = ['sales-check', 'order_id', 'sku_code', 'customer_id', 'shipping_quantity', 'return_quantity', 'damaged_quantity', 'delete-sales']

SUPPLIER_SKU_HEADERS = ['Supplier Id', 'WMS Code', 'Supplier Code', 'Preference', 'MOQ','Price']

MARKETPLACE_SKU_HEADERS = ['WMS Code', 'Flipkart SKU', 'Snapdeal SKU', 'Paytm SKU', 'Amazon SKU', 'HomeShop18 SKU', 'Jabong SKU', 'Indiatimes SKU', 'Flipkart Description', 'Snapdeal Description', 'Paytm Description', 'HomeShop18 Description', 'Jabong Description', 'Indiatimes Description', 'Amazon Description']

PURCHASE_ORDER_HEADERS = ['PO Name', 'PO Date(MM-DD-YYYY)', 'Supplier ID', 'WMS SKU Code', 'Quantity', 'Price', 'Ship TO']

LOCK_FIELDS = ['', 'Inbound', 'Outbound', 'Inbound and Outbound']

LOCATION_FIELDS = ( (('Zone ID *', 'zone_id'),('Location *', 'location')),
                    (('Capacity', 'max_capacity'), ('Put Sequence', 'fill_sequence')),
                    ( ('Get Sequence', 'pick_sequence'), ('Status', 'status')),
                    (('Location Lock', 'lock_status'), ))

USER_FIELDS = ( (('User Name *', 'username'),('Name *', 'first_name')),
                (('Groups', 'groups'),),)

ADD_USER_FIELDS = ( (('User Name *', 'username'),('First Name *', 'first_name')),
                    (('Last Name', 'last_name'), ('Email', 'email')),
                    (('Password *', 'password'), ('Re-type Password', 're_password')),)

ADD_GROUP_FIELDS = ( (('Group Name *', 'group'),('Permissions', 'permissions')),)

SHIPMENT_FIELDS = ( (('Shipment Number *', 'shipment_number'),('Shipment Date *', 'shipment_date')),
                    (('Truck Number *', 'truck_number'), ('Shipment Reference *', 'shipment_reference')),
                    (('Customer ID', 'customer_id'),) )

ST_ORDER_FIELDS = {'picklist_id': '', 'stock_transfer_id': ''}

CREATE_ORDER_FIELDS = ( (('Customer ID *', 'customer_id'), ('Customer Name', 'customer_name')),
                    (('Telephone', 'telephone'),('Shipment Date *','shipment_date')),
                    (('Address', 'address'), ('Email', 'email_id'))  )

CREATE_ORDER_FIELDS1 = OrderedDict([('SKU Code/WMS Code *','sku_id'),('Quantity *','quantity'), ('Invoice Amount', 'invoice_amount')])

SALES_RETURN_FIELDS = ( (('Return Tracking ID', 'return_id'),), )

MARKETPLACE_SKU_FIELDS = {'marketplace_code': '', 'sku_id': '', 'description': '',
                          'sku_type': ''}

MARKET_LIST_HEADERS = ['Market Place', 'SKU', 'Description']

MARKETPLACE_LIST = ['Flipkart', 'Snapdeal', 'Paytm', 'Amazon', 'Shopclues', 'HomeShop18', 'Jabong', 'Indiatimes']

ORDER_HEADERS = ['Order ID', 'Title', 'SKU Code', 'Quantity','Shipment Date(yyyy-mm-dd)', 'Channel Name', 'Customer Name', 'Email ID', 'Phone Number','Shipping Address', 'State', 'City', 'PIN Code', 'Tax Percentage', 'Invoice Amount']

SALES_RETURN_FIELDS = ( (('Return Tracking ID', 'return_id'),), )

REPORT_FIELDS = ( (('From Date', 'from_date'),('To Date', 'to_date')),
                    (('SKU Code', 'sku_code'), ('SKU Category', 'sku_category')),
                    (('SKU Type', 'sku_type'), ('SKU Class', 'sku_class')) )

SKU_LIST_REPORTS_DATA = {('sku_list_form','reportsTable','SKU List Filters','sku-list', 1, 2, 'sku-report') : (['SKU Code', 'WMS Code', 'SKU Group', 'SKU Type', 'SKU Category', 'SKU Class', 'Put Zone', 'Threshold Quantity'],( (('SKU Code', 'sku_code'), ('SKU Category', 'sku_category')), (('SKU Type', 'sku_type'), ('SKU Class', 'sku_class')),(('WMS Code','wms_code'),))),}

LOCATION_WISE_FILTER = {('location_wise_form', 'locationTable', 'Location Wise Filters', 'location-wise', 3, 4, 'location-report') : (['Location', 'SKU Code', 'WMS Code', 'Product Description', 'Zone', 'Receipt Number', 'Receipt Date', 'Quantity'], ( (('SKU Code', 'sku_code'), ('SKU Category', 'sku_category')), (('SKU Type', 'sku_type'), ('SKU Class', 'sku_class')), (('Location','location'), ('Zone','zone_id')),(('WMS Code', 'wms_code'),), )),}

SUPPLIER_WISE_POS = {('supplier_wise_form', 'suppliertable', 'Supplier Wise Filters', 'supplier-wise', 1, 2, 'supplier-report'): (['Order Date', 'PO Number', 'WMS Code', 'Design', 'Ordered Quantity', 'Received Quantity'], ((('Supplier', 'supplier'),), )),}

GOODS_RECEIPT_NOTE = {('receipt_note_form', 'receiptTable', 'Goods Receipt Filter', 'receipt-note', 11, 12, 'po-report'): (['PO Number', 'Supplier ID', 'Supplier Name', 'Total Quantity'], ( (('From Date', 'from_date'),('To Date', 'to_date')), (('PO Number', 'open_po'), ('WMS Code','wms_code') ), )),}

RECEIPT_SUMMARY = {('receipt_summary_form', 'summaryTable', 'Receipt Summary', 'summary-wise', 5, 6, 'receipt-report'): (['Supplier', 'Receipt Number', 'WMS Code', 'Description', 'Received Quantity'], ( (('From Date', 'from_date'),('To Date', 'to_date')), (('WMS Code', 'wms_code'), ('Supplier', 'supplier')),(('SKU Code','sku_code'),), )),}

DISPATCH_SUMMARY = {('dispatch_summary_form', 'dispatchTable', 'Dispatch Summary', 'dispatch-wise', 13, 14, 'dispatch-report'): (['Order ID', 'WMS Code', 'Description', 'Quantity', 'Date'], ( (('From Date', 'from_date'),('To Date', 'to_date')), (('WMS Code', 'wms_code'),('SKU Code','sku_code') )) ),}

ORDER_SUMMARY_DICT = {'filters': [{'label': 'From Date', 'name': 'from_date', 'type': 'date'}, {'label': 'To Date', 'name': 'to_date',
'type': 'date'}, {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'}, {'label': 'Marketplace', 'name': 'marketplace', 'type': 'select'}, {'label': 'City', 'name': 'city', 'type': 'input'}, {'label': 'State', 'name': 'state', 'type': 'input'}, {'label': 'SKU Category', 'name': 'sku_category', 'type': 'select'}, {'label': 'SKU Brand', 'name': 'brand', 'type': 'input'}, {'label': 'SKU Class', 'name': 'sku_class', 'type': 'input'}, {'label': 'SKU Size', 'name': 'sku_size', 'type': 'input'}, {'label': 'Status', 'name': 'order_report_status', 'type': 'select'}],
                        'dt_headers': ['Order Date', 'Order ID', 'Customer Name' ,'SKU Brand', 'SKU Category', 'SKU Class', 'SKU Size', 'SKU Description', 'SKU Code', 'Order Qty', 'Unit Price', 'Price', 'MRP', 'Discount', 'City', 'State', 'Marketplace', 'Invoice Amount', 'Status'],
                      'dt_url': 'get_order_summary_filter', 'excel_name': 'order_summary_report', 'print_url': 'print_order_summary_report',
                     }

OPEN_JO_REP_DICT = {'filters': [{'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'}, {'label': 'SKU Class','name': 'class',
                                 'type': 'input'}, {'label': 'SKU Category', 'name': 'category','type': 'select'}, {'label': 'SKU Brand',
                                 'name': 'brand', 'type': 'select'}, {'label': 'JO Code','name': 'jo_code', 'type': 'input'},
                                 {'label': 'Stages', 'name': 'stage', 'type': 'select'}],
                    'dt_headers': ['JO Code', 'Jo Creation Date', 'SKU Brand', 'SKU Category', 'SKU Class', 'SKU Code', 'Stage', 'Quantity'],
                    'dt_url': 'get_openjo_report_details', 'excel_name': 'open_jo_report', 'print_url': 'print_open_jo_report',
                   }

SKU_WISE_PO_DICT = {'filters': [{'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'}],
                    'dt_headers': ['PO Date', 'Supplier', 'SKU Code', 'Order Quantity', 'Received Quantity', 'Rejected Quantity', 'Receipt Date', 'Status'],
                    'mk_dt_headers': ['PO Date', 'PO Number', 'Supplier ID', 'Supplier Name', 'Recepient',  'SKU Code', 'SKU Description', 'SKU Class', 'SKU Style Name', 'SKU Brand', 'SKU Category', 'PO Qty', 'Unit Rate', 'Pre-Tax PO Amount', 'Tax', 'After Tax PO Amount', 'Qty received', 'Qty Status'],
                    'dt_url': 'get_sku_purchase_filter', 'excel_name': 'sku_wise_purchases', 'print_url': 'print_sku_wise_purchase',
                   }

REPORT_DATA_NAMES = {'order_summary_report': ORDER_SUMMARY_DICT, 'open_jo_report': OPEN_JO_REP_DICT, 'sku_wise_po_report': SKU_WISE_PO_DICT}

SKU_WISE_STOCK = {('sku_wise_form','skustockTable','SKU Wise Stock Summary','sku-wise', 1, 2, 'sku-wise-report') : (['SKU Code', 'WMS Code', 'Product Description', 'SKU Category', 'Total Quantity'],( (('SKU Code', 'sku_code'), ('SKU Category', 'sku_category')), (('SKU Type', 'sku_type'), ('SKU Class', 'sku_class')),(('WMS Code','wms_code'),))),}

SKU_WISE_PURCHASES =  {('sku_wise_purchase','skupurchaseTable','SKU Wise Purchase Orders','sku-purchase-wise', 1, 2, 'sku-wise-purchase-report') : (['PO Date', 'Supplier', 'SKU Code', 'Order Quantity', 'Received Quantity', 'Receipt Date', 'Status'],( (('WMS SKU Code', 'wms_code'),),)),}

SALES_RETURN_REPORT = {('sales_return_form','salesreturnTable','Sales Return Reports','sales-report', 1, 2, 'sales-return-report') : (['SKU Code', 'Order ID', 'Customer ID', 'Return Date', 'Status', 'Quantity'],( (('SKU Code', 'sku_code'), ('WMS Code', 'wms_code')), (('Order ID', 'order_id'), ('Customer ID', 'customer_id')),(('Date','creation_date'),))),}

LOCATION_HEADERS = ['Zone', 'Location', 'Capacity', 'Put sequence', 'Get sequence', 'SKU Group']

SKU_HEADERS = ['WMS Code','SKU Description', 'SKU Group', 'SKU Type', 'SKU Category', 'SKU Class', 'SKU Brand', 'Style Name', 'SKU Size',
               'Size Type', 'Put Zone', 'Price', 'MRP Price', 'Sequence', 'Image Url', 'Threshold Quantity', 'Measurment Type',
               'Sale Through', 'Color', 'EAN Number', 'Status']

MARKET_USER_SKU_HEADERS = ['WMS Code','SKU Description', 'SKU Group', 'SKU Type(Options: FG, RM)', 'SKU Category', 'SKU Class',
                           'SKU Brand', 'Style Name', 'Mix SKU Attribute(Options: No Mix, Mix within Group)', 'Put Zone',
                           'Price', 'MRP Price', 'Sequence', 'Image Url','Threshold Quantity', 'Measurment Type', 'Sale Through',
                           'Color', 'EAN Number', 'Status']

SALES_RETURNS_HEADERS = ['Return ID', 'Order ID', 'SKU Code', 'Return Quantity', 'Damaged Quantity', 'Return Date(YYYY-MM-DD)']

EXCEL_HEADERS = ['Receipt Number', 'Receipt Date(YYYY-MM-DD)',  'WMS SKU', 'Location', 'Quantity', 'Receipt Type']
EXCEL_RECORDS = ('receipt_number', 'receipt_date', 'wms_code', 'location', 'wms_quantity', 'receipt_type')

SKU_EXCEL = ('wms_code', 'sku_desc', 'sku_group', 'sku_type', 'sku_category', 'sku_class', 'sku_brand', 'style_name', 'sku_size', 'zone_id',
             'threshold_quantity', 'status')

PICKLIST_FIELDS = { 'order_id': '', 'picklist_number': '', 'reserved_quantity': '', 'picked_quantity': 0, 'remarks': '', 'status': 'open'}
PICKLIST_HEADER = ('ORDER ID', 'WMS Code', 'Title', 'Zone', 'Location', 'Reserved Quantity', 'Picked Quantity')

PRINT_OUTBOUND_PICKLIST_HEADERS = ('WMS Code', 'Title','Zone', 'Location', 'Reserved Quantity', 'Picked Quantity')

PRINT_PICKLIST_HEADERS = ('WMS Code', 'Title', 'Zone', 'Location', 'Reserved Quantity', 'Picked Quantity', 'Units Of Measurement')

PROCESSING_HEADER = ('WMS Code', 'Title', 'Zone', 'Location', 'Reserved Quantity', 'Picked Quantity', '')

SKU_SUPPLIER_MAPPING = OrderedDict([('Supplier ID','supplier__id'),('SKU CODE','sku__wms_code'),('Supplier Code', 'supplier_code'),('Priority','preference'),('MOQ','moq')])

SUPPLIER_MASTER_HEADERS = OrderedDict([('Supplier ID','id'),('Name','name'),('Address','address'),('Phone Number','phone_number'),('Email','email_id'),('Status','status')])


STOCK_DET = ([('0','receipt_number'),('1','receipt_date'),('2','sku_id__sku_code'),('3','sku_id__wms_code'),('4','sku_id__sku_desc'),('5','location_id__zone'),('6','location_id__location'),('7','quantity')])

ORDER_DETAIL_HEADERS = OrderedDict([('Order ID','order_id'),('SKU Code','sku_id__sku_code'),('Title','title'),('Product Quantity','quantity'),('Shipment Date','shipment_date')])

OPEN_PICK_LIST_HEADERS = OrderedDict([('Picklist ID','picklist_number'), ('Customer / Marketplace','picklist_number'), ('Picklist Note','remarks'), ('Reserved Quantity', 'reserved_quantity'), ('Shipment Date', 'order__shipment_date'), ('Date','creation_date')])

PICKED_PICK_LIST_HEADERS = OrderedDict([('Picklist ID','picklist_number'), ('Customer / Marketplace','picklist_number'), ('Picklist Note','remarks'), ('Reserved Quantity', 'reserved_quantity'), ('Shipment Date', 'order__shipment_date'), ('Date','creation_date')])

BATCH_PICK_LIST_HEADERS = OrderedDict([('Picklist ID','picklist_number'), ('Picklist Note','remarks'), ('Date','creation_date')])


PO_SUGGESTIONS = OrderedDict([('0','creation_date'),('1','supplier_id'),('2','sku_id'),('3','order_quantity'),('4','price'),('5','status')])

RECEIVE_PO_HEADERS = OrderedDict([('Order ID','order_id'),('Order Date','creation_date'),('Supplier ID','open_po_id__supplier_id__id'),('Supplier Name','open_po_id__supplier_id__name')])

STOCK_DETAIL_HEADERS = OrderedDict([('SKU Code','sku_id__sku_code'),('WMS Code','sku_id__wms_code'),('Product Description','sku_id__sku_desc'),('Quantity','quantity')])

CYCLE_COUNT_HEADERS = OrderedDict([('WMS Code','sku_id__wms_code'),('Zone','location_id__zone'),('Location','location_id__location'),('Quantity','quantity')])

BATCH_DATA_HEADERS = OrderedDict([('SKU Code','sku__sku_code'),('Title','title'),('Total Quantity','quantity')])

PUT_AWAY = OrderedDict([('PO Number','open_po_id'),('Order Date','creation_date'),('Supplier ID','open_po_id__supplier_id__id'),('Supplier Name','open_po_id__supplier_id__name')])

SKU_MASTER_HEADERS = OrderedDict([('WMS SKU Code', 'wms_code'), ('Product Description', 'sku_desc'), ('SKU Type', 'sku_type'), ('SKU Category', 'sku_category'), ('SKU Class', 'sku_class'), ('Color', 'color'), ('Zone', 'zone_id'), ('Status', 'status')])

PRICING_MASTER_HEADER = OrderedDict([('SKU Code', 'sku__sku_code'), ('SKU Description', 'sku__sku_desc'), ('Selling Price Type', 'price_type'), ('Price', 'price'), ('Discount', 'discount')])

SKU_MASTER_EXCEL_HEADERS = ['WMS SKU Code', 'Product Description', 'SKU Type', 'SKU Category', 'SKU Brand', 'SKU Class', 'Style Name',
                            'SKU Size', 'SKU Group', 'Color', 'Zone', 'Price', 'MRP Price', 'Measurement Type', 'Sequence',
                            'Sale Through', 'Status']

SIZE_MASTER_HEADERS = OrderedDict([('Size Name', 'size_name'), ('Sizes', 'size_value')])

QUALITY_CHECK = OrderedDict([('','id'),('Purchase Order ID','purchase_order__order_id'),('Supplier ID','purchase_order__open_po__supplier_id'),('Supplier Name',  'purchase_order__open_po__supplier__name'),('Total Quantity','purchase_order__received_quantity')])

SHIPMENT_INFO = OrderedDict([('',id),('Customer ID','order__customer_id'),('Customer Name','order__customer_name')])

CYCLE_COUNT_FIELDS = {'cycle': '', 'sku_id': '', 'location_id': '',
                   'quantity': '', 'seen_quantity': '',
                   'status': 1, 'creation_date': '', 'updation_date': ''}

INVENTORY_FIELDS =  {'cycle_id': '', 'adjusted_location': '',
                   'adjusted_quantity': '', 'reason': 'Moved Successfully',
                    'creation_date': '', 'updation_date': ''}

BACK_ORDER_TABLE = [ 'WMS Code', 'Ordered Quantity', 'Stock Quantity', 'Transit Quantity', 'Procurement Quantity']

BACK_ORDER_RM_TABLE = [ 'Job Code', 'WMS Code', 'Ordered Quantity', 'Stock Quantity', 'Transit Quantity', 'Procurement Quantity']

BACK_ORDER_HEADER = ['Supplier Name', 'WMS Code', 'Title', 'Quantity', 'Price']

QC_WMS_HEADER = ['Purchase Order', 'Quantity', 'Accepted Quantity', 'Rejected Quantity']

REJECT_REASONS = ['Color Mismatch', 'Price Mismatch', 'Wrong Product', 'Package Damaged', 'Product Damaged', 'Others']

QC_SERIAL_FIELDS = {'quality_check_id': '', 'serial_number_id': '', 'status': '','reason': ''}

RAISE_JO_HEADERS = OrderedDict([('Product SKU Code', 'product_code'), ('Product SKU Quantity', 'product_quantity'),
                                ('Material SKU Code', 'material_code'), ('Material SKU Quantity', 'material_quantity'), ('Measurement Type', 'measurement_type')])

JO_PRODUCT_FIELDS = {'product_quantity': 0, 'received_quantity': 0, 'job_code': 0, 'jo_reference': '','status': 'open', 'product_code_id': ''}

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

CUSTOMER_FIELDS = ( (('Customer ID *', 'id',60), ('Customer Name *', 'name',256)),
                    (('Email *', 'email_id',64), ('Phone No. *', 'phone_number',10)),
                    (('Address *', 'address'), ('Status', 'status',11)), )

CUSTOMER_DATA = {'name': '', 'address': '', 'phone_number': '', 'email_id': '', 'status': 1, 'price_type': '', 'tax_type': ''}

PRODUCTION_STAGES = {'Apparel': ['Raw Material Inspection', 'Fabric Washing', 'Finishing'], 'Default': ['Raw Material Inspection',
                     'Fabric Washing', 'Finishing']}

STATUS_TRACKING_FIELDS = {'status_id': '', 'status_type': '', 'status_value': ''}

BOM_TABLE_HEADERS = ['Product SKU Code', 'Product Description']

BOM_UPLOAD_EXCEL_HEADERS = ['Product SKU Code', 'Material SKU Code', 'Material Quantity', 'Wastage Percentage', 'Unit of Measurement' ]

ADD_BOM_HEADERS = OrderedDict([('Material SKU Code', 'material_sku'), ('Material Quantity', 'material_quantity'),
                               ('Unit of Measurement', 'unit_of_measurement')])

ADD_BOM_FIELDS = {'product_sku_id': '', 'material_sku_id': '', 'material_quantity': 0, 'unit_of_measurement': ''}

UOM_FIELDS = ['Kgs', 'Units', 'Meters']

PICKLIST_SKIP_LIST = ('sortingTable_length', 'fifo-switch', 'ship_reference', 'selected')

MAIL_REPORTS = { 'sku_list': ['SKU List'], 'location_wise_stock': ['Location Wise SKU'], 'receipt_note': ['Receipt Summary'], 'dispatch_summary': ['Dispatch Summary'], 'sku_wise': ['SKU Wise Stock'] }

MAIL_REPORTS_DATA = {'Raise PO': 'raise_po', 'Receive PO': 'receive_po', 'Orders': 'order', 'Dispatch': 'dispatch', 'Internal Mail' : 'internal_mail'}

PICKLIST_OPTIONS = {'Scan SKU': 'scan_sku', 'Scan SKU Location': 'scan_sku_location'}

REPORTS_DATA = {'SKU List': 'sku_list', 'Location Wise SKU': 'location_wise_stock', 'Receipt Summary': 'receipt_note', 'Dispatch Summary': 'dispatch_summary', 'SKU Wise Stock': 'sku_wise'}

SKU_CUSTOMER_FIELDS = ( (('Customer ID *', 'customer_id',60), ('Customer Name *', 'customer_name',256)),
                        (('SKU Code *','sku_code'), ('Price *', 'price'), ) )

CUSTOMER_SKU_DATA = {'customer_name_id': '', 'sku_id': '', 'price': ''}

CUSTOMER_SKU_MAPPING_HEADERS = OrderedDict([('Customer ID','customer_name__customer_id'),('Customer Name','customer_name__name'),
                                            ('SKU Code','sku__sku_code'),('Price','price')])


ADD_USER_DICT = {'username': '', 'first_name': '', 'last_name': '', 'password': '', 'email': ''}

ADD_WAREHOUSE_DICT = {'user_id': '', 'city': '', 'is_active': 1, 'country': '', u'state': '', 'pin_code': '', 'address': '',
                      'phone_number': '', 'prefix': '', 'location': ''}

PICKLIST_EXCEL = OrderedDict(( ('WMS Code', 'wms_code'), ('Title', 'title'), ('Zone', 'zone'), ('Location', 'location'),
                               ('Reserved Quantity', 'reserved_quantity'), ('Stock Left', 'stock_left'),
                               ('Last Picked Location', 'last_picked_locs')
                            ))

SHOPCLUES_EXCEL = {'order_id': 1, 'quantity': 5, 'title': 3, 'invoice_amount': 20, 'address': 11, 'customer_name': 10,
                   'marketplace': 'Shopclues', 'sku_code': 15}

SHOPCLUES_EXCEL1 = {'order_id': 0, 'quantity': 13, 'title': 6, 'invoice_amount': 45, 'address': 9, 'customer_name': 8,
                    'marketplace': 'Shopclues', 'sku_code': 48}

VOONIK_EXCEL = {'order_id': 0, 'sku_code': 1, 'invoice_amount': 4, 'marketplace': 'Voonik'}

FLIPKART_EXCEL = {'order_id': 6, 'quantity': 14, 'title': 2, 'invoice_amount': 17, 'address': 22, 'customer_name': 21,
                  'marketplace': 'Flipkart', 'sku_code': 8}

FLIPKART_EXCEL1 = {'order_id': 6, 'quantity': 14, 'title': 2, 'invoice_amount': 16, 'address': 21, 'customer_name': 20,
                  'marketplace': 'Flipkart', 'sku_code': 8}

FLIPKART_EXCEL2 = {'order_id': 2, 'quantity': 15, 'title': 8, 'invoice_amount': 12, 'address': 19, 'customer_name': 18,
                   'marketplace': 'Flipkart', 'sku_code': 7}

FLIPKART_EXCEL3 = {'order_id': 2, 'quantity': 17, 'title': 15, 'invoice_amount': 7, 'address': 21, 'customer_name': 20,
                   'marketplace': 'Flipkart', 'sku_code': 14}

FLIPKART_EXCEL4 = {'order_id': 2, 'quantity': 19, 'title': 17, 'invoice_amount': 7, 'address': 23, 'customer_name': 22,
                   'marketplace': 'Flipkart', 'sku_code': 16}

PAYTM_EXCEL1 = {'order_id': 0, 'quantity': 21, 'title': 12, 'invoice_amount': 20, 'address': 7, 'customer_name': 3, 'marketplace': 'Paytm',
               'sku_code': 14}

PAYTM_EXCEL2 = {'order_id': 13, 'quantity': 10, 'title': 1, 'invoice_amount': 9, 'address': 22, 'customer_name': 18, 'marketplace': 'Paytm',
                'sku_code': 3}

FLIPKART_FA_EXCEL = {'order_id': 1, 'quantity': 13, 'title': 8, 'invoice_amount': 9, 'address': 20, 'customer_name': 29,
                     'marketplace': 'Flipkart FA', 'sku_code': 7}

SNAPDEAL_EXCEL = {'order_id': 3, 'title': 1, 'invoice_amount': 13, 'customer_name': 8, 'marketplace': 'Snapdeal', 'sku_code': 4,
                  'shipment_date': 17}

SNAPDEAL_EXCEL1 = {'order_id': 3, 'title': 2, 'invoice_amount': 14, 'customer_name': 9, 'marketplace': 'Snapdeal', 'sku_code': 5,
                  'shipment_date': 8}

AMAZON_FA_EXCEL = {'title': 4, 'invoice_amount': 14, 'marketplace': 'Amazon FA', 'sku_code': 3, 'quantity': 7}

SNAPDEAL_FA_EXCEL = {'title': 4, 'invoice_amount': 6, 'marketplace': 'Snapdeal FA', 'sku_code': 3, 'quantity': 5}

ORDER_DEF_EXCEL = OrderedDict(( ('order_id', 0), ('quantity', 3), ('title', 1), ('shipment_date', 4), ('sku_code', 2),
                                ('channel_name', 5), ('shipment_check', 'true'), ('customer_name', 6), ('address', 9),
                                ('state', 10), ('city', 11), ('pin_code', 12), ('tax_percentage', [13, 14]), ('email_id', 7),
                                ('telephone', 8)
                             ))

EASYOPS_ORDER_EXCEL = {'order_id': 1, 'quantity': 8, 'invoice_amount': 3, 'channel_name': 5, 'sku_code': 7, 'title': 6, 'status': 4,
                       'split_order_id': 1}

SKU_DEF_EXCEL = OrderedDict(( ('wms_code', 0), ('sku_desc', 1), ('sku_group', 2), ('sku_type', 3), ('sku_category', 4), ('sku_class', 5),
                              ('sku_brand', 6), ('style_name', 7), ('sku_size', 8), ('size_type', 9), ('zone_id', 10), ('price', 11),
                              ('mrp', 12), ('sequence', 13), ('image_url', 14), ('threshold_quantity', 15), ('measurement_type', 16),
                              ('sale_through', 17), ('color', 18), ('ean_number', 19), ('status', 20)
                           ))
MARKETPLACE_SKU_DEF_EXCEL = OrderedDict(( ('wms_code', 0), ('sku_desc', 1), ('sku_group', 2), ('sku_type', 3), ('sku_category', 4),
                                          ('sku_class', 5), ('sku_brand', 6), ('style_name', 7), ('mix_sku', 8), ('zone_id', 9),
                                          ('price', 10), ('mrp', 11), ('sequence', 12), ('image_url', 13), ('threshold_quantity', 14),
                                          ('measurement_type', 15), ('sale_through', 16), ('color', 17), ('ean_number', 18), ('status', 19)
                           ))

ITEM_MASTER_EXCEL = OrderedDict(( ('wms_code', 1), ('sku_desc', 2), ('sku_category', 25), ('image_url', 18), ('sku_size', 14) ))

JABONG_EXCEL = {'order_id': 1, 'title': 7, 'invoice_amount': 14, 'marketplace': 'Jabong', 'sku_code': 5, 'quantity': 9}

JABONG_EXCEL1 = {'order_id': 6, 'title': 37, 'invoice_amount': 33, 'marketplace': 'Jabong', 'sku_code': 2}

INDIA_TIMES_EXCEL = {'order_id': 2, 'invoice_amount': 16, 'address': 8, 'customer_name': 7,
                     'marketplace': 'Indiatimes', 'sku_code': 15, 'telephone': 12}

HOMESHOP18_EXCEL = {'order_id': 0, 'invoice_amount': 10, 'address': 18, 'customer_name': 4, 'marketplace': 'HomeShop18',
                    'title': 6, 'sku_code': 8, 'quantity': 9, 'telephone': 22}

AMAZON_EXCEL = {'order_id': 1, 'invoice_amount': 25, 'address': [17,18,19], 'customer_name': 8, 'marketplace': 'Amazon',
                'title': 11, 'sku_code': 10, 'quantity': 12, 'telephone': 9, 'email_id': 7}

AMAZON_EXCEL1 = {'order_id': 1, 'invoice_amount': 11, 'address': [17,18,19], 'customer_name': 16, 'marketplace': 'Amazon',
                        'title': 8, 'sku_code': 7, 'quantity': 9, 'telephone': 6, 'email_id': 4}

ASKMEBAZZAR_EXCEL = {'order_id': 0, 'invoice_amount': 14, 'address': 27, 'customer_name': 9, 'marketplace': 'Ask Me Bazzar',
                    'title': 30, 'sku_code': 29, 'quantity': 12, 'telephone': 10}

FLIPKART_FA_EXCEL1 = {'order_id': 16, 'invoice_amount': 15, 'marketplace': 'Flipkart FA', 'title': 0, 'sku_code': 2, 'quantity': 9}

CAMPUS_SUTRA_EXCEL = {'order_id': 2, 'invoice_amount': 14, 'marketplace': 'Campus Sutra', 'sku_code': 6, 'quantity': 13, 'customer_name': 3,
                      'address': 5, 'telephone': 10, 'email_id': 7, 'shipment_date': 1}

LIMEROAD_EXCEL = {'order_id': 0, 'invoice_amount': 8, 'marketplace': 'Lime Road', 'sku_code': 3, 'quantity': 9, 'customer_name': 10,
                      'address': 12, 'telephone': 11,  'shipment_date': 1}

MYNTRA_EXCEL = {'invoice_amount': 14, 'marketplace': 'Myntra', 'sku_code': 2, 'quantity': 9, 'title': 7, 'original_order_id': 1, 'order_id': 1,
                'vat': [14, 11], 'mrp': 12, 'discount': 13}

UNI_COMMERCE_EXCEL = {'order_id': 12, 'title': 19, 'channel_name': 2, 'sku_code': 1, 'recreate': True}

# ---  Return Marketplace headers --
GENERIC_RETURN_EXCEL = OrderedDict((('sku_id', 2), ('order_id', 1), ('quantity', 3), ('damaged_quantity', 4),
                                   ('return_id', 0),  ('return_date', 5)))

#MYNTRA_RETURN_EXCEL = OrderedDict((('sku_id', [5,7]), ('quantity', 8), ('reason', 13), ('marketplace', "MYNTRA")))

MYNTRA_RETURN_EXCEL = OrderedDict((('sku_id', [5,7]), ('quantity', 8), ('reason', 13), ('marketplace', "MYNTRA")))

UNIWEAR_RETURN_EXCEL = OrderedDict((('sku_id', 4), ('channel', 14),('reason', 12),
                                        ('return_id', 5),  ('return_date', 8)))


UNI_COMMERCE_EXCEL1 = {'order_id': 8, 'channel_name': 2, 'sku_code': 20, 'customer_name': 9, 'email_id': 10, 'telephone': 11,
                       'address': [12, 13, 14], 'state': 15, 'pin_code': 16, 'invoice_amount': 19, 'recreate': True}

UNI_WARE_EXCEL = {'order_id': 12, 'channel_name': 2, 'sku_code': 1, 'quantity': 34}

UNI_WARE_EXCEL1 = {'order_id': 0, 'email_id': 5, 'telephone': 20, 'customer_name': 13, 'address': [14, 15], 'city': 16, 'state': 17,
                   'pin_code': 19, 'title': 33, 'channel_name': 37, 'sku_code': 31, 'invoice_amount': 42, 'discount': 46}

EXCEL_REPORT_MAPPING = {'dispatch_summary': 'get_dispatch_data', 'sku_list': 'get_sku_filter_data', 'location_wise': 'get_location_stock_data',
                        'goods_receipt': 'get_po_filter_data', 'receipt_summary': 'get_receipt_filter_data',
                        'sku_stock': 'print_sku_wise_data', 'sku_wise_purchases': 'sku_wise_purchase_data',
                        'supplier_wise': 'get_supplier_details_data', 'sales_report': 'get_sales_return_filter_data',
                        'inventory_adjust_report': 'get_adjust_filter_data', 'inventory_aging_report': 'get_aging_filter_data',
                        'stock_summary_report': 'get_stock_summary_data', 'daily_production_report': 'get_daily_production_data',
                        'order_summary_report': 'get_order_summary_data', 'open_jo_report': 'get_openjo_details'}

SHIPMENT_STATUS = ['Dispatched', 'In Transit', 'Out for Delivery', 'Delivered']

RWO_FIELDS = {'vendor_id': '', 'job_order_id': '', 'status': 1}


COMBO_SKU_EXCEL_HEADERS = ['SKU Code', 'Combo SKU']


RWO_PURCHASE_FIELDS = {'purchase_order_id': '', 'rwo_id': ''}

VENDOR_PICKLIST_FIELDS = {'jo_material_id': '', 'status': 'open', 'reserved_quantity': 0, 'picked_quantity': 0}

STAGES_FIELDS = {'stage_name': '', 'user': ''}

SIZES_LIST = ['S', 'M', 'L', 'XL', 'XXL', 'XXXL', 'FREE SIZE']

SKU_FIELD_TYPES = [{'field_name': 'sku_category', 'field_value': 'SKU Category'}, {'field_name': 'sku_brand', 'field_value': 'SKU Brand'},
                   {'field_name': 'sku_group', 'field_value': 'SKU Group'}]

PERMISSION_DICT = OrderedDict((
                               # Masters
                               ("MASTERS_LABEL", (("SKU Master", "skumaster"), ("Location Master", "locationmaster"), 
                               ("Supplier Master", "suppliermaster"),("Supplier SKU Mapping", "skusupplier"), 
                               ("Customer Master", "customermaster"),("Customer SKU Master", "customersku"), ("BOM Master", "bommaster"), 
                               ("Vendor Master", "vendormaster"),("Discount Master", "categorydiscount"), 
                               ("Custom SKU Template", "productproperties"),("Size Master", "sizemaster"))),
                               # Inbound
                               ("INBOUND_LABEL", (("Raise PO", "openpo"), ("Receive PO", "purchaseorder"), ("Quality Check", "qualitycheck"),
                               ("Putaway Confirmation", "polocation"), ("Sales Returns", "orderreturns"),
                               ("Returns Putaway", "returnslocation"))),
                               # Production
                               ("PRODUCTION_LABEL", (("Raise Job order", "jomaterial"), ("RM Picklist", "materialpicklist"), 
                               ("Receive Job Order", "joborder"),("Job Order Putaway", "rmlocation"))),
                               # Stock Locator
                               ("STOCK_LABEL",(("Stock Detail", "stockdetail"), ("Vendor Stock", "vendorstock"), ("Cycle Count", "cyclecount"),
                               ("Inventory Adjustment", "inventoryadjustment"),("Stock Summary", "skustock"))),
                               # Outbound
                               ("OUTBOUND_LABEL",(("Create Orders", "orderdetail"), ("View Orders", "picklist"), 
                               ("Pull Confirmation", "picklistlocation"))),
                               # Shipment Info
                               ("SHIPMENT_LABEL",(("Shipment Info", "shipmentinfo"))),
                               # Others
                               ("OTHERS_LABEL", (("Raise Stock Transfer", "openst"), ("Create Stock Transfer", "stocktransfer"))),
                               # Payment
                               ("PAYMENT_LABEL", (("PAYMENTS","paymentsummary")))
                             ))

ORDERS_TRACK_STATUS = {0: 'Resolved', 1: "Conflict", 2: "Delete"}

EASYOPS_ORDER_MAPPING = {'id': 'order["itemId"]', 'order_id': 'orderTrackingNumber', 'items': 'orderItems', 'channel': 'orders["channel"]',
                         'sku': 'order["easyopsSku"]',
                         'title': 'order["productTitle"]', 'quantity': 'order["quantity"]',
                         'shipment_date': 'orders["orderDate"]', 'channel_sku': 'order["channelSku"]',
                         'unit_price': 'order["unitPrice"]', 'order_items': 'orders["orderItems"]'}

EASYOPS_SHIPPED_ORDER_MAPPING = {'id': 'order["itemId"]', 'order_id': 'orderTrackingNumber', 'items': 'orderItems', 'channel': 'channel',
                         'sku': 'order["easyopsSku"]',
                         'title': 'order["productTitle"]', 'quantity': 'order["quantity"]',
                         'shipment_date': 'orders["orderDate"]',
                         'unit_price': 'order["unitPrice"]', 'order_items': 'orders["orderItems"]'}

ORDER_SUMMARY_FIELDS = {'discount': 0, 'creation_date': datetime.datetime.now(), 'issue_type': 'order', 'vat': 0, 'tax_value': 0,
                        'order_taken_by': ''}

EASYOPS_STOCK_HEADERS = OrderedDict([('Product Name', 'sku_desc'), ('Sku', 'wms_code'), ('Vendor Sku', 'wms_code'),
                                     ('Stock', 'stock_count'), ('Purchase Price', 'purchase_price')])

EASYOPS_RETURN_ORDER_MAPPING = {'order_id': 'orderId', 'items': 'data', 'return_id': 'rtnId',
                                'return_date': 'returnDate', 'sku': 'order["easyopsSku"]',
                                'damaged_quantity': 'order["badQty"]', 'return_quantity': 'order["goodQty"]',
                                'return_type': 'orders["returnType"]', 'order_items': 'orders["lineItems"]',
                                'marketplace': 'orders["channel"]', 'reason': 'orders["returnReason"]'}

EASYOPS_CANCEL_ORDER_MAPPING = {'id': 'orderId', 'order_id': 'orderTrackingNumber', 'items': 'orderItems', 'channel': 'channel',
                                'sku': 'order["easyopsSku"]',
                                'title': 'order["productTitle"]', 'quantity': 'order["quantity"]',
                                'shipment_date': 'orders["orderDate"]',
                                'unit_price': 'order["unitPrice"]', 'order_items': 'orders["orderItems"]'}

ORDER_DETAIL_STATES = {0: 'Picklist generated', 1: 'Newly Created', 2: 'Dispatched', 3: 'Cancelled', 4: 'Returned'}

PAYMENT_MODES = ['Credit Card', 'Debit Card', 'Cash', 'NEFT', 'RTGS', 'IMPS', 'Online Transfer', 'Cash Remittance', 'Cheque']

ORDER_HEADERS_d = OrderedDict(( ('Unit Price', 'unit_price'), ('Amount', 'amount'), ('Tax', 'tax'), ('Total Amount', 'total_amount'),
                                       ( 'Remarks', 'remarks') ))

STYLE_DETAIL_HEADERS = OrderedDict(( ('SKU Code', 'wms_code'), ('SKU Description', 'sku_desc'), ('Size', 'sku_size'),
                                     ('1-Day Stock', 'physical_stock'), ('3-Day Stock', 'all_quantity')
                                  ))

TAX_TYPES = OrderedDict(( ('DEFAULT', 0), ('VAT', 5.5), ('CST', 2) ))

##RETAILONE RELATED
R1_ORDER_MAPPING = {'id': 'id', 'order_id': 'order_id', 'items': 'items',
                    'channel': 'orders["channel_sku"]["channel"]["name"]', 'sku': 'order["sku"]', 'channel_sku': 'order["mp_id_value"]',
                    'title': 'order["title"]', 'quantity': 'order["quantity"]',
                    'shipment_date': 'order["ship_by"]',
                    'unit_price': '0', 'order_items': ''}

R1_RETURN_ORDER_MAPPING = {'order_id': 'order_id', 'items': 'items', 'return_id': 'return_id',
                           'return_date': 'return_date', 'sku': 'order["sku"]', 'return_type': 'order["return_type"]',
                           'damaged_quantity': '0', 'return_quantity': 'order["quantity"]',
                           'order_items': '', 'reason': 'order["return_reason"]', 'marketplace': 'order["channel_sku"]["channel"]["name"]'}

#BARCODE_FORMATS = {'adam_clothing': {'format1': ['sku_master'], 'format2': ['sku_master'], 'format3': ['sku_master']}}

BARCODE_DICT = {'format1': {'SKUCode': '', 'SKUDes': '', 'Color': '', 'Size': '', 'SKUPrintQty': '', 'Brand': '', 'Style': ''},
                'format2': {'SKUCode': '', 'SKUDes': '', 'color': '', 'Size': '', 'SKUPrintQty': '', 'Brand': '', 'Product': '',
                            'DesignNo': '', 'Qty': '1', 'Gender': '', 'MRP': '', 'Packed on': '', 'Manufactured By': '', 'Marketed By': ''},
                'format3': {'SKUCode': '', 'SKUDes': '', 'color': '', 'Size': '', 'SKUPrintQty': '', 'Brand': '', 'Product': '', 'DesignNo': '',
                            'Qty': '1', 'Gender': '', 'MRP': '', 'MFD': '', 'Manufactured By': '', 'Marketed By': ''}}

BARCODE_KEYS = {'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details'}

BARCODE_ADDRESS_DICT = {'adam_clothing1': 'Adam Exports 401, 4th Floor, Pratiek Plazza, S.V.Road, Goregaon West, Mumbai - 400062. MADE IN INDIA'}

PRICING_MASTER_HEADERS = ['SKU Code', 'Selling Price type', 'Price', 'Discount']

PRICE_DEF_EXCEL = OrderedDict(( ('sku_id', 0), ('price_type', 1), ('price', 2), ('discount', 3) ))

PRICE_MASTER_DATA = {'sku_id': '', 'price_type': '', 'price': 0, 'discount': 0}

SELLER_DATA = {'name': '', 'address': '', 'phone_number': '', 'email_id': '', 'status': 1, 'price_type': ''}

USER_SKU_EXCEL = {'warehouse_user': SKU_HEADERS, 'marketplace_user': MARKET_USER_SKU_HEADERS, 'customer': SKU_HEADERS}

USER_SKU_EXCEL_MAPPING = {'warehouse_user': SKU_DEF_EXCEL, 'marketplace_user': MARKETPLACE_SKU_DEF_EXCEL, 'customer': SKU_DEF_EXCEL}

MIX_SKU_MAPPING = {'no mix': 'no_mix', 'mix within group': 'mix_group'}

RETURNS_TYPE_MAPPING = {'return to origin(rto)': 'rto', 'customer initiated return': 'customer_return'}

MYNTRA_BANGALORE_ADDRESS = 'Myntra Designs Pvt Ltd\nNumber 88/17-18 and 19, Khata number 44 and 45, Ward Number 7 ,\n\
                            Singasandra Village, Hongasandra panchayat,\nBegur Hobli, Bangalore - 560068\nKarnataka       TIN:29910754899'

MYNTRA_MUMBAI_ADDRESS = 'Myntra Designs Pvt Ltd\nSSN Logistics Pvt Ltd, B-2, Antariksha Lodgidrome Warehousing Complex, Opp\n\
                         Vashere HP petrol pump Aamne-sape, Pagdha, Kalyan rd,Bhiwandi - 421302\n\
                         TIN: 27590747736'

USER_MYNTRA_ADDRESS = {'campus_sutra': MYNTRA_BANGALORE_ADDRESS, 'adam_clothing': MYNTRA_MUMBAI_ADDRESS, 'adam_clothing1': MYNTRA_MUMBAI_ADDRESS}

SHOTANG_ORDER_FILE_EXCEL = {'order_id': 1, 'customer_name': 8, 'customer_id': 7, 'telephone': 9, 'address': 10, 'title': 13, 'sku_code': 2,
                            'invoice_amount': 6, 'sor_id': 0, 'order_date': 3, 'quantity': 4, 'order_status': 19, 'seller': 11,
                            'invoice_no': 16, 'marketplace': 'Shotang'}

SELLER_ORDER_FIELDS = {'sor_id': '', 'quantity': 0, 'order_status': '', 'order_id': '', 'seller_id': '', 'status': 1, 'invoice_no': ''}

SELLER_MARGIN_DICT = {'seller_id': '', 'sku_id': '', 'margin': 0}

def fn_timer(function):
    @wraps(function)
    def function_timer(*args, **kwargs):
        t0 = time.time()
        result = function(*args, **kwargs)
        t1 = time.time()
        print ('Time taken to run %s: %s seconds' %
               (function.func_name, str(t1-t0))
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
    if 'Invoice Amount' in headers: #For Order Summary Report
        table_data = '<table class="table"><tbody style="font-size:8px"><tr class="active">'

    for header in headers:
        table_data += "<th style='width:20%;word-wrap: break-word;'>"+str(header)+"</th>"
    table_data += "</tr>"

    for item in data:
        table_data += "<tr>"
        if isinstance(item, dict):
            item = item.values()

        for dat in item:
            table_data += "<td style='text-align:center;width:20%;word-wrap: break-word;'>"+str(dat)+"</td>"
        table_data += "</tr>"
    table_data += "</tbody></table>"

    return table_data

def create_po_reports_table(headers, data, user_profile, supplier):
    order_date = (str(datetime.datetime.now()).split(' ')[0]).split('-')
    order_date.reverse()
    table_data = "<center>" + user_profile.company_name + "</center>"
    table_data += "<center>" + user_profile.user.username + "</center>"
    table_data += "<center>" + user_profile.location + "</center>"
    table_data += "<table style='padding-bottom: 10px;text-align:right;'><tr><th>Pending Purchase Orders till date:</th><th>" + "-".join(order_date) + "</th></tr>"
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

        temp_data['aaData'].append(OrderedDict(( ('SKU Code', data.sku_code), ('WMS Code', data.wms_code), ('SKU Group', data.sku_group),
                                    ('SKU Type', data.sku_type), ('SKU Category', data.sku_category), ('SKU Class', data.sku_class),
                                    ('Put Zone', zone), ('Threshold Quantity', data.threshold_quantity) )))

    return temp_data


def get_location_stock_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    results_data = copy.deepcopy( AJAX_DATA )
    total_quantity = 0
    search_parameters = {}
    search_mapping = {'sku_code': 'sku__sku_code__iexact', 'sku_category': 'sku__sku_category__iexact',
                      'sku_type': 'sku__sku_type__iexact', 'sku_class': 'sku__sku_class__iexact', 'zone': 'location__zone__zone__iexact',
                      'location': 'location__location__iexact', 'wms_code': 'sku__wms_code'}

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
    if search_parameters:
        stock_detail = StockDetail.objects.exclude(receipt_number=0).filter(**search_parameters)
        total_quantity = stock_detail.aggregate(Sum('quantity'))['quantity__sum']

    results_data['recordsTotal'] = len(stock_detail)
    results_data['recordsFiltered'] = len(stock_detail)

    if stop_index:
        stock_detail = stock_detail[start_index:stop_index]

    for data in stock_detail:
        results_data['aaData'].append(OrderedDict(( ('SKU Code', data.sku.sku_code), ('WMS Code', data.sku.wms_code),
                                                    ('Product Description', data.sku.sku_desc), ('Zone', data.location.zone.zone),
                                                    ('Location', data.location.location), ('Quantity', data.quantity),
                                                    ('Receipt Number', data.receipt_number),
                                                    ('Receipt Date', str(data.receipt_date).split('+')[0]) )))
    return results_data, total_quantity

def get_receipt_filter_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    search_parameters = {}
    lis = ['open_po__supplier__name', 'order_id', 'open_po__sku__wms_code', 'open_po__sku__sku_desc', 'received_quantity']
    temp_data = copy.deepcopy( AJAX_DATA )
    temp_data['draw'] = search_params.get('draw')

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    if 'from_date' in search_params:
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_parameters['creation_date__lt'] = search_params['to_date']

    if 'supplier' in search_params:
        search_parameters['open_po__supplier__id__iexact'] = search_params['supplier']
    if 'wms_code' in search_params:
        search_parameters['open_po__sku__wms_code__iexact'] = search_params['wms_code']
    if 'sku_code' in search_params:
        search_parameters['open_po__sku__sku_code__iexact'] = search_params['sku_code']

    purchase_order = []
    search_parameters['open_po__sku__user'] = user.id
    search_parameters['status__in'] = ['grn-generated', 'location-assigned', 'confirmed-putaway']
    search_parameters['open_po__sku_id__in'] = sku_master_ids

    purchase_order = PurchaseOrder.objects.filter(**search_parameters)
    if search_params.get('order_term'):
        order_data = lis[search_params['order_index']]
        if search_params['order_term'] == 'desc':
            order_data = "-%s" % order_data

        purchase_order = purchase_order.order_by(order_data)

    temp_data['recordsTotal'] = len(purchase_order)
    temp_data['recordsFiltered'] = len(purchase_order)

    if stop_index:
        purchase_order = purchase_order[start_index:stop_index]
    for data in purchase_order:
        po_reference = '%s%s_%s' %(data.prefix, str(data.creation_date).split(' ')[0].replace('-', ''), data.order_id)
        temp_data['aaData'].append(OrderedDict(( ('PO Reference', po_reference), ('WMS Code', data.open_po.sku.wms_code), ('Description', data.open_po.sku.sku_desc),
                                    ('Supplier', '%s (%s)' % (data.open_po.supplier.name, data.open_po.supplier_id)),
                                    ('Receipt Number', data.open_po_id), ('Received Quantity', data.received_quantity) )))
    return temp_data

def get_dispatch_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from miebach_admin.views import *
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    lis = ['order__order_id', 'order__sku__wms_code', 'order__sku__sku_desc', 'stock__location__location', 'picked_quantity', 'picked_quantity', 'updation_date', 'updation_date']
    temp_data = copy.deepcopy( AJAX_DATA )
    search_parameters = {}

    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['updation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date']  + datetime.timedelta(1), datetime.time())
        search_parameters['updation_date__lt'] = search_params['to_date']
    if 'wms_code' in search_params:
        search_parameters['stock__sku__wms_code'] = search_params['wms_code']
    if 'sku_code' in search_params:
        search_parameters['stock__sku__sku_code'] = search_params['sku_code']

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    search_parameters['status__contains'] = 'picked'
    search_parameters['stock__gt'] = 0
    search_parameters['order__user'] = user.id
    search_parameters['stock__sku_id__in'] = sku_master_ids

    picklist = Picklist.objects.filter(**search_parameters)
    if search_params.get('order_term'):
        order_data = lis[search_params['order_index']]
        if search_params['order_term'] == 'desc':
            order_data = "-%s" % order_data
        picklist = picklist.order_by(order_data)

    temp_data['recordsTotal'] = len(picklist)
    temp_data['recordsFiltered'] = len(picklist)

    if stop_index:
        picklist = picklist[start_index:stop_index]

    for data in picklist:
        picked_quantity = data.picked_quantity
        if data.stock.location.zone.zone == 'DEFAULT':
            picked_quantity = 0
        date = get_local_date(user, data.updation_date).split(' ')

        temp_data['aaData'].append(OrderedDict(( ('Order ID', data.order.order_id), ('WMS Code', data.stock.sku.wms_code),
                                                 ('Description', data.stock.sku.sku_desc), ('Location', data.stock.location.location),
                                                 ('Quantity', data.picked_quantity), ('Picked Quantity', picked_quantity),
                                                 ('Date', ' '.join(date[0:3])), ('Time', ' '.join(date[3:5]))  )))

    return temp_data

def sku_wise_purchase_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from itertools import chain
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    data_list = []
    received_list = []
    temp_data = copy.deepcopy( AJAX_DATA )
    search_parameters = {}

    if 'wms_code' in search_params:
        search_parameters['open_po__sku__wms_code'] = search_params['wms_code']

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    search_parameters['open_po__sku__user'] = user.id
    search_parameters['open_po__sku_id__in'] = sku_master_ids
    purchase_orders = PurchaseOrder.objects.filter(**search_parameters)
    temp_data['recordsTotal'] = len(purchase_orders)
    temp_data['recordsFiltered'] = len(purchase_orders)
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
        temp = OrderedDict(( ('PO Date', str(data.po_date).split('+')[0]), ('Supplier', order_data['supplier_name']),
                             ('SKU Code', order_data['wms_code']), ('Order Quantity', order_data['order_quantity']),
                             ('Received Quantity', data.received_quantity), ('Receipt Date', receipt_date), ('Status', status) ))
        temp['Rejected Quantity'] = 0
        rejected = QualityCheck.objects.filter(purchase_order_id=data.id, po_location__location__zone__user=user.id).\
                                        aggregate(Sum('rejected_quantity'))['rejected_quantity__sum']
        if rejected:
            temp['Rejected Quantity'] = rejected
        if status == 'Received':
            received_list.append(temp)
        else:
            data_list.append(temp)

    data_list = list(chain(data_list, received_list))
    if stop_index:
        data_list = data_list[start_index:stop_index]
    temp_data['aaData'] = list(chain(temp_data['aaData'], data_list))

    return temp_data

def get_po_filter_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    lis = ['order_id', 'open_po__supplier_id', 'open_po__supplier__name', 'received_quantity']
    search_parameters = {}
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    temp_data = copy.deepcopy( AJAX_DATA )
    temp_data['draw'] = search_params.get('draw')

    if 'from_date' in search_params:
        search_parameters['creation_date__gte'] = search_params['from_date']
    if 'to_date' in search_params:
        search_parameters['creation_date__lte'] = search_params['to_date']

    if 'open_po' in search_params and search_params['open_po']:
        temp = re.findall('\d+', search_params['open_po'])
        if temp:
            search_parameters['order_id'] = temp[-1]

    if 'wms_code' in search_params:
        search_parameters['open_po__sku__wms_code__iexact'] = search_params['wms_code']


    search_parameters['open_po__sku__user'] = user.id
    search_parameters['open_po__sku_id__in'] = sku_master_ids
    result_values = ['order_id', 'open_po__supplier_id', 'open_po__supplier_id__name', 'prefix']
    purchase_order = PurchaseOrder.objects.exclude(status='').filter(**search_parameters).values(*result_values).distinct()
    if 'order_term' not in search_params:
        search_params['order_term'] = 0
    if search_params['order_term']:
        order_data = lis[search_params['order_index']]
        if search_params['order_term'] == 'desc':
            order_data = "-%s" % order_data
        purchase_order = PurchaseOrder.objects.exclude(status='').filter(**search_parameters).order_by(order_data).\
                                               values(*result_values).distinct()

    temp_data['recordsTotal'] = len(purchase_order)
    temp_data['recordsFiltered'] = len(purchase_order)

    if stop_index:
        purchase_order = purchase_order[start_index:stop_index]

    for data in purchase_order:
        total_quantity = 0
        results = PurchaseOrder.objects.filter(order_id=data['order_id'],open_po__sku__user=user.id)
        for result in results:
            total_quantity += result.received_quantity
        po_number = '%s%s_%s' %(data['prefix'], str(result.creation_date).split(' ')[0].replace('-', ''), data['order_id'])
        temp_data['aaData'].append(OrderedDict(( ('PO Number', po_number), ('Supplier ID', data['open_po__supplier_id']),
                                                 ('Supplier Name', data['open_po__supplier_id__name']), ('Total Quantity', total_quantity),
                                                 ('DT_RowClass', 'results'), ('DT_RowAttr', {'data-id': data['order_id']}) )))
    return temp_data

def get_purchase_order_data(order):
    order_data = {}
    if 'job_code' in dir(order):
        order_data = {'wms_code': order.product_code.wms_code, 'sku_group': order.product_code.sku_group }
        return order_data
    elif order.open_po:
        open_data = order.open_po
        user_data = order.open_po.supplier
        address = user_data.address
        email_id = user_data.email_id
        username = user_data.name
        order_quantity = open_data.order_quantity
    else:
        st_order = STPurchaseOrder.objects.filter(po_id=order.id)
        st_picklist = STOrder.objects.filter(stock_transfer__st_po_id=st_order[0].id)
        open_data = st_order[0].open_st
        user_data = UserProfile.objects.get(user_id=st_order[0].open_st.warehouse_id)
        address = user_data.location
        email_id = user_data.user.email
        username = user_data.user.username
        order_quantity = open_data.order_quantity


    order_data = {'order_quantity': order_quantity, 'price': open_data.price, 'wms_code': open_data.sku.wms_code,
                  'sku_code': open_data.sku.wms_code, 'supplier_id': user_data.id, 'zone': open_data.sku.zone,
                  'qc_check': open_data.sku.qc_check, 'supplier_name': username,
                  'sku_desc': open_data.sku.sku_desc, 'address': address,
                  'phone_number': user_data.phone_number, 'email_id': email_id,
                  'sku_group': open_data.sku.sku_group, 'sku_id': open_data.sku.id, 'sku': open_data.sku }

    return order_data

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
    extra_headers =  list(ProductionStages.objects.filter(**stage_filter).order_by('order').values_list('stage_name', flat=True))
    job_order = JobOrder.objects.filter(product_code__user=user.id, status__in=['grn-generated', 'pick_confirm', 'partial_pick'])

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

    sku_master = StockDetail.objects.exclude(receipt_number=0).values_list('sku_id', 'sku__sku_code', 'sku__sku_desc', 'sku__sku_brand',
                                              'sku__sku_category').distinct().annotate(total=Sum('quantity')).filter(quantity__gt=0,
                                              **search_parameters)
    if search_stage and not search_stage == 'In Stock':
        sku_master = []
    wms_codes = map(lambda d: d[0], sku_master)
    sku_master1 = job_order.exclude(product_code_id__in=wms_codes).filter(**job_filter).values_list('product_code_id', 'product_code__sku_code',
                                     'product_code__sku_desc', 'product_code__sku_brand', 'product_code__sku_category').distinct()
    sku_master = list(chain(sku_master, sku_master1))

    purchase_orders = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']).filter(open_po__sku__user=user.id).\
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
        status_track = status_tracking.filter(status_id__in=job_ids).values('status_value').distinct().annotate(total=Sum('quantity'))

        tracking = dict(zip(map(lambda d: d.get('status_value', ''), status_track), map(lambda d: d.get('total', '0'), status_track)))
        for head in extra_headers:
            quantity = tracking.get(head, 0)
            if quantity:
                sku_stages_dict[head] = tracking.get(head, 0)
        for key, value in sku_stages_dict.iteritems():
            sku_master_list.append(OrderedDict(( ('SKU Code', sku[1]), ('Description', sku[2]),
                                                 ('Brand', sku[3]), ('Category', sku[4]),
                                                 ('Stage', key), ('Stage Quantity', value) )))

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
    all_data = OrderedDict()
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
    extra_headers =  list(ProductionStages.objects.filter(**stage_filter).order_by('order').values_list('stage_name', flat=True))
    job_orders = JobOrder.objects.filter(product_code__user=user.id, status__in=['grn-generated', 'pick_confirm', 'partial_pick',
                                         'location-assigned', 'confirmed-putaway'], **search_parameters)
    job_code_ids = job_orders.values('job_code', 'id').distinct()
    job_ids = map(lambda d: d['id'], job_code_ids)
    status_filter = {'status_tracking__status_type': 'JO', 'processed_stage__in': extra_headers,
                     'status_tracking__status_id__in': job_ids}
    if 'from_date' in search_params:
        status_filter['creation_date__gte'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
    if 'to_date' in search_params:
        status_filter['creation_date__lte'] = datetime.datetime.combine(search_params['to_date']  + datetime.timedelta(1), datetime.time())
    status_summary = StatusTrackingSummary.objects.filter(**status_filter)

    job_order_ids = job_orders.values_list('job_code', flat=True).distinct()

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    for summary in status_summary:
        job_order = job_orders.get(id=summary.status_tracking.status_id)
        summary_date = get_local_date(user, summary.creation_date).split(' ')
        summary_date = ' '.join(summary_date[0:3])
        jo_creation_date = get_local_date(user, job_order.creation_date).split(' ')
        jo_creation_date = ' '.join(jo_creation_date[0:3])
        cond = (summary_date, job_order.job_code, jo_creation_date, job_order.product_code.sku_class, job_order.product_code.sku_code,
                job_order.product_code.sku_brand,job_order.product_code.sku_category, job_order.product_quantity, summary.processed_stage)
        all_data.setdefault(cond, 0)
        all_data[cond] += float(summary.processed_quantity)
        #job_code = filter(lambda job_code_ids: job_code_ids['id'] == summary.status_tracking.status_id, job_code_ids)

    data = []
    temp_data['recordsTotal'] = len(all_data.keys())
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    order_term = search_params.get('order_term', '')
    order_index = search_params.get('order_index', '')

    all_data_keys = all_data.keys()
    for key in all_data_keys:
        data.append(OrderedDict(( ('Date', key[0]), ('Job Order', key[1]), ('JO Creation Date', key[2]), ('SKU Class', key[3]),
                                  ('SKU Code', key[4]), ('Brand', key[5]), ('SKU Category', key[6]), ('Total JO Quantity', key[7]),
                                  ('Reduced Quantity', all_data[key]),('Stage', key[8])
                   )))

    if order_term == 'asc' and order_index:
        data = sorted(data, key=itemgetter(data[0].keys()[order_index]))
    elif order_index or (order_index == 0 and order_term == 'desc'):
        data = sorted(data, key=itemgetter(data[0].keys()[order_index]), reverse=True)

    temp_data['aaData'] = data
    if stop_index:
        temp_data['aaData'] = data[start_index:stop_index]

    return temp_data


def get_openjo_details(search_params, user, sub_user):
    from miebach_admin.models import *
    from miebach_admin.views import *
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    lis = ['jo_id', 'jo_creation_date', 'sku__brand', 'sku__sku_category', 'sku__sku_class', 'sku__sku_code', 'stage', 'quantity']
    temp_data = copy.deepcopy( AJAX_DATA )
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
        jos = JobOrder.objects.filter(**search_parameters).exclude(status = 'confirmed-putaway')
        if search_params['stage'] == 'Putaway pending':
            jos = jos.filter(status__in = ['location-assigned', 'grn-generated'])
        elif search_params['stage'] == 'Picklist Generated':
            jos = jos.filter(status = 'picklist_gen')
        elif search_params['stage'] == 'Created':
            jos = jos.filter(status__in = ['open', 'order-confirmed'])
        elif search_params['stage'] == 'Partially Picked':
            jos = jos.filter(status = 'partial_pick')
        elif search_params['stage'] == 'Picked':
            jos = jos.filter(status = 'pick_confirm')
        else:
            jos = jos.filter(status = 'pick_confirm')
            jos = list(jos.filter(**search_parameters).values_list('id', flat=True))
            jos = StatusTracking.objects.filter(status_id__in = jos, status_value = search_params['stage'], status_type='JO').values_list('status_id', flat=True)
            jos = JobOrder.objects.filter(id__in=jos)
    else:
        jos = JobOrder.objects.filter(**search_parameters).exclude(status = 'confirmed-putaway')

    for data in jos:
        if (data.status == 'open') or (data.status == 'order-confirmed'):
            stage = 'Created'
            quantity = data.product_quantity
            final_data.append({'stage': stage, 'quantity': quantity, 'data': data})
        elif data.status == 'picklist_gen':
            stage = 'Picklist Generated'
            quantity = data.product_quantity
            final_data.append({'stage': stage, 'quantity': quantity, 'data': data})
        elif (data.status == 'location-assigned') or (data.status == 'grn-generated'):
            stage = 'Putaway pending'
            quantity = data.product_quantity
            final_data.append({'stage': stage, 'quantity': quantity, 'data': data})
        elif (data.status == 'pick_confirm'):
            stages_list = StatusTracking.objects.filter(status_id = data.id).values_list('original_quantity', 'status_value')
            if 'stage' in search_params:
                stages_list = StatusTracking.objects.filter(status_id = data.id, status_value = search_params['stage']).values_list('original_quantity', 'status_value')
            if stages_list:
                for sing_stage in stages_list:
                    stage = sing_stage[1]
                    quantity = sing_stage[0]
                    final_data.append({'stage': stage, 'quantity': quantity, 'data': data})
            else:
                stage = 'Picked'
                quantity = data.product_quantity
                final_data.append({'stage': stage, 'quantity': quantity, 'data': data})
        elif (data.status == 'partial_pick'):
            MaterialPicklist.objects.filter(jo_material__job_order__job_code= data.id)
            stage = 'Partially Picked'
            quantity = data.product_quantity
            final_data.append({'stage': stage, 'quantity': quantity, 'data': data})

    temp_data['recordsTotal'] = len(final_data)
    temp_data['recordsFiltered'] = len(final_data)

    order_term = search_params.get('order_term', '')
    order_index = search_params.get('order_index', '')

    last_data = []
    for one_data in final_data:
        date = get_local_date(user, one_data['data'].creation_date).split(' ')
        last_data.append(OrderedDict(( ('JO Code', one_data['data'].job_code), ('Jo Creation Date', ' '.join(date[0:3])),
                                                 ('SKU Brand', one_data['data'].product_code.sku_brand),
                                                 ('SKU Category', one_data['data'].product_code.sku_category),
                                                 ('SKU Class', one_data['data'].product_code.sku_class),
                                                 ('SKU Code', one_data['data'].product_code.sku_code),
                                                 ('Stage', one_data['stage']), ('Quantity', one_data['quantity']))  ))

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
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    lis = ['creation_date', 'order_id', 'customer_name' ,'sku__sku_brand', 'sku__sku_category', 'sku__sku_class', 'sku__sku_size', 'sku__sku_desc', 'sku_code', 'quantity', 'sku__mrp', 'sku__mrp', 'sku__mrp', 'sku__discount_percentage', 'city', 'state', 'marketplace', 'invoice_amount', 'order_id'];
    #lis = ['order_id', 'customer_name', 'sku__sku_code', 'sku__sku_desc', 'quantity', 'updation_date', 'updation_date', 'marketplace']
    temp_data = copy.deepcopy( AJAX_DATA )
    search_parameters = {}

    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date']  + datetime.timedelta(1), datetime.time())
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

    status_search = search_params.get('order_report_status', "")

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    search_parameters['quantity__gt'] = 0
    search_parameters['user'] = user.id
    search_parameters['sku_id__in'] = sku_master_ids

    orders = OrderDetail.objects.filter(**search_parameters)

    open_orders =  OrderDetail.objects.filter(status=1,user=user.id).values_list('order_id', flat = True).distinct()

    picklist_generated = Picklist.objects.filter(order__user= user.id, status__icontains='open', picked_quantity=0).values_list('order__order_id', flat = True).distinct()

    partially_picked =  Picklist.objects.filter(order__user= user.id, status__icontains='open', picked_quantity__gt=0, reserved_quantity__gt=0).values_list('order__order_id', flat=True).distinct()

    picked_orders = Picklist.objects.filter(order__user= user.id, status__icontains='picked', picked_quantity__gt=0, reserved_quantity=0).values_list('order__order_id', flat=True).distinct()

    order_ids = OrderDetail.objects.filter(status=1,user= user.id).values_list('order_id', flat=True).distinct()
    partial_generated = Picklist.objects.filter(order__user= user.id, order__order_id__in=order_ids).values_list('order__order_id', flat=True).distinct()

    _status = ""
    if status_search:
       #['Open', 'Picklist generated', 'Partial Picklist generated', 'Picked', 'Partially picked'] 
        ord_ids = ""
        if status_search == 'Open':
            ord_ids = open_orders
        elif status_search == 'Picklist generated':
            ord_ids = picklist_generated
        elif status_search == 'Partial Picklist generated':
            ord_ids = partially_picked
        elif status_search == 'Picked':
            ord_ids = picked_orders
        elif status_search == 'Partially picked':
            ord_ids = partial_generated

        if ord_ids:
            orders = orders.filter(order_id__in  = ord_ids)
        _status = status_search

    if search_params.get('order_term'):
        order_data = lis[search_params['order_index']]
        if search_params['order_term'] == 'desc':
            order_data = "-%s" % order_data
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


    for data in orders:
        date = get_local_date(user, data.creation_date).split(' ')
        order_id = str(data.order_code) + str(data.order_id)
        if data.original_order_id:
            order_id = data.original_order_id

        #['Open', 'Picklist generated', 'Partial Picklist generated', 'Picked', 'Partially picked']
        if not _status:
            if data.order_id in open_orders:
                status = ORDER_SUMMARY_REPORT_STATUS[0]
            elif data.order_id in picklist_generated:
                status = ORDER_SUMMARY_REPORT_STATUS[1]
            elif data.order_id in partially_picked:
                status = ORDER_SUMMARY_REPORT_STATUS[2]
            elif data.order_id in picked_orders:
                status = ORDER_SUMMARY_REPORT_STATUS[3]
            if data.order_id in partial_generated:
                status = ORDER_SUMMARY_REPORT_STATUS[4]
        else:
            status = _status

        tax = 0
        vat = 5.5
        discount = 0
        mrp_price = data.sku.mrp
        order_summary = CustomerOrderSummary.objects.filter(order__user=user.id, order_id=data.id)
        if order_summary:
            tax = order_summary[0].tax_value
            vat = order_summary[0].vat
            mrp_price = order_summary[0].mrp
            discount = order_summary[0].discount
        else:
            tax = float(float(data.invoice_amount)/100) * vat

        unit_price = ((float(data.invoice_amount)/ float(data.quantity))) - discount - (tax/float(data.quantity))
        unit_price = "%.2f" % unit_price



        temp_data['aaData'].append( OrderedDict(( ('Order Date', ''.join(date[0:3])), ('Order ID', order_id), ('Customer Name', data.customer_name), ('SKU Brand', data.sku.sku_brand),  ('SKU Category', data.sku.sku_category), ('SKU Class', data.sku.sku_class), ('SKU Size', data.sku.sku_size), ('SKU Description', data.sku.sku_desc), ('SKU Code', data.sku.sku_code), ('Order Qty', int(data.quantity)),  ('MRP', int(data.sku.mrp)), ('Unit Price', unit_price), ('Discount', data.sku.discount_percentage), ('City', data.city), ('State', data.state), ('Marketplace', data.marketplace), ('Invoice Amount', data.invoice_amount), ('Price', data.sku.price), ('Status', status) )) )

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
