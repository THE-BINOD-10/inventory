from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import auth
from django.views.decorators.csrf import csrf_exempt
from miebach_admin.models import *
from miebach_admin.custom_decorators import login_required
from collections import OrderedDict
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from itertools import chain
from django.db.models import Sum, Count
from rest_api.views.common import get_local_date, folder_check
from rest_api.views.miebach_utils import MILKBASKET_BULK_ZONE, MILKBASKET_USERS
from rest_api.views.integrations import *
import json
import datetime
import os
from django.db.models import Q, F
from django.core.serializers.json import DjangoJSONEncoder
from rest_api.views.utils import *

today = datetime.datetime.now().strftime("%Y%m%d")
log = init_logger('logs/integrations_' + today + '.log')
log_err = init_logger('logs/integration_errors.log')
storehippo_log = init_logger('logs/storehippo_' + today + '.log')
create_order_storehippo_log = init_logger('logs/storehippo_create_order_log_' + today + '.log')
create_update_sku_storehippo_log = init_logger('logs/storehippo_create_update_log_' + today + '.log')
order_edit_storehippo_log = init_logger('logs/order_edit_storehippo_log_' + today + '.log')

# Create your views here.

NOW = datetime.datetime.now()

def return_response(data, content_type='application/json'):
    return HttpResponse(json.dumps(data, cls=DjangoJSONEncoder), content_type=content_type)

def decide_and_return_response(request, **kwargs):

    status = ''
    if 'refresh' in request.POST.keys():
        status = request.POST.get('refresh', '')
    data = kwargs.get('data', {})
    if kwargs.get('scroll'):
        data = scroll_data(request, kwargs.get('data', {}))
    if status:
        return return_response(data)
    return data

def scroll_data(request, obj_lists, limit='', request_type='POST'):
    #if not obj_lists: return {}
    items, page_num = 10, 1
    if limit:
        items = limit
    if request_type == 'body':
        request_data = json.loads(request.body)
    elif request_type == 'POST':
        request_data = request.POST.dict()
    else:
        request_data = request.GET.dict()
    if 'items' in request_data.keys():
        items = request_data.get('items', items)
    if 'pagenum' in request_data.keys():
        page_num = int(request_data.get('pagenum', page_num))
    paginator = Paginator(obj_lists, items)

    if items:
        try:
            records = paginator.page(page_num)
        except PageNotAnInteger:
            page_num = 1
            records = paginator.page(page_num)
        except EmptyPage:
            page_num = paginator.num_pages
            records = paginator.page(paginator.num_pages)
    else:
        records = stock_list
    page_info = {'page_info': {'current_page': page_num,'total_pages': paginator.num_pages}}
    page_info.update({'data': records.object_list})
    return page_info


@csrf_exempt
def authenticate_user(request):
    data = {'status': 'fail'}
    username = request.POST.get('username')
    passwd = request.POST.get('password')
    if not username or not passwd:
        return return_response(data)

    user = authenticate(username=username, password=passwd)
    if not user:
        user = authenticate(username=username, password=passwd)
    '''
    if user and user.is_authenticated():
        data['status'] = 'warning'
        data['reason'] = 'Please reset your password'
        return return_response(data)

    user = authenticate(username=username, password=passwd)
    '''

    if user and user.is_authenticated():
        login(request, user)
        session_key = request.session._get_session_key()
        if session_key:
            data['status'] = 'success'
            data['session_key'] = session_key
            data['username'] = user.username

    return return_response(data)

def create_password(request):
    data = {'status': 'fail'}
    username = request.POST.get('username')
    password = request.POST.get('password')
    password2 = request.POST.get('password2')
    if password != password2:
        data['reason'] = 'Password did not match'
        return return_response(data)

    user = User.objects.get(username=username)
    if not user:
        data['reason'] = 'User is not registered'
        return return_response(data)

    user.set_password(password)
    user.save()
    data['status'] = 'success'
    data['message'] = 'Password changed successfully'
    return return_response(data)

@csrf_exempt
def get_zones_count(request):
    zone_list = []
    filter_params = {'zone__user': request.user.id}
    locations = LocationMaster.objects.exclude(zone__zone='TEMP_ZONE').filter(**filter_params)

    locations_count = {}
    for location in locations:
        stock_data = StockDetail.objects.filter(location_id=location.id,location__zone__user=request.user.id, quantity__gt=0)
        total_stock = 0
        for stock in stock_data:
            total_stock += stock.quantity

        if total_stock > location.max_capacity:
            location.max_capacity = total_stock
        loc_count = locations_count.setdefault(location.zone.zone, [0, 0])
        locations_count[location.zone.zone] = [loc_count[0] + total_stock, loc_count[1] + (location.max_capacity - total_stock)]

    for key, value in locations_count.iteritems():
        zone_list.append(OrderedDict(( ('Zone', key), ('Total Capacity', value[0] + value[1]), ('Free Capacity', value[1]) )))

    return decide_and_return_response(request= request, data= zone_list, scroll= True)

@csrf_exempt
def open_po(request):

    supplier_data = []
    results = PurchaseOrder.objects.exclude(open_po__isnull=True).filter(status__in=['','grn-generated'], open_po__sku__user=request.user.id).order_by('-po_date').values('order_id').distinct()

    for result in results:
        suppliers = PurchaseOrder.objects.filter(status='', order_id=result['order_id'], open_po__sku__user=request.user.id)
        for supplier in suppliers[:1]:
            po_number = '%s%s_%s' %(supplier.prefix, str(supplier.creation_date).split(' ')[0].replace('-', ''), supplier.order_id)
            supplier_data.append(OrderedDict(( ('Supplier ID', supplier.open_po.supplier.id), ('PO Number', po_number), ('Supplier Name', supplier.open_po.supplier.name), ('Order ID', supplier.order_id), ('Order Date', str(supplier.creation_date).split('+')[0]) )))

    return decide_and_return_response(request, data=supplier_data, scroll=True)

@csrf_exempt
def dashboard_api(request):
    data = {}
    data['results'] = OrderedDict()
    data['results']['Purchase Orders'] = {}
    data['results']['Free Locations List'] ={}
    data['results']['Stock Summary List'] = {}
    data['results']['Shipment Tracker List'] = {}
    data['results']['Today Transactions List'] = {}
    data['results']['Sales Return List'] = {}
    data['total_results'] = len(data['results'])
    return return_response(data)

@csrf_exempt
def get_stock_count(request):
    stock_list = []
    sku_records = SKUMaster.objects.filter(user = request.user.id)

    stock_objs = StockDetail.objects.filter(sku__user=request.user.id, quantity__gt=0).values('sku_id').distinct().\
                                     annotate(in_stock=Sum('quantity'))

    stocks = map(lambda d: d['sku_id'], stock_objs)
    for sku in sku_records:
        stock_quantity = 0
        if sku.id in stocks:
            data_value = map(lambda d: d['in_stock'], stock_objs)[stocks.index(sku.id)]
            if data_value:
                stock_quantity = data_value
        stock_dict = OrderedDict(( ('SKU Code', sku.sku_code),
                                   ('WMS Code', sku.wms_code),
                                   ('Product Description', sku.sku_desc),
                                   ('Quantity', stock_quantity) ))
        if stock_dict['Quantity'] > 0:
            stock_list.append(stock_dict)

    return decide_and_return_response(request, data=stock_list, scroll=True)


@csrf_exempt
def stock_search(request):
    data ={}
    post_data = {}
    post_data1 = {}
    sku_master = []
    for key, value in request.POST.iteritems():
        if key == 'pagenum':
            continue
        if key not in ['session_key', 'refresh'] and value != '':
            if key == 'sku_desc':
                post_data['sku_desc__icontains'] = value
            else:
                post_data[key] = value
    for key, value in post_data.iteritems():
        post_data1['sku__' + key] = value
    post_data1['sku__user'] = request.user.id
    post_data1['quantity__gt'] = 0
    stock_list = []
    sku_records = StockDetail.objects.filter(**post_data1).values('sku_id', 'sku__sku_code', 'sku__wms_code', 'sku__sku_desc').distinct().\
                                      annotate(total=Sum('quantity')).order_by('-total')[0:20]
    exclude_ids = map(lambda d: d['sku_id'], sku_records)
    if post_data:
        post_data['user'] = request.user.id
        sku_master = SKUMaster.objects.exclude(id__in=exclude_ids).filter(**post_data).values('sku_code', 'wms_code', 'sku_desc')
    if not sku_records:
        stock_list = []
    for sku in sku_records:
        stock_list.append(OrderedDict(( ('SKU Code', sku['sku__sku_code']),
                                   ('WMS Code', sku['sku__wms_code']),
                                   ('Product Description', sku['sku__sku_desc']),
                                   ('Quantity', sku['total']) ))  )
    for sku in sku_master:
        stock_list.append(OrderedDict(( ('SKU Code', sku['sku_code']),
                                   ('WMS Code', sku['wms_code']),
                                   ('Product Description', sku['sku_desc']),
                                   ('Quantity', 0) ))  )
    return decide_and_return_response(request, data=stock_list, scroll=True)

#SHIPMENT TRACKER API's

@csrf_exempt
def shipment_tracker_level1(request):
    status_code = request.POST.get('status_code')
    output_data = get_shipment_info(request, True, status_code)
    new_list = []
    all_data = OrderedDict()

    for record in output_data:
        cond = (record['Shipment Id'], record['Customer Name'])
        all_data.setdefault(cond, [0,0])
        all_data[cond][0] += 1
        all_data[cond][1] += record['Order Qty']
    for key, value in all_data.iteritems():
        new_dict = OrderedDict(( ('Order Number', key[0] ),
                                 ('Customer Name', key[1]),
                                 ('Number of Order Lines',  value[0]),
                                 ('Total Quantity', value[1] ),
                                 ('Total Weight',0 ) ))

        new_list.append(new_dict)
    return decide_and_return_response(request, data=new_list, scroll=True)

@csrf_exempt
def shipment_tracker_level2(request):
    order_id = request.POST.get('shipment_tracker_id')
    output_data = get_shipment_info(request, False, request.POST.get('status_code'), {'order_id': order_id})
    order_list = []
    order_detail_dict = {}

    for record in output_data:
        if str(record['Shipment Id']) == order_id:
            order_list.append(record)
    order_detail_dict['results'] = order_list

    return return_response(order_detail_dict)


