import datetime
import time
from functools import wraps
from collections import OrderedDict
from django.db import models as django_models
from django.db.models import Sum
from models import *
import copy
import re

AJAX_DATA = {
  "draw": 0,
  "recordsTotal": 0,
  "recordsFiltered": 0,
  "aaData": [
  ]
}

NOW = datetime.datetime.now()
SKU_DATA = {'user': '', 'sku_code': '', 'wms_code': '',
            'sku_desc': '', 'sku_group': '', 'sku_type': '',
            'sku_category': '', 'sku_class': '', 'threshold_quantity': 0, 'zone_id': '',
            'status': 1, 'online_percentage': 0, 'qc_check': 0, 'creation_date': NOW, 
            'enable_serial_based': 0, 'block_for_po': ''}

SKU_STOCK_DATA = {'sku_id': '', 'total_quantity': 0,
            'online_quantity': 0, 'offline_quantity': 0}

SUPPLIER_DATA = {'name': '', 'address': '',
            'phone_number': '', 'email_id': '',
            'status': 1, 'creation_date': NOW}

ISSUE_DATA = {'issue_title': '', 'priority': '', 'status': 'Active',
            'issue_description': '', 'creation_date': NOW}

SUPPLIER_SKU_DATA = {'supplier_id': '', 'supplier_type': '',
        'sku': '','supplier_code':'', 'preference': '','moq': '', 'price': '',
             'creation_date': NOW}

UPLOAD_ORDER_DATA = {'order_id': '', 'title': '','user': '',
             'sku_id': '', 'status': 1, 'shipment_date': NOW, 'creation_date': NOW}


LOC_DATA = {'zone_id': '', 'location': '',
            'max_capacity': 0, 'fill_sequence': 0, 'pick_sequence': 0,
            'filled_capacity': 0, 'status': 1, 'creation_date': NOW}
ZONE_DATA = {'user': '', 'zone': '', 'creation_date': NOW}

ORDER_DATA = {'order_id': '', 'sku_id': '', 'title': '',
              'quantity': '', 'status': 1, 'creation_date': NOW}

RETURN_DATA = {'order_id': '', 'return_id': '', 'return_date': '',
              'quantity': '', 'status': 1, 'creation_date': NOW}

PALLET_FIELDS = {'pallet_code': '', 'quantity': 0, 'status': 1, 'creation_date': NOW}

CONFIRM_SALES_RETURN = {'order_id':'','sku_id':''}

CANCEL_ORDER_HEADERS = OrderedDict([('','id'),('Order ID','order_id'),('SKU Code','sku__sku_code'),('Customer ID','customer_id')])

PO_SUGGESTIONS_DATA = {'supplier_id': '', 'sku_id':'', 'order_quantity': '',
                       'price': 0, 'status': 1, 'creation_date': NOW}
PO_DATA = {'open_po_id': '', 'status': '', 'received_quantity': 0, 'creation_date': NOW}

ORDER_SHIPMENT_DATA = {'shipment_number': '', 'shipment_date': '', 'truck_number': '', 'shipment_reference': '', 'status': 1, 'creation_date': NOW}

SKU_FIELDS = ( (('WMS SKU Code *', 'wms_code',60), ('Product Description *', 'sku_desc',256)),
               (('SKU Type', 'sku_type',60), ('SKU Class', 'sku_class',60)),
               (('SKU Category', 'sku_category',60), ('SKU Group', 'sku_group')),
               (('Put Zone *', 'zone_id',60), ('Threshold Quantity *', 'threshold_quantity')),
               (('Status', 'status',11), ))

QUALITY_CHECK_FIELDS = {'purchase_order_id': '', 'accepted_quantity': 0,'rejected_quantity': 0, 'putaway_quantity': 0, 'status': 'qc_pending', 'reason': '', 'creation_date': NOW}

ORDER_PACKAGING_FIELDS = {'order_shipment_id':'', 'package_reference': '', 'status': 1, 'creation_date': NOW}

SHIPMENT_INFO_FIELDS = {'order_shipment_id':'', 'order': '', 'shipping_quantity': '', 'status': 1,'order_packaging_id': '', 'creation_date': NOW }

ADD_SKU_FIELDS = ( (('WMS SKU Code *', 'wms_code',60), ('Product Description *', 'sku_desc',256)),
                   (('SKU Type', 'sku_type',60), ('SKU Class', 'sku_class',60)),
                   (('SKU Category', 'sku_category',60), ('SKU Group', 'sku_group')),
                   (('Put Zone *', 'zone_id',60), ('Threshold Quantity *', 'threshold_quantity')),
                   (('Status', 'status',11), ))


RAISE_ISSUE_FIELDS = ( ('Issue Title', 'issue_title'),
               ('Priority', 'priority'),
               ('Issue Description', 'issue_description'), )

UPDATE_ISSUE_FIELDS = ( (('Issue Title', 'issue_title',60), ('Priority', 'priority',32)),
                    (('Issue Description', 'issue_description',256), ('Status', 'status',11)),
                      (('Resolved Description', 'resolved_description'),),   )


RESOLVED_ISSUE_FIELDS = ( (('Issue Title', 'issue_title',60), ('Priority', 'priority',32)),
                    (('Issue Description', 'issue_description',256), ('Status', 'status',11)),
                      (('Resolved Description', 'resolved_description'),),   )



SUPPLIER_FIELDS = ( (('Supplier Id *', 'id',60), ('Supplier Name *', 'name',256)),
                    (('Email *', 'email_id',64), ('Phone No. *', 'phone_number',10)),
                    (('Address *', 'address'), ('Status', 'status',11)), )

SKU_SUPPLIER_FIELDS = ( (('Supplier ID *', 'supplier_id',60), ('WMS Code *', 'wms_id','')),
                        (('Supplier Code','supplier_code'), ('Priority *', 'preference',32) ),
                        (('MOQ', 'moq',256,0), ('Price', 'price'), ) )

RAISE_PO_FIELDS = ( (('Supplier ID', 'supplier_id',11), ('PO Name', 'po_name',30)),
                    (('Ship To', 'ship_to',''), ) )

RAISE_PO_FIELDS1 = OrderedDict([('WMS Code *','wms_code'), ('Supplier Code', 'supplier_code'), ('Quantity *','order_quantity'),('Price','price')])

MOVE_INVENTORY_FIELDS = ( (('WMS Code *','wms_code'),('Source Location *','source_loc')),
                          (('Destination Location *','dest_loc'),('Quantity *','quantity')), )

ADJUST_INVENTORY_FIELDS = ( (('WMS Code *','wms_code'),('Location *','location')),
                            (('Physical Quantity *','quantity'),('Reason','reason')),)

MOVE_INVENTORY_UPLOAD_FIELDS = ['WMS Code', 'Source Location', 'Destination Location', 'Quantity']

SUPPLIER_HEADERS = ['Supplier Id', 'Supplier Name', 'Address', 'Email', 'Phone No.']

SALES_RETURN_HEADERS = ['Return ID', 'Return Date', 'SKU Code', 'Product Description', 'Market Place', 'Quantity']

SALES_RETURN_TOGGLE = ['Return ID', 'SKU Code', 'Product Description', 'Shipping Quantity', 'Return Quantity', 'Damaged Quantity' ]

RETURN_DATA_FIELDS = ['sales-check', 'order_id', 'sku_code', 'customer_id', 'shipping_quantity', 'return_quantity', 'damaged_quantity', 'delete-sales']

SUPPLIER_SKU_HEADERS = ['Supplier Id', 'WMS Code', 'Preference', 'MOQ','Price']

MARKETPLACE_SKU_HEADERS = ['WMS Code', 'Flipkart SKU', 'Snapdeal SKU', 'Paytm SKU', 'Amazon SKU', 'HomeShop18 SKU', 'Jabong SKU', 'Indiatimes SKU', 'Myntra SKU', 'Voonik SKU', 'Campus Sutra SKU', 'Flipkart Description', 'Snapdeal Description', 'Paytm Description', 'HomeShop18 Description', 'Jabong Description', 'Indiatimes Description', 'Amazon Description']

PURCHASE_ORDER_HEADERS = ['PO Name', 'PO Date(MM-DD-YYYY)', 'Supplier ID', 'WMS SKU Code', 'Quantity', 'Price', 'Ship TO']

LOCK_FIELDS = ['', 'Inbound', 'Outbound', 'Inbound and Outbound']

LOCATION_FIELDS = ( (('Zone ID *', 'zone_id'),('Location *', 'location')),
                    (('Capacity', 'max_capacity'), ('Put Sequence', 'fill_sequence')),
                    ( ('Get Sequence', 'pick_sequence'), ('Status', 'status')),
                    (('Location Lock', 'lock_status'), ('SKU Group', 'location_group')) )

USER_FIELDS = ( (('User Name *', 'username'),('Name *', 'first_name')),
                (('Groups', 'groups'),),)

ADD_USER_FIELDS = ( (('User Name *', 'username'),('First Name *', 'first_name')),
                    (('Last Name', 'last_name'), ('Email', 'email')),
                    (('Password *', 'password'), ('Re-type Password', 're_password')),)

WAREHOUSE_USER_FIELDS = ( (('User Name *', 'username'),('First Name *', 'first_name')),
                          (('Last Name', 'last_name'), ('Phone Number', 'phone_number')),
                          (('Email', 'email'), ('Password *', 'password')),
                          (('Re-type Password', 're_password'), ('Country', 'country')),
                          (('State', 'state'), ('City', 'city')),
                          (('Address', 'address'), ('Pincode', 'pin_code')),
                        )

WAREHOUSE_UPDATE_FIELDS = ( (('User Name', 'username'),('First Name', 'first_name')),
                          (('Last Name', 'last_name'), ('Phone Number', 'phone_number')),
                          (('Email', 'email'), ('Country', 'country')),
                          (('State', 'state'), ('City', 'city')),
                          (('Address', 'address'), ('Pincode', 'pin_code')),
                        )

ADD_GROUP_FIELDS = ( (('Group Name *', 'group'),('Permissions', 'permissions')),)

SHIPMENT_FIELDS = ( (('Shipment Number *', 'shipment_number'),('Shipment Date *', 'shipment_date')),
                    (('Truck Number *', 'truck_number'), ('Shipment Reference *', 'shipment_reference')),
                    (('Customer ID', 'customer_id'), ('Market Place', 'marketplace')) )



CREATE_ORDER_FIELDS = ( (('Customer ID *', 'customer_id'), ('Customer Name', 'customer_name')),
                    (('Telephone', 'telephone'),('Shipment Date *','shipment_date')),
                    (('Address', 'address'), ('Email', 'email_id'))  )

CREATE_ORDER_FIELDS1 = OrderedDict([('SKU Code/WMS Code *','sku_id'),('Quantity','quantity'), ('Invoice Amount', 'invoice_amount')])

SALES_RETURN_FIELDS = ( (('Return Tracking ID', 'scan_return_id'), ('SKU Code', 'return_sku_code')), )

MARKETPLACE_SKU_FIELDS = {'marketplace_code': '', 'sku_id': '', 'description': '',
                          'sku_type': '', 'creation_date': NOW}

MARKET_LIST_HEADERS = ['Market Place', 'SKU', 'Description']

MARKETPLACE_LIST = ['Flipkart', 'Snapdeal', 'Paytm', 'Amazon', 'Shopclues', 'HomeShop18', 'Jabong', 'Indiatimes']

ORDER_HEADERS = ['Order ID', 'Title', 'SKU Code', 'Quantity','Shipment Date(yyyy-mm-dd)']

REPORT_FIELDS = ( (('From Date', 'from_date'),('To Date', 'to_date')),
                    (('SKU Code', 'sku_code'), ('SKU Category', 'sku_category')),
                    (('SKU Type', 'sku_type'), ('SKU Class', 'sku_class')) )

SKU_LIST_REPORTS_DATA = {('sku_list_form','reportsTable','SKU List Filters','sku-list', 1, 2, 'sku-report') : (['SKU Code', 'WMS Code', 'SKU Group', 'SKU Type', 'SKU Category', 'SKU Class', 'Put Zone', 'Threshold Quantity'],( (('SKU Code', 'sku_code'), ('SKU Category', 'sku_category')), (('SKU Type', 'sku_type'), ('SKU Class', 'sku_class')),(('WMS Code','wms_code'),))),}

LOCATION_WISE_FILTER = {('location_wise_form', 'locationTable', 'Location Wise Filters', 'location-wise', 3, 4, 'location-report') : (['Location', 'SKU Code', 'WMS Code', 'Product Description', 'Zone', 'Receipt Number', 'Receipt Date', 'Quantity'], ( (('SKU Code', 'sku_code'), ('SKU Category', 'sku_category')), (('SKU Type', 'sku_type'), ('SKU Class', 'sku_class')), (('Location','location'), ('Zone','zone_id')),(('WMS Code', 'wms_code'),), )),}

SUPPLIER_WISE_POS = {('supplier_wise_form', 'suppliertable', 'Supplier Wise Filters', 'supplier-wise', 1, 2, 'supplier-report'): (['Order Date', 'PO Number', 'Supplier Name', 'WMS Code', 'Design', 'Ordered Quantity', 'Received Quantity', 'Status'], ((('Supplier', 'supplier'),), )),}

GOODS_RECEIPT_NOTE = {('receipt_note_form', 'receiptTable', 'Goods Receipt Filter', 'receipt-note', 11, 12, 'po-report'): (['PO Number', 'Supplier ID', 'Supplier Name', 'Total Quantity'], ( (('From Date', 'from_date'),('To Date', 'to_date')), (('PO Number', 'open_po'), ('WMS Code','wms_code') ), )),}

RECEIPT_SUMMARY = {('receipt_summary_form', 'summaryTable', 'Receipt Summary', 'summary-wise', 5, 6, 'receipt-report'): (['Supplier', 'PO Reference', 'WMS Code', 'Description', 'Received Quantity'], ( (('From Date', 'from_date'),('To Date', 'to_date')), (('WMS Code', 'wms_code'), ('Supplier', 'supplier')),(('SKU Code','sku_code'),), )),}

DISPATCH_SUMMARY = {('dispatch_summary_form', 'dispatchTable', 'Dispatch Summary', 'dispatch-wise', 13, 14, 'dispatch-report'): (['Order ID', 'WMS Code', 'Description', 'Location', 'Quantity', 'Picked Quantity', 'Date', 'Time'], ( (('From Date', 'from_date'),('To Date', 'to_date')), (('WMS Code', 'wms_code'),('SKU Code','sku_code') )) ),}

SKU_WISE_STOCK = {('sku_wise_form','skustockTable','SKU Wise Stock Summary','sku-wise', 1, 2, 'sku-wise-report') : (['SKU Code', 'WMS Code', 'Product Description', 'SKU Category', 'Total Quantity'],( (('SKU Code', 'sku_code'), ('SKU Category', 'sku_category')), (('SKU Type', 'sku_type'), ('SKU Class', 'sku_class')),(('WMS Code','wms_code'),))),}

SKU_WISE_PURCHASES =  {('sku_wise_purchase','skupurchaseTable','SKU Wise Purchase Orders','sku-purchase-wise', 1, 2, 'sku-wise-purchase-report') : (['PO Date', 'Supplier', 'SKU Code', 'Order Quantity', 'Received Quantity', 'Receipt Date', 'Status'],( (('WMS SKU Code', 'wms_code'),),)),}

SALES_RETURN_REPORT = {('sales_return_form','salesreturnTable','Sales Return Reports','sales-report', 1, 2, 'sales-return-report') : (['SKU Code', 'Order ID', 'Customer ID', 'Return Date', 'Status', 'Quantity'],( (('SKU Code', 'sku_code'), ('WMS Code', 'wms_code')), (('Order ID', 'order_id'), ('Customer ID', 'customer_id')),(('Date','creation_date'),))),}

INVENTORY_ADJUST_REPORT = {('inventory_adjust_form','inventoryadjustTable','Inventory Adjustment Reports','adjustment-report', 1, 2, 'inventory-adjust-report') : (['SKU Code', 'Location', 'Quantity', 'Date', 'Remarks'],( (('From Date', 'from_date'),('To Date', 'to_date')), (('SKU Code', 'sku_code'), ('WMS Code', 'wms_code')), (('Location', 'location'),),   )),}

INVENTORY_AGING_REPORT = {('inventory_aging_form','inventoryagingTable','Inventory Aging Reports','aging-report', 1, 2, 'inventory-aging-report') : (['SKU Code', 'SKU Description', 'SKU Category', 'Location', 'Quantity', 'As on Date(Days)'],( (('From Date', 'from_date'),('To Date', 'to_date')), (('SKU Code', 'sku_code'), ('SKU Category', 'sku_category')),   )),}

LOCATION_HEADERS = ['Zone', 'Location', 'Capacity', 'Put sequence', 'Get sequence', 'SKU Group']

