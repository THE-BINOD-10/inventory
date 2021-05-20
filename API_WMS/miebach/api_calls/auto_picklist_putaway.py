from django.core.management import BaseCommand
import os
import logging
import django
from miebach_admin.models import *
from rest_api.views.common import *
from rest_api.views.outbound import *
import datetime

def view_picklist(idpc, wh_id):
    show_image = 'false'
    use_imei = 'false'
    data_id = idpc
    warehouse_id = wh_id
    user = User.objects.get(id=warehouse_id)
    single_order = ''
    order_status = ''
    headers = list(PRINT_OUTBOUND_PICKLIST_HEADERS)
    qc_items_qs = UserAttributes.objects.filter(user_id=user.id,
                                                attribute_model='dispatch_qc',
                                                status=1).values_list('attribute_name', flat=True)
    qc_items = list(qc_items_qs)
    misc_detail = MiscDetail.objects.filter(user=user.id)
    data = misc_detail.filter(misc_type='show_image')
    if data:
        show_image = data[0].misc_value
    if show_image == 'true':
        headers.insert(0, 'Image')
    imei_data = misc_detail.filter(misc_type='use_imei')
    if imei_data:
        use_imei = imei_data[0].misc_value
    if use_imei == 'true':
        headers.insert(-1, 'Serial Number')
    pallet_switch = get_misc_value('pallet_switch', user.id)
    if pallet_switch == 'true':
        headers.insert(headers.index('Location') + 1, 'Pallet Code')
    data, sku_total_quantities, courier_name = get_picklist_data(data_id, user.id)
    if data:
        order_count = list(set(map(lambda d: d.get('order_no', ''), data)))
        order_count_len = len(filter(lambda x: len(str(x)) > 0, order_count))
        if order_count_len == 1:
            single_order = str(order_count[0])
        order_status = data[0]['status']
    datum = {'data': data, 'picklist_id': data_id,
                'show_image': show_image, 'use_imei': use_imei,
                'order_status': order_status,
                'single_order': single_order,
                'sku_total_quantities': sku_total_quantities, 'courier_name' : courier_name,
                'qc_items': qc_items, 'warehouse_id': warehouse_id}
    return datum

