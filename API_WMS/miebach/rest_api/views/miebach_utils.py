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

SUB_CATEGORIES = {'round_neck': 'ROUND NECK', 'v_neck': 'V NECK', 'polo': 'POLO', 'chinese_collar': 'CHINESE COLLAR', 'henley': 'HENLEY'}

DECLARATIONS = {'default': 'We declare that this invoice shows actual price of the goods described inclusive of taxes and that all particulars are true and correct.',
                'TranceHomeLinen': 'Certify that the particulars given above are true and correct and the amount indicated represents the price actually charged and that there is no flow of additional consideration directly or indirectly.\n Subject to Banglore Jurisdication'}

PERMISSION_KEYS =['add_qualitycheck', 'add_skustock', 'add_shipmentinfo', 'add_openpo', 'add_orderreturns', 'add_openpo', 'add_purchaseorder',
                  'add_joborder', 'add_materialpicklist', 'add_polocation', 'add_stockdetail', 'add_cyclecount', 'add_inventoryadjustment',
                  'add_orderdetail', 'add_picklist']
LABEL_KEYS = ["MASTERS_LABEL", "INBOUND_LABEL", "PRODUCTION_LABEL", "STOCK_LABEL", "OUTBOUND_LABEL", "SHIPMENT_LABEL", "OTHERS_LABEL",
                "PAYMENT_LABEL"]

SKU_DATA = {'user': '', 'sku_code': '', 'wms_code': '',
            'sku_desc': '', 'sku_group': '', 'sku_type': '', 'mix_sku': '',
            'sku_category': '', 'sku_class': '', 'threshold_quantity': 0, 'color': '', 'mrp': 0,
            'status': 1, 'online_percentage': 0, 'qc_check': 0, 'sku_brand': '', 'sku_size': '', 'style_name': '', 'price': 0,
             'ean_number': 0, 'load_unit_handle': 'unit', 'zone_id': None, 'hsn_code': 0, 'product_type': '',
             'ean_number': 0, 'load_unit_handle': 'unit', 'zone_id': None, 'hsn_code': 0, 'product_type': ''}

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
                        'Completed': 'cmpltd', 'Approved': 'approved', 'Disapproved': 'disapproved'}


RAISE_PO_FIELDS1 = OrderedDict([('WMS Code *','wms_code'), ('Supplier Code', 'supplier_code'), ('Quantity *','order_quantity'),('Price','price')])

MOVE_INVENTORY_FIELDS = ( (('WMS Code *','wms_code'),('Source Location *','source_loc')),
                          (('Destination Location *','dest_loc'),('Quantity *','quantity')), )

ADJUST_INVENTORY_FIELDS = ( (('WMS Code *','wms_code'),('Location *','location')),
                            (('Physical Quantity *','quantity'),('Reason','reason')),)

MOVE_INVENTORY_UPLOAD_FIELDS = ['WMS Code', 'Source Location', 'Destination Location', 'Quantity']

SUPPLIER_HEADERS = ['Supplier Id', 'Supplier Name', 'Address', 'Email', 'Phone No.', 'GSTIN Number', 'PAN Number', 'PIN Code',
                    'City', 'State', 'Country']

VENDOR_HEADERS = ['Vendor Id', 'Vendor Name', 'Address', 'Email', 'Phone No.']

CUSTOMER_HEADERS = ['Customer Id', 'Customer Name', 'Credit Period', 'CST Number', 'TIN Number', 'PAN Number', 'Email', 'Phone No.',
                    'City', 'State', 'Country', 'Pin Code', 'Address', 'Selling Price Type', 'Tax Type(Options: Inter State, Intra State)',
                    'Margin Percentage']

CUSTOMER_EXCEL_MAPPING = OrderedDict(( ('customer_id', 0), ('name', 1), ('credit_period', 2), ('cst_number', 3), ('tin_number', 4),
                                       ('pan_number', 5), ('email_id', 6), ('phone_number', 7), ('city', 8), ('state', 9), ('country', 10),
                                       ('pincode', 11), ('address', 12), ('price_type', 13), ('tax_type', 14), ('margin', 15)
                                    ))

MARKETPLACE_CUSTOMER_EXCEL_MAPPING = OrderedDict(( ('customer_id', 0), ('phone', 1), ('name', 2), ('address', 3), ('pincode', 4), ('city', 5), ('tin', 6)
                                                ))

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

# User Type Order Formats
ORDER_HEADERS = ['Order ID', 'Title', 'SKU Code', 'Quantity','Shipment Date(yyyy-mm-dd)', 'Channel Name', 'Customer ID', 'Customer Name', 'Email ID', 'Phone Number', 'Shipping Address', 'State', 'City', 'PIN Code', 'Invoice Amount(Without Tax and Discount)', 'Total Discount', 'CGST(%)', 'SGST(%)', 'IGST(%)']

MARKETPLACE_ORDER_HEADERS = ['SOR ID', 'UOR ID', 'Seller ID', 'Order Status', 'Title', 'SKU Code', 'Quantity','Shipment Date(yyyy-mm-dd)', 'Channel Name', 'Customer ID', 'Customer Name', 'Email ID', 'Phone Number', 'Shipping Address', 'State', 'City', 'PIN Code', 'Invoice Amount(Without Tax and Discount)', 'Total Discount', 'CGST(%)', 'SGST(%)', 'IGST(%)']

USER_ORDER_EXCEL_MAPPING = {'warehouse_user': ORDER_HEADERS, 'marketplace_user': MARKETPLACE_ORDER_HEADERS, 'customer': ORDER_HEADERS}

# User Type Order Excel Mapping

ORDER_DEF_EXCEL = OrderedDict(( ('order_id', 0), ('title', 1), ('sku_code', 2), ('quantity', 3), ('shipment_date', 4),
                                ('channel_name', 5), ('shipment_check', 'true'), ('customer_id', 6), ('customer_name', 7), ('email_id', 8),
                                ('telephone', 9), ('address', 10), ('state', 11), ('city', 12), ('pin_code', 13),
                                ('amount', 14), ('amount_discount', 15), ('cgst_tax', 16), ('sgst_tax', 17), ('igst_tax', 18)
                             ))

MARKETPLACE_ORDER_DEF_EXCEL = OrderedDict(( ('sor_id', 0), ('order_id', 1), ('seller', 2), ('order_status', 3), ('title', 4),
                                            ('sku_code', 5), ('quantity', 6), ('shipment_date', 7), ('channel_name', 8),
                                            ('shipment_check', 'true'), ('customer_id', 9),
                                            ('customer_name', 10), ('email_id', 11), ('telephone', 12), ('address', 13),
                                            ('state', 14), ('city', 15), ('pin_code', 16), ('amount', 17),
                                            ('amount_discount', 18), ('cgst_tax', 19), ('sgst_tax', 20), ('igst_tax', 21)
                             ))

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
'type': 'date'}, {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'}, {'label': 'Marketplace', 'name': 'marketplace', 'type': 'select'}, {'label': 'City', 'name': 'city', 'type': 'input'}, {'label': 'State', 'name': 'state', 'type': 'input'}, {'label': 'SKU Category', 'name': 'sku_category', 'type': 'select'}, {'label': 'SKU Brand', 'name': 'brand', 'type': 'input'}, {'label': 'SKU Class', 'name': 'sku_class', 'type': 'input'}, {'label': 'SKU Size', 'name': 'sku_size', 'type': 'input'}, {'label': 'Status', 'name': 'order_report_status', 'type': 'select'}, {'label': 'Order ID', 'name': 'order_id', 'type': 'input'}],
                        'dt_headers': ['Order Date', 'Order ID', 'Customer Name' ,'SKU Brand', 'SKU Category', 'SKU Class', 'SKU Size', 'SKU Description', 'SKU Code', 'Order Qty', 'Unit Price', 'Price', 'MRP', 'Discount', 'City', 'State', 'Marketplace', 'Invoice Amount', 'Status', 'Order Status', 'Remarks'],
                      'dt_url': 'get_order_summary_filter', 'excel_name': 'order_summary_report', 'print_url': 'print_order_summary_report',
                     }

OPEN_JO_REP_DICT = {'filters': [{'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'}, {'label': 'SKU Class','name': 'class',
                                 'type': 'input'}, {'label': 'SKU Category', 'name': 'category','type': 'select'}, {'label': 'SKU Brand',
                                 'name': 'brand', 'type': 'select'}, {'label': 'JO Code','name': 'job_code', 'type': 'input'},
                                 {'label': 'Stages', 'name': 'stage', 'type': 'select'}],
                    'dt_headers': ['JO Code', 'Jo Creation Date', 'SKU Brand', 'SKU Category', 'SKU Class', 'SKU Code', 'Stage', 'Quantity'],
                    'dt_url': 'get_openjo_report_details', 'excel_name': 'open_jo_report', 'print_url': 'print_open_jo_report',
                   }

SKU_WISE_PO_DICT = {'filters': [{'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'}],
                    'dt_headers': ['PO Date', 'Supplier', 'SKU Code', 'Order Quantity', 'Received Quantity', 'Rejected Quantity', 'Receipt Date', 'Status'],
                    'mk_dt_headers': ['PO Date', 'PO Number', 'Supplier ID', 'Supplier Name', 'Recepient',  'SKU Code', 'SKU Description', 'SKU Class', 'SKU Style Name', 'SKU Brand', 'SKU Category', 'PO Qty', 'Unit Rate', 'Pre-Tax PO Amount', 'Tax', 'After Tax PO Amount', 'Qty received', 'Status'],
                    'dt_url': 'get_sku_purchase_filter', 'excel_name': 'sku_wise_purchases', 'print_url': 'print_sku_wise_purchase',
                   }

