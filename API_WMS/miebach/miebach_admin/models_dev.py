from django.db import models
from django.contrib.auth.models import User,Group
from miebach_utils import BigAutoField
from datetime import date

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

    def __unicode__(self):
        return str(self.zone)

class SKUMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    sku_code = models.CharField(max_length=64)
    wms_code = models.CharField(max_length=64)
    sku_desc = models.CharField(max_length=256)
    sku_group = models.CharField(max_length=64)
    sku_type = models.CharField(max_length=64)
    sku_category = models.CharField(max_length=64)
    sku_class = models.CharField(max_length=64)
    zone = models.ForeignKey(ZoneMaster, null=True, blank=True, default = None)
    threshold_quantity = models.PositiveIntegerField()
    online_percentage = models.PositiveIntegerField()
    discount_percentage = models.PositiveIntegerField(default=0)
    price = models.FloatField(default=0)
    image_url = models.URLField(default='')
    qc_check = models.IntegerField(default=0)
    status = models.IntegerField(default=1)
    relation_type = models.CharField(max_length=32, default = '')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_MASTER'
        unique_together = ('user', 'sku_code', 'wms_code')

    def __unicode__(self):
        return str(self.sku_code)

class LocationMaster(models.Model):
    id = BigAutoField(primary_key=True)
    zone = models.ForeignKey(ZoneMaster)
    location = models.CharField(max_length=64)
    max_capacity = models.PositiveIntegerField()
    fill_sequence = models.PositiveIntegerField()
    pick_sequence = models.PositiveIntegerField()
    filled_capacity = models.PositiveIntegerField(default=0)
    pallet_capacity = models.PositiveIntegerField(default=0)
    pallet_filled = models.PositiveIntegerField(default=0)
    lock_status = models.CharField(max_length=64,default='')
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'LOCATION_MASTER'
        unique_together = ('zone', 'location')

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

    def __unicode__(self):
        return str(self.name)

class SKUSupplier(models.Model):
    id = BigAutoField(primary_key=True)
    supplier = models.ForeignKey(SupplierMaster)
    supplier_type = models.CharField(max_length=32)
    sku = models.ForeignKey(SKUMaster)
    preference = models.CharField(max_length=32)
    moq = models.PositiveIntegerField()
    supplier_reference = models.CharField(max_length=256, default='')
    supplier_code = models.CharField(max_length=128, default='')
    price = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_SUPPLIER_MAPPING'

    def __unicode__(self):
        return str(self.sku) + " : " + str(self.supplier)

class OrderDetail(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    order_id = models.BigIntegerField()
    customer_id = models.PositiveIntegerField(default=0)
    customer_name = models.CharField(max_length=128,default='')
    email_id = models.EmailField(max_length=64, default='')
    address = models.CharField(max_length=256,default='')
    telephone = models.CharField(max_length=128, default='')
    sku = models.ForeignKey(SKUMaster)
    title = models.CharField(max_length=128)
    quantity = models.PositiveIntegerField()
    invoice_amount = models.FloatField(default=0)
    shipment_date = models.DateTimeField()
    marketplace = models.CharField(max_length=256, default='')
    order_code = models.CharField(max_length=128, default='')
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)
    sku_code = models.CharField(max_length=256, default='')

    class Meta:
        db_table = 'ORDER_DETAIL'
        unique_together = ('order_id','sku','order_code')

    def __unicode__(self):
        return str(self.sku)

class SKUQuantity(models.Model):
    id = BigAutoField(primary_key=True)
    sku = models.ForeignKey(SKUMaster)
    location = models.ForeignKey(LocationMaster)
    quantity = models.PositiveIntegerField()
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_QUANTITY'

    def __unicode__(self):
        return str(self.sku)

class OpenPO(models.Model):
    id = BigAutoField(primary_key=True)
    supplier = models.ForeignKey(SupplierMaster)
    sku = models.ForeignKey(SKUMaster)
    order_quantity = models.PositiveIntegerField()
    price = models.FloatField()
    wms_code = models.CharField(max_length=32, default='')
    po_name = models.CharField(max_length=32,default='')
    supplier_code = models.CharField(max_length=32, default='')
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
    received_quantity = models.PositiveIntegerField()
    saved_quantity = models.PositiveIntegerField(default=0)
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
    product_quantity = models.PositiveIntegerField()
    received_quantity = models.PositiveIntegerField()
    saved_quantity = models.PositiveIntegerField(default=0)
    job_code = models.PositiveIntegerField(default=0)
    jo_reference = models.PositiveIntegerField(default=0)
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
    quantity = models.PositiveIntegerField()
    original_quantity = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PO_LOCATION'

class PalletDetail(models.Model):
    id = BigAutoField(primary_key = True)
    user = models.PositiveIntegerField()
    pallet_code = models.CharField(max_length = 64)
    quantity = models.PositiveIntegerField()
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
    quantity = models.PositiveIntegerField()
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'STOCK_DETAIL'
        unique_together = ('receipt_number', 'receipt_date', 'sku', 'location', 'pallet_detail')

    def __unicode__(self):
        return str(self.sku) + " : " + str(self.location)

class Picklist(models.Model):
    id = BigAutoField(primary_key=True)
    order = models.ForeignKey(OrderDetail, blank=True, null=True)
    stock = models.ForeignKey(StockDetail, blank=True, null=True)
    sku_code = models.CharField(max_length=60, default='', blank=True)
    picklist_number = models.PositiveIntegerField()
    reserved_quantity = models.PositiveIntegerField()
    picked_quantity = models.PositiveIntegerField()
    remarks = models.CharField(max_length=100)
    order_type = models.CharField(max_length=100, default='')
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PICKLIST'

    def __unicode__(self):
        return str(self.picklist_number)

