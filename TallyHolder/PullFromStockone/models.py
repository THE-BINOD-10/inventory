# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
# Create your models here.


class CustomerVendorMaster(models.Model):
    client_name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    customer_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    ip = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    port = models.CharField(max_length=6, blank=True, null=True, db_index=True)
    data = models.TextField(null=True, blank=True, default='')
    push_status = models.IntegerField(default=0, null=False, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "CUSTOMERVENDORMASTER"
        unique_together = (('client_name', 'customer_id'),)

    def __unicode__(self):
        return "Customer: %s, Status: %s, Created At: %s, Updated At: %s" %\
               (self.customer_id, self.push_status, self.created_at, self.updated_at)


class ItemMaster(models.Model):
    client_name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    item_code = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    ip = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    port = models.CharField(max_length=6, blank=True, null=True, db_index=True)
    data = models.TextField(null=True, blank=True, default='')
    push_status = models.IntegerField(default=0, null=False, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "ITEMMASTER"
        unique_together = (('client_name', 'item_code'),)

    def __unicode__(self):
        return "Customer: %s, Status: %s, Created At: %s, Updated At: %s" %\
               (self.item_code, self.push_status, self.created_at, self.updated_at)


class SalesInvoice(models.Model):
    client_name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    invoice_num = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    order_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    ip = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    port = models.CharField(max_length=6, blank=True, null=True, db_index=True)
    data = models.TextField(null=True, blank=True, default='')
    push_status = models.IntegerField(default=0, null=False, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "SALESINVOICE"
        unique_together = (('client_name', 'invoice_num', 'order_id'),)

    def __unicode__(self):
        return "Invoice: %s, Order Id: %s, Status: %s, Created At: %s, Updated At: %s" %\
               (self.invoice_num, self.order_id, self.push_status, self.created_at, self.updated_at)


class SalesReturn(SalesInvoice):
    class Meta:
        db_table = "SalesReturn"


class PurchaseInvoice(SalesInvoice):
    class Meta:
        db_table = "PURCHASEINVOICE"


class PurchaseReturn(SalesInvoice):
    class Meta:
        db_table = "PurchaseReturn"