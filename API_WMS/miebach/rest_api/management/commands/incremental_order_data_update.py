from django.core.management import BaseCommand
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
from operator import itemgetter
import operator
from django.db.models import Q, F, Value, FloatField, BooleanField, CharField
from rest_api.views.common import get_order_prefix, get_priceband_admin_user
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


log = init_logger('logs/incremental_order_data_update.log')


class Command(BaseCommand):
    """
    order_ids moved to incremental table...
    """
    help = "updating the order Ids in the incremental table."
    def handle(self, *args, **options):
        self.stdout.write("Started Updating")
        today = datetime.datetime.now().date()
        users = User.objects.filter(is_staff=True)
        except_cli = {}
        for user in users:
            print "-------------" + str(user.id) + "-------------"
            order_code = get_order_prefix(user.id)
            order_detail_id = OrderDetail.objects.filter(Q(order_code__in=\
                                                  [order_code, 'Delivery Challan', 'sample', 'R&D', 'CO','Pre Order']) |
                                                  reduce(operator.or_, (Q(order_code__icontains=x)\
                                                  for x in ['DC', 'PRE'])), user=user.id)\
                                                  .order_by("-creation_date")
            if order_detail_id:
                order_id = int(order_detail_id[0].order_id)
            else:
                order_id = 1001
            try:
                if order_id:
                    type_name = 'order'
                    IncrementalTable.objects.create(user_id=user.id, type_name=type_name, value=order_id)
            except Exception as e:
                except_cli[user.username] = order_id
            print str(order_code) + str(order_id)
        print except_cli
        self.stdout.write("Updation Completed")