activate_this = 'setup/MIEBACH/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()

import sys
from miebach_admin.models import *
from datetime import datetime, date, timedelta
from django.db.models import Sum
from xlwt import Workbook
import json

from dict_to_txt import text_file_creator

def get_user_customer_data(user):
   user = User.objects.get(id=user)
   total_data = []
   master_data = CustomerMaster.objects.filter(user=user.id).values('id','name', 'last_name', 'address', 'phone_number', 'email_id', 'status')

   for data in master_data:
      status = 'Inactive'
      if data['status']:
          status = 'Active'

      if data['phone_number']:
        data['phone_number'] = int(float(data['phone_number'])) if data['phone_number'] != 'NaN' else ''
      total_data.append({'ID': data['id'], 'FirstName': data['name'], 'LastName': data['last_name'], 'Address': data['address'],\
                           'Number': str(data['phone_number']), 'Email': data['email_id']})

   path = 'static/text_files'
   dump_name = 'customer_master'
   print text_file_creator(user, path, total_data, dump_name)


if __name__ == '__main__':
   print str(sys.argv)
   user = sys.argv[1]
   get_user_customer_data(user)
