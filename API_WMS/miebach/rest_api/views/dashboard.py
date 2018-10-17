from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseRedirect
import json
from django.contrib.auth import authenticate
from django.contrib import auth
from dateutil.relativedelta import relativedelta
from common import *
from miebach_utils import *
from django.db.models import Sum, Count
from miebach_admin.models import *
from miebach_admin.custom_decorators import login_required, get_admin_user, check_customer_user
from django.core import serializers


# Create your views here.

@csrf_exempt
def home(request):
    print request.user
    return HttpResponse(json.dumps({'status': 'Success'}), content_type='application/json')


def get_daily_transactions(data_dict, key_pair, table, user):
    for key, value in key_pair.iteritems():
        results = table.objects.filter(order__user=user, **value[0])
        for result in results:
            data_dict[key] += 1


def get_quantity(data_dict, key_pair, no_date=False, order_level=True):
    for key, value in key_pair.iteritems():
        if no_date and not key in ['executed', 'Picked']:
            date_str = [k for (k, v) in value[1].iteritems() if 'date' in k]
            if date_str:
                del value[1][date_str[0]]
        model_data = value[0].objects.filter()
        if len(value) > 2:
            model_data = model_data.exclude(**value[2])
        if value[0] == OrderDetail:
            if order_level:
                results = model_data.filter(**value[1]).values('order_id').distinct()
            else:
                data_dict[key] = model_data.filter(**value[1]).aggregate(Sum('quantity'))['quantity__sum']
        elif value[0] == PurchaseOrder:
            if order_level:
                results = model_data.filter(**value[1]).values('order_id').distinct()
            else:
                data_dict[key] = model_data.filter(**value[1]).values('order_id'). \
                    aggregate(Sum('open_po__order_quantity'), Sum('received_quantity'))
                if not data_dict[key]['open_po__order_quantity__sum']:
                    data_dict[key]['open_po__order_quantity__sum'] = 0
                if not data_dict[key]['received_quantity__sum']:
                    data_dict[key]['received_quantity__sum'] = 0
                data_dict[key] = data_dict[key]['open_po__order_quantity__sum'] - data_dict[key][
                    'received_quantity__sum']
        elif value[0] == POLocation:
            if order_level:
                results = model_data.filter(**value[1]).values('purchase_order__order_id').distinct()
            else:
                data_dict[key] = model_data.filter(**value[1]).aggregate(Sum('quantity'))['quantity__sum']
        else:
            if order_level:
                results = model_data.filter(**value[1]).values('order__order_id').distinct()
            else:
                if key == 'Picked':
                    data_dict[key] = model_data.filter(**value[1]).aggregate(Sum('picked_quantity'))[
                        'picked_quantity__sum']
                else:
                    data_dict[key] = model_data.filter(**value[1]).aggregate(Sum('reserved_quantity'))[
                        'reserved_quantity__sum']
        if order_level:
            data_dict[key] = results.count()
        else:
            if not data_dict[key]:
                data_dict[key] = 0
            data_dict[key] = round(data_dict[key])


def sales_return_data(user, input_param=''):
    returns_data = OrderReturns.objects.filter(sku__user=user.id, creation_date__year=NOW.year,
                                               creation_date__month=NOW.month).values('sku_id').distinct().annotate(
        total=Count('id'))
    if (input_param):
        returns_data = OrderReturns.objects.values('sku_id').distinct().annotate(total=Count('id')).filter(
            **input_param)
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

    return data_list[:4]