SKU_HEADERS = ['WMS Code','SKU Description', 'SKU Group', 'SKU Type', 'SKU Category', 'SKU Class', 'Put Zone', 'Threshold Quantity', 'Status']

EXCEL_HEADERS = ['Receipt Number', 'Receipt Date',  'WMS SKU', 'Location', 'Quantity', 'Receipt Type']
EXCEL_RECORDS = ('receipt_number', 'receipt_date', 'wms_code', 'location', 'wms_quantity', 'receipt_type')

SKU_EXCEL = ('wms_code', 'sku_desc', 'sku_group', 'sku_type', 'sku_category', 'sku_class', 'zone_id', 'threshold_quantity', 'status')

PICKLIST_FIELDS = { 'order_id': '', 'picklist_number': '', 'reserved_quantity': '', 'picked_quantity': 0, 'remarks': '', 'status': 'open'}
PICKLIST_HEADER = ('ORDER ID', 'WMS Code', 'Title', 'Zone', 'Location', 'Reserved Quantity', 'Picked Quantity')

PICKLIST_HEADER1 = ('WMS Code', 'Title','Zone', 'Location', 'Reserved Quantity', 'Picked Quantity','')

PRINT_PICKLIST_HEADERS = ('WMS Code', 'Title', 'Zone', 'Location', 'Reserved Quantity', 'Picked Quantity','Stock Left')

PICKLIST_EXCEL = OrderedDict(( ('WMS Code', 'wms_code'), ('Title', 'title'), ('Zone', 'zone'), ('Location', 'location'),
                               ('Reserved Quantity', 'reserved_quantity')))

PROCESSING_HEADER = ('WMS Code', 'Title', 'Zone', 'Location', 'Reserved Quantity', 'Picked Quantity', '')

SKU_SUPPLIER_MAPPING = OrderedDict([('Supplier ID','supplier_id'),('SKU CODE','sku__wms_code'),('Supplier Code', 'supplier_code'),('Priority','preference'),('MOQ','moq')])

SUPPLIER_MASTER_HEADERS = OrderedDict([('Supplier ID','id'),('Name','name'),('Address','address'),('Phone Number','phone_number'),('Email','email_id'),('Status','status')])


STOCK_DET = ([('0','receipt_number'),('1','receipt_date'),('2','sku_id__sku_code'),('3','sku_id__wms_code'),('4','sku_id__sku_desc'),('5','location_id__zone'),('6','location_id__location'),('7','quantity')])

ORDER_DETAIL_HEADERS = OrderedDict([('Order ID','order_id'),('SKU Code','sku_id__sku_code'),('Title','title'),('Product Quantity','quantity'),('Shipment Date','shipment_date')])

PICK_LIST_HEADERS = OrderedDict([('Picklist ID','picklist_number'),('Picklist Note','remarks'),('Date','creation_date')])

PO_SUGGESTIONS = OrderedDict([('0','creation_date'),('1','supplier_id'),('2','sku_id'),('3','order_quantity'),('4','price'),('5','status')])

RECEIVE_PO_HEADERS = OrderedDict([('Order ID','order_id'),('Order Date','creation_date'),('Supplier ID','open_po_id__supplier_id__id'),('Supplier Name','open_po_id__supplier_id__name')])

STOCK_DETAIL_HEADERS = OrderedDict([('SKU Code','sku_id__sku_code'),('WMS Code','sku_id__wms_code'),('Product Description','sku_id__sku_desc'),('Quantity','quantity')])

CYCLE_COUNT_HEADERS = OrderedDict([('WMS Code','sku_id__wms_code'),('Zone','location_id__zone'),('Location','location_id__location'),('Quantity','quantity')])

BATCH_DATA_HEADERS = OrderedDict([('SKU Code','sku__sku_code'),('Title','title'),('Total Quantity','quantity')])

PUT_AWAY = OrderedDict([('PO Number','open_po_id'),('Order Date','creation_date'),('Supplier ID','open_po_id__supplier_id__id'),('Supplier Name','open_po_id__supplier_id__name')])

SKU_MASTER_HEADERS = OrderedDict([('WMS SKU Code', 'wms_code'), ('Product Description', 'sku_desc'), ('SKU Type', 'sku_type'), ('SKU Category', 'sku_category'), ('SKU Class', 'sku_class'), ('Zone', 'zone_id'), ('Status', 'status')])

