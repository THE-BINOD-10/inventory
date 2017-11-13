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
import datetime
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
        html = '<p> Hi %s, </p> <p> Thanks for using our demo version . This is valid for 30 Days. </p> To signup please click given link </p><p>link: https://%s/#/signup?hashcode=%s </p>' %(full_name, "go.stockone.in", hash_code)
        send_mail([email], 'StockOne 30 day trial', html)
        status = "Added Successfully"

	subject = "NEW FREE TRIAL SIGNUP"
	body = "<p> Following user requested for FREE TRIAL</p>  <p> NAME : %s</p> <p> Email : %s</p> <p> CONTACT: %s</p> <p> COMPANY: %s</p>" %(full_name, email, contact, company)
	inform_mail(subject, body)
    else:
        status = "Email Already exists"
    return HttpResponse(status)

def inform_mail(subject, body):
    """sending mail to concerned Miebach team"""
    recipient = ['abhishek@headrun.com', 'sreekanth@mieone.com', 'vimal.nair@miebach.com', 'karthik@headrun.com', 'roopal@mieone.com', 'alkesh.karamkar@miebach.com', 'sameena@mieone.com']
    try:
    	send_mail(recipient, subject, body)
    except:
        print "some issue there"


@csrf_exempt 
def contact_us(request):
    full_name = request.POST.get('full_name')
    email = request.POST.get('email')
    contact = request.POST.get('contact')
    company = request.POST.get('company')
    query = request.POST.get('query')

    ContactUs.objects.create(full_name = full_name, email = email, contact= contact, company= company, query=query, added_dt = datetime.datetime.now())

    html = "<p>Hi %s </p> <p> Thanks for contacting us. </p> <p> Our team will get back to you shortly. </p> <p> Thanks, </p> <p> Mieone Team </p>" %(full_name)
    send_mail([email], 'StockOne Query Auto Response', html)
    status = "Success"
    subject = "NEW QUERY GENERATED"
    body = "<p> Following user created a query</p>  <p> NAME : %s</p> <p> Email : %s</p> <p> CONTACT: %s</p> <p> COMPANY: %s</p> <p> QUERY: %s</p>" %(full_name, email, contact, company, query)
    inform_mail(subject, body)

    return HttpResponse(status)

