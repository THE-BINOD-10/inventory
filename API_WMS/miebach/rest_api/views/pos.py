import os
import subprocess
import sys

import json
from dateutil import tz
from dateutil.relativedelta import relativedelta

from django.http import HttpResponse, HttpResponseRedirect
from django.core import serializers
from django.contrib.auth import authenticate
from django.contrib import auth
from django.views.decorators.csrf import csrf_exempt

from miebach_admin.custom_decorators import login_required, get_admin_user
from common import *
from miebach_utils import *

# Create your views here.
log = init_logger('logs/pos.log')

@login_required
@csrf_exempt
def validate_sales_person(request):
    response_data = {'status': 'Fail'}
    user_id = request.GET.get('user_id')
    user_name = request.GET.get('user_name')
    if user_id and user_name:
        data = SalesPersons.objects.filter(user_id = user_id)
        VAT = '14.5'
        response_data['status'] = 'Success'
        response_data['VAT'] = VAT
        response_data['user_name'] = data[0].user_name
        response_data['sales_person_id'] = data[0].id
        response_data['user_id'] = user_id
    return HttpResponse(json.dumps(response_data))

@login_required
@csrf_exempt
def get_pos_user_data(request):
    user_id = request.GET.get('id')
    user = User.objects.get(id = user_id)
    status = subprocess.check_output(['pgrep -lf sku_master_file_creator'],\
                                     stderr = subprocess.STDOUT, shell = True)
    if "python" not in status:
       sku_query = "%s %s/%s %s&" % ("python", settings.BASE_DIR,\
                                    "sku_master_file_creator.py", str(user.id))
       subprocess.call(sku_query, shell=True)
    else:
       log.info("\nAlready running sku master creation script\n")
    customer_query = "%s %s/%s %s&" % ("python", settings.BASE_DIR,\
                     "customer_master_file_creator.py", str(user.id))
    subprocess.call(customer_query, shell=True)

    response_data = {}
    user = UserProfile.objects.filter(user__id = user_id)
    if user:
        user = user[0]
        vat = '14.5'
        response_data['status'] = 'Success'
        response_data['VAT'] = vat
        response_data['parent_id'] = user.user.id
        response_data['company'] = user.company_name
        response_data['address'] = user.address
        response_data['phone'] = user.phone_number
        response_data['gstin'] = user.gst_number
        return HttpResponse(json.dumps(response_data))
    return HttpResponse("fail")


@login_required
@csrf_exempt
def get_current_order_id(request):
   user = request.GET.get('user','')
   order_id = get_order_id(user)
   return HttpResponse(json.dumps({'order_id': order_id}))


@login_required
def search_pos_customer_data(request):
    search_key = request.GET['key']
    total_data = []
    user = request.user.id
    user = request.GET.get('user')
    if user:
        user = user
    if len(search_key) < 3:
      return HttpResponse(json.dumps(total_data))
    lis = ['name', 'email_id', 'phone_number', 'address', 'status']
    master_data = CustomerMaster.objects.filter(Q(phone_number__icontains = search_key) |\
                                         Q(name__icontains = search_key), user = user)
    for data in master_data[:30]:
        status = 'Inactive'
        if data.status:
            status = 'Active'
        if data.phone_number:
            data.phone_number = int(float(data.phone_number))
        total_data.append({'ID': data.id, 'FirstName': data.name,
                           'LastName': data.last_name, 'Address': data.address,
                           'Number': str(data.phone_number), 'Email': data.email_id})
    return HttpResponse(json.dumps(total_data))