GRN_DICT = {'filters': [{'label': 'From Date', 'name': 'from_date', 'type': 'date'}, {'label': 'To Date', 'name': 'to_date','type': 'date'},
                        {'label': 'PO Number', 'name': 'open_po', 'type': 'input'}, {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'}],
            'dt_headers': ['PO Number', 'Supplier ID', 'Supplier Name', 'Total Quantity'],
            'mk_dt_headers': ['Received Date', 'PO Date', 'PO Number', 'Supplier ID', 'Supplier Name', 'Recepient', 'SKU Code',
                              'SKU Description', 'SKU Class', 'SKU Style Name', 'SKU Brand', 'SKU Category', 'Received Qty', 'Unit Rate',
                              'Pre-Tax Received Value', 'CGST(%)', 'SGST(%)', 'IGST(%)', 'UTGST(%)','Post-Tax Received Value',
                              'Margin %', 'Margin', 'Invoiced Unit Rate', 'Invoiced Total Amount'],
            'dt_url': 'get_po_filter', 'excel_name': 'goods_receipt', 'print_url': '',
                     }

SELLER_INVOICE_DETAILS_DICT = {
            'filters': [{'label': 'From Date', 'name': 'from_date', 'type': 'date'}, {'label': 'To Date', 'name': 'to_date','type': 'date'},
                        {'label': 'SKU Code', 'name': 'sku_code', 'type': 'sku_search'}],
            'dt_headers': ['Date', 'Supplier', 'Seller ID', 'Seller Name',  'SKU Code', 'SKU Description', 'SKU Class', 'SKU Style Name', 'SKU Brand', 'SKU Category', 'Accepted Qty', 'Rejected Qty', 'Total Qty', 'Amount', 'Tax', 'Total Amount'],
            'dt_url': 'get_seller_invoices_filter', 'excel_name': 'seller_invoices_filter', 'print_url': 'print_seller_invoice_report',
                              }

REPORT_DATA_NAMES = {'order_summary_report': ORDER_SUMMARY_DICT, 'open_jo_report': OPEN_JO_REP_DICT, 'sku_wise_po_report': SKU_WISE_PO_DICT,
                     'grn_report': GRN_DICT, 'seller_invoice_details': SELLER_INVOICE_DETAILS_DICT}

SKU_WISE_STOCK = {('sku_wise_form','skustockTable','SKU Wise Stock Summary','sku-wise', 1, 2, 'sku-wise-report') : (['SKU Code', 'WMS Code', 'Product Description', 'SKU Category', 'Total Quantity'],( (('SKU Code', 'sku_code'), ('SKU Category', 'sku_category')), (('SKU Type', 'sku_type'), ('SKU Class', 'sku_class')),(('WMS Code','wms_code'),))),}

SKU_WISE_PURCHASES =  {('sku_wise_purchase','skupurchaseTable','SKU Wise Purchase Orders','sku-purchase-wise', 1, 2, 'sku-wise-purchase-report') : (['PO Date', 'Supplier', 'SKU Code', 'Order Quantity', 'Received Quantity', 'Receipt Date', 'Status'],( (('WMS SKU Code', 'wms_code'),),)),}

SALES_RETURN_REPORT = {('sales_return_form','salesreturnTable','Sales Return Reports','sales-report', 1, 2, 'sales-return-report') : (['SKU Code', 'Order ID', 'Customer ID', 'Return Date', 'Status', 'Quantity'],( (('SKU Code', 'sku_code'), ('WMS Code', 'wms_code')), (('Order ID', 'order_id'), ('Customer ID', 'customer_id')),(('Date','creation_date'),))),}

LOCATION_HEADERS = ['Zone', 'Location', 'Capacity', 'Put sequence', 'Get sequence', 'SKU Group']

SKU_HEADERS = ['WMS Code','SKU Description', 'Product Type', 'SKU Group', 'SKU Type(Options: FG, RM)', 'SKU Category', 'SKU Class',
               'SKU Brand', 'Style Name', 'SKU Size', 'Size Type', 'Put Zone', 'Price', 'MRP Price', 'Sequence', 'Image Url',
               'Threshold Quantity', 'Measurment Type', 'Sale Through', 'Color', 'EAN Number',
               'Load Unit Handling(Options: Enable, Disable)', 'HSN Code', 'Sub Category', 'Status']

MARKET_USER_SKU_HEADERS = ['WMS Code','SKU Description', 'Product Type', 'SKU Group', 'SKU Type(Options: FG, RM)', 'SKU Category',
                           'SKU Class', 'SKU Brand', 'Style Name', 'Mix SKU Attribute(Options: No Mix, Mix within Group)', 'Put Zone',
                           'Price', 'MRP Price', 'Sequence', 'Image Url','Threshold Quantity', 'Measurment Type', 'Sale Through',
                           'Color', 'EAN Number', 'HSN Code', 'Status']

SALES_RETURNS_HEADERS = ['Return ID', 'Order ID', 'SKU Code', 'Return Quantity', 'Damaged Quantity', 'Return Date(YYYY-MM-DD)']

EXCEL_HEADERS = ['Receipt Number', 'Receipt Date(YYYY-MM-DD)',  'WMS SKU', 'Location', 'Quantity', 'Receipt Type']
EXCEL_RECORDS = ('receipt_number', 'receipt_date', 'wms_code', 'location', 'wms_quantity', 'receipt_type')

SKU_EXCEL = ('wms_code', 'sku_desc', 'sku_group', 'sku_type', 'sku_category', 'sku_class', 'sku_brand', 'style_name', 'sku_size', 'zone_id',
             'threshold_quantity', 'status')

PICKLIST_FIELDS = { 'order_id': '', 'picklist_number': '', 'reserved_quantity': '', 'picked_quantity': 0, 'remarks': '', 'status': 'open'}
PICKLIST_HEADER = ('ORDER ID', 'WMS Code', 'Title', 'Zone', 'Location', 'Reserved Quantity', 'Picked Quantity')

PRINT_OUTBOUND_PICKLIST_HEADERS = ('WMS Code', 'Title', 'Category', 'Zone', 'Location', 'Reserved Quantity', 'Picked Quantity')

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

TAX_MASTER_HEADER = OrderedDict([('Product Type', 'product_type'), ('Creation Date', 'creation_date')])

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

# Configurations
PICKLIST_OPTIONS = {'Scan SKU': 'scan_sku', 'Scan SKU Location': 'scan_sku_location', 'Scan Serial': 'scan_serial', 'Scan Label': 'scan_label',
                    'Scan None': 'scan_none'}

BARCODE_OPTIONS = {'SKU Code': 'sku_code', 'Embedded SKU Code in Serial': 'sku_serial', 'EAN Number': 'sku_ean'}

REPORTS_DATA = {'SKU List': 'sku_list', 'Location Wise SKU': 'location_wise_stock', 'Receipt Summary': 'receipt_note', 'Dispatch Summary': 'dispatch_summary', 'SKU Wise Stock': 'sku_wise'}

SKU_CUSTOMER_FIELDS = ( (('Customer ID *', 'customer_id',60), ('Customer Name *', 'customer_name',256)),
                        (('SKU Code *','sku_code'), ('Price *', 'price'), ) )

CUSTOMER_SKU_DATA = {'customer_id': '', 'sku_id': '', 'price': 0, 'customer_sku_code': ''}

CUSTOMER_SKU_MAPPING_HEADERS = OrderedDict([('Customer ID','customer__customer_id'),('Customer Name','customer__name'),
                                            ('SKU Code','sku__sku_code'),('Price','price')])


ADD_USER_DICT = {'username': '', 'first_name': '', 'last_name': '', 'password': '', 'email': ''}

ADD_WAREHOUSE_DICT = {'user_id': '', 'city': '', 'is_active': 1, 'country': '', u'state': '', 'pin_code': '', 'address': '',
                      'phone_number': '', 'prefix': '', 'location': ''}

PICKLIST_EXCEL = OrderedDict(( ('WMS Code', 'wms_code'), ('Title', 'title'), ('Category', 'category'), ('Zone', 'zone'),
                               ('Location', 'location'),
                               ('Reserved Quantity', 'reserved_quantity'), ('Stock Left', 'stock_left'),
                               ('Last Picked Location', 'last_picked_locs')
                            ))

#Campus Sutra
SHOPCLUES_EXCEL = {'original_order_id': 0, 'order_id': 0, 'quantity': 14, 'title': 7, 'invoice_amount': 46, 'address': 10,
                   'customer_name': 9, 'marketplace': 'Shopclues', 'sku_code': 19}

#SHOPCLUES_EXCEL1 = {'order_id': 0, 'quantity': 13, 'title': 6, 'invoice_amount': 45, 'address': 9, 'customer_name': 8,
#                    'marketplace': 'Shopclues', 'sku_code': 48}

VOONIK_EXCEL = {'order_id': 0, 'sku_code': 1, 'invoice_amount': 4, 'marketplace': 'Voonik'}

FLIPKART_EXCEL = {'order_id': 6, 'quantity': 14, 'title': 2, 'invoice_amount': 17, 'address': 22, 'customer_name': 21,
                  'marketplace': 'Flipkart', 'sku_code': 8}

FLIPKART_EXCEL1 = {'order_id': 6, 'quantity': 14, 'title': 2, 'invoice_amount': 16, 'address': 21, 'customer_name': 20,
                  'marketplace': 'Flipkart', 'sku_code': 8}

#Trance Home
FLIPKART_EXCEL2 = {'original_order_id': 3, 'order_id': 3, 'quantity': 17, 'title': 9, 'invoice_amount': 14, 'address': 21, 'customer_name': 19,
                   'marketplace': 'Flipkart', 'sku_code': 8}

#Campus Sutra
FLIPKART_EXCEL3 = {'original_order_id': 2,'order_id': 2, 'quantity': 17, 'title': 15, 'invoice_amount': 5, 'address': 21, 'customer_name': 20,
                   'marketplace': 'Flipkart', 'sku_code': 14}

FLIPKART_EXCEL4 = {'original_order_id': 2, 'order_id': 2, 'quantity': 19, 'title': 17, 'invoice_amount': 7, 'address': 23, 'customer_name': 22,
                   'marketplace': 'Flipkart', 'sku_code': 16}

#Campus Sutra
PAYTM_EXCEL = {'original_order_id': 0, 'order_id': 0, 'quantity': 9, 'title': 5, 'unit_price': 8, 'address': 12, 'customer_name': 10,
               'marketplace': 'Paytm', 'sku_code': 3}

FYND_EXCEL = {'original_order_id': 1, 'order_id': 1, 'title': 4, 'unit_price': 7, 'address': 16, 'customer_name': 14,
               'marketplace': 'Fynd', 'sku_code': 9}

#PAYTM_EXCEL2 = {'order_id': 13, 'quantity': 10, 'title': 1, 'invoice_amount': 9, 'address': 22, 'customer_name': 18, 'marketplace': 'Paytm',
#                'sku_code': 3}

FLIPKART_FA_EXCEL = {'original_order_id': 1, 'order_id': 1, 'quantity': 13, 'title': 8, 'invoice_amount': 9, 'address': 20, 'customer_name': 29,
                     'marketplace': 'Flipkart FA', 'sku_code': 7}

SNAPDEAL_EXCEL = {'original_order_id': 3, 'order_id': 3, 'title': 1, 'invoice_amount': 13, 'customer_name': 8, 'marketplace': 'Snapdeal',
                  'sku_code': 4, 'shipment_date': 17}

SNAPDEAL_EXCEL1 = {'order_id': 3, 'title': 2, 'invoice_amount': 14, 'customer_name': 9, 'marketplace': 'Snapdeal', 'sku_code': 5,
                  'shipment_date': 8}

AMAZON_FA_EXCEL = {'title': 4, 'invoice_amount': 14, 'marketplace': 'Amazon FA', 'sku_code': 3, 'quantity': 7}

SNAPDEAL_FA_EXCEL = {'title': 4, 'invoice_amount': 6, 'marketplace': 'Snapdeal FA', 'sku_code': 3, 'quantity': 5}

EASYOPS_ORDER_EXCEL = {'order_id': 1, 'quantity': 9, 'invoice_amount': 3, 'channel_name': 5, 'sku_code': 8, 'title': 7, 'status': 4,
                       'split_order_id': 1}

# SKU Master Upload Templates
SKU_DEF_EXCEL = OrderedDict(( ('wms_code', 0), ('sku_desc', 1), ('product_type', 2), ('sku_group', 3), ('sku_type', 4),
                              ('sku_category', 5), ('sku_class', 6), ('sku_brand', 7), ('style_name', 8), ('sku_size', 9),
                              ('size_type', 10), ('zone_id', 11), ('price', 12),
                              ('mrp', 13), ('sequence', 14), ('image_url', 15), ('threshold_quantity', 16), ('measurement_type', 17),
                              ('sale_through', 18), ('color', 19), ('ean_number', 20), ('load_unit_handle', 21), ('hsn_code', 22),
                              ('sub_category', 23), ('status', 24)
                           ))

MARKETPLACE_SKU_DEF_EXCEL = OrderedDict(( ('wms_code', 0), ('sku_desc', 1), ('product_type', 2), ('sku_group', 3), ('sku_type', 4),
                                          ('sku_category', 5), ('sku_class', 6), ('sku_brand', 7), ('style_name', 8), ('mix_sku', 9),
                                          ('zone_id', 10), ('price', 11), ('mrp', 12), ('sequence', 13), ('image_url', 14),
                                          ('threshold_quantity', 15), ('measurement_type', 16), ('sale_through', 17), ('color', 18),
                                          ('ean_number', 19), ('hsn_code', 20), ('status', 21)
                           ))

ITEM_MASTER_EXCEL = OrderedDict(( ('wms_code', 1), ('sku_desc', 2), ('sku_category', 25), ('image_url', 18), ('sku_size', 14) ))

SHOTANG_SKU_MASTER_EXCEL = OrderedDict(( ('wms_code', 2), ('sku_desc', 3), ('color', 4), ('sku_brand', 7), ('sku_category', 8) ))

# End of SKU Master U[pload templates

# Order File Upload Templates
INDIA_TIMES_EXCEL = {'order_id': 2, 'invoice_amount': 16, 'address': 8, 'customer_name': 7,
                     'marketplace': 'Indiatimes', 'sku_code': 15, 'telephone': 12}

HOMESHOP18_EXCEL = {'order_id': 0, 'invoice_amount': 10, 'address': 18, 'customer_name': 4, 'marketplace': 'HomeShop18',
                    'title': 6, 'sku_code': 8, 'quantity': 9, 'telephone': 22}

AMAZON_EXCEL = {'order_id': 1, 'address': [17,18,19], 'customer_name': 8, 'marketplace': 'Amazon',
                'title': 11, 'sku_code': 10, 'quantity': 12, 'telephone': 9, 'email_id': 7}

#AMAZON_EXCEL1 = {'order_id': 1, 'invoice_amount': 11, 'address': [17,18,19], 'customer_name': 16, 'marketplace': 'Amazon',
#                        'title': 8, 'sku_code': 7, 'quantity': 9, 'telephone': 6, 'email_id': 4}

ASKMEBAZZAR_EXCEL = {'order_id': 0, 'invoice_amount': 14, 'address': 27, 'customer_name': 9, 'marketplace': 'Ask Me Bazzar',
                    'title': 30, 'sku_code': 29, 'quantity': 12, 'telephone': 10}

FLIPKART_FA_EXCEL1 = {'order_id': 16, 'invoice_amount': 15, 'marketplace': 'Flipkart FA', 'title': 0, 'sku_code': 2, 'quantity': 9}

CAMPUS_SUTRA_EXCEL = {'order_id': 2, 'invoice_amount': 14, 'marketplace': 'Campus Sutra', 'sku_code': 6, 'quantity': 13, 'customer_name': 3,
                      'address': 5, 'telephone': 10, 'email_id': 7, 'shipment_date': 1}

#Campus Sutra
LIMEROAD_EXCEL = {'original_order_id': 0, 'order_id': 0, 'unit_price': 20, 'marketplace': 'Lime Road', 'sku_code': 14,
                  'quantity': 21, 'customer_name': 3, 'address': 7, 'telephone': 6,  'shipment_date': 23}

#Craftsvilla
CRAFTSVILLA_EXCEL = OrderedDict(( ('order_id', 0), ('title', 12), ('sku_code', 17), ('quantity', 13), ('marketplace', 'Craftsvilla'),
                                  ('customer_name', 3), ('address', 7), ('telephone', 9), ('email_id', 4),
                                  ('amount', 21), ('amount_discount', 22), ('cgst_tax', 26), ('sgst_tax', 28), ('igst_tax', 30)
                               ))

CRAFTSVILLA_AMAZON_EXCEL = OrderedDict(( ('order_id', 0), ('title', 10), ('sku_code', 11), ('quantity', 14), ('marketplace', 'Amazon'),
                                  ('unit_price', 16)
                               ))

#Adam clothing and Campus Sutra
MYNTRA_EXCEL = {'invoice_amount': 19, 'marketplace': 'Myntra', 'sku_code': 2, 'quantity': 10, 'title': 8, 'original_order_id': 1,
                'order_id': 1, 'mrp': 13, 'discount': 14, 'unit_price': 12, 'cgst_amt': 16, 'sgst_amt': 18, 'igst_amt': 15,
                'utgst_amt': 17}

#Adam clothing
JABONG_EXCEL = {'invoice_amount': 14, 'marketplace': 'Jabong', 'sku_code': 2, 'quantity': 9, 'title': 7, 'original_order_id': 1, 'order_id': 1,
                'vat': [14, 11], 'mrp': 12, 'discount': 13, 'unit_price': 11}


#Adam clothing
UNI_COMMERCE_EXCEL = {'order_id': 12, 'title': 19, 'channel_name': 2, 'sku_code': 17, 'recreate': True}

# ---  Returns Default headers --
GENERIC_RETURN_EXCEL = OrderedDict((('sku_id', 2), ('order_id', 1), ('quantity', 3), ('damaged_quantity', 4),
                                   ('return_id', 0),  ('return_date', 5)))

# ---  Shotang Returns headers --
SHOTANG_RETURN_EXCEL = OrderedDict((('sku_id', 2), ('order_id', 1), ('quantity', 3), ('return_date', 4), ('seller_order_id', 0),
                                    ('return_type', 5), ('marketplace', 'Shotang')
                                  ))

#MYNTRA_RETURN_EXCEL = OrderedDict((('sku_id', [5,7]), ('quantity', 8), ('reason', 13), ('marketplace', "MYNTRA")))

MYNTRA_RETURN_EXCEL = OrderedDict((('sku_id', [5,7]), ('quantity', 8), ('reason', 13), ('marketplace', "MYNTRA")))

UNIWEAR_RETURN_EXCEL = OrderedDict((('sku_id', 4), ('channel', 14),('reason', 12),
                                        ('return_id', 5),  ('return_date', 8)))

#Adam clothing
MYNTRA_BULK_PO_EXCEL = OrderedDict(( ('order_id', 0), ('original_order_id', 0), ('sku_code', 1), ('title', 3),
                                     ('marketplace', 'Myntra'), ('mrp', 7), ('quantity', 6), ('invoice_amount', [6, 12]),
                                     ('vat', {'tax': 10, 'quantity': 6, 'tax_value': 11}),
                                  ))

# Alpha Ace
ALPHA_ACE_ORDER_EXCEL = OrderedDict(( ('order_id', 0), ('title', 9), ('sku_code', 27), ('quantity', 12),
                                ('marketplace', 'Alpha Ace'), ('customer_name', 25), ('telephone', 26),
                                ('unit_price', 20), ('invoice_amount', [12,20]), ('cgst_tax', 16), ('sgst_tax', 18)
                             ))


UNI_COMMERCE_EXCEL1 = {'order_id': 8, 'channel_name': 2, 'sku_code': 20, 'customer_name': 9, 'email_id': 10, 'telephone': 11,
                       'address': [12, 13, 14], 'state': 15, 'pin_code': 16, 'invoice_amount': 19, 'recreate': True}

UNI_WARE_EXCEL = {'order_id': 12, 'channel_name': 2, 'sku_code': 1, 'quantity': 34}

UNI_WARE_EXCEL1 = {'order_id': 0, 'email_id': 5, 'telephone': 20, 'customer_name': 13, 'address': [14, 15], 'city': 16, 'state': 17,
                   'pin_code': 19, 'title': 33, 'channel_name': 37, 'sku_code': 31, 'invoice_amount': 42, 'discount': 46}

SHOTANG_ORDER_FILE_EXCEL = {'order_id': 1, 'customer_name': 6, 'customer_id': 5, 'telephone': 7, 'address': 8, 'sku_code': 2,
                            'invoice_amount': 16, 'sor_id': 0, 'order_date': 3, 'quantity': 4, 'order_status': 11, 'seller': 9,
                            'marketplace': 'Shotang', 'vat': {'tax': 14, 'quantity': 4, 'tot_tax': 15} }

# End of Order File Upload Templates

# Download Excel Report Mapping
EXCEL_REPORT_MAPPING = {'dispatch_summary': 'get_dispatch_data', 'sku_list': 'get_sku_filter_data', 'location_wise': 'get_location_stock_data',
                        'goods_receipt': 'get_po_filter_data', 'receipt_summary': 'get_receipt_filter_data',
                        'sku_stock': 'print_sku_wise_data', 'sku_wise_purchases': 'sku_wise_purchase_data',
                        'supplier_wise': 'get_supplier_details_data', 'sales_report': 'get_sales_return_filter_data',
                        'inventory_adjust_report': 'get_adjust_filter_data', 'inventory_aging_report': 'get_aging_filter_data',
                        'stock_summary_report': 'get_stock_summary_data', 'daily_production_report': 'get_daily_production_data',
                        'order_summary_report': 'get_order_summary_data', 'seller_invoices_filter': 'get_seller_invoices_filter_data',
                        'open_jo_report': 'get_openjo_details', 'grn_inventory_addition': 'get_grn_inventory_addition_data',
                        'sales_returns_addition': 'get_returns_addition_data',
                        'seller_stock_summary_replace': 'get_seller_stock_summary_replace'
                       }
# End of Download Excel Report Mapping

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
                               ("MASTERS_LABEL", (("SKU Master", "add_skumaster"), ("Location Master", "add_locationmaster"),
                               ("Supplier Master", "add_suppliermaster"),("Supplier SKU Mapping", "add_skusupplier"),
                               ("Customer Master", "add_customermaster"),("Customer SKU Mapping", "add_customersku"),
                               ("BOM Master", "add_bommaster"),
                               ("Vendor Master", "add_vendormaster"),("Discount Master", "add_categorydiscount"),
                               ("Custom SKU Template", "add_productproperties"),("Size Master", "add_sizemaster"))),

                               # Inbound
                               ("INBOUND_LABEL", (("Raise PO", "add_openpo"), ("Receive PO", "add_purchaseorder"),
                               ("Quality Check", "add_qualitycheck"),
                               ("Putaway Confirmation", "add_polocation"), ("Sales Returns", "add_orderreturns"),
                               ("Returns Putaway", "add_returnslocation"))),

                               # Production
                               ("PRODUCTION_LABEL", (("Raise Job order", "add_jomaterial"), ("RM Picklist", "add_materialpicklist"),
                               ("Receive Job Order", "add_joborder"),("Job Order Putaway", "add_rmlocation"))),

                               # Stock Locator
                               ("STOCK_LABEL",(("Stock Detail", "add_stockdetail"), ("Vendor Stock", "add_vendorstock"),
                               ("Cycle Count", "add_cyclecount"), ("Move Inventory", "change_inventoryadjustment"),
                               ("Inventory Adjustment", "add_inventoryadjustment"),("Stock Summary", "add_skustock"),
                               ("Warehouse Stock", "add_usergroups"), ("IMEI Tracker", "add_poimeimapping"))),

                               # Outbound
                               ("OUTBOUND_LABEL",(("Create Orders", "add_orderdetail"), ("View Orders", "add_picklist"),
                               ("Pull Confirmation", "add_picklistlocation"))),

                               # Shipment Info
                               ("SHIPMENT_LABEL",(("Shipment Info", "add_shipmentinfo"))),

                               # Others
                               ("OTHERS_LABEL", (("Raise Stock Transfer", "add_openst"), ("Create Stock Transfer", "add_stocktransfer"))),

                               # Payment
                               ("PAYMENT_LABEL", (("PAYMENTS", "add_paymentsummary"))),

                             ))

ORDERS_TRACK_STATUS = {0: 'Resolved', 1: "Conflict", 2: "Delete"}

# Shotang Integration Mapping Dictionaries

ORDER_DETAIL_API_MAPPING = {'id': 'order["itemId"]', 'order_id': 'uorId', 'items': 'orders',
                            'channel': 'orders.get("channel", "Shotang")', 'order_items': 'orders["subOrders"]', 'sku': 'sku_item["sku"]',
                         'title': 'sku_item["name"]', 'quantity': 'sku_item["quantity"]',
                         'shipment_date': 'orders.get("orderDate", '')', 'channel_sku': 'sku_item["sku"]',
                         'unit_price': 'sku_item["unitPrice"]', 'seller_id': 'order["sellerId"]',
                         'sor_id': 'order["sorId"]', 'cgst_tax': 'sku_item.get("cgstTax", "0")', 'sgst_tax':'sku_item.get("sgstTax", "0")',
                         'igst_tax': 'sku_item.get("igstTax", "0")', 'order_status': 'sku_item.get("status", "")',
                         'line_items': 'order["lineItems"]', 'customer_id': 'orders.get("retailerId", "")',
                         'customer_name': '(orders.get("retailerAddress", {})).get("name", "")',
                         'telephone': '(orders.get("retailerAddress", {})).get("phoneNo", "")',
                         'address': '(orders.get("retailerAddress", {})).get("address", "")',
                         'city': '(orders.get("retailerAddress", {})).get("city", "")', 'seller_item_id': 'sku_item["lineItemId"]',
                         'seller_parent_item_id': 'sku_item["parentLineItemId"]'
                        }

