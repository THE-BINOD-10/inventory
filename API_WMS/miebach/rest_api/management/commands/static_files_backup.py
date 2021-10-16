from django.core.management import BaseCommand
import os,tarfile, shutil
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
import datetime
from datetime import timedelta, datetime
from django.contrib.sessions.models import Session
from oauth2_provider.models import *
from rest_api.views.ftp_file_upload import file_upload


def init_logger(log_file):
    log = logging.getLogger(log_file)

    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    return log


log = init_logger('logs/static_file.log')


class Command(BaseCommand):
    help = "Static FTP upload"
    def handle(self, *args, **options):

        def make_tarfile(output_filename, source_dir):
            with tarfile.open(output_filename, "w:gz") as tar:
                tar.add(source_dir, arcname=os.path.basename(source_dir))
        
        def sending_mail(res):
            if res == "success":
                subject = "Static File Backup Successfull"
                body = "Hi Team, Backup is created successfully"

            else:
                subject = "Alert : Static File backup Failed"
                body = "Hi Team, Backup creation is failed please check asap."

            send_to = ["kaladhar@mieone.com"]
            send_mail(send_to, subject, body)

    	dest_path = '/root/DATA/static_backup/'
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)
        bdate = datetime.now().strftime('%Y%m%d%H%M')
        bfile =  "static_"+bdate+'.tar.gz'
        tar_file_path = os.path.join(dest_path, bfile)
        try:
            source_path = dest_path+'static'
            if os.path.exists(source_path):
                shutil.rmtree(source_path)
            shutil.copytree('static', source_path)
            make_tarfile(tar_file_path, source_path)
            shutil.rmtree(source_path)
        except:
            sending_mail('Error')
            # print 'Fail'
        status = file_upload(tar_file_path, '/static_files/', 'u239654.your-storagebox.de', 'u239654', 'jb6k87AIEzRBvI9u', 0, 2)
        if not status:
            sending_mail('Error')
        else:
            os.remove(tar_file_path)
        log.info("Static files uploded %s" % bdate)
