from collections import OrderedDict
from django.core.management import BaseCommand
from django.db.models import Q, Sum, F
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
from rest_api.views.common import get_local_date, get_misc_value
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


log = init_logger('logs/stock_stats.log')


class Command(BaseCommand):
    """
    Deleting Enquiry Orders based on the extend_date
    """
    help = "Save Stock Stats everyday"

    def handle(self, *args, **options):
        users_list = []
        self.stdout.write("Started Updating")
        today = datetime.datetime.now().date()
        tomorrow = today + datetime.timedelta(1)
        today_start = datetime.datetime.combine(today, datetime.time())
        today_end = datetime.datetime.combine(tomorrow, datetime.time())
        print str(datetime.datetime.now())
        run_users = ['incnut','GGN01', 'ggn01_con','TranceHomeLinen', 'ola_admin', 'creation_overseas',
                    'savis_retail', 'GM_admin', 'grandspitstop', 'aidin_technologies']
        for username in run_users:
            user_objs = UserGroups.objects.filter(admin_user__username=username)
            users_list.append(username)
            for user_obj in user_objs:
                users_list.append(user_obj.user.username)
        users = User.objects.filter(is_staff=True).order_by('-last_login')
        for user in users:
            print user
            userprofile = UserProfile.objects.filter(user_id=user.id)
            if not userprofile.exists():
                continue
            non_transact_process = get_misc_value('non_transacted_skus', user.id)
            try:
                log.info(get_local_date(user, datetime.datetime.now()))
            except Exception as e:
                log.info(datetime.datetime.now())
            sku_obj = SKUMaster.objects.filter(user=user.id)
            for sku in sku_obj:
                if SKUDetailStats.objects.filter(creation_date__startswith=today, sku__user=user.id, sku_id=sku.id).exists():
                    all_sku_stats = SKUDetailStats.objects.filter(sku__user=user.id, creation_date__startswith = today)
                    sku_codes = all_sku_stats.order_by('sku__sku_code').\
                                                    values('sku_id', 'sku__sku_code', 'sku__sku_desc').distinct()
                    putaway_objs = dict(all_sku_stats.filter(transact_type='po').values_list('sku_id').distinct().\
                                                        annotate(quantity=Sum('quantity')))
                    stock_uploaded_objs = dict(all_sku_stats.filter(transact_type='inventory-upload').values_list('sku_id').\
                                               distinct().annotate(quantity=Sum('quantity')))
                    market_data = dict(all_sku_stats.filter(transact_type='picklist').\
                                                    values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
                    stock_objs = dict(StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values_list('sku_id').\
                                      distinct().annotate(in_stock=Sum('quantity')))
                    stock_value_objs = dict(StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values_list('sku_id').\
                                      distinct().annotate(stock_value=Sum(F('quantity') * F('sku__average_price'))))
                    adjust_objs = dict(all_sku_stats.filter(transact_type='inventory-adjustment').\
                                                        values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
                    return_objs = dict(all_sku_stats.filter(transact_type='return').\
                                                        values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
                    cancelled_objs = dict(all_sku_stats.filter(transact_type='cancelled_location').\
                                                        values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
                    jo_putaway_objs = dict(all_sku_stats.filter(transact_type='jo').\
                                                        values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
                    rm_picklist_objs = dict(all_sku_stats.filter(transact_type='rm_picklist').\
                                                        values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
                    rtv_objs = dict(all_sku_stats.filter(transact_type='rtv').\
                                                        values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
                    dest_substitute = dict(all_sku_stats.filter(transact_type='dest_substitute').\
                                                        values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
                    src_substitue = dict(all_sku_stats.filter(transact_type='src_substitute').\
                                                        values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
                    cancel_grn = dict(all_sku_stats.filter(transact_type='cancel-grn').\
                                                        values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
                    mr_picklist = dict(all_sku_stats.filter(transact_type='mr_picklist').\
                                                        values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
                    mr_po = dict(all_sku_stats.filter(transact_type='mr_po').\
                                                        values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
                    st_picklist = dict(all_sku_stats.filter(transact_type='st_picklist').\
                                                        values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
                    st_po = dict(all_sku_stats.filter(transact_type='st_po').\
                                                        values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
                    so_picklist = dict(all_sku_stats.filter(transact_type='so_picklist').\
                                                        values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
                    so_po = dict(all_sku_stats.filter(transact_type='so_po').\
                                                        values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))

                    putaway_quantity = putaway_objs.get(sku.id, 0)
                    uploaded_quantity = stock_uploaded_objs.get(sku.id, 0)
                    stock_quantity = stock_objs.get(sku.id, 0)
                    closing_stock_value = stock_value_objs.get(sku.id, 0)
                    return_quantity = return_objs.get(sku.id, 0)
                    cancelled_quantity = cancelled_objs.get(sku.id, 0)
                    adjusted = adjust_objs.get(sku.id, 0)
                    dispatched = market_data.get(sku.id, 0)
                    produced_quantity = jo_putaway_objs.get(sku.id, 0)
                    consumed = rm_picklist_objs.get(sku.id, 0)
                    dest_substitute_quantity = dest_substitute.get(sku.id, 0)
                    src_substitue_quantity = src_substitue.get(sku.id, 0)
                    cancel_grn_quantity = cancel_grn.get(sku.id, 0)
                    produced_quantity += dest_substitute_quantity
                    consumed += src_substitue_quantity
                    rtv_quantity = rtv_objs.get(sku.id,0)
                    mr_picklist_qty = mr_picklist.get(sku.id, 0)
                    mr_receipt_qty = mr_po.get(sku.id, 0)
                    st_picklist_qty = st_picklist.get(sku.id, 0)
                    st_receipt_qty = st_po.get(sku.id, 0)
                    so_picklist_qty = so_picklist.get(sku.id, 0)
                    so_receipt_qty = so_po.get(sku.id, 0)
                    # stock_stat_objects = StockStats.objects.filter(sku_id=sku.id, sku__user=user.id).order_by('-creation_date')
                    stock_stat_objects = StockStats.objects.filter(sku_id=sku.id, sku__user=user.id).exclude(creation_date__startswith=today)
                    if stock_stat_objects.exists():
                        lat_rec = stock_stat_objects.latest('creation_date')
                        openinig_stock = lat_rec.closing_stock
                        opening_stock_value = lat_rec.closing_stock_value
                    else:
                        openinig_stock = 0
                        opening_stock_value = 0
                    # openinig_stock = stock_quantity+rtv_quantity - (putaway_quantity + uploaded_quantity + return_quantity +\
                    #                                    produced_quantity) + (dispatched + consumed) - adjusted
                    stock_stat = StockStats.objects.filter(sku_id=sku.id, creation_date__startswith=today)
                    data_dict = {'opening_stock': openinig_stock, 'receipt_qty': putaway_quantity, 'opening_stock_value': opening_stock_value,
                                 'uploaded_qty': uploaded_quantity, 'produced_qty': produced_quantity, 'grn_cancelled_qty': cancel_grn_quantity,
                                 'dispatch_qty': dispatched, 'return_qty': return_quantity,'rtv_quantity':rtv_quantity,
                                 'adjustment_qty': adjusted, 'closing_stock': stock_quantity,'closing_stock_value': closing_stock_value,
                                  'uploaded_qty': uploaded_quantity, 'consumed_qty': consumed, 'cancelled_qty':cancelled_quantity,
                                  'mr_receipt_qty': mr_receipt_qty, 'mr_picklist_qty': mr_picklist_qty, 'st_receipt_qty': st_receipt_qty, 'st_picklist_qty': st_picklist_qty,
                                  'so_receipt_qty': so_receipt_qty, 'so_picklist_qty': so_picklist_qty,
                                  'creation_date': today
                                }
                    if not stock_stat:
                        data_dict['sku_id'] = sku.id
                        stock_stat = StockStats.objects.create(**data_dict)
                        stock_stat.creation_date = today
                        stock_stat.save()
                    else:
                        stock_stat.update(**data_dict)
                else:
                    if non_transact_process == 'true':
                        stock_stat = StockStats.objects.filter(sku_id=sku.id, creation_date__startswith=today)
                        current_stock =StockDetail.objects.filter(sku__user=user.id, quantity__gt=0, sku_id=sku.id).aggregate(Sum('quantity'), stock_value=Sum(F('quantity') * F('sku__average_price')))
                        stock_object = StockStats.objects.filter(sku_id=sku.id, sku__user=user.id).exclude(creation_date__startswith=today)
                        quantity = current_stock['quantity__sum']
                        closing_stock_value = current_stock['stock_value'] or 0
                        if not quantity:
                            quantity = 0
                        if stock_object.exists():
                            lat_re = stock_object.latest('creation_date')
                            data_dict = {'opening_stock': lat_re.closing_stock, 'closing_stock': quantity, 'sku_id':sku.id,
                                        'opening_stock_value': lat_re.closing_stock_value, 'closing_stock_value': closing_stock_value}
                            if stock_stat.exists():
                                stock_stat.update(**data_dict)
                            else:
                                StockStats.objects.create(**data_dict)
                        else:
                            data_dict = {'opening_stock': 0, 'closing_stock': quantity, 'sku_id':sku.id, 'closing_stock_value': closing_stock_value,
                                        'opening_stock_value': 0}
                            if stock_stat.exists():
                                stock_stat.update(**data_dict)
                            else:
                                StockStats.objects.create(**data_dict)
            log.info("Updated the Stock Stats for the following users %s" % user.username)
        self.stdout.write("Updating Completed")