SKU_MASTER_API_MAPPING = OrderedDict(( ('skus', 'skus'), ('sku_code', 'sku_code'), ('sku_desc', 'sku_name'),
                                       ('sku_brand', 'sku_brand'), ('sku_category', 'sku_category_name'), ('price', 'price'),
                                       ('mrp', 'mrp'), ('product_type', 'product_type'), ('sku_class', 'sku_class'),
                                       ('style_name', 'style_name'), ('status', 'status'), ('hsn_code', 'hsn_code'),
                                       ('ean_number', 'ean_number'), ('threshold_quantity', 'threshold_quantity'), ('color', 'color'),
                                       ('measurement_type', 'measurement_type'), ('sku_size', 'sku_size'), ('size_type', 'size_type'),
                                       ('mix_sku', 'mix_sku'), ('sku_type', 'sku_type'), ('attributes', 'sku_options'),
                                       ('child_skus', 'child_skus') ))

CUSTOMER_MASTER_API_MAPPING = OrderedDict(( ('customers', 'customers'), ('customer_id', 'customer_id'), ('name', 'name'),
                                            ('address', 'address'), ('city', 'city'), ('state', 'state'), ('country', 'country'),
                                            ('pincode', 'pincode'), ('phone_number', 'phone_number'), ('email_id', 'email_id'),
                                            ('status', 'status'), ('last_name', 'last_name'), ('credit_period', 'credit_period'),
                                            ('tin_number', 'tin_number'), ('price_type', 'price_type'), ('tax_type', 'tax_type'),
                                            ('pan_number', 'pan_number')
                                         ))

SELLER_MASTER_API_MAPPING = OrderedDict(( ('sellers', 'sellers'), ('seller_id', 'seller_id'), ('name', 'name'),
                                            ('phone_number', 'phone_number'), ('address', 'address'),
                                            ('email_id', 'email_id'), ('tin_number', 'gstin_no'),
                                            ('vat_number', 'vat_number'), ('price_type', 'price_type'),
                                            ('margin', 'margin'), ('status', 'status')
                                         ))

# Easyops Integration Mapping Dictionaries
EASYOPS_ORDER_MAPPING = {'id': 'order["itemId"]', 'order_id': 'orderTrackingNumber', 'items': 'orders.get("orderItems", [])',
                         'channel': 'orders["channel"]',
                         'sku': 'sku_item["easyopsSku"]',
                         'title': 'sku_item["productTitle"]', 'quantity': 'sku_item["quantity"]',
                         'shipment_date': 'orders["orderDate"]', 'channel_sku': 'sku_item["channelSku"]',
                         'unit_price': 'sku_item["unitPrice"]', 'order_items': 'orders["orderItems"]'}

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
# End of Easyops Integration Mapping Dictionaries

ORDER_DETAIL_STATES = {0: 'Picklist generated', 1: 'Newly Created', 2: 'Dispatched', 3: 'Cancelled', 4: 'Returned',
                       5: 'Delivery Reschedule Cancelled'}

SELLER_ORDER_STATES = {0: 'Seller Order Picklist generated', 1: 'Newly Created', 4: 'Returned'}

PAYMENT_MODES = ['Credit Card', 'Debit Card', 'Cash', 'NEFT', 'RTGS', 'IMPS', 'Online Transfer', 'Cash Remittance', 'Cheque']

ORDER_HEADERS_d = OrderedDict(( ('Unit Price', 'unit_price'), ('Amount', 'amount'), ('Tax', 'tax'), ('Total Amount', 'total_amount'),
                                       ( 'Remarks', 'remarks') , ( 'Discount', 'discount'), ('Discount Percentage', 'discount_percentage')))

STYLE_DETAIL_HEADERS = OrderedDict(( ('SKU Code', 'wms_code'), ('SKU Description', 'sku_desc'), ('Size', 'sku_size'),
                                     ('1-Day Stock', 'physical_stock'), ('3-Day Stock', 'all_quantity')
                                  ))

TAX_TYPES = OrderedDict(( ('DEFAULT', 0), ('VAT', 5.5), ('CST', 2) ))
D_TAX_TYPES = OrderedDict(( ('DEFAULT', 0), ('VAT', 6), ('CST', 2) ))

##RETAILONE RELATED
R1_ORDER_MAPPING = {'id': 'id', 'order_id': 'order_id', 'items': 'orders.get("items", [])',
                    'channel': 'orders["channel_sku"]["channel"]["name"]', 'sku': 'sku_item["sku"]', 'channel_sku': 'sku_item["mp_id_value"]',
                    'title': 'sku_item["title"]', 'quantity': 'sku_item["quantity"]',
                    'shipment_date': 'order["ship_by"]',
                    'unit_price': '0', 'order_items': ''}