@csrf_exempt
def get_shipment_info(request, internal=False, reqCode='stock_summary', filter_params={}):

    shipment_list = []
    dispatched_orders_list = []
    picked_orders_list = []
    open_orders_list = []
    ship_stat_list = []
    filter_params['user'] = request.user.id

    all_orders = OrderDetail.objects.filter(**filter_params).order_by('-updation_date')
    limit_orders = list(all_orders.values_list('order_id', flat=True).distinct())[:20]
    filter_params['order_id__in'] = limit_orders
    order_objects = all_orders.filter(**filter_params)
    for order in order_objects:
        orders_dict = OrderedDict(( ('SKU Code', order.sku.sku_code),
                                    ('WMS Code', order.sku.wms_code),
                                    ('Order Qty', order.quantity),
                                    ('SKU Description', order.sku.sku_desc),
                                    ('Customer Name', order.customer_name),
                                    ('Customer Id', order.customer_id),
                                    ('Shipment Id', order.order_id),
                                    ('Order Date', str(order.creation_date)),
                                    ('Status','')  ))
        total_picked_quantity = 0
        picklist = Picklist.objects.filter(order_id = order, order__user=request.user.id);
        status_list =[]
        count = 0

        for p in picklist:
            total_picked_quantity += p.picked_quantity
            count += 1
            if p.status =='dispatched':
                status_list.append(p.status)
        if (len(status_list) == count):
            orders_dict['Status'] = 'Dispatched from warehouse'
            dispatched_orders_list.append(orders_dict)
        else:
            if (total_picked_quantity == order.quantity ):
                orders_dict['Status'] = 'Ready to dispatch'
                picked_orders_list.append(orders_dict)
            else:
                orders_dict['Status'] = 'Ready to pick'
                open_orders_list.append(orders_dict)
        shipment_list.append(orders_dict)
    ship_status_list =[]
    ship_status_list.append( OrderedDict(( ('Status_Code',1), ('Status','Ready to pick'), ('Order Count',len(open_orders_list)) )) )
    ship_status_list.append( OrderedDict(( ('Status_Code',2), ('Status','Ready to dispatch'), ('Order Count',len(picked_orders_list)) )) )
    #ship_status_list.append( OrderedDict(( ('Status_Code',3), ('Status','Dispatched from warehouse'), ('Order Count',len(dispatched_orders_list)) )) )

    if reqCode == '1':
        data_list = open_orders_list
    elif reqCode == '2':
        data_list = picked_orders_list
    elif reqCode == '3':
        data_list = dispatched_orders_list
    elif reqCode == 'stock_summary':
        data_list = ship_status_list
    else:
        data_list = []
    if internal:
        return data_list
    return decide_and_return_response(request, data=data_list, scroll=False)

@csrf_exempt
def shipment_search(request):
    data = {}
    post_data = {}
    for key, value in request.POST.iteritems():
        if key == 'order_no' and value:
            post_data['order_id'] = value
        elif key == 'customer_name' and value:
            post_data[key + '__icontains'] = value
        elif key == 'order_date' and value:
            ar = value.split('/')
            d = '%s-%s-%s' % (ar[2], ar[0], ar[1])
            post_data['creation_date__startswith'] = str(d)
    post_data['user'] = request.user.id
    shipment_list = []
    order_details = OrderDetail.objects.filter(**post_data).order_by('-creation_date')[0:20]
    for order in order_details:
        orders_dict = OrderedDict(( ('Order ID',order.order_id),
                                    ('SKU Code',order.sku.sku_code),
                                    ('WMS Code',order.sku.wms_code),
                                    ('Quantity',order.quantity),
                                    ('Status','')  ))
        total_picked_quantity = 0
        picklist = Picklist.objects.filter(order = order)
        status_list =[]
        count = 0
        for p in picklist:
            total_picked_quantity += p.picked_quantity
            count += 1
            if p.status =='dispatched':
                status_list.append(p.status)
        if (len(status_list) == count):
            orders_dict['Status'] = 'Dispatched from Warehouse'
        else:
            if (total_picked_quantity == order.quantity ):
                orders_dict['Status'] = 'Ready to dispatch'
            else:
                orders_dict['Status'] = 'Ready to pick'
        shipment_list.append(orders_dict)
    return decide_and_return_response(request, data=shipment_list, scroll=True)

@csrf_exempt
def receipt_search(request):
    return HttpResponse("Pending...")

@csrf_exempt
def today_returns(request):
    return HttpResponse("Pending...")

def form_default_domain(request, org_url):
        img_url = "/".join(["%s:/" % (request.META['wsgi.url_scheme']), request.META['HTTP_HOST'], org_url.lstrip("/")]) if org_url.startswith("/static") else org_url
        return img_url
@csrf_exempt
def get_order_detail(request):
    order_data = []
    order_id = request.POST.get('order_id')
    purchase_orders = PurchaseOrder.objects.filter(order_id=order_id, status='', open_po__sku__user=request.user.id)

    for order in purchase_orders:
        supplier_id = order.open_po.supplier_id
        sku_id = order.open_po.sku_id
        design_code = order.open_po.supplier_code
        supplier_code = SKUSupplier.objects.filter(supplier_id=supplier_id, sku_id=sku_id)
        if supplier_code:
            design_code = supplier_code[0].supplier_code

        #img_url = "/".join([request.META['HTTP_HOST'], order.open_po.sku.image_url.lstrip("/")]) if order.open_po.sku.image_url.startswith("/static") else order.open_po.sku.image_url
        img_url = form_default_domain(request, order.open_po.sku.image_url)
        order_data.append(OrderedDict(( ('id', order.id), ('design_code', design_code), ('order_quantity', order.open_po.order_quantity), ('price', order.open_po.price), ('image_url', img_url), ('wms_code', order.open_po.sku.wms_code) )))
    return return_response(order_data)

@csrf_exempt
def sales_return_data(request, input_param):
    returns_data = OrderReturns.objects.filter(sku__user = request.user.id , creation_date__year = NOW.year,
                                               creation_date__month = NOW.month).values('sku_id').distinct().annotate(total=Count('id'))
    if(input_param):
        returns_data = OrderReturns.objects.values('sku_id').distinct().annotate(total=Count('id')).filter( **input_param)
    data_list = []

    for order_return in returns_data:
        data = OrderReturns.objects.filter(sku_id=order_return['sku_id'], **input_param)[0]
        data_dict = OrderedDict()
        data_dict['Year'] = data.creation_date.year
        data_dict['Month'] = data.creation_date.month
        data_dict['SKU Group'] = data.sku.sku_code
        data_dict['WMS Code'] = data.sku.wms_code
        data_dict['Return Quantity'] = order_return['total']
        data_list.append(data_dict)

    return data_list


@csrf_exempt
def sales_return_level1(request):
    output_dict = {}
    year = int(request.POST.get('year'))
    month = int(request.POST.get('month'))
    start_date = datetime.datetime(year, month, 1)
    end_date = start_date + relativedelta(day=31)
    input_param = {'sku__user': request.user.id, 'creation_date__range' : [start_date,end_date] }
    output_data = sales_return_data(request, input_param)
    return decide_and_return_response(request, data=output_data, scroll=True)

@csrf_exempt
def sales_return_level2(request):
    output_dict = {}
    sku = request.POST.get('sku_group')
    year = int(request.POST.get('year'))
    month = int(request.POST.get('month'))
    start_date = datetime.datetime(year, month, 1)
    end_date = datetime.datetime(year, month, 1) + relativedelta(day=31)

    input_param = {'sku__sku_code': sku, 'creation_date__range': [start_date, end_date], 'sku__user': request.user.id }
    returns_data = OrderReturns.objects.filter( **input_param)
    data_list = []

    for data in returns_data:
        data_dict = OrderedDict()
        data_dict['SKU Code'] = data.sku.sku_code
        data_dict['Quantity'] = data.quantity
        data_dict['Return ID'] = data.return_id
        #data_dict['Customer Id'] = data.order.customer_id
        #data_dict['Customer Name'] = data.order.customer_name
        data_dict['SKU Description'] = data.sku.sku_desc
        data_dict['Receipt Date'] = str(data.creation_date)
        data_list.append(data_dict)
    return decide_and_return_response(request, data=data_list, scroll=True)

@csrf_exempt
def get_transactions_data(request):
    data_list = []

    receipts = PurchaseOrder.objects.filter(open_po__sku__user = request.user.id, creation_date__startswith = str(NOW).split(' ')[0] ).values('order_id').distinct()
    receipt_dict = OrderedDict(( ('S_NO', 1), ('Transaction','Number of Receipts'),('Detail',len(receipts)) ))

    receipts2 = PurchaseOrder.objects.filter(open_po__sku__user = request.user.id, creation_date__startswith = str(NOW).split(' ')[0])
    receipt_qty = 0
    for record in receipts2:
        receipt_qty += record.received_quantity
    receipt_dict2 = OrderedDict(( ('S_NO', 2), ('Transaction','Total Receipt Quantity'),('Detail', receipt_qty) ))


    #orders_dt = OrderDetail.objects.filter(user = request.user.id )
    shipment_count = 0
    shipment_qty = 0
    picklist = Picklist.objects.filter(order__user = request.user.id, updation_date__startswith = str(NOW).split(' ')[0])
    for record in picklist:
        if record.status == 'dispatched' or 'picked' in record.status:
            shipment_count += 1
            shipment_qty += record.picked_quantity

    shipment_dict = OrderedDict(( ('S_NO', 3), ('Transaction','Number of shipments'),('Detail', shipment_count) ))
    shipment_dict2 = OrderedDict(( ('S_NO', 4), ('Transaction','Total Shipment Quantity'), ('Detail', shipment_qty) ))

    open_receipts = PurchaseOrder.objects.filter(status = '' , open_po__sku__user = request.user.id,
                                                 creation_date__startswith = str(NOW).split(' ')[0]).values('order_id').distinct()

    open_receipt_dict =  OrderedDict(( ('S_NO', 5), ('Transaction','Number of open Receipts'), ('Detail', len(open_receipts)) ))

    open_orders = Picklist.objects.filter(status__icontains = 'open',
                                          order__user = request.user.id ,
                                          creation_date__startswith = str(NOW).split(' ')[0])
    open_orders_dict = OrderedDict(( ('S_NO', 6), ('Transaction','Number of open Orders'), ('Detail', len(open_orders)) ))

    pending_sku_putaway =  PurchaseOrder.objects.filter(status__in = ['grn-generated','location-assigned'],
                                                        open_po__sku__user = request.user.id,
                                                        updation_date__startswith = str(NOW).split(' ')[0])
    sku_count = 0
    for order in pending_sku_putaway:
        sku_count += order.received_quantity

    pending_putaway_dict =  OrderedDict(( ('S_NO', 7), ('Transaction','Pending SKU Putaway Task'), ('Detail', sku_count) ))

    data_list = [receipt_dict, receipt_dict2, shipment_dict, shipment_dict2, open_receipt_dict, open_orders_dict, pending_putaway_dict ]
    return decide_and_return_response(request, data=data_list, scroll=False)


