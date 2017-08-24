import requests
import urlparse
import json
import create_environment
from urllib import urlencode
from miebach_admin.models import UserAccessTokens, UserProfile, Integrations
from urlparse import urlparse, urljoin, urlunparse, parse_qs
import sys
import traceback
import ConfigParser
import datetime
from rest_api.views.miebach_utils  import *
LOAD_CONFIG = ConfigParser.ConfigParser()
LOAD_CONFIG.read('rest_api/views/configuration.cfg')

class EasyopsAPI:
    def __init__(self, company_name='', warehouse='', token='', user=''):
        self.company_name = company_name
        self.warehouse = warehouse
        self.auth_url = LOAD_CONFIG.get(self.company_name, 'auth_url', '')
        self.auth = eval(LOAD_CONFIG.get(self.company_name, 'auth', 'False'))
        self.auth_check = eval(LOAD_CONFIG.get(self.company_name, 'auth_check', 'False'))
        self.host = LOAD_CONFIG.get(self.company_name, 'host', '')
        self.auth_data = LOAD_CONFIG.get(self.company_name, 'authentication', '')
        self.access_token_name = LOAD_CONFIG.get(self.company_name, 'access_token_name', '')
        self.is_full_link = LOAD_CONFIG.get(self.company_name, 'is_full_link', False)
        self.content_type_name = LOAD_CONFIG.get(self.company_name, 'content_type_name', False)
        self.token = token
        self.user = user
        self.content_type = 'application/json'
        self.headers = { self.content_type_name : self.content_type }

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
        if user and self.auth_check:
            self.user = user
            access_token = UserAccessTokens.objects.filter(user_profile__user_id=user.id, app_host=self.company_name)
            if access_token:
                self.token = access_token[0].access_token
            else:
                self.get_access_token(self.user)

    def get_response(self, url, data=None, put=False, auth=False, is_first=True):
        """ Getting API response using request module """
        if self.access_token_name == 'access_token':
            self.headers["Authorization"] = "Bearer " + self.token
        else:
            self.headers[self.access_token_name] = self.token
        if put:
            response = requests.put(url, headers=self.headers, data=json.dumps(data), verify=False)
        elif data:
            response = requests.post(url, headers=self.headers, data=json.dumps(data), verify=False)
        else:
            response = requests.get(url, headers=self.headers, verify=False)

        try:
            response = response.json()
        except:
            if is_first:
                self.get_access_token(self.user)
                response = self.get_response(url, data, put, is_first=False)

        return response

    def get_access_token(self, user=''):
        """ Collecting access token """
        self.user = user
        data = eval(self.auth_data)
        integrations = Integrations.objects.filter(user=user.id, name=self.company_name)
        if integrations:
            self.client_id = integrations[0].client_id
            self.secret = integrations[0].secret
            if self.client_id:
                data = (self.client_id, self.secret)
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
        order_mapping = eval(LOAD_CONFIG.get(self.company_name, 'order_mapping_dict', ''))
        run_iterator = 1
        data = {}
        if user:
            self.user = user
        self.token = token
        if not token:
            self.get_user_token(user)

        main_json_response = ""

        today_start = datetime.datetime.combine(datetime.datetime.now() - datetime.timedelta(days=30), datetime.time())
        data = eval(LOAD_CONFIG.get(self.company_name, 'pending_order_dict', '') % eval(LOAD_CONFIG.get(self.company_name, 'pending_order_values', '')))
        offset = 0
        while run_iterator:
            url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'pending_orders', ''))
            if eval(LOAD_CONFIG.get(self.company_name, 'is_pagination', 'False')):
                data.update(eval(LOAD_CONFIG.get(self.company_name, 'pagination_dict', '') % str(offset)))

            json_response = self.get_response(url, data=data)
            if len(json_response[order_mapping['items']]) > 0:
                if offset == 0:
                    main_json_response = json_response
                else:
                    main_json_response[order_mapping['items']].extend(json_response[order_mapping['items']])

                if eval(LOAD_CONFIG.get(self.company_name, 'is_pagination', 'False')):
                    offset += int(LOAD_CONFIG.get(self.company_name, 'page_size', 0))
                else:
                    run_iterator = 0

            else:
                run_iterator = 0
            print data
        return main_json_response

    def get_stock_count(self, sku_id, token='', user=''):
        """ Getting Stock Count for a particular SKU """
        if user:
            self.user = user
            self.get_user_token(user)
        url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'get_sku_stock', '')) % (sku_id, self.warehouse)
        json_response = self.get_response(url)
        return json_response

    def update_sku_count(self, data={}, token='', user='', method_put=True, individual_update=False):
        """ Updating SKU count for a particular User """
        if user:
            self.user = user
            self.get_user_token(user)
        run_iterator = 1
        url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'update_stock', ''))
        #data = eval(LOAD_CONFIG.get(self.company_name, 'update_stock_dict', '') % stock_count)
        run_limit = len(data)
        offset = 0
        if LOAD_CONFIG.get(self.company_name, 'stock_pagination_limit', ''):
            run_limit = int(LOAD_CONFIG.get(self.company_name, 'stock_pagination_limit', ''))
        while run_iterator:
            slice_data = data[offset:(offset + run_limit)]
            if individual_update:
                slice_data = slice_data[0]
            json_response = self.get_response(url, slice_data, put=method_put)
            offset += run_limit
            if offset >= len(data):
                run_iterator = 0
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

    def confirm_order_status(self, data={}, token='', user=''):
        """ API to confirm the order status (shotang)"""
        if user:
            self.user = user
            self.get_user_token(user)

        if self.is_full_link:
            url = LOAD_CONFIG.get(self.company_name, 'confirm_picklist', '')
        else:
            url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'confirm_picklist', ''))
        json_response = self.get_response(url, data)
        return json_response

    def get_shipped_orders(self, token='', user=''):
        """ Collecting all shipped orders for a particular user """
        order_mapping = eval(LOAD_CONFIG.get(self.company_name, 'shipped_mapping_dict', ''))
        data = {}
        run_iterator = 1
        if user:
            self.user = user
        self.token = token
        if not token:
            self.get_user_token(user)
        main_json_response = ""

        today_start = datetime.datetime.combine(datetime.datetime.now() - datetime.timedelta(days=30), datetime.time())
        data = eval(LOAD_CONFIG.get(self.company_name, 'shipped_order_dict', '') % today_start.strftime('%Y-%m-%dT%H:%M:%SZ'))
        offset = 0
        while run_iterator:

            url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'shipped_orders', ''))
            if LOAD_CONFIG.get(self.company_name, 'is_pagination', ''):
                data.update(eval(LOAD_CONFIG.get(self.company_name, 'pagination_dict', '') % str(offset)))

            json_response = self.get_response(url, data=data)
            if len(json_response[order_mapping['items']]) > 0:
                if offset == 0:
                    main_json_response = json_response
                else:
                    main_json_response[order_mapping['items']].extend(json_response[order_mapping['items']])

                offset += int(LOAD_CONFIG.get(self.company_name, 'page_size', 0))

            else:
                run_iterator = 0
            print data
        return main_json_response

    def get_returned_orders(self, token='', user=''):
        """ Collecting all return orders for a particular user """
        order_mapping = eval(LOAD_CONFIG.get(self.company_name, 'returned_mapping_dict', ''))
        run_iterator = 1
        data = {}
        if user:
            self.user = user
        self.token = token
        if not token:
            self.get_user_token(user)
        main_json_response = ""

        today_start = datetime.datetime.combine(datetime.datetime.now() - datetime.timedelta(days=30), datetime.time())
        data = eval(LOAD_CONFIG.get(self.company_name, 'returned_order_dict', '') % eval(LOAD_CONFIG.get(self.company_name, 'returned_order_values', '')))

        offset = 0
        while run_iterator:
            url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'returned_orders', ''))
            if eval(LOAD_CONFIG.get(self.company_name, 'is_pagination', 'False')):
                data.update(eval(LOAD_CONFIG.get(self.company_name, 'pagination_dict', '') % str(offset)))

            json_response = self.get_response(url, data=data)
            if len(json_response[order_mapping['items']]) > 0:
                if offset == 0:
                    main_json_response = json_response
                else:
                    main_json_response[order_mapping['items']].extend(json_response[order_mapping['items']])

                if eval(LOAD_CONFIG.get(self.company_name, 'is_pagination', 'False')):
                    offset += int(LOAD_CONFIG.get(self.company_name, 'page_size', 0))
                else:
                    run_iterator = 0

            else:
                run_iterator = 0
            print data
        return main_json_response

    def get_cancelled_orders(self, token='', user=''):
        """ Collecting all cancelled orders for a particular user """
        order_mapping = eval(LOAD_CONFIG.get(self.company_name, 'cancelled_mapping_dict', ''))
        run_iterator = 1
        data = {}
        if user:
            self.user = user
        self.token = token
        if not token:
            self.get_user_token(user)
        main_json_response = ""

        today_start = datetime.datetime.combine(datetime.datetime.now() - datetime.timedelta(days=30), datetime.time())
        data = eval(LOAD_CONFIG.get(self.company_name, 'cancelled_order_dict', '') % today_start.strftime('%Y-%m-%dT%H:%M:%SZ'))
        offset = 0
        while run_iterator:
            url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'cancelled_orders', ''))
            if LOAD_CONFIG.get(self.company_name, 'is_pagination', ''):
                data.update(eval(LOAD_CONFIG.get(self.company_name, 'pagination_dict', '') % str(offset)))

            json_response = self.get_response(url, data=data)
            if len(json_response[order_mapping['items']]) > 0:
                if offset == 0:
                    main_json_response = json_response
                else:
                    main_json_response[order_mapping['items']].extend(json_response[order_mapping['items']])

                offset += int(LOAD_CONFIG.get(self.company_name, 'page_size', 0))

            else:
                run_iterator = 0
            print data
        return main_json_response
