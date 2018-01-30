from django.core.management import BaseCommand
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
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
        old_enqs = EnquiryMaster.objects.filter(extend_date__lt=datetime.today().date())
        old_enq_ids = old_enqs.values_list('enquiry_id', 'user', 'customer_name')
        log.info("Deleted records in Enquiry Master::%s" %(old_enq_ids))
        log.info(old_enqs.delete())