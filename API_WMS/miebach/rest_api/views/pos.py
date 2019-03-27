import os
import subprocess
import sys
from decimal import Decimal

from mail_server import send_mail, send_mail_attachment
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
from outbound import send_mail_ordered_report, check_and_send_mail, create_intransit_order, delete_intransit_orders, check_req_min_order_val
from send_message import send_sms

# Create your views here.
log = init_logger('logs/pos.log')


@login_required
@csrf_exempt
def validate_sales_person(request):
    response_data = {'status': 'Fail'}
    user_id = request.GET.get('user_id')
    user_name = request.GET.get('user_name')
    if user_id and user_name:
        data = SalesPersons.objects.filter(user_id=user_id)
        VAT = '14.5'
        response_data['status'] = 'Success'
        response_data['VAT'] = VAT
        response_data['user_name'] = data[0].user_name
        response_data['sales_person_id'] = data[0].id
        response_data['user_id'] = user_id
    return HttpResponse(json.dumps(response_data))


@login_required
@csrf_exempt
@get_admin_user
def get_pos_user_data(request, user=''):
    user_id = user.id
    status = subprocess.check_output(['pgrep -lf sku_master_file_creator'], \
                                     stderr=subprocess.STDOUT, shell=True)
    if "python" not in status:
        sku_query = "%s %s/%s %s&" % ("python", settings.BASE_DIR, \
                                      "sku_master_file_creator.py", str(user.id))
        subprocess.call(sku_query, shell=True)
    else:
        log.info("\nAlready running sku master creation script\n")
    customer_query = "%s %s/%s %s&" % ("python", settings.BASE_DIR, \
                                       "customer_master_file_creator.py", str(user.id))
    subprocess.call(customer_query, shell=True)

    response_data = {}
    user = UserProfile.objects.filter(user__id=user_id)
    if user:
        user = user[0]
        vat = '14.5'
        response_data['status'] = 'Success'
        response_data['VAT'] = vat
        response_data['parent_id'] = user.user.id
        response_data['user_id'] = request.user.id
        response_data['company'] = user.company_name
        response_data['address'] = user.address
        response_data['phone'] = user.phone_number
        response_data['gstin'] = user.gst_number
        return HttpResponse(json.dumps(response_data))
    return HttpResponse("fail")


@login_required
@csrf_exempt
@get_admin_user
def get_current_order_id(request, user=''):
    order_id = get_order_id(user.id, is_pos=True)
    return HttpResponse(json.dumps({'order_id': order_id}))