def picklist_confirmations(user, final_data_list, picklist_number, all_picklists, picks_all):
    request = ''
    st_time = datetime.datetime.now()
    all_data = {}
    auto_skus = []
    picklists_send_mail = {}
    mod_locations = []
    seller_pick_number = ''
    status = ''
    seller_id = ''
    grn_number_dict = {}
    passed_serial_number = {}
    failed_serial_number = {}
    imei_qc_details = ''
    if passed_serial_number:
        passed_serial_number = eval(passed_serial_number)
    if failed_serial_number:
        failed_serial_number = eval(failed_serial_number)
    if imei_qc_details:
        imei_qc_details = eval(imei_qc_details)
    log.info('Request params for ' + user.username + ' is ' + str(final_data_list))
    try:
        error_string = ''
        picklist_number = picklist_number
        single_order = ''
        enable_damaged_stock = 'false'
        user_profile = UserProfile.objects.get(user_id=user.id)
        decimal_limit = get_decimal_value(user.id)
        if not decimal_limit:
            decimal_limit = 1
        merge_flag = ''
        all_skus = SKUMaster.objects.filter(user=user.id)
        all_locations = LocationMaster.objects.filter(zone__user=user.id)
        all_pick_ids = all_picklists.values_list('id', flat=True)
        all_pick_locations = PicklistLocation.objects.filter(picklist__picklist_number=picklist_number, status=1,
                                                             picklist_id__in=all_pick_ids)
        with transaction.atomic('default'):
            for picklist_dict in final_data_list:
                picklist = picklist_dict['picklist']
                if picklist.storder_set.filter():
                    transact_type = 'st_picklist'
                else:
                    transact_type = 'picklist'
                picklist_batch = picklist_dict['picklist_batch']
                count = picklist_dict['count']
                picklist_order_id = picklist_dict['picklist_order_id']
                value = picklist_dict['value']
                key = picklist_dict['key']
                for val in value:
                    if not val['picked_quantity']:
                        continue
                    else:
                        val['picked_quantity'] = float(val['picked_quantity']) * float(val['conversion_value'])
                        count = float(val['picked_quantity'])
                    if picklist_order_id:
                        picklist_batch = list(set([picklist]))
                    if not val['location'] == 'NO STOCK':
                        picklist_batch = update_no_stock_to_location(request, user, picklist, val, picks_all,
                                                                     picklist_batch)
                    temp_pick_ids = map(lambda x: x.id, picklist_batch)
                    picklist_batch_objs = Picklist.objects.using('default').filter(id__in=temp_pick_ids).select_for_update()
                    for picklist in picklist_batch_objs.iterator():
                        save_status = ''
                        if not failed_serial_number.keys() and count == 0:
                            continue

                        status = ''
                        if not val['location'] == 'NO STOCK':
                            pic_check_data, status = validate_location_stock(val, all_locations, all_skus, user,
                                                                             picklist)
                        if status:
                            continue
                        if not picklist.stock:
                            if val['location'] == 'NO STOCK':
                                if float(picklist.reserved_quantity) > float(val['picked_quantity']):
                                    picking_count = float(val['picked_quantity'])
                                else:
                                    picking_count = float(picklist.reserved_quantity)
                                count -= picking_count
                                seller_pick_number = confirm_no_stock(picklist, request, user, picks_all,
                                                                      picklists_send_mail, merge_flag, user_profile,
                                                                      seller_pick_number, val=val,
                                                                      p_quantity=picking_count)
                                continue
                        if not seller_pick_number:
                            if picklist.storder_set.filter():
                                seller_pick_number  =  get_stocktransfer_picknumber(user, picklist)
                            else:
                                seller_pick_number = get_seller_pick_id(picklist, user)
                        if float(picklist.reserved_quantity) > float(val['picked_quantity']):
                            picking_count = float(val['picked_quantity'])
                        else:
                            picking_count = float(picklist.reserved_quantity)
                        picking_count1 = 0  # picking_count
                        wms_id = all_skus.exclude(sku_code='').get(wms_code=val['wms_code'], user=user.id)
                        if not val.get('batchno', ''):
                            total_stock1 = StockDetail.objects.using('default').filter(batch_detail__batch_no='', creation_date__lt='2020-12-01', **pic_check_data).\
                                                    distinct().select_for_update()
                            total_stock2 = StockDetail.objects.using('default').filter(creation_date__lt='2020-12-01', **pic_check_data).\
                                                    exclude(batch_detail__batch_no='').distinct().select_for_update()
                            total_stock = total_stock1 | total_stock2
                        else:
                            total_stock = StockDetail.objects.using('default').filter(creation_date__lt='2020-12-01', **pic_check_data).distinct().select_for_update()
                        if 'imei' in val.keys() and val['imei'] and picklist.order and val['imei'] != '[]':
                            insert_order_serial(picklist, val)
                        if 'labels' in val.keys() and val['labels'] and picklist.order:
                            update_order_labels(picklist, val)
                        order_id = picklist.order
                        if picklist.order and picklist.order.sku.wms_code in passed_serial_number.keys():
                            if val.get('passed_serial_number', ''):
                                send_imei_qc_details = dict(zip(json.loads(val.get('passed_serial_number', '')), [imei_qc_details[k] for k in json.loads(val.get('passed_serial_number', ''))]))
                                save_status = "PASS"
                            try:
                                dispatch_qc(user, send_imei_qc_details, order_id, save_status)
                            except Exception as e:
                                import traceback
                                picklist_qc_log.debug(traceback.format_exc())
                                picklist_qc_log.info("Error in Dispatch QC - On Pass - %s - %s" % (str(user.username),  str(e)))
                        if picklist.order and picklist.order.sku.wms_code in failed_serial_number.keys():
                            if val.get('failed_serial_number', ''):
                                send_imei_qc_details = dict(zip(json.loads(val.get('failed_serial_number', '')), [imei_qc_details[k] for k in json.loads(val.get('failed_serial_number', ''))]))
                                save_status = "FAIL"
                            try:
                                dispatch_qc(user, send_imei_qc_details, order_id, save_status)
                            except Exception as e:
                                import traceback
                                picklist_qc_log.debug(traceback.format_exc())
                                picklist_qc_log.info("Error in Dispatch QC - On Fail - %s - %s" % (str(user.username), str(e)))
                        if count == 0:
                            continue
                        if  'imei' in val.keys() and val['imei'] and not picklist.order and val['imei'] != '[]' :
                            order = picklist.storder_set.filter()
                            if order:
                                order = order[0]
                                insert_st_order_serial(picklist, val, order=order)
                        if passed_serial_number and picklist.storder_set.filter():
                            order = picklist.storder_set.filter()
                            order = order[0]
                            insert_st_order_serial(picklist, val, order=order,passed_serial_number = passed_serial_number)
                        reserved_quantity1 = picklist.reserved_quantity
                        tot_quan = 0
                        for stock in total_stock:
                            tot_quan += float(stock.quantity)

                        seller_stock_objs = []
                        for stock in total_stock:
                            update_picked = 0
                            if user.userprofile.user_type == 'marketplace_user':
                                if picklist.order:
                                    seller_order = picklist.order.sellerorder_set.filter()
                                    seller_id = ''
                                    if seller_order:
                                        seller_id = seller_order[0].seller_id
                                elif picklist.storder_set.filter():
                                    stock_transfer = picklist.storder_set.filter()[0].stock_transfer
                                    seller_id = stock_transfer.st_seller_id
                                stock_quantity = SellerStock.objects.filter(stock_id=stock.id, seller_id=seller_id,
                                                                        quantity__gt=0).aggregate(Sum('quantity'))['quantity__sum']
                                if not stock_quantity:
                                    stock_quantity = 0
                            else:
                                stock_quantity = stock.quantity
                            pre_stock = float(stock_quantity)
                            if picking_count == 0:
                                break
                            # new Code
                            # print picking_count
                            # conv_value = 1
                            # if stock.batch_detail:
                            #     conv_value = stock.batch_detail.pcf
                            #     if not conv_value:
                            #         uom_dict = get_uom_with_sku_code(user, stock.sku.sku_code, uom_type='purchase')
                            #         conv_value = uom_dict.get('sku_conversion', 1)
                            # new Code
                            if picking_count > stock_quantity:
                                update_picked = float(stock_quantity)
                                picking_count -= stock_quantity
                                picklist.reserved_quantity -= stock_quantity

                                stock.quantity = stock.quantity - stock_quantity
                            else:
                                update_picked = picking_count
                                stock.quantity -= picking_count
                                picklist.reserved_quantity -= picking_count
                                picking_count = 0
                            update_picked = truncate_float(update_picked, 5)
                            picklist.reserved_quantity = truncate_float(picklist.reserved_quantity, 5)
                            stock.quantity = truncate_float(stock.quantity, 5)
                            if float(stock.location.filled_capacity) - update_picked >= 0:
                                location_fill_capacity = (float(stock.location.filled_capacity) - update_picked)
                                location_fill_capacity = truncate_float(location_fill_capacity, 5)
                                setattr(stock.location, 'filled_capacity', location_fill_capacity)
                                stock.location.save()
                            if picklist.storder_set.filter():
                                try:
                                    if picklist.storder_set.filter()[0].stock_transfer.st_type == 'MR':
                                        transact_type = 'mr_picklist'
                                    else:
                                        transact_type = 'st_picklist'
                                except Exception as e:
                                    transact_type = 'st_picklist'
                            else:
                                transact_type = 'picklist'
                            search_po_locations = {
                                'picklist_id': picklist.id,
                                'stock__location_id': stock.location_id,
                                'status': 1
                            }
                            if stock.batch_detail:
                                search_po_locations['stock__batch_detail__batch_no'] = stock.batch_detail.batch_no
                            pick_loc = all_pick_locations.filter(**search_po_locations)
                            # update_picked = picking_count1
                            st_order = picklist.storder_set.filter()
                            if st_order:
                                stock_transfer = st_order[0].stock_transfer
                                last_change_date = stock_transfer.creation_date.date()
                                if stock_transfer.status != 1:
                                    stock_transfer.status = 2
                                if stock_transfer.st_seller:
                                    change_seller_stock(stock_transfer.st_seller_id, stock, user, update_picked, 'dec')
                                stock_transfer.save()
                                order_typ = stock_transfer.st_type
                                if not order_typ:
                                    order_typ = request.POST.get('order_typ', '')
                                update_picked_pack_qty = update_picked/float(val['conversion_value'])
                                grn_number_dict = update_stock_transfer_po_batch(user, stock_transfer, stock,
                                                                            update_picked_pack_qty,
                                                               order_typ = order_typ,
                                                                                 grn_number_dict=grn_number_dict, last_change_date=last_change_date)
                                save_sku_stats(user, stock.sku_id, picklist.id, transact_type, update_picked, stock, transact_date=last_change_date)
                            else:
                                # SKU Stats
                                save_sku_stats(user, stock.sku_id, picklist.id, transact_type, update_picked, stock)
                            if pick_loc:
                                update_picklist_locations(pick_loc, picklist, update_picked, pick_sequence=seller_pick_number)
                            else:
                                data = PicklistLocation(picklist_id=picklist.id, stock=stock, quantity=update_picked,
                                                        reserved=0, status=0,
                                                        creation_date=datetime.datetime.now(),
                                                        updation_date=datetime.datetime.now())
                                data.save()
                                exist_pics = all_pick_locations.exclude(id=data.id).filter(picklist_id=picklist.id,
                                                                                           status=1, reserved__gt=0)
                                po_location_sequence_mapping(data, seller_pick_number, update_picked)
                                update_picklist_locations(exist_pics, picklist, update_picked, 'true')
                            if stock.location.zone.zone == 'BAY_AREA':
                                reduce_putaway_stock(stock, update_picked, user.id)
                            dec_quantity = pre_stock - float(stock.quantity)
                            if stock.pallet_detail:
                                update_picklist_pallet(stock, update_picked)
                            stock.save()
                            seller_stock_objs.append(stock)
                            mod_locations.append(stock.location.location)
                            picking_count1 += update_picked
                        picklist.picked_quantity = float(picklist.picked_quantity) + picking_count1
                        if picklist.reserved_quantity == 0:
                            if picklist.order and picklist.order.order_type == 'Transit':
                                serial_order_mapping(picklist, user)
                            if picklist.status == 'batch_open':
                                picklist.status = 'batch_picked'
                            else:
                                picklist.status = 'picked'
                            if picklist.order:
                                check_and_update_order(user.id, picklist.order.original_order_id)
                            all_pick_locations.filter(picklist_id=picklist.id, status=1).update(status=0)
                        picklist.save()
                        if user_profile.user_type == 'marketplace_user' and picklist.order:
                            create_seller_order_summary(picklist, picking_count1, seller_pick_number, picks_all,
                                                        seller_stock_objs)
                        else:
                            create_order_summary(picklist, picking_count1, seller_pick_number, picks_all)
                        picked_status = ""
                        if picklist.picked_quantity > 0 and picklist.order:
                            if merge_flag:
                                quantity = picklist.picked_quantity
                            else:
                                quantity = picking_count1
                            if picklist.order.order_id in picklists_send_mail.keys():
                                if picklist.order.sku.sku_code in picklists_send_mail[picklist.order.order_id].keys():
                                    qty = float(picklists_send_mail[picklist.order.order_id][picklist.order.sku.sku_code])
                                    picklists_send_mail[picklist.order.order_id][picklist.order.sku.sku_code] = qty + float(
                                        quantity)
                                else:
                                    picklists_send_mail[picklist.order.order_id].update(
                                        {picklist.order.sku.sku_code: float(quantity)})

                            else:
                                picklists_send_mail.update(
                                    {picklist.order.order_id: {picklist.order.sku.sku_code: float(quantity)}})
                        count = count - picking_count1
                        auto_skus.append(val['wms_code'])
            for grn_dict in grn_number_dict.values():
                update_sku_avg_from_grn(grn_dict['warehouse'], grn_dict['grn_number'])
        if auto_skus:
            auto_skus = list(set(auto_skus))
            if user.username in MILKBASKET_USERS: check_and_update_marketplace_stock(auto_skus, user)
            price_band_flag = get_misc_value('priceband_sync', user.id)
            if price_band_flag == 'true':
                reaches_order_val, sku_qty_map = check_req_min_order_val(user, auto_skus)
                if reaches_order_val:
                    auto_po(auto_skus, user.id)
                    delete_intransit_orders(auto_skus, user)  # deleting intransit order after creating actual order.
                else:
                    create_intransit_order(auto_skus, user, sku_qty_map)
            else:
                auto_po(auto_skus, user.id)
        detailed_invoice = get_misc_value('detailed_invoice', user.id)

        if (detailed_invoice == 'false' and picklist.order and picklist.order.marketplace == "Offline"):
            check_and_send_mail(request, user, picklist, picks_all, picklists_send_mail)
        order_ids = picks_all.values_list('order_id', flat=True).distinct()
        if get_misc_value('automate_invoice', user.id) == 'true' and single_order:
            order_ids = picks_all.filter(order__order_id=single_order, picked_quantity__gt=0).values_list('order_id',
                                                                                                          flat=True).distinct()
            order_id = picklists_send_mail.keys()
            if order_ids and order_id:
                ord_id = order_id[0]
                order_ids = [str(int(i)) for i in order_ids]
                order_ids = ','.join(order_ids)
                invoice_data = get_invoice_data(order_ids, user, picklists_send_mail[ord_id])
                invoice_data = modify_invoice_data(invoice_data, user)
                offline_flag = False
                if picklist.order.marketplace == "Offline":
                    offline_flag = True
                invoice_data['offline_flag'] = offline_flag
                invoice_data['picklist_id'] = picklist.id
                invoice_data['picklists_send_mail'] = str(picklists_send_mail)

                invoice_data['order_id'] = invoice_data['order_id']
                user_profile = UserProfile.objects.get(user_id=user.id)
                if not invoice_data['detailed_invoice'] and invoice_data['is_gst_invoice']:
                    invoice_data = build_invoice(invoice_data, user, False)
                    return HttpResponse(invoice_data)
                return HttpResponse(json.dumps({'data': invoice_data, 'message': '', 'status': 'invoice'}))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Picklist Confirmation failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(final_data_list), str(e)))
        return HttpResponse('Picklist Confirmation Failed')
    end_time = datetime.datetime.now()
    duration = end_time - st_time
    log.info("process completed")
    log.info("total time -- %s" % (duration))

    if mod_locations:
        update_filled_capacity(list(set(mod_locations)), user.id)
    if status:
        return HttpResponse(status)

