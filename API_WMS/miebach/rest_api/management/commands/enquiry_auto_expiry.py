from django.core.management import BaseCommand
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
from rest_api.views.outbound import send_mail_enquiry_order_report
from rest_api.views.common import send_push_notification, get_priceband_admin_user
from datetime import datetime


def init_logger(log_file):
    log = logging.getLogger(log_file)

    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    return log


log = init_logger('logs/auto_expiry_enq_orders.log')


class Command(BaseCommand):
    """
    Deleting Enquiry Orders based on the extend_date
    """
    help = "Delete 10 days old Enquiry Orders"

    def handle(self, *args, **options):
        self.stdout.write("Started Updating")
        items = []
        today_enqs = EnquiryMaster.objects.filter(extend_date=datetime.today().date())
        for today_enq in today_enqs:
            customer_details = {}
            enquiry_id = today_enq.enquiry_id
            user_id = today_enq.user
            user = User.objects.filter(id=user_id)
            if user:
                user = user[0]
            else:
                continue
            admin_user = get_priceband_admin_user(user)
            res_user_id = CustomerUserMapping.objects.get(customer_id=today_enq.customer_id).user_id
            customer_details['email_id'] = today_enq.email_id
            customer_details['customer_name'] = today_enq.customer_name
            enquired_sku_list = today_enq.enquiredsku_set.values()
            for enq_sku in enquired_sku_list:
                style_name = enq_sku['title']
                qty = enq_sku['quantity']
                tot_amt = enq_sku['invoice_amount']
                items.append([style_name, qty, tot_amt])
            cont_vals = (enquiry_id, customer_details['customer_name'])
            contents = {"en": "Enquiry Order %s placed by %s will expire today EOD" % cont_vals}
            users_list = [res_user_id, user.id, admin_user.id]
            send_push_notification(contents, users_list)
            send_mail_enquiry_order_report(items, enquiry_id, user, customer_details, is_expiry=True)

        old_enqs = EnquiryMaster.objects.filter(extend_date__lt=datetime.today().date())
        old_enq_ids = old_enqs.values_list('enquiry_id', 'user', 'customer_name')
        log.info("Deleted records in Enquiry Master::%s" %(old_enq_ids))
        log.info(old_enqs.delete())