R1_RETURN_ORDER_MAPPING = {'order_id': 'order_id', 'items': 'items', 'return_id': 'return_id',
                           'return_date': 'return_date', 'sku': 'order["sku"]', 'return_type': 'order["return_type"]',
                           'damaged_quantity': '0', 'return_quantity': 'order["quantity"]',
                           'order_items': '', 'reason': 'order["return_reason"]', 'marketplace': 'order["channel_sku"]["channel"]["name"]'}

#BARCODE_FORMATS = {'adam_clothing': {'format1': ['sku_master'], 'format2': ['sku_master'], 'format3': ['sku_master']}}

BARCODE_DICT = {'format1': {'SKUCode': '', 'SKUDes': '', 'Color': '', 'Size': '', 'SKUPrintQty': '', 'Brand': '', 'Style': ''},
                'format2': {'SKUCode': '', 'SKUDes': '', 'Color': '', 'Size': '', 'SKUPrintQty': '', 'Brand': '', 'Product': '',
                            'DesignNo': '', 'Qty': '1', 'Gender': '', 'MRP': '', 'Packed on': '', 'Manufactured By': '', 'Marketed By': ''},
                'format3': {'SKUCode': '', 'SKUDes': '', 'Color': '', 'Size': '', 'SKUPrintQty': '', 'Brand': '', 'Product': '','DesignNo': '',
                            'Qty': '1', 'Gender': '', 'MRP': '', 'MFD': '', 'Manufactured By': '', 'Marketed By': ''},
                'format4': {'SKUCode': '', 'color': '', 'Size': '', 'SKUPrintQty': '',
                            'Qty': '1', 'MRP': '', 'Manufactured By': '', 'Marketed By': '', 'Phone': '',
                            'Vendor SKU': '', 'PO No': '', 'Email': ''},
                'Bulk Barcode': {'SKUCode': '', 'Color': '', 'SKUPrintQty': '1', 'Qty': '1', 
                            'DesignNo': '', 'UOM': '', 'Product': '', 'Company': ''}
               }

BARCODE_KEYS = {'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details', 'format4': 'Details', 'Bulk Barcode': 'Details'}

BARCODE_ADDRESS_DICT = {'adam_clothing1': 'Adam Exports 401, 4th Floor,\n Pratiek Plazza, S.V.Road,\n Goregaon West, Mumbai - 400062.\n MADE IN INDIA'}

PRICING_MASTER_HEADERS = ['SKU Code', 'Selling Price type', 'Price', 'Discount']

PRICE_DEF_EXCEL = OrderedDict(( ('sku_id', 0), ('price_type', 1), ('price', 2), ('discount', 3) ))

PRICE_MASTER_DATA = {'sku_id': '', 'price_type': '', 'price': 0, 'discount': 0}

SELLER_DATA = {'name': '', 'address': '', 'phone_number': '', 'email_id': '', 'status': 1, 'price_type': '', 'margin': 0}

USER_SKU_EXCEL = {'warehouse_user': SKU_HEADERS, 'marketplace_user': MARKET_USER_SKU_HEADERS, 'customer': SKU_HEADERS}

USER_SKU_EXCEL_MAPPING = {'warehouse_user': SKU_DEF_EXCEL, 'marketplace_user': MARKETPLACE_SKU_DEF_EXCEL, 'customer': SKU_DEF_EXCEL}

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

JABONG_ADDRESS = 'Jabong Marketplace Mahindra Logistics Limited\nBlock No. H2 Sai Dhara Warehousing & Logistics Park,\n\
                  Opp. Indian Oil Petrol Pump\nNear Shangrila Resort\nMumbai-Nasik Highway,\nBhiwandi,\nMaharashtra,421302'

USER_CHANNEL_ADDRESS = {'campus_sutra:myntra': MYNTRA_BANGALORE_ADDRESS, 'adam_clothing:myntra': MYNTRA_MUMBAI_ADDRESS,
                        'adam_clothing1:myntra': MYNTRA_MUMBAI_ADDRESS, 'adam_clothing1:myntra:bulk': MYNTRA_BULK_ADDRESS,
                        'adam_clothing1:jabong': JABONG_ADDRESS, 'campus_sutra:jabong': MYNTRA_JABONG_ADDRESS
                       }

MYNTRA_BULK_ADDRESS = 'MYNTRA DESIGNS PVT LTD\nKsquare Industrial Park, Warehouse 4\n\
                         Before Padgha Toll naka Nashik-Mumbai Highway \nNear Pushkar Mela Hotel Rahul Narkhede,\n\
                         Padgha-Bhiwandi\nTin# 27590747736'


# End of Myntra Invoice Address based on username

SELLER_ORDER_FIELDS = {'sor_id': '', 'quantity': 0, 'order_status': '', 'order_id': '', 'seller_id': '', 'status': 1, 'invoice_no': ''}

SELLER_MARGIN_DICT = {'seller_id': '', 'sku_id': '', 'margin': 0}

RECEIVE_OPTIONS = OrderedDict(( ('One step Receipt + Qc', 'receipt-qc'), ('Two step Receiving', '2-step-receive')))

PERMISSION_IGNORE_LIST = ['session', 'webhookdata', 'swxmapping', 'userprofile', 'useraccesstokens', 'contenttype', 'user',
                          'permission','group','logentry', 'corsmodel']

# Customer Invoices page headers based on user type
MP_CUSTOMER_INVOICE_HEADERS = ['UOR ID', 'SOR ID', 'Seller ID', 'Customer Name', 'Order Quantity', 'Picked Quantity', 'Order Date&Time',
                               'Invoice Number']

WH_CUSTOMER_INVOICE_HEADERS = ['Order ID', 'Customer Name', 'Order Quantity', 'Picked Quantity', 'Order Date&Time']

# End of Customer Invoices page headers based on user type

SUPPLIER_EXCEL_FIELDS = OrderedDict(( ('id', 0), ('name', 1), ('address', 2), ('email_id', 3), ('phone_number', 4),
                                      ('tin_number', 5), ('pan_number', 6), ('pincode',7), ('city', 8), ('state', 9), ('country', 10)
                                   ))
STATUS_DICT = {1: True, 0: False}

PO_RECEIPT_TYPES = ['Purchase Order', 'Buy & Sell', 'Hosted Warehouse']

PO_ORDER_TYPES = {'SR': 'Self Receipt', 'VR': 'Vendor Receipt', 'HW': 'Hosted Warehouse', 'BS': 'Buy & Sell'}

LOAD_UNIT_HANDLE_DICT = {'enable': 'pallet', 'disable': 'unit'}

MIX_SKU_ATTRIBUTES = {'no_mix': 'No Mix', 'mix_group': 'Mix within Group'}

TAX_TYPE_ATTRIBUTES = {'inter_state': 'Inter State', 'intra_state': 'Intra State'}

TAX_VALUES = [{'tax_name': 'Inter State', 'tax_value': 'inter_state'}, {'tax_name': 'Intra State', 'tax_value': 'intra_state'}]

SUMMARY_INTER_STATE_STATUS = {0: 'intra_state', 1: 'inter_state', '2': 'default'}

#Username and GST Tin Mapping

GSTIN_USER_MAPPING = {'sagar_fab': '29ABEFS4899J1ZA', 'adam_clothing1': '2788OFB3466F1ZB', 'adam_abstract': '2788OFB3466F1ZB',
                      'dazzle_export': '26AHQPP2057B1ZB', 'legends_overseas': '27AAGFL3290D1ZF', 'TranceHomeLinen': '29ADOPS6189BIZX',
                      'demo': 'ABC12345678', 'sjpmg': '07BDBPS8474F1Z7', 'tshirt_inc': '36AAHFT9169L1ZC',
                      'scholar_clothing': '29AMPPN7507A1ZW', 'campus_sutra': '29AAIFC4655P1ZQ', 'Subhas_Publishing': '29AABHS0537D1ZD'}

#End of Username and GST Tin Mapping

#ORDER LABEL MAPPING EXCEL (Campus Sutra)

ORDER_LABEL_EXCEL_HEADERS = ['Order ID', 'SKU Code', 'Label']

MYNTRA_LABEL_EXCEL_MAPPING = OrderedDict(( ('sku_code', 2), ('order_id', 0), ('label', 1), ('vendor_sku', 4),
                                           ('title', 3), ('size', 5), ('color', 6), ('mrp', 7)))

MYNTRA_LABEL_EXCEL_MAPPING1 = OrderedDict(( ('sku_code', 2), ('order_id', 0), ('label', 1), ('vendor_sku', 4),
                                            ('title', 3), ('size', 5), ('color', 6), ('mrp', 8)))

ORDER_LABEL_EXCEL_MAPPING = OrderedDict(( ('sku_code', 1), ('order_id', 0), ('label', 2) ))

ORDER_SERIAL_EXCEL_HEADERS = ['Seller ID', 'Customer ID', 'Uor ID', 'PO Number', 'SKU Code', 'Quantity', 'Unit Price', 'CGST(%)',
                              'SGST(%)', 'IGST(%)', 'Order Type(Options: Normal, Transit)']

ORDER_SERIAL_EXCEL_MAPPING = OrderedDict(( ('order_id', 2), ('seller_id', 0), ('customer_id', 1), ('sku_code', 4), ('po_number', 3),
                                           ('quantity', 5), ('unit_price', 6), ('cgst_tax', 7), ('sgst_tax', 8), ('igst_tax', 9),
                                           ('order_type', 10) ))

PO_SERIAL_EXCEL_HEADERS = ['Supplier ID', 'SKU Code', 'Location', 'Unit Price', 'Serial Number']

PO_SERIAL_EXCEL_MAPPING = OrderedDict(( ('supplier_id', 0), ('sku_code', 1), ('location', 2), ('unit_price', 3),
                                        ('imei_number', 4)))

JOB_ORDER_EXCEL_HEADERS = ['Product SKU Code', 'Product SKU Quantity']

JOB_ORDER_EXCEL_MAPPING = OrderedDict(( ('product_code', 0), ('product_quantity', 1)))

#Company logo names
COMPANY_LOGO_PATHS = {'TranceHomeLinen': 'trans_logo.jpg', 'Subhas_Publishing': 'book_publications.png'}

# Configurtions Mapping
CONFIG_SWITCHES_DICT = {'use_imei': 'use_imei', 'tally_config': 'tally_config', 'show_mrp': 'show_mrp',
                      'stock_display_warehouse': 'stock_display_warehouse', 'seller_margin': 'seller_margin', 'hsn_summary': 'hsn_summary',
                      'send_message': 'send_message', 'order_management': 'order_manage', 'back_order': 'back_order',
                      'display_customer_sku': 'display_customer_sku', 'pallet_switch': 'pallet_switch', 'receive_process': 'receive_process',
                      'no_stock_switch': 'no_stock_switch', 'show_disc_invoice': 'show_disc_invoice',
                      'production_switch': 'production_switch', 'sku_sync': 'sku_sync', 'display_remarks_mail': 'display_remarks_mail',
                      'stock_sync': 'stock_sync', 'float_switch': 'float_switch', 'automate_invoice': 'automate_invoice',
                      'pos_switch': 'pos_switch', 'create_seller_order': 'create_seller_order',
                      'marketplace_model': 'marketplace_model', 'decimal_limit': 'decimal_limit', 'batch_switch': 'batch_switch',
                      'view_order_status': 'view_order_status', 'label_generation': 'label_generation', 'grn_scan_option': 'grn_scan_option',
                      'show_imei_invoice': 'show_imei_invoice', 'style_headers': 'style_headers', 'picklist_sort_by': 'picklist_sort_by',
                      'barcode_generate_opt': 'barcode_generate_opt', 'online_percentage': 'online_percentage', 'mail_alerts': 'mail_alerts',
                      'detailed_invoice': 'detailed_invoice', 'invoice_titles': 'invoice_titles', 'show_image': 'show_image',
                      'auto_generate_picklist': 'auto_generate_picklist', 'auto_po_switch': 'auto_po_switch', 'fifo_switch': 'fifo_switch',
                      'internal_mails': 'Internal Emails', 'increment_invoice': 'increment_invoice'
                     }

CONFIG_INPUT_DICT = {'email': 'email', 'report_freq': 'report_frequency', 'scan_picklist_option': 'scan_picklist_option',
                     'data_range': 'report_data_range', 'imei_limit': 'imei_limit', 'invoice_remarks': 'invoice_remarks',
                     'invoice_marketplaces': 'invoice_marketplaces'
                    }

CONFIG_DEF_DICT = {'receive_options': dict(RECEIVE_OPTIONS), 'all_view_order_status': CUSTOM_ORDER_STATUS, 'mail_options': MAIL_REPORTS_DATA,
                   'mail_reports': MAIL_REPORTS, 'style_detail_headers': STYLE_DETAIL_HEADERS, 'picklist_options': PICKLIST_OPTIONS,
                   'order_headers': ORDER_HEADERS_d, 'barcode_generate_options': BARCODE_OPTIONS
                  }

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
    from rest_api.views.common import get_sku_master, get_misc_value, get_local_date
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    search_parameters = {}
    use_imei = get_misc_value('use_imei', user.id)
    query_prefix = ''
    lis = ['open_po__supplier__name', 'order_id', 'open_po__sku__wms_code', 'open_po__sku__sku_desc', 'received_quantity',
           'updation_date']
    model_obj = PurchaseOrder
    if use_imei == 'true':
        lis = ['purchase_order__open_po__supplier__name', 'purchase_order__order_id', 'purchase_order__open_po__sku__wms_code',
               'purchase_order__open_po__sku__sku_desc', 'imei_number', 'creation_date']
        query_prefix = 'purchase_order__'
        model_obj = POIMEIMapping
    temp_data = copy.deepcopy( AJAX_DATA )
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
        po_reference = '%s%s_%s' %(data.prefix, str(data.creation_date).split(' ')[0].replace('-', ''), data.order_id)
        temp_data['aaData'].append(OrderedDict(( ('PO Reference', po_reference), ('WMS Code', data.open_po.sku.wms_code), ('Description', data.open_po.sku.sku_desc),
                                    ('Supplier', '%s (%s)' % (data.open_po.supplier.name, data.open_po.supplier_id)),
                                    ('Receipt Number', data.open_po_id), ('Received Quantity', data.received_quantity),
                                    ('Serial Number', serial_number), ('Received Date', received_date) )))
    return temp_data

def get_dispatch_data(search_params, user, sub_user, serial_view=False):
    from miebach_admin.models import *
    from miebach_admin.views import *
    from rest_api.views.common import get_sku_master, get_order_detail_objs
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    search_parameters = {}
    if serial_view:
        lis = ['order__order_id', 'order__sku__wms_code', 'order__sku__sku_desc', 'order__customer_name', 'po_imei__imei_number',
               'updation_date', 'updation_date']
        model_obj = OrderIMEIMapping
        param_keys = {'wms_code': 'order__sku__wms_code', 'sku_code': 'order__sku__sku_code'}
        search_parameters['status'] = 1
        search_parameters['order__user'] = user.id
        search_parameters['order__sku_id__in'] = sku_master_ids
    else:
        lis = ['order__order_id', 'order__sku__wms_code', 'order__sku__sku_desc', 'stock__location__location', 'picked_quantity',                  'picked_quantity', 'updation_date', 'updation_date']
        model_obj = Picklist
        param_keys = {'wms_code': 'stock__sku__wms_code', 'sku_code': 'stock__sku__sku_code'}
        search_parameters['status__in'] = ['picked', 'batch_picked', 'dispatched']
        search_parameters['stock__gt'] = 0
        search_parameters['order__user'] = user.id
        search_parameters['stock__sku_id__in'] = sku_master_ids

    temp_data = copy.deepcopy( AJAX_DATA )

    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['updation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date']  + datetime.timedelta(1), datetime.time())
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
        order_detail = get_order_detail_objs(search_params['order_id'], user, search_params={},all_order_objs = [])
        if order_detail:
            search_parameters['order_id__in'] = order_detail.values_list('id', flat=True)
        else:
            search_parameters['order_id__in'] = []

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)


    model_data = model_obj.objects.filter(**search_parameters)
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
        if not serial_view:
            picked_quantity = data.picked_quantity
            if data.stock.location.zone.zone == 'DEFAULT':
                picked_quantity = 0
            date = get_local_date(user, data.updation_date).split(' ')
            order_id = data.order.original_order_id
            if not order_id:
                order_id = str(data.order.order_code) + str(data.order.order_id)

            temp_data['aaData'].append(OrderedDict(( ('Order ID', order_id), ('WMS Code', data.stock.sku.wms_code),
                                                    ('Description', data.stock.sku.sku_desc), ('Location', data.stock.location.location),
                                                    ('Quantity', data.picked_quantity), ('Picked Quantity', picked_quantity),
                                                    ('Date', ' '.join(date[0:3])), ('Time', ' '.join(date[3:5]))  )))
        else:
            order_id = data.order.original_order_id
            if not order_id:
                order_id = str(data.order.order_code) + str(data.order.order_id)
            serial_number = ''
            if data.po_imei:
                serial_number = data.po_imei.imei_number
            date = get_local_date(user, data.updation_date).split(' ')
            temp_data['aaData'].append(OrderedDict(( ('Order ID', order_id), ('WMS Code', data.order.sku.wms_code),
                                                    ('Description', data.order.sku.sku_desc), ('Customer Name', data.order.customer_name),
                                                    ('Serial Number', serial_number),
                                                    ('Date', ' '.join(date[0:3])), ('Time', ' '.join(date[3:5]))  )))

    return temp_data

def sku_wise_purchase_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from itertools import chain
    from rest_api.views.common import *
    from rest_api.views.inbound import get_purchase_order_data
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    data_list = []
    received_list = []
    temp_data = copy.deepcopy( AJAX_DATA )
    search_parameters = {}
    user_profile = UserProfile.objects.get(user_id=user.id)

    if 'sku_code' in search_params:
        search_parameters['open_po__sku__sku_code'] = search_params['sku_code']

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    search_parameters['open_po__sku__user'] = user.id
    search_parameters['open_po__sku_id__in'] = sku_master_ids
    purchase_orders = PurchaseOrder.objects.filter(**search_parameters)
    temp_data['recordsTotal'] = purchase_orders.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    quality_checks = QualityCheck.objects.filter(po_location__location__zone__user=user.id,
                                                 purchase_order_id__in=purchase_orders.values_list('id', flat=True)).\
                                          values('purchase_order_id').distinct().annotate(total_rejected=Sum('rejected_quantity'))
    qc_po_ids = map(lambda d: d['purchase_order_id'], quality_checks)
    qc_reject_sums = map(lambda d: d['total_rejected'], quality_checks)
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
            temp = OrderedDict(( ('PO Date', str(data.po_date).split('+')[0]), ('Supplier', order_data['supplier_name']),
                                 ('SKU Code', order_data['wms_code']), ('Order Quantity', order_data['order_quantity']),
                                 ('Received Quantity', data.received_quantity), ('Receipt Date', receipt_date), ('Status', status) ))
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
                aft_price = price + ((price/100)*tax)
            pre_amount = float(order_data['order_quantity']) * float(price)
            aft_amount = float(order_data['order_quantity']) * float(aft_price)
            temp = OrderedDict(( ('PO Date', str(data.po_date).split('+')[0]), ('PO Number', po_number),
                                 ('Supplier ID', order_data['supplier_id']), ('Supplier Name', order_data['supplier_name']),
                                 ('Recepient', 'SHProc'),('SKU Code', order_data['sku_code']),('SKU Description', order_data['sku_desc']),
                                 ('SKU Class', order_data['sku'].sku_class), ('SKU Style Name', order_data['sku'].style_name),
                                 ('SKU Brand', order_data['sku'].sku_brand), ('SKU Category', order_data['sku'].sku_category),
                                 ('PO Qty', order_data['order_quantity']), ('Unit Rate', order_data['price']),
                                 ('Pre-Tax PO Amount', pre_amount), ('Tax', tax), ('After Tax PO Amount', aft_amount),
                                 ('Qty received', data.received_quantity), ('Status', status)
                            ))
            if status == 'Received':
                received_list.append(temp)
            else:
                data_list.append(temp)

    order_term = search_params.get('order_term', '')
    order_index = search_params.get('order_index', '')
    data_list = list(chain(data_list, received_list))
    if user_profile.user_type == 'marketplace_user':
        columns = SKU_WISE_PO_DICT['mk_dt_headers']
    else:
        columns = SKU_WISE_PO_DICT['dt_headers']
    data_list = apply_search_sort(columns, data_list, order_term, '', order_index)
    if stop_index:
        data_list = data_list[start_index:stop_index]
    temp_data['aaData'] = list(chain(temp_data['aaData'], data_list))

    return temp_data