def generate_picklist(data_dict, user):
    enable_damaged_stock = data_dict.get('enable_damaged_stock', 'false')
    out_of_stock = []
    picklist_number = get_picklist_number(user)
    picklist_exclude_zones = get_exclude_zones(user)
    sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
    switch_vals = {'marketplace_model': get_misc_value('marketplace_model', user.id),
                   'fifo_switch': get_misc_value('fifo_switch', user.id),
                   'no_stock_switch': get_misc_value('no_stock_switch', user.id),
                   'combo_allocate_stock': get_misc_value('combo_allocate_stock', user.id),
                   'allow_partial_picklist': get_misc_value('allow_partial_picklist', user.id)}
    seller_stocks = SellerStock.objects.filter(seller__user=user.id, stock__quantity__gt=0).values('stock_id', 'seller_id')
    key, value = data_dict.get("st_order_id"), user.id
    # for key, value in request.POST.iteritems():
    # if key == 'enable_damaged_stock':
    #     pass
    warehouse_id = value
    user = User.objects.get(id=value)
    if enable_damaged_stock == 'true':
        sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').filter(sku__user=user.id,
                                                                                    quantity__gt=0,
                                                                                    location__zone__zone__in=[
                                                                                        'DAMAGED_ZONE'])
    else:
        sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(
            location__zone__zone__in=picklist_exclude_zones).filter(sku__user=user.id, quantity__gt=0)
    if switch_vals['fifo_switch'] == 'true':
        stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').order_by(
            'receipt_date')
        stock_detail2 = sku_stocks.order_by('receipt_date')
    else:
        stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).order_by(
            'location_id__pick_sequence')
        stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).order_by(
            'receipt_date')
    sku_stocks = stock_detail1 | stock_detail2
    orders_data = StockTransfer.objects.filter(order_id=key, status=1, sku__user=user.id)
    if orders_data and orders_data[0].st_seller:
        seller_stock_dict = filter(lambda person: str(person['seller_id']) == str(orders_data[0].st_seller_id),
                                   seller_stocks)
        if seller_stock_dict:
            sell_stock_ids = map(lambda person: person['stock_id'], seller_stock_dict)
            sku_stocks = sku_stocks.filter(id__in=sell_stock_ids)
        else:
            sku_stocks = sku_stocks.filter(id=0)
    stock_status, picklist_number = picklist_generation(orders_data, enable_damaged_stock, picklist_number, user,
                                                        sku_combos, sku_stocks, switch_vals)

    if stock_status:
        out_of_stock = out_of_stock + stock_status

    if out_of_stock:
        stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
    else:
        stock_status = ''

    check_picklist_number_created(user, picklist_number + 1)
    order_status = ''
    data, sku_total_quantities, courier_name = get_picklist_data(picklist_number + 1, user.id)
    if data:
        order_status = data[0]['status']
    # return HttpResponse(json.dumps({'data': data, 'picklist_id': picklist_number + 1, 'stock_status': stock_status,
    #                                 'order_status': order_status, 'warehouse_id': warehouse_id}))
