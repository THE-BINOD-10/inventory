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
from rest_api.views.sendgrid_mail import send_sendgrid_mail
from rest_api.views.mail_server import send_mail, send_mail_attachment


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
host = 'http://95.216.96.177:7023'


def generate_mrp_main(user, run_user_ids=None, run_sku_codes=None,  is_autorun=False, sub_user=None):
    mrp_objs = []
    if not run_user_ids:
        user = User.objects.get(username='mhl_admin')
        if user.is_staff and user.userprofile.warehouse_type == 'ADMIN':
            users = get_related_users_filters(user.id, warehouse_types=['DEPT'])
        else:
            req_users = [user.id]
            users = check_and_get_plants(request, req_users)
            users = users.filter(userprofile__warehouse_type__in=['DEPT'])
        plant_users = get_related_users_filters(user.id, warehouse_types=['STORE', 'SUB_STORE'])
        plant_user_names = list(plant_users.values_list('username', flat=True))
        plant_user_ids = list(plant_users.values_list('id', flat=True))
    else:
        users = User.objects.filter(id__in=run_user_ids, userprofile__warehouse_type__in=['DEPT'])
        plant_user_ids = []
        plant_user_names = []
        for user in users:
            if user.userprofile.warehouse_type == 'DEPT':
                temp_plant = get_admin(user)
                plant_user_ids.append(temp_plant.id)
                plant_user_names.append(temp_plant.username)
    plant_dept_user_ids = list(get_related_users_filters(user.id, warehouse_types=['DEPT'], warehouse=plant_user_names, send_parent=True).values_list('id', flat=True))
    user_ids = list(users.values_list('id', flat=True))
    search_params = {'user__in': user_ids}
    main_user = get_company_admin_user(user)
    mrp_pr_days = get_misc_value('mrp_pr_days', main_user.id)
    mrp_po_days = get_misc_value('mrp_po_days', main_user.id)
    if not run_sku_codes:
        kandc_skus = list(SKUMaster.objects.filter(user=main_user.id).exclude(id__in=AssetMaster.objects.all()).exclude(id__in=ServiceMaster.objects.all()).\
                                        exclude(id__in=OtherItemsMaster.objects.all()).exclude(id__in=TestMaster.objects.all()).values_list('sku_code', flat=True))
    else:
        kandc_skus = run_sku_codes
    search_params['sku_code__in'] = kandc_skus
    master_data = SKUMaster.objects.filter(**search_params)
    #res_plants = set()
    sku_codes = kandc_skus
    #for dat in master_data:
    #    res_plants.add(dat.user)
    #    sku_codes.append(dat.sku_code)
    usernames = list(User.objects.filter(id__in=user_ids).values_list('username', flat=True))
    #dept_users = get_related_users_filters(user.id, warehouse_types=['DEPT'], warehouse=usernames, send_parent=True)
    #dept_user_ids = list(dept_users.values_list('id', flat=True))
    dept_user_ids = user_ids
    repl_master = ReplenushmentMaster.objects.filter(user__in=dept_user_ids, sku__sku_code__in=sku_codes)
    repl_dict = {}
    repl_sku_codes = list(repl_master.values_list('sku__sku_code', flat=True))
    repl_sku_ids = list(repl_master.values_list('sku_id', flat=True))
    for dat in repl_master:
        grp_key = (dat.user.id, dat.sku.sku_code)
        repl_dict.setdefault(grp_key, {})
        repl_dict[grp_key]['lead_time'] = dat.lead_time
        repl_dict[grp_key]['min_days'] = dat.min_days
        repl_dict[grp_key]['max_days'] = dat.max_days
    print "Preparing repl dict completed"
    sku_codes = repl_sku_codes

    stocks = StockDetail.objects.filter(sku__user__in=dept_user_ids, sku_id__in=repl_sku_ids, quantity__gt=0).\
                                            values('sku__user', 'sku__sku_code').distinct().annotate(total=Sum('quantity'))
    stock_qtys = {}
    user_id_mapping = {}
    for stock in stocks:
        #if stock['sku__user'] in user_id_mapping:
        #    usr = user_id_mapping[stock['sku__user']]
        #else:
        #    usr = User.objects.get(id=stock['sku__user'])
        #    if usr.userprofile.warehouse_type == 'DEPT':
        #        usr = get_admin(usr)
        #    user_id_mapping[stock['sku__user']] = usr
        grp_key = (stock['sku__user'], stock['sku__sku_code'])
        stock_qtys.setdefault(grp_key, 0)
        stock_qtys[grp_key] += stock['total']
    print "Preparing stock dict completed"
    plant_stock_qtys = {}
    plant_stocks = StockDetail.objects.filter(sku__user__in=plant_user_ids, sku__sku_code__in=sku_codes, quantity__gt=0).\
                                                values('sku__user', 'sku__sku_code').distinct().annotate(total=Sum('quantity'))
    for plant_stock in plant_stocks:
        grp_key = (plant_stock['sku__user'], plant_stock['sku__sku_code'])
        plant_stock_qtys.setdefault(grp_key, 0)
        plant_stock_qtys[grp_key] += plant_stock['total']
    print "Preparing plant stock dict completed"
    consumption_qtys = {}
    plant_consumption_qtys = {}
    consumption_lt3 = get_last_three_months_consumption(filters={'sku__user__in': plant_dept_user_ids, 'sku__sku_code__in': sku_codes})
    plant_allde_mapping = {}
    for cons in consumption_lt3.only('sku__user', 'sku__sku_code', 'id', 'quantity'):
        print "Preparing Consumption: " + str(cons.id)
        cons_sku_user = cons.sku.user
        if cons.sku.user in user_id_mapping:
            usr = user_id_mapping[cons.sku.user]
        else:
            cons_usr = User.objects.get(id=cons.sku.user)
            if cons_usr.userprofile.warehouse_type == 'DEPT':
                usr = get_admin(cons_usr)
            else:
                usr = cons_usr
            user_id_mapping[cons.sku.user] = usr
        if cons_usr.userprofile.warehouse_type in ['STORE', 'SUB_STORE']:
            if cons_usr.id in plant_allde_mapping:
                cons_sku_user = plant_allde_mapping[cons_usr.id]
            else:
                allde_users = get_related_users_filters(user.id, warehouse_types=['DEPT'], warehouse=[usr.username]).filter(userprofile__stockone_code='ALLDE')
                if allde_users:
                    cons_sku_user = allde_users[0].id
                plant_allde_mapping[cons_usr.id] = cons_sku_user
        grp_key = (cons_sku_user, cons.sku.sku_code)
        consumption_qtys.setdefault(grp_key, 0)
        consumption_qtys[grp_key] += cons.quantity
        plant_grp = (usr.id, cons.sku.sku_code)
        plant_consumption_qtys.setdefault(plant_grp, 0)
        plant_consumption_qtys[plant_grp] += cons.quantity
    print "Preparing consumption dict completed"
    pr_pending_filter_dict = {'sku__user__in': dept_user_ids, 'sku_id__in': repl_sku_ids, 'pending_pr__final_status__in': ['pending', 'approved']}
    if mrp_pr_days not in ['false', '']:
        try:
            pr_pending_filter_dict['creation_date__gte'] = (datetime.datetime.now() - datetime.timedelta(float(mrp_pr_days))).date()
        except:
            pass
    pr_pending = PendingLineItems.objects.filter(**pr_pending_filter_dict)
    pending_pr_dict = {}
    for pr_pend in pr_pending:
        #if pr_pend.sku.user in user_id_mapping:
        #    pr_user = user_id_mapping[pr_pend.sku.user]
        #else:
        #    pr_user = User.objects.get(id=pr_pend.sku.user)
        #    if pr_user.userprofile.warehouse_type == 'DEPT':
        #        pr_user = get_admin(pr_user)
        #    user_id_mapping[pr_pend.sku.user] = pr_user
        pr_user = User.objects.get(id=pr_pend.sku.user)
        grp_key = (pr_user.id, pr_pend.sku.sku_code)
        pending_pr_dict.setdefault(grp_key, {'qty': 0})
        pending_pr_dict[grp_key]['qty'] += pr_pend.quantity
    print "Preparing pr pending dict completed"
    po_pending_filter_dict = {'sku__user__in': plant_user_ids, 'sku__sku_code__in': sku_codes, 'pending_po__final_status__in': ['saved', 'pending', 'approved']}
    if mrp_po_days not in ['false', '']:
        try:
            po_pending_filter_dict['creation_date__gte'] = (datetime.datetime.now() - datetime.timedelta(float(mrp_po_days))).date()
        except:
            pass

    po_pending = PendingLineItems.objects.filter(**po_pending_filter_dict).only('id', 'sku', 'quantity', 'pending_po__open_po_id', 'pending_po__pending_prs__wh_user_id')
                                                #pending_po__open_po__purchaseorder__isnull=True).only('id', 'sku', 'quantity')
    pending_po_dict = {}
    po_pending_open_po_ids = list(po_pending.values_list('pending_po__open_po_id', flat=True))
    po_raised_open_po_ids = list(PurchaseOrder.objects.filter(open_po_id__in=po_pending_open_po_ids).values_list('open_po_id', flat=True))
    for po_pend in po_pending.iterator():
        print 'preparing po pending: ' + str(po_pend.id)
        if po_pend.pending_po.open_po_id in po_raised_open_po_ids:
            continue
        pending_pr = po_pend.pending_po.pending_prs.filter()
        if not pending_pr:
            continue
        pending_pr = pending_pr[0]
        '''if po_pend.sku.user in user_id_mapping:
            po_user = user_id_mapping[po_pend.sku.user]
        else:
            po_user = User.objects.get(id=po_pend.sku.user)
            #if po_user.userprofile.warehouse_type == 'DEPT':
            #    po_user = get_admin(po_user)
            user_id_mapping[po_pend.sku.user] = po_user'''
        grp_key = (pending_pr.wh_user_id, po_pend.sku.sku_code)
        pending_po_dict.setdefault(grp_key, {'qty': 0})
        pending_po_dict[grp_key]['qty'] += po_pend.quantity
    print "Preparing po pending dict completed"
    po_filter_dict = {}
    if mrp_po_days not in ['false', '']:
        try:
            po_filter_dict['creation_date__gte'] = (datetime.datetime.now() - datetime.timedelta(float(mrp_po_days))).date()
        except:
            pass
    purchase_orders = PurchaseOrder.objects.filter(open_po__sku__user__in=plant_user_ids , open_po__sku__sku_code__in=sku_codes,
                                                    open_po__order_quantity__gt=F('received_quantity'), **po_filter_dict).\
                                            exclude(status__in=['location-assigned', 'confirmed-putaway', 'stock-transfer', 'deleted']).\
                                            only('id', 'po_number', 'open_po__sku__sku_code', 'open_po__order_quantity', 'received_quantity')
    po_dict = {}
    for purchase_order in purchase_orders:
        print 'preparing purchase order: ' + str(purchase_order.id)
        p_pos = PendingPO.objects.filter(full_po_number=purchase_order.po_number)
        if p_pos.exists():
            p_prs = p_pos[0].pending_prs.filter()
            if p_prs:
                p_prs_user = p_prs[0].wh_user
                grp_key = (p_prs_user.id, purchase_order.open_po.sku.sku_code)
                po_dict.setdefault(grp_key, {'qty': 0})
                po_dict[grp_key]['qty'] += (purchase_order.open_po.order_quantity - purchase_order.received_quantity)
    sku_supp_details = dict(SKUSupplier.objects.filter(sku__sku_code__in=sku_codes, sku__user__in=plant_user_ids).order_by('-price').\
                                    annotate(grp_key=Concat('sku__user', Value('<<>>'), 'sku__sku_code', output_field=CharField()),
                                    grp_val=Concat('supplier_id', Value('<<>>'), 'price', output_field=CharField())).values_list('grp_key', 'grp_val'))
    print "Preparing purchase order dict completed"
    sku_uoms = get_uom_with_multi_skus(user, sku_codes, uom_type='purchase', uom='')
    MRP.objects.filter(user__in=dept_user_ids, status=1, sku__sku_code__in=sku_codes).update(status=0)
    master_data = master_data.filter(id__in=repl_sku_ids).only('id', 'sku_code', 'user')
    plant_dept = {}
    transact_number = ''
    usr_id_obj_mapping = {}
    for data in master_data.iterator():
        print 'preparing MRP data for creation: ' + str(data.id)
        usr_obj_che = usr_id_obj_mapping.get(data.user)
        if usr_obj_che :
            user = usr_obj_che
        else:
            user = User.objects.get(id=data.user)
            usr_id_obj_mapping[data.user] = user
        if data.user in plant_dept.keys():
            plant_usr = plant_dept[data.user]
        else:
            plant_usr = get_admin(user)
        plant_usr_id = plant_usr.id
        data_dict = {}
        uom_dict = sku_uoms.get(data.sku_code, {})
        sku_pcf = uom_dict.get('sku_conversion', 1)
        sku_pcf = sku_pcf if sku_pcf else 1
        grp_key = (data.user, data.sku_code)
        plant_grp_key = (plant_usr_id, data.sku_code)
        cons_qtybm = consumption_qtys.get(grp_key, 0)/3
        cons_qtypd = (cons_qtybm/30)
        cons_qty = round(cons_qtypd/sku_pcf, 5)
        plant_cons_qtybm = plant_consumption_qtys.get(plant_grp_key, 0)/3
        plant_cons_qtypd = (plant_cons_qtybm/30)
        plant_cons_qty = round(plant_cons_qtypd/sku_pcf, 5)
        sku_repl = repl_dict.get(grp_key, {})
        lead_time = round(cons_qty * sku_repl.get('lead_time', 0), 5)
        min_days = round(cons_qty * sku_repl.get('min_days', 0),5)
        max_days = round(cons_qty * sku_repl.get('max_days', 0), 5)
        stock_qty = round((stock_qtys.get(grp_key, 0))/sku_pcf, 5)
        plant_stock_qty = 0
        if plant_cons_qty:
            plant_stock_qty = round((plant_stock_qtys.get(plant_grp_key, 0) * (cons_qty/plant_cons_qty))/sku_pcf, 5)
        sku_pending_pr = pending_pr_dict.get(grp_key, {}).get('qty', 0)
        sku_pending_po = pending_po_dict.get(grp_key, {}).get('qty', 0) + po_dict.get(grp_key, {}).get('qty', 0)
        total_stock = stock_qty + sku_pending_pr + sku_pending_po + plant_stock_qty
        total_stock = round(total_stock, 5)
        if (total_stock - lead_time) > min_days:
            suggested_qty = 0
        else:
            suggested_qty = (max_days + lead_time - total_stock)
            suggested_qty = math.ceil(suggested_qty)
        if True:#suggested_qty > 0:
            if not transact_number:
                transact_number = datetime.datetime.now().strftime('%Y%m%d') + '-' + str(get_incremental_with_lock(main_user, 'mrp_run', default_val=1)).zfill(3)
            supp_details = sku_supp_details.get(str(plant_usr_id)+'<<>>'+data.sku_code)
            #supp_details = get_sku_supplier_data_suggestions(data.sku_code, plant_usr, qty='')
            supplier_id, amount = '', 0
            if sku_supp_details.get(str(plant_usr_id)+'<<>>'+data.sku_code):
                sku_supp_obj = sku_supp_details.get(str(plant_usr_id)+'<<>>'+data.sku_code)
                supplier_id = sku_supp_obj.split('<<>>')[0]
                amount = suggested_qty * float(sku_supp_obj.split('<<>>')[1])
            data_dict = {
                        'transact_number': transact_number,
                        'sku': data,
                        'user': user,
                        'avg_sku_consumption_day': cons_qty,
                        'avg_plant_sku_consumption_day': plant_cons_qty,
                        'lead_time_qty': lead_time,
                        'min_days_qty': min_days,
                        'max_days_qty': max_days,
                        'system_stock_qty': stock_qty,
                        'plant_stock_qty': plant_stock_qty,
                        'pending_pr_qty': sku_pending_pr,
                        'pending_po_qty': sku_pending_po,
                        'total_stock_qty': total_stock,
                        'suggested_qty': suggested_qty,
                        'supplier_id': supplier_id,
                        'amount': amount,
                        'status': 1
            }
            mrp_obj = MRP(**data_dict)
            mrp_objs.append(mrp_obj)
    if mrp_objs:
        bulk_create_in_batches(MRP, mrp_objs)
        #MRP.objects.bulk_create(mrp_objs)
    if is_autorun:
        mrp_objs = MRP.objects.filter(user__in=dept_user_ids, status=1).values('user').annotate(Count('id'))
        for mrp_obj in mrp_objs:
            user_obj = User.objects.get(id=mrp_obj['user'])
            plant = get_admin(user_obj)
            plant_code = plant.userprofile.stockone_code
            email_subject = "Material Planning generated for Plant: %s, Department: %s" % (plant_code, user_obj.first_name)
            url = '%s/#/inbound/MaterialPlanning?plant_code=%s&dept_type=%s' % (host, plant_code, user_obj.userprofile.stockone_code)
            email_body = 'Hi Team,<br><br>Material Planning data is generated successfully for Plant: %s, Department: %s.<br><br>Please Click on the below link to view the data.<br><br>%s' % (plant_code, user_obj.first_name, url)
            #emails = StaffMaster.objects.filter(plant__name=plant.username, department_type__name=user_obj.userprofile.stockone_code, position='PR User', mrp_user=True).values_list('email_id', flat=True)
            repl_obj = ReplenushmentMaster.objects.filter(user=user_obj.id).first()
            emails = []
            if repl_obj:
                emails = [repl_obj.mrp_receiver]
            if len(emails) > 0:
                emails.extend(['sreekanth@mieone.com', 'pradeep@mieone.com', 'kaladhar@mieone.com'])
            send_sendgrid_mail('', user, 'mhl_mail@stockone.in', emails, email_subject, email_body, files=[])
            # send_sendgrid_mail('mhl_mail@stockone.in', ['sreekanth@mieone.com', 'pradeep@mieone.com', 'kaladhar@mieone.com'], email_subject, email_body, files=[])
    if sub_user:
        url = '%s/#/inbound/MaterialPlanning' % (host)
        email_subject = "Material Planning Generated Successfully"
        email_body = 'Hi Team,<br><br>Material Planning data is generated successfully.<br><br>Please Click on the below link to view the data.<br><br>%s' % (url)
        emails = [sub_user.email]
        send_sendgrid_mail('', user, 'mhl_mail@stockone.in', emails, email_subject, email_body, files=[])

class Command(BaseCommand):
    """
    Loading the MRP Table
    """
    help = "Loading MRP Module"
    def handle(self, *args, **options):
        self.stdout.write("Script Started")
        user = User.objects.get(username='mhl_admin')
        try:
            generate_mrp_main(user, is_autorun=True)
        except Exception as e: 
            import traceback
            log.debug(traceback.format_exc())
            log.info("Generate MRP run failed for params  on " + \
                     str(get_local_date(user, datetime.datetime.now())) + "and error statement is " + str(e))
        self.stdout.write("Script Completed")
