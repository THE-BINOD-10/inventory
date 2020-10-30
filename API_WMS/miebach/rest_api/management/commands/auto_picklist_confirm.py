from django.core.management import BaseCommand
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
from rest_api.views.common import *
from rest_api.views.outbound import *
import datetime


def init_logger(log_file):
    log = logging.getLogger(log_file)
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    return log


log = init_logger('logs/auto_picklist_data.log')


class Command(BaseCommand):
    help = "upating the auto picklist confirm"

    def handle(self, *args, **options):
        self.stdout.write("auto picklist confirm")

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
                        for picklist in picklist_batch.iterator():
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
                            total_stock = StockDetail.objects.filter(**pic_check_data).distinct()
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
                                # if tot_quan < reserved_quantity1:
                                # total_stock = create_temp_stock(picklist.stock.sku.sku_code, picklist.stock.location.zone, abs(reserved_quantity1 - tot_quan), list(total_stock), user.id)

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
                                update_picked = truncate_float(update_picked, decimal_limit)
                                picklist.reserved_quantity = truncate_float(picklist.reserved_quantity, decimal_limit)
                                stock.quantity = truncate_float(stock.quantity, decimal_limit)
                                if float(stock.location.filled_capacity) - update_picked >= 0:
                                    location_fill_capacity = (float(stock.location.filled_capacity) - update_picked)
                                    location_fill_capacity = truncate_float(location_fill_capacity, decimal_limit)
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
                                # SKU Stats
                                save_sku_stats(user, stock.sku_id, picklist.id, transact_type, update_picked, stock)
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
                                    stock_transfer.status = 2
                                    if stock_transfer.st_seller:
                                        change_seller_stock(stock_transfer.st_seller_id, stock, user, update_picked, 'dec')
                                    stock_transfer.save()
                                    order_typ = stock_transfer.st_type
                                    if not order_typ:
                                        order_typ = request.POST.get('order_typ', '')
                                    update_stock_transfer_po_batch(user, stock_transfer, stock, update_picked, order_typ = order_typ)
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
                                # Auto Shipment check and Mapping the serial Number
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
                        # invoice_data['invoice_no'] = 'TI/1116/' + invoice_data['order_no']
                        # invoice_data['invoice_date'] = get_local_date(user, datetime.datetime.now())
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
                            #return HttpResponse(json.dumps({'data': invoice_data, 'message': '',
                            #                                'sku_codes': [], 'status': 1}))
                            return HttpResponse(invoice_data)
                        return HttpResponse(json.dumps({'data': invoice_data, 'message': '', 'status': 'invoice'}))
            except Exception as e:
                import traceback
                log.debug(traceback.format_exc())
                log.info('Picklist Confirmation failed for %s and params are %s and error statement is %s' % (
                str(user.username), str(final_data_list), str(e)))
                #return HttpResponse(json.dumps({'message': 'Picklist Confirmation Failed',
                #                                'sku_codes': [], 'status': 0}))
                return HttpResponse('Picklist Confirmation Failed')
            end_time = datetime.datetime.now()
            duration = end_time - st_time
            log.info("process completed")
            log.info("total time -- %s" % (duration))

            if mod_locations:
                update_filled_capacity(list(set(mod_locations)), user.id)
            if status:
                return HttpResponse(status)
            else:
                try:
                    netsuite_picklist_confirmation(final_data_list, user)
                except Exception as e:
                    import traceback
                    log.debug(traceback.format_exc())
                    log.info('Netsuite Picklist Confirmation pushing failed for %s and params are %s and error statement is %s' % (
                    str(user.username), str(final_data_list), str(e)))
                return HttpResponse('Picklist Confirmed')


        start_params = {'reserved_quantity__gt': 0, 'status__icontains': 'open'}
        total_picklists = Picklist.objects.select_related('order', 'stock').filter(storder__stock_transfer__st_type='MR', **start_params)
        dist_total_picklists = total_picklists.values('picklist_number', 'stock__sku__user').distinct()
        for mrpicklist in dist_total_picklists:
            print '---------------------------------------------------------------------------------------'
            user, picklist_number = '', ''
            picklist_number = mrpicklist['picklist_number']
            warehouse_id = mrpicklist['stock__sku__user']
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
                # print datum['data']
                for dat in datum['data']:
                    if dat['order_id'] == 'None':
                        dat['order_id'] = ''
                    dat['orig_wms'] = dat['wms_code']
                    dat['passed_serial_number'] = '[]'
                    dat['failed_serial_number'] = '[]'
                    dat['labels'] = ''
                    dat['picklist_status'] = dat['status']
                    dat['orig_loc'] = dat['location']
                    del(dat['status'], dat['sku_imeis_map'], dat['is_combo_picklist'], dat['sequence'], dat['price'], dat['sku_brand'], dat['sku_code'], dat['customer_address'], dat['remarks'], dat['order_no'], dat['original_order_id'], dat['sku_sequence'], dat['category'], dat['picklist_number'], dat['zone'], dat['batch_ref'], dat['load_unit_handle'], dat['stock_left'], dat['invoice_amount'], dat['pallet_code'], dat['customer_name'], dat['image'], dat['marketplace'], dat['last_picked_locs'])
                    picklist = Picklist.objects.get(id=dat['id'])
                    picklist_batch = get_picklist_batch(picklist, [dat], all_picklists)
                    final_data_list.append({'picklist': picklist, 'picklist_batch': picklist_batch,
                                'count': dat['picked_quantity'], 'picklist_order_id': dat['order_id'],
                                'value': [dat], 'key': picklist.id})
                print final_data_list
                datas = picklist_confirmations(user, final_data_list, picklist_number, all_picklists, picks_all)
                print datas
        self.stdout.write("Updation Completed")
