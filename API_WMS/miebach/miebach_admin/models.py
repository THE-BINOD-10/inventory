from django.db import models
from django.contrib.auth.models import User,Group
from miebach_utils import BigAutoField
from datetime import date
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.

class ZoneMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    zone = models.CharField(max_length=64)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ZONE_MASTER'
        unique_together = ('user', 'zone')
        index_together = ('user', 'zone')

    def __unicode__(self):
        return str(self.zone)

    def natural_key(self):
        return {'id': self.id, 'user': self.user, 'zone': self.zone}

class SKUMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    sku_code = models.CharField(max_length=128)
    wms_code = models.CharField(max_length=128)
    sku_desc = models.CharField(max_length=350, default='')
    sku_group = models.CharField(max_length=64, default='')
    sku_type = models.CharField(max_length=64, default='')
    sku_category = models.CharField(max_length=64, default='')
    sku_class = models.CharField(max_length=64, default='')
    sku_brand = models.CharField(max_length=64, default='')
    style_name = models.CharField(max_length=64, default='')
    sku_size = models.CharField(max_length=64, default='')
    product_group = models.CharField(max_length=64, default='')
    zone = models.ForeignKey(ZoneMaster, null=True, blank=True, default = None)
    threshold_quantity = models.FloatField(default=0)
    online_percentage = models.PositiveIntegerField()
    discount_percentage = models.PositiveIntegerField(default=0)
    price = models.FloatField(default=0)
    mrp = models.FloatField(default=0)
    image_url = models.URLField(default='')
    qc_check = models.IntegerField(default=0)
    sequence = models.PositiveIntegerField(default=0)
    status = models.IntegerField(default=1)
    relation_type = models.CharField(max_length=32, default = '')
    measurement_type = models.CharField(max_length=32, default = '')
    sale_through = models.CharField(max_length=32, default = '')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_MASTER'
        unique_together = ('user', 'sku_code', 'wms_code')
        index_together = ('user', 'sku_code', 'wms_code')

    def __unicode__(self):
        return str(self.sku_code)

    def natural_key(self):
        return {'id': self.id, 'sku_code': self.sku_code, 'wms_code': self.wms_code,
                'sku_desc': self.sku_desc, 'sku_group': self.sku_group, 'sku_type': self.sku_type,
                'sku_category': self.sku_category, 'sku_class': self.sku_class, 'zone': self.zone.zone,
                'threshold_quantity': self.threshold_quantity, 'online_percentage': self.online_percentage,
                'discount_percentage': self.discount_percentage, 'price': self.price, 'image_url': self.image_url,
                'qc_check': self.qc_check, 'status': self.status, 'relation_type': self.relation_type}

class LocationMaster(models.Model):
    id = BigAutoField(primary_key=True)
    zone = models.ForeignKey(ZoneMaster)
    location = models.CharField(max_length=64)
    max_capacity = models.FloatField(default=0)
    fill_sequence = models.PositiveIntegerField()
    pick_sequence = models.PositiveIntegerField()
    filled_capacity = models.FloatField(default=0)
    pallet_capacity = models.FloatField(default=0)
    pallet_filled = models.FloatField(default=0)
    lock_status = models.CharField(max_length=64,default='')
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'LOCATION_MASTER'
        unique_together = ('zone', 'location')
        index_together = ('zone', 'location')

    def __unicode__(self):
        return self.location

