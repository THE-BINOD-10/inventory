from collections import OrderedDict
from django.core.management import BaseCommand
from django.db.models import Q, Sum
import os
import logging
import django
import datetime
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from django.template import loader, Context
from django.db.models import F
from miebach_admin.models import *
from rest_api.views.mail_server import send_mail
from rest_api.views.common import get_po_reference, get_local_date



def init_logger(log_file):
    log = logging.getLogger(log_file)

    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    return log


log = init_logger('logs/remainder_mails.log')


class Command(BaseCommand):
    """
    Sending Remainder Mails
    """
    help = "Send Remainder Mails everyday based on configuration"

    def handle(self, *args, **options):
        self.stdout.write("Started Checking")
        today = datetime.datetime.now()
        alert_users = User.objects.filter(mailalerts__alert_value__gt=0, mailalerts__alert_name='po_remainder')
        for user in alert_users:
            internal_mails = []
            internal_mail = MiscDetail.objects.filter(user=user.id, misc_type='Internal Emails')
            misc_internal_mail = MiscDetail.objects.filter(user=user.id, misc_type='internal_mail',
                                                           misc_value='true')
            if misc_internal_mail and internal_mail:
                internal_mail = internal_mail[0].misc_value.split(",")
                internal_mails.extend(internal_mail)
            company_name = user.userprofile.company_name
            if not company_name:
                company_name = user.username
            alert_duration = user.mailalerts_set.filter()[0].alert_value
            all_purchase_orders = PurchaseOrder.objects.exclude(Q(status__in=['location-assigned', 'confirmed-putaway']) |
                                                            Q(open_po__supplier__email_id='')). \
                                                    filter(open_po__sku__user=user.id,
                                                           received_quantity__lt=F('open_po__order_quantity'))
            order_ids = all_purchase_orders.values_list('order_id', flat=True).distinct()
            for order_id in order_ids:
                purchase_orders = all_purchase_orders.filter(order_id=order_id)
                purchase_order = purchase_orders[0]
                client_name = ''
                order_mapping = OrderMapping.objects.filter(mapping_id=purchase_order.order_id,\
                                                     mapping_type='PO')
                if order_mapping:
                    order_mapping = order_mapping[0]
                    client_name = order_mapping.order.customerordersummary_set.values_list('client_name', flat=True)[0]
                if purchase_order.remainder_mail:
                    alert_duration = int(purchase_order.remainder_mail)
                time_diff = (today - purchase_order.creation_date.replace(tzinfo=None)).days
                if (time_diff % alert_duration) == 0:
                    supplier = purchase_order.open_po.supplier
                    po_reference = get_po_reference(purchase_order)
                    ordered_date = get_local_date(user, purchase_order.creation_date)
                    mail_subject_line = "Please find below details of PO Number: %s, raised on %s. Please update status\
                     and expected delivery date of the same" % (po_reference, ordered_date)
                    if purchase_order.open_po.order_type == 'SP':
                        mail_subject_line = "Please find below, the sample's ordered on %s. Since the due date\
                            for these samples have expired, kindly return the same ASAP." % (ordered_date)
                    item_list = []
                    headers = ['SKU Code', 'Description', 'Quantity']
                    for order in purchase_orders:
                        quantity = int(order.open_po.order_quantity) - int(order.intransit_quantity) -\
                                    int(order.received_quantity)
                        item_list.append(OrderedDict((('sku_code', order.open_po.sku.sku_code),
                                                      ('sku_desc', order.open_po.sku.sku_desc),
                                                      ('quantity', quantity)
                                                    )))

                    self.mail_subject = 'PO Remainder for %s Purchase Order : %s' % (company_name, po_reference)
                    self.data_dict = {'supplier_name': supplier.name, 'mail_subject_line': mail_subject_line,
                                      'item_list': item_list, 'headers': headers, 'client_name': client_name}
                    self.receiver_list = [supplier.email_id]
                    self.receiver_list.extend(internal_mails)
                    self.prepare_and_send_mail()
        self.stdout.write("Updating Completed")

    def prepare_and_send_mail(self):
        t = loader.get_template('templates/remainder_mails/po_remainder.html')
        rendered = t.render(self.data_dict)
        send_mail(self.receiver_list, self.mail_subject, rendered)
        log.info(self.mail_subject)
