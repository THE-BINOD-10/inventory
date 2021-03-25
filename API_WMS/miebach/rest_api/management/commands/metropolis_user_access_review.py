from django.core.management import BaseCommand
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
from rest_api.views.inbound import sendMailforPendingPO
import datetime
from rest_api.views.common import *
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
        ad_user = User.objects.get(username='mhl_admin')
        Main_end = "<p>Below Staff Users are reporting to you, please reply - <label style='color: #ff6500;'>if any changes are required.</label></p>"
        Main_mid_table_head = "<table style='width:25%;'><tr><td><b>Plant Name</b></td></tr>"
        all_staff = StaffMaster.objects.filter().exclude(status=0)
        unique_rm = list(all_staff.values_list('reportingto_email_id', flat=True).distinct())
        for reporting_manager in unique_rm[0:2]:
            print reporting_manager
            try:
                staff_d = all_staff.get(email_id=reporting_manager)
            except:
                print reporting_manager
                continue
            Main_head = "<p> Dear %s , </p>  \
                <p>Your Position - <label style='color:forestgreen;'><b>%s</b></label>" %(staff_d.staff_name, staff_d.position)
            stf_usrs = all_staff.filter(reportingto_email_id=reporting_manager)
            '''if len(all_plants) > 0:
                for pan in all_plants:
                    Main_mid_table_mid = Main_mid_table_mid + "<tr><td>"+ pan +"</td></tr>"'''
            #Main_mid_table_tail = "</table>"
            #Main_mid = "%s%s%s" %(Main_mid_table_head, Main_mid_table_mid, Main_mid_table_tail)
            Main = "%s%s" %(Main_head,Main_end)
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
                      <th>Plants</th>
                      <th>Departments</th>
                      <th>Groups</th>
                    </tr>
                  </thead>"""
            Tail_1 = "</table><br>"
            Tail_2 = "<a href='https://drive.google.com/file/d/1fy7-Gph9EBypFoIr5E0wgQqKElD9-YWX/view?usp=sharing'>Click here for More Information about Groups & Permissions</a><br>"
            Tail_3="Thank you!</body></html>"
            Tail = Tail_1 + Tail_2 + Tail_3
            Middle = ""
            linked_whs = get_related_users_filters(ad_user.id, send_parent=True)
            sub_user_id_list = []
            for linked_wh in linked_whs:
                sub_objs =  get_sub_users(linked_wh)
                sub_user_id_list = list(chain(sub_user_id_list, sub_objs.values_list('id', flat=True)))
            for staff in stf_usrs:
                group_names = []
                staff_list, dept_list = [], []
                plant, dept = '', ''
                split_by_own = ','
                staff_list = list(staff.plant.filter().values_list('name', flat=True))
                dms = list(staff.department_type.filter().values_list('name', flat=True))
                pms = list(User.objects.filter(username__in= staff_list).values_list('first_name', flat=True))
                plant = split_by_own.join(pms)
                dept = split_by_own.join(dms)
                if staff.user:
                    sub_user = User.objects.get(email=staff.email_id, id__in=sub_user_id_list)
                    sub_user_parent = get_sub_user_parent(sub_user)
                    company_id = get_company_id(ad_user)
                    roles_list = list(CompanyRoles.objects.filter(company_id=company_id).values_list('group__name', flat=True))
                    roles_list1 = copy.deepcopy(roles_list)
                    roles_list1 = list(chain(roles_list1, [sub_user_parent]))
                    user_groups = sub_user.groups.filter().exclude(name__in=roles_list1)
                    if user_groups:
                        for i in user_groups:
                            i_name = (i.name).replace(ad_user.username + ' ', '')
                            i_name = (i_name).replace(sub_user_parent.username + ' ', '')
                            group_names.append(i_name)
                group = split_by_own.join(group_names)
                Mid = "<tbody><tr><td>"+str(staff.staff_code)+"</td><td>"+str(staff.staff_name)+"</td><td>"+str(staff.email_id)+"</td><td>"+str(staff.position)+"</td><td>"+ plant +"</td><td>"+ dept +"</td><td>"+group+"</td></tr></tbody>"
                Middle = Middle + Mid
            body = Main + Head + Middle +Tail
            send_mail(['kaladhar@mieone.com'], mailSub, body, extra_mail='remainder')
        self.stdout.write("Updation Completed")