class SupplierMaster(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    user = models.PositiveIntegerField()
    name = models.CharField(max_length=256)
    address = models.CharField(max_length=256)
    city = models.CharField(max_length=64)
    state = models.CharField(max_length=64)
    country = models.CharField(max_length=64)
    pincode = models.CharField(max_length=64)
    phone_number = models.CharField(max_length=32)
    email_id = models.EmailField(max_length=64)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SUPPLIER_MASTER'
        index_together = ('name', 'user')

    def __unicode__(self):
        return str(self.name)

class SKUSupplier(models.Model):
    id = BigAutoField(primary_key=True)
    supplier = models.ForeignKey(SupplierMaster)
    supplier_type = models.CharField(max_length=32)
    sku = models.ForeignKey(SKUMaster)
    preference = models.CharField(max_length=32)
    moq = models.FloatField(default=0)
    supplier_reference = models.CharField(max_length=256, default='')
    supplier_code = models.CharField(max_length=128, default='')
    price = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_SUPPLIER_MAPPING'
        index_together = ('supplier', 'sku')

    def __unicode__(self):
        return str(self.sku) + " : " + str(self.supplier)

class OrderDetail(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    #order_id = models.BigIntegerField()
    order_id = models.DecimalField(max_digits=35, decimal_places=0, primary_key=True)
    original_order_id = models.CharField(max_length=128,default='')
    customer_id = models.PositiveIntegerField(default=0)
    customer_name = models.CharField(max_length=256,default='')
    email_id = models.EmailField(max_length=64, default='')
    address = models.CharField(max_length=256,default='')
    telephone = models.CharField(max_length=128, default='')
    sku = models.ForeignKey(SKUMaster)
    title = models.CharField(max_length=256, default='')
    quantity = models.FloatField(default=0)
    invoice_amount = models.FloatField(default=0)
    shipment_date = models.DateTimeField()
    marketplace = models.CharField(max_length=256, default='')
    order_code = models.CharField(max_length=128, default='')
    vat_percentage = models.FloatField(default=0)
    status = models.CharField(max_length=32)
    sku_code = models.CharField(max_length=256, default='')
    city = models.CharField(max_length=60, default='')
    state = models.CharField(max_length=60, default='')
    pin_code = models.PositiveIntegerField(default=0)
    remarks = models.CharField(max_length=128, default='')
    payment_mode = models.CharField(max_length=64, default='')
    payment_received = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_DETAIL'
        unique_together = ('order_id','sku','order_code')
        index_together = ('order_id','sku','order_code')

    def __unicode__(self):
        return str(self.sku)

class OrderCharges(models.Model):
    id = BigAutoField(primary_key=True)
    order_id = models.CharField(max_length=128, default='')
    user = models.ForeignKey(User, blank=True, null=True)
    charge_name = models.CharField(max_length=128, default='')
    charge_amount = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_CHARGES'

class SKUQuantity(models.Model):
    id = BigAutoField(primary_key=True)
    sku = models.ForeignKey(SKUMaster)
    location = models.ForeignKey(LocationMaster)
    quantity = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_QUANTITY'

    def __unicode__(self):
        return str(self.sku)

class VendorMaster(models.Model):
    user = models.PositiveIntegerField()
    vendor_id = models.PositiveIntegerField()
    name = models.CharField(max_length=256)
    address = models.CharField(max_length=256)
    city = models.CharField(max_length=64)
    state = models.CharField(max_length=64)
    country = models.CharField(max_length=64)
    pincode = models.CharField(max_length=64)
    phone_number = models.CharField(max_length=32)
    email_id = models.EmailField(max_length=64)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'VENDOR_MASTER'

    def __unicode__(self):
        return str(self.name)

class OpenPO(models.Model):
    id = BigAutoField(primary_key=True)
    supplier = models.ForeignKey(SupplierMaster, blank=True, null=True)
    vendor = models.ForeignKey(VendorMaster, blank=True, null=True)
    sku = models.ForeignKey(SKUMaster)
    order_quantity = models.FloatField(default=0)
    price = models.FloatField()
    wms_code = models.CharField(max_length=32, default='')
    po_name = models.CharField(max_length=32,default='')
    supplier_code = models.CharField(max_length=32, default='')
    order_type = models.CharField(max_length=32, default='SR')
    remarks = models.CharField(max_length=256, default='')
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'OPEN_PO'

    def __unicode__(self):
        return str(str(self.sku) + " : " + str(self.supplier))

class PurchaseOrder(models.Model):
    id = BigAutoField(primary_key=True)
    order_id = models.PositiveIntegerField()
    open_po = models.ForeignKey(OpenPO, blank=True, null=True)
    received_quantity = models.FloatField(default=0)
    saved_quantity = models.FloatField(default=0)
    po_date = models.DateTimeField(auto_now_add=True)
    ship_to = models.CharField(max_length=64,default='')
    status = models.CharField(max_length=32)
    prefix = models.CharField(max_length=32, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PURCHASE_ORDER'

    def __unicode__(self):
        return str(self.id)

class JobOrder(models.Model):
    id = BigAutoField(primary_key=True)
    product_code = models.ForeignKey(SKUMaster)
    vendor = models.ForeignKey(VendorMaster, blank=True, null=True)
    product_quantity = models.FloatField(default=0)
    received_quantity = models.FloatField(default=0)
    saved_quantity = models.FloatField(default=0)
    job_code = models.PositiveIntegerField(default=0)
    jo_reference = models.PositiveIntegerField(default=0)
    order_type = models.CharField(max_length=32, default='SP')
    status = models.CharField(max_length=32, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'JOB_ORDER'
        unique_together = ('product_code', 'job_code', 'jo_reference')

class POLocation(models.Model):
    id = BigAutoField(primary_key=True)
    purchase_order = models.ForeignKey(PurchaseOrder, blank=True, null=True)
    job_order = models.ForeignKey(JobOrder, blank=True, null=True)
    location = models.ForeignKey(LocationMaster, blank=True, null=True)
    quantity = models.FloatField(default=0)
    original_quantity = models.FloatField(default=0)
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PO_LOCATION'

class PalletDetail(models.Model):
    id = BigAutoField(primary_key = True)
    user = models.PositiveIntegerField()
    pallet_code = models.CharField(max_length = 64)
    quantity = models.FloatField(default=0)
    status = models.IntegerField(max_length=1, default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PALLET_DETAIL'

class PalletMapping(models.Model):
    id = BigAutoField(primary_key = True)
    pallet_detail = models.ForeignKey(PalletDetail, blank=True, null=True)
    po_location = models.ForeignKey(POLocation, blank=True, null=True)
    status = models.IntegerField(max_length=1,default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PALLET_MAPPING'

class StockDetail(models.Model):
    id = BigAutoField(primary_key=True)
    receipt_number = models.PositiveIntegerField()
    receipt_date = models.DateTimeField()
    receipt_type = models.CharField(max_length=32, default='')
    sku = models.ForeignKey(SKUMaster)
    location = models.ForeignKey(LocationMaster)
    pallet_detail = models.ForeignKey(PalletDetail, blank=True, null=True)
    quantity = models.FloatField(default=0)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'STOCK_DETAIL'
        unique_together = ('receipt_number', 'receipt_date', 'sku', 'location', 'pallet_detail')
        index_together = ('sku', 'location', 'quantity')

    def __unicode__(self):
        return str(self.sku) + " : " + str(self.location)

class Picklist(models.Model):
    id = BigAutoField(primary_key=True)
    order = models.ForeignKey(OrderDetail, blank=True, null=True)
    stock = models.ForeignKey(StockDetail, blank=True, null=True)
    sku_code = models.CharField(max_length=60, default='', blank=True)
    picklist_number = models.PositiveIntegerField()
    reserved_quantity = models.FloatField(default=0)
    picked_quantity = models.FloatField(default=0)
    remarks = models.CharField(max_length=100)
    order_type = models.CharField(max_length=100, default='')
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PICKLIST'
        index_together = ('picklist_number', 'order', 'stock')

    def __unicode__(self):
        return str(self.picklist_number)

class PicklistLocation(models.Model):
    id = BigAutoField(primary_key=True)
    picklist = models.ForeignKey(Picklist)
    stock = models.ForeignKey(StockDetail)
    quantity = models.FloatField(default=0)
    reserved = models.FloatField(default=0)
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PICKLIST_LOCATION'
        index_together = ('picklist', 'stock', 'reserved')

class MiscDetail(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    misc_type = models.CharField(max_length=64)
    misc_value = models.CharField(max_length=64)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'MISC_DETAIL'
        unique_together = ('user', 'misc_type')

class CycleCount(models.Model):
    id = BigAutoField(primary_key=True)
    cycle = models.PositiveIntegerField()
    sku = models.ForeignKey(SKUMaster)
    location = models.ForeignKey(LocationMaster)
    quantity = models.FloatField(default=0)
    seen_quantity = models.FloatField(default=0)
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CYCLE_COUNT'
        unique_together = ('cycle','sku','location','creation_date')

    def __unicode__(self):
        return str(self.cycle)

class InventoryAdjustment(models.Model):
    id = BigAutoField(primary_key=True)
    cycle = models.ForeignKey(CycleCount)
    adjusted_location = models.CharField(max_length=64)
    adjusted_quantity = models.FloatField(default=0)
    reason = models.TextField()
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'INVENTORY_ADJUSTMENT'
        unique_together = ('cycle', 'adjusted_location')

    def __unicode__(self):
        return str(self.id)

class Issues(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User)
    issue_title = models.CharField(max_length=256)
    name = models.CharField(max_length=256, default='')
    email_id = models.EmailField(max_length=64, default='')
    issue_description = models.TextField()
    status = models.CharField(max_length=64)
    priority = models.CharField(max_length=64)
    resolved_description = models.TextField()
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ISSUES'

class WebhookData(models.Model):
    id = BigAutoField(primary_key=True)
    data = models.TextField()
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'WEBHOOK_DATA'

class QualityCheck(models.Model):
    id = BigAutoField(primary_key=True)
    purchase_order = models.ForeignKey(PurchaseOrder)
    accepted_quantity = models.FloatField(default=0)
    po_location = models.ForeignKey(POLocation)
    rejected_quantity = models.FloatField(default=0)
    putaway_quantity = models.FloatField(default=0)
    status = models.CharField(max_length=64)
    reason = models.CharField(max_length=256)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'QUALITY_CHECK'

class OrderShipment(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    shipment_number = models.PositiveIntegerField()
    shipment_date = models.DateTimeField()
    truck_number = models.CharField(max_length=64)
    shipment_reference = models.CharField(max_length=64)
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_SHIPMENT'

class OrderPackaging(models.Model):
    id = BigAutoField(primary_key=True)
    order_shipment = models.ForeignKey(OrderShipment)
    package_reference = models.CharField(max_length=64)
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_PACKAGING'

class ShipmentInfo(models.Model):
    id = BigAutoField(primary_key=True)
    order_shipment = models.ForeignKey(OrderShipment)
    order_packaging = models.ForeignKey(OrderPackaging)
    order = models.ForeignKey(OrderDetail)
    shipping_quantity = models.FloatField(default=0)
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SHIPMENT_INFO'
        unique_together = ('order_shipment', 'order_packaging', 'order')

class SKUStock(models.Model):
    id = BigAutoField(primary_key=True)
    sku = models.ForeignKey(SKUMaster)
    total_quantity = models.FloatField(default=0)
    online_quantity = models.FloatField(default=0)
    offline_quantity = models.FloatField(default=0)
    status = models.IntegerField(max_length=1, default=0)

    class Meta:
        db_table = 'SKU_STOCK'

class CustomerMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    customer_id = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=256)
    last_name = models.CharField(max_length=256, default='')
    address = models.CharField(max_length=256)
    city = models.CharField(max_length=64)
    state = models.CharField(max_length=64)
    country = models.CharField(max_length=64)
    pincode = models.CharField(max_length=64)
    phone_number = models.CharField(max_length=32)
    email_id = models.EmailField(max_length=64)
    tin_number = models.CharField(max_length=64, default='')
    credit_period = models.PositiveIntegerField(default=0)
    status = models.IntegerField(max_length=1, default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CUSTOMER_MASTER'

class CustomerUserMapping(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User, blank=True, null=True)
    customer = models.ForeignKey(CustomerMaster, blank=True, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CUSTOMER_USER_MAPPING'


class OrderReturns(models.Model):
    id = BigAutoField(primary_key=True)
    return_id = models.CharField(max_length=256)
    order = models.ForeignKey(OrderDetail, blank=True, null=True)
    return_date = models.DateTimeField(auto_now_add=True)
    quantity = models.FloatField(default=0)
    damaged_quantity = models.FloatField(default=0)
    sku = models.ForeignKey(SKUMaster, blank=True, null=True)
    return_type = models.CharField(max_length=64, default='')
    reason = models.CharField(max_length=256,default='')
    status = models.CharField(max_length=64)
    marketplace = models.CharField(max_length=32,default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_RETURNS'

class UserProfile(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.OneToOneField(User)
    phone_number = models.CharField(max_length=32, default='')
    birth_date = models.DateTimeField(auto_now_add=True, default=date.today)
    is_active = models.IntegerField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)
    timezone = models.CharField(max_length=64,default='')
    swx_id = models.IntegerField(default=None, blank=True, null=True)
    prefix = models.CharField(max_length=64,default='')
    company_name = models.CharField(max_length=256, default='')
    location = models.CharField(max_length=60, default='')
    city = models.CharField(max_length=60, default='')
    state = models.CharField(max_length=60, default='')
    country = models.CharField(max_length=60, default='')
    pin_code = models.PositiveIntegerField(default=0)
    address = models.CharField(max_length=256, default='')
    multi_warehouse = models.IntegerField(default=0)
    is_trail = models.IntegerField(default=0)
    api_hash = models.CharField(max_length=256, default='')
    setup_status = models.CharField(max_length=60, default='completed')
    user_type = models.CharField(max_length=60, default='warehouse_user')

    class Meta:
        db_table = 'USER_PROFILE'

    def __unicode__(self):
        return str(self.user)

class UserAccessTokens(models.Model):
    id = BigAutoField(primary_key=True)
    user_profile = models.OneToOneField(UserProfile)
    code = models.CharField(max_length=64, default='')
    access_token = models.CharField(max_length=320, default='', blank=True, null=True)
    refresh_token = models.CharField(max_length=64, default='', blank=True, null=True)
    token_type = models.CharField(max_length=64)
    expires_in = models.IntegerField()
    app_host = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'USER_ACCESS_TOKENS'

    def __unicode__(self):
        return str(self.user_profile)

class SWXMapping(models.Model):
    id = BigAutoField(primary_key = True)
    swx_id = models.PositiveIntegerField()
    local_id = models.PositiveIntegerField(default=0)
    swx_type = models.CharField(max_length = 32, default = '')
    app_host = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SWX_MAPPING'
        unique_together = ('swx_id', 'local_id', 'swx_type')

class LRDetail(models.Model):
    id = BigAutoField(primary_key = True)
    lr_number = models.CharField(max_length = 64)
    carrier_name = models.CharField(max_length = 64)
    quantity = models.FloatField(default=0)
    purchase_order =  models.ForeignKey(PurchaseOrder)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'LR_DETAIL'

class POIMEIMapping(models.Model):
    id = BigAutoField(primary_key = True)
    purchase_order =  models.ForeignKey(PurchaseOrder)
    imei_number = models.CharField(max_length = 64, default = '')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PO_IMEI_MAPPING'
        unique_together = ('purchase_order', 'imei_number')

class OrderIMEIMapping(models.Model):
    id = BigAutoField(primary_key = True)
    order = models.ForeignKey(OrderDetail)
    po_imei = models.ForeignKey(POIMEIMapping, blank=True, null=True)
    imei_number =  models.CharField(max_length = 64, default = '')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_IMEI_MAPPING'

class ReturnsLocation(models.Model):
    id = BigAutoField(primary_key=True)
    returns = models.ForeignKey(OrderReturns, blank=True, null=True)
    location = models.ForeignKey(LocationMaster, blank=True, null=True)
    quantity = models.FloatField(default=0)
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'RETURNS_LOCATION'

class CancelledLocation(models.Model):
    id = BigAutoField(primary_key=True)
    picklist = models.ForeignKey(Picklist, blank=True, null=True)
    location = models.ForeignKey(LocationMaster, blank=True, null=True)
    quantity = models.FloatField(default=0)
    status = models.IntegerField(max_length=1, default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CANCELLED_LOCATION'

class UserGroups(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User)
    admin_user = models.ForeignKey(User, related_name='admin_user', blank=True, null=True)

    class Meta:
        db_table = 'USER_GROUPS'

class AdminGroups(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.OneToOneField(User, blank=True, null=True)
    group = models.OneToOneField(Group)

    class Meta:
        db_table = 'ADMIN_GROUPS'

class StockMismatch(models.Model):
    id = BigAutoField(primary_key=True)
    sku = models.ForeignKey(SKUMaster)
    swx_count = models.PositiveIntegerField(default=0)
    wms_count = models.PositiveIntegerField(default=0)
    difference = models.PositiveIntegerField(default=0)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'STOCK_MISMATCH'


class SkuTypeMapping(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    prefix = models.CharField(max_length=32, default='')
    item_type = models.CharField(max_length=32, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_TYPE_MAPPING'

class QCSerialMapping(models.Model):
    id = BigAutoField(primary_key=True)
    quality_check = models.ForeignKey(QualityCheck)
    serial_number = models.ForeignKey(POIMEIMapping)
    status = models.CharField(max_length=32, default='')
    reason = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'QC_SERIAL_MAPPING'

class MarketplaceMapping(models.Model):
    id = BigAutoField(primary_key=True)
    sku = models.ForeignKey(SKUMaster, blank=True, null=True)
    marketplace_code = models.CharField(max_length=64, default='')
    sku_type = models.CharField(max_length=64, default='')
    description = models.CharField(max_length=256, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'MARKETPLACE_MAPPING'
        index_together = ('sku', 'marketplace_code', 'sku_type')

class JOMaterial(models.Model):
    job_order = models.ForeignKey(JobOrder)
    material_code = models.ForeignKey(SKUMaster)
    material_quantity = models.FloatField(default = 0)
    status = models.IntegerField(max_length=1, default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'JO_MATERIAL'

class MaterialPicklist(models.Model):
    jo_material = models.ForeignKey(JOMaterial)
    reserved_quantity = models.FloatField(default=0)
    picked_quantity = models.FloatField(default=0)
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'MATERIAL_PICKLIST'

class RMLocation(models.Model):
    id = BigAutoField(primary_key=True)
    material_picklist = models.ForeignKey(MaterialPicklist)
    stock = models.ForeignKey(StockDetail, blank=True, null=True)
    reserved = models.FloatField(default=0)
    quantity = models.FloatField(default = 0)
    status = models.IntegerField(max_length=1, default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'RM_LOCATION'



class SKURelation(models.Model):
    id = BigAutoField(primary_key=True)
    parent_sku = models.ForeignKey(SKUMaster, blank=True, null=True, related_name='parent_sku')
    member_sku = models.ForeignKey(SKUMaster, blank=True, null=True, related_name='member_sku')
    relation_type = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_RELATION'
        unique_together = ('parent_sku', 'member_sku', 'relation_type')

    def __unicode__(self):
        return '%s: %s || %s' % (self.relation_type, self.parent_sku, self.member_sku)

class StatusTracking(models.Model):
    id = BigAutoField(primary_key=True)
    status_id = models.PositiveIntegerField()
    status_type = models.CharField(max_length=64, default='')
    status_value = models.CharField(max_length=64, default='')
    quantity = models.FloatField(default=0)
    original_quantity = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'STATUS_TRACKING'

class StatusTrackingSummary(models.Model):
    id = BigAutoField(primary_key=True)
    status_tracking = models.ForeignKey(StatusTracking, blank=True, null=True)
    processed_stage = models.CharField(max_length=64, default='')
    processed_quantity = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'STATUS_TRACKING_SUMMARY'

class BOMMaster(models.Model):
    id = BigAutoField(primary_key=True)
    material_sku = models.ForeignKey(SKUMaster, default = None)
    product_sku = models.ForeignKey(SKUMaster, related_name='product_sku', blank=True, null=True)
    material_quantity = models.FloatField(default = 0)
    wastage_percent = models.FloatField(default = 0)
    unit_of_measurement = models.CharField(max_length=10, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'BOM_MASTER'
        unique_together = ('material_sku', 'product_sku')

class CustomerSKU(models.Model):
    id = BigAutoField(primary_key=True)
    customer_name = models.ForeignKey(CustomerMaster)
    sku = models.ForeignKey(SKUMaster)
    price = models.FloatField(default=0)
    discount = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CUSTOMER_SKU'
        unique_together = ('customer_name', 'sku')

class SKUGroups(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    group = models.CharField(max_length=60, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_GROUPS'
        unique_together = ('user', 'group')

class LocationGroups(models.Model):
    id = BigAutoField(primary_key=True)
    location = models.ForeignKey(LocationMaster)
    group = models.CharField(max_length=60, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'LOCATION_GROUPS'
        unique_together = ('location', 'group')

class OpenST(models.Model):
    id = BigAutoField(primary_key=True)
    warehouse = models.ForeignKey(User)
    sku = models.ForeignKey(SKUMaster)
    order_quantity = models.FloatField(default=0)
    price = models.FloatField()
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'OPEN_ST'

    def __unicode__(self):
        return str(str(self.sku) + " : " + str(self.warehouse_id))

class STPurchaseOrder(models.Model):
    id = BigAutoField(primary_key=True)
    po = models.ForeignKey(PurchaseOrder)
    open_st = models.ForeignKey(OpenST)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ST_PURCHASE_ORDER'

    def __unicode__(self):
        return str(self.po_id)

class StockTransfer(models.Model):
    id = BigAutoField(primary_key=True)
    order_id = models.BigIntegerField()
    st_po = models.ForeignKey(STPurchaseOrder)
    sku = models.ForeignKey(SKUMaster)
    invoice_amount = models.FloatField(default=0)
    quantity = models.FloatField(default=0)
    shipment_date = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'STOCK_TRANSFER'
        unique_together = ('order_id','st_po', 'sku')

    def __unicode__(self):
        return str(self.order_id)

class STOrder(models.Model):
    id = BigAutoField(primary_key=True)
    picklist = models.ForeignKey(Picklist)
    stock_transfer = models.ForeignKey(StockTransfer)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ST_ORDER'

    def __unicode__(self):
        return str(self.picklist_id) + ":" + str(self.stock_transfer)


class CustomerOrderSummary(models.Model):
    order = models.ForeignKey(OrderDetail)
    discount = models.FloatField(default = 0)
    vat = models.FloatField(default=0)
    mrp = models.FloatField(default=0)
    issue_type = models.CharField(max_length=64, default='')
    tax_value = models.FloatField(default=0)
    tax_type = models.CharField(max_length=64, default='')
    order_taken_by = models.CharField(max_length=128, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=24, default='')
    class Meta:
        db_table = 'CUSTOMER_ORDER_SUMMARY'

class CategoryDiscount(models.Model):
    user = models.ForeignKey(User)
    category = models.CharField(max_length=64, default='')
    discount = models.FloatField(default = 0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_CATEGORY_DISCOUNT'
        unique_together = ('user', 'category')

class TaxMaster(models.Model):
    city = models.CharField(max_length=64, default='')
    state = models.CharField(max_length=64, default='')
    tax_type = models.CharField(max_length=64, default='')
    tax_percentage = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'TAX_MASTER'

class SalesPersons(models.Model):
    user = models.OneToOneField(User)
    user_name = models.CharField(max_length=64, default='')
    first_name = models.CharField(max_length=64, default='')
    last_name = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SALES_PERSONS'

class ProductGroups(models.Model):
    group_type = models.CharField(max_length=64)
    group_value = models.CharField(max_length=64)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PRODUCT_GROUPS'

class ProductProperties(models.Model):
    user = models.ForeignKey(User, default=None)
    name = models.CharField(max_length=64, default='')
    property_type = models.CharField(max_length=64, default='')
    property_name = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PRODUCT_PROPERTIES'

class ProductAttributes(models.Model):
    product_property = models.ForeignKey(ProductProperties, default=None)
    attribute_name = models.CharField(max_length=64, default='')
    description = models.CharField(max_length=128, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PRODUCT_ATTRIBUTES'


class SKUFields(models.Model):
    sku = models.ForeignKey(SKUMaster)
    field_id = models.PositiveIntegerField(default=0)
    field_type = models.CharField(max_length=128, default='')
    field_value = models.CharField(max_length=128, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_FIELDS'

class OrderJson(models.Model):
    order = models.ForeignKey(OrderDetail)
    json_data = models.CharField(max_length=1000, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_JSON'


class ProductImages(models.Model):
    image_id = models.PositiveIntegerField(default=0)
    image_url = models.CharField(max_length=256, default='')
    image_type = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PRODUCT_IMAGES'

class ProductGroupsMapping(models.Model):
    group_id = models.PositiveIntegerField()
    product_groups = models.ForeignKey(ProductGroups)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PRODUCT_GROUPS_MAPPING'

class customerGroupsMapping(models.Model):
    customer =  models.ForeignKey(CustomerMaster)
    group_id = models.PositiveIntegerField()
    tax_type = models.CharField(max_length=64, default='')
    tax_percentage = models.FloatField(default=0)
    discount_type = models.CharField(max_length=64, default='')
    discount_percentage = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CUSTOMER_GROUPS_MAPPING'

class SKUImages(models.Model):
    sku =  models.ForeignKey(SKUMaster)
    image_url = models.CharField(max_length=256, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_IMAGES'
        unique_together = ('sku', 'image_url')


class RWOrder(models.Model):
    vendor = models.ForeignKey(VendorMaster)
    job_order =models.ForeignKey(JobOrder)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'RW_ORDER'

class RWPurchase(models.Model):
    rwo =  models.ForeignKey(RWOrder)
    purchase_order = models.ForeignKey(PurchaseOrder)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'RW_PURCHASE'

class ShipmentTracking(models.Model):
    shipment =  models.ForeignKey(ShipmentInfo)
    ship_status = models.CharField(max_length=64)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SHIPMENT_TRACKING'
        unique_together = ('shipment', 'ship_status')

class Marketplaces(models.Model):
    user = models.PositiveIntegerField()
    name = models.CharField(max_length=128)
    status = models.IntegerField(default=1)
    image_url = models.CharField(max_length=256, default='')
    last_synced = models.DateTimeField(auto_now_add=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'MARKETPLACES'
        unique_together = ('user', 'name')

class ProductTagging(models.Model):
    user = models.OneToOneField(User)
    product_type = models.CharField(max_length=64, default='')
    tag_type = models.CharField(max_length=64, default='')
    tag_value = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PRODUCT_TAGGING'
        unique_together = ('product_type', 'tag_type', 'tag_value')

class ProductionStages(models.Model):
    user = models.PositiveIntegerField()
    stage_name = models.CharField(max_length=64, default='')
    order = models.PositiveIntegerField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PRODUCTION_STAGES'
        unique_together = ('user', 'stage_name')
    def __unicode__(self):
        return self.stage_name

class OrdersAPI(models.Model):
    user = models.PositiveIntegerField(default=0)
    order_type = models.CharField(max_length=64, default='')
    order_id = models.BigIntegerField(default=0)
    engine_type = models.CharField(max_length=64, default='')
    status = models.PositiveIntegerField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDERS_API'
        unique_together = ('order_type', 'order_id', 'engine_type')

class OrdersInvoice(models.Model):
    invoice_number = models.PositiveIntegerField(default=0)
    orders_api = models.ForeignKey(OrdersAPI, blank=True, null=True)
    quantity_sent = models.FloatField(default=0)
    status = models.PositiveIntegerField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDERS_INVOICE'

class OrdersTrack(models.Model):
    user = models.PositiveIntegerField(default=0)
    sku_code = models.CharField(max_length=64, default='')
    order_id = models.CharField(max_length=64, default='')
    reason = models.CharField(max_length=126, default='')
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDERS_TRACK'
        unique_together = ('user', 'sku_code', 'order_id')

class POTaxMaster(models.Model):
    user = models.PositiveIntegerField(default=0)
    state = models.CharField(max_length=64, default='')
    product_group = models.CharField(max_length=64, default='')
    tax_percentage = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PO_TAX_MASTER'

class BookTrial(models.Model):
    full_name = models.CharField(max_length=64, default='')
    email = models.EmailField(max_length=64)
    contact = models.CharField(max_length=20, default='')
    company = models.CharField(max_length=64, default='')
    hash_code = models.CharField(max_length=256, default='')
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
	db_table = "BOOK_TRIAL"

class VendorStock(models.Model):
    id = BigAutoField(primary_key=True)
    receipt_number = models.PositiveIntegerField()
    receipt_date = models.DateTimeField()
    vendor = models.ForeignKey(VendorMaster, blank=True, null=True)
    sku = models.ForeignKey(SKUMaster)
    quantity = models.FloatField(default=0)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'VENDOR_STOCK'
        unique_together = ('receipt_number', 'receipt_date', 'vendor', 'sku')

class VendorPicklist(models.Model):
    jo_material = models.ForeignKey(JOMaterial, blank=True, null=True)
    reserved_quantity = models.FloatField(default=0)
    picked_quantity = models.FloatField(default=0)
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'VENDOR_PICKLIST'

class OrderMapping(models.Model):
    order = models.ForeignKey(OrderDetail, blank=True, null=True)
    mapping_id = models.PositiveIntegerField(default=0)
    mapping_type = models.CharField(max_length=32, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_MAPPING'

class SizeMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    size_name = models.CharField(max_length=64, default='')
    size_value = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SIZE_MASTER'
        unique_together = ('user', 'size_name')

class Brands(models.Model):
    user = models.ForeignKey(User)
    brand_name = models.CharField(max_length=64, default='')

    class Meta:
	db_table = 'BRANDS'
    def __unicode__(self):
	return self.brand_name

class UserBrand(models.Model):
    user = models.ForeignKey(User)
    brand_list = models.ManyToManyField(Brands)

    class Meta:
        db_table = 'USER_BRAND'

class GroupStage(models.Model):
    user = models.ForeignKey(User)
    stages_list = models.ManyToManyField(ProductionStages)

    class Meta:
	db_table = 'GROUP_STAGE'

class Integrations(models.Model):
    user = models.PositiveIntegerField()
    name = models.CharField(max_length=64, default='')
    api_instance = models.CharField(max_length=64, default='')
    client_id = models.CharField(max_length=64, default='')
    secret = models.CharField(max_length=256, default='')
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'INTEGRATIONS'

class PaymentSummary(models.Model):
    id = BigAutoField(primary_key=True)
    order = models.ForeignKey(OrderDetail, blank=True, null=True)
    payment_received = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PAYMENT_SUMMARY'

class FileDump(models.Model):
    user = models.ForeignKey(User, blank=True, null=True)
    name = models.CharField(max_length=128, default='')
    checksum = models.CharField(max_length=256, default='')
    path = models.CharField(max_length=256, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'FILE_DUMP'

class UserStages(models.Model):
    user = models.ForeignKey(User)
    stages_list = models.ManyToManyField(ProductionStages)

    class Meta:
	db_table = 'USER_STAGE'

class GroupBrand(models.Model):
    group = models.ForeignKey(Group)
    brand_list = models.ManyToManyField(Brands)

    class Meta:
        db_table = 'GROUP_BRAND'

class GroupStages(models.Model):
    group = models.ForeignKey(Group)
    stages_list = models.ManyToManyField(ProductionStages)

    class Meta:
        db_table = 'GROUP_STAGE_MAP'


class ContactUs(models.Model):
    full_name = models.CharField(max_length=64, default='')
    email = models.EmailField(max_length=64)
    contact = models.CharField(max_length=20, default='')
    company = models.CharField(max_length=64, default='')
    query = models.CharField(max_length=255, default='')
    added_dt = models.DateTimeField(auto_now_add=True)

    class Meta:
	db_table = "CONTACT_US"