@login_required
def search_product_data(request):
    search_key = request.GET['key']
    user_id = request.GET['user']
    user = User.objects.filter(id = user_id)[0]
    total_data = []
    master_data = SKUMaster.objects.exclude(sku_type = 'RM')\
                           .filter(Q(wms_code__icontains = search_key) |\
                            Q(sku_desc__icontains = search_key), user = user_id)
    for data in master_data[:30]:
        status = 'Inactive'
        if data.status:
            status = 'Active'
        zone = ''
        if data.zone_id:
            zone = data.zone.zone
        price = data.price
        tax_master = TaxMaster.objects.filter(user = user,\
                     product_type = data.product_type, max_amt__gte=data.price,\
                     min_amt__lte = data.price)
        sgst, cgst, igst, utgst = [0]*4
        if tax_master:
           sgst = tax_master[0].sgst_tax
           cgst = tax_master[0].cgst_tax
           igst = tax_master[0].igst_tax
           utgst= tax_master[0].utgst_tax

        discount_percentage = data.discount_percentage
        discount_price = price
        if not data.discount_percentage:
          category = CategoryDiscount.objects.filter(category = data.sku_category)
          if category:
            category = category[0]
            if category.discount:
              discount_percentage = category.discount
        if discount_percentage:
            discount_price = price - ((price * discount_percentage) / 100)
        stock_quantity = StockDetail.objects.exclude(location__zone__zone = 'DAMAGED_ZONE')\
                                    .filter(sku__wms_code = data.wms_code,\
                                     sku__user = user_id).aggregate(Sum('quantity'))
        stock_quantity = stock_quantity['quantity__sum']
        if not stock_quantity:
            stock_quantity = 0
        total_data.append({'search': str(data.wms_code) + " " + data.sku_desc,
                           'SKUCode': data.wms_code,
                           'ProductDescription': data.sku_desc,
                           'price': discount_price,
                           'url': data.image_url, 'data-id': data.id,
                           'discount': discount_percentage,
                           'selling_price': price,
                           'stock_quantity': stock_quantity,
                           'sgst': sgst, 'cgst': cgst,
                           'igst': igst, 'utgst': utgst})
    return HttpResponse(json.dumps(total_data))


@login_required
def add_customer(request):
    new_customers = eval(request.POST.get("customers"))
    user = new_customers[0]["user"]
    customer_id = 1
    customer_master = CustomerMaster.objects.filter(user = user)\
                                    .values_list('customer_id', flat = True)\
                                    .order_by('-customer_id')
    if customer_master:
        customer_id = customer_master[0] + 1
    for customer in new_customers:
       CustomerMaster.objects.create(name = customer['firstName'],\
                                     last_name = customer['secondName'],\
                                     email_id = customer['mail'],\
                                     phone_number = customer['number'],\
                                     user = customer['user'], customer_id = customer_id)
       customer_id += 1
    #update master customer txt file
    customer_query = "%s %s/%s %s&" % ("python", settings.BASE_DIR,\
                                      "customer_master_file_creator.py", str(user))
    subprocess.call(customer_query, shell=True)
    return HttpResponse("success")


def get_stock_count(request, order, stock, stock_diff, user, order_quantity):
    stock_quantity = float(stock.quantity)
    if stock_quantity <= 0:
        return 0, stock_diff
    if stock_diff:
        if stock_quantity >= stock_diff:
            stock_count = stock_diff
            stock_diff = 0
        else:
            stock_count = stock_quantity
            stock_diff -= stock_quantity
    else:
        if stock_quantity >= order_quantity:
            stock_count = order_quantity
        else:
            stock_count = stock_quantity
            stock_diff = order_quantity - stock_quantity
    return stock_count, stock_diff


