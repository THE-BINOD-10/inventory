from collections import OrderedDict
from django.core.management import BaseCommand
from django.db.models import Q, Sum
import os
import tarfile
import os.path
import logging
import django
import datetime
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from django.template import loader, Context
from django.db.models import F
from miebach_admin.models import *
from rest_api.views.mail_server import *
from rest_api.views.common import *
from rest_api.views.sendgrid_mail import *
from rest_api.views.reports import *



def init_logger(log_file):
    log = logging.getLogger(log_file)

    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    return log


log = init_logger('logs/Material_requirement_planning.log')


class Command(BaseCommand):
    """
    Loading the MRP Table
    """
    help = "Loading MRP Module"
    def handle(self, *args, **options):
        self.stdout.write("Script Started")
        mrp_objs = []
        user = User.objects.get(username='mhl_admin')
        if user.is_staff and user.userprofile.warehouse_type == 'ADMIN':
            users = get_related_users_filters(user.id, warehouse_types=['STORE', 'SUB_STORE'])
        else:
            req_users = [user.id]
            users = check_and_get_plants(request, req_users)
            users = users.filter(userprofile__warehouse_type__in=['STORE', 'SUB_STORE'])
        user_ids = list(users.values_list('id', flat=True))
        search_params = {'user__in': user_ids}
        main_user = get_company_admin_user(user)
        kandc_skus = list(SKUMaster.objects.filter(user=main_user.id).exclude(id__in=AssetMaster.objects.all()).exclude(id__in=ServiceMaster.objects.all()).\
                                            exclude(id__in=OtherItemsMaster.objects.all()).exclude(id__in=TestMaster.objects.all()).values_list('sku_code', flat=True))
        search_params['sku_code__in'] = kandc_skus
        master_data = SKUMaster.objects.filter(**search_params)
        res_plants = set()
        sku_codes = []
        for dat in master_data:
            res_plants.add(dat.user)
            sku_codes.append(dat.sku_code)
        usernames = list(User.objects.filter(id__in=res_plants).values_list('username', flat=True))
        dept_users = get_related_users_filters(user.id, warehouse_types=['DEPT'], warehouse=usernames, send_parent=True)
        dept_user_ids = list(dept_users.values_list('id', flat=True))
        stocks = StockDetail.objects.filter(sku__user__in=dept_user_ids, sku__sku_code__in=sku_codes, quantity__gt=0).\
                                                values('sku__user', 'sku__sku_code').distinct().annotate(total=Sum('quantity'))
        stock_qtys = {}
        user_id_mapping = {}
        for stock in stocks:
            if stock['sku__user'] in user_id_mapping:
                usr = user_id_mapping[stock['sku__user']]
            else:
                usr = User.objects.get(id=stock['sku__user'])
                if usr.userprofile.warehouse_type == 'DEPT':
                    usr = get_admin(usr)
                user_id_mapping[stock['sku__user']] = usr
            grp_key = (usr.id, stock['sku__sku_code'])
            stock_qtys.setdefault(grp_key, 0)
            stock_qtys[grp_key] += stock['total']
        consumption_qtys = {}
        consumption_lt3 = get_last_three_months_consumption(filters={'sku__user__in': dept_user_ids, 'sku__sku_code__in': sku_codes})
        for cons in consumption_lt3:
            if cons.sku.user in user_id_mapping:
                usr = user_id_mapping[cons.sku.user]
            else:
                usr = User.objects.get(id=cons.sku.user)
                if usr.userprofile.warehouse_type == 'DEPT':
                    usr = get_admin(usr)
                user_id_mapping[cons.sku.user] = usr
            grp_key = (usr.id, cons.sku.sku_code)
            consumption_qtys.setdefault(grp_key, 0)
            consumption_qtys[grp_key] += cons.quantity
        repl_master = ReplenushmentMaster.objects.filter(user__in=dept_user_ids, sku__sku_code__in=sku_codes)
        repl_dict = {}
        for dat in repl_master:
            grp_key = (dat.user.id, dat.sku.sku_code)
            repl_dict.setdefault(grp_key, {})
            repl_dict[grp_key]['lead_time'] = dat.lead_time
            repl_dict[grp_key]['min_days'] = dat.min_days
            repl_dict[grp_key]['max_days'] = dat.max_days
        pr_pending = PendingLineItems.objects.filter(sku__user__in=dept_user_ids, sku__sku_code__in=sku_codes, pending_pr__final_status__in=['pending', 'approved'])
        pending_pr_dict = {}
        for pr_pend in pr_pending:
            if pr_pend.sku.user in user_id_mapping:
                pr_user = user_id_mapping[pr_pend.sku.user]
            else:
                pr_user = User.objects.get(id=pr_pend.sku.user)
                if pr_user.userprofile.warehouse_type == 'DEPT':
                    pr_user = get_admin(pr_user)
                user_id_mapping[pr_pend.sku.user] = pr_user
            grp_key = (pr_user.id, pr_pend.sku.sku_code)
            pending_pr_dict.setdefault(grp_key, {'qty': 0})
            pending_pr_dict[grp_key]['qty'] += pr_pend.quantity
        po_pending = PendingLineItems.objects.filter(sku__user__in=dept_user_ids, sku__sku_code__in=sku_codes,
                                                    pending_po__final_status__in=['saved', 'pending', 'approved'],
                                                    pending_po__open_po__purchaseorder__isnull=True).distinct()
        pending_po_dict = {}
        for po_pend in po_pending:
            if po_pend.sku.user in user_id_mapping:
                po_user = user_id_mapping[po_pend.sku.user]
            else:
                po_user = User.objects.get(id=po_pend.sku.user)
                if po_user.userprofile.warehouse_type == 'DEPT':
                    po_user = get_admin(po_user)
                user_id_mapping[po_pend.sku.user] = po_user
            grp_key = (po_user.id, po_pend.sku.sku_code)
            pending_po_dict.setdefault(grp_key, {'qty': 0})
            pending_po_dict[grp_key]['qty'] += po_pend.quantity
        purchase_orders = PurchaseOrder.objects.filter(open_po__sku__user__in=dept_user_ids, open_po__sku__sku_code__in=sku_codes,
                                                        open_po__order_quantity__gt=F('received_quantity')).\
                                                exclude(status__in=['location-assigned', 'confirmed-putaway', 'stock-transfer', 'deleted'])
        po_dict = {}
        for purchase_order in purchase_orders:
            grp_key = (purchase_order.open_po.sku.user, purchase_order.open_po.sku.sku_code)
            po_dict.setdefault(grp_key, {'qty': 0})
            po_dict[grp_key]['qty'] += (purchase_order.open_po.order_quantity - purchase_order.received_quantity)
        sku_uoms = get_uom_with_multi_skus(user, sku_codes, uom_type='purchase', uom='')
        for data in master_data:
            data_dict = {}
            uom_dict = sku_uoms.get(data.sku_code, {})
            sku_pcf = uom_dict.get('sku_conversion', 1)
            sku_pcf = sku_pcf if sku_pcf else 1
            user = User.objects.get(id=data.user)
            grp_key = (data.user, data.sku_code)
            cons_qtybm = consumption_qtys.get(grp_key, 0)/3
            cons_qtypd = (cons_qtybm/30)
            cons_qty = round(cons_qtypd/sku_pcf, 5)
            sku_repl = repl_dict.get(grp_key, {})
            lead_time = round(cons_qty * sku_repl.get('lead_time', 0), 2)
            min_days = round(cons_qty * sku_repl.get('min_days', 0),2)
            max_days = round(cons_qty * sku_repl.get('max_days', 0), 2)
            stock_qty = round((stock_qtys.get(grp_key, 0))/sku_pcf, 2)
            sku_pending_pr = pending_pr_dict.get(grp_key, {}).get('qty', 0)
            sku_pending_po = pending_po_dict.get(grp_key, {}).get('qty', 0) + po_dict.get(grp_key, {}).get('qty', 0)
            total_stock = stock_qty + sku_pending_pr + sku_pending_po
            total_stock = round(total_stock, 2)
            if (total_stock - lead_time) > min_days:
                suggested_qty = 0
            else:
                suggested_qty = (max_days + lead_time - total_stock)
                suggested_qty = math.ceil(suggested_qty)
            if suggested_qty > 0:
                data_dict = {
                            'sku': data,
                            'user': user,
                            'avg_sku_consumption_day': cons_qty,
                            'lead_time_qty': lead_time,
                            'min_days_qty': min_days,
                            'max_days_qty': max_days,
                            'system_stock_qty': stock_qty,
                            'pending_pr_qty': sku_pending_pr,
                            'pending_po_qty': sku_pending_po,
                            'total_stock_qty': total_stock,
                            'suggested_qty': suggested_qty
                }
                mrp_obj = MRP(**data_dict)
                mrp_objs.append(mrp_obj)
        if mrp_objs:
            MRP.objects.bulk_create(mrp_objs)
        self.stdout.write("Updating Completed")
