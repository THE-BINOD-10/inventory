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


apiKey = '945ae8b1-1886-43f4-9d0e-4986c0f383d3'
secretKey = 'lolnJIoZK2otG_d_PUiAXFgWOWOuglfJ8wnwNvDhg-w'

API_HOST = 'api.ristaapps.com'
ENDPOINT = '/v1/inventory/transfer'

SCHEME = 'https'

def save_transfer_in(input_data):
    tokencreationtime = int(round(time.time()))
    payload = {
        "iss": apiKey,
        "iat": tokencreationtime
    }
    token = jwt.encode(payload, secretKey, algorithm='HS256')
    import pdb;pdb.set_trace()
    headers =  {
        'x-api-key': apiKey,
        'x-api-token': token,
        'content-type': 'application/json'
    }
    url = "{}://{}{}".format(SCHEME, API_HOST, ENDPOINT)
    #inv_payload = {'branch' : 'BW', 'day' : '2019-01-05'}
    resp = requests.post(url, headers=headers, data=json.dumps(input_data))
    #with open('inventory_indent.json', 'w') as f:
    #    f.write(resp.content)
    print len(resp.json())
    print resp.json()
    return True