@fn_timer
def get_orders_statistics(user, order_level=True):
    order_stats = OrderedDict()
    NOW = get_local_date(user, datetime.datetime.now(), True)
    all_orders = OrderDetail.objects.filter(user=user.id, creation_date__range=[NOW - relativedelta(months=1), NOW])
    all_picks = Picklist.objects.filter(creation_date__range=[NOW - relativedelta(months=1), NOW], order__user=user.id)
    for i in range(30):
        cur_date = NOW - datetime.timedelta(days=i)
        cur_date = cur_date.date().strftime('%Y-%m-%d')
        order_stats.setdefault(cur_date, {'Received': 0, 'Picked': 0})
        if order_level:
            order_stats[cur_date]['Received'] = all_orders.filter(creation_date__regex=cur_date, user=user.id).values(
                'order_id'). \
                distinct().count()
            order_stats[cur_date]['Picked'] = all_picks.filter(creation_date__regex=cur_date,
                                                               status__icontains='picked'). \
                values('order__order_id').distinct().count()
        else:
            order_stats[cur_date]['Received'] = \
            all_orders.filter(creation_date__regex=cur_date, user=user.id).aggregate(Sum('quantity'))['quantity__sum']
            if not order_stats[cur_date]['Received']:
                order_stats[cur_date]['Received'] = 0
            order_stats[cur_date]['Picked'] = \
            all_picks.filter(creation_date__regex=cur_date, status__in=['picked', 'batch_picked',
                                                                        'dispatched', 'open', 'batch_open']).aggregate(
                Sum('picked_quantity'))['picked_quantity__sum']
            if not order_stats[cur_date]['Picked']:
                order_stats[cur_date]['Picked'] = 0

            order_stats[cur_date]['Received'] = round(order_stats[cur_date]['Received'])
            order_stats[cur_date]['Picked'] = round(order_stats[cur_date]['Picked'])
    return order_stats


