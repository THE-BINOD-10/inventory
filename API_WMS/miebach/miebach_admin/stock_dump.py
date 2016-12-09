from sellerworx_api import *
from models import *
from mail_server import send_mail
from django.db.models import Sum
from datetime import datetime
import threading
import time

MAIL_TO = [ 'sudheer@headrun.com' ]
EXCLUDE_LOCATION = ['K1', 'C1', 'C2', 'TEMP1']

LOCATION = LocationMaster.objects.get(location='TEMP1')

class CollectData:
    def __init__(self):
        self.users = UserAccessTokens.objects.all()
        self.sellerworx_api = SellerworxAPI()

    def populate_data(self, query_class, user):
        data = query_class(token=user.access_token, user=user.user_profile.user)
        return data


    def update_stock(self, sku, orders, user):
        sku_code = sku['sku']
        orders_count = 0
        for order in orders:
            is_fbm = order['channel_sku']['is_fbm']
            if is_fbm == "1":
                continue

            if order['sku'] == sku_code:
                orders_count += int(order['quantity'])


        filter_params = {'quantity__gt': 0, 'sku__user': user.id, 'sku__sku_code': sku_code}
        stock_count = StockDetail.objects.filter(**filter_params).exclude(location__location__in=EXCLUDE_LOCATION).aggregate(Sum('quantity'))
        temp_stock = StockDetail.objects.filter(location__location__in=EXCLUDE_LOCATION, **filter_params)

        total_stock = stock_count['quantity__sum']
        if not total_stock:
            total_stock = 0

        stock_difference = 0
        if int(sku['stock']) > (total_stock - orders_count):
            stock_difference = int(sku['stock']) - (total_stock - orders_count)

        for temp in temp_stock:
            temp.quantity = stock_difference
            temp.save()
            stock_difference = 0
        else:
            sku_master = SKUMaster.objects.filter(sku_code=sku_code)
            if stock_difference and sku_master:
                data_dict = {'receipt_number': 1, 'receipt_date': datetime.now(), 'quantity': stock_difference, 'status': 1, 'creation_date': datetime.now(), 'updation_date': datetime.now(), 'location': LOCATION, 'sku': sku_master[0]}
                StockDetail(**data_dict).save()


    def get_user_skus(self):

        for user in self.users:
            if user.user_profile.user.username != "Pavechas":
                continue
            try:
                skus = self.populate_data(self.sellerworx_api.get_all_skus, user)
                orders = self.populate_data(self.sellerworx_api.get_pending_orders, user)
                skus = skus['items']
                orders = orders.get('items', [])
                for sku in skus:
                    try:
                        self.update_stock(sku, orders, user)
                        print "Stock Updated: %s" % user.user_profile.user.username
                    except:
                        print "Failed to update the stock"
            except:
                continue


    def run_main(self):
        threads = []
        thread_obj = [ self.get_user_skus ]
        for count, obj in enumerate(thread_obj):
            thread = threading.Thread(name='Thread%s' % count, target=obj)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()
