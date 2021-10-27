from django.core.management import BaseCommand
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
from rest_api.views.inbound import sendMailforPendingPO
import datetime
from django.db.models import Sum, F

def init_logger(log_file):
    log = logging.getLogger(log_file)
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    return log


log = init_logger('logs/send_daily_reminder_mails.log')

class Command(BaseCommand):
    help = "Sending Pending Mails"
    def handle(self, *args, **options):
        self.stdout.write("Sending Mails")
        mailSub = 'remainder_pr_created'
        is_resubmitted = False
        urlPath = 'http://mi.stockone.in'
        time_to_check = datetime.datetime.now() - datetime.timedelta(days=1)
        all_pending_approval_details = PurchaseApprovals.objects.filter(creation_date__lt=time_to_check, status__in=['', 'on_approved'], purchase_type='PR').exclude(status__in=['approved', 'resubmitted', 'rejected'])
        if all_pending_approval_details.exists():
            for record in all_pending_approval_details:
                mailSub = 'remainder_pr_created'
                pending_pr, user, baseLevel = ['']*3
                pending_pr = record.pending_pr
                qty = pending_pr.pending_prlineItems.aggregate(total_qty = Sum(F('quantity')))['total_qty']
                if not qty:
                    continue
                if record.status == 'on_approved':
                    mailSub = 'pr_approval_at_last_level'
                if pending_pr.final_status not in ['pr_converted_to_po', 'cancelled', 'rejected']:
                    user = record.pending_pr.wh_user
                    baseLevel = record.level
                    mails_to_send = record.purchaseapprovalmails_set.filter(status='')
                    if mails_to_send.exists():
                        for mail_rec in mails_to_send:
                            eachMail = ''
                            eachMail = mail_rec.email
                            hash_code = mail_rec.hash_code
                            print pending_pr.id, user, baseLevel, mailSub, eachMail, urlPath, hash_code, is_resubmitted
                            print '------------------------------------------------------------------------------'
                            sendMailforPendingPO(pending_pr.id, user, baseLevel, mailSub, eachMail, urlPath, hash_code, poFor=False, is_resubmitted=is_resubmitted)
                            log.info("sending PR ::%s%s" %(pending_pr.id, str(time_to_check)))
        self.stdout.write("Updation Completed")
