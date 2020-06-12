# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User

from django.test import TestCase
from stockone_integrations.views import Integrations as intg

# Create your tests here.


data_dict = { 'sku_code' : 'GPR_1' }

cu = User.objects.get(pk=2)
cu

newintgobj = intg(cu, 'netsuiteIntegration')

newintgobj.is_connected



class NetsuiteIntegrationTest(TestCase):
    def setUp(self):
        data_dict = { 'sku_code' : 'GPR_1' }
        cu = User.objects.get(pk=2)
        self.newintgobj = intg(cu, 'netsuiteIntegration')
        print("Conneted::%s" % (self.newintgobj.is_connected))

    def integrateSkuMaster(self):
        print(self.newintgobj.integrateSkuMaster(data_dict, 'sku_code'))
        
