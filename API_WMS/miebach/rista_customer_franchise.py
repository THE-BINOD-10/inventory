import requests
import jwt

import time
import json
import csv
import os
import ConfigParser
import datetime
LOAD_CONFIG = ConfigParser.ConfigParser()
LOAD_CONFIG.read('rest_api/views/configuration_prod.cfg')

apiKey = '1db15d25-6a99-479e-a48f-b4fb56a3dbad'
secretKey = 'OVfw7xnQAwO2XFfUJBM5I1xZh6UxGusqj_XvgR98P-s'

API_HOST = 'api.ristaapps.com'
ENDPOINT = '/v1/branch/list'
SCHEME = 'https'
rista_location_keys = eval(LOAD_CONFIG.get('rista', 'rista_location_keys', ''))
branch_list = eval(LOAD_CONFIG.get('rista', 'branch_list', ''))

def create_csv(data, branch_code):
    temp_data = []
    csv_headers = ['Customer Id', 'Customer Name', 'Customer Code', 'Credit Period', 'CST Number', 'TIN Number', 'PAN Number', 'Email', 'Phone No.', 'City', 'State', 'Country', 'Pin Code', 'Address', 'Shipping Address', 'Selling Price Type', 'Tax Type(Options: Inter State, Intra State)', 'Discount Percentage(%)', 'Markup(%)', 'SPOC Name']
    print "Resp Data : branch_Code"
    for idx, xer in enumerate(data):
        assign_id = idx + 1
	obj = []
	customer_id = assign_id
	customer_code = xer['branchCode']
	customer_name = xer['branchName']
	obj.append(customer_id)
	obj.append(customer_name)
        obj.append(customer_code)
	obj.append('')
	obj.append('')
	obj.append('')
	obj.append('')
	obj.append('')
	obj.append('')
	obj.append(xer['address']['city'])
	obj.append(xer['address']['state'])
	obj.append(xer['address']['country'])
	obj.append(xer['address']['zip'])
	obj.append(xer['address']['addressLine'])
	obj.append(xer['address']['addressLine'])
	obj.append('Type1')
	obj.append('Intra State')
	obj.append(0)
	obj.append(0)
	obj.append('')
	temp_data.append(obj)
    path = '/root/aravind/rista_stockone/'
    if not os.path.exists(path):
        os.makedirs(path)
    with open(path + str(branch_code) + '_franchise_list' + str(datetime.datetime.now())[0:19].replace(' ', '_') + '.csv', mode='w') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, delimiter=',')
        counter = 0
        try:
            thedatawriter.writerow(itemgetter(*csv_headers)(headers))
        except:
            thedatawriter.writerow(csv_headers)
        for data in temp_data:
            try:
                thedatawriter.writerow(data)
            except:
                print "RISTA Error"
            counter += 1
    return path

def make_request():
    url = "{}://{}{}".format(SCHEME, API_HOST, ENDPOINT)
    for branch_code in branch_list:
        get_api_key_secret = rista_location_keys[branch_code]
	apiKey = get_api_key_secret[0]
        secretKey = get_api_key_secret[1]
	tokencreationtime = int(round(time.time()))
        jti = int(time.time() * 1000.0)
        payload = { "jti": jti, "iss": apiKey, "iat": tokencreationtime }
        token = jwt.encode(payload, secretKey, algorithm='HS256')
        headers =  { 'x-api-key': apiKey, 'x-api-token': token, 'content-type': 'application/json' }
        resp = requests.get(url, headers=headers)
    	create_csv(resp.json(), branch_code)

make_request()
