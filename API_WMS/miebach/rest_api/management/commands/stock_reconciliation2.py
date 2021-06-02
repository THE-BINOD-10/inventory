from collections import OrderedDict
from django.core.management import BaseCommand
from django.db.models import Q, Sum, F
import os
import logging
import django
import pandas as pd
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
from rest_api.views import *
from rest_api.views.common import get_company_id, get_related_users_filters, get_company_admin_user, get_uom_with_sku_code, get_admin
import datetime
from rest_api.views.easyops_api import *


def init_logger(log_file):
    log = logging.getLogger(log_file)

    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    return log

log = init_logger('logs/metropolis_stock_reconciliation.log')

def recon_calc(main_user, user, data_list, opening_date, closing_date, start_day, end_day):
    skus = SKUMaster.objects.filter(user=user.id).exclude(id__in=AssetMaster.objects.all()).exclude(id__in=ServiceMaster.objects.all()).\
                                exclude(id__in=OtherItemsMaster.objects.all()).only('sku_code')
    counter = 0
    usr = user

    dates = [start_day, end_day]

    dept_users = get_related_users_filters(main_user.id, warehouse_types=['DEPT'], warehouse=[user.username])
    dept_user_ids = list(dept_users.values_list('id', flat=True))
    dept_user_ids.append(user.id)
    sku_codes = list(skus.values_list('sku_code', flat=True))
    sku_uoms = get_uom_with_multi_skus(user, sku_codes, 'purchase')

    opening_dict = {}
    po_grn_dict = {}
    st_grn_dict = {}
    mr_grn_dict = {}
    st_out_dict = {}
    mr_out_dict = {}
    mr_pending_dict = {}
    rtv_dict = {}
    cons_dict = {}
    stock_dict = {}
    closing_dict = {}
    adjust_dict = {}
    opening_st = ClosingStock.objects.filter(stock__sku__user__in=dept_user_ids, creation_date__date=opening_date).only('quantity', 'sku_avg_price', 'sku_pcf')
    if opening_st.exists():
        for cls in opening_st:
            sku_code = cls.stock.sku.sku_code
            opening_dict.setdefault(sku_code, {'opening_qty': 0, 'opening_value': 0})
            opening_dict[sku_code]['opening_qty'] += cls.quantity/cls.sku_pcf
            opening_dict[sku_code]['opening_value'] += cls.sku_avg_price*(cls.quantity/cls.sku_pcf)
    adjustment = InventoryAdjustment.objects.filter(stock__sku__user__in=dept_user_ids, creation_date__range=dates)
    for adj in adjustment:
        sku_code = adj.stock.sku.sku_code
        uom_dict = sku_uoms.get(sku_code, {})
        sku_pcf = uom_dict.get('sku_conversion', 1)
        adjust_dict.setdefault(sku_code, {'adj_qty': 0, 'adj_value': 0})
        adjust_dict[sku_code]['adj_qty'] += float(adj.adjusted_quantity/sku_pcf)
        adjust_dict[sku_code]['adj_value'] += float(adj.price*(adj.adjusted_quantity/sku_pcf))
    poss = SellerPOSummary.objects.prefetch_related('batch_detail').filter(purchase_order__open_po__sku__user=usr.id, creation_date__range=dates).\
                                    only('purchase_order__open_po__sku__sku_code', 'quantity', 'batch_detail__pcf', 'batch_detail__tax_percent', 'batch_detail__cess_percent')
    for psp in poss:
        sku_code = psp.purchase_order.open_po.sku.sku_code
        uom_dict = sku_uoms.get(sku_code, {})
        sku_pcf = uom_dict.get('sku_conversion', 1)
        po_grn_dict.setdefault(sku_code, {'po_grn_qty': 0, 'po_grn_value': 0})
        if psp.batch_detail:
            po_grn_dict[sku_code]['po_grn_qty'] += (psp.quantity * psp.batch_detail.pcf)/sku_pcf
            unit_price_tax = psp.batch_detail.buy_price + ((psp.batch_detail.buy_price/100) * (psp.batch_detail.tax_percent+psp.batch_detail.cess_percent))
            po_grn_dict[sku_code]['po_grn_value'] += psp.quantity * unit_price_tax
        else:
            po_grn_dict[sku_code]['po_grn_qty'] += psp.quantity
            po_grn_dict[sku_code]['po_grn_value'] += psp.price * psp.quantity
    spss = SellerPOSummary.objects.filter(purchase_order__stpurchaseorder__open_st__sku__user=usr.id, creation_date__range=dates,
                                            purchase_order__stpurchaseorder__stocktransfer__st_type='ST_INTRA')
    for sps in spss:
        st_obj = sps.purchase_order.stpurchaseorder_set.filter()[0].stocktransfer_set.filter()[0]
        open_st = sps.purchase_order.stpurchaseorder_set.filter()[0].open_st
        open_st_price = open_st.price
        sku_code = open_st.sku.sku_code
        uom_dict = sku_uoms.get(sku_code, {})
        sku_pcf = uom_dict.get('sku_conversion', 1)
        st_grn_dict.setdefault(sku_code, {'st_grn_qty': 0, 'st_grn_value': 0})
        if sps.batch_detail:
            st_grn_dict[sku_code]['st_grn_qty'] += (sps.quantity * sps.batch_detail.pcf)/sku_pcf
            st_grn_dict[sku_code]['st_grn_value'] += open_st_price * sps.quantity
        else:
            st_grn_dict[sku_code]['st_grn_qty'] += sps.quantity
            st_grn_dict[sku_code]['st_grn_value'] += open_st_price * sps.quantity
    spss_mr = SellerPOSummary.objects.filter(purchase_order__stpurchaseorder__open_st__sku__user__in=dept_user_ids, creation_date__range=dates,
                                            purchase_order__stpurchaseorder__stocktransfer__st_type='MR')
    for sps in spss_mr:
        st_obj = sps.purchase_order.stpurchaseorder_set.filter()[0].stocktransfer_set.filter()[0]
        open_st = sps.purchase_order.stpurchaseorder_set.filter()[0].open_st
        open_st_price = open_st.price
        sku_code = open_st.sku.sku_code
        uom_dict = sku_uoms.get(sku_code, {})
        sku_pcf = uom_dict.get('sku_conversion', 1)
        mr_grn_dict.setdefault(sku_code, {'st_grn_qty': 0, 'st_grn_value': 0})
        if sps.batch_detail:
            mr_grn_dict[sku_code]['st_grn_qty'] += (sps.quantity * sps.batch_detail.pcf)/sku_pcf
            mr_grn_dict[sku_code]['st_grn_value'] += open_st_price * sps.quantity
        else:
            mr_grn_dict[sku_code]['st_grn_qty'] += sps.quantity
            mr_grn_dict[sku_code]['st_grn_value'] += open_st_price * sps.quantity

    stock_transfers = StockTransferSummary.objects.filter(creation_date__range=dates, stock_transfer__st_type='ST_INTRA', stock_transfer__sku__user=usr.id)
    for stock_transfer in stock_transfers:
        sku_code = stock_transfer.stock_transfer.sku.sku_code
        uom_dict = sku_uoms.get(sku_code, {})
        sku_pcf = uom_dict.get('sku_conversion', 1)
        st_out_dict.setdefault(sku_code, {'st_out_qty': 0, 'st_out_value': 0})
        st_out_dict[sku_code]['st_out_qty'] += (stock_transfer.quantity/sku_pcf)
        if stock_transfer.price:
            price = stock_transfer.price
        else:
            price = stock_transfer.stock_transfer.st_po.open_st.price
        st_out_dict[sku_code]['st_out_value'] += ((stock_transfer.quantity/sku_pcf) * price)
    stock_transfers1 = StockTransferSummary.objects.filter(creation_date__range=dates, stock_transfer__st_type='MR', stock_transfer__sku__user__in=dept_user_ids)
    for stock_transfer1 in stock_transfers1:
        sku_code = stock_transfer1.stock_transfer.sku.sku_code
        uom_dict = sku_uoms.get(sku_code, {})
        sku_pcf = uom_dict.get('sku_conversion', 1)
        mr_out_dict.setdefault(sku_code, {'mr_out_qty': 0, 'mr_out_value': 0})
        temp_mr_qty = (stock_transfer1.quantity/sku_pcf)
        mr_out_dict[sku_code]['mr_out_qty'] += temp_mr_qty
        if stock_transfer1.price:
            price = stock_transfer1.price
        else:
            price = stock_transfer1.stock_transfer.st_po.open_st.price
        mr_out_dict[sku_code]['mr_out_value'] += (temp_mr_qty * price)
    #RTVS
    rtvs = ReturnToVendor.objects.filter(creation_date__range=dates, seller_po_summary__purchase_order__open_po__sku__user=usr.id).exclude(rtv_number='')
    for rtv in rtvs:
        rtv_sps = rtv.seller_po_summary
        sku_code = rtv_sps.purchase_order.open_po.sku.sku_code
        uom_dict = sku_uoms.get(sku_code, {})
        sku_pcf = uom_dict.get('sku_conversion', 1)
        rtv_dict.setdefault(sku_code, {'rtv_qty': 0, 'rtv_value': 0})
        rtv_dict[sku_code]['rtv_qty'] += (rtv.quantity * rtv_sps.batch_detail.pcf)/sku_pcf
        unit_rtv_price_tax = rtv_sps.batch_detail.buy_price + ((rtv_sps.batch_detail.buy_price/100) * (rtv_sps.batch_detail.tax_percent+rtv_sps.batch_detail.cess_percent))
        rtv_dict[sku_code]['rtv_value'] += rtv.quantity * unit_rtv_price_tax
    cons = ConsumptionData.objects.filter(creation_date__range=dates, sku__user__in=dept_user_ids).only('quantity', 'price')
    for con in cons:
        sku_code = con.sku.sku_code
        uom_dict = sku_uoms.get(sku_code, {})
        sku_pcf = uom_dict.get('sku_conversion', 1)
        cons_dict.setdefault(sku_code, {'cons_qty': 0, 'cons_value': 0})
        cons_dict[sku_code]['cons_qty'] += con.quantity/sku_pcf
        cons_dict[sku_code]['cons_value'] += (con.quantity/sku_pcf) * con.price
    stocks = StockDetail.objects.filter(sku__user__in=dept_user_ids, quantity__gt=0, creation_date__lte=closing_date+datetime.timedelta(days=1)).only('quantity')
    for stock in stocks:
        sku_code = stock.sku.sku_code
        uom_dict = sku_uoms.get(sku_code, {})
        sku_pcf = uom_dict.get('sku_conversion', 1)
        stock_dict.setdefault(sku_code, {'stock_qty': 0, 'stock_value': 0})
        stock_dict[sku_code]['stock_qty'] += (stock.quantity/sku_pcf)
        stock_dict[sku_code]['stock_value'] += ((stock.quantity/sku_pcf)*stock.sku.average_price)
    mclosing_st = ClosingStock.objects.filter(stock__sku__user__in=dept_user_ids, creation_date__date=closing_date).only('quantity', 'sku_avg_price', 'sku_pcf')
    for mcls in mclosing_st:
        sku_code = mcls.stock.sku.sku_code
        uom_dict = sku_uoms.get(sku_code, {})
        sku_pcf = uom_dict.get('sku_conversion', 1)
        closing_dict.setdefault(sku_code, {'mclosing_qty': 0, 'mclosing_value': 0})
        closing_dict[sku_code]['mclosing_qty'] += mcls.quantity/mcls.sku_pcf
        closing_dict[sku_code]['mclosing_value'] += mcls.sku_avg_price*(mcls.quantity/mcls.sku_pcf)

    doas = MastersDOA.objects.filter(model_name='mr_doa', doa_status='pending', requested_user_id__in=dept_user_ids)
    for doa in doas:
        json_dat = json.loads(doa.json_data)
        sku_code = json_dat['sku_code']
        price = PurchaseOrder.objects.get(id=json_dat['po']).stpurchaseorder_set.filter()[0].open_st.price
        mr_pending_dict.setdefault(sku_code, {'pending_qty': 0, 'pending_value': 0})
        mr_pending_dict[sku_code]['pending_qty'] += json_dat['update_picked']
        mr_pending_dict[sku_code]['pending_value'] += (json_dat['update_picked'] * price)

    for sku in skus:
        sk = sku.sku_code
        data_dict = {}
        counter += 1
        user_obj = User.objects.get(id=usr.id)
        dept_users = get_related_users_filters(main_user.id, warehouse_types=['DEPT'], warehouse=[user_obj.username])
        dept_user_ids = list(dept_users.values_list('id', flat=True))
        dept_user_ids.append(usr.id)
        opening_qty, opening_value, st_grn_qty, st_grn_value, po_grn_qty, po_grn_value, st_out_qty, st_out_value, rtv_qty,\
                rtv_value, cons_qty, cons_value, mr_out_qty, mr_out_value, stock_qty, stock_value = [0]*16
        opening_sku = opening_dict.get(sk, {})
        opening_qty = opening_sku.get('opening_qty', 0)
        opening_value = opening_sku.get('opening_value', 0)
        uom_dict = sku_uoms.get(sk, {})
        sku_pcf = uom_dict.get('sku_conversion', 1)
        grn_dict = po_grn_dict.get(sk, {})
        po_grn_qty = grn_dict.get('po_grn_qty', 0)
        po_grn_value = grn_dict.get('po_grn_value', 0)
        st_grn = st_grn_dict.get(sk, {})
        st_grn_qty = st_grn.get('st_grn_qty', 0)
        st_grn_value = st_grn.get('st_grn_value', 0)
        mr_grn = mr_grn_dict.get(sk, {})
        mr_grn_qty = mr_grn.get('st_grn_qty', 0)
        mr_grn_value = mr_grn.get('st_grn_value', 0)
        sku_st_out = st_out_dict.get(sk, {})
        st_out_qty = sku_st_out.get('st_out_qty', 0)
        st_out_value = sku_st_out.get('st_out_value', 0)
        sku_mr_out = mr_out_dict.get(sk, {})
        mr_out_qty = sku_mr_out.get('mr_out_qty', 0)
        mr_out_value = sku_mr_out.get('mr_out_value', 0)
        sku_mr = mr_pending_dict.get(sk, {})
        mr_pending_qty = sku_mr.get('pending_qty', 0)
        mr_pending_value = sku_mr.get('pending_value', 0)
        sku_rtv = rtv_dict.get(sk, {})
        rtv_qty = sku_rtv.get('rtv_qty', 0)
        rtv_value = sku_rtv.get('rtv_value', 0)
        sku_adj = adjust_dict.get(sk, {})
        sku_adj_qty = sku_adj.get('adj_qty', 0)
        sku_adj_value = sku_adj.get('adj_value', 0)
        sku_cons = cons_dict.setdefault(sk, {})
        cons_qty = sku_cons.get('cons_qty', 0)
        cons_value = sku_cons.get('cons_value', 0)
        sku_stock = stock_dict.get(sk, {})
        stock_qty = sku_stock.get('stock_qty', 0)
        stock_value = sku_stock.get('stock_value', 0)
        sku_closing = closing_dict.get(sk, {})
        mclosing_qty = sku_closing.get('mclosing_qty', 0)
        mclosing_value = sku_closing.get('mclosing_value', 0)
        current_avg = sku.average_price
        total_denom_qty = (opening_qty + po_grn_qty + st_grn_qty - st_out_qty - rtv_qty - cons_qty)
        #if round(mclosing_qty, 1) != round(total_denom_qty,1):
        #    print "Qty Issue"
        #    print user.username, sk
        total_denom_qty1 = (opening_qty + po_grn_qty + st_grn_qty - st_out_qty - rtv_qty + sku_adj_qty)
        total_denom_qty1 = total_denom_qty1 if total_denom_qty1 else 1
        total_value = (opening_value + po_grn_value + st_grn_value - st_out_value - rtv_value + sku_adj_value)
        main_avg_price = total_value/total_denom_qty1
        main_avg_price = abs(float('%.5f' % main_avg_price))
        if round(main_avg_price, 5) != round(current_avg, 5):
            #print "Price Issue"
            #print user.username, sk, main_avg_price, current_avg
            pass
        exp_closing_qty = opening_qty + po_grn_qty + st_grn_qty + mr_grn_qty - st_out_qty - rtv_qty - cons_qty - mr_out_qty + sku_adj_qty
        exp_closing_val = opening_value + po_grn_value + st_grn_value + mr_grn_value - st_out_value - rtv_value - cons_value - mr_out_value + sku_adj_value
        data_dict =  OrderedDict((
                                ('Plant Code', user.userprofile.stockone_code), ('SKU Code', sk),
                                ('Opening Qty', opening_qty), ('Opening Value', opening_value),
                                ('GRN Qty', po_grn_qty), ('GRN Value', po_grn_value),
                                ('RTV Qty', rtv_qty), ('RTV Value', rtv_value),
                                ('Adjustment Qty', sku_adj_qty), ('Adjustment Value', sku_adj_value),
                                ('Stock Transfer In Qty', st_grn_qty), ('Stock Transfer In Value', st_grn_value),
                                ('Stock Transfer Out Qty', st_out_qty), ('Stock Transfer Out Value', st_out_value),
                                ('MR In Qty', mr_grn_qty), ('MR In Value', mr_grn_value),
                                ('MR Out Qty', mr_out_qty), ('MR Out Value', mr_out_value),
                                ('MR Pending Qty', mr_pending_qty), ('MR Pending Value', mr_pending_value),
                                ('Closing Qty', mclosing_qty), ('Closing Value', mclosing_value),
                                ('Stock Qty', stock_qty), ('Stock Value', stock_value),
                                ('Consumption Qty', cons_qty), ('Consumption Value', cons_value),
                                ('Expected Closing Qty', exp_closing_qty), ('Expected Closing Value', exp_closing_val),
                        ))
        if (opening_qty+po_grn_qty+st_grn_qty+mr_grn_qty+mr_out_qty+stock_qty+mclosing_qty+mr_pending_qty+mr_grn_qty+mr_pending_value+sku_adj_qty):
            data_list.append(data_dict)
    return data_list