@csrf_exempt
@check_customer_user
@login_required
@get_admin_user
def dashboard(request, user=''):
    if not request.user.is_authenticated():
        return HttpResponse("fail")

    dashboard_order_level = request.GET.get('display_order_level', '')
    dashboard_order_level = True if dashboard_order_level == 'true' else False
    user_id = user.id
    datetime_now = get_local_date(user, datetime.datetime.now(), True)
    today_start = datetime.datetime.combine(datetime_now, datetime.time())
    today_end = datetime.datetime.combine(datetime_now + relativedelta(days=1), datetime.time())
    today_range = [today_start, today_end]
    top_skus = OrderDetail.objects.filter(user=user_id,
                                          creation_date__range=[today_start - relativedelta(months=1), today_start]). \
                   values('sku__sku_code').distinct().annotate(Sum('quantity')).order_by('-quantity__sum')[:5]
    top_skus_data = {'data': [], 'labels': [], 'stock_count': []}
    for top in top_skus:
        members = [top['sku__sku_code']]
        combos = SKURelation.objects.filter(parent_sku__sku_code=top['sku__sku_code'], parent_sku__user=user.id,
                                            relation_type='combo'). \
            values_list('member_sku__sku_code', flat=True)
        if combos:
            members = list(combos)
        for member in members:
            stock_count = 0
            if member in top_skus_data['labels']:
                continue
            sku_stock = StockDetail.objects.filter(sku__sku_code=member, sku__user=user_id).values(
                'sku__sku_code').annotate(Sum('quantity'))
            if sku_stock:
                stock_count = sku_stock[0]['quantity__sum']
            top_skus_data['data'].append(top['quantity__sum'])
            top_skus_data['labels'].append(member)
            top_skus_data['stock_count'].append(get_decimal_limit(user_id, stock_count))
            if len(top_skus_data['data']) == 5:
                break
        if len(top_skus_data['data']) == 5:
            break

    filter_params = {'user': user_id}
    locations_count = {"Utilized": [], 'Free': [], 'zones': []}
    zone_list = ZoneMaster.objects.exclude(zone__in=['TEMP_ZONE', 'DEFAULT', 'DAMAGED_ZONE']).filter(**filter_params)
    others = 0
    for zones in zone_list:
        total_stock = 0
        max_capacity = 0
        stock_data = StockDetail.objects.filter(location__zone__zone=zones.zone,
                                                sku__user=user_id).aggregate(Sum('quantity'))
        if not None in stock_data.values():
            total_stock = int(stock_data['quantity__sum'])
        locations = LocationMaster.objects.filter(zone__user=user_id, zone__zone=zones.zone).aggregate(
            Sum('max_capacity'))
        if not None in locations.values():
            max_capacity = int(locations['max_capacity__sum'])
        if others == 3:
            locations_count["Utilized"].append(0)
            locations_count["Free"].append(0)
            locations_count["zones"].append('others')
        if (others < 3):
            locations_count["Utilized"].append(total_stock)
            locations_count["Free"].append(max_capacity - total_stock)
            locations_count["zones"].append(zones.zone)
            others = others + 1
        else:
            locations_count['Utilized'][3] = total_stock
            locations_count["Free"][3] += (max_capacity - total_stock)
            others = others + 1

    top_inventory = list(
        StockDetail.objects.filter(sku__user=user.id).values('sku__wms_code').annotate(Sum('quantity')). \
        order_by('-quantity__sum')[:10])

    pie_putaway = {'executed': 0, 'In-progress': 0, 'Putaway not generated': 0}
    # 'executed': (POLocation, {'status': 0, 'purchase_order__open_po__sku__user': user_id,'updation_date__range': today_range}),
    results_dict = {'In-progress': (POLocation, {'purchase_order__status__in': ['grn-generated', 'location-assigned'],
                                                 'purchase_order__open_po__sku__user': user_id, 'status__in': [1, 2]},
                                    {'location__isnull': True}),
                    'Putaway not generated': (PurchaseOrder, {'open_po__sku__user': user_id,
                                                              'received_quantity__lt': F('open_po__order_quantity')},
                                              {'status__in': ['location-assigned',
                                                              'confirmed-putaway']})}

    get_quantity(pie_putaway, results_dict, True, dashboard_order_level)

    pie_picking = {'Picked': 0, 'In-progres': 0, 'Picklist not generated': 0}

    results_dict = {'Picklist not generated': (OrderDetail, {'user': user_id, 'status': 1, 'quantity__gt': 0}),
                    'In-progres': (
                    Picklist, {'status__contains': 'open', 'order__user': user_id, 'reserved_quantity__gt': 0}),
                    'Picked': (Picklist, {'status__in': ['picked', 'batch_picked', 'dispatched', 'open', 'batch_open'],
                                          'order__user': user_id, 'updation_date__range': today_range})}
    get_quantity(pie_picking, results_dict, True, dashboard_order_level)

    # sales_returns = sales_return_data(user, input_param={'sku__user': user.id, 'return_date__range': [datetime.datetime.now() - relativedelta(months=1), today_start]})
    # picklist_inprogress = Picklist.objects.filter(order__user=user.id, order__status=0, status__icontains='open').\
    #                                       values('order__order_id').distinct().count()

    all_pos = PurchaseOrder.objects.filter(open_po__sku__user=user.id)

    if dashboard_order_level:

        orders = {'open': pie_picking['Picklist not generated'] + pie_picking['In-progres'],
                  'picked': pie_picking['Picked']}

        pending_confirmation = OpenPO.objects.filter(sku__user=user.id, order_quantity__gt=0,
                                                     status__in=[1, 'Manual', 'Automated']).values(
            'supplier_id').distinct().count()

        pending_month = all_pos.exclude(status__in=['location-assigned', 'confirmed-putaway']).filter(
            open_po__sku__user=user.id,
            received_quantity__lt=F('open_po__order_quantity'), po_date__lte=today_start - relativedelta(months=1)). \
            values('order_id').distinct().count()

        received_today = all_pos.filter(open_po__sku__user=user.id, status__in=['grn-generated', 'location-assigned',
                                                                                'confirmed-putaway'],
                                        updation_date__startswith=datetime.datetime.now().strftime('%Y-%m-%d')). \
            values('order_id').distinct().count()

        putaway_pending = POLocation.objects.filter(purchase_order__status__in=['grn-generated', 'location-assigned'],
                                                    quantity__gt=0,
                                                    status=1, purchase_order__open_po__sku__user=user.id).values(
            'purchase_order__order_id'). \
            distinct().count()

        yet_to_receive = all_pos.exclude(status__in=['location-assigned', 'confirmed-putaway']).filter(
            open_po__sku__user=user.id,
            received_quantity__lt=F('open_po__order_quantity')).values('order_id').distinct().count()

    else:

        view_orders_qty = OrderDetail.objects.filter(user=user_id, status=1, quantity__gt=0).aggregate(Sum('quantity'))[
            'quantity__sum']
        if not view_orders_qty:
            view_orders_qty = 0
        open_picklists_qty = \
        Picklist.objects.filter(status__contains='open', order__user=user_id, reserved_quantity__gt=0). \
            aggregate(Sum('reserved_quantity'))['reserved_quantity__sum']
        if not open_picklists_qty:
            open_picklists_qty = 0

        pending_confirmation = \
        OpenPO.objects.filter(sku__user=user.id, order_quantity__gt=0, status__in=[1, 'Manual', 'Automated']). \
            aggregate(Sum('order_quantity'))['order_quantity__sum']

        pending_month = all_pos.exclude(status__in=['location-assigned', 'confirmed-putaway']).filter(
            open_po__sku__user=user.id,
            received_quantity__lt=F('open_po__order_quantity'), po_date__lte=today_start - relativedelta(months=1)). \
            aggregate(Sum('open_po__order_quantity'), Sum('received_quantity'))

        received_today = all_pos.filter(open_po__sku__user=user.id, status__in=['grn-generated', 'location-assigned',
                                                                                'confirmed-putaway'],
                                        updation_date__startswith=datetime.datetime.now().strftime('%Y-%m-%d')). \
            aggregate(Sum('received_quantity'))['received_quantity__sum']

        putaway_pending = \
        POLocation.objects.filter(purchase_order__status__in=['grn-generated', 'location-assigned'], quantity__gt=0,
                                  status=1, purchase_order__open_po__sku__user=user.id). \
            aggregate(Sum('quantity'))['quantity__sum']

        yet_to_receive = all_pos.exclude(status__in=['location-assigned', 'confirmed-putaway']). \
            filter(received_quantity__lt=F('open_po__order_quantity')). \
            aggregate(Sum('open_po__order_quantity'), Sum('received_quantity'))

        if not pending_confirmation:
            pending_confirmation = 0

        if not pending_month['open_po__order_quantity__sum']:
            pending_month['open_po__order_quantity__sum'] = 0
        if not pending_month['received_quantity__sum']:
            pending_month['received_quantity__sum'] = 0
        pending_month = pending_month['open_po__order_quantity__sum'] - pending_month['received_quantity__sum']

        if not received_today:
            received_today = 0

        if not putaway_pending:
            putaway_pending = 0

        if not yet_to_receive['open_po__order_quantity__sum']:
            yet_to_receive['open_po__order_quantity__sum'] = 0
        if not yet_to_receive['received_quantity__sum']:
            yet_to_receive['received_quantity__sum'] = 0
        yet_to_receive = yet_to_receive['open_po__order_quantity__sum'] - yet_to_receive['received_quantity__sum']

        orders = {'open': int(view_orders_qty) + int(open_picklists_qty), 'picked': pie_picking['Picked']}

    purchase_orders = {'pending_confirmation': round(pending_confirmation), 'yet_to_receive': round(yet_to_receive),
                       'pending_month': round(pending_month), 'received_today': round(received_today),
                       'putaway_pending': round(putaway_pending)}

    orders_stats = get_orders_statistics(user, dashboard_order_level)

    return HttpResponse(
        json.dumps({'locations_count': locations_count, 'top_skus_data': top_skus_data, 'top_inventory': top_inventory,
                    'putaway': pie_putaway, 'picking': pie_picking, 'orders': orders,
                    'purchase_orders': purchase_orders, 'orders_stats': orders_stats}))


