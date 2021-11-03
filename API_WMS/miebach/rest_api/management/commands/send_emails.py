from django.core.management import BaseCommand
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
from rest_api.views.inbound import sendMailforPendingPO
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


log = init_logger('logs/send_metro_pending_mails.log')

class Command(BaseCommand):
    help = "Sending Pending Mails"
    def handle(self, *args, **options):
        self.stdout.write("Started Updating")
        self.stdout.write("Started Updating")
        baseLevel = 'level0'
        mailSub = 'pr_created'
        is_resubmitted = False
        urlPath = 'http://mi.stockone.in'
        today = datetime.datetime.now().date()
        six_days_old = today - datetime.timedelta(6)
        one_days_old = today - datetime.timedelta(1)
        pending_prs = PendingPR.objects.filter(creation_date__gt=six_days_old, creation_date__lt=one_days_old, pending_level='level0', final_status='pending')
        for pending_pr in pending_prs:
            user = pending_pr.wh_user
            hash_code = ''
            approval_mail_ref = pending_pr.pending_prApprovals.filter(level='level0', status='')[0]
            mailsList = list(pending_pr.pending_prApprovals.filter(level='level0', status='').values_list('validated_by', flat=True).distinct())
            mailsList = mailsList[0].split(',')
            if len(mailsList) > 0:
                for eachMail in mailsList:
                    approval_hash_codes = approval_mail_ref.purchaseapprovalmails_set.filter(email=eachMail)
                    if approval_hash_codes.exists():
                        hash_code = approval_hash_codes[0].hash_code
                        print pending_pr.id, user, baseLevel, mailSub, eachMail, urlPath, hash_code, is_resubmitted
                        print '------------------------------------------------------------------------------'
                        sendMailforPendingPO(pending_pr.id, user, baseLevel, mailSub, eachMail, urlPath, hash_code, poFor=False, is_resubmitted=is_resubmitted)
                        log.info("sending PR ::%s" %(pending_pr.id))
        self.stdout.write("Updation Completed")