# start_params = {'reserved_quantity__gt': 0, 'status__icontains': 'open'}
# total_picklists = Picklist.objects.select_related('order', 'stock').filter(storder__stock_transfer__st_type='MR', **start_params)
# dist_total_picklists = total_picklists.values('picklist_number', 'stock__sku__user').distinct()
# for mrpicklist in dist_total_picklists:
    print '---------------------------------------------------------------------------------------'
    # user, picklist_number = '', ''
    picklist_number = picklist_number + 1
    warehouse_id = user.id
    try:
        user = User.objects.get(id=warehouse_id)
    except Exception as e:
        pass
    if user and picklist_number:
        all_picklists = Picklist.objects.filter(Q(order__sku__user=user.id) | Q(stock__sku__user=user.id),
                                            picklist_number=picklist_number,
                                            status__icontains="open")
        picks_all = Picklist.objects.filter(Q(order__sku__user=user.id) | Q(stock__sku__user=user.id),
                                        picklist_number=picklist_number)
        # if picklist_number == 1090:
        final_data_list = []
        datum = view_picklist(picklist_number, warehouse_id)
        for dat in datum['data']:
            if dat['order_id'] == 'None':
                dat['order_id'] = ''
            dat['orig_wms'] = dat['wms_code']
            dat['passed_serial_number'] = '[]'
            dat['failed_serial_number'] = '[]'
            dat['labels'] = ''
            dat['picklist_status'] = dat['status']
            dat['orig_loc'] = dat['location']
            dat['orig_batchno'] = dat['batchno']
            del(dat['status'], dat['sku_imeis_map'], dat['is_combo_picklist'], dat['sequence'], dat['price'], dat['sku_brand'], dat['sku_code'], dat['customer_address'], dat['remarks'], dat['order_no'], dat['original_order_id'], dat['sku_sequence'], dat['category'], dat['picklist_number'], dat['zone'], dat['batch_ref'], dat['load_unit_handle'], dat['stock_left'], dat['invoice_amount'], dat['pallet_code'], dat['customer_name'], dat['image'], dat['marketplace'], dat['last_picked_locs'])
            picklist = Picklist.objects.get(id=dat['id'])
            picklist_batch = get_picklist_batch(picklist, [dat], all_picklists)
            final_data_list.append({'picklist': picklist, 'picklist_batch': picklist_batch,
                        'count': dat['picked_quantity'], 'picklist_order_id': dat['order_id'],
                        'value': [dat], 'key': picklist.id})
        print final_data_list
        datas = picklist_confirmations(user, final_data_list, picklist_number, all_picklists, picks_all)
        print datas
# self.stdout.write("Updation Completed")