@login_required
@get_admin_user
def search_pos_customer_data(request, user=''):
    search_key = request.GET['key']
    total_data = []
    if len(search_key) < 3:
        return HttpResponse(json.dumps(total_data))
    lis = ['name', 'email_id', 'phone_number', 'address', 'status']
    master_data = CustomerMaster.objects.filter(Q(phone_number__icontains=search_key) | \
                                                Q(name__icontains=search_key), user=user.id)
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
@get_admin_user
def search_product_data(request, user=''):
    search_key = request.GET['key']
    style_switch = True if request.GET['style_search']=='true' else False
    total_data = []
    if style_switch:
        sku_obj = SKUMaster.objects.exclude(sku_type='RM').filter(Q(wms_code__icontains=search_key) |
                                                                  Q(sku_desc__icontains=search_key) |
                                                                  Q(style_name__icontains=search_key),
                                                                  status = 1,user=user.id)
        style = sku_obj[0].style_name if sku_obj else ''
        master_data = SKUMaster.objects.exclude(sku_type='RM').filter(style_name=style, user=user.id)\
                      if style else []
    else:
        try:
            master_data = SKUMaster.objects.exclude(sku_type='RM').filter(Q(wms_code__icontains=search_key) |
                                                                          Q(sku_desc__icontains=search_key) |
                                                                          Q(ean_number=int(search_key)) |
                                                                          Q(eannumbers__ean_number=int(search_key)),
                                                                          status = 1, user=user.id)
        except:
            master_data = SKUMaster.objects.exclude(sku_type='RM').filter(Q(wms_code__icontains=search_key) |
                                                                      Q(sku_desc__icontains=search_key),status = 1,user=user.id)
    filt_master_ids = list(master_data.values_list('id', flat=True)[:30])
    stock_dict = dict(StockDetail.objects.exclude(location__zone__zone='DAMAGED_ZONE') \
        .filter(sku__user=user.id, quantity__gt=0, sku_id__in=filt_master_ids).values_list('sku_id').distinct().\
                      annotate(total=Sum('quantity')))
    pick_reserved = dict(PicklistLocation.objects.filter(stock__sku__user=user.id, status=1,
                                                          stock__sku_id__in=filt_master_ids).\
                                           only('stock__sku_id', 'reserved').\
                                    values_list('stock__sku_id').distinct().annotate(in_reserved=Sum('reserved')))
    rm_reserved = dict(RMLocation.objects.filter(stock__sku__user=user.id, status=1,
                                                stock__sku_id__in=filt_master_ids).\
                                           only('stock__sku_id', 'reserved').\
                                    values_list('stock__sku_id').distinct().annotate(in_reserved=Sum('reserved')))
    for data in master_data[:30]:
        status = 'Inactive'
        if data.status:
            status = 'Active'
        zone = ''
        if data.zone_id:
            zone = data.zone.zone
        price = data.price
        tax_master = TaxMaster.objects.filter(user=user, \
                                              product_type=data.product_type, max_amt__gte=data.price, \
                                              min_amt__lte=data.price)
        sgst, cgst, igst, utgst = [0] * 4
        if tax_master:
            sgst = tax_master[0].sgst_tax
            cgst = tax_master[0].cgst_tax
            igst = tax_master[0].igst_tax
            utgst = tax_master[0].utgst_tax

        discount_percentage = 0#data.discount_percentage
        discount_price = price
        if not data.discount_percentage:
            category = CategoryDiscount.objects.filter(category=data.sku_category, \
                                                       user_id=user.id)
            if category:
                category = category[0]
                if category.discount:
                    discount_percentage = category.discount
        if discount_percentage:
            discount_price = price - ((price * discount_percentage) / 100)
        '''stock_quantity = StockDetail.objects.exclude(location__zone__zone='DAMAGED_ZONE') \
            .filter(sku__wms_code=data.wms_code, \
                    sku__user=user.id).aggregate(Sum('quantity'))
        stock_quantity = stock_quantity['quantity__sum']
        if not stock_quantity:
            stock_quantity = 0'''
        stock_quantity = stock_dict.get(data.id, 0)
        stock_quantity -= pick_reserved.get(data.id, 0)
        stock_quantity -= rm_reserved.get(data.id, 0)
        ean_numbers = get_sku_ean_list(data)
        ean_numbers = ','.join(ean_numbers)
        total_data.append({'search': str(data.wms_code) + " " + data.sku_desc + " " +\
                                     str(ean_numbers) + " " + str(data.style_name),
                           'SKUCode': data.wms_code,
                           'style_name': data.style_name,
                           'sku_size' : data.sku_size,
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
    customer_master = CustomerMaster.objects.filter(user=user) \
        .values_list('customer_id', flat=True) \
        .order_by('-customer_id')
    if customer_master:
        customer_id = customer_master[0] + 1
    for customer in new_customers:
        CustomerMaster.objects.create(name=customer['firstName'], \
                                      last_name=customer['secondName'], \
                                      email_id=customer['mail'], \
                                      phone_number=customer['number'], \
                                      user=customer['user'], customer_id=customer_id)
        customer_id += 1
    # update master customer txt file
    customer_query = "%s %s/%s %s&" % ("python", settings.BASE_DIR, \
                                       "customer_master_file_creator.py", str(user))
    subprocess.call(customer_query, shell=True)
    return HttpResponse("success")


def get_stock_count(request, order, stock, stock_diff, user, order_quantity, stock_qty):
    stock_quantity = stock_qty
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


def picklist_creation(request, stock_detail, stock_quantity, order_detail, \
                      picklist_number, stock_diff, item, user, invoice_number,\
                      picks_all=[], picklists_send_mail={}):
    auto_skus = []
    # seller_order_summary object creation
    seller_order_summary = SellerOrderSummary.objects.create(pick_number=1, \
                                                             seller_order=None, \
                                                             order=order_detail, \
                                                             picklist=None, \
                                                             quantity=order_detail.quantity, \
                                                             invoice_number=invoice_number)
    needed_order_quantity = float(order_detail.quantity)
    pick_reserved = dict(PicklistLocation.objects.prefetch_related('picklist', 'stock'). \
            filter(picklist__order__user=order_detail.user, picklist__stock__sku_id=order_detail.sku_id).\
            values_list('stock_id').distinct().annotate(total=Sum('reserved')))
    raw_reserved = dict(RMLocation.objects.filter(status=1, stock__sku_id=order_detail.sku_id,
                                                material_picklist__jo_material__material_code__user=order_detail.user).\
                                             values_list('stock_id').distinct().annotate(total=Sum('reserved')))
    stock_diff = 0
    for stock in stock_detail:
        stock_qty = stock.quantity
        stock_qty -= pick_reserved.get(stock.id, 0)
        stock_qty -= raw_reserved.get(stock.id, 0)
        stock_count, stock_diff = get_stock_count(request, order_detail, stock, \
                                                  stock_diff, user, order_detail.quantity, stock_qty)
        auto_skus.append(order_detail.sku.wms_code)
        if not stock_count:
            continue
        stock.quantity = float(stock.quantity) - stock_count
        stock.quantity = get_decimal_limit(user.id, float(stock.quantity))
        stock.save()
        picklist = Picklist.objects.create(picklist_number=picklist_number, \
                                           reserved_quantity=0, \
                                           picked_quantity=stock_count, \
                                           remarks='Picklist_' + str(picklist_number), \
                                           status='batch_picked', \
                                           order_id=order_detail.id, \
                                           stock_id=stock.id, creation_date=NOW)
        PicklistLocation.objects.create(quantity=stock_count, status=0, \
                                        picklist_id=picklist.id, reserved=0, \
                                        stock_id=stock.id, \
                                        creation_date=NOW)
        needed_order_quantity -= stock_count
        picks_all.append(picklist.id)
        quantity = picklist.picked_quantity
        if picklist.order.order_id in picklists_send_mail.keys():
            if picklist.order.sku.sku_code in picklists_send_mail[picklist.order.order_id].keys():
                qty = float(picklists_send_mail[picklist.order.order_id][picklist.order.sku.sku_code])
                picklists_send_mail[picklist.order.order_id][picklist.order.sku.sku_code] = qty +\
                      float(quantity)
            else:
                picklists_send_mail[picklist.order.order_id].update(
                    {picklist.order.sku.sku_code: float(quantity)})
        else:
            picklists_send_mail.update(
                {picklist.order.order_id: {picklist.order.sku.sku_code: float(quantity)}})
        if not stock_diff:
            break
    if needed_order_quantity > 0:
        picklist = Picklist.objects.create(picklist_number=picklist_number, \
                                           reserved_quantity=0, \
                                           picked_quantity=needed_order_quantity, \
                                           remarks='Picklist_' + str(picklist_number), \
                                           status='batch_picked', \
                                           order_id=order_detail.id, \
                                           stock=None, creation_date=NOW)
        needed_order_quantity = 0
        picks_all.append(picklist.id)
        quantity = picklist.picked_quantity
        if picklist.order.order_id in picklists_send_mail.keys():
            if picklist.order.sku.sku_code in picklists_send_mail[picklist.order.order_id].keys():
                qty = float(picklists_send_mail[picklist.order.order_id][picklist.order.sku.sku_code])
                picklists_send_mail[picklist.order.order_id][picklist.order.sku.sku_code] = qty +\
                      float(quantity)
            else:
                picklists_send_mail[picklist.order.order_id].update(
                    {picklist.order.sku.sku_code: float(quantity)})
        else:
            picklists_send_mail.update(
                {picklist.order.order_id: {picklist.order.sku.sku_code: float(quantity)}})

    obj, created = CustomerOrderSummary.objects.get_or_create(order_id=order_detail.id)
    if created:
        obj.discount = item['discount']
        obj.issue_type = order_detail.order_code
        obj.cgst_tax = item['cgst_percent']
        obj.sgst_tax = item['sgst_percent']
        obj.creation_date = NOW
        obj.save()
    #auto po
    if auto_skus:
        auto_skus = list(set(auto_skus))
    price_band_flag = get_misc_value('priceband_sync', user.id)
    if price_band_flag == 'true':
        reaches_order_val, sku_qty_map = check_req_min_order_val(user, auto_skus)
        if reaches_order_val:
            auto_po(auto_skus, user.id)
            delete_intransit_orders(auto_skus, user)  # deleting intransit order after creating actual order
        else:
            create_intransit_order(auto_skus, user, sku_qty_map)
    else:
        auto_po(auto_skus, user.id)

    if order_detail.order_code == "PRE%s" %(request.user.id):
        return picks_all, picklists_send_mail
    return "Success"


@login_required
@csrf_exempt
def customer_order(request):
    orders = request.POST['order']
    null = None
    log.info("Create orders request: %s\n" %(str(orders)))
    orders = eval(orders)
    order_ids = []
    only_return = True
    order_codes = {"Delivery Challan": "DC",
                   "Pre Order": "PRE"}
    if isinstance(orders, dict): orders = [orders]
    for order in orders:
        order_created = False
        items_to_mail = []
        for typ, pay in order['summary'].get('payment', {}).iteritems():
            if not pay:
                order['summary']['payment'][typ] = 0
        total_payment_received = sum(order['summary'].get('payment', {}).values())
        user_id = order['user']['parent_id']
        user = User.objects.get(id=user_id)
        if not order['customer_data'] and order['summary']['issue_type'] == "Pre Order":
            return HttpResponse(json.dumps({'message': 'Missing Customer Data'}))
        cust_dict = order['customer_data']
        number = order['customer_data']['Number']
        customer_data = CustomerMaster.objects.filter(phone_number=number, \
                                                      user=user_id) if number else []
        frontend_order_id = order['summary']['order_id']
        if order['summary']['nw_status'] == 'online':
            backend_order_id = get_order_id(user_id, is_pos=True)
            order_id = backend_order_id if (backend_order_id > frontend_order_id) else frontend_order_id
        else:
            order_id = frontend_order_id
        log.info("Latest Order ID : %s\n" %(str(order_id)))
        status = 0 if order['summary']['issue_type'] == "Delivery Challan" \
            else 1
        order_code = order_codes[order['summary']['issue_type']] + str(request.user.id)
        original_order_id = order_code + str(order_id)
        order_ids.append(order_id)

        picklist_number = get_picklist_number(user) + 1
        if customer_data:
            customer_id = customer_data[0].id
            customer_name = customer_data[0].name
        else:
            customer_id = 0
            customer_name = cust_dict.get('FirstName', '')
        customer_order = []

        sku_stocks = StockDetail.objects.filter(sku__user=user_id, quantity__gt=0)
        sku_id_stocks = sku_stocks.values('id', 'sku_id').annotate(total=Sum('quantity'))
        pick_res_locat = PicklistLocation.objects.prefetch_related('picklist', 'stock') \
            .filter(status=1) \
            .filter(picklist__order__user=user_id) \
            .values('stock__sku_id') \
            .annotate(total=Sum('reserved'))
        """val_dict = {}
        val_dict['pic_res_ids'] = map(lambda d: d['stock__sku_id'], pick_res_locat)
        val_dict['pic_res_quans'] = map(lambda d: d['total'], pick_res_locat)
        val_dict['sku_ids'] = map(lambda d: d['sku_id'], sku_id_stocks)
        val_dict['stock_ids'] = map(lambda d: d['id'], sku_id_stocks)
        val_dict['stock_totals'] = map(lambda d: d['total'], sku_id_stocks)"""
        if (customer_name and order['summary']['issue_type'] == "Pre Order") or \
                        order['summary']['issue_type'] == "Delivery Challan":
            #tot_sku_level_discount = 0
            #for item in order['sku_data']:
                #if item['return_status'] == "false":
                    #tot_sku_level_discount += ((int(item['selling_price']) - item['unit_price']) * item['quantity'])
            tot_order_level_discount = order['summary']['total_discount']
            order_level_disc_per_sku = tot_order_level_discount / float(len(order['sku_data']))

            for item in order['sku_data']:

                sku = SKUMaster.objects.get(wms_code=item['sku_code'], \
                                            user=user_id)
                # if not returning item
                if item['return_status'] == "false":
                    only_return = False
                    payment_received = 0
                    if item['price'] < total_payment_received :
                        payment_received = item['price']
                        total_payment_received -= item['price']
                    else:
                        payment_received = total_payment_received
                        total_payment_received = 0
                    try:
                        order_detail = OrderDetail.objects.create(user=user_id, \
                                                                  marketplace="Offline", \
                                                                  order_id=order_id, \
                                                                  sku_id=sku.id, \
                                                                  customer_id=customer_id, \
                                                                  customer_name=customer_name, \
                                                                  telephone=number, \
                                                                  title=sku.sku_desc, \
                                                                  quantity=item['quantity'], \
                                                                  invoice_amount=item['price'], \
                                                                  order_code=order_code, \
                                                                  shipment_date=NOW, \
                                                                  original_order_id=original_order_id, \
                                                                  nw_status=order['summary']['nw_status'], \
                                                                  status=status, \
                                                                  email_id=cust_dict.get('Email', ''), \
                                                                  unit_price=item['unit_price'],
                                                                  payment_received=payment_received)
                        log.info("Order %s created" %(order_detail.original_order_id))
                    except Exception as exece:
                        import traceback
                        log.debug(traceback.format_exc())
                        check_picklist_number_created(user, picklist_number)
                        if "Duplicate entry" in exece[1]:
                            order_detail = OrderDetail.objects.get(user=user_id, \
                                                                   order_id=order_id, \
                                                                   sku_id=sku.id, \
                                                                   order_code=order_code)
                            log.info("Duplicate order: id=%s, qty=%s, invoice_amt=%s, paymnt_received=%s"\
                                    %(str(order_detail.original_order_id), str(order_detail.quantity),\
                                    str(order_detail.invoice_amount), str(order_detail.payment_received)))
                            new_sku_count = float(order_detail.quantity) + item['quantity']
                            new_invoice_amount = order_detail.invoice_amount + item['price']
                            new_payment_received = order_detail.payment_received + payment_received
                            #order_detail.quantity = new_sku_count
                            #order_detail.invoice_amount = new_invoice_amount
                            #order_detail.payment_received = new_payment_received
                            #order_detail.save()
                            log.info("duplicate order didnt save, data is : id=%s, qty=%s, amt=%s,\
                                     payment_receieved=%s" %(str(order_detail.original_order_id),\
                                     str(item['quantity']), str(item['price']),\
                                     str(payment_received)))
                            continue
                    sku_disc = (int(item['selling_price']) - item['unit_price']) * item['quantity']
                    CustomerOrderSummary.objects.create(order_id=order_detail.id, \
                                                        discount=order_level_disc_per_sku, \
                                                        issue_type=order['summary']['issue_type'], \
                                                        cgst_tax=item['cgst_percent'], \
                                                        sgst_tax=item['sgst_percent'], \
                                                        order_taken_by=order['summary']['staff_member'], \
                                                        creation_date=NOW)
                    order_created = True
                    items_to_mail.append([sku.sku_desc, item['quantity'], item['price']])
                    if status == 0:
                        stock_diff, invoice_number = item['quantity'], order_id
                        stock_detail = sku_stocks.exclude( \
                            location__zone__zone='DAMAGED_ZONE') \
                            .filter(sku__wms_code=sku.wms_code, \
                                    sku__user=user_id)
                        stock_quantity = stock_detail.aggregate(Sum('quantity'))['quantity__sum']
                        picklist_creation(request, stock_detail, \
                                          stock_quantity, order_detail, \
                                          picklist_number, stock_diff, \
                                          item, user, invoice_number)
                # return item : increase stock
                else:
                    sku_stocks_ = StockDetail.objects.filter(sku__user=user_id, \
                                                             sku_id=sku.id)
                    if sku_stocks_:
                        sku_stocks_ = sku_stocks_[0]
                    else:
                        recpt_no = StockDetail.objects.filter(sku__user=user_id) \
                                       .aggregate(Max('receipt_number')) \
                                       .get('receipt_number__max', 0)
                        recpt_no = recpt_no + 1 if recpt_no else 0
                        put_zone = ZoneMaster.objects.filter(zone='DEFAULT', \
                                                             user=user_id)
                        if not put_zone:
                            create_default_zones(user, 'DEFAULT', 'DEFAULT', 10001)
                            put_zone = ZoneMaster.objects.filter(zone='DEFAULT', user=user.id)[0]
                        else:
                            put_zone = put_zone[0]
                        sku_stocks_ = StockDetail.objects.create( \
                            receipt_number=recpt_no, \
                            sku_id=sku.id, \
                            receipt_date=NOW, \
                            creation_date=NOW, \
                            location=put_zone.locationmaster_set.all()[0])
                    sku_stocks_.quantity = float(sku_stocks_.quantity) + item['quantity']
                    sku_stocks_.save()
                    log.info("return item, stock increased: sku_id=%s, user=%s, qty=%s, new_stock=%s"\
                            %(str(sku.id), str(user_id), str(item['quantity']), str(sku_stocks_.quantity)))
                    #order_id = "return"
                    # add item to OrderReturns
                    order_return = OrderReturns.objects.create( \
                        order=None, \
                        seller_order=None, \
                        quantity=item['quantity'], \
                        damaged_quantity=0, \
                        sku=sku, reason='', \
                        status=0)
                    order_return.return_id = "MN" + str(order_return.id)
                    order_return.save()
                    log.info("OrderReturns object created with id: %s" %(str(order_return.id)))
                    return_location = ReturnsLocation.objects.create( \
                        quantity=0, \
                        status=0, \
                        location=sku_stocks_.location, \
                        returns=order_return)
            if order_created:

                #send mail and sms for pre order
                if order["summary"]["issue_type"] == "Pre Order" and customer_data:
                    email_id, phone_number = customer_data[0].email_id, customer_data[0].phone_number
                    if email_id or phone_number:
                        other_charge_amounts = 0
                        order_detail.order_id = order_detail.original_order_id
                        order_data = {
                                      "customer_name": customer_data[0].name,
                                      "address": customer_data[0].address,
                                      "telephone": phone_number,
                                      "email_id": email_id
                                     }
                        send_mail_ordered_report(order_detail, phone_number, items_to_mail,\
                                                 other_charge_amounts, order_data, user)
                # store extra details
                for field, val in order["summary"].get("payment", {}).iteritems():
                    OrderFields.objects.create(original_order_id=original_order_id, name="payment_" + field, value=val,
                                               user=user.id)
                    reference_number = order.get('reference_number' ,'')
                    if field != 'Cash':
                        OrderFields.objects.create(original_order_id=order_detail.original_order_id, \
                                               name='reference_number', value=reference_number, user=user.id)
                for field, val in order["customer_data"].get("extra_fields", {}).iteritems():
                    OrderFields.objects.create(original_order_id=order_detail.original_order_id, \
                                               name=field, value=val, user=user.id)



    if only_return: order_ids = ['return']
    return HttpResponse(json.dumps({'order_ids': order_ids}))


def prepare_delivery_challan_json(request, order_id, user_id, parent_user=''):
    json_data = {}
    customer_data, summary, gst_based = {}, {}, {}
    sku_data = []
    total_quantity, total_amount, subtotal, total_discount, tot_cgst, tot_sgst = [0] * 6
    status = 'fail'
    order_date = NOW
    user = User.objects.get(id=user_id)
    order_date = get_local_date(user, NOW)
    #check where discount is saved
    order_detail = OrderDetail.objects.filter(original_order_id__icontains=order_id, \
                                              user=user_id, quantity__gt=0)
    payment_type = ''
    reference_number = ''
    if  'DC'  in order_detail[0].order_code or 'PRE' in order_detail[0].order_code:
        payment_obj = OrderFields.objects.filter(original_order_id=order_id, \
                               name__contains='payment', user=user_id)
        if payment_obj.exists():
            payment_obj = payment_obj[0]
            payment_type = payment_obj.name.replace("payment_","")
        reference_obj = OrderFields.objects.filter(original_order_id=order_id, \
                               name='reference_number', user=user_id)
        if reference_obj.exists():
            reference_obj = reference_obj[0]
            reference_number = reference_obj.value

    if parent_user:
        order_detail = OrderDetail.objects.filter(original_order_id__icontains=order_id, \
                                              user=parent_user.id, quantity__gt=0)

    for order in order_detail:
        discount = 0
        sku = SKUMaster.objects.get(id=order.sku_id)
        discount_percentage = 0#sku.discount_percentage
        if not sku.discount_percentage:
            category = CategoryDiscount.objects.filter(category=sku.sku_category, \
                                                       user_id=user.id)
            if category:
                category = category[0]
                if category.discount:
                    discount_percentage = 0#category.discount
        #original_selling_price = sku.price
        original_selling_price = (order.unit_price * 100)/(100 - discount_percentage)
        #discount = original_selling_price - order.unit_price
        selling_price = float(order.invoice_amount) / float(order.quantity)
        order_summary = CustomerOrderSummary.objects.filter(order_id=order.id)
        if order_summary:
            #total_discount  += (order_summary[0].discount * order.quantity)
            total_discount += order_summary[0].discount
            tax_master = order_summary.values('sgst_tax', 'cgst_tax', 'igst_tax', 'utgst_tax')[0]
        else:
            tax_master = {'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0, 'utgst_tax': 0}
        item_sgst = (order.invoice_amount/float(order.quantity)) * tax_master['sgst_tax']/100
        item_cgst = (order.invoice_amount/float(order.quantity)) * tax_master['cgst_tax']/100
        selling_price -= (item_cgst + item_sgst)
        gst_based.setdefault(tax_master['cgst_tax'], {'taxable_amt': 0,
                                                      'cgst_percent': tax_master["cgst_tax"],
                                                      'sgst_percent': tax_master["sgst_tax"],
                                                      'sgst': 0,
                                                      'cgst': 0})
        gst_based[tax_master['cgst_tax']]['taxable_amt'] += order.invoice_amount - \
                                  order_summary[0].discount -\
                                  (float(order.invoice_amount) * tax_master["sgst_tax"] / 100) - \
                                  (float(order.invoice_amount) * tax_master["cgst_tax"] / 100)
        gst_based[tax_master['cgst_tax']]['sgst'] += order.invoice_amount * tax_master["sgst_tax"] / 100
        gst_based[tax_master['cgst_tax']]['cgst'] += order.invoice_amount * tax_master["cgst_tax"] / 100

        sku_data.append({'name': order.title,
                         'quantity': float(order.quantity),
                         'sku_code': order.sku.sku_code,
                         'price': order.invoice_amount,
                         'unit_price': selling_price,
                         'selling_price': original_selling_price,
                         'discount': discount_percentage,
                         'sgst': item_sgst,
                         'cgst': item_cgst
                         })
        total_quantity += float(order.quantity)
        #total_amount += (float(order.invoice_amount) + discount + \
        #                 (float(order.invoice_amount) * tax_master["sgst_tax"] / 100) + \
        #                 (float(order.invoice_amount) * tax_master["cgst_tax"] / 100) );
        if order_summary[0].issue_type == "Delivery Challan":
            sgst_temp = float(order.invoice_amount) * tax_master["sgst_tax"] / 100;
            cgst_temp = float(order.invoice_amount) * tax_master["cgst_tax"] / 100;
            total_amount += (float(order.invoice_amount) - sgst_temp - cgst_temp)
        else:
            total_amount += (float(order.invoice_amount))
    if order_detail:
        status = 'success'
        order = order_detail[0]
        customer_id = ''
        order_date = get_local_date(user, order.creation_date)
        extra_field_obj = list(OrderFields.objects.filter(original_order_id = order.original_order_id, user = user_id)\
                                  .exclude(name__icontains = "payment_").values_list('name', 'value'))
        extra_fields = {}
        [extra_fields.update({a[0]:a[1]}) for a in extra_field_obj]
        if order.customer_id:
            customer_master = CustomerMaster.objects.filter(id=order.customer_id, \
                                                            name=order.customer_name, \
                                                            user=user_id)
            if customer_master:
                customer_id = customer_master[0].id
        customer_data = {'FirstName': order.customer_name,
                         'LastName': '',
                         'Number': order.telephone,
                         'ID': customer_id,
                         'Address': order.address,
                         'Email': order.email_id}
        order_summary = CustomerOrderSummary.objects.filter(order_id=order.id)
        if order_summary:
            order_summary = order_summary[0]
            for item in gst_based:
                tot_sgst += gst_based[item]['sgst']
                tot_cgst += gst_based[item]['cgst']
            summary = {'total_quantity': total_quantity,
                       'total_amount': total_amount,
                       'total_discount': total_discount,
                       'subtotal': total_amount,
                       'cgst': tot_cgst,
                       'sgst': tot_sgst,
                       'gst_based': gst_based,
                       'staff_member': order_summary.order_taken_by,
                       'issue_type': order_summary.issue_type}
            json_data = {'data':{'customer_data': customer_data, 'summary': summary,
                                 'sku_data': sku_data, 'order_id': order_id,
                                 'order_date': order_date,
                                 'payment_mode':payment_type,
                                 'reference_number':reference_number,
                                 'customer_extra': extra_fields},
                        'status': status
                        }
    return json_data


@login_required
@csrf_exempt
@get_admin_user
def print_order_data(request, user=''):
    user_id = user.id
    order_id = request.GET['order_id']
    json_data = prepare_delivery_challan_json(request, order_id, user_id)
    return HttpResponse(json.dumps(json_data))


def get_order_details(order_id, user_id, mobile, customer_name, request_from, sub_user=''):
    customer_data, order_data = {}, {}
    summary, sku_data = [], []
    total_quantity, total_amount, subtotal = [0] * 3
    to_zone = tz.gettz('Asia/Kolkata')
    # if return, get orders of all order code with status 0
    if request_from == "return" or request_from == "initial_preorder":
        status = 0 if request_from == "return" else 1
        min_order_date = datetime.datetime.now() - datetime.timedelta(days=20)
        order_detail = OrderDetail.objects.filter(user=user_id, \
                                                  quantity__gt=0, status=status, \
                                                  creation_date__gte=min_order_date)
        if status == 1:
            order_detail = order_detail.filter(order_code='PRE' + str(sub_user.id))
        if order_id:
            order_detail = order_detail.filter(order_id=order_id)
        else:
            if mobile:
                order_detail = order_detail.filter(telephone=mobile)
            if customer_name:
                order_detail = order_detail.filter(customer_name__icontains=customer_name)
    elif request_from == "preorder":
        order_detail = OrderDetail.objects.filter(user=user_id, quantity__gt=0, \
                                                  order_code='PRE' + str(sub_user.id))
    else:
        order_detail = OrderDetail.objects.filter(user=user_id, \
                                                  status=1, order_code='PRE' + str(sub_user.id))
    if order_id: order_detail = order_detail.filter(order_id=order_id)
    for order in order_detail:
        selling_price = order.unit_price if order.unit_price != 0 \
            else float(order.invoice_amount) / float(order.quantity)
        order_id = str(order.order_id)
        order_data.setdefault(order_id, {})
        order_data[order_id]['order_id'] = order_id
        order_data[order_id]['original_order_id'] = order.original_order_id
        order_data[order_id]['order_date'] = order.creation_date \
            .astimezone(to_zone) \
            .strftime("%d %b %Y %I:%M %p")
        order_data[order_id]['status'] = order.status
        order_data[order_id].setdefault('sku_data', []).append({'name': order.title,
                                                                'quantity': order.quantity,
                                                                'sku_code': order.sku.sku_code,
                                                                'price': order.invoice_amount,
                                                                'selling_price': selling_price,
                                                                'order_id': order_id,
                                                                'id': order.id})
        total_quantity += float(order.quantity)
        total_amount += float(order.invoice_amount)
        status = order.status

        order_data[order_id]['customer_data'] = {'Name': order.customer_name,
                                                 'Number': order.telephone,
                                                 'Address': order.address,
                                                 'Email': order.email_id}
    return json.dumps({'data': order_data})


@get_admin_user
@login_required
def pre_order_data(request, user=''):
    data = eval(request.POST['data'])
    order_id = data.get('order_id', '')
    mobile = data.get('mobile', '')
    customer_name = data.get('customer_name', '')
    request_from = data.get('request_from', '')
    order_details = get_order_details(order_id, user.id, mobile, \
                                      customer_name, request_from, request.user)
    return HttpResponse(order_details)


@login_required
@get_admin_user
def update_order_status(request, user=''):
    parent_user = user
    full_data = eval(request.POST['data'])
    nw_status = "offline"
    if isinstance(full_data, dict):
        full_data = [full_data]
        nw_status = "online"
    for data in full_data:
        order_detail = OrderDetail.objects.filter(order_id=data['order_id'], \
                                                  user=parent_user.id,
                                                  #user=data['user'], \
                                                  quantity__gt=0, \
                                                  order_code='PRE' + str(request.user.id))
        if data['delete_order'] == "true":
            order_detail.delete()
            if nw_status == "online":
                return HttpResponse(json.dumps({"message": "Deleted Successfully !", "data": {}}))
            else:
                continue
        picks_all = []
        picklists_send_mail = {}
        for order in order_detail:
            order.status = 0
            order.payment_received = order.invoice_amount
            sku = order.sku
            user_id = order.user
            user = User.objects.get(id=user_id)
            picklist_number = get_picklist_number(user) + 1
            stock_detail = StockDetail.objects.filter(sku=sku, quantity__gt=0)
            if stock_detail:
                order.save()
            else:
                if nw_status == "online": return HttpResponse(json.dumps({"message": "Error", "data": {}}))
                order.save()
                continue
            stock_diff = StockDetail.objects.filter(sku=sku) \
                .exclude(location__zone__zone='DAMAGED_ZONE') \
                .values_list('sku__wms_code').distinct() \
                .annotate(total=Sum('quantity'))[0][1]
            sku_master = SKUMaster.objects.filter(user=user_id, id=order.sku.id) \
                .values_list('product_type', \
                             'price', 'discount_percentage')[0]

            tax_master = {'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0, 'utgst_tax': 0} if not sku_master[0] else \
            TaxMaster.objects \
                .filter(user=user_id, product_type=sku_master[0], \
                        max_amt__gte=sku_master[1], min_amt__lte=sku_master[1]) \
                .values('sgst_tax', 'cgst_tax', 'igst_tax', 'utgst_tax')[0]
            item = {'discount': sku_master[2],
                    'cgst_percent': tax_master['cgst_tax'],
                    'sgst_percent': tax_master['sgst_tax'],
                    'igst_percent': tax_master['igst_tax'],
                    'utgst_percent': tax_master['utgst_tax'],
                    'issue_type': order.order_code}
            sku_stocks = StockDetail.objects.filter(sku__user=user_id, \
                                                    quantity__gt=0)
            sku_id_stocks = sku_stocks.values('id', 'sku_id') \
                .annotate(total=Sum('quantity'))
            pick_res_locat = PicklistLocation.objects \
                .prefetch_related('picklist', 'stock') \
                .filter(status=1) \
                .filter(picklist__order__user=user_id) \
                .values('stock__sku_id') \
                .annotate(total=Sum('reserved'))
            invoice_number = order.order_id
            stock_detail = StockDetail.objects.exclude(location__zone__zone='DAMAGED_ZONE') \
                .filter(sku__wms_code=order.sku.wms_code, sku__user=user_id)
            stock_quantity = stock_detail.aggregate(Sum('quantity'))['quantity__sum']
            picks_all, picklists_send_mail = picklist_creation(request, stock_detail,\
                              stock_quantity, order, picklist_number, stock_diff,\
                              item, user, invoice_number, picks_all, picklists_send_mail)
            from_pos = True
    all_picks = Picklist.objects.filter(id__in=picks_all)
    check_and_send_mail(request, user, all_picks[0], all_picks, picklists_send_mail, from_pos)
    json_data = prepare_delivery_challan_json(request, full_data[0]['order_id'], request.user.id, parent_user=parent_user)
    return HttpResponse(json.dumps({"message": "Delivered Successfully !", "data": json_data}))


@login_required
@get_admin_user
def get_extra_fields(request, user=''):
    user_id = user.id
    extra_fields = {}
    extra_fields_obj = MiscDetail.objects.filter(user=user_id, misc_type__icontains="pos_extra_fields_")
    for item in extra_fields_obj:
        typ = item.misc_type.replace("pos_extra_fields_", "")
        extra_fields[typ] = item.misc_value.split(",")
    return HttpResponse(json.dumps(extra_fields))


@login_required
@get_admin_user
def get_staff_members_list(request, user=''):
    members = []
    staff_obj = StaffMaster.objects.filter(user=user.id)
    if staff_obj:
        for staff in staff_obj:
            members.append(staff.staff_name)
    return HttpResponse(json.dumps({'members': members}))


@csrf_exempt
@login_required
@get_admin_user
def pos_tax_inclusive(request, user=''):
    data = {}
    tax_inclusive = get_misc_value('tax_inclusive', user.id)
    data['tax_inclusive_switch'] = json.loads(tax_inclusive)
    return HttpResponse(json.dumps(data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def pos_extra_fields(request, user=''):
    input_fld = request.POST.get('Input', '')
    textarea_fld = request.POST.get('Textarea', '')
    try:
        log.info("Insert pos extra fields data user %s and request params are %s" %
                 (str(user.username), str(request.GET.dict())))
        if input_fld:
            exe_data = MiscDetail.objects.filter(user=user.id, misc_type='pos_extra_fields_input')
            if exe_data:
                exe_array = exe_data[0].misc_value.split(',')
                input_array = input_fld.split(',')
                for val in input_array:
                    if not val in exe_array:
                        exe_array.append(val)
                exe_data[0].misc_value = ','.join(exe_array)
                exe_data[0].updation_date = datetime.datetime.now()
                exe_data[0].save()
            if not exe_data:
                MiscDetail.objects.create(user=user.id, misc_type='pos_extra_fields_input', misc_value=input_fld,
                                          creation_date=datetime.datetime.now(), updation_date=datetime.datetime.now())
        if textarea_fld:
            exe_data = MiscDetail.objects.filter(user=user.id, misc_type='pos_extra_fields_textarea')
            if exe_data:
                exe_array = exe_data[0].misc_value.split(',')
                input_array = textarea_fld.split(',')
                for val in input_array:
                    if not val in exe_array:
                        exe_array.append(val)
                exe_data[0].misc_value = ','.join(exe_array)
                exe_data[0].updation_date = datetime.datetime.now()
                exe_data[0].save()
            if not exe_data:
                MiscDetail.objects.create(user=user.id, misc_type='pos_extra_fields_textarea', misc_value=textarea_fld,
                                          creation_date=datetime.datetime.now(), updation_date=datetime.datetime.now())
        status = 'Success'
    except:
        status = 'Fail'
    return HttpResponse(status)

@csrf_exempt
@login_required
@get_admin_user
def pos_send_mail(request , user =''):
    from inbound import write_and_mail_pdf
    # data_dict = json.loads(request.POST)
    for obj in request.POST.iteritems():
        data_dict = json.loads(obj[0])
        data = data_dict['data']
        for item in data['sku_data']:
            rate = item['unit_price'] + item['sgst'] + item['cgst'] + (item['selling_price']*item['discount']/100)
            amount = item['unit_price'] + item['sgst'] + item['cgst'] + (item['selling_price']*item['discount']/100)
            item['rate'] = rate
            item['amount'] = amount
        data['summary_total_amount']  = data['summary']['subtotal'] + data['summary']['sgst']+ data['summary']['igst'] + data['summary']['utgst'] + data['summary']['cgst']
        data['summary_discount'] = data['summary_total_amount'] - data['summary']['total_discount']
        data['summary_total'] = data['summary']['subtotal'] - data['summary']['total_discount']
        data_dict['data']= data
        # user = data_dict['user']
        try:
            t = loader.get_template('templates/toggle/pos_print.html')
            rendered = t.render(data_dict)
            write_and_mail_pdf('posorder', rendered, request, user,
                               data['customer_data']['Email'], data['customer_data']['Number'],"POS ORDER",
                               '',False,False,'posform')
        except Exception as e:
            pass
