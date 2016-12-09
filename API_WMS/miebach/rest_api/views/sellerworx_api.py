import requests
import urlparse
import json
import create_environment
from urllib import urlencode
from models import UserAccessTokens
from urlparse import urlparse, urljoin, urlunparse, parse_qs
import sys
import traceback

URL = 'https://connect.sellerworx.com'
CLIENT_ID = 'e4d03633-eaf2-4696-970f-8c9f60745d7b'
SECRET = '$2y$10$hmWXHf.Btf2DOH.7e7lag.pLw8uHRd0uH'
REDIRECT = 'http://sconnect.miebach.tech'
AUTHORIZE_URL = '%s/oauth/authorize?client_id=%s&redirect_uri=%s&response_type=code'
ACCESS_TOKEN = 'oauth/access_token'
ALL_SKUS = '/api/v5/skus?access_token='
PENDING_ORDERS = '/api/v5/orders?filters={"status":{"in":["PENDING"]}}&sort_by=created_at&sort_order=DESC&limit=400&access_token='
CANCELLED_ORDERS = '/api/v5/orders?filters={"status":{"in":["CANCELLED"]}}&sort_by=created_at&sort_order=DESC&limit=400&access_token='
RETURNED_ORDERS = '/api/v5/orders?filters={"status":{"in":["RETURNS"]}}&access_token='
RETURNS = 'api/v5/orders?filters={"channel_orderitem_id":{"in":["%s"]},"sku": {"in": ["%s"]}}&access_token='
PENDING_SKU_ORDERS = '/api/v5/orders?filters={"status":{"in":["PENDING"]},"sku":{"in":["%s"]}}&access_token='
UPDATE_SKU = '/api/v5/skus/%s?access_token='
UPDATE_ORDER = '/api/v5/orders/%s'
SELLER = '/api/v5/seller?access_token='

class SellerworxAPI:
    def __init__(self, url=URL, client_id=CLIENT_ID, secret=SECRET, redirect=REDIRECT, user=''):
        self.url = url
        self.client_id = client_id
        self.secret = secret
        self.redirect = redirect
        self.token = ''
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
        access_token = UserAccessTokens.objects.get(user_profile__user=self.user)
        access_token.access_token = json_response.get('access_token')
        access_token.refresh_token = json_response.get('refresh_token')
        access_token.save()

    def get_response(self, url, data=None, put=False):
        """ Getting API response using request module """
        if put:
            self.headers["Authorization"] = "Bearer " + self.token
            response = requests.put(url, headers=self.headers, data=data, verify=False)
        elif data:
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

        url = urljoin(URL, SELLER) + self.token
        json_response = self.get_response(url)
        return json_response

    def get_all_skus(self, token='', user=''):
        """ Collecting all sku's for a particular user """
        if token:
            self.token = token
        if user:
            self.user = user

        url = urljoin(URL, ALL_SKUS) + self.token
        json_response = self.get_response(url)
        return json_response

    def get_pending_orders(self, token='', user=''):
        """ Collecting all pending orders for a particular user """
        if token:
            self.token = token
        if user:
            self.user = user

        url = urljoin(URL, PENDING_ORDERS) + self.token
        json_response = self.get_response(url)
        return json_response

    def get_cancelled_orders(self, token='', user=''):
        """ Collecting all pending orders for a particular user """
        if token:
            self.token = token
        if user:
            self.user = user

        url = urljoin(URL, CANCELLED_ORDERS) + self.token
        json_response = self.get_response(url)
        return json_response

    def get_pending_sku_orders(self, sku, token='', user=''):
        """ Collecting all pending orders for a particular user """
        if token:
            self.token = token
        if user:
            self.user = user

        url = urljoin(URL, PENDING_SKU_ORDERS % sku) + self.token
        json_response = self.get_response(url)
        return json_response

    def get_stock_count(self, sku_id, token='', user=''):
        """ Getting Stock Count for a particular SKU """
        if token:
            self.token = token
        if user:
            self.user = user

        url = urljoin(URL, UPDATE_SKU) % sku_id + self.token
        json_response = self.get_response(url)
        return json_response

    def update_sku_count(self, sku_id, stock_count, token='', user=''):
        """ Updating SKU count for a particular User """
        if token:
            self.token = token
        if user:
            self.user = user

        url = urljoin(URL, UPDATE_SKU) % sku_id + self.token
        data = {"stock": stock_count}
        json_response = self.get_response(url, data, put=True)
        return json_response

    def confirm_picklist(self, order_id, token='', user=''):
        """ API to confirm the picklist status """
        if token:
            self.token = token
        if user:
            self.user = user

        url = urljoin(URL, UPDATE_ORDER) % order_id
        data = '{"status":"PICK_LIST_GEN"}'
        json_response = self.get_response(url, data, put=True)
        return json_response

    def get_returned_orders(self, token='', user=''):
        """ Collecting all pending orders for a particular user """
        if token:
            self.token = token
        if user:
            self.user = user

        url = urljoin(URL, RETURNED_ORDERS) + self.token
        json_response = self.get_response(url)
        return json_response

    def get_all_returned(self, order_id, sku, token='', user=''):
        """ Getting Returned orders for a particular User """
        if token:
            self.token = token
        if user:
            self.user = user

        self.token = self.user.refresh_token
        url = urljoin(URL, RETURNS % (order_id, sku)) + self.token
        json_response = self.get_response(url)
        return json_response

