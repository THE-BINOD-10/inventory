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

save_transfer_in_logs = init_logger('logs/save_transfer_in.log')

apiKey = '945ae8b1-1886-43f4-9d0e-4986c0f383d3'
secretKey = 'lolnJIoZK2otG_d_PUiAXFgWOWOuglfJ8wnwNvDhg-w'

API_HOST = 'api.ristaapps.com'
ENDPOINT = '/v1/inventory/transfer'

SCHEME = 'https'

def save_transfer_in_rista(input_data):
    a = datetime.datetime.now()
    save_transfer_in_logs.info(' ------ Started Transfer In - Rista ------')
    resp_data_dict = {}
    tokencreationtime = int(round(time.time()))
    jti = int(time.time() * 1000.0)
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

