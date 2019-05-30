from django.core.management import BaseCommand
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
from rest_api.views.outbound import send_mail_enquiry_order_report
from rest_api.views.common import send_push_notification, get_priceband_admin_user
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


log = init_logger('logs/auto_expiry_cart_items.log')


class Command(BaseCommand):
    """
    Deleting Cart Items based on the creation_date
    """
    help = "Delete 3 days old Cart Items"

    def handle(self, *args, **options):
        self.stdout.write("Started Updating")
        today = datetime.datetime.now().date()
        three_days_old = today - datetime.timedelta(3)
        user = User.objects.filter(username = 'isprava_admin')
        today_deleted_items = CustomerCartData.objects.filter(creation_date__startswith=three_days_old, user_id = user[0].id)
        if today_deleted_items.exists():
            for notify_items in today_deleted_items:
                cont_vals = (notify_items.sku.sku_code)
                contents = {"en": "SKU %s has been removed from cart, since it extends 72 Hours" % cont_vals}
                users_list = [notify_items.customer_user.id]
                send_push_notification(contents, users_list)
            old_cart_items = today_deleted_items.values_list('id', 'user', 'customer_user')
            log.info("Deleted records in Customer Cart Data::%s" %(old_cart_items))
            log.info(today_deleted_items.delete())
        else:
            log.info("No Items to delete::%s" %(today))
        self.stdout.write("Updation Completed")