def picklist_creation(request, stock_detail, stock_quantity, order_detail,\
                      picklist_number, stock_diff, item, user, invoice_number):
   #seller_order_summary object creation
   seller_order_summary = SellerOrderSummary.objects.create(pick_number = 1,\
                                             seller_order = None,\
                                             order = order_detail,\
                                             picklist = None,\
                                             quantity = order_detail.quantity,\
                                             invoice_number = invoice_number)
   if stock_quantity < int(order_detail.quantity):
       picklist = Picklist.objects.create(picklist_number = picklist_number,\
                                          reserved_quantity = 0,\
                                          picked_quantity = stock_diff,\
                                          remarks = 'Picklist_' + str(picklist_number),\
                                          status = 'batch_picked',\
                                          order_id = order_detail.id,\
                                          stock_id = '', creation_date=NOW)
   CustomerOrderSummary.objects.create(order_id = order_detail.id,\
                                       discount = item['discount'],\
                                       issue_type = order_detail.order_code,\
                                       cgst_tax = item['cgst_percent'],\
                                       sgst_tax = item['sgst_percent'],\
                                       creation_date = NOW)
   stock_diff = 0
   for stock in stock_detail:
       stock_count, stock_diff = get_stock_count(request, order_detail, stock,\
                                     stock_diff, user, order_detail.quantity)
       if not stock_count:
           continue
       stock.quantity = int(stock.quantity) - stock_count
       stock.save()
       picklist = Picklist.objects.create(picklist_number=picklist_number,\
                                          reserved_quantity = 0,\
                                          picked_quantity = stock_count,\
                                          remarks = 'Picklist_' + str(picklist_number),\
                                          status = 'batch_picked',\
                                          order_id = order_detail.id,\
                                          stock_id = stock.id,creation_date = NOW)
       PicklistLocation.objects.create(quantity = stock_count, status = 0,\
                                       picklist_id = picklist.id, reserved = 0,\
                                       stock_id = stock.id,\
                                       creation_date=NOW)
       if not stock_diff:
           break
   return "Success"


@login_required
@csrf_exempt
def customer_order(request):
    orders = request.POST['order']
    orders = eval(orders)
    order_ids = []
    only_return = True
    if isinstance(orders, dict): orders = [orders]
    for order in orders:
            user_id = order['user']['parent_id']
            user = User.objects.get(id = user_id)
            if not order['customer_data']:
                return HttpResponse(json.dumps({'message': 'Missing Customer Data'}))
            cust_dict = order['customer_data']
            number = order['customer_data']['Number']
            customer_data = CustomerMaster.objects.filter(phone_number = number,\
                                                          user = user_id)
            order_id = get_order_id(user_id) if order['summary']['nw_status'] == 'online'\
                                             else order['summary']['order_id']
            status = 0 if order['summary']['issue_type'] == "Delivery Challan"\
                       else 1
            order_ids.append(order_id)
            picklist_number = get_picklist_number(user) + 1
            if customer_data:
                customer_id = customer_data[0].id
                customer_name = customer_data[0].name
            else:
                customer_id = 0
                customer_name = cust_dict.get('FirstName','')
            customer_order = []

            sku_stocks = StockDetail.objects.filter(sku__user=user_id, quantity__gt=0)
            sku_id_stocks = sku_stocks.values('id', 'sku_id').annotate(total = Sum('quantity'))
            pick_res_locat = PicklistLocation.objects.prefetch_related('picklist', 'stock')\
                                             .filter(status = 1)\
                                             .filter(picklist__order__user = user_id)\
                                             .values('stock__sku_id')\
                                             .annotate(total = Sum('reserved'))
            """val_dict = {}
            val_dict['pic_res_ids'] = map(lambda d: d['stock__sku_id'], pick_res_locat)
            val_dict['pic_res_quans'] = map(lambda d: d['total'], pick_res_locat)
            val_dict['sku_ids'] = map(lambda d: d['sku_id'], sku_id_stocks)
            val_dict['stock_ids'] = map(lambda d: d['id'], sku_id_stocks)
            val_dict['stock_totals'] = map(lambda d: d['total'], sku_id_stocks)"""
            if customer_name:
                for item in order['sku_data']:

                    sku = SKUMaster.objects.get(wms_code = item['sku_code'],\
                                                user = user_id)
                    #if not returning item
                    if item['return_status'] == "false":
                        only_return = False
                        order_detail = OrderDetail.objects.create(user = user_id,\
                                                   marketplace = "Offline",\
                                                   order_id = order_id,\
                                                   sku_id = sku.id,\
                                                   customer_id = customer_id,\
                                                   customer_name = customer_name,\
                                                   telephone = number,\
                                                   title = sku.sku_desc,\
                                                   quantity = item['quantity'],\
                                                   invoice_amount = item['price'],\
                                                   order_code = order['summary']['issue_type'],\
                                                   shipment_date = NOW,\
                                                   original_order_id = order['summary']['issue_type'] + str(order_id),\
                                                   nw_status = order['summary']['nw_status'],\
                                                   status = status,\
                                                   email_id = cust_dict.get('Email',''),\
                                                   unit_price = item['unit_price'])
                        if status == 0:
                            stock_diff, invoice_number = item['quantity'], order_id
                            stock_detail = StockDetail.objects.exclude(\
                                                              location__zone__zone = 'DAMAGED_ZONE')\
                                                              .filter(sku__wms_code = sku.wms_code,\
                                                              sku__user=user_id)
                            stock_quantity = stock_detail.aggregate(Sum('quantity'))['quantity__sum']
                            picklist_creation(request, stock_detail,\
                                              stock_quantity, order_detail,\
                                              picklist_number, stock_diff,\
                                              item, user, invoice_number)
                    # return item : increase stock
                    else:
                        sku_stocks_ = StockDetail.objects.filter(sku__user = user_id,\
                                                                 sku_id=sku.id)
                        if sku_stocks_: sku_stocks_ = sku_stocks_[0]
                        else:
                            recpt_no = StockDetail.objects.filter(sku__user = user_id)\
                                                  .aggregate(Max('receipt_number'))\
                                                  .get('receipt_number__max', 0) + 1
                            put_zone = ZoneMaster.objects.filter(zone = 'DEFAULT',\
                                                          user=user_id)
                            if not put_zone:
                                create_default_zones(user, 'DEFAULT', 'DEFAULT', 10001)
                                put_zone = ZoneMaster.objects.filter(zone = 'DEFAULT', user = user.id)[0]
                            else:put_zone = put_zone[0]
                            sku_stocks_ = StockDetail.objects.create(\
                                                      receipt_number = recpt_no,\
                                                      sku_id = sku.id,\
                                                      receipt_date = NOW,\
                                                      creation_date = NOW,\
                                                      location = put_zone.locationmaster_set.all()[0])
                        sku_stocks_.quantity = int(sku_stocks_.quantity) + item['quantity']
                        sku_stocks_.save()
                        order_id = "return"
                        #add item to OrderReturns
                        order_return = OrderReturns.objects.create(\
                                                    order = None,\
                                                    seller_order = None,\
                                                    quantity = item['quantity'],\
                                                    damaged_quantity = 0,\
                                                    sku = sku, reason = '',\
                                                    status = 0)
                        order_return.return_id = "MN" + str(order_return.id)
                        order_return.save()
                        return_location = ReturnsLocation.objects.create(\
                                                          quantity = 0,\
                                                          status = 0,\
                                                          location = sku_stocks_.location,\
                                                          returns=order_return)
    if only_return: order_ids=['return']
    return HttpResponse(json.dumps({'order_ids': order_ids}))


@login_required
@csrf_exempt
def print_order_data(request):
    customer_data, summary, gst_based = {}, {}, {}
    sku_data = []
    total_quantity, total_amount, subtotal = [0]*3
    status = 'fail'
    order_date = NOW
    user_id = request.GET['user']
    user = User.objects.get(id = user_id)
    order_id = request.GET['order_id']
    order_date = get_local_date(user, NOW)
    order_detail = OrderDetail.objects.filter(order_id = order_id,\
                                       user = user_id, quantity__gt = 0)
    for order in order_detail:
        selling_price = order.unit_price if order.unit_price != 0\
                                         else float(order.invoice_amount)/float(order.quantity)
        tax_master = {'cgst_tax':0, 'sgst_tax':0, 'igst_tax':0, 'utgst_tax':0} if not order.sku else TaxMaster.objects\
                                                            .filter(user=user_id, product_type=order.sku.product_type,\
                                                            max_amt__gte=order.sku.price, min_amt__lte=order.sku.price)\
                                                            .values('sgst_tax', 'cgst_tax', 'igst_tax', 'utgst_tax')[0]
        gst_based.setdefault(tax_master['cgst_tax'], {'taxable_amt': 0,
                                                      'cgst_percent': tax_master["cgst_tax"],
                                                      'sgst_percent': tax_master["sgst_tax"],
                                                      'sgst': 0,
                                                      'cgst': 0})
        gst_based[tax_master['cgst_tax']]['taxable_amt'] += order.invoice_amount
        gst_based[tax_master['cgst_tax']]['sgst'] += order.invoice_amount * tax_master["sgst_tax"]/100
        gst_based[tax_master['cgst_tax']]['cgst'] += order.invoice_amount * tax_master["cgst_tax"]/100
        sku_data.append({'name': order.title,
                         'quantity': order.quantity,
                         'sku_code': order.sku.sku_code,
                         'price': order.invoice_amount,
                         'unit_price': selling_price,
                         'sgst': selling_price * tax_master["sgst_tax"]/100,
                         'cgst': selling_price * tax_master["cgst_tax"]/100
                       })
        total_quantity += int(order.quantity)
        total_amount += (float(order.invoice_amount) + float(order.invoice_amount) * tax_master["sgst_tax"]/100 +\
                        float(order.invoice_amount) * tax_master["cgst_tax"]/100);
    if order_detail:
        status = 'success'
        order = order_detail[0]
        customer_id = ''
        order_date = get_local_date(user, order.creation_date)
        if order.customer_id:
            customer_master = CustomerMaster.objects.filter(id = order.customer_id,\
                                                     name = order.customer_name,\
                                                     user = user_id)
            if customer_master:
                customer_id = customer_master[0].id
        customer_data = {'FirstName': order.customer_name,
                         'LastName': '',
                         'Number': order.telephone,
                         'ID': customer_id,
                         'Address': order.address,
                         'Email': order.email_id}
        order_summary = CustomerOrderSummary.objects.filter(order_id = order.id)
        if order_summary:
            order_summary = order_summary[0]
            summary = {'total_quantity': total_quantity,
                       'total_amount': total_amount,
                       'subtotal': total_amount,
                       'gst_based': gst_based,
                       'issue_type': order_summary.issue_type}
    return HttpResponse(json.dumps({'data':
                                        {'customer_data': customer_data,
                                         'summary': summary,
                                         'sku_data': sku_data,
                                         'order_id': order_id,
                                         'order_date': order_date},
                                    'status': status}))


def get_order_details(order_id, user_id, mobile, customer_name, request_from):
    customer_data, order_data = {}, {}
    summary, sku_data = [], []
    total_quantity, total_amount, subtotal = [0]*3
    to_zone = tz.gettz('Asia/Kolkata')
    #if return, get orders of all order code with status 0
    if request_from == "return" or request_from == "initial_preorder":
        status = 0 if request_from == "return" else 1
        min_order_date = datetime.datetime.now() - datetime.timedelta(days = 20)
        order_detail = OrderDetail.objects.filter(user = user_id,\
                                           quantity__gt = 0,status = status,\
                                           creation_date__gte = min_order_date)
        if status == 1:
            order_detail = order_detail.filter(order_code = 'Pre Order')
        if order_id:
            order_detail = order_detail.filter(order_id = order_id)
        else:
            if mobile:
                order_detail = order_detail.filter(telephone = mobile)
            if customer_name :
                order_detail = order_detail.filter(customer_name__icontains = customer_name)
    elif request_from == "preorder":
        order_detail = OrderDetail.objects.filter(user = user_id, quantity__gt = 0,\
                                                  order_code='Pre Order')
    else:
        order_detail = OrderDetail.objects.filter(user = user_id,\
                                           status = 1, order_code = 'Pre Order')
    if order_id: order_detail = order_detail.filter(order_id = order_id)
    for order in order_detail:
        selling_price = order.unit_price if order.unit_price != 0\
                                         else float(order.invoice_amount)/float(order.quantity)
        order_id = str(order.order_id)
        order_data.setdefault(order_id,{})
        order_data[order_id]['order_id'] = order_id
        order_data[order_id]['order_date'] = order.creation_date\
                                                  .astimezone(to_zone)\
                                                  .strftime("%d %b %Y %I:%M %p")
        order_data[order_id]['status'] = order.status
        order_data[order_id].setdefault('sku_data', []).append({'name': order.title,
                                                                'quantity': order.quantity,
                                                                'sku_code': order.sku.sku_code,
                                                                'price': order.invoice_amount,
                                                                'selling_price': selling_price,
                                                                'order_id': order_id,
                                                                'id': order.id})
        total_quantity += int(order.quantity)
        total_amount += int(order.invoice_amount)
	status = order.status

        order_data[order_id]['customer_data'] = {'Name': order.customer_name,
                                                 'Number': order.telephone,
                                                 'Address': order.address,
                                                 'Email': order.email_id}
    return json.dumps({'data': order_data})


