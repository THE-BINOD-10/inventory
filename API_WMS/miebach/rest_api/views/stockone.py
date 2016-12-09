from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import copy
import os
import json, ast
from django.db.models import Q, F
from itertools import chain
from collections import OrderedDict
from django.contrib.auth import authenticate
from django.contrib import auth
from miebach_admin.models import *
from miebach_utils import *
from mail_server import send_mail, send_mail_attachment
from django.core import serializers
from django.template import loader, Context
import dicttoxml
from operator import itemgetter
from common import *
from xmljson import badgerfish as bf
from xml.etree.ElementTree import fromstring
#from retailone_api import *
import requests
import traceback
import hashlib
from mail_server import send_mail

#retail_orders_url = 'http://176.9.181.39:8000/orders/'
#RETAIL_ADD_MARKETPLACE_URL = 'http://dev.retail.one/api/v1/marketplaces/'
#EXTRA_INFO_FIELDS = ['flipkart_advantage']
#IGNORE_MARKETPLACE = []

@csrf_exempt
#@login_required
#@get_admin_user
def book_trial(request, user=''):
    full_name = request.POST.get('full_name')
    email = request.POST.get('email')
    contact = request.POST.get('contact')
    company = request.POST.get('company')

    book_instance = BookTrial.objects.filter(email=email)
    if not book_instance:
        hash_code = hashlib.md5(b'%s:%s' % (full_name, email)).hexdigest()
        book_trial = BookTrial.objects.create(full_name = full_name, email = email, contact = contact, company = company, hash_code=hash_code,
                     status=1)
        html = '<p>link: http://anant.mieone.com:9001/#/signup?hashcode='+hash_code+'</p>'
        send_mail([email], 'StokeOne 30 day trial', html)
        status = "Added Successfully"
    else:
        status = "Email Already exists"
    return HttpResponse(status)


