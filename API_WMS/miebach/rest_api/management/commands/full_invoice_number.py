from django.core.management import BaseCommand
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
from rest_api.views.common import get_local_date, get_misc_value, get_full_invoice_number
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


log = init_logger('logs/full_invoice_number.log')


class Command(BaseCommand):
    """
    Updatingn the full invoice number in seller order Summary
    """
    help = "upating the Full Invoice number to all clients"

    def handle(self, *args, **options):
        self.stdout.write("Started Invoice number Updating")
        users = User.objects.filter(username = 'sagar_fab')
        today = datetime.datetime.now().date()
        financial_year = today - datetime.timedelta(422)
        # users = User.objects.filter(is_staff=True)
        for user in users:
            print user
            increment_invoice = get_misc_value('increment_invoice', user.id)
            userprofile = UserProfile.objects.filter(user_id=user.id)
            if userprofile:
                if userprofile[0].user_type == 'marketplace_user':
                    seller_orders = SellerOrderSummary.objects.filter(seller_order__order__user=user.id, full_invoice_number='', order__creation_date__gte=financial_year)
                else:
                    seller_orders = SellerOrderSummary.objects.filter(order__user=user.id, full_invoice_number='', order__creation_date__gte=financial_year)
                if seller_orders.exists():
                    for se_order in seller_orders:
                        if se_order.invoice_number and increment_invoice == 'true':
                            invoice_number = get_full_invoice_number(user, se_order.invoice_number, se_order.order, invoice_date='', pick_number='')
                            se_order.full_invoice_number = invoice_number
                            se_order.save()
                        elif increment_invoice == 'false':
                            invoice_number = get_full_invoice_number(user, se_order.order.order_id, se_order.order, invoice_date='', pick_number='')
                            se_order.full_invoice_number = invoice_number
                            se_order.save()
                else:
                    print 'No orders Found'
        self.stdout.write("Updation Completed")
