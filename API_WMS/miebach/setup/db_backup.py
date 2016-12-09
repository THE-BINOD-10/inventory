#!/usr/bin/env python

from datetime import datetime
import sys, os, subprocess, tarfile
from ftp_file_upload import file_upload

class DBBackup:
    def __init__(self, dir_path):
        self.dir_path = dir_path
        self.settings_dir = os.path.join(self.dir_path, '../miebach/')
        sys.path.append(self.settings_dir)
        import settings
        self.default = settings.DATABASES['default']
        self.db_name = self.default['NAME']
        self.password = self.default['PASSWORD']

    def mysql_backup(self):
        bdate = datetime.now().strftime('%Y%m%d%H%M')
        bfile =  self.db_name+'_'+bdate+'.sql'
        dumpfile = open(os.path.join(self.dir_path, bfile), 'w')

        cmd = ['mysqldump', '--password='+self.password, self.db_name]
        p = subprocess.Popen(cmd, stdout=dumpfile)
        retcode = p.wait()
        dumpfile.close()
        if retcode > 0:
            print 'Error:', self.db_name, 'backup error'
        self.backup_compress(bfile)

    def backup_compress(self, bfile):
        tar_file_path = os.path.join(self.dir_path, bfile)+'.tar.gz'
        tar = tarfile.open(tar_file_path, 'w:gz')
        tar.add(os.path.join(self.dir_path, bfile), arcname=bfile)
        tar.close()
        os.remove(os.path.join(self.dir_path, bfile))
        status = file_upload(tar_file_path, '/WMS_SQL/', 'u121527.your-backup.de', 'u121527', 'g4ofUe6PdHJvAKMa', 1)


if __name__ == '__main__':
    args = sys.argv[1:]
    if args:
        dir_path = args[0]
        OBJ = DBBackup(dir_path)
        OBJ.mysql_backup()
    else:
        print 'Working directory is not defined'
