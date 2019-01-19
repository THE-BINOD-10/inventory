import requests
import jwt

import time
import json

import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()
from django.db.models import Q
from miebach_admin.models import *
import datetime
from rest_api.views.utils import *
import time
import ConfigParser
from miebach.settings import *
save_transfer_in_logs = init_logger('logs/rista_save_transfer_in.log')
SCHEME = 'https'
LOAD_CONFIG = ConfigParser.ConfigParser()
LOAD_CONFIG.read(INTEGRATIONS_CFG_FILE)
API_HOST = LOAD_CONFIG.get('rista', 'rista_app_url', '')
ENDPOINT = LOAD_CONFIG.get('rista', 'save_transfer_url', '')
rista_location_keys = eval(LOAD_CONFIG.get('rista', 'rista_location_keys', ''))

def save_transfer_in_rista(input_data, branch_code):
    a = datetime.datetime.now()
    save_transfer_in_logs.info(' ------ Started Transfer In - Rista ------')
    resp_data_dict = {}
    tokencreationtime = int(round(time.time()))
    jti = int(time.time() * 1000.0)
    get_api_key_secret = rista_location_keys[branch_code]
    apiKey = get_api_key_secret[0]
    secretKey = get_api_key_secret[1]
    payload = {
        "jti": jti,
        "iss": apiKey,
        "iat": tokencreationtime
    }
    token = jwt.encode(payload, secretKey, algorithm='HS256')
    headers =  {
        'x-api-key': apiKey,
        'x-api-token': token,
        'content-type': 'application/json'
    }
    url = "{}://{}{}".format(SCHEME, API_HOST, ENDPOINT)
    save_transfer_in_logs.info(' ------ Input Data ------- :' + str(json.dumps(input_data)) )
    response = requests.post(url, headers=headers, data=json.dumps(input_data))
    json_resp = response.json()
    save_transfer_in_logs.info(' ------ Output Data ------- :' + str(json_resp) )
    if str(response.status_code) in ['500', '422', '409', '404', '403', '401', '400']:
        resp_data_dict['message'] = json.dumps(json_resp)
	resp_data_dict['status'] = False
    else:
	resp_data_dict['message'] = json.dumps(json_resp)
	resp_data_dict['status'] = True
    b = datetime.datetime.now()
    delta = b - a
    time_taken = str(delta.total_seconds() * 1000)
    save_transfer_in_logs.info("--------Stoped Transfer In - Rista-------")
    save_transfer_in_logs.info("Total Time Taken in Sec " + time_taken)
    return resp_data_dict