QUALITY_CHECK = OrderedDict([('Purchase Order ID','purchase_order__order_id'),('Supplier ID','purchase_order__open_po__supplier_id'),('Supplier Name',  'purchase_order__open_po__supplier__name'),('Total Quantity','purchase_order__received_quantity')])

SHIPMENT_INFO = OrderedDict([('',id),('Customer ID','order__customer_id'),('Customer Name','order__customer_name')])

CYCLE_COUNT_FIELDS = {'cycle': '', 'sku_id': '', 'location_id': '',
                   'quantity': '', 'seen_quantity': '',
                   'status': 1, 'creation_date': '', 'updation_date': ''}

INVENTORY_FIELDS =  {'cycle_id': '', 'adjusted_location': '',
                   'adjusted_quantity': '', 'reason': 'Moved Successfully',
                    'creation_date': '', 'updation_date': ''}

BACK_ORDER_TABLE = [ 'WMS Code', 'Ordered Quantity', 'Stock Quantity', 'Transit Quantity', 'Procurement Quantity']

BACK_ORDER_RM_TABLE = [ 'WMS Code', 'Ordered Quantity', 'Stock Quantity', 'Transit Quantity', ' Procurement Quantity']

BACK_ORDER_HEADER = ['Supplier Name', 'WMS Code', 'Title', 'Quantity', 'Price']

QC_WMS_HEADER = ['Purchase Order', 'Quantity', 'Accepted Quantity', 'Rejected Quantity']

REJECT_REASONS = ['Color Mismatch', 'Price Mismatch', 'Wrong Product', 'Package Damaged', 'Product Damaged', 'Others']

QC_SERIAL_FIELDS = {'quality_check_id': '', 'serial_number_id': '', 'status': '','reason': '', 'creation_date': NOW}

RAISE_JO_HEADERS = OrderedDict([('Product SKU Code', 'product_code'), ('Product SKU Quantity', 'product_quantity'),
                                ('Material SKU Code', 'material_code'), ('Material SKU Quantity', 'material_quantity')])

JO_PRODUCT_FIELDS = {'product_quantity': 0, 'received_quantity': 0, 'job_code': 0, 'jo_reference': '','status': 'open', 'product_code_id': '',
                     'creation_date': NOW}

JO_MATERIAL_FIELDS = {'material_code_id': '', 'job_order_id': '', 'material_quantity': '', 'status': 1, 'creation_date': NOW}

RAISE_JO_TABLE_HEADERS = ['JO Reference', 'Creation Date']

RM_CONFIRMED_HEADERS = ['Job Code ', 'Creation Date', 'Order Type']

MATERIAL_PICKLIST_FIELDS = {'jo_material_id': '', 'status': 'open', 'reserved_quantity': 0, 'picked_quantity': 0, 'creation_date': NOW}

MATERIAL_PICK_LOCATIONS = {'material_picklist_id': '', 'stock_id': '', 'quantity': 0, 'status': 1, 'creation_date': NOW}

RECEIVE_JO_TABLE = [' Job Code', 'Creation Date', 'Receive Status']

RECEIVE_JO_TABLE_HEADERS = ['WMS CODE', 'JO Quantity', 'Received Quantity', 'Stage']

GRN_HEADERS = ('WMS CODE', 'Order Quantity', 'Received Quantity')

PUTAWAY_JO_TABLE_HEADERS = ['  Job Code', 'Creation Date']

PUTAWAY_HEADERS = ['WMS CODE', 'Location', 'Original Quantity', 'Putaway Quantity', '']

CUSTOMER_MASTER_HEADERS = [' Customer ID', 'Customer Name', 'Email', 'Phone Number', 'Address', 'Status']

CUSTOMER_FIELDS = ( (('Customer ID *', 'id',60), ('Customer Name *', 'name',256)),
                    (('Email *', 'email_id',64), ('Phone No. *', 'phone_number',10)),
                    (('Address *', 'address'), ('Status', 'status',11)), )

CUSTOMER_DATA = {'name': '', 'address': '', 'phone_number': '', 'email_id': '', 'status': 1, 'creation_date': NOW}

PRODUCTION_STAGES = {'Apparel': ['', 'Raw Material Inspection', 'Fabric Washing', 'Finishing'], 'Default': ['', 'Raw Material Inspection',
                     'Fabric Washing', 'Finishing']}

STATUS_TRACKING_FIELDS = {'status_id': '', 'status_type': '', 'status_value': '', 'creation_date': NOW}

