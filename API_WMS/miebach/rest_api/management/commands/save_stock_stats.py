from collections import OrderedDict
from django.core.management import BaseCommand
from django.db.models import Q, Sum
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
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
        self.stdout.write("Started Updating")
        today = datetime.datetime.now().date()
        tomorrow = today + datetime.timedelta(1)
        today_start = datetime.datetime.combine(today, datetime.time())
        today_end = datetime.datetime.combine(tomorrow, datetime.time())
        updated_users = SKUDetailStats.objects.filter(creation_date__startswith=today).\
                                                values_list('sku__user', flat=True)
        users = User.objects.filter(id__in=updated_users)
        for user in users:
            print str(datetime.datetime.now())
            print get_local_date(user, datetime.datetime.now())
            log.info(get_local_date(user, datetime.datetime.now()))
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
            adjust_objs = dict(all_sku_stats.filter(transact_type='inventory-adjustment').\
                                                values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
            return_objs = dict(all_sku_stats.filter(transact_type='return').\
                                                values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
            jo_putaway_objs = dict(all_sku_stats.filter(transact_type='jo').\
                                                values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
            rm_picklist_objs = dict(all_sku_stats.filter(transact_type='rm_picklist').\
                                                values_list('sku_id').distinct().annotate(quantity=Sum('quantity')))
            for sku in sku_codes:
                putaway_quantity = putaway_objs.get(sku['sku_id'], 0)
                uploaded_quantity = stock_uploaded_objs.get(sku['sku_id'], 0)
                stock_quantity = stock_objs.get(sku['sku_id'], 0)
                return_quantity = return_objs.get(sku['sku_id'], 0)
                adjusted = adjust_objs.get(sku['sku_id'], 0)
                dispatched = market_data.get(sku['sku_id'], 0)
                produced_quantity = jo_putaway_objs.get(sku['sku_id'], 0)
                consumed = rm_picklist_objs.get(sku['sku_id'], 0)
                openinig_stock = (stock_quantity - putaway_quantity - uploaded_quantity - \
                                    return_quantity - produced_quantity) + (dispatched + consumed - adjusted)

                stock_stat = StockStats.objects.filter(sku_id=sku['sku_id'], creation_date__startswith=today)
                data_dict = {'opening_stock': openinig_stock, 'receipt_qty': putaway_quantity,
                             'uploaded_qty': uploaded_quantity, 'produced_qty': produced_quantity,
                             'dispatch_qty': dispatched, 'return_qty': return_quantity,
                             'adjustment_qty': adjusted, 'closing_stock': stock_quantity,
                              'uploaded_qty': uploaded_quantity, 'consumed_qty': consumed,
                              'creation_date': today
                             }
                if not stock_stat:
                    data_dict['sku_id'] = sku['sku_id']
                    stock_stat = StockStats.objects.create(**data_dict)
                    stock_stat.creation_date = today
                    stock_stat.save()
                else:
                    stock_stat.update(**data_dict)
            log.info("Updated the Stock Stats for the following users %s" % user.username)
        self.stdout.write("Updating Completed")
