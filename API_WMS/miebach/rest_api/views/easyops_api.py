import requests
import urlparse
import json
import create_environment
from urllib import urlencode
from miebach_admin.models import UserAccessTokens, UserProfile
from urlparse import urlparse, urljoin, urlunparse, parse_qs
import sys
import traceback
import ConfigParser
import datetime

LOAD_CONFIG = ConfigParser.ConfigParser()
LOAD_CONFIG.read('rest_api/views/configuration.cfg')

class EasyopsAPI:
    def __init__(self, company_name='', warehouse='', token='', user=''):
        self.company_name = company_name
        self.warehouse = warehouse
        self.auth_url = LOAD_CONFIG.get(self.company_name, 'auth_url', '')
        self.auth = LOAD_CONFIG.get(self.company_name, 'auth', '')
        self.host = LOAD_CONFIG.get(self.company_name, 'host', '')
        self.auth_data = LOAD_CONFIG.get(self.company_name, 'authentication', '')
        self.token = token
        self.user = user
        self.content_type = 'application/json'
        self.headers = { 'ContentType' : self.content_type }

    def update_token(self, json_response):
        """ Updating refresh token details to DB """
        access_token = UserAccessTokens.objects.filter(user_profile__user=self.user, app_host='easyops')
        if access_token:
            access_token = access_token[0]
            access_token.access_token = json_response.get('access_token', '')
            access_token.refresh_token = json_response.get('refresh_token', '')
            access_token.save()
        else:
            user_profile = UserProfile.objects.get(user_id=self.user.id)
            access_token = UserAccessTokens.objects.create(access_token=json_response.get('access_token'), app_host='easyops',
                                                           token_type= json_response.get('token_type'),
                                                           code=json_response.get('tenant_id'),
                                                           expires_in=json_response.get('expires_in'),user_profile_id=user_profile.id)

    def get_user_token(self, user=''):
        self.token = ''
        if user:
            self.user = user
            access_token = UserAccessTokens.objects.filter(user_profile__user_id=user.id, app_host='easyops')
            if access_token:
                self.token = access_token[0].access_token
            else:
                self.get_access_token(self.user)

    def get_response(self, url, data=None, put=False, auth=False):
        """ Getting API response using request module """
        self.headers["Authorization"] = "Bearer " + self.token
        if put:
            response = requests.put(url, headers=self.headers, data=json.dumps(data), verify=False)
        elif data:
            response = requests.post(url, headers=self.headers, data=json.dumps(data), verify=False)
        else:
            response = requests.get(url, headers=self.headers, verify=False)

        try:
            response = response.json()
        except:
            self.get_access_token(self.user)
            response = self.get_response(url, data, put)

        return response

    def get_access_token(self, user=''):
        """ Collecting access token """
        self.user = user
        data = eval(self.auth_data)

        auth_url = urljoin(self.host, self.auth_url)
        if self.auth:
            json_response = requests.post(auth_url, headers=self.headers, auth=data, verify=False).json()
        else:
            json_response = self.get_response(auth_url, data)
        self.token = json_response.get('access_token', '')
        self.update_token(json_response)
        return json_response

    def get_pending_orders(self, token='', user=''):
        """ Collecting all pending orders for a particular user """
        data = {}
        if user:
            self.user = user
        self.token = token
        if not token:
            self.get_user_token(user)

        today_start = datetime.datetime.combine(datetime.datetime.now() - datetime.timedelta(days=30), datetime.time())
        data = eval(LOAD_CONFIG.get(self.company_name, 'pending_order_dict', '') % today_start.strftime('%Y-%m-%dT%H:%M:%SZ'))

        url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'pending_orders', ''))

        json_response = self.get_response(url, data=data)
        return json_response

    def get_stock_count(self, sku_id, token='', user=''):
        """ Getting Stock Count for a particular SKU """
        if user:
            self.user = user
            self.get_user_token(user)
        url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'get_sku_stock', '')) % (sku_id, self.warehouse)
        json_response = self.get_response(url)
        return json_response

    def update_sku_count(self, sku_id, stock_count, token='', user=''):
        """ Updating SKU count for a particular User """
        data = {}
        if user:
            self.user = user
            self.get_user_token(user)

        url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'update_stock', '')) % (sku_id, stock_count)
        #data = eval(LOAD_CONFIG.get(self.company_name, 'update_stock_dict', '') % stock_count)
        json_response = self.get_response(url, data, put=True)
        return json_response

    def confirm_picklist(self, order_id, token='', user=''):
        """ API to confirm the picklist status """
        data = {}
        if user:
            self.user = user
            self.get_user_token(user)

        url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'confirm_picklist', ''))
        data = eval(LOAD_CONFIG.get(self.company_name, 'confirm_picklist_dict', '') % order_id)
        json_response = self.get_response(url, data, put=True)
        return json_response

    def get_shipped_orders(self, token='', user=''):
        """ Collecting all shipped orders for a particular user """
        data = {}
        if user:
            self.user = user
        self.token = token
        if not token:
            self.get_user_token(user)

        today_start = datetime.datetime.combine(datetime.datetime.now() - datetime.timedelta(days=30), datetime.time())
        data = eval(LOAD_CONFIG.get(self.company_name, 'shipped_order_dict', '') % today_start.strftime('%Y-%m-%dT%H:%M:%SZ'))

        url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'shipped_orders', ''))

        json_response = self.get_response(url, data=data)
        return json_response

    def get_returned_orders(self, token='', user=''):
        """ Collecting all return orders for a particular user """
        data = {}
        if user:
            self.user = user
        self.token = token
        if not token:
            self.get_user_token(user)

        url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'returned_orders', ''))

        today_start = datetime.datetime.combine(datetime.datetime.now() - datetime.timedelta(days=30), datetime.time())
        data = eval(LOAD_CONFIG.get(self.company_name, 'returned_order_dict', '') % today_start.strftime('%Y-%m-%dT%H:%M:%SZ'))

        json_response = self.get_response(url, data=data)
        return json_response

    def get_cancelled_orders(self, token='', user=''):
        """ Collecting all cancelled orders for a particular user """
        data = {}
        if user:
            self.user = user
        self.token = token
        if not token:
            self.get_user_token(user)

        today_start = datetime.datetime.combine(datetime.datetime.now() - datetime.timedelta(days=30), datetime.time())
        data = eval(LOAD_CONFIG.get(self.company_name, 'cancelled_order_dict', '') % today_start.strftime('%Y-%m-%dT%H:%M:%SZ'))

        url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'cancelled_orders', ''))

        json_response = self.get_response(url, data=data)
        return json_response