@login_required
def pre_order_data(request):
   data = eval(request.POST['data'])
   order_id = data.get('order_id', '')
   mobile = data.get('mobile', '')
   customer_name = data.get('customer_name', '')
   request_from = data.get('request_from', '')
   order_details = get_order_details(order_id, data['user'], mobile,\
                                     customer_name, request_from)
   return HttpResponse(order_details)


@login_required
def update_order_status(request):
  full_data = eval(request.POST['data'])
  nw_status = "offline"
  if isinstance(full_data, dict):
    full_data = [full_data]
    nw_status = "online"
  for data in full_data:
      order_detail = OrderDetail.objects.filter(order_id = data['order_id'],\
                                                user=data['user'],\
                                                quantity__gt=0,\
                                                order_code='Pre Order')
      if data['delete_order'] == "true":
        order_detail.delete()
        if nw_status=="online":
            return HttpResponse("Deleted Successfully !")
        else:
            continue
      for order in order_detail:
        order.status = 0
        sku = order.sku
        user_id = order.user
        user = User.objects.get(id = user_id)
        picklist_number = get_picklist_number(user) + 1
        stock_detail = StockDetail.objects.filter(sku = sku, quantity__gt = 0)
        if stock_detail: order.save()
        else:
           if nw_status=="online": return HttpResponse("Error")
           order.save()
           continue

        stock_diff = StockDetail.objects.filter(sku = sku)\
                                .exclude(location__zone__zone = 'DAMAGED_ZONE')\
                                .values_list('sku__wms_code').distinct()\
                                .annotate(total = Sum('quantity'))[0][1]
        sku_master = SKUMaster.objects.filter(user = user_id, id = order.sku.id)\
                                      .values_list('product_type',\
                                                   'price', 'discount_percentage')[0]

        tax_master = {'cgst_tax':0, 'sgst_tax':0, 'igst_tax':0, 'utgst_tax':0} if not sku_master[0] else TaxMaster.objects\
                                                            .filter(user=user_id, product_type=sku_master[0],\
                                                            max_amt__gte=sku_master[1], min_amt__lte=sku_master[1])\
                                                            .values('sgst_tax', 'cgst_tax', 'igst_tax', 'utgst_tax')[0]
        item = {'discount': sku_master[2],
                'cgst_percent': tax_master['cgst_tax'],
                'sgst_percent': tax_master['sgst_tax'],
                'igst_percent': tax_master['igst_tax'],
                'utgst_percent': tax_master['utgst_tax'],
                'issue_type':order.order_code }
        sku_stocks = StockDetail.objects.filter(sku__user = user_id,\
                                                quantity__gt=0)
        sku_id_stocks = sku_stocks.values('id', 'sku_id')\
                                  .annotate(total = Sum('quantity'))
        pick_res_locat = PicklistLocation.objects\
                                         .prefetch_related('picklist', 'stock')\
                                         .filter(status = 1)\
                                         .filter(picklist__order__user = user_id)\
                                         .values('stock__sku_id')\
                                         .annotate(total = Sum('reserved'))
        invoice_number = order.order_id
        stock_detail = StockDetail.objects.exclude(location__zone__zone = 'DAMAGED_ZONE')\
                                          .filter(sku__wms_code=order.sku.wms_code, sku__user=user_id)
        stock_quantity = stock_detail.aggregate(Sum('quantity'))['quantity__sum']
        picklist_creation(request, stock_detail, stock_quantity, order,\
                          picklist_number, stock_diff, item, user, invoice_number)
  return HttpResponse("Delivered Successfully !")