BOM_TABLE_HEADERS = ['Product SKU Code', 'Product Description']

BOM_UPLOAD_EXCEL_HEADERS = ['Product SKU Code', 'Material SKU Code', 'Material Quantity', 'Unit of Measurement' ]

COMBO_SKU_EXCEL_HEADERS = ['SKU Code', 'Combo SKU']

ADD_BOM_HEADERS = OrderedDict([('Material SKU Code', 'material_sku'), ('Material Quantity', 'material_quantity'),
                               ('Unit of Measurement', 'unit_of_measurement')])

ADD_BOM_FIELDS = {'product_sku_id': '', 'material_sku_id': '', 'material_quantity': 0, 'unit_of_measurement': '', 'creation_date': NOW}

UOM_FIELDS = ['KGS', 'UNITS', 'METERS', 'SHEETS']

MAIL_REPORTS = { 'sku_list': ['SKU List'], 'location_wise_stock': ['Location Wise SKU'], 'receipt_note': ['Receipt Summary'], 'dispatch_summary': ['Dispatch Summary'], 'sku_wise': ['SKU Wise Stock'] }

MAIL_REPORTS_DATA = {'Raise PO': 'raise_po', 'Receive PO': 'receive_po', 'Orders': 'order', 'Dispatch': 'dispatch'}

REPORTS_DATA = {'SKU List': 'sku_list', 'Location Wise SKU': 'location_wise_stock', 'Receipt Summary': 'receipt_note', 'Dispatch Summary': 'dispatch_summary', 'SKU Wise Stock': 'sku_wise'}

SKU_CUSTOMER_FIELDS = ( (('Customer ID *', 'customer_id',60), ('Customer Name *', 'customer_name',256)),
                        (('SKU Code *','sku_code'), ('Price *', 'price'), ) )

CUSTOMER_SKU_DATA = {'customer_name_id': '', 'sku_id': '',
            'price': '', 'creation_date': NOW}

CUSTOMER_SKU_MAPPING_HEADERS = OrderedDict([('Customer ID','customer_name__id'),('Customer Name','customer_name__name'),
                                            ('SKU Code','sku__sku_code'),('Price','price')])

SHOPCLUES_EXCEL = {'order_id': 1, 'quantity': 5, 'title': 3, 'invoice_amount': 20, 'address': 11, 'customer_name': 10,
                   'marketplace': 'Shopclues', 'sku_code': 15}

FLIPKART_EXCEL = {'order_id': 6, 'quantity': 14, 'title': 2, 'invoice_amount': 17, 'address': 22, 'customer_name': 21,
                  'marketplace': 'Flipkart', 'sku_code': 8}

FLIPKART_EXCEL1 = {'order_id': 6, 'quantity': 14, 'title': 2, 'invoice_amount': 16, 'address': 21, 'customer_name': 20,
                  'marketplace': 'Flipkart', 'sku_code': 8}

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

ORDER_DEF_EXCEL = {'order_id': 0, 'quantity': 3, 'title': 1, 'shipment_date': 4,'sku_code': 2, 'marketplace': ''}

JABONG_EXCEL = {'order_id': 1, 'title': 7, 'invoice_amount': 14, 'marketplace': 'Jabong', 'sku_code': 5, 'quantity': 9}

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

MYNTRA_EXCEL = {'invoice_amount': 14, 'marketplace': 'Myntra', 'sku_code': 2, 'quantity': 9, 'title': 7}

COMBO_SKU_HEADERS = ['Combo SKU Code', 'Description']

ADJUST_INVENTORY_EXCEL_HEADERS = ['WMS Code', 'Location', 'Physical Quantity', 'Reason']

EXCEL_REPORT_MAPPING = {'dispatch_summary': 'get_dispatch_data', 'sku_list': 'get_sku_filter_data', 'location_wise': 'get_location_stock_data',
                        'goods_receipt': 'get_po_filter_data', 'receipt_summary': 'get_receipt_filter_data',
                        'sku_stock': 'print_sku_wise_data', 'sku_wise_purchases': 'sku_wise_purchase_data',
                        'supplier_wise': 'get_supplier_details_data', 'sales_report': 'get_sales_return_filter_data',
                        'inventory_adjust_report': 'get_adjust_filter_data', 'inventory_aging_report': 'get_aging_filter_data',
                        'rm_picklist_report': 'get_rm_picklist_data'}