@csrf_exempt
def picklist_data(request):
    use_imei = 'false'
    data_id = request.POST['data_id']
    data = get_picklist_data(request, data_id, request.user.id)
    return return_response({'results': data})

def get_picklist_data(request, data_id,user_id):

    picklist_orders = Picklist.objects.filter(Q(order__sku__user=user_id) | Q(stock__sku__user=user_id), picklist_number=data_id)
    pick_stocks = StockDetail.objects.filter(sku__user=user_id)
    data = []
    if not picklist_orders:
        return data
    order_status = ''
    for orders in picklist_orders:
        if 'open' in orders.status:
            order_status = orders.status
    if not order_status:
        order_status = 'picked'
    if order_status == "batch_open":
        batch_data = {}
        for order in picklist_orders:
            stock_id = ''
            wms_code = order.sku_code
            if order.stock:
                stock_id = pick_stocks.get(id=order.stock_id)
            if order.order:
                sku_code = order.order.sku_code
                title = order.order.title
                invoice = order.order.invoice_amount
            else:
                st_order = STOrder.objects.filter(picklist_id=order.id)
                sku_code = ''
                title = st_order[0].stock_transfer.sku.sku_desc
                invoice = st_order[0].stock_transfer.invoice_amount

            pallet_code = ''
            pallet_detail = ''
            if stock_id and stock_id.pallet_detail:
                pallet_code = stock_id.pallet_detail.pallet_code
                pallet_detail = stock_id.pallet_detail

            zone = 'NO STOCK'
            st_id = 0
            sequence = 0
            location = 'NO STOCK'
            image = ''
            if stock_id:
                zone = stock_id.location.zone.zone
                st_id = order.stock_id
                sequence = stock_id.location.pick_sequence
                location = stock_id.location.location
                image = form_default_domain(request, stock_id.sku.image_url)
                wms_code = stock_id.sku.wms_code

            match_condition = (location, pallet_detail, wms_code, sku_code, title)
            if match_condition not in batch_data:
                if order.reserved_quantity == 0:
                    continue

                batch_data[match_condition] = {'wms_code': wms_code, 'zone': zone, 'sequence': sequence, 'location': location, 'reserved_quantity': order.reserved_quantity, 'picklist_number': data_id, 'stock_id': st_id, 'picked_quantity':order.picked_quantity, 'id': order.id, 'invoice_amount': invoice, 'price': invoice * order.reserved_quantity, 'image': image, 'order_id': order.order_id, 'status': order.status, 'pallet_code': pallet_code, 'sku_code': sku_code, 'title': title}
            else:
                batch_data[match_condition]['reserved_quantity'] += order.reserved_quantity
                batch_data[match_condition]['invoice_amount'] += invoice
        data = batch_data.values()

        data = sorted(data, key=itemgetter('sequence'))
        return data

    elif order_status == "open":
        for order in picklist_orders:
            stock_id = ''
            if order.order:
                wms_code = order.order.sku.wms_code
                invoice_amount = order.order.invoice_amount
                order_id = order.order.order_id
                sku_code = order.order.sku_code
                title = order.order.title
            else:
                wms_code = order.stock.sku.wms_code
                invoice_amount = 0
                order_id = ''
                sku_code = order.stock.sku.sku_code
                title = order.stock.sku.sku_desc
            if order.stock_id:
                stock_id = pick_stocks.get(id=order.stock_id)
            if order.reserved_quantity == 0:
                continue
            pallet_code = ''
            if stock_id and stock_id.pallet_detail:
                pallet_code = stock_id.pallet_detail.pallet_code

            zone = 'NO STOCK'
            st_id = 0
            sequence = 0
            location = 'NO STOCK'
            image = ''
            if stock_id:
                zone = stock_id.location.zone.zone
                st_id = order.stock_id
                sequence = stock_id.location.pick_sequence
                location = stock_id.location.location
                image = form_default_domain(request, stock_id.sku.image_url)#stock_id.sku.image_url

            data.append({'wms_code': wms_code, 'zone': zone, 'location': location, 'reserved_quantity': order.reserved_quantity, 'picklist_number': data_id, 'stock_id': st_id, 'order_id': order.order_id, 'picked_quantity':order.picked_quantity, 'id': order.id, 'sequence': sequence, 'invoice_amount': invoice_amount, 'price': invoice_amount * order.reserved_quantity, 'image': image, 'status': order.status, 'order_no': order_id,'pallet_code': pallet_code, 'sku_code': sku_code, 'title': title})
        data = sorted(data, key=itemgetter('sequence'))
        return data
    else:
        for order in picklist_orders:
            stock_id = ''
            wms_code = order.order.sku.wms_code
            if order.stock_id:
                stock_id = pick_stocks.get(id=order.stock_id)

            zone = 'NO STOCK'
            st_id = 0
            sequence = 0
            location = 'NO STOCK'
            image = ''
            pallet_code = ''
            if stock_id:
                zone = stock_id.location.zone.zone
                st_id = order.stock_id
                pallet_code = stock_id.pallet_detail.pallet_code if stock_id.pallet_detail else ''
                sequence = stock_id.location.pick_sequence
                location = stock_id.location.location
                image = form_default_domain(request, stock_id.sku.image_url)

            #if order.reserved_quantity == 0:
            #    continue

            data.append({'wms_code': wms_code, 'zone': zone, 'location': location, 'reserved_quantity': order.reserved_quantity,                'picklist_number': data_id, 'order_id': order.order_id, 'stock_id': st_id, 'picked_quantity':order.picked_quantity, 'id': order.id, 'sequence': sequence, 'invoice_amount': order.order.invoice_amount, 'price': order.order.invoice_amount * order.reserved_quantity, 'image': image,          'status': order.status, 'pallet_code': pallet_code, 'sku_code': order.order.sku_code, 'title': order.order.title })
        data = sorted(data, key=itemgetter('sequence'))
        return data


@csrf_exempt
def picklist(request):

    status = request.POST.get('status')
    if status not in ['open', 'picked']:
        return return_response('Please enter valid Status')

    temp_data = {}
    master_data = Picklist.objects.filter( status__contains = status, order__user=request.user.id ).order_by('creation_date')

    data_dict = {}
    picklist_count = []
    final_data = []
    for data in master_data:
        if data.picklist_number in picklist_count:
            continue

        picklist_count.append(data.picklist_number)
        final_data.append(data)

    temp_data['recordsTotal'] = len( final_data )
    temp_data['recordsFiltered'] = len( final_data )
    temp_data['results'] = []

    for data in final_data:
        picklist_id = PicklistLocation.objects.filter(picklist_id=data.id, picklist__order__user=request.user.id)
        result_data = {'Picklist Note': data.remarks, 'Date': str(data.creation_date).split('+')[0]}
        result_data['Picklist ID'] = data.picklist_number
        temp_data['results'].append(result_data)
    return decide_and_return_response(request, data=temp_data['results'], scroll=True)

@csrf_exempt
def get_inbound_outbound_stats(request):
    user_id = request.GET.get('user', '')
    orders = Picklist.objects.filter(status__in=['picked', 'batch_picked'], order__user = user_id)
    order_ids = {}
    total_outbound_quantity = {}
    for order in orders:
        if str(order.updation_date).split(' ')[0] in total_outbound_quantity.keys():
            total_outbound_quantity[str(order.updation_date).split(' ')[0]] +=order.picked_quantity
        else:
            total_outbound_quantity.setdefault(str(order.updation_date).split(' ')[0], order.picked_quantity)
        order_ids.setdefault(str(order.updation_date).split(' ')[0], []).append(order.order_id)

    pos = PurchaseOrder.objects.filter(status='confirmed-putaway', open_po__sku__user = user_id)
    po_ids = {}
    total_inbound_quantity = {}
    for po in pos:
        if str(po.updation_date).split(' ')[0] in total_inbound_quantity.keys():
            total_inbound_quantity[str(po.updation_date).split(' ')[0]] +=po.received_quantity
        else:
            total_inbound_quantity.setdefault(str(po.updation_date).split(' ')[0], po.received_quantity)
        po_ids.setdefault(str(po.updation_date).split(' ')[0], []).append(po.order_id)
    username = User.objects.filter(id=user_id)
    if not username:
        username = "unknown user"
    else:
        username = username[0].username
    data = {'inbound': total_inbound_quantity, 'outbound': total_outbound_quantity, 'warehouse' : username}
    return return_response(data)



def get_purchase_order_data(order):
    order_data = {}
    if order.open_po:
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
        if st_picklist:
            picked = 0
            for st in st_picklist:
                picked += int(st.picklist.picked_quantity)
            processed = POLocation.objects.filter(purchase_order_id=st_order[0].po_id).\
                                           aggregate(Sum('original_quantity'))['original_quantity__sum']
            received = int(order.received_quantity)
            order_quantity = picked
            if processed:
                order_quantity = (order_quantity + received) - int(processed)


    order_data = {'order_quantity': order_quantity, 'price': open_data.price, 'wms_code': open_data.sku.wms_code,
                  'sku_code': open_data.sku.wms_code, 'supplier_id': user_data.id, 'zone': open_data.sku.zone,
                  'qc_check': open_data.sku.qc_check, 'supplier_name': username,
                  'sku_desc': open_data.sku.sku_desc, 'address': address,
                  'phone_number': user_data.phone_number, 'email_id': email_id,
                  'sku_group': open_data.sku.sku_group, 'sku_id': open_data.sku.id, 'sku': open_data.sku }

    return order_data

