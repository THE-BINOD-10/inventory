"""
 Code for Milkbasket BA and SA Mail
"""
from collections import OrderedDict
from django.core.management import BaseCommand
from django.db.models import Q, Sum, F
import os
import logging
import copy
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from itertools import chain
from django.db.models import Count
from datetime import datetime, date, timedelta
from miebach_admin.models import *
from rest_api.views.common import get_sku_weight, get_all_sellable_zones, get_work_sheet
from rest_api.views.miebach_utils import MILKBASKET_USERS, fn_timer
from rest_api.views.mail_server import send_mail_attachment

def init_logger(log_file):
    log = logging.getLogger(log_file)
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    return log

log = init_logger('logs/milkbasket_central_report_mail.log')

ba_location = 'BA'

class Command(BaseCommand):
    help = "Milkbasket Central Reports Mail"

    def handle(self, *args, **options):
        self.stdout.write("Milkbasket Central Reports Script")

        def write_excel_col(ws, row_count, column_count, value):
            ws.write(row_count, column_count, value)
            column_count += 1
            return ws, column_count

        users = User.objects.filter(username__in=MILKBASKET_USERS)
        category_list = list(SKUMaster.objects.filter(user__in=users).exclude(sku_category='').\
                             values_list('sku_category', flat=True).distinct())
        inv_value_dict = OrderedDict()
        inv_value_headers = ['Category']
        user_mapping = dict(users.values_list('id', 'username'))
        inv_value_headers = list(chain(inv_value_headers, user_mapping.values()))
        try:
            wb, ws = get_work_sheet('central_inventory_value', inv_value_headers)
            file_name = '%s.%s' % ('central_inventory_value_report', 'xls')
            path = ('static/excel_files/%s') % file_name
            if not os.path.exists('static/excel_files/'):
                os.makedirs('static/excel_files/')
            for category in category_list:
                for user in users:
                    inv_value_dict.setdefault(category, {})
                    inv_value_dict[category].setdefault(int(user.id), 0)
                master_data = SellerStock.objects.filter(stock__sku__user__in=users, stock__sku__sku_category=category). \
                    exclude(stock__receipt_number=0). \
                    values('stock__sku__sku_category', 'stock__sku__user').distinct(). \
                    annotate(total_value=Sum(F('quantity') * F('stock__batch_detail__buy_price')))
                for data in master_data:
                    inv_value_dict[data['stock__sku__sku_category']][int(data['stock__sku__user'])] += data['total_value']
            row_count = 1
            for category, user_value in inv_value_dict.iteritems():
                ws, column_count = write_excel_col(ws, row_count, 0, category)
                for user, value in user_value.iteritems():
                    column_count = (user_mapping.keys().index(user)) + 1
                    value = float("%.2f" % value)
                    ws, column_count = write_excel_col(ws, row_count, column_count, value)
                row_count += 1
            wb.save(path)
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Milkbasket BA SA report creation failed for user %s and error statement is %s' %
                     (str(user.username), str(e)))