class PicklistLocation(models.Model):
    id = BigAutoField(primary_key=True)
    picklist = models.ForeignKey(Picklist)
    stock = models.ForeignKey(StockDetail)
    quantity = models.PositiveIntegerField()
    reserved = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PICKLIST_LOCATION'

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
    quantity = models.PositiveIntegerField()
    seen_quantity = models.PositiveIntegerField()
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
    adjusted_quantity = models.PositiveIntegerField()
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
    accepted_quantity = models.PositiveIntegerField()
    po_location = models.ForeignKey(POLocation)
    rejected_quantity = models.PositiveIntegerField()
    putaway_quantity = models.PositiveIntegerField()
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
    shipping_quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SHIPMENT_INFO'
        unique_together = ('order_shipment', 'order_packaging', 'order')

class SKUStock(models.Model):
    id = BigAutoField(primary_key=True)
    sku = models.ForeignKey(SKUMaster)
    total_quantity = models.PositiveIntegerField()
    online_quantity = models.PositiveIntegerField()
    offline_quantity = models.PositiveIntegerField()
    status = models.IntegerField(max_length=1, default=0)

    class Meta:
        db_table = 'SKU_STOCK'

class CustomerMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    name = models.CharField(max_length=256)
    last_name = models.CharField(max_length=256, default='')
    address = models.CharField(max_length=256)
    city = models.CharField(max_length=64)
    state = models.CharField(max_length=64)
    country = models.CharField(max_length=64)
    pincode = models.CharField(max_length=64)
    phone_number = models.CharField(max_length=32)
    email_id = models.EmailField(max_length=64)
    status = models.IntegerField(max_length=1, default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)
    role = models.CharField(max_length=64) 

    class Meta:
        db_table = 'CUSTOMER_MASTER'

class OrderReturns(models.Model):
    id = BigAutoField(primary_key=True)
    return_id = models.CharField(max_length=256)
    order = models.ForeignKey(OrderDetail, blank=True, null=True)
    return_date = models.DateTimeField(auto_now_add=True)
    quantity = models.PositiveIntegerField(default=0)
    sku = models.ForeignKey(SKUMaster, blank=True, null=True)
    status = models.CharField(max_length=64)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_RETURNS'

class UserProfile(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.OneToOneField(User)
    phone_number = models.CharField(max_length=32)
    birth_date = models.DateTimeField(auto_now_add=True, default=date.today)
    is_active = models.IntegerField()
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
    class Meta:
        db_table = 'USER_PROFILE'

    def __unicode__(self):
        return str(self.user)

class UserAccessTokens(models.Model):
    id = BigAutoField(primary_key=True)
    user_profile = models.OneToOneField(UserProfile)
    code = models.CharField(max_length=64)
    access_token = models.CharField(max_length=64)
    refresh_token = models.CharField(max_length=64)
    token_type = models.CharField(max_length=64)
    expires_in =  models.IntegerField()
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
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SWX_MAPPING'
        unique_together = ('swx_id', 'local_id', 'swx_type')

class LRDetail(models.Model):
    id = BigAutoField(primary_key = True)
    lr_number = models.CharField(max_length = 64)
    carrier_name = models.CharField(max_length = 64)
    quantity = models.PositiveIntegerField()
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
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'RETURNS_LOCATION'

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
    reserved_quantity = models.PositiveIntegerField(default=0)
    picked_quantity = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'MATERIAL_PICKLIST'

class RMLocation(models.Model):
    id = BigAutoField(primary_key=True)
    material_picklist = models.ForeignKey(MaterialPicklist)
    stock = models.ForeignKey(StockDetail)
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
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'STATUS_TRACKING'

class BOMMaster(models.Model):
    id = BigAutoField(primary_key=True)
    material_sku = models.ForeignKey(SKUMaster, default = None)
    product_sku = models.ForeignKey(SKUMaster, related_name='product_sku', blank=True, null=True)
    material_quantity = models.FloatField(default = 0)
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
    price = models.FloatField()
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
    order_quantity = models.PositiveIntegerField()
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
    quantity = models.PositiveIntegerField()
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

class CustomerOrders(models.Model):
    customer = models.ForeignKey(CustomerMaster)
    total_price = models.PositiveIntegerField()
    total_quantity = models.PositiveIntegerField(default = 0)
    vat = models.PositiveIntegerField(default = 0)
    discount = models.PositiveIntegerField(default = 0)
    issue_type=models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CUSTOMER_ORDERS'

class CustomerOrderSummary(models.Model):
    customer_order = models.ForeignKey(CustomerOrders)
    sku = models.ForeignKey(SKUMaster)
    quantity = models.PositiveIntegerField()
    discount = models.PositiveIntegerField()
    selling_price = models.PositiveIntegerField()
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CUSTOMER_ORDER_SUMMARY'

class CategoryDiscount(models.Model):
    user = models.ForeignKey(User)
    category = models.CharField(max_length=64, default='')
    discount = models.PositiveIntegerField(default=0)
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
    order =  models.ForeignKey(OrderDetail)
    ship_status = models.CharField(max_length=64)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SHIPMENT_TRACKING'
        unique_together = ('order', 'ship_status')

class Marketplaces(models.Model):
    user = models.PositiveIntegerField()
    name = models.CharField(max_length=128)

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