@csrf_exempt
def putaway_list(request):
    temp_data = {'recordsTotal': 0, 'recordsFiltered': 0, 'aaData': []}
    supplier_data = {}
    results = PurchaseOrder.objects.filter(open_po__sku__user = request.user.id).exclude(status__in=['', 'confirmed-putaway']).values('order_id').distinct()
    data = []
    temp = []
    for result in results:
        suppliers = PurchaseOrder.objects.filter(order_id=result['order_id'], open_po__sku__user = request.user.id).exclude(status__in=['', 'confirmed-putaway'])
        if not suppliers:
            st_order_ids = STPurchaseOrder.objects.filter(po__order_id=result, open_st__sku__user = request.user.id).values_list('po_id', flat=True)
            suppliers = PurchaseOrder.objects.filter(id__in=st_order_ids)
        for supplier in suppliers:
            po_loc = POLocation.objects.filter(purchase_order_id=supplier.id, status=1, location__zone__user = request.user.id)
            if po_loc and result not in temp:
                temp.append(result)
                data.append(supplier)

    temp_data['recordsTotal'] = len(data)
    temp_data['recordsFiltered'] = len(data)
    for supplier in data:
        order_data = get_purchase_order_data(supplier)
        po_reference = '%s%s_%s' % (supplier.prefix, str(supplier.creation_date).split(' ')[0].replace('-', ''), supplier.order_id)
        temp_data['aaData'].append({'Supplier ID': order_data['supplier_id'],
                                    'Supplier Name': order_data['supplier_name'],
                                    ' Order ID': supplier.order_id, 'Order Date': str(get_local_date(request.user, supplier.creation_date, send_date='')).split('+')[0],
                                    ' PO Number': po_reference })
    return return_response(temp_data)

def get_misc_value(misc_type, user):

    if not misc_type:
        return return_response('Please send misc_type in GET params')

    misc_value = 'false'
    data = MiscDetail.objects.filter(user=user, misc_type=misc_type)
    if data:
        misc_value = data[0].misc_value
    return misc_value

@csrf_exempt
def get_api_misc_value(request):
    misc_type = request.GET.get('misc_type', '')
    if not misc_type:
        return return_response('Please send misc_type in GET params')

    misc_value = get_misc_value(misc_type, request.user.id)
    return return_response(misc_value)


