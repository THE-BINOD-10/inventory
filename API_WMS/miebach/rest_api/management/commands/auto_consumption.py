"""
 Code for Auto Picklist generation and Confirmation
"""
from collections import OrderedDict
from django.core.management import BaseCommand
from django.db.models import Q, Sum
import os
import logging
import datetime
import copy
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from itertools import chain
from miebach_admin.models import *
from rest_api.views.common import reduce_conumption_stock
# from rest_api.views.common import get_exclude_zones, get_misc_value, get_picklist_number, \
#     get_sku_stock, get_stock_count, save_sku_stats, change_seller_stock, check_picklist_number_created, \
#     update_stocks_data, get_max_seller_transfer_id, get_financial_year, get_stock_receipt_number
# from rest_api.views.outbound import get_seller_pick_id
# from rest_api.views.miebach_utils import MILKBASKET_USERS, PICKLIST_FIELDS, ST_ORDER_FIELDS


def init_logger(log_file):
    log = logging.getLogger(log_file)

    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    return log


log = init_logger('logs/auto_consumption.log')

class Command(BaseCommand):
    """
    Auto Consume Stock
    """
    help = "Auto Consumption"
    def handle(self, *args, **options):
        self.stdout.write("Started Updating")
        consumptions = Consumption.objects.filter(status=1)
        reduce_conumption_stock(consumptions)
        log.info('Sale Cron Completed for at {}'.format(str(datetime.datetime.now())))
        self.stdout.write("Updating Completed")