class Command(BaseCommand):
    help = "Stock Reconciliation for remaining"

    def handle(self, *args, **options):
        main_user = User.objects.get(username='mhl_admin')
        plant_users = get_related_users_filters(main_user.id, warehouse_types=['STORE', 'SUB_STORE'])[70:140]
        #plant_users = User.objects.filter(userprofile__stockone_code='27001')
        self.stdout.write("Started Reconciliation")
        main_user = User.objects.get(username='mhl_admin')
        current_date = datetime.datetime.now()
        if current_date.day < 7:
            start_day = (current_date-relativedelta(months=1)).replace(day=1).date()
            end_day = (start_day.replace(day=1) + relativedelta(months=1))
        else:
            start_day = current_date.replace(day=1).date()
            end_day = (current_date.replace(day=1) + relativedelta(months=1)).date()
        opening_date = start_day - datetime.timedelta(days=1)
        closing_date = start_day + relativedelta(months=1) - datetime.timedelta(days=1)
        data_list = []
        counter = 0
        log.info("Started Reconciliation for %s Plants" % str(plant_users.count()))
        for user in plant_users:
            counter += 1
            data_list = recon_calc(main_user, user, data_list, opening_date, closing_date, start_day, end_day)
            log.info("Ended Reconciliation for %s and Counter %s" % (user.username, str(counter)))
        df = pd.DataFrame(data_list)
        df.to_csv('StockReconciliation2.csv', index=False)
        self.stdout.write("Completed Reconciliation")
