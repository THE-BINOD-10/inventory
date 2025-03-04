#!/usr/bin/env python

from datetime import datetime
import sys, os, subprocess, tarfile
from ftp_file_upload import file_upload
from mail_server import *

class DBBackup:
    def __init__(self, dir_path, running_type):
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
        self.running_type = running_type

    def mysql_backup(self):
        bdate = datetime.now().strftime('%Y%m%d%H%M')
        if self.running_type == 'hourly':
            bfile =  self.db_name+'_'+bdate+'.sql'
        else:
            bfile =  self.db_name+'_'+bdate+'_daily.sql'
        dumpfile = open(os.path.join(self.backup_path, bfile), 'w')
        cmd = ['mysqldump', '--host='+self.host, '--user='+self.user, '--password='+self.password, '--single-transaction=TRUE', '--quick', self.db_name]
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
        if self.running_type == 'hourly':
            status = file_upload(tar_file_path, '/WMS_SQL/', 'u156461.your-backup.de', 'u156461', 'ZAl8lR76yJZ2pLSX', 1, 3)
        else:
            status = file_upload(tar_file_path, '/METROPOLIS/', 'u239654.your-storagebox.de', 'u239654', 'jb6k87AIEzRBvI9u', 1, 28)
        if not status:
            self.sending_mail('Error')
        else:
            os.remove(tar_file_path)

    def sending_mail(self, res):
        if res == "success":
            subject = "Metropolis DB Backup Successfull"
            body = "Hi Team, Backup is created successfully"

        else:
            subject = "Alert : Metropolis DB backup Failed"
            body = "Hi Team, Backup creation is failed please check asap."

        send_to = ["avinash@mieone.com", "sreekanth@mieone.com", "avadhani@mieone.com", "kaladhar@mieone.com"]
        #send_to = ["sreekanth@mieone.com"]
        send_mail(send_to, subject, body)


if __name__ == '__main__':
    args = sys.argv[1:]
    if args:
        dir_path = args[0]
        running_type = args[1]
        OBJ = DBBackup(dir_path, running_type)
        OBJ.mysql_backup()
    else:
        print 'Working directory is not defined'
