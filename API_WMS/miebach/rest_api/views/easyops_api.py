import requests
import urlparse
import json
import create_environment
from urllib import urlencode
from miebach_admin.models import UserAccessTokens, UserProfile, Integrations
from miebach.settings import INTEGRATIONS_CFG_FILE
from urlparse import urlparse, urljoin, urlunparse, parse_qs
import sys
import traceback
import ConfigParser
import datetime
from rest_api.views.miebach_utils import *
from utils import *

LOAD_CONFIG = ConfigParser.ConfigParser()
LOAD_CONFIG.read(INTEGRATIONS_CFG_FILE)

log = init_logger('logs/integration_requests.log')


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
        self.use_exist_auth = LOAD_CONFIG.get(self.company_name, 'use_exist_auth', False)
        self.token = token
        self.user = user
        self.content_type = 'application/json'
        self.headers = {self.content_type_name: self.content_type}

    def update_token(self, json_response):
        """ Updating refresh token details to DB """
        access_token = UserAccessTokens.objects.filter(user_profile__user=self.user, app_host=self.company_name)
        if access_token:
            access_token = access_token[0]
            access_token.access_token = json_response.get('access_token', '')
            access_token.refresh_token = json_response.get('refresh_token', '')
            access_token.save()
        else:
            user_profile = UserProfile.objects.get(user_id=self.user.id)
            access_token = UserAccessTokens.objects.create(access_token=json_response.get('access_token', ''), app_host=self.company_name,
                                                    token_type= json_response.get('token_type', ''),
                                                    code=json_response.get('tenant_id', ''),
                                                    expires_in=json_response.get('expires_in', 0),user_profile_id=user_profile.id)

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
        response = {'status': 'Internal Server Error'}
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
                try:
                    response = self.get_response(url, data, put, is_first=False)
                    response = response.json()
                except Exception as e:
                    import traceback
                    log.debug(traceback.format_exc())
                    response = {'status': 'Internal Server Error'}
        if "emizainc.in/emizawms/GetInventory" in url:
            log.info("API call for url is %s headers is %s request is %s\n" % (url, str(self.headers), str(data)))
        else:
            log.info("API call for url is %s headers is %s request is %s and response is %s" %
                            (url, str(self.headers), str(data), str(response)))
        return response

    def get_access_token(self, user=''):
        """ Collecting access token """
        self.user = user
        data = eval(self.auth_data)
        if self.use_exist_auth and data:
            self.token = data[1]
            self.update_token({'access_token': data[1]})
            return {}
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
            json_response = self.get_response(auth_url, data, is_first=False)
        if self.check_response_type(json_response, 'json'):
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
        data = eval(LOAD_CONFIG.get(self.company_name, 'pending_order_dict', '') % eval(
            LOAD_CONFIG.get(self.company_name, 'pending_order_values', '')))
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

    def update_sku_count(self, data={}, token='', user='', individual_update=False):
        """ Updating SKU count for a particular User """
        if user:
            self.user = user
            self.get_user_token(user)
        run_iterator = 1
        stock_method_name = LOAD_CONFIG.get(self.company_name, 'update_stock_method', '')
        url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'update_stock', ''))
        # data = eval(LOAD_CONFIG.get(self.company_name, 'update_stock_dict', '') % stock_count)
        run_limit = len(data)
        offset = 0
        if LOAD_CONFIG.get(self.company_name, 'stock_pagination_limit', ''):
            run_limit = int(LOAD_CONFIG.get(self.company_name, 'stock_pagination_limit', ''))
        while run_iterator:
            slice_data = data[offset:(offset + run_limit)]
            if individual_update:
                slice_data = slice_data[0]
            if stock_method_name == 'POST':
                json_response = self.get_response(url, slice_data, put=False)
            else:
                json_response = self.get_response(url, slice_data, put=True)
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
        data = eval(
            LOAD_CONFIG.get(self.company_name, 'shipped_order_dict', '') % today_start.strftime('%Y-%m-%dT%H:%M:%SZ'))
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
        data = eval(LOAD_CONFIG.get(self.company_name, 'returned_order_dict', '') % eval(
            LOAD_CONFIG.get(self.company_name, 'returned_order_values', '')))

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
        data = eval(
            LOAD_CONFIG.get(self.company_name, 'cancelled_order_dict', '') % today_start.strftime('%Y-%m-%dT%H:%M:%SZ'))
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

    def check_response_type(self, response, check_type):
        supported_types = ['html', 'json']
        if check_type in supported_types:
            try:
                actual_type = response.headers['Content-Type'].split(';')[0].split('/')[1]
            except Exception as e:
                return False
            return actual_type == check_type
        return False

    def set_return_order_status(self, data={}, token='', user='', status='RETURNED'):
        """ API to set returned as order status (shotang)"""
        if user:
            self.user = user
            self.get_user_token(user)

        if self.is_full_link:
            url = LOAD_CONFIG.get(self.company_name, 'return_order', '')
            if status == 'CANCELLED':
                url = LOAD_CONFIG.get(self.company_name, 'cancel_order', '')
        else:
            url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'return_order', ''))
            if status == 'CANCELLED':
                url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'cancel_order', ''))
        json_response = self.get_response(url, data)
        return json_response

    def qssi_order_push(self, data={}, user=''):
        """ API to push order (QSSI)"""
        if user:
            self.user = user
            self.get_user_token(user)

        if self.is_full_link:
            url = LOAD_CONFIG.get(self.company_name, 'order_push', '')
        else:
            url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'order_push', ''))
        json_response = self.get_response(url, data)
        return json_response


    def qssi_get_inventory(self, data={}, user=''):
        """ API to get inventory (QSSI)"""
        if user:
            self.user = user
            self.get_user_token(user)

        if self.is_full_link:
            url = LOAD_CONFIG.get(self.company_name, 'get_inventory', '')
        else:
            url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'get_inventory', ''))
        json_response = self.get_response(url, data)
        return json_response

    def qssi_get_order_status(self, data={}, user=''):
        """ API to get order status (QSSI)"""
        if user:
            self.user = user
            self.get_user_token(user)
        if self.is_full_link:
            url = LOAD_CONFIG.get(self.company_name, 'get_order_status', '')
        else:
            url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'get_order_status', ''))
        json_response = self.get_response(url, data)
        return json_response

