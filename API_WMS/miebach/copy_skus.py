import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()
from miebach_admin.models import *
from rest_api.views.sync_sku import *
import datetime
import shutil

print sys.argv[1]
'''sku_ids, sku_codes = eval(sys.argv[1])[0], eval(sys.argv[1])[1]
sku_codes=sys.argv[2]
print sys.argv
print eval(sku_ids)
sku_masters = SKUMaster.objects.filter(id__in=sku_ids)
create_sku(sku_masters, sku_codes)'''