def get_po_filter_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master, get_local_date, apply_search_sort
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    user_profile = UserProfile.objects.get(user_id=user.id)
    is_market_user = False
    if user_profile.user_type == 'marketplace_user':
        is_market_user = True
    if is_market_user:
        unsorted_dict = { 14: 'Pre-Tax Received Value', 19: 'Post-Tax Received Value', 20: 'Margin', 22:'Invoiced Unit Rate',
                             23: 'Invoiced Total Amount'}
        lis = ['purchase_order__updation_date', 'purchase_order__creation_date', 'purchase_order__order_id',
               'purchase_order__open_po__supplier_id', 'purchase_order__open_po__supplier__name', 'id',
               'purchase_order__open_po__sku__sku_code', 'purchase_order__open_po__sku__sku_desc', 'purchase_order__open_po__sku__sku_class',
               'purchase_order__open_po__sku__style_name', 'purchase_order__open_po__sku__sku_brand',
               'purchase_order__open_po__sku__sku_category', 'total_received', 'purchase_order__open_po__price', 'id',
               'purchase_order__open_po__cgst_tax', 'purchase_order__open_po__sgst_tax', 'purchase_order__open_po__igst_tax',
               'purchase_order__open_po__utgst_tax', 'id', 'seller_po__margin_percent', 'id', 'id', 'id', 'seller_po__receipt_type']
        model_name = SellerPOSummary
        field_mapping = {'from_date': 'purchase_order__creation_date', 'to_date': 'purchase_order__creation_date',
                         'order_id': 'purchase_order__order_id', 'wms_code': 'purchase_order__open_po__sku__wms_code__iexact',
                         'user': 'purchase_order__open_po__sku__user', 'sku_id__in': 'purchase_order__open_po__sku_id__in',
                         'prefix': 'purchase_order__prefix', 'supplier_id': 'purchase_order__open_po__supplier_id',
                         'supplier_name': 'purchase_order__open_po__supplier__name', 'receipt_type': 'seller_po__receipt_type'}
        result_values = ['purchase_order__order_id', 'purchase_order__open_po__supplier_id', 'purchase_order__open_po__supplier__name',
                         'purchase_order__open_po__sku__sku_code', 'purchase_order__open_po__sku__sku_desc',
                         'purchase_order__open_po__sku__sku_class', 'purchase_order__open_po__sku__style_name',
                         'purchase_order__open_po__sku__sku_brand', 'purchase_order__open_po__sku__sku_category',
                         'purchase_order__received_quantity', 'purchase_order__open_po__price', 'purchase_order__open_po__cgst_tax',
                         'purchase_order__open_po__sgst_tax', 'purchase_order__open_po__igst_tax', 'purchase_order__open_po__utgst_tax',
                         'seller_po__margin_percent', 'purchase_order__prefix', 'seller_po__unit_price', 'id', 'seller_po__receipt_type']
        excl_status = {'purchase_order__status': ''}
        rec_quan = 'quantity'
    else:
        lis = ['order_id', 'open_po__supplier_id', 'open_po__supplier__name', 'total_received']
        unsorted_dict = {}
        model_name = PurchaseOrder
        field_mapping = {'from_date': 'creation_date',  'to_date': 'creation_date', 'order_id': 'order_id',
                         'wms_code': 'open_po__sku__wms_code__iexact', 'user': 'open_po__sku__user', 'sku_id__in': 'open_po__sku_id__in',
                         'prefix': 'prefix', 'supplier_id': 'open_po__supplier_id', 'supplier_name': 'open_po__supplier__name'}
        result_values = ['order_id', 'open_po__supplier_id', 'open_po__supplier__name', 'prefix']
        excl_status = {'status': ''}
        rec_quan = 'received_quantity'

    search_parameters = {}
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    temp_data = copy.deepcopy( AJAX_DATA )
    temp_data['draw'] = search_params.get('draw')

    if 'from_date' in search_params:
        search_parameters[ field_mapping['from_date'] + '__gte'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date']  + datetime.timedelta(1), datetime.time())
        search_parameters[ field_mapping['to_date'] + '__lte'] = search_params['to_date']

    if 'open_po' in search_params and search_params['open_po']:
        temp = re.findall('\d+', search_params['open_po'])
        if temp:
            search_parameters[field_mapping['order_id']] = temp[-1]

    if 'sku_code' in search_params:
        search_parameters[field_mapping['wms_code']] = search_params['sku_code']


    search_parameters[field_mapping['user']] = user.id
    search_parameters[field_mapping['sku_id__in']] = sku_master_ids
    query_data = model_name.objects.exclude(**excl_status).filter(**search_parameters)
    model_data = query_data.values(*result_values).distinct().annotate(total_received=Sum(rec_quan))
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
        result = purchase_orders.filter(order_id=data[field_mapping['order_id']],open_po__sku__user=user.id)[0]
        po_number = '%s%s_%s' %(data[field_mapping['prefix']], str(result.creation_date).split(' ')[0].replace('-', ''), data[field_mapping['order_id']])
        if not is_market_user:
            temp_data['aaData'].append(OrderedDict(( ('PO Number', po_number), ('Supplier ID', data[field_mapping['supplier_id']]),
                                                     ('Supplier Name', data[field_mapping['supplier_name']]),
                                                     ('Total Quantity', data['total_received']),
                                                     ('DT_RowClass', 'results'), ('DT_RowAttr', {'data-id': data[field_mapping['order_id']]}),
                                                     ('key', 'po_id'), ('receipt_type', 'Purchase Order')
                                                  )))
        else:
            amount = float(data['total_received'] * data['purchase_order__open_po__price'])
            tot_tax = float(data['purchase_order__open_po__cgst_tax']) + float(data['purchase_order__open_po__sgst_tax']) + \
                      float(data['purchase_order__open_po__igst_tax']) + float(data['purchase_order__open_po__utgst_tax'])
            aft_unit_price = float(data['purchase_order__open_po__price']) + (float(data['purchase_order__open_po__price']/100) * tot_tax)
            post_amount = aft_unit_price * float(data['total_received'])
            margin_price = float(data['seller_po__unit_price'] - aft_unit_price)
            if margin_price < 0:
                margin_price = 0
            margin_price = "%.2f" % (margin_price * float(data['total_received']))
            final_price = data['seller_po__unit_price']
            if not final_price:
                final_price = aft_unit_price
            invoice_total_amount = float(final_price) * float(data['total_received'])
            temp_data['aaData'].append(OrderedDict(( ('Received Date', get_local_date(user, result.updation_date)),
                                                     ('PO Date', get_local_date(user, result.creation_date)), ('PO Number', po_number),
                                                     ('Supplier ID', data[field_mapping['supplier_id']]),
                                                     ('Supplier Name', data[field_mapping['supplier_name']]), ('Recepient', 'SHProc'),
                                                     ('SKU Code', data['purchase_order__open_po__sku__sku_code']),
                                                     ('SKU Description', data['purchase_order__open_po__sku__sku_desc']),
                                                     ('SKU Class', data['purchase_order__open_po__sku__sku_class']),
                                                     ('SKU Style Name', data['purchase_order__open_po__sku__style_name']),
                                                     ('SKU Brand', data['purchase_order__open_po__sku__sku_brand']),
                                                     ('SKU Category', data['purchase_order__open_po__sku__sku_category']),
                                                     ('Received Qty', data['total_received']),
                                                     ('Unit Rate', data['purchase_order__open_po__price']), ('Pre-Tax Received Value', amount),
                                                     ('CGST(%)', data['purchase_order__open_po__cgst_tax']),
                                                     ('SGST(%)', data['purchase_order__open_po__sgst_tax']),
                                                     ('IGST(%)', data['purchase_order__open_po__igst_tax']),
                                                     ('UTGST(%)', data['purchase_order__open_po__utgst_tax']),
                                                     ('Post-Tax Received Value', post_amount),
                                                     ('Margin %', data['seller_po__margin_percent']), ('Margin', margin_price),
                                                     ('Invoiced Unit Rate', final_price),
                                                     ('Invoiced Total Amount',invoice_total_amount),
                                                     ('DT_RowAttr', {'data-id': data['id']}), ('key', 'po_summary_id'),
                                                     ('receipt_type', data['seller_po__receipt_type'])
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

    if data:
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
    from rest_api.views.common import get_sku_master, get_order_detail_objs, get_local_date
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
    if 'order_id' in search_params:
        order_detail = get_order_detail_objs(search_params['order_id'], user, search_params={},all_order_objs = [])
        if order_detail:
            search_parameters['id__in'] = order_detail.values_list('id', flat=True)

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
    dispatched = OrderDetail.objects.filter(status=2,user= user.id).values_list('order_id', flat=True).distinct()
    reschedule_cancelled = OrderDetail.objects.filter(status=5,user= user.id).values_list('order_id', flat=True).distinct()

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

    status = ''
    for data in orders:
        is_gst_invoice = False
        invoice_date = get_local_date(user, data.creation_date, send_date='true')
        if datetime.datetime.strptime('2017-07-01', '%Y-%m-%d').date() <= invoice_date.date():
            is_gst_invoice = True
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
            if data.order_id in dispatched:
                status = ORDER_DETAIL_STATES.get(2, '')
            if data.order_id in reschedule_cancelled:
                status = ORDER_DETAIL_STATES.get(5, '')
        else:
            status = _status

        tax = 0
        vat = 5.5
        discount = 0
        mrp_price = data.sku.mrp
        order_status = ''
        remarks = ''
        order_summary = CustomerOrderSummary.objects.filter(order__user=user.id, order_id=data.id)
        unit_price = data.unit_price
        if order_summary:
            mrp_price = order_summary[0].mrp
            discount = order_summary[0].discount
            order_status = order_summary[0].status
            remarks = order_summary[0].central_remarks
            if not is_gst_invoice:
                tax = order_summary[0].tax_value
                vat = order_summary[0].vat
                if not unit_price:
                    unit_price = ((float(data.invoice_amount)/ float(data.quantity))) - float(discount) - (tax/float(data.quantity))
            else:
                amt = unit_price * float(data.quantity)
                cgst_amt = float(order_summary[0].cgst_tax) * (float(amt)/100)
                sgst_amt = float(order_summary[0].sgst_tax) * (float(amt)/100)
                igst_amt = float(order_summary[0].igst_tax) * (float(amt)/100)
                utgst_amt = float(order_summary[0].utgst_tax) * (float(amt)/100)
                tax = cgst_amt + sgst_amt + igst_amt + utgst_amt
        else:
            tax = float(float(data.invoice_amount)/100) * vat

        if order_status == 'None':
            order_status = ''
        invoice_amount = "%.2f" % ((float(unit_price) * float(data.quantity)) + tax - discount)
        unit_price = "%.2f" % unit_price

        temp_data['aaData'].append( OrderedDict(( ('Order Date', ''.join(date[0:3])), ('Order ID', order_id),
                                                  ('Customer Name', data.customer_name), ('SKU Brand', data.sku.sku_brand),
                                                  ('SKU Category', data.sku.sku_category), ('SKU Class', data.sku.sku_class),
                                                  ('SKU Size', data.sku.sku_size), ('SKU Description', data.sku.sku_desc),
                                                  ('SKU Code', data.sku.sku_code), ('Order Qty', int(data.quantity)),
                                                  ('MRP', int(data.sku.mrp)), ('Unit Price', unit_price),
                                                  ('Discount', data.sku.discount_percentage), ('City', data.city),
                                                  ('State', data.state), ('Marketplace', data.marketplace),
                                                  ('Invoice Amount', invoice_amount), ('Price', data.sku.price),
                                                  ('Status', status), ('Order Status', order_status), ('Remarks', remarks))) )

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

    unsorted_dict = { 10: 'Accepted Qty', 11: 'Rejected Qty', 13: 'Amount', 15: 'Total Amount'}
    search_parameters = {}
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    temp_data = copy.deepcopy( AJAX_DATA )
    temp_data['draw'] = search_params.get('draw')

    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['open_po__creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date']  + datetime.timedelta(1), datetime.time())
        search_parameters['open_po__creation_date__lt'] = search_params['to_date']

    if 'sku_code' in search_params:
        search_parameters['open_po__sku__sku_code__iexact'] = search_params['sku_code']


    search_parameters['open_po__sku__user'] = user.id
    search_parameters['open_po__sku_id__in'] = sku_master_ids
    exc_po_ids = PurchaseOrder.objects.filter(open_po__sku__user=user.id, status='').values_list('open_po_id', flat=True)
    seller_pos = SellerPO.objects.exclude(open_po_id__in=exc_po_ids).filter(**search_parameters)
    quality_checks = QualityCheck.objects.filter(po_location__location__zone__user=user.id,
                                                 purchase_order__open_po_id__in=seller_pos.values_list('open_po_id', flat=True)).\
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
            final_price = float('%.2f' % ((final_price * 100)/(100 + float(data.open_po.tax))))
        amount = final_price * float(data.open_po.order_quantity)
        total_amount = amount
        if data.open_po.tax:
            total_amount = amount + (amount/100) * float(data.open_po.tax)
        if int(data.open_po_id) in qc_po_ids:
            rejected_quan = qc_reject_sums[qc_po_ids.index(int(data.open_po_id))]
        if int(data.open_po_id) in qc_po_ids:
            accepted_quan = qc_accept_sums[qc_po_ids.index(int(data.open_po_id))]
        temp_data['aaData'].append(OrderedDict(( ('Date', get_local_date(user, data.creation_date)), ('Supplier', data.open_po.supplier.name),
                                                 ('Seller ID', data.seller.seller_id), ('Seller Name', data.seller.name),
                                                 ('SKU Code', data.open_po.sku.sku_code), ('SKU Description', data.open_po.sku.sku_desc),
                                                 ('SKU Class', data.open_po.sku.sku_class), ('SKU Style Name', data.open_po.sku.style_name),
                                                 ('SKU Brand', data.open_po.sku.sku_brand), ('SKU Category', data.open_po.sku.sku_category),
                                                 ('Accepted Qty', accepted_quan), ('Rejected Qty', rejected_quan),
                                                 ('Total Qty', data.open_po.order_quantity), ('Amount', '%.2f' % amount),
                                                 ('Tax', data.open_po.tax), ('Total Amount', '%.2f' % total_amount),
                                                 ('DT_RowClass', 'results'), ('DT_RowAttr', {'data-id': data.id}) )))

    if stop_index and custom_search:
        if temp_data['aaData']:
            temp_data['aaData'] = apply_search_sort(temp_data['aaData'][0].keys(), temp_data['aaData'], order_term, '', col_num, exact=False)
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data

def get_grn_inventory_addition_data(search_params, user, sub_user):
    from miebach_admin.models import *
    from rest_api.views.common import get_sku_master, get_local_date, apply_search_sort
    sku_master, sku_master_ids = get_sku_master(user, sub_user)

    search_parameters = {}
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    temp_data = copy.deepcopy( AJAX_DATA )
    temp_data['draw'] = search_params.get('draw')
    result_values = ['purchase_order__order_id', 'receipt_number', 'purchase_order__open_po__sku__sku_code', 'seller_po__seller__seller_id',
                     'purchase_order__received_quantity', 'purchase_order__open_po__price', 'purchase_order__open_po__sgst_tax',
                     'purchase_order__open_po__cgst_tax', 'purchase_order__open_po__igst_tax', 'purchase_order__open_po__utgst_tax',
                     'seller_po__margin_percent', 'purchase_order__prefix', 'seller_po__unit_price']

    if 'from_date' in search_params:
        search_parameters['creation_date__gte'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date']  + datetime.timedelta(1), datetime.time())
        search_parameters['creation_date__lte'] = search_params['to_date']

    if 'open_po' in search_params and search_params['open_po']:
        temp = re.findall('\d+', search_params['open_po'])
        if temp:
            search_parameters['purchase_order__order_id'] = temp[-1]

    if 'sku_code' in search_params:
        search_parameters['seller_po__open_po__sku__wms_code'] = search_params['sku_code']


    search_parameters['seller_po__seller__user'] = user.id
    search_parameters['seller_po__open_po__sku_id__in'] = sku_master_ids
    damaged_ids = SellerStock.objects.filter(stock__location__zone__zone='DAMAGED_ZONE', seller__user=user.id, seller_po_summary__isnull=False).\
                                      values_list('seller_po_summary_id', flat=True)
    query_data = SellerPOSummary.objects.filter(**search_parameters).exclude(id__in=damaged_ids)
    model_data = query_data.values(*result_values).distinct().annotate(total_received=Sum('quantity'))

    temp_data['recordsTotal'] = model_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    purchase_orders = PurchaseOrder.objects.filter(open_po__sku__user=user.id)
    for data in model_data:
        result = purchase_orders.filter(order_id=data['purchase_order__order_id'],open_po__sku__user=user.id)[0]
        po_number = '%s%s_%s' %(data['purchase_order__prefix'], str(result.creation_date).split(' ')[0].replace('-', ''), data['purchase_order__order_id'])
        amount = float(data['total_received'] * data['purchase_order__open_po__price'])
        tax = float(data['purchase_order__open_po__sgst_tax']) + float(data['purchase_order__open_po__cgst_tax']) + float(data['purchase_order__open_po__igst_tax']) + float(data['purchase_order__open_po__utgst_tax'])
        aft_unit_price = float(data['purchase_order__open_po__price']) + (float(data['purchase_order__open_po__price']/100) * tax)
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
        temp_data['aaData'].append(OrderedDict(( ('Transaction ID', po_number + '-' + str(sku_code) + '/' + str(data['receipt_number'])),
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

    temp_data = copy.deepcopy( AJAX_DATA )
    temp_data['draw'] = search_params.get('draw')
    result_values = ['return_id', 'sku__sku_code', 'return_type']

    query_filter = {}
    if 'creation_date' in search_params and search_params['creation_date']:
        search_parameters['creation_date__gte'] = search_params['creation_date']
        to_date = datetime.datetime.combine(search_params['creation_date']  + datetime.timedelta(1), datetime.time())
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
            transaction_id = ('%s-%s-%s') % (str(order.order_id), str(seller_order.sor_id),transaction_id)
        elif order_return and order_return[0].order:
            order = order_return[0].order
            invoice_amount = (order.invoice_amount / order.quantity) * data['total_received']
            transaction_id = ('%s-%s') % (str(order.order_id), transaction_id)
        temp_data['aaData'].append(OrderedDict(( ('Transaction ID', transaction_id),
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

    temp_data = copy.deepcopy( AJAX_DATA )
    temp_data['draw'] = search_params.get('draw')

    if 'seller_id' in search_params:
        search_parameters['seller__seller_id'] = search_params['seller_id']


    search_parameters['seller__user'] = user.id
    search_parameters['stock__sku_id__in'] = sku_master_ids
    query_data = SellerStock.objects.filter(**search_parameters).exclude(stock__location__zone__zone='DAMAGED_ZONE')
    model_data = query_data.values('seller__seller_id', 'stock__sku__sku_code').distinct().annotate(total_received=Sum('quantity'))

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
        temp_data['aaData'].append(OrderedDict(( ('Transaction ID', transaction_id),
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



