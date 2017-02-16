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

class RetailoneAPI:
    def __init__(self, company_name='retailone', warehouse='', token='', user=''):
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

    def update_url(self, url):
        """ Updating url with new access token """
        url = urlparse(url)
        query = parse_qs(url.query)
        query['access_token'] = self.token
        url = url._replace(query=urlencode(query, True))
        return urlunparse(url)

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

    def get_response(self, url, data=None, put=False):
        """ Getting API response using request module """
        if put:
            self.headers["Authorization"] = "Bearer " + self.token
            response = requests.put(url, headers=self.headers, data=data, verify=False)
        elif data:
	    data = json.dumps(data)
            response = requests.post(url, headers=self.headers, data=data, verify=False)
        else:
            response = requests.get(url, headers=self.headers, verify=False)

        response = response.json()
        if isinstance(response, dict) and '/access_token' not in url \
                and response.get('error') and response.get('error') == 'access_denied':
            response = self.refresh_token()
            token = response.get('access_token')
            if token:
                self.token = token
                url = self.update_url(url)
                response = self.get_response(url, data, put)
                return response

        return response

    def refresh_token(self):
        """ Getting token details by using refresh token """
        data = { 'client_id': self.client_id,
                 'client_secret': self.secret,
                 'redirect_uri': self.redirect,
                 'grant_type': 'refresh_token' }

        user_access_token = UserAccessTokens.objects.get(user_profile__user=self.user.id, token_type='Bearer')
        data['refresh_token'] = user_access_token.refresh_token
        url = urljoin(URL, ACCESS_TOKEN)
        json_response = self.get_response(url, data)
        self.update_token(json_response)
        return json_response

    def get_access_token(self, code=''):
        """ Collecting access token """
        data = { 'client_id': self.client_id,
                 'client_secret': self.secret,
                 'redirect_uri': self.redirect,
                 'grant_type': 'authorization_code',
                 'code': code }

        url = urljoin(URL, ACCESS_TOKEN)
        json_response = self.get_response(url, data)
        self.token = json_response.get('access_token', '')
        return json_response

    def get_seller_details(self, token=''):
        """ Collecting seller profile details """
        if token:
            self.token = token

	url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'seller', '')) + self.token
        json_response = self.get_response(url)
        return json_response

    def get_all_skus(self, token='', user=''):
        """ Collecting all sku's for a particular user """
        if token:
            self.token = token
        if user:
            self.user = user

        #url = urljoin(URL, ALL_SKUS) + self.token
	url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'all_skus', '')) + self.token
        json_response = self.get_response(url)
        return json_response

    def get_pending_orders(self, token='', user=''):
        """ Collecting all pending orders for a particular user """
	if token:
	    self.token = token
	if user:
	    self.user = user

	#url = urljoin(URL, RETURNED_ORDERS) + self.token

	url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'sync_orders', ''))

	#today_start = datetime.datetime.combine(datetime.datetime.now() - datetime.timedelta(days=30), datetime.time())/strftime('%Y-%m-%dT%H:%M:%SZ')
	#approved_order_dict = {"sync_token": %s, "mp_info_id": '', "states": ['APPROVED', 'Pending', 'UnShipped'], 'user': %s, 'source': 'stockone'}
	data = eval(LOAD_CONFIG.get(self.company_name, 'approved_order_dict', '') % ("0", int(user.id)))

	json_response = self.get_response(url, data)
	return json_response

    def get_cancelled_orders(self, token='', user=''):
        """ Collecting all pending orders for a particular user """
        if token:
            self.token = token
        if user:
            self.user = user

        #url = urljoin(URL, CANCELLED_ORDERS) + self.token
	url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'cancelled_orders', '')) + self.token
        json_response = self.get_response(url)
        return json_response

    def get_pending_sku_orders(self, sku, token='', user=''):
        """ Collecting all pending orders for a particular user """
        if token:
            self.token = token
        if user:
            self.user = user

        #url = urljoin(URL, PENDING_SKU_ORDERS % sku) + self.token
	url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'pending_sku_orders', '')) + self.token
        json_response = self.get_response(url)
        return json_response

    def get_stock_count(self, sku_id, token='', user=''):
        """ Getting Stock Count for a particular SKU """
        if token:
            self.token = token
        if user:
            self.user = user

        #url = urljoin(URL, UPDATE_SKU) % sku_id + self.token
	url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'get_sku_stock', '')) % (sku_id) + self.token
        json_response = self.get_response(url)
        return json_response

    def update_sku_count(self, sku_id, stock_count, token='', user=''):
        """ Updating SKU count for a particular User """
        if token:
            self.token = token
        if user:
            self.user = user

        #url = urljoin(URL, UPDATE_SKU) % sku_id + self.token
        #data = {"stock": stock_count}
	url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'update_stock', '')) % (sku_id) + self.token
	data = eval(LOAD_CONFIG.get(self.company_name, 'update_stock_dict', '') % stock_count)

        json_response = self.get_response(url, data, put=True)
        return json_response

    def confirm_picklist(self, order_id, token='', user=''):
        """ API to confirm the picklist status """
        if token:
            self.token = token
        if user:
            self.user = user

        #url = urljoin(URL, UPDATE_ORDER) % order_id
        #data = '{"status":"PICK_LIST_GEN"}'
        url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'confirm_picklist', '')) % order_id
        data = eval(LOAD_CONFIG.get(self.company_name, 'confirm_picklist_dict', ''))
        json_response = self.get_response(url, data, put=True)
        return json_response

    def get_returned_orders(self, token='', user=''):
        """ Collecting all pending orders for a particular user """
        if token:
            self.token = token
        if user:
            self.user = user

        #url = urljoin(URL, RETURNED_ORDERS) + self.token

        url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'sync_orders', ''))

        #today_start = datetime.datetime.combine(datetime.datetime.now() - datetime.timedelta(days=30), datetime.time())/strftime('%Y-%m-%dT%H:%M:%SZ')
	data = eval(LOAD_CONFIG.get(self.company_name, 'returned_order_dict', '') % ("0", int(user.id)))

        json_response = self.get_response(url, data)
        return json_response

    def get_all_returned(self, order_id, sku, token='', user=''):
        """ Getting Returned orders for a particular User """
        if token:
            self.token = token
        if user:
            self.user = user

        self.token = self.user.refresh_token
        #url = urljoin(URL, RETURNS % (order_id, sku)) + self.token
        url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'return_sku_orders', '') % (order_id, sku)) + self.token

        json_response = self.get_response(url)
        return json_response

    def add_update_marketplace(self, data, token='', user=''):
        """ Add or Update Marketplace details for a particular User """
        if token:
            self.token = token
        if user:
            self.user = user
	url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'market_data'))
	if "form" in data:
	    if data["form"] == "add":
	        url = url + "?username=root&api_key=28231a94a648d6a7697ee346435f7d7bbfba8c6d"
	        json_response = self.get_response(url, data = data, put=False)
	    elif data["form"] in ['update','status']:
	        data_id = str(int(data['id']))
	        url = url + '?id=' + data_id
		json_response = self.get_response(url, data = json.dumps(data), put=True)
        return json_response

    def get_seller_channels(self, token='', user=''):
        """ Add or Update Marketplace details for a particular User """
	url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'market_data'))
        if token:
            self.token = token
        if user:
            self.user = user
            url = url + '?user=' + str(user.id) + '&source=stockone&email='+str(user.email)+'&username='+str(user.username)
        json_response = self.get_response(url)
        return json_response

    def get_all_channel_data(self, token='', user=''):
	url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'channel_data_url'))
        if token:
            self.token = token
        url = url + 'all?username=root&api_key=28231a94a648d6a7697ee346435f7d7bbfba8c6d'
        json_response = self.get_response(url)
        return json_response

    def pull_marketplace_data(self, data, token='', user=''):
	url = urljoin(self.host, LOAD_CONFIG.get(self.company_name, 'pull_data_url'))
        if token:
            self.token = token
	if user:
	    self.user = user
	url = url + data
	try:
	    json_response = self.get_response(url)
	except:
	    json_response = { 'errorCode' : "Pull Now Failed" }
        
	return json_response