SKU_GROUP_FIELDS = {'group': '', 'user': '', 'creation_date': NOW}

LOCATION_GROUP_FIELDS = {'group': '', 'location_id': '', 'creation_date': NOW}

RAISE_ST_FIELDS = ( (('Warehouse Name', 'warehouse_name',60), ), )

RAISE_ST_FIELDS1 = OrderedDict([('WMS Code *','wms_code'), ('Quantity *','order_quantity'),
                                ('Price','price')])

OPEN_STOCK_HEADERS = ['Warehouse Name', 'Total Quantity']

OPEN_ST_FIELDS = {'warehouse_id': '', 'order_quantity': 0, 'price': 0, 'sku_id': '', 'status': 1, 'creation_date': NOW}

STOCK_TRANSFER_FIELDS = {'order_id': '', 'invoice_amount': 0, 'quantity': 0, 'shipment_date': NOW, 'st_po_id': '', 'sku_id': '', 'status': 1}

STOCK_TRANSFER_HEADERS = ['Warehouse Name', 'Stock Transfer ID', 'SKU Code', 'Quantity']

VIEW_STOCK_TRANSFER = OrderedDict([('WMS Code','wms_code'), ('Quantity','quantity'), ('Price','price')])

ST_ORDER_FIELDS = {'picklist_id': '', 'stock_transfer_id': ''}

WAREHOUSE_HEADERS = ['Username', 'Name', 'Email', 'City']

ADD_USER_DICT = {'username': '', 'first_name': '', 'last_name': '', 'password': '', 'email': ''}

ADD_WAREHOUSE_DICT = {'user_id': '', 'city': '', 'is_active': 1, 'country': '', u'state': '', 'pin_code': '', 'address': '',
                      'phone_number': '', 'prefix': '', 'location': ''}


ADD_DISCOUNT_FIELDS = ( (('SKU Code *','sku_code'),('SKU Discount *','sku_discount')),
                            (('Category *','category'),('Category Discount *','category_discount')),)

DISCOUNT_HEADERS = ['SKU Code', 'SKU Category', 'SKU Discount', 'Category Discount']

VENDOR_HEADERS = ['Vendor ID', 'Name', 'Address', 'Phone Number', 'Email', 'Status']

VENDOR_FIELDS = ( (('Vendor ID *', 'vendor_id',60), ('Vendor Name *', 'name',256)),
                    (('Email *', 'email_id',64), ('Phone No. *', 'phone_number',10)),
                    (('Address *', 'address'), ('Status', 'status',11)), )

VENDOR_DATA = {'vendor_id': '', 'name': '', 'address': '', 'phone_number': '', 'email_id': '', 'status': 1, 'creation_date': NOW}

RWO_FIELDS = {'vendor_id': '', 'job_order_id': '', 'status': 1, 'creation_date': NOW}

RWO_PURCHASE_FIELDS = {'purchase_order_id': '', 'rwo_id': '', 'creation_date': NOW}

SHIPMENT_STATUS = ['Dispatched', 'In Transit', 'Out for Delivery', 'Delivered']

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

def create_po_reports_table(headers, data, user_profile, supplier):
    order_date = (str(NOW).split(' ')[0]).split('-')
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

def get_sku_filter_data(search_params, user):
    from models import *
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
    sku_master = SKUMaster.objects.filter(**search_parameters)

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


def get_location_stock_data(search_params, user):
    from models import *
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

def get_receipt_filter_data(search_params, user):
    from models import *
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


def get_dispatch_data(search_params, user):
    from models import *
    from views import *
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

def sku_wise_purchase_data(search_params, user):
    from models import *
    from itertools import chain
    data_list = []
    received_list = []
    temp_data = copy.deepcopy( AJAX_DATA )
    search_parameters = {}

    if 'wms_code' in search_params:
        search_parameters['open_po__sku__wms_code'] = search_params['wms_code']

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    search_parameters['open_po__sku__user'] = user.id
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
        temp = OrderedDict(( ('PO Date', str(data.po_date).split('+')[0]), ('Supplier', data.open_po.supplier.name),
                             ('SKU Code', data.open_po.sku.wms_code), ('Order Quantity', data.open_po.order_quantity),
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

def get_po_filter_data(search_params, user):
    from models import *
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
