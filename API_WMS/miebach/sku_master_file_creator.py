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

def get_user_sku_data(user):
   user = User.objects.get(id=user)
   print "inside sku func"
   total_data = []
   master_data = SKUMaster.objects.exclude(sku_type='RM').filter(user = user.id).only('id', 'zone_id', 'price', 'product_type',\
                                                         'discount_percentage', 'sku_category', 'wms_code', 'sku_desc', 'image_url')\
                                                         .prefetch_related('zone')

   stocks = dict(StockDetail.objects.filter(sku__user=user.id).exclude(location__zone__zone='DAMAGED_ZONE')
                                    .values_list('sku__wms_code').distinct().annotate(total=Sum('quantity')))
   for data in master_data:
      status = 'Inactive'
      if data.status:
         status = 'Active'

      zone = ''
      if data.zone_id:
         zone = data.zone.zone

      price = data.price

      tax_master = TaxMaster.objects.filter(user=user, product_type=data.product_type, max_amt__gte=data.price, min_amt__lte=data.price)\
                                    .values('sgst_tax', 'cgst_tax', 'igst_tax', 'utgst_tax')
      sgst, cgst, igst, utgst = [0]*4
      if tax_master:
         sgst = tax_master[0]['sgst_tax']
         cgst = tax_master[0]['cgst_tax']
         igst = tax_master[0]['igst_tax']
         utgst= tax_master[0]['utgst_tax']

      discount_percentage = data.discount_percentage
      discount_price = price
      if not data.discount_percentage:
         category = CategoryDiscount.objects.filter(category = data.sku_category).values('discount')
         if category:
            category = category[0]
            if category['discount']:
               discount_percentage = category['discount']
      if discount_percentage:
         discount_price = price - ((price * discount_percentage) / 100)
      stock_quantity = stocks.get(data.wms_code, 0)
      total_data.append({'search': str(data.wms_code) + " " + data.sku_desc, 'SKUCode': data.wms_code, 'ProductDescription': data.sku_desc, \
                         'price': discount_price, 'url': data.image_url, 'data-id': data.id, 'discount': discount_percentage,\
                         'selling_price': price, 'stock_quantity': stock_quantity, 'sgst': sgst, 'cgst': cgst, 'igst': igst, 'utgst': utgst})

   path = 'static/text_files'
   dump_name = 'sku_master'
   print text_file_creator(user, path, total_data, dump_name)


if __name__ == '__main__':
   print str(sys.argv)
   user = sys.argv[1]
   get_user_sku_data(user)