@csrf_exempt
def putaway_detail(request):
    all_data = {}
    temp = get_misc_value('pallet_switch', request.user.id)
    headers = ('WMS CODE', 'Location', 'Pallet Number', 'Original Quantity', 'Putaway Quantity', '')
    data = {}
    supplier_id = request.GET['order_id']
    purchase_orders = PurchaseOrder.objects.filter(order_id=supplier_id, open_po__sku__user = request.user.id).exclude(
                                                   status__in=['', 'confirmed-putaway'])
    if not purchase_orders:
        st_orders = STPurchaseOrder.objects.filter(po__order_id=supplier_id, open_st__sku__user = request.user.id).\
                                exclude(po__status__in=['', 'confirmed-putaway', 'stock-transfer']).values_list('po_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(id__in=st_orders)
    for order in purchase_orders:
        order_id = order.id
        order_data = get_purchase_order_data(order)
        po_location = POLocation.objects.filter(purchase_order_id=order_id, status=1, location__zone__user = request.user.id)
        for location in po_location:
            pallet_number = ''
            if temp == "true":
                pallet_mapping = PalletMapping.objects.filter(po_location_id=location.id, status=1)
                if pallet_mapping:
                    pallet_number = pallet_mapping[0].pallet_detail.pallet_code
                    cond = (pallet_number, location.location.location)
                    all_data.setdefault(cond, [0, '',0, '', []])
                    if all_data[cond] == [0, '', 0, '', []]:
                        all_data[cond] = [all_data[cond][0] + int(location.quantity), order_data['wms_code'],
                                          int(location.quantity), location.location.fill_sequence, [{'orig_id': location.id,
                                          'orig_quantity': location.quantity}], location.location.id]
                    else:
                        if all_data[cond][2] < int(location.quantity):
                            all_data[cond][2] = int(location.quantity)
                            all_data[cond][1] = order_data['wms_code']
                        all_data[cond][0] += int(location.quantity)
                        all_data[cond][3] = location.location.fill_sequence
                        all_data[cond][4].append({'orig_id': location.id, 'orig_quantity': location.quantity})
            if temp == 'false' or (temp == 'true' and not pallet_mapping):
                data[location.id] = (order_data['wms_code'], location.location.location, location.quantity, location.quantity,
                                     location.location.fill_sequence, location.id, pallet_number, '', location.location.id)
    if temp == 'true' and all_data:
        for key, value in all_data.iteritems():
            data[key[0]] = (value[1], key[1], value[0], value[0], value[3], '', key[0], value[4], value[5])

    data_list = data.values()
    new_data = []
    for data in data_list:
        new_data.append({'wms_code': data[0], 'location': data[1], 'quantity': data[2], 'fill_sequence': data[4], 'po_id': data[5], 'pallet_number': data[6], 'location_id': data[-1], 'orig_data': str(data[7])})

    return return_response(new_data)

@csrf_exempt
def get_confirmed_po(request):
    data_list = []
    data = []
    supplier_data = {}
    temp_data = {'aaData': []}

    results = PurchaseOrder.objects.filter(open_po__sku__user = request.user.id).exclude(status__in=['location-assigned', 'confirmed-putaway']).values('order_id').distinct()

    for result in results:
        suppliers = PurchaseOrder.objects.filter(order_id=result['order_id'], open_po__sku__user = request.user.id).exclude(status__in=['location-assigned', 'confirmed-putaway'])
        if not suppliers:
            st_order_ids = STPurchaseOrder.objects.filter(po__order_id=result['order_id'], open_st__sku__user = requestuser.id).values_list('po_id', flat=True)
            suppliers = PurchaseOrder.objects.filter(id__in=st_order_ids)
        for supplier in suppliers[:1]:
            supplier_data = get_purchase_order_data(supplier)
            if not int(supplier_data['order_quantity']) - int(supplier.received_quantity) <= 0:
                data.append(supplier)

    temp_data['recordsTotal'] = len(data)
    temp_data['recordsFiltered'] = len(data)
    for supplier in data:
        receive_status = 'Yet To Receive'
        order_data = get_purchase_order_data(supplier)
        if supplier.received_quantity and not int(order_data['order_quantity']) == int(supplier.received_quantity):
            receive_status = 'Partially Receive'
        po_reference = '%s%s_%s' % (supplier.prefix, str(supplier.creation_date).split(' ')[0].replace('-', ''), supplier.order_id)
        data_list.append({'DT_RowId': supplier.order_id, 'PO Number': po_reference, 'Order Date': str(supplier.creation_date).split('+')[0],
                          'Supplier ID': order_data['supplier_id'], 'Supplier Name': order_data['supplier_name'],
                          'Receive Status': receive_status})

    temp_data['aaData'] = list(chain(temp_data['aaData'], data_list))
    return return_response(temp_data)


@csrf_exempt
def get_supplier_data(request):
    temp = get_misc_value('pallet_switch', request.user.id)
    data = []
    order_id = request.GET['supplier_id']
    purchase_orders = PurchaseOrder.objects.filter(order_id=order_id, open_po__sku__user = request.user.id).exclude(status='location-assigned')
    if not purchase_orders:
        st_orders = STPurchaseOrder.objects.filter(po__order_id=order_id, open_st__sku__user = request.user.id).\
                                exclude(po__status__in=['location-assigned', 'stock-transfer']).values_list('po_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(id__in=st_orders)
    for order in purchase_orders:
        order_data = get_purchase_order_data(order)
        po_quantity = int(order_data['order_quantity']) - int(order.received_quantity)
        if po_quantity > 0:
            data.append({'order_id': order.id, 'wms_code': order_data['wms_code'],'po_quantity': int(order_data['order_quantity'])-int(order.received_quantity),
                              'name': str(order.order_id) + '-' + str(order_data['wms_code']), 'value': str(int(order.saved_quantity)),
                              'price': order_data['price'], 'temp_wms': order_data['wms_code'] })

    return return_response(data)


@csrf_exempt
def get_skus(request):
    if request.user.is_anonymous():
        return HttpResponse(json.dumps({'message': 'fail'}))
    data = []
    limit = request.POST.get('limit', '')
    sku_records = SKUMaster.objects.filter(user = request.user.id)
    for sku in sku_records:
        updated = ''
        if sku.updation_date:
            updated = sku.updation_date.strftime('%Y-%m-%d %H:%M:%S')
        data.append(OrderedDict(( ('id', sku.id), ('sku_code', sku.sku_code), ('sku_desc', sku.sku_desc), ('sku_category', sku.sku_category),
                     ('price', str(sku.price)), ('active', sku.status), ('created_at', sku.creation_date.strftime('%Y-%m-%d %H:%M:%S')),
                     ('updated_at', updated ))))

    data = scroll_data(request, data, limit=limit)

    data['message'] = 'success'
    return HttpResponse(json.dumps(data, cls=DjangoJSONEncoder))

@csrf_exempt
@login_required
def get_sku(request):
    if request.user.is_anonymous():
        return HttpResponse(json.dumps({'message': 'fail'}))
    data = []
    limit = request.POST.get('limit', '')
    combo_skus = SKURelation.objects.filter(parent_sku__user=request.user.id)
    member_sku_ids = combo_skus.values_list('member_sku_id', flat=True)
    sku_records = SKUMaster.objects.exclude(id__in=member_sku_ids).filter(user = request.user.id).order_by('sku_code')
    for ind, sku in enumerate(sku_records):
        updated = ''
        if sku.updation_date:
            updated = sku.updation_date.strftime('%Y-%m-%d %H:%M:%S')
        data.append(OrderedDict(( ('id', sku.id), ('sku_code', sku.sku_code), ('sku_desc', sku.sku_desc), ('sku_category', sku.sku_category),
                     ('price', str(sku.price)), ('active', sku.status), ('created_at', sku.creation_date.strftime('%Y-%m-%d %H:%M:%S')),
                     ('updated_at', updated ))))
        if sku.relation_type == 'combo':
            child_skus = combo_skus.filter(parent_sku_id=sku.id, parent_sku__user=request.user.id)
            data[ind]['child_skus'] = []
            for child in child_skus:
                data[ind]['child_skus'].append(OrderedDict(( ('id', child.member_sku.id), ('sku_code', child.member_sku.sku_code),
                                                      ('sku_desc', child.member_sku.sku_desc), ('sku_category', child.member_sku.sku_category),
                                                        ('price', str(child.member_sku.price)), ('active', child.member_sku.status),
                                                        ('created_at', child.member_sku.creation_date.strftime('%Y-%m-%d %H:%M:%S')),
                                              )))

    data = scroll_data(request, data, limit=limit)

    data['message'] = 'success'
    return HttpResponse(json.dumps(data, cls=DjangoJSONEncoder))

@csrf_exempt
@login_required
def update_order(request):
    try:
        orders = json.loads(request.body)
    except:
        return HttpResponse(json.dumps({'message': 'Please send proper data'}))
    log.info('Request params for ' + request.user.username + ' is ' + str(orders))
    try:
        validation_dict, final_data_dict = validate_orders(orders, user=request.user, company_name='mieone')
        if validation_dict:
            return HttpResponse(json.dumps({'messages': validation_dict, 'status': 0}))
        status = update_order_dicts(final_data_dict, user=request.user, company_name='mieone')
        log.info(status)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update orders data failed for %s and params are %s and error statement is %s' % (str(request.user.username), str(request.body), str(e)))
        status = {'messages': 'Internal Server Error', 'status': 0}
    return HttpResponse(json.dumps(status))

@csrf_exempt
@login_required
def update_sku(request):
    skus = ''
    try:
        skus = json.loads(request.body)
    except:
        log.info('Incorrect Request params for ' + request.user.username + ' is ' + str(skus))
        return HttpResponse(json.dumps({'status': 400, 'message': 'Invalid JSON Data'}), status=400)
    log.info('Request params for ' + request.user.username + ' is ' + str(skus))
    try:
        insert_status, failed_status = update_skus(skus, user=request.user, company_name='mieone')
        log.info(insert_status)
        log.info(failed_status)
        if not failed_status:
            failed_status = {'status': 200, 'message': 'Success'}
        else:
            if not (insert_status.get('SKUS Created', '') or insert_status.get('SKUS updated', '')):
                failed_status = {'status': 422, 'messages': failed_status}
            else:
                failed_status = {'status': 207, 'messages': failed_status}
        return HttpResponse(json.dumps(failed_status), status=failed_status.get('status', 200))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update SKUS data failed for %s and params are %s and error statement is %s' % (str(request.user.username), str(request.body), str(e)))
        status = {'message': 'Internal Server Error'}
        return HttpResponse(json.dumps(status), status=500)


@csrf_exempt
@login_required
def update_customer(request):
    try:
        customers = json.loads(request.body)
    except:
        return HttpResponse(json.dumps({'message': 'Please send proper data'}))
    log.info('Request params for ' + request.user.username + ' is ' + str(customers))
    try:
        message = update_customers(customers, user=request.user, company_name='mieone')
        status = {'status': 1, 'message': message}
        log.info(status)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Customers data failed for %s and params are %s and error statement is %s' % (str(request.user.username), str(request.body), str(e)))
        status = {'status': 0,'message': 'Internal Server Error'}
    return HttpResponse(json.dumps(status))

@csrf_exempt
@login_required
def update_seller(request):
    try:
        sellers = json.loads(request.body)
    except:
        return HttpResponse(json.dumps({'message': 'Please send proper data'}))
    log.info('Request params for ' + request.user.username + ' are ' + str(sellers))
    try:
        status = update_sellers(sellers, user=request.user, company_name='mieone')
        log.info(status)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Sellers data failed for %s and params are %s and error statement is %s' % (str(request.user.username), str(request.body), str(e)))
        status = {'message': 'Internal Server Error'}
    return HttpResponse(json.dumps(status))

@csrf_exempt
@login_required
def cancel_order(request):
    try:
        orders = json.loads(request.body)
        log.info('Request params for ' + request.user.username + ' are ' + str(orders))
    except:
        log.info('Request params for ' + request.user.username + ' are ' + str(request.body))
        return HttpResponse(json.dumps({'message': 'Please send proper data'}))
    try:
        validation_dict, final_data_dict = validate_orders(orders, user=request.user, company_name='mieone', is_cancelled=True)
        if validation_dict:
            return HttpResponse(json.dumps({'messages': validation_dict, 'status': 0}))
        validation_dict2, status = update_order_cancel(final_data_dict, user=request.user, company_name='mieone')
        if validation_dict2:
            return HttpResponse(json.dumps({'messages': validation_dict2, 'status': 0}))
        status = {'status': 1, 'messages': ['Success']}
        log.info(status)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Sellers data failed for %s and params are %s and error statement is %s' % (str(request.user.username), str(request.body), str(e)))
        status = {'message': 'Internal Server Error'}
    return HttpResponse(json.dumps(status))

@csrf_exempt
@login_required
def update_return(request):
    try:
        orders = json.loads(request.body)
        log.info('Request params for ' + request.user.username + ' are ' + str(orders))
    except:
        log.info('Request params for ' + request.user.username + ' are ' + str(request.body))
        return HttpResponse(json.dumps({'message': 'Please send proper data'}))
    try:
        validation_dict, final_data_dict = validate_orders(orders, user=request.user, company_name='mieone', is_cancelled=True)
        if validation_dict:
            return HttpResponse(json.dumps({'messages': validation_dict, 'status': 0}))
        validation_dict2, status = update_order_returns(final_data_dict, user=request.user, company_name='mieone')
        if validation_dict2:
            return HttpResponse(json.dumps({'messages': validation_dict2, 'status': 0}))
        status = {'status': 1, 'messages': ['Success']}
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Sellers data failed for %s and params are %s and error statement is %s' % (str(request.user.username), str(request.body), str(e)))
        status = {'message': 'Internal Server Error'}
    return HttpResponse(json.dumps(status))


@csrf_exempt
@login_required
def update_orders(request):
    try:
        orders = json.loads(request.body)
    except:
        return HttpResponse(json.dumps({'status': 400, 'message': 'Please send proper data'}))
    log.info('Request params for ' + request.user.username + ' is ' + str(orders))
    try:
        if request.user.userprofile.user_type == 'marketplace_user':
            validation_dict, failed_status, final_data_dict = validate_seller_orders_format(orders, user=request.user,
                                                                                     company_name='mieone')
        else:
            validation_dict, failed_status, final_data_dict = validate_orders_format(orders, user=request.user, company_name='mieone')
        if validation_dict:
            return HttpResponse(json.dumps({'messages': validation_dict, 'status': 0}))
        if failed_status:
            if type(failed_status) == dict:
                failed_status.update({'Status': 'Failure'})
            if type(failed_status) == list:
                failed_status = failed_status[0]
                failed_status.update({'Status': 'Failure'})
            return HttpResponse(json.dumps(failed_status))
        #status = update_ingram_order_dicts(final_data_dict, seller_id, user=request.user)
        status = update_order_dicts(final_data_dict, user=request.user, company_name='mieone')
        log.info(status)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update orders data failed for %s and params are %s and error statement is %s' % (str(request.user.username), str(request.body), str(e)))
        status = {'messages': 'Internal Server Error', 'status': 0}
    return HttpResponse(json.dumps(status))

@csrf_exempt
@login_required
def get_orders(request):
    record = []
    limit = request.POST.get('limit', '')
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lt'] = search_params['to_date']
    if 'order_id' in search_params:
        search_parameters['original_order_id'] = search_params['order_id']
    search_parameters['user'] = request.user.id
    order_records = OrderDetail.objects.filter(**search_parameters).values_list('original_order_id',flat= True).distinct()
    page_info = scroll_data(request, order_records, limit=limit)
    for order in page_info['data']:
        data_dict = OrderDetail.objects.filter(user=request.user.id,original_order_id=order)
        shipment = data_dict[0].shipment_date.strftime('%Y-%m-%d %H:%M:%S')
        created = data_dict[0].creation_date.strftime('%Y-%m-%d %H:%M:%S')
        items = []
        charge_amount= 0
        discount_amount = 0
        item_dict = {}
        for data in data_dict:
            tax_data = CustomerOrderSummary.objects.filter(order_id=data.id)
            charge = OrderCharges.objects.filter(order_id = data.original_order_id, user=request.user.id, charge_name = 'Shipping Charge').values('charge_amount')
            if charge:
                charge_amount = charge[0]
            if tax_data.exists():
                discount_amount = tax_data[0].discount
                if tax_data[0].cgst_tax:
                    item_dict['tax_percent'] = {'CGST': tax_data[0].cgst_tax, 'SGST': tax_data[0].sgst_tax}
                elif tax_data[0].igst_tax:
                    item_dict['tax_percent'] = {'IGST': tax_data[0].igst_tax}
            item_dict = {'sku':data.sku.sku_code, 'name':data.sku.sku_desc,'quantity':data.quantity, 'unit_price':data.unit_price, 'shipment_charge':charge_amount, 'discount_amount':discount_amount}
            items.append(item_dict)       
        billing_address = {"customer_id": data_dict[0].customer_id,
               "name": data_dict[0].customer_name,
               "email": data_dict[0].email_id,
               "phone_number": data_dict[0].telephone,
               "address": data_dict[0].address,
               "city": data_dict[0].city,
               "state": data_dict[0].state,
               "pincode": data_dict[0].pin_code}
        record.append(OrderedDict(( ('order_id',data_dict[0].original_order_id),('order_date',created),('shipment_date',shipment),('source',data_dict[0].marketplace),('billing_address',billing_address ),('items',items))))
    page_info['data'] = record
    page_info['message'] = 'success'
    return HttpResponse(json.dumps(page_info, cls=DjangoJSONEncoder))

@csrf_exempt
@login_required
def update_mp_orders(request):
    try:
        orders = json.loads(request.body)
    except:
        return HttpResponse(json.dumps({'status': 400, 'message': 'Invalid JSON Data'}), status=400)
    log.info('Request params for ' + request.user.username + ' is ' + str(orders))
    order_file_path = 'static/order_files'
    folder_check(order_file_path)
    file_time_stamp = str(datetime.datetime.now()).replace(':', '_').replace('.', '_').replace(' ', '_')
    load_file_path = '%s/%s' % (order_file_path, 'mp_orders_' + file_time_stamp + '.txt')
    load_file = open(load_file_path, 'w')
    load_file.write(json.dumps(orders))
    try:
        validation_dict, failed_status, final_data_dict = validate_seller_orders_format(orders, user=request.user, company_name='mieone')
        if validation_dict:
            return HttpResponse(json.dumps({'messages': validation_dict, 'status': 207}), status=207)
        insert_status = update_order_dicts_skip_errors(final_data_dict, failed_status, user=request.user, company_name='mieone')
        if failed_status:
            final_failed_status = {'status': 422}
            if type(failed_status) == dict:
                final_failed_status.update({'status': 422, 'messages': failed_status})
            if type(failed_status) == list:
                failed_status = failed_status
                final_failed_status.update({'messages': failed_status})
            return HttpResponse(json.dumps(final_failed_status), status=422)
        #status = update_order_dicts(final_data_dict, user=request.user, company_name='mieone')
        status = {'status': 1, 'messages': 'Success'}
        log.info(status)
    except Exception as e:
        import traceback
        log_err.debug(traceback.format_exc())
        log_err.info('Update orders data failed for %s and params are %s and error statement is %s' % (str(request.user.username), str(request.body), str(e)))
        status = {'messages': 'Internal Server Error', 'status': 0}
    return HttpResponse(json.dumps(status))


@csrf_exempt
@login_required
def get_mp_inventory(request):
    user = request.user
    data = []
    industry_type = user.userprofile.industry_type
    filter_params = {}
    error_status = []
    request_data = request.body
    try:
        try:
            request_data = json.loads(request_data)
            limit = request_data.get('limit', 100)
            skus = request_data.get('sku', [])
            skus = map(lambda sku: str(sku), skus)
            seller_id = request_data.get('seller_id', '')
            warehouse = request_data.get('warehouse', '')
            #skus = eval(skus)
            if skus:
                filter_params['sku_code__in'] = skus
                limit = len(skus)
            log_mp = ('MP inventory request from %s with request data %s '%
                         (str(request.user.username), str(request_data)))
            mb_stock_sycn_log(log_mp, user)
        except:
            return HttpResponse(json.dumps({'status': 400, 'message': 'Invalid JSON Data'}), status=400)
        if not seller_id:
            return HttpResponse(json.dumps({'status': 400, 'message': 'Seller ID is Mandatory'}), status=400)
        if not warehouse:
            return HttpResponse(json.dumps({'status': 400, 'message': 'Warehouse Name is Mandatory'}), status=400)
        token_user = user
        sister_whs1 = list(get_sister_warehouse(user).values_list('user__username', flat=True))
        sister_whs1.append(token_user.username)
        sister_whs = []
        for sister_wh1 in sister_whs1:
            sister_whs.append(str(sister_wh1).lower())
        if warehouse.lower() in sister_whs:
            user = User.objects.get(username=warehouse)
        else:
            return HttpResponse(json.dumps({'status': 400, 'message': 'Invalid Warehouse Name'}), status=400)
        try:
            seller_master = SellerMaster.objects.filter(user=user.id, seller_id=seller_id)
            if not seller_master:
                return HttpResponse(json.dumps({'status': 400, 'message': 'Invalid Seller ID'}), status=400)
        except:
            return HttpResponse(json.dumps({'status': 400, 'message': 'Invalid Seller ID'}), status=400)
        seller_master_id = seller_master[0].id
        picklist_exclude_zones = get_exclude_zones(user)
        filter_params['user'] = user.id
        sku_records = SKUMaster.objects.filter(**filter_params).values('sku_code', 'id')
        error_skus = set(skus) - set(sku_records.values_list('sku_code', flat=True))
        for error_sku in error_skus:
            error_status.append({'sku': error_sku, 'message': 'SKU Not found', 'status': 5030})
        page_info = scroll_data(request, sku_records, limit=limit, request_type='body')
        sku_records = page_info['data']
        bulk_zone = MILKBASKET_BULK_ZONE
        bulk_zones = get_all_zones(user, zones=[bulk_zone])
        combo_allocate_stock = get_misc_value('combo_allocate_stock', user.id)
        if industry_type == 'FMCG':
            sellable_zones = ZoneMaster.objects.filter(user=user.id, segregation='sellable').values_list('zone', flat=True)
            if sellable_zones:
                sellable_zones = get_all_zones(user, zones=sellable_zones)
            non_sellable_zones = ZoneMaster.objects.filter(user=user.id, segregation='non_sellable').\
                exclude(zone__in=bulk_zones).values_list('zone', flat=True)
            if non_sellable_zones:
                non_sellable_zones = get_all_zones(user, zones=non_sellable_zones)

            stocks = SellerStock.objects.prefetch_related('seller', 'stock', 'stock__location__zone').\
                          filter(seller_id=seller_master_id,stock__sku__user=user.id, stock__quantity__gt=0, stock__location__zone__zone__in=sellable_zones).\
                                exclude(Q(stock__location__zone__zone__in=picklist_exclude_zones) |
                                        Q(stock__receipt_number=0)).only('stock__sku__sku_code',
                                                                        'stock__batch_detail__mrp', 'quantity').\
                          annotate(group_key=Concat('stock__sku__sku_code',Value('<<>>'), 'stock__batch_detail__mrp',
                                                    Value('<<>>'), 'stock__batch_detail__weight',
                                    output_field=CharField())).values('group_key').distinct().\
                          annotate(stock_sum=Sum('quantity'))
            pick_res = dict(PicklistLocation.objects.select_related('seller__sellerstock', 'stock', 'stock__sku').\
                            filter(stock__sellerstock__seller_id=seller_master_id, reserved__gt=0, status=1,
                                    stock__sellerstock__quantity__gt=0, stock__sku__user=user.id, stock__location__zone__zone__in=sellable_zones). \
                            only('stock__sku__sku_code', 'stock__batch_detail__mrp', 'reserved').\
                            annotate(group_key=Concat('stock__sku__sku_code',Value('<<>>'), 'stock__batch_detail__mrp',
                                                      Value('<<>>'), 'stock__batch_detail__weight',
                                              output_field=CharField())).values_list('group_key').distinct(). \
                            annotate(stock_sum=Sum('reserved')))
            unsellable_stock = SellerStock.objects.select_related('seller', 'stock', 'stock__location__zone__zone').\
                          filter(seller_id=seller_master_id,stock__sku__user=user.id, stock__quantity__gt=0,
                                 stock__location__zone__zone__in=non_sellable_zones). \
                          only('stock__sku__sku_code', 'stock__batch_detail__mrp', 'reserved').\
                          annotate(group_key=Concat('stock__sku__sku_code',Value('<<>>'), 'stock__batch_detail__mrp',
                                                    Value('<<>>'), 'stock__batch_detail__weight',
                                          output_field=CharField())).values('group_key').distinct(). \
                          annotate(stock_sum=Sum('quantity'))
            bulk_zone_stock = SellerStock.objects.select_related('seller', 'stock', 'stock__location__zone__zone').\
                          filter(seller_id=seller_master_id,stock__sku__user=user.id, stock__quantity__gt=0,
                                 stock__location__zone__zone__in=bulk_zones). \
                          only('stock__sku__sku_code', 'stock__batch_detail__mrp', 'reserved').\
                          annotate(group_key=Concat('stock__sku__sku_code',Value('<<>>'), 'stock__batch_detail__mrp',
                                                    Value('<<>>'), 'stock__batch_detail__weight',
                                          output_field=CharField())).values('group_key').distinct(). \
                          annotate(stock_sum=Sum('quantity'))
            open_orders = dict(OrderDetail.objects.filter(user=user.id, quantity__gt=0, status=1).\
                                annotate(group_key=Concat('sku__sku_code', Value('<<>>'), F('customerordersummary__mrp'), output_field=CharField())).\
                                values_list('group_key').distinct().annotate(Sum('quantity')))
            sku_weight_dict = dict(SKUAttributes.objects.filter(sku__user=user.id, attribute_name='weight').\
                                   exclude(attribute_value='').values_list('sku__sku_code', 'attribute_value'))

            combo_sku_list = list(SKUMaster.objects.filter(user=user.id, relation_type='combo').\
                                  values_list('sku_code', flat=True))
            sku_open_orders_dict = {}
            open_orders1 = copy.deepcopy(open_orders)
            for open_order, open_order_qty in open_orders1.iteritems():
                temp_key = open_order.split('<<>>')
                if temp_key[0] in combo_sku_list and combo_allocate_stock != 'true':
                    sku_combos = SKURelation.objects.filter(parent_sku__user=user.id, parent_sku__sku_code=temp_key[0],
                                               relation_type='combo').annotate(str_mrp=Cast('member_sku__mrp', CharField()))
                    for sku_combo in sku_combos:
                        member_sku_code = str(sku_combo.member_sku.sku_code)
                        open_order_combo_key = '%s<<>>%s' % (member_sku_code, sku_combo.str_mrp)
                        sku_open_orders_dict.setdefault(member_sku_code, [])
                        if open_order_combo_key not in sku_open_orders_dict[member_sku_code]:
                            sku_open_orders_dict[member_sku_code].append(open_order_combo_key)
                        open_orders.setdefault(open_order_combo_key, 0)
                        open_orders[open_order_combo_key] += (sku_combo.quantity * open_order_qty)
                    del open_orders[open_order]
                else:
                    sku_open_orders_dict.setdefault(temp_key[0], [])
                    if open_order not in sku_open_orders_dict[temp_key[0]]:
                        sku_open_orders_dict[temp_key[0]].append(open_order)

            for sku in sku_records:
                group_data = stocks.filter(stock__sku__sku_code=sku['sku_code']).values('group_key', 'stock_sum')
                group_data1 = unsellable_stock.filter(stock__sku__sku_code=sku['sku_code'])#.\
                                        #exclude(group_key__in=group_data.values_list('group_key', flat=True))
                group_data2 = bulk_zone_stock.filter(stock__sku__sku_code=sku['sku_code']) #.\
                                        #exclude(group_key__in=group_data.values_list('group_key', flat=True))
                mrp_dict = {}
                sku_open_orders = sku_open_orders_dict.get(str(sku['sku_code']), [])
                for stock_dat in group_data:
                    splitted_val = stock_dat['group_key'].split('<<>>')
                    sku_code = splitted_val[0]
                    mrp = splitted_val[1]
                    #ean = splitted_val[2]
                    weight = splitted_val[2]
                    # if not ean:
                    #     ean = ''
                    if not weight:
                        weight = 0
                    if not mrp:
                        mrp = 0
                    sub_group_key = '%s<<>>%s' % (str(mrp), str(weight))
                    inventory = stock_dat['stock_sum']
                    if not inventory:
                        inventory = 0
                    pick_filter = {'stock__sku__sku_code': sku_code}
                    if mrp:
                        pick_filter['stock__batch_detail__mrp'] = mrp
                    reserved = pick_res.get(stock_dat['group_key'], 0)
                    sell_filter = {'stock__sku__sku_code': sku_code}
                    if mrp or mrp == 0:
                        sell_filter['stock__batch_detail__mrp'] = mrp
                    unsellable = unsellable_stock.filter(**sell_filter).\
                                                aggregate(Sum('quantity'))['quantity__sum']
                    if not unsellable:
                        unsellable = 0
                    # bulk_stock = bulk_zone_stock.filter(**sell_filter).\
                    #                             aggregate(Sum('quantity'))['quantity__sum']
                    # if not bulk_stock:
                    #     bulk_stock = 0
                    inventory -= reserved
                    open_order_key = '%s<<>>%s' % (str(sku_code), str(mrp))
                    open_qty = open_orders.get(open_order_key, 0)
                    if open_order_key in sku_open_orders:
                        del sku_open_orders[sku_open_orders.index(open_order_key)]
                    inventory -= open_qty
                    reserved += open_qty
                    #if inventory < 0:
                    #    inventory = 0
                    mrp_dict.setdefault(sub_group_key, OrderedDict(( ('mrp', mrp), ('weight', weight),
                                                                     ('inventory', OrderedDict((('sellable', 0),
                                                                                                ('on_hold', 0),
                                                                                                ('un_sellable', 0),
                                                                                                ('bulk_area', 0)))))))
                    mrp_dict[sub_group_key]['inventory']['sellable'] += int(inventory)
                    mrp_dict[sub_group_key]['inventory']['on_hold'] += int(reserved)
                    #mrp_dict[sub_group_key]['inventory']['un_sellable'] += int(unsellable)
                for stock_dat1 in group_data1:
                    splitted_val = stock_dat1['group_key'].split('<<>>')
                    sku_code = splitted_val[0]
                    mrp = splitted_val[1]
                    #ean = splitted_val[2]
                    weight = splitted_val[2]
                    # if not ean:
                    #     ean = ''
                    if not weight:
                        weight = 0
                    if not mrp:
                        mrp = 0
                    sub_group_key = '%s<<>>%s' % (str(mrp), weight)
                    if not mrp:
                        mrp = 0
                    inventory = stock_dat1['stock_sum']
                    if not inventory:
                        inventory = 0
                    mrp_dict.setdefault(sub_group_key, OrderedDict(( ('mrp', mrp), ('weight', weight),
                                                                     ('inventory', OrderedDict((('sellable', 0),
                                                                                                ('on_hold', 0),
                                                                                                ('un_sellable', 0),
                                                                                                ('bulk_area', 0)))))))
                    mrp_dict[sub_group_key]['inventory']['un_sellable'] += int(inventory)
                for stock_dat2 in group_data2:
                    splitted_val = stock_dat2['group_key'].split('<<>>')
                    sku_code = splitted_val[0]
                    mrp = splitted_val[1]
                    #ean = splitted_val[2]
                    weight = splitted_val[2]
                    # if not ean:
                    #     ean = ''
                    if not weight:
                        weight = 0
                    if not mrp:
                        mrp = 0
                    sub_group_key = '%s<<>>%s' % (str(mrp), weight)
                    if not mrp:
                        mrp = 0
                    inventory = stock_dat2['stock_sum']
                    if not inventory:
                        inventory = 0
                    mrp_dict.setdefault(sub_group_key, OrderedDict(( ('mrp', mrp), ('weight', weight),
                                                                     ('inventory', OrderedDict((('sellable', 0),
                                                                                                ('on_hold', 0),
                                                                                                ('un_sellable', 0),
                                                                                                ('bulk_area', 0)))))))
                    mrp_dict[sub_group_key]['inventory']['bulk_area'] += int(inventory)
                for sku_open_order in sku_open_orders:
                    open_sku_code, open_sku_mrp = sku_open_order.split('<<>>')
                    # open_ean = 0
                    # if sku_eans.get(open_sku_code, 0):
                    #     open_ean = sku_eans[open_sku_code]
                    # elif ean_list.get(open_sku_code, 0):
                    #     open_ean = ean_list[open_sku_code]
                    open_weight = sku_weight_dict.get(open_sku_code, '')
                    if not open_weight:
                        open_weight = 0
                    open_order_grouping_key = '%s<<>>%s' % (str(open_sku_mrp), str(open_weight))
                    mrp_dict.setdefault(open_order_grouping_key, OrderedDict(( ('mrp', open_sku_mrp),
                                                                      ('weight', open_weight), ('inventory',
                                                         OrderedDict((('sellable', 0),
                                                                    ('on_hold', 0),
                                                                    ('un_sellable', 0),
                                                                      ('bulk_area', 0)))))))
                    mrp_dict[open_order_grouping_key]['inventory']['sellable'] -= open_orders[sku_open_order]
                    mrp_dict[open_order_grouping_key]['inventory']['on_hold'] += open_orders[sku_open_order]
                mrp_list = mrp_dict.values()
                if not mrp_list:
                    sku_obj = SKUMaster.objects.get(id=sku['id'])
                    mrp_list = [OrderedDict(( ('mrp', sku_obj.mrp), ('weight', get_sku_weight(sku_obj)),
                                                                     ('inventory', OrderedDict((('sellable', 0),
                                                                                                ('on_hold', 0),
                                                                                                ('un_sellable', 0),
                                                                                                ('bulk_area', 0))))))]
                data.append(OrderedDict(( ('sku', sku['sku_code']), ('data', mrp_list))))
        else:
            stocks = dict(SellerStock.objects.select_related('seller', 'stock', 'stock__location__zone').\
                          filter(seller_id=seller_master_id,stock__sku__user=user.id, stock__quantity__gt=0).\
                                exclude(Q(stock__location__zone__zone__in=picklist_exclude_zones) |
                                        Q(stock__receipt_number=0)).values_list('stock__sku__sku_code').distinct().\
                          annotate(tot_stock=Sum('quantity')))
            pick_res = dict(PicklistLocation.objects.select_related('seller__sellerstock', 'stock', 'stock__sku').\
                            filter(stock__sellerstock__seller_id=seller_master_id, reserved__gt=0, status=1,
                                    stock__sellerstock__quantity__gt=0, stock__sku__user=user.id).\
                            values_list('stock__sku__sku_code').distinct().annotate(tot_stock=Sum('reserved')))
            unsellable_stock = dict(SellerStock.objects.select_related('seller', 'stock', 'stock__location__zone__zone').\
                          filter(seller_id=seller_master_id,stock__sku__user=user.id, stock__quantity__gt=0,
                                 stock__location__zone__zone='Non Sellable Zone').\
                              values_list('stock__sku__sku_code').distinct().\
                          annotate(tot_stock=Sum('quantity')))
            for sku in sku_records:
                inventory = stocks.get(sku['sku_code'], 0)
                reserved = pick_res.get(sku['sku_code'], 0)
                unsellable = unsellable_stock.get(sku['sku_code'], 0)
                inventory -= reserved
                data.append(OrderedDict(( ('sku', sku['sku_code']), ('inventory', int(inventory)),
                                          ('on_hold', int(reserved)), ('un_sellable', unsellable))))
        page_info['data'] = data
        #data = scroll_data(request, data, limit=limit)
        response_data = {'page_info': page_info.get('page_info', {}), 'status': 200,
                         'messages': [{'errors': error_status}],
                         'products': page_info['data']}
        output_status = 200
        if error_status:
            output_status = 207
        if user.username in MILKBASKET_USERS:
            log_mb_sync = ('Get inventory for user %s is %s ' %(str(request.user.username), str(data)))
            mb_stock_sycn_log(log_mb_sync, user)
        return HttpResponse(json.dumps(response_data, cls=DjangoJSONEncoder), status=output_status)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Get Inventory failed for %s and params are %s and error statement is %s' % (str(request.user.username), str(request.body), str(e)))
        response_data = {'messages': 'Internal Server Error', 'status': 500}
        return HttpResponse(json.dumps(response_data, cls=DjangoJSONEncoder), status=500)


@csrf_exempt
@login_required
def rista_update_orders(request):
    try:
        orders = json.loads(eval(request.body)['all_orders'])
        rista_resp = json.loads(eval(request.body)['resp'])
    except:
        return HttpResponse(json.dumps({'status': 400, 'message': 'Please send proper data'}))
    log.info('Request params for ' + request.user.username + ' is ' + str(orders))
    try:
        if request.user.userprofile.user_type == 'marketplace_user':
            validation_dict, failed_status, final_data_dict = validate_seller_orders_format(orders, user=request.user,
                                                                                     company_name='mieone')
        else:
            validation_dict, failed_status, final_data_dict = validate_orders_format_rista(orders, user=request.user, company_name='mieone')
        if validation_dict:
            return HttpResponse(json.dumps({'messages': validation_dict, 'status': 0}))
        if failed_status:
            if type(failed_status) == dict:
                failed_status.update({'Status': 'Failure'})
            if type(failed_status) == list:
                failed_status = failed_status[0]
                failed_status.update({'Status': 'Failure'})
            return HttpResponse(json.dumps(failed_status))
        status = update_order_dicts_rista(final_data_dict, rista_resp, user=request.user, company_name='mieone')
        log.info(status)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update orders data failed for %s and params are %s and error statement is %s' % (str(request.user.username), str(request.body), str(e)))
        status = {'messages': 'Internal Server Error', 'status': 0}
    return HttpResponse(json.dumps(status))


def store_hippo_line_items(line_items):
    itemsArr = []
    for Item in line_items:
        cgst_percent = 0
        sgst_percent = 0
        igst_percent = 0
        for ind in Item['taxes']:
            if ind['name'] == "IGST":
                igst_percent += ind['rate']
            if ind['name'] == "SGST":
                sgst_percent += ind['rate']
            if ind['name'] == "CGST":
                cgst_percent += ind['rate']
        obj = {
            "line_item_id": Item.get('_id',None),
            "sku": Item.get('sku',None),
            "name": Item.get('name',None),
            "quantity": Item.get('quantity',None),
            "unit_price": Item.get('price',None),
            "shipping_charge": Item.get('shipping_total',None),
            "discount_amount": 0,
            "tax_percent": {
                "CGST": cgst_percent,
                "SGST": sgst_percent,
                "IGST": igst_percent
            }
        }
        itemsArr.append(obj)
    return itemsArr


def create_order_storehippo(store_hippo_data, user_obj):
    create_order_storehippo_log.info('Create Store Hippo Data' + str(store_hippo_data))
    allOrders = []
    create_order = {}
    customer_obj = store_hippo_data.get('billing_address', '')
    create_order['source'] = 'store_hippo'
    create_order['original_order_id'] = store_hippo_data.get('order_id', '')
    create_order['order_id'] = create_order.get('original_order_id', '')
    create_order['order_code'] = ''
    create_order['order_date'] = store_hippo_data['created_on'][0:10] + " " + store_hippo_data['created_on'][11:19]
    create_order['order_status'] = 'NEW'
    create_order['billing_address'] = customer_obj
    create_order['shipping_address'] = store_hippo_data.get('shipping_address', '')
    create_order['items'] = store_hippo_line_items(store_hippo_data.get('items', ''))
    create_order['discount'] = store_hippo_data.get('discounts_total', 0)
    create_order['shipping_charges'] = store_hippo_data.get('shipping_total', 0)
    create_order['customer_name'] = customer_obj.get('full_name', '')
    create_order['customer_code'] = ''
    create_order['item_count'] = store_hippo_data.get('item_count', 0)
    create_order['all_total_items'] = store_hippo_data.get('sub_total', 0)
    create_order['all_total_tax'] = store_hippo_data.get('taxes_total', 0)
    create_order['status'] = store_hippo_data.get('status', 0)
    create_order['fulfillmentStatus'] = store_hippo_data.get('fulfillment_status', '')
    create_order['custom_shipping_applied'] = store_hippo_data.get('custom_shipping_applied', 0)
    create_order['order_reference'] = store_hippo_data.get('_id', '')
    admin_discounts = store_hippo_data.get('discounts', [])
    if admin_discounts:
        admin_discounts = admin_discounts[0].get('saved_amount',0)
    create_order['invoice_amount'] = create_order.get('all_total_items', 0) + create_order.get('all_total_tax', 0) + create_order.get('shipping_charges', 0) - create_order.get('discount', 0)
    allOrders.append(create_order)
    try:
        validation_dict, failed_status, final_data_dict = validate_orders_format_storehippo(allOrders, user=user_obj, company_name='mieone')
        if validation_dict:
            return json.dumps({'messages': validation_dict, 'status': 0})
        if failed_status:
            if type(failed_status) == dict:
                failed_status.update({'Status': 'Failure'})
            if type(failed_status) == list:
                failed_status = failed_status[0]
                failed_status.update({'Status': 'Failure'})
            return json.dumps(failed_status)
        create_order_storehippo_log.info('StoreHippo Data Sent to Stockone ' + str(final_data_dict))
        status = update_order_dicts(final_data_dict, user=user_obj, company_name='storehippo')
        create_order_storehippo_log.info(status)
        return status
    except Exception as e:
        import traceback
        create_order_storehippo_log.debug(traceback.format_exc())
        create_order_storehippo_log.info('Update orders data failed for %s and params are %s and error statement is %s' % (str(user_obj.username), str(request.body), str(e)))
        status = {'messages': 'Internal Server Error', 'status': 0}
        return status


def create_update_sku_storehippo(store_hippo_data, user_obj):
    create_update_sku_storehippo_log.info('StoreHippo Data ' + str(store_hippo_data))
    try:
        stockone_data = {}
        sku_code = store_hippo_data.get('uniquesku', '')
        if sku_code:
            sku_code = sku_code[0]
        categories = store_hippo_data.get('categories', '')
        if categories:
            categories = categories[0]
        image = store_hippo_data.get('images','')
        if image:
            image = image[0]['tempSrc']
        desc = store_hippo_data.get('description', '')
        if desc:
            desc = desc.replace('<p>', '')
            desc = desc.replace('</p>', '')
        variants = store_hippo_data.get('variants', [])
        for var_obj in variants:
            sku_code = var_obj.get('sku', '')
            stockone_data['sku_code'] = sku_code
            stockone_data['wms_code'] = sku_code
            stockone_data['sku_desc'] = desc
            stockone_data['sku_group'] = ''
            stockone_data['sku_type'] = ''
            stockone_data['sku_category'] = categories
            stockone_data['sku_class'] = ''
            stockone_data['threshold_quantity'] = store_hippo_data.get('inventory_low_stock_quantity', 0)
            stockone_data['online_percentage'] = 0
            stockone_data['image_url'] = image
            stockone_data['qc_check'] = 0
            stockone_data['status'] = store_hippo_data.get('publish', 0)
            stockone_data['relation_type'] = ''
            stockone_data['discount_percentage'] = 0
            stockone_data['price'] = var_obj.get('price', 0)
            stockone_data['product_type'] = ''
            stockone_data['sku_brand'] = store_hippo_data.get('brand', '')
            stockone_data['sku_size'] = ''
            stockone_data['style_name'] = var_obj.get('variant_id','')
            stockone_data['mrp'] = var_obj.get('compare_price', 0)
            stockone_data['sequence'] = 0
            stockone_data['measurement_type'] = ''
            stockone_data['sale_through'] = ''
            stockone_data['color'] = ''
            stockone_data['mix_sku'] = ''
            stockone_data['load_unit_handle'] = ''
            stockone_data['hsn_code'] = ''
            stockone_data['sub_category'] = ''
            stockone_data['primary_category'] = ''
            stockone_data['cost_price'] = var_obj.get('price', 0)
            stockone_data['shelf_life'] = 0
            stockone_data['enable_serial_based'] = 0
            stockone_data['youtube_url'] = ''
            stockone_data['user'] = user_obj.id
            try:
		sku_obj = SKUMaster.objects.filter(**{'user':user_obj.id, 'sku_code':sku_code})
		if not sku_obj:
		    sku_query_obj = SKUMaster.objects.create(**stockone_data)
		    create_update_sku_storehippo_log.info('Created SKU ' + str(stockone_data))
		else:
		    sku_query_obj = sku_obj.update(**stockone_data)
		    create_update_sku_storehippo_log.info('Updated SKU '+ str(stockone_data))
            except:
		sku_query_obj = "Error Occured"
		create_update_sku_storehippo_log.info('Error Occured in create_update_sku_storehippo')
        else:
            stockone_data['sku_code'] = sku_code
            stockone_data['wms_code'] = sku_code
            stockone_data['sku_desc'] = desc
            stockone_data['sku_group'] = ''
            stockone_data['sku_type'] = ''
            stockone_data['sku_category'] = categories
            stockone_data['sku_class'] = ''
            stockone_data['threshold_quantity'] = store_hippo_data.get('inventory_low_stock_quantity', 0)
            stockone_data['online_percentage'] = 0
            stockone_data['image_url'] = image
            stockone_data['qc_check'] = 0
            stockone_data['status'] = store_hippo_data.get('publish', 0)
            stockone_data['relation_type'] = ''
            stockone_data['discount_percentage'] = 0
            stockone_data['price'] = store_hippo_data.get('price', 0)
            stockone_data['product_type'] = ''
            stockone_data['sku_brand'] = store_hippo_data.get('brand', '')
            stockone_data['sku_size'] = ''
            stockone_data['style_name'] = ''
            stockone_data['mrp'] = store_hippo_data.get('compare_price', 0)
            stockone_data['sequence'] = 0
            stockone_data['measurement_type'] = ''
            stockone_data['sale_through'] = ''
            stockone_data['color'] = ''
            stockone_data['mix_sku'] = ''
            stockone_data['load_unit_handle'] = ''
            stockone_data['hsn_code'] = ''
            stockone_data['sub_category'] = ''
            stockone_data['primary_category'] = ''
            stockone_data['cost_price'] = store_hippo_data.get('price', 0)
            stockone_data['shelf_life'] = 0
            stockone_data['enable_serial_based'] = 0
            stockone_data['youtube_url'] = ''
            stockone_data['user'] = user_obj.id
            try:
		sku_obj = SKUMaster.objects.filter(**{'user':user_obj.id, 'sku_code':sku_code})
		if not sku_obj:
		    sku_query_obj = SKUMaster.objects.create(**stockone_data)
		    create_update_sku_storehippo_log.info('Created SKU ' + str(stockone_data))
		else:
		    sku_query_obj = sku_obj.update(**stockone_data)
		    create_update_sku_storehippo_log.info('Updated SKU '+ str(stockone_data))
            except:
		sku_query_obj = "Error Occured"
		create_update_sku_storehippo_log.info('Error Occured in create_update_sku_storehippo')
    except:
        create_update_sku_storehippo_log.info('Error Occured in create_update_sku_storehippo function')
        return "Error Occured"
    return sku_query_obj


def order_edit_storehippo(store_hippo_data, user_obj):
    order_edit_storehippo_log.info('Input Data - For User '+ user_obj.username + ' , ' + str(store_hippo_data))
    order_id_list = []
    if store_hippo_data['status'] == 'cancelled':
        order_id = store_hippo_data.get('order_id', '')
        order_id_list.append(order_id)
	ids_of_orders = list(set(OrderDetail.objects.filter(original_order_id__in=order_id_list).values_list('id', flat=True)))
        order_edit_storehippo_log.info('Input List of Order IDs sent' + str(ids_of_orders))
	cancel_order = order_cancel_functionality(ids_of_orders)
        order_edit_storehippo_log.info('Output Response' + str(cancel_order))
    return store_hippo_data


def store_hippo(request):
    a = datetime.datetime.now()
    api_type = request.META['HTTP_TYPE']
    store_hippo_data = json.loads(request.body)
    storehippo_log.info('------------API Type -' + api_type + '------------')
    status_resp = ''
    try:
        user_obj = User.objects.get(username='acecraft')
    except:
        storehippo_log.info("User Not Found")
        return HttpResponse("User Not found")
    if api_type == 'add_order':
        status_resp = create_order_storehippo(store_hippo_data, user_obj)
    if api_type in ['add_sku', 'edit_sku']:
        status_resp = create_update_sku_storehippo(store_hippo_data, user_obj)
    if api_type == 'order_edit':
        status_resp = order_edit_storehippo(store_hippo_data, user_obj)
    b = datetime.datetime.now()
    delta = b - a
    time_taken = str(delta.total_seconds())
    storehippo_log.info('------------End Time Taken in Seconds --- ' + time_taken + '-----')
    return HttpResponse(json.dumps(status_resp.sku_code))
