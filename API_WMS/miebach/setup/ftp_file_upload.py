#!/usr/bin/env python

import os
import ftplib
import traceback
from datetime import datetime, timedelta

def login_to_ftp_server(server, user_name, password):
    try:
        ftp = ftplib.FTP(server)
        ftp.login(user_name, password)
    except:
        print traceback.print_exc()

    return ftp


def remove_old_files(ftp, backup_days):
    old_date = (datetime.now() - timedelta(days=backup_days)).strftime('%Y%m%d')

    try:
        for f_name in ftp.nlst():
            if old_date in f_name:
                ftp.delete(f_name)

    except ftplib.error_perm, resp:
        if str(resp) == "550 No files found":
            print "Empty Directory"


def file_upload(file_name, dest_dir, server, user_name, password, old_files, backup_days):
    status = 0

    ftp = login_to_ftp_server(server, user_name, password)
    try:
        if old_files:
            remove_old_files(ftp, backup_days)
        ftp.cwd(dest_dir)
        file_pointer = open(file_name, 'rb')
        f_name = os.path.basename(file_name)
        ftp.storbinary('STOR %s' % f_name, file_pointer)
        file_pointer.close()
        status = 1


    except:
        print traceback.print_exc()

    ftp.quit()

    return status
