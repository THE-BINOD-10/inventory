import create_environment
from models import *
from mail_server import send_mail
from datetime import datetime, date, timedelta
from mail_server import send_mail
from django.db.models import Sum
from xlwt import Workbook

date_length = 7

all_dates = []
for d in range(date_length):
    all_dates.append(date.today() - timedelta(days=int(d)))

final_count = {}
for report_date in all_dates:
    stock_detail = StockDetail.objects.exclude(location__location='DFLT1').filter(creation_date__lte=report_date, quantity__gt=0).values('sku__wms_code').annotate(quantity = Sum('quantity')).order_by('-quantity')
    total_count = 0
    for detail in stock_detail:
        total_count += detail['quantity']
    final_count [str(report_date)] = total_count


print final_count
