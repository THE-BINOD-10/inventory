#!/usr/bin/env python

from datetime import datetime
import sys, os, subprocess, tarfile
from ftp_file_upload import file_upload
from mail_server import *

class DBBackup:
    def __init__(self, dir_path):
        self.dir_path = dir_path
        self.settings_dir = os.path.join(self.dir_path, '../miebach/')
        sys.path.append(self.settings_dir)
        self.backup_path = "/root/DATA/hourly_backup/"
        import settings
        self.default = settings.DATABASES['default']
        self.db_name = self.default['NAME']
        self.password = self.default['PASSWORD']
        self.host = self.default.get('HOST', 'localhost')
        self.user = self.default['USER']

    def mysql_backup(self):
        bdate = datetime.now().strftime('%Y%m%d%H%M')
        bfile =  self.db_name+'_'+bdate+'.sql'
        dumpfile = open(os.path.join(self.backup_path, bfile), 'w')
        cmd = ['mysqldump', '--host='+self.host, '--user='+self.user, '--password='+self.password, self.db_name]
        p = subprocess.Popen(cmd, stdout=dumpfile)
        retcode = p.wait()
        dumpfile.close()
        if retcode > 0:
            print 'Error:', self.db_name, 'backup error'
            res = "Error"
            self.sending_mail(res)
        else:
            res = "success"
            self.sending_mail(res)
        self.backup_compress(bfile)

    def backup_compress(self, bfile):
        tar_file_path = os.path.join(self.backup_path, bfile)+'.tar.gz'
        tar = tarfile.open(tar_file_path, 'w:gz')
        tar.add(os.path.join(self.backup_path, bfile), arcname=bfile)
        tar.close()
        os.remove(os.path.join(self.backup_path, bfile))
        status = file_upload(tar_file_path, '/WMS_SQL/', 'u156461.your-backup.de', 'u156461', 'ZAl8lR76yJZ2pLSX', 1)
        if not status:
            self.sending_mail('Error')
        else:
            os.remove(tar_file_path)

    def sending_mail(self, res):
        if res == "success":
            subject = "DB Backup Successfull"
            body = "Hi Team, Backup is created successfully"

        else:
            subject = "Alert : DB backup Failed"
            body = "Hi Team, Backup creation is failed please check asap."

        send_to = ["wms-dev@mieone.com", "sai@mieone.com", "sreekanth@mieone.com"]
        #send_to = ["sreekanth@mieone.com"]
        send_mail(send_to, subject, body)


if __name__ == '__main__':
    args = sys.argv[1:]
    if args:
        dir_path = args[0]
        OBJ = DBBackup(dir_path)
        OBJ.mysql_backup()
    else:
        print 'Working directory is not defined'
