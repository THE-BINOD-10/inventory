import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()
from rest_api.views.easyops_api import *
from miebach_admin.models import *
from rest_api.views.integrations import update_orders, update_shipped
from mail_server import send_mail
import threading
import time

MAIL_TO = [ 'sreekanth@mieone.com' ]

class CollectData:
    def __init__(self, company_name=''):
        self.users = User.objects.filter(username="demo")
        self.easyops_api = EasyopsAPI(company_name=company_name, warehouse='default')
        self.company_name = company_name

    def populate_data(self, query_class, func):
        signal = 0
        for user in self.users:
            try:
                access_token = ''
                user_access_token = UserAccessTokens.objects.filter(user_profile__user_id=user.id)
                if user_access_token:
                    access_token = user_access_token[0].access_token
                data = query_class(token=access_token, user=user)
                print data
                func(data, user=user, company_name=self.company_name)
            except:
                continue

        return signal

    def get_user_skus(self):
        while True:
            signal = self.populate_data(self.sellerworx_api.get_all_skus, update_skus)
            if signal:
                break

            time.sleep(86400)
        send_mail('DUMPS: SKU master dump status', 'SKU Master loading failed', receivers=MAIL_TO)

    def cancelled_orders(self):
        while True:
            signal = self.populate_data(self.sellerworx_api.get_cancelled_orders, update_cancelled_orders)
            if signal:
                break

            time.sleep(60)
        send_mail('DUMPS: Cancelled Orders dump status', 'Cancelledd Orders dump failed', receivers=MAIL_TO)

    def get_user_orders(self):
        while True:
            signal = self.populate_data(self.easyops_api.get_pending_orders, update_orders)
            if signal:
                break

            time.sleep(60)
        send_mail('DUMPS: Orders dump status', 'Order Detail loading failed', receivers=MAIL_TO)

    def returned_orders(self):
        while True:
            signal = self.populate_data(self.sellerworx_api.get_returned_orders, update_returns)
            if signal:
                break

            time.sleep(60)
        send_mail('DUMPS: Returned Orders dump status', 'Returned Orders dump failed', receivers=MAIL_TO)

    def shipped_orders(self):
        while True:
            signal = self.populate_data(self.easyops_api.get_shipped_orders, update_shipped)
            if signal:
                break

            time.sleep(60)
        send_mail('DUMPS: Shipped Orders dump status', 'Shipped Orders dump failed', receivers=MAIL_TO)

    def run_main(self):
        threads = []
        thread_obj = [ self.get_user_orders, self.shipped_orders ]
        #thread_obj = [ self.shipped_orders ]
        for count, obj in enumerate(thread_obj):
            thread = threading.Thread(name='Thread%s' % count, target=obj)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()
