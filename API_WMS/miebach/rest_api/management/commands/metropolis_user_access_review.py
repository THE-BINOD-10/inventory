from django.core.management import BaseCommand
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
from rest_api.views.inbound import sendMailforPendingPO
import datetime
from rest_api.views.mail_server import send_mail

def init_logger(log_file):
    log = logging.getLogger(log_file)
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    return log


log = init_logger('logs/metropolis_user_access_review.log')

class Command(BaseCommand):
    help = "Sending Pending Mails"
    def handle(self, *args, **options):
        self.stdout.write("Sending Mails")
        mailSub = 'User Access Review'
        Main_mid, Main_mid_table_mid = "", ""
        Main_head = "<p> Dear %s , </p>  \
            <p>Your are - <label style='color:forestgreen;'><b>%s</b></label> for below Plants</p>" %('nagi@mieone.com', 'ADMIN')
        Main_end = "<p>Below Staff Users are reporting to you, please reply - <label style='color: #ff6500;'>if any changes are required.</label></p>"
        all_plants = ['Metropolis Vidya Vihar', 'Thane CDC', 'Delhi', 'MumBai', 'Jaiput', 'Ranchi']
        Main_mid_table_head = "<table style='width:25%;'><tr><td><b>Plant Name</b></td></tr>"
        if len(all_plants) > 0:
            for pan in all_plants:
                Main_mid_table_mid = Main_mid_table_mid + "<tr><td>"+ pan +"</td></tr>"
        Main_mid_table_tail = "</table>"
        Main_mid = "%s%s%s" %(Main_mid_table_head, Main_mid_table_mid, Main_mid_table_tail)
        Main = "%s%s%s" %(Main_head, Main_mid, Main_end)
        Head = """
            <!DOCTYPE html>
            <html>
              <head>
                <meta charset="utf-8" />
                <style type="text/css">
                  table {
                    background: white;
                    border-radius:3px;
                    border-collapse: collapse;
                    height: auto;
                    max-width: 900px;
                    padding:5px;
                    width: 100%;
                    animation: float 5s infinite;
                  }
                  th {
                    color:#D5DDE5;;
                    background:#1b1e24;
                    border-bottom: 4px solid #9ea7af;
                    font-size:14px;
                    font-weight: 300;
                    padding:10px;
                    text-align:center;
                    vertical-align:middle;
                  }
                  tr {
                    border-top: 1px solid #C1C3D1;
                    border-bottom: 1px solid #C1C3D1;
                    border-left: 1px solid #C1C3D1;
                    color:#666B85;
                    font-size:16px;
                    font-weight:normal;
                  }
                  tr:hover td {
                    background:#faffee;
                    color:#0d0d0d;
                    border-top: 1px solid #22262e;
                  }
                  td {
                    background:#FFFFFF;
                    padding:10px;
                    text-align:left;
                    vertical-align:middle;
                    font-weight:300;
                    font-size:13px;
                    border-right: 1px solid #C1C3D1;
                  }
                </style>
              </head>
              <body>
                <table>
                  <thead>
                    <tr style="border: 1px solid #1b1e24;">
                      <th>Staff ID</th>
                      <th>Name</th>
                      <th>Email</th>
                      <th>Position</th>
                    </tr>
                  </thead>"""
        Tail = """</table>
                <br>
                Thank you!
              </body>
            </html>"""
        datas = [('IMP1', 'Sreekanth ME', 'sreekanth@mieone.com', 'Store Manager'), ('IMP2', 'avinash', 'avi@mieone.com', 'PR User')]
        Middle = ""
        for dat in datas:
            Mid = "<tbody><tr><td>"+str(dat[0])+"</td><td>"+str(dat[1])+"</td><td>"+str(dat[2])+"</td><td>"+str(dat[3])+"</td></tr></tbody>"
            Middle = Middle + Mid
        body = Main + Head + Middle +Tail
        # send_mail(['kaladhar@mieone.com'], mailSub, body, extra_mail='remainder')
        self.stdout.write("Updation Completed")