@csrf_exempt
@login_required
@get_admin_user
@fn_timer
def daily_stock_report(request, user=''):
    get_date = request.GET.get('date', '')
    header_style = easyxf('font: bold on')
    headers = ['SKU Code', 'Description', 'Opening Stock', 'Inwards Quantity', 'Outwards Quantity',
               'Adjustment Quantity', 'Closing Stock']
    market_places = []
    data_dict = []
    all_data = {}
    if get_date:
        today = datetime.datetime.strptime(get_date, '%d-%m-%Y')
    else:
        today = NOW.date()
    wb, ws = get_work_sheet('skus', headers)

    tomorrow = today + datetime.timedelta(1)
    today_start = datetime.datetime.combine(today, datetime.time())
    today_end = datetime.datetime.combine(tomorrow, datetime.time())
    sku_codes = SKUMaster.objects.filter(user=user.id).order_by('sku_code').values('id', 'sku_code',
                                                                                   'sku_desc').distinct()
    data_count = 1
    receipt_objs = POLocation.objects.exclude(status='').filter(Q(updation_date__range=(today_start, today_end)) |
                                                                Q(creation_date__range=(today_start, today_end)),
                                                                location__zone__user=user.id).values(
        'purchase_order__open_po__sku_id').distinct(). \
        annotate(receipts=Sum('original_quantity'))
    putaway_objs = POLocation.objects.filter(Q(updation_date__range=(today_start, today_end)) |
                                             Q(creation_date__range=(today_start, today_end)),
                                             purchase_order__open_po__sku__user=user.id, status=0). \
        values('purchase_order__open_po__sku_id').distinct().annotate(putaway=Sum('original_quantity'))
    market_data = Picklist.objects.filter(Q(updation_date__range=(today_start, today_end)) |
                                          Q(creation_date__range=(today_start, today_end)), status__icontains='picked',
                                          order__user=user.id).values('stock__sku_id', 'order__marketplace').distinct(). \
        annotate(picked=Sum('picked_quantity'))
    stock_objs = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values('sku_id').distinct(). \
        annotate(in_stock=Sum('quantity'))
    adjust_objs = CycleCount.objects.filter(Q(updation_date__range=(today_start, today_end)) |
                                            Q(creation_date__range=(today_start, today_end)), sku__user=user.id).values(
        'sku_id'). \
        distinct().annotate(adjusted=Sum('quantity'), seen_quantity=Sum('seen_quantity'))
    for sku in sku_codes:
        receipt_quantity = 0
        receipts = map(lambda d: d['purchase_order__open_po__sku_id'], receipt_objs)
        if sku['id'] in receipts:
            data_value = map(lambda d: d['receipts'], receipt_objs)[receipts.index(sku['id'])]
            if data_value:
                receipt_quantity = data_value
        putaway_quantity = 0
        putaways = map(lambda d: d['purchase_order__open_po__sku_id'], putaway_objs)
        if sku['id'] in putaways:
            data_value = map(lambda d: d['putaway'], putaway_objs)[putaways.index(sku['id'])]
            if data_value:
                putaway_quantity = data_value
        stock_quantity = 0
        stocks = map(lambda d: d['sku_id'], stock_objs)
        if sku['id'] in stocks:
            data_value = map(lambda d: d['in_stock'], stock_objs)[stocks.index(sku['id'])]
            if data_value:
                stock_quantity = data_value
        adjusted = 0
        adjusts = map(lambda d: d['sku_id'], adjust_objs)
        if sku['id'] in adjusts:
            data_value = map(lambda d: d['adjusted'], adjust_objs)[adjusts.index(sku['id'])]
            seen_quantity = map(lambda d: d['seen_quantity'], adjust_objs)[adjusts.index(sku['id'])]
            if data_value:
                adjusted = seen_quantity - data_value

        temp = OrderedDict(
            (('SKU Code', sku['sku_code']), ('Description', sku['sku_desc']), ('Inwards Quantity', receipt_quantity),
             ('Outwards Quantity', 0), ('Adjustment Quantity', adjusted), ('Closing Stock', stock_quantity)))
        markets = map(lambda d: d['stock__sku_id'], market_data)
        indices = [i for i, x in enumerate(markets) if x == sku['id']]
        for data_index in indices:
            picked_quantity = map(lambda d: d['picked'], market_data)[data_index]
            marketplace = map(lambda d: d['order__marketplace'], market_data)[data_index]
            temp['Outwards Quantity'] += int(picked_quantity)
            cond = (sku['sku_code'], marketplace)
            all_data.setdefault(cond, 0)
            all_data[cond] += int(picked_quantity)
            if marketplace not in market_places:
                market_places.append(marketplace)
                ws.write(0, len(headers), marketplace, header_style)
                headers.append(marketplace)

        temp['market_data'] = all_data
        temp['Opening Stock'] = (int(stock_quantity) - int(putaway_quantity)) + (
        int(temp['Outwards Quantity']) - adjusted)
        for i in range(len(headers)):
            if i in range(0, 7):
                ws.write(data_count, i, temp[headers[i]])
            elif (temp['SKU Code'], headers[i]) in all_data.keys():
                ws.write(data_count, i, all_data[(temp['SKU Code'], headers[i])])
        data_count += 1

    file_name = "%s.%s" % (user.id, 'Daily Stock Report on ' + str(get_date))
    path = 'static/excel_files/' + file_name + '.xls'
    wb.save(path)
    path_to_file = '../../' + path
    return HttpResponseRedirect(path_to_file)
