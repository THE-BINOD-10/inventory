from django.core.management import BaseCommand
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from django.http import HttpRequest
from miebach_admin.models import *
from rest_api.views.inbound import sendMailforPendingPO, create_mail_attachments
from rest_api.views.common import get_related_users_filters
from rest_api.views.sendgrid_mail import send_sendgrid_mail
from rest_api.views.reports import print_purchase_order_form
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


log = init_logger('logs/supplier_reminder_mails.log')

class Command(BaseCommand):
    help = "Sending Supplier Reminder Mails"
    def handle(self, *args, **options):
        self.stdout.write("Sending Mails")
        main_user = User.objects.get(username='mhl_admin')
        users = get_related_users_filters(main_user.id, warehouse_types=['STORE', 'SUB_STORE'])
        user_ids = list(users.values_list('id', flat=True))
        mailSub = 'Reminder for PO Number: '
        time_to_check = datetime.datetime.now() + datetime.timedelta(days=2)
        po_numbers = list(PurchaseOrder.objects.filter(status='', open_po__sku__user__in=user_ids, received_quantity=0).values_list('po_number', flat=True))
        pend_pos = list(PendingPO.objects.filter(full_po_number__in=po_numbers, delivery_date=time_to_check.date()).values_list('full_po_number', flat=True).distinct())
        for pend_po in pend_pos:
            po = PurchaseOrder.objects.filter(po_number=pend_po, open_po__sku__user__in=user_ids)[0]
            receivers = [po.open_po.supplier.email_id]
            user_id = po.open_po.sku.user
            internal_mail = MiscDetail.objects.filter(user=user_id, misc_type='Internal Emails')
            misc_internal_mail = MiscDetail.objects.filter(user=user_id, misc_type='internal_mail', misc_value='true')
            if misc_internal_mail and internal_mail:
                internal_mail = internal_mail[0].misc_value.split(",")
                receivers.extend(internal_mail)
            due_date = PendingPO.objects.filter(full_po_number=pend_po)[0].delivery_date.strftime('%d-%m-%Y')
            email_subject = mailSub + po.po_number
            email_body = 'Hi %s,<br><br>This is a gentle reminder about the due date of the PO no. %s.<br><br>The due date for the same is %s<br><br>Regards,<br>Procurement Team<br>Metropolis Healthcare Limited' % (po.open_po.supplier.name, po.po_number, due_date)
            request = HttpRequest()
            request.user = main_user
            request.GET['po_id'] = po.order_id
            request.GET['prefix'] = po.prefix
            request.GET['po_number'] = po.po_number
            request.META['SERVER_NAME'] = 'localhost'
            request.META['SERVER_PORT'] = '80'
            request.GET['for_mail'] = True
            res_data = print_purchase_order_form(request)
            attachments = create_mail_attachments(po.po_number, res_data.content)
            send_sendgrid_mail('mhl_mail@stockone.in', receivers, email_subject, email_body, files=attachments)
            log.info("Sending Mail for %s to %s" %(po.po_number, ','.join(receivers)))
        self.stdout.write("Updation Completed")
