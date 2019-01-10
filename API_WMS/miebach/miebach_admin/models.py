from django.db import models
from django.contrib.auth.models import User, Group
from miebach_utils import BigAutoField
from datetime import date
from django.db.models.signals import post_save
from django.dispatch import receiver
import reversion
from .choices import UNIT_TYPE_CHOICES, REMARK_CHOICES, TERMS_CHOICES, CUSTOMIZATION_TYPES, ROLE_TYPE_CHOICES, \
    CUSTOMER_ROLE_CHOICES, APPROVAL_STATUSES

# from longerusername import MAX_USERNAME_LENGTH
# Create your models here.

class ZoneMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    zone = models.CharField(max_length=64)
    level = models.IntegerField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ZONE_MASTER'
        unique_together = ('user', 'zone')
        index_together = ('user', 'zone')

    def __unicode__(self):
        return str(self.zone)

    def natural_key(self):
        return {'id': self.id, 'user': self.user, 'zone': self.zone, 'level': self.level}


class SubZoneMapping(models.Model):
    id = BigAutoField(primary_key=True)
    zone = models.ForeignKey(ZoneMaster, default=None)
    sub_zone = models.ForeignKey(ZoneMaster, related_name= 'sub_zone',default=None)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SUB_ZONE_MAPPING'
        unique_together = ('zone', 'sub_zone')

    def __unicode__(self):
        return '%s:%s' % (str(self.zone.zone), str(self.sub_zone.zone))


class ZoneMarketplaceMapping(models.Model):
    id = BigAutoField(primary_key=True)
    zone = models.ForeignKey(ZoneMaster, null=True, blank=True, default=None)
    marketplace = models.CharField(max_length=64)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ZONE_MARKETPLACE_MAPPING'
        unique_together = ('zone', 'marketplace')

    def __unicode__(self):
        return str(self.zone)


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


class SKUMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    sku_code = models.CharField(max_length=128)
    wms_code = models.CharField(max_length=128)
    sku_desc = models.CharField(max_length=350, default='')
    sku_group = models.CharField(max_length=64, default='')
    sku_type = models.CharField(max_length=64, default='')
    sku_category = models.CharField(max_length=128, default='')
    sku_class = models.CharField(max_length=64, default='')
    sku_brand = models.CharField(max_length=64, default='')
    style_name = models.CharField(max_length=256, default='')
    sku_size = models.CharField(max_length=64, default='')
    product_type = models.CharField(max_length=64, default='')
    zone = models.ForeignKey(ZoneMaster, null=True, blank=True, default=None)
    threshold_quantity = models.FloatField(default=0)
    online_percentage = models.PositiveIntegerField(default=0)
    discount_percentage = models.PositiveIntegerField(default=0)
    price = models.FloatField(default=0)
    cost_price = models.FloatField(default=0)
    mrp = models.FloatField(default=0)
    image_url = models.URLField(default='')
    qc_check = models.IntegerField(default=0)
    sequence = models.PositiveIntegerField(default=0)
    status = models.IntegerField(default=1)
    relation_type = models.CharField(max_length=32, default='')
    measurement_type = models.CharField(max_length=32, default='')
    sale_through = models.CharField(max_length=32, default='')
    mix_sku = models.CharField(max_length=32, default='', db_index=True)
    color = models.CharField(max_length=64, default='')
    ean_number = models.DecimalField(max_digits=20, decimal_places=0, db_index=True, default=0)
    load_unit_handle = models.CharField(max_length=32, default='unit', db_index=True)
    hsn_code = models.DecimalField(max_digits=20, decimal_places=0, db_index=True, default=0)
    sub_category = models.CharField(max_length=64, default='')
    primary_category = models.CharField(max_length=64, default='')
    shelf_life = models.IntegerField(default=0)
    youtube_url = models.CharField(max_length=64, default='')
    enable_serial_based = models.IntegerField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_MASTER'
        unique_together = ('user', 'sku_code', 'wms_code')
        index_together = ('user', 'sku_code', 'wms_code')

    def __unicode__(self):
        return str(self.sku_code)

    def natural_key(self):
        zone = ''
        if self.zone:
            zone = self.zone.zone
        return {'id': self.id, 'sku_code': self.sku_code, 'wms_code': self.wms_code,
                'sku_desc': self.sku_desc, 'sku_group': self.sku_group, 'sku_type': self.sku_type,
                'sku_category': self.sku_category, 'sku_class': self.sku_class, 'zone': zone,
                'threshold_quantity': self.threshold_quantity, 'online_percentage': self.online_percentage,
                'discount_percentage': self.discount_percentage, 'price': self.price, 'image_url': self.image_url,
                'qc_check': self.qc_check, 'status': self.status, 'relation_type': self.relation_type}


class EANNumbers(models.Model):
    id = BigAutoField(primary_key=True)
    ean_number = models.DecimalField(max_digits=20, decimal_places=0, db_index=True, default=0)
    sku = models.ForeignKey(SKUMaster)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'EAN_NUMBERS'
        unique_together = ('ean_number', 'sku')


class SKUJson(models.Model):
    id = BigAutoField(primary_key=True)
    sku = models.ForeignKey(SKUMaster)
    json_data = models.TextField()
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_JSON'

    def __unicode__(self):
        return self.sku


class IncrementalTable(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User)
    type_name = models.CharField(max_length=64)
    value = models.PositiveIntegerField()
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'INCREMENTAL_TABLE'

    def __unicode__(self):
        return str(self.value)


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
    lock_status = models.CharField(max_length=64, default='')
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
    cst_number = models.CharField(max_length=64, default='')
    tin_number = models.CharField(max_length=64, default='')
    pan_number = models.CharField(max_length=64, default='')
    status = models.IntegerField(default=1)
    tax_type = models.CharField(max_length=32, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)
    supplier_type = models.CharField(max_length=64, default='')
    days_to_supply = models.IntegerField(default=0)
    fulfillment_amt = models.FloatField(default=0)
    credibility = models.CharField(max_length=32, default='')
    po_exp_duration = models.IntegerField(default=0)
    owner_name = models.CharField(max_length=256, default='')
    owner_number = models.CharField(max_length=64, default='')
    owner_email_id = models.EmailField(max_length=64, default='')
    spoc_name = models.CharField(max_length=256, default='')
    spoc_number = models.CharField(max_length=64, default='')
    spoc_email_id = models.EmailField(max_length=64, default='')
    lead_time = models.IntegerField(default=0)
    credit_period = models.IntegerField(default=0)
    bank_name = models.CharField(max_length=256, default='')
    ifsc_code = models.CharField(max_length=64, default='')
    branch_name = models.CharField(max_length=256, default='')
    account_number = models.BigIntegerField(default=0)
    account_holder_name = models.CharField(max_length=256, default='')

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
    order_id = models.DecimalField(max_digits=50, decimal_places=0, primary_key=True)
    original_order_id = models.CharField(max_length=128, default='')
    customer_id = models.PositiveIntegerField(default=0)
    customer_name = models.CharField(max_length=256, default='')
    email_id = models.EmailField(max_length=64, default='')
    address = models.CharField(max_length=256, default='')
    telephone = models.CharField(max_length=128, default='', blank=True, null=True)
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
    unit_price = models.FloatField(default=0)
    nw_status = models.CharField(max_length=32, blank=True, null=True)
    order_type = models.CharField(max_length=64, default='Normal')
    order_reference = models.CharField(max_length=128, default='')
    order_reference_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'ORDER_DETAIL'
        unique_together = ('order_id', 'sku', 'order_code')
        index_together = (('order_id', 'sku', 'order_code'), ('user', 'order_code'),
                          ('customer_id', 'order_code', 'marketplace', 'original_order_id', 'order_id', 'customer_name'),
                          ('status', 'user', 'quantity'))

    def __unicode__(self):
        return str(self.sku) + ':' + str(self.original_order_id)


class GenericOrderDetailMapping(models.Model):
    id = BigAutoField(primary_key=True)
    generic_order_id = models.PositiveIntegerField(default=0)
    orderdetail = models.ForeignKey(OrderDetail)
    customer_id = models.PositiveIntegerField(default=0)
    cust_wh_id = models.PositiveIntegerField(default=0)
    quantity = models.FloatField(default=0)
    unit_price = models.FloatField(default=0)
    el_price = models.FloatField(default=0)
    po_number = models.CharField(max_length=128, default='')
    client_name = models.CharField(max_length=256, default='')
    schedule_date = models.DateField()
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'GENERIC_ORDERDETAIL_MAPPING'
        unique_together = ('generic_order_id', 'orderdetail', 'customer_id', 'cust_wh_id')


class IntermediateOrders(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User)
    customer_user = models.ForeignKey(User, related_name='customer', blank=True, null=True)
    order_assigned_wh = models.ForeignKey(User, related_name='warehouse', blank=True, null=True)
    interm_order_id = models.DecimalField(max_digits=50, decimal_places=0)
    order = models.ForeignKey(OrderDetail, blank=True, null=True)
    sku = models.ForeignKey(SKUMaster)
    alt_sku = models.ForeignKey(SKUMaster, related_name='alt_sku', blank=True, null=True)
    quantity = models.FloatField(default=1)
    unit_price = models.FloatField(default=0)
    tax = models.FloatField(default=0)
    inter_state = models.IntegerField(default=0)
    cgst_tax = models.FloatField(default=0)
    sgst_tax = models.FloatField(default=0)
    igst_tax = models.FloatField(default=0)
    utgst_tax = models.FloatField(default=0)
    status = models.CharField(max_length=32, default='')
    shipment_date = models.DateTimeField()
    project_name = models.CharField(max_length=256, default='')
    remarks = models.CharField(max_length=128, default='')
    customer_id = models.PositiveIntegerField(default=0)
    customer_name = models.CharField(max_length=256, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "INTERMEDIATE_ORDERS"
        #unique_together = ('interm_order_id', 'sku')

    def json(self):
        invoice_amount = self.quantity * self.sku.price
        return {
            'sku_id': self.sku.sku_code,
            'quantity': self.quantity,
            'price': self.sku.price,
            'unit_price': self.sku.price,
            'invoice_amount': invoice_amount,
            'tax': self.tax,
            'total_amount': ((invoice_amount * self.tax) / 100) + invoice_amount,
            'image_url': self.sku.image_url,
            'cgst_tax': self.cgst_tax,
            'sgst_tax': self.sgst_tax,
            'igst_tax': self.igst_tax,
            'utgst_tax': self.utgst_tax,
        }


class OrderFields(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    original_order_id = models.CharField(max_length=128, default='')
    name = models.CharField(max_length=256, default='')
    value = models.CharField(max_length=256, default='')
    order_type = models.CharField(max_length=256, default='order')

    class Meta:
        db_table = 'ORDER_FIELDS'

    def __unicode__(self):
        return str(self.original_order_id)

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


@reversion.register()
class OpenPO(models.Model):
    id = BigAutoField(primary_key=True)
    supplier = models.ForeignKey(SupplierMaster, blank=True, null=True, db_index=True)
    vendor = models.ForeignKey(VendorMaster, blank=True, null=True)
    sku = models.ForeignKey(SKUMaster, db_index=True)
    order_quantity = models.FloatField(default=0, db_index=True)
    price = models.FloatField(default=0)
    wms_code = models.CharField(max_length=32, default='')
    po_name = models.CharField(max_length=128, default='')
    supplier_code = models.CharField(max_length=32, default='')
    order_type = models.CharField(max_length=32, default='SR')
    remarks = models.CharField(max_length=256, default='')
    tax_type = models.CharField(max_length=32, default='')
    sgst_tax = models.FloatField(default=0)
    cgst_tax = models.FloatField(default=0)
    igst_tax = models.FloatField(default=0)
    cess_tax = models.FloatField(default=0)
    utgst_tax = models.FloatField(default=0)
    mrp = models.FloatField(default=0)
    delivery_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=32)
    measurement_unit = models.CharField(max_length=32, default='')
    ship_to = models.CharField(max_length=128, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)
    terms = models.TextField(default='', max_length=256)

    class Meta:
        db_table = 'OPEN_PO'
        index_together = (('sku', 'supplier'), ('sku', ), ('vendor', 'sku', 'supplier'), ('sku', 'order_quantity', 'price'))

    def __unicode__(self):
        return str(str(self.sku) + " : " + str(self.supplier))


@reversion.register()
class PurchaseOrder(models.Model):
    id = BigAutoField(primary_key=True)
    order_id = models.PositiveIntegerField(db_index=True)
    open_po = models.ForeignKey(OpenPO, blank=True, null=True)
    received_quantity = models.FloatField(default=0)
    saved_quantity = models.FloatField(default=0)
    intransit_quantity = models.FloatField(default=0)
    po_date = models.DateTimeField(auto_now_add=True)
    ship_to = models.CharField(max_length=64, default='')
    status = models.CharField(max_length=32, db_index=True)
    reason = models.TextField(blank=True, null=True)
    prefix = models.CharField(max_length=32, default='')
    remarks = models.TextField(default='')
    expected_date = models.DateField(blank=True, null=True)
    remainder_mail = models.IntegerField(default=0)
    payment_received = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PURCHASE_ORDER'
        index_together = (('order_id', 'open_po'), ('order_id', 'open_po', 'received_quantity'))

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
        index_together = ('product_code', 'job_code')


class JOMaterial(models.Model):
    job_order = models.ForeignKey(JobOrder)
    material_code = models.ForeignKey(SKUMaster)
    material_quantity = models.FloatField(default=0)
    status = models.IntegerField(default=1)
    unit_measurement_type = models.CharField(max_length=32, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'JO_MATERIAL'
        index_together = (('job_order', 'material_code'), ('job_order', 'material_code', 'status'),
                            ('job_order', 'material_code', 'status', 'material_quantity'))


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
        index_together = (('purchase_order', 'location'), ('purchase_order', 'location', 'quantity', 'status'))


class PalletDetail(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    pallet_code = models.CharField(max_length=64)
    quantity = models.FloatField(default=0)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PALLET_DETAIL'
        index_together = (('user', 'pallet_code'), ('user', 'pallet_code', 'quantity'))


class PalletMapping(models.Model):
    id = BigAutoField(primary_key=True)
    pallet_detail = models.ForeignKey(PalletDetail, blank=True, null=True)
    po_location = models.ForeignKey(POLocation, blank=True, null=True)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PALLET_MAPPING'
        index_together = ('pallet_detail', 'po_location')

@reversion.register()
class BatchDetail(models.Model):
    id = BigAutoField(primary_key=True)
    batch_no = models.CharField(max_length=64, default='')
    buy_price = models.FloatField(default=0)
    mrp = models.FloatField(default=0)
    manufactured_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    tax_percent = models.FloatField(default=0)
    transact_id = models.IntegerField(default=0)
    transact_type = models.CharField(max_length=36, default='')
    weight = models.FloatField(default=0)
    ean_number = models.DecimalField(max_digits=20, decimal_places=0, default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'BATCH_DETAIL'
        index_together = (('transact_id', 'transact_type'), ('batch_no', 'buy_price', 'mrp', 'manufactured_date', 'expiry_date', 'tax_percent'),
                            ('batch_no', 'mrp'))

class StockDetail(models.Model):
    id = BigAutoField(primary_key=True)
    receipt_number = models.PositiveIntegerField(db_index=True)
    receipt_date = models.DateTimeField()
    receipt_type = models.CharField(max_length=32, default='')
    sku = models.ForeignKey(SKUMaster)
    location = models.ForeignKey(LocationMaster, db_index=True)
    pallet_detail = models.ForeignKey(PalletDetail, blank=True, null=True)
    batch_detail = models.ForeignKey(BatchDetail, blank=True, null=True)
    quantity = models.FloatField(default=0)
    unit_price = models.FloatField(default=0)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)
    remarks =models.CharField(max_length =128 , default ='')

    class Meta:
        db_table = 'STOCK_DETAIL'
        unique_together = ('receipt_number', 'receipt_date', 'sku', 'location', 'pallet_detail', 'batch_detail', 'unit_price', 'receipt_type')
        index_together = (('sku', 'location', 'quantity'), ('location', 'sku', 'pallet_detail'))

    def __unicode__(self):
        return str(self.sku) + " : " + str(self.location)


class ASNStockDetail(models.Model):
    id = BigAutoField(primary_key=True)
    asn_po_num = models.CharField(max_length=32, default='')
    sku = models.ForeignKey(SKUMaster)
    quantity = models.IntegerField(default=0)
    status = models.CharField(max_length=32, default='open')
    arriving_date = models.DateField(blank=True, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ASN_STOCK_DETAIL'
        unique_together = ('asn_po_num', 'sku')


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
    damage_suggested = models.IntegerField(default=0)
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PICKLIST'
        index_together = (('picklist_number', 'order', 'stock'), ('order', 'order_type', 'picked_quantity'),
                          ('picklist_number',), ('picklist_number', 'order'), ('picklist_number', 'stock'),
                          ('picklist_number', 'reserved_quantity'))

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
        index_together = (('picklist', 'stock', 'reserved'), ('picklist', 'status'),
                          ('picklist', 'reserved'), ('picklist', 'stock', 'status'),
                          ('picklist', 'reserved', 'stock', 'status'))


class OrderLabels(models.Model):
    id = BigAutoField(primary_key=True)
    order = models.ForeignKey(OrderDetail, blank=True, null=True)
    label = models.CharField(max_length=128, default='')
    vendor_sku = models.CharField(max_length=128, default='')
    item_sku = models.CharField(max_length=128, default='')
    mrp = models.FloatField(default=0)
    title = models.CharField(max_length=256, default='')
    size = models.CharField(max_length=32, default='')
    color = models.CharField(max_length=64, default='')
    picklist = models.ForeignKey(Picklist, blank=True, null=True)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_LABELS'
        unique_together = ('order', 'label')
        index_together = ('order', 'label')

    def __unicode__(self):
        return str(self.label)


class MiscDetail(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    misc_type = models.CharField(max_length=64)
    misc_value = models.CharField(max_length=255)
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
        unique_together = ('cycle', 'sku', 'location', 'creation_date')

    def __unicode__(self):
        return str(self.cycle)


class InventoryAdjustment(models.Model):
    id = BigAutoField(primary_key=True)
    cycle = models.ForeignKey(CycleCount)
    adjusted_location = models.CharField(max_length=64)
    adjusted_quantity = models.FloatField(default=0)
    reason = models.TextField()
    pallet_detail = models.ForeignKey(PalletDetail, blank=True, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'INVENTORY_ADJUSTMENT'
        unique_together = ('cycle', 'adjusted_location')

    def __unicode__(self):
        return str(self.id)


class SubstitutionSummary(models.Model):
    source_sku_code = models.ForeignKey(SKUMaster, blank=True, null=True, related_name='source_sku')
    destination_sku_code = models.ForeignKey(SKUMaster, blank=True, null=True, related_name='destination_sku')
    source_location = models.CharField(max_length=64)
    destination_location = models.CharField(max_length=64)
    source_quantity = models.FloatField(default=0)
    destination_quantity = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SUBSTITUTION_SUMMARY'

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
    manifest_number = models.DecimalField(max_digits=50, decimal_places=0,default=0)
    shipment_date = models.DateTimeField()
    driver_name = models.CharField(max_length =32 , default ='')
    driver_phone_number = models.CharField(max_length =32 , default ='')
    truck_number = models.CharField(max_length=64)
    shipment_reference = models.CharField(max_length=64)
    status = models.CharField(max_length=32)
    courier_name = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_SHIPMENT'


class OrderPackaging(models.Model):
    id = BigAutoField(primary_key=True)
    order_shipment = models.ForeignKey(OrderShipment)
    package_reference = models.CharField(max_length=64)
    box_number = models.CharField(max_length=64, default='')
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
    invoice_number = models.CharField(max_length=64, default='')
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
    status = models.IntegerField(default=0)

    class Meta:
        db_table = 'SKU_STOCK'


class CustomerMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    customer_id = models.PositiveIntegerField(default=0)
    customer_code = models.CharField(max_length=256, default='')
    name = models.CharField(max_length=256, default='')
    last_name = models.CharField(max_length=256, default='')
    address = models.CharField(max_length=256, default='')
    shipping_address = models.CharField(max_length=256, default='')
    city = models.CharField(max_length=64, default='')
    state = models.CharField(max_length=64, default='')
    country = models.CharField(max_length=64, default='')
    pincode = models.CharField(max_length=64, default='')
    phone_number = models.CharField(max_length=32)
    email_id = models.EmailField(max_length=64, default='')
    tin_number = models.CharField(max_length=64, default='')
    cst_number = models.CharField(max_length=64, default='')
    pan_number = models.CharField(max_length=64, default='')
    credit_period = models.PositiveIntegerField(default=0)
    price_type = models.CharField(max_length=32, default='')
    tax_type = models.CharField(max_length=32, default='')
    discount_percentage = models.FloatField(default=0)
    markup = models.FloatField(default=0)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)
    customer_type = models.CharField(max_length=64, default='')
    is_distributor = models.BooleanField(default=False)
    lead_time = models.PositiveIntegerField(blank=True, default=0)
    role = models.CharField(max_length=64, choices=CUSTOMER_ROLE_CHOICES, default='')
    spoc_name = models.CharField(max_length=256, default='')

    class Meta:
        db_table = 'CUSTOMER_MASTER'
        unique_together = ('user', 'customer_id', 'customer_code')
        index_together = ('user', 'customer_id', 'customer_code')


class CustomerUserMapping(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User, blank=True, null=True)
    customer = models.ForeignKey(CustomerMaster, blank=True, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CUSTOMER_USER_MAPPING'


class UserProfile(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.OneToOneField(User)
    phone_number = models.CharField(max_length=32, default='', blank=True)
    birth_date = models.DateTimeField(auto_now=True)
    is_active = models.IntegerField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)
    timezone = models.CharField(max_length=64, default='', blank=True)
    swx_id = models.IntegerField(default=None, blank=True, null=True)
    prefix = models.CharField(max_length=64, default='')
    company_name = models.CharField(max_length=256, default='')
    location = models.CharField(max_length=60, default='', blank=True)
    city = models.CharField(max_length=60, default='', blank=True)
    state = models.CharField(max_length=60, default='', blank=True)
    country = models.CharField(max_length=60, default='', blank=True)
    pin_code = models.PositiveIntegerField(default=0)
    address = models.CharField(max_length=256, default='', blank=True)
    wh_address = models.CharField(max_length=256, default='', blank=True)
    wh_phone_number = models.CharField(max_length=32, default='', blank=True)
    gst_number = models.CharField(max_length=32, default='', blank=True)
    multi_warehouse = models.IntegerField(default=0, blank=True)
    is_trail = models.IntegerField(default=0, blank=True)
    api_hash = models.CharField(max_length=256, default='', blank=True)
    setup_status = models.CharField(max_length=60, default='completed', blank=True)
    user_type = models.CharField(max_length=60, default='warehouse_user')
    warehouse_type = models.CharField(max_length=60, default='', blank=True)
    warehouse_level = models.IntegerField(default=0, blank=True)
    min_order_val = models.PositiveIntegerField(default=0)
    level_name = models.CharField(max_length=64, default='', blank=True)
    zone = models.CharField(max_length=64, default='', blank=True)
    cin_number = models.CharField(max_length=64, default='', blank=True)
    customer_logo = models.ImageField(upload_to='static/images/customer_logos/', default='', blank=True)
    bank_details = models.TextField(default='', blank=True)
    industry_type = models.CharField(max_length=32, default='', blank=True)
    order_prefix = models.CharField(max_length=32, default='', null=True, blank=True)
    pan_number = models.CharField(max_length=64, default='', blank=True)

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
    id = BigAutoField(primary_key=True)
    swx_id = models.PositiveIntegerField()
    local_id = models.PositiveIntegerField(default=0)
    swx_type = models.CharField(max_length=32, default='')
    app_host = models.CharField(max_length=64, default='')
    imei = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SWX_MAPPING'
        unique_together = ('swx_id', 'local_id', 'swx_type', 'app_host', 'imei')


class LRDetail(models.Model):
    id = BigAutoField(primary_key=True)
    lr_number = models.CharField(max_length=64)
    carrier_name = models.CharField(max_length=64)
    quantity = models.FloatField(default=0)
    purchase_order = models.ForeignKey(PurchaseOrder)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'LR_DETAIL'


class SellerMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    seller_id = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=256, default='')
    email_id = models.EmailField(max_length=64, default='')
    phone_number = models.CharField(max_length=32)
    address = models.CharField(max_length=256, default='')
    vat_number = models.CharField(max_length=64, default='')
    tin_number = models.CharField(max_length=64, default='')
    price_type = models.CharField(max_length=32, default='')
    margin = models.CharField(max_length=256, default=0)
    supplier = models.ForeignKey(SupplierMaster, null=True, blank=True, default=None)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SELLER_MASTER'
        unique_together = ('user', 'seller_id')
        index_together = ('user', 'seller_id')

    def json(self):
        supplier_id = '' if not self.supplier else self.supplier.id
        return {
            'id': self.id,
            'seller_id': self.seller_id,
            'name': self.name,
            'email_id': self.email_id,
            'phone_number': self.phone_number,
            'address': self.address,
            'vat_number': self.vat_number,
            'tin_number': self.tin_number,
            'price_type': self.price_type,
            'margin': self.margin,
            'supplier': supplier_id,
            'status': self.status
        }


class POIMEIMapping(models.Model):
    id = BigAutoField(primary_key=True)
    sku = models.ForeignKey(SKUMaster, blank=True, null=True)
    seller = models.ForeignKey(SellerMaster, blank=True, null=True)
    purchase_order = models.ForeignKey(PurchaseOrder, blank=True, null=True)
    pack_status = models.IntegerField(default=0)
    job_order = models.ForeignKey(JobOrder, blank=True, null=True)
    imei_number = models.CharField(max_length=64, default='')
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PO_IMEI_MAPPING'
        unique_together = ('purchase_order','imei_number', 'sku', 'job_order', 'seller')


class OrderIMEIMapping(models.Model):
    id = BigAutoField(primary_key=True)
    order = models.ForeignKey(OrderDetail, blank=True, null=True)
    jo_material = models.ForeignKey(JOMaterial, blank=True, null=True)
    sku = models.ForeignKey(SKUMaster)
    seller = models.ForeignKey(SellerMaster, blank=True, null=True)
    po_imei = models.ForeignKey(POIMEIMapping, blank=True, null=True)
    #stock_transfer = models.ForeignKey(StockTransfer, blank=True, null=True)
    imei_number = models.CharField(max_length=64, default='')
    sor_id = models.CharField(max_length=128, default='')
    order_reference = models.CharField(max_length=128, default='')
    marketplace = models.CharField(max_length=64, default='')
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_IMEI_MAPPING'


class UserGroups(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User)
    admin_user = models.ForeignKey(User, related_name='admin_user', blank=True, null=True)

    class Meta:
        db_table = 'USER_GROUPS'


class WarehouseCustomerMapping(models.Model):
    id = BigAutoField(primary_key=True)
    warehouse = models.ForeignKey(User)
    customer = models.ForeignKey(CustomerMaster, null=True, blank=True)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'WAREHOUSE_CUSTOMER_MAPPING'
        unique_together = ('warehouse', 'customer')


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


class MaterialPicklist(models.Model):
    jo_material = models.ForeignKey(JOMaterial)
    reserved_quantity = models.FloatField(default=0)
    picked_quantity = models.FloatField(default=0)
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'MATERIAL_PICKLIST'
        index_together = (('jo_material', 'status'), ('jo_material', 'status', 'reserved_quantity'))


class RMLocation(models.Model):
    id = BigAutoField(primary_key=True)
    material_picklist = models.ForeignKey(MaterialPicklist)
    stock = models.ForeignKey(StockDetail, blank=True, null=True)
    reserved = models.FloatField(default=0)
    quantity = models.FloatField(default=0)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'RM_LOCATION'
        index_together = (('material_picklist', 'stock'), ('material_picklist', 'stock', 'status'), ('material_picklist', 'stock', 'status', 'reserved'))


class SKURelation(models.Model):
    id = BigAutoField(primary_key=True)
    parent_sku = models.ForeignKey(SKUMaster, blank=True, null=True, related_name='parent_sku')
    member_sku = models.ForeignKey(SKUMaster, blank=True, null=True, related_name='member_sku')
    quantity = models.FloatField(default=1)
    relation_type = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_RELATION'
        unique_together = ('parent_sku', 'member_sku', 'relation_type')
        index_together = ('parent_sku', 'member_sku', 'relation_type')

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
        index_together = (('status_id', 'status_type'),('status_type', 'status_value', 'quantity'), ('status_id', 'status_type', 'status_value'))


class StatusTrackingSummary(models.Model):
    id = BigAutoField(primary_key=True)
    status_tracking = models.ForeignKey(StatusTracking, blank=True, null=True)
    processed_stage = models.CharField(max_length=64, default='')
    processed_quantity = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'STATUS_TRACKING_SUMMARY'
        index_together = (('status_tracking', 'processed_stage'), ('status_tracking', 'processed_stage', 'processed_quantity'))


class BOMMaster(models.Model):
    id = BigAutoField(primary_key=True)
    material_sku = models.ForeignKey(SKUMaster, default=None)
    product_sku = models.ForeignKey(SKUMaster, related_name='product_sku', blank=True, null=True)
    material_quantity = models.FloatField(default=0)
    wastage_percent = models.FloatField(default=0)
    unit_of_measurement = models.CharField(max_length=10, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'BOM_MASTER'
        unique_together = ('material_sku', 'product_sku')


class PriceMaster(models.Model):
    id = BigAutoField(primary_key=True)
    sku = models.ForeignKey(SKUMaster, default=None)
    price_type = models.CharField(max_length=32, default='')
    price = models.FloatField(default=0)
    discount = models.FloatField(default=0)
    min_unit_range = models.FloatField(default=0)
    max_unit_range = models.FloatField(default=0)
    unit_type = models.CharField(max_length=64, choices=UNIT_TYPE_CHOICES, default='quantity')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PRICE_MASTER'
        unique_together = ('sku', 'price_type', 'min_unit_range', 'max_unit_range', 'unit_type')
        index_together = ('sku', 'price_type', 'min_unit_range', 'max_unit_range')

    def json(self):
        return {
            'id': self.id,
            'sku': self.sku.sku_code,
            'price_type': self.price_type,
            'price': self.price,
            'discount': self.discount,
            'min_unit_range': self.min_unit_range,
            'max_unit_range': self.max_unit_range,
            'unit_type': self.unit_type,
        }


class CancelledLocation(models.Model):
    id = BigAutoField(primary_key=True)
    picklist = models.ForeignKey(Picklist, blank=True, null=True)
    location = models.ForeignKey(LocationMaster, blank=True, null=True)
    quantity = models.FloatField(default=0)
    status = models.IntegerField(default=0)
    seller = models.ForeignKey(SellerMaster, blank=True, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CANCELLED_LOCATION'


class CustomerSKU(models.Model):
    id = BigAutoField(primary_key=True)
    customer = models.ForeignKey(CustomerMaster, null=True, blank=True)
    sku = models.ForeignKey(SKUMaster)
    price = models.FloatField(default=0)
    discount = models.FloatField(default=0)
    customer_sku_code = models.CharField(max_length=120, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CUSTOMER_SKU'
        unique_together = ('customer', 'sku')


class CorporateMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=256, default='')
    address = models.CharField(max_length=256, default='')
    city = models.CharField(max_length=64, default='')
    state = models.CharField(max_length=64, default='')
    country = models.CharField(max_length=64, default='')
    pincode = models.CharField(max_length=64, default='')
    phone_number = models.CharField(max_length=32, default='')
    email_id = models.CharField(max_length=64, default='')
    status = models.CharField(max_length=11, default='')
    tin_number = models.CharField(max_length=64, default='')
    corporate_id = models.PositiveIntegerField(default=0)
    cst_number = models.CharField(max_length=64, default='')
    pan_number = models.CharField(max_length=64, default='')
    tax_type = models.CharField(max_length=32, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CORPORATE_MASTER'

class CorpResellerMapping(models.Model):
    id = BigAutoField(primary_key=True)
    reseller_id = models.PositiveIntegerField()
    corporate_id = models.PositiveIntegerField()
    status = models.CharField(max_length=10, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CORP_RESELLER_MAPPING'


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
        unique_together = ('order_id', 'st_po', 'sku')

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
    discount = models.FloatField(default=0)
    vat = models.FloatField(default=0)
    mrp = models.FloatField(default=0)
    issue_type = models.CharField(max_length=64, default='')
    tax_value = models.FloatField(default=0)
    tax_type = models.CharField(max_length=64, default='')
    order_taken_by = models.CharField(max_length=128, default='')
    shipment_time_slot = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=24, default='')
    consignee = models.CharField(max_length=256, default='')
    payment_terms = models.CharField(max_length=24, default='')
    dispatch_through = models.CharField(max_length=24, default='')
    invoice_date = models.DateTimeField(null=True, blank=True)
    central_remarks = models.CharField(max_length=256, default='')
    inter_state = models.IntegerField(default=0)
    cgst_tax = models.FloatField(default=0)
    sgst_tax = models.FloatField(default=0)
    igst_tax = models.FloatField(default=0)
    utgst_tax = models.FloatField(default=0)
    cess_tax = models.FloatField(default=0)
    invoice_type = models.CharField(max_length=64, default='Tax Invoice')
    client_name = models.CharField(max_length=64, default='')
    mode_of_transport = models.CharField(max_length=24, default='')
    payment_status = models.CharField(max_length=64, default='')
    courier_name = models.CharField(max_length=64, default='')
    vehicle_number = models.CharField(max_length=64, default='')

    class Meta:
        db_table = 'CUSTOMER_ORDER_SUMMARY'


class CategoryDiscount(models.Model):
    user = models.ForeignKey(User)
    category = models.CharField(max_length=64, default='')
    discount = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_CATEGORY_DISCOUNT'
        unique_together = ('user', 'category')


'''class TaxMaster(models.Model):
    city = models.CharField(max_length=64, default='')
    state = models.CharField(max_length=64, default='')
    tax_type = models.CharField(max_length=64, default='')
    tax_percentage = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'TAX_MASTER'''


class SalesPersons(models.Model):
    user = models.OneToOneField(User)
    user_name = models.CharField(max_length=64, default='')
    first_name = models.CharField(max_length=64, default='')
    last_name = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SALES_PERSONS'


class SizeMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    size_name = models.CharField(max_length=64, default='')
    size_value = models.TextField()
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SIZE_MASTER'
        unique_together = ('user', 'size_name')


class ProductAttributes(models.Model):
    user = models.ForeignKey(User, default=None)
    attribute_name = models.CharField(max_length=64, default='')
    description = models.CharField(max_length=128, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PRODUCT_ATTRIBUTES'
        unique_together = ('user', 'attribute_name')
        index_together = ('user', 'attribute_name')


class ProductProperties(models.Model):
    user = models.ForeignKey(User, default=None)
    name = models.CharField(max_length=64, default='')
    brand = models.CharField(max_length=64, default='')
    category = models.CharField(max_length=64, default='')
    size_types = models.ManyToManyField(SizeMaster, default=None)
    attributes = models.ManyToManyField(ProductAttributes, default=None)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PRODUCT_PROPERTIES'
        unique_together = ('name', 'brand', 'category')
        index_together = ('name', 'brand', 'category')


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
    json_data = models.TextField()
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


class customerGroupsMapping(models.Model):
    customer = models.ForeignKey(CustomerMaster)
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
    sku = models.ForeignKey(SKUMaster)
    image_url = models.CharField(max_length=256, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_IMAGES'
        unique_together = ('sku', 'image_url')


class RWOrder(models.Model):
    vendor = models.ForeignKey(VendorMaster)
    job_order = models.ForeignKey(JobOrder)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'RW_ORDER'


class RWPurchase(models.Model):
    rwo = models.ForeignKey(RWOrder)
    purchase_order = models.ForeignKey(PurchaseOrder)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'RW_PURCHASE'


class ShipmentTracking(models.Model):
    shipment = models.ForeignKey(ShipmentInfo)
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
    quantity = models.FloatField(default=0)
    marketplace = models.CharField(max_length=64, default='')
    title = models.CharField(max_length=255, default='')
    channel_sku = models.CharField(max_length=64, default='')
    shipment_date = models.DateTimeField(blank=True, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)
    mapped_sku_code = models.CharField(max_length=64, default='')
    company_name = models.CharField(max_length=64, default='')

    class Meta:
        db_table = 'ORDERS_TRACK'
        unique_together = ('user', 'sku_code', 'order_id', 'channel_sku')


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
    payment_id = models.CharField(max_length=60, default='')
    order = models.ForeignKey(OrderDetail, blank=True, null=True)
    payment_received = models.FloatField(default=0)
    bank = models.CharField(max_length=64, default='')
    mode_of_pay = models.CharField(max_length=64, default='')
    remarks = models.CharField(max_length=128, default='')
    entered_amount = models.FloatField(default=0)
    balance_amount = models.FloatField(default=0)
    tds_amount = models.FloatField(default=0)
    payment_date = models.DateField(blank=True, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PAYMENT_SUMMARY'

class POPaymentSummary(models.Model):
    id = BigAutoField(primary_key=True)
    order = models.ForeignKey(PurchaseOrder, blank=True, null=True)
    payment_received = models.FloatField(default=0)
    bank = models.CharField(max_length=64, default='')
    mode_of_pay = models.CharField(max_length=64, default='')
    remarks = models.CharField(max_length=128, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PO_PAYMENT_SUMMARY'


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


class SellerPO(models.Model):
    id = BigAutoField(primary_key=True)
    seller = models.ForeignKey(SellerMaster, blank=True, null=True)
    open_po = models.ForeignKey(OpenPO, blank=True, null=True)
    seller_quantity = models.FloatField(default=0)
    received_quantity = models.FloatField(default=0)
    receipt_type = models.CharField(max_length=64, default='purchase_order')
    unit_price = models.FloatField(default=0)
    margin_percent = models.FloatField(default=0)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SELLER_PO'
        unique_together = ('seller', 'open_po')
        index_together = ('seller', 'open_po')

    def __unicode__(self):
        return str(self.id)


@reversion.register(follow=('batch_detail',))
class SellerPOSummary(models.Model):
    id = BigAutoField(primary_key=True)
    receipt_number = models.PositiveIntegerField(default=0)
    invoice_number = models.CharField(max_length=64, default='')
    invoice_date = models.DateField(blank=True, null=True)
    seller_po = models.ForeignKey(SellerPO, blank=True, null=True, db_index=True)
    purchase_order = models.ForeignKey(PurchaseOrder, blank=True, null=True, db_index=True)
    location = models.ForeignKey(LocationMaster, blank=True, null=True)
    batch_detail = models.ForeignKey(BatchDetail, blank=True, null=True)
    putaway_quantity = models.FloatField(default=0)
    quantity = models.FloatField(default=0)
    challan_number = models.CharField(max_length=64, default='')
    order_status_flag = models.CharField(max_length=64, default='processed_pos')
    challan_date = models.DateField(blank=True, null=True)
    discount_percent = models.FloatField(default=0)
    round_off_total = models.FloatField(default=0)
    cess_tax = models.FloatField(default=0)
    overall_discount = models.FloatField(default=0)
    remarks = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SELLER_PO_SUMMARY'
        index_together = (('receipt_number',), ('purchase_order', 'receipt_number'))

    def __unicode__(self):
        return str(self.id)


class SellerStock(models.Model):
    id = BigAutoField(primary_key=True)
    seller = models.ForeignKey(SellerMaster, blank=True, null=True)
    stock = models.ForeignKey(StockDetail, blank=True, null=True)
    seller_po_summary = models.ForeignKey(SellerPOSummary, blank=True, null=True, db_index=True)
    quantity = models.FloatField(default=0)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SELLER_STOCK'
        unique_together = ('seller', 'stock', 'seller_po_summary')
        index_together = (('seller', 'stock', 'seller_po_summary'), ('seller', 'stock'), ('seller', 'stock', 'quantity'))


class SellerMarginMapping(models.Model):
    id = BigAutoField(primary_key=True)
    seller = models.ForeignKey(SellerMaster, blank=True, null=True, db_index=True)
    sku = models.ForeignKey(SKUMaster, blank=True, null=True, db_index=True)
    margin = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SELLER_MARGIN_MAPPING'
        unique_together = ('seller', 'sku')

    def __unicode__(self):
        return str(self.seller) + " : " + str(self.sku)


class SellerOrder(models.Model):
    id = BigAutoField(primary_key=True)
    seller = models.ForeignKey(SellerMaster, blank=True, null=True)
    sor_id = models.CharField(max_length=128, default='')
    order = models.ForeignKey(OrderDetail, blank=True, null=True)
    quantity = models.FloatField(default=0)
    order_status = models.CharField(max_length=64, default='')
    invoice_no = models.CharField(max_length=64, default='')
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SELLER_ORDER'
        unique_together = ('sor_id', 'order')
        index_together = ('sor_id', 'order')

    def __unicode__(self):
        return str(self.sor_id)


class OrderReturns(models.Model):
    id = BigAutoField(primary_key=True)
    return_id = models.CharField(max_length=256)
    order = models.ForeignKey(OrderDetail, blank=True, null=True)
    seller_order = models.ForeignKey(SellerOrder, blank=True, null=True)
    seller = models.ForeignKey(SellerMaster, blank=True, null=True)
    return_date = models.DateTimeField(auto_now_add=True)
    quantity = models.FloatField(default=0)
    damaged_quantity = models.FloatField(default=0)
    sku = models.ForeignKey(SKUMaster, blank=True, null=True)
    return_type = models.CharField(max_length=64, default='')
    reason = models.CharField(max_length=256, default='')
    status = models.CharField(max_length=64)
    marketplace = models.CharField(max_length=32, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_RETURNS'


class OrderReturnReasons(models.Model):
    id = BigAutoField(primary_key=True)
    order_return = models.ForeignKey(OrderReturns, blank=True, null=True)
    quantity = models.FloatField(default=0)
    reason = models.CharField(max_length=256, default='')
    status = models.CharField(max_length=64)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_RETURN_REASONS'


class ReturnsIMEIMapping(models.Model):
    id = BigAutoField(primary_key=True)
    order_imei = models.ForeignKey(OrderIMEIMapping, blank=True, null=True)
    order_return = models.ForeignKey(OrderReturns, blank=True, null=True)
    status = models.CharField(max_length=64, default='')
    reason = models.CharField(max_length=128, default='')
    imei_status = models.IntegerField(max_length=1, default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'RETURNS_IMEI_MAPPING'
        unique_together = ('order_imei', 'order_return')
        index_together = ('order_imei', 'order_return')


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


class SellerOrderDetail(models.Model):
    id = BigAutoField(primary_key=True)
    seller_order = models.ForeignKey(SellerOrder, blank=True, null=True, db_index=True)
    picklist = models.ForeignKey(Picklist, blank=True, null=True, db_index=True)
    quantity = models.FloatField(default=0)
    reserved = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SELLER_ORDER_DETAIL'
        unique_together = ('seller_order', 'picklist')
        index_together = ('seller_order', 'picklist')


class SellerOrderSummary(models.Model):
    id = BigAutoField(primary_key=True)
    pick_number = models.PositiveIntegerField(default=0)
    seller_order = models.ForeignKey(SellerOrder, blank=True, null=True, db_index=True)
    order = models.ForeignKey(OrderDetail, blank=True, null=True, db_index=True)
    picklist = models.ForeignKey(Picklist, blank=True, null=True, db_index=True)
    quantity = models.FloatField(default=0)
    invoice_number = models.CharField(max_length=64, default='')
    challan_number = models.CharField(max_length=64, default='')
    order_status_flag = models.CharField(max_length=64, default='processed_orders')
    delivered_flag = models.IntegerField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SELLER_ORDER_SUMMARY'
        index_together = (('pick_number', 'seller_order'), ('pick_number', 'order'), ('pick_number', 'seller_order', 'picklist'),
                            ('pick_number', 'order', 'picklist'), ('order', 'order_status_flag'),
                          ('seller_order', 'order_status_flag'), ('picklist', 'seller_order'),
                          ('picklist', 'order'))

    def __unicode__(self):
        return str(self.id)


class TallyConfiguration(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User, blank=True, null=True)
    tally_ip = models.CharField(max_length=32, default='')
    tally_port = models.PositiveIntegerField(default=0)
    tally_path = models.CharField(max_length=256, default='')
    company_name = models.CharField(max_length=64, default='')
    stock_group = models.CharField(max_length=32, default='')
    stock_category = models.CharField(max_length=32, default='')
    maintain_bill = models.IntegerField(default=0)
    automatic_voucher = models.IntegerField(default=0)
    credit_period = models.IntegerField(default=0)
    round_off_ledger = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'TALLY_CONFIGURATION'

    def __unicode__(self):
        return str(self.company_name)

    def json(self):
        return {
            'id': self.id,
            'user_id': self.user.id,
            'tally_ip': self.tally_ip,
            'tally_port': self.tally_port,
            'tally_path': self.tally_path,
            'company_name': self.company_name,
            'stock_group': self.stock_group,
            'stock_category': self.stock_category,
            'maintain_bill': int(self.maintain_bill),
            'automatic_voucher': int(self.automatic_voucher),
            'credit_period': self.credit_period,
            'round_off_ledger': self.round_off_ledger,
        }


class MasterGroupMapping(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User, blank=True, null=True)
    master_type = models.CharField(max_length=32, default='')
    master_value = models.CharField(max_length=32, default='')
    parent_group = models.CharField(max_length=32, default='')
    sub_group = models.CharField(max_length=32, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'MASTER_GROUP_MAPPING'
        unique_together = ('master_type', 'master_value', 'user')

    def __unicode__(self):
        return str(self.parent_group)

    def json(self):
        return {
            'id': self.id,
            'user_id': self.user.id,
            'master_type': self.master_type,
            'master_value': self.master_value,
            'parent_group': self.parent_group,
            'sub_group': self.sub_group,
        }


class GroupLedgerMapping(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User, blank=True, null=True)
    ledger_type = models.CharField(max_length=64, default='')
    product_group = models.CharField(max_length=64, default='')
    state = models.CharField(max_length=64, default='')
    ledger_name = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'GROUP_LEDGER_MAPPING'
        unique_together = ('ledger_type', 'product_group', 'user')

    def __unicode__(self):
        return str(self.parent_group)

    def json(self):
        return {
            'id': self.id,
            'user_id': self.user.id,
            'ledger_type': self.ledger_type,
            'product_group': self.product_group,
            'state': self.state,
            'ledger_name': self.ledger_name
        }


class VatLedgerMapping(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User, blank=True, null=True)
    tax_type = models.CharField(max_length=32, default='')
    tax_percentage = models.FloatField(default=0)
    ledger_name = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "VAT_LEDGER_MAPPING"
        unique_together = ('tax_type', 'ledger_name', 'user')

    def __unicode__(self):
        return str(self.ledger_name)

    def json(self):
        return {
            'id': self.id,
            'user_id': self.user.id,
            'tax_type': self.tax_type,
            'tax_percentage': self.tax_percentage,
            'ledger_name': self.ledger_name,
        }


class CustomerCartData(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User)
    customer_user = models.ForeignKey(User, related_name='customer_user', blank=True, null=True)
    warehouse_level = models.IntegerField(default=0)
    sku = models.ForeignKey(SKUMaster)
    quantity = models.FloatField(default=1)
    tax = models.FloatField(default=0)
    inter_state = models.IntegerField(default=0)
    cgst_tax = models.FloatField(default=0)
    sgst_tax = models.FloatField(default=0)
    igst_tax = models.FloatField(default=0)
    utgst_tax = models.FloatField(default=0)
    remarks = models.CharField(max_length=128, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)
    levelbase_price = models.FloatField(default=0)

    class Meta:
        db_table = "CUSTOMER_CART_DATA"

    def json(self):
        invoice_amount = self.quantity * self.sku.price
        return {
            'sku_id': self.sku.sku_code,
            'quantity': self.quantity,
            'price': self.sku.price,
            'unit_price': self.sku.price,
            'invoice_amount': invoice_amount,
            'tax': self.tax,
            'total_amount': ((invoice_amount * self.tax) / 100) + invoice_amount,
            'image_url': self.sku.image_url,
            'cgst_tax': self.cgst_tax,
            'sgst_tax': self.sgst_tax,
            'igst_tax': self.igst_tax,
            'utgst_tax': self.utgst_tax,
            'warehouse_level': self.warehouse_level,
            'remarks': self.remarks,
        }


class ApprovingOrders(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User)
    customer_user = models.ForeignKey(User, related_name='accessing_customer', blank=True, null=True)
    approve_id = models.CharField(max_length=64, default='')
    approval_status = models.CharField(choices=APPROVAL_STATUSES, default='', max_length=32)
    approving_user_role = models.CharField(max_length=64, default='')
    sku = models.ForeignKey(SKUMaster)
    quantity = models.FloatField(default=1)
    unit_price = models.FloatField(default=0)
    tax = models.FloatField(default=0)
    inter_state = models.IntegerField(default=0)
    cgst_tax = models.FloatField(default=0)
    sgst_tax = models.FloatField(default=0)
    igst_tax = models.FloatField(default=0)
    utgst_tax = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)
    shipment_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "APPROVING_ORDERS"
        unique_together = ('user', 'customer_user', 'approve_id', 'approval_status', 'approving_user_role', 'sku')

    def json(self):
        invoice_amount = self.quantity * self.sku.price
        return {
            'sku_id': self.sku.sku_code,
            'quantity': self.quantity,
            'price': self.sku.price,
            'unit_price': self.sku.price,
            'invoice_amount': invoice_amount,
            'tax': self.tax,
            'total_amount': ((invoice_amount * self.tax) / 100) + invoice_amount,
            'image_url': self.sku.image_url,
            'cgst_tax': self.cgst_tax,
            'sgst_tax': self.sgst_tax,
            'igst_tax': self.igst_tax,
            'utgst_tax': self.utgst_tax,
        }


class TaxMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User, null=True, blank=True, default=None)
    product_type = models.CharField(max_length=64, default='')
    inter_state = models.IntegerField(default=0)
    cgst_tax = models.FloatField(default=0)
    sgst_tax = models.FloatField(default=0)
    igst_tax = models.FloatField(default=0)
    cess_tax = models.FloatField(default=0)
    utgst_tax = models.FloatField(default=0)
    min_amt = models.FloatField(default=0)
    max_amt = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'TAX_MASTER'
        # unique_together = ('user', 'product_type', 'inter_state', 'cgst_tax', 'sgst_tax', 'igst_tax')
        index_together = ('user', 'product_type', 'inter_state')

    def json(self):
        return {
            'id': self.id,
            'product_type': self.product_type,
            'inter_state': self.inter_state,
            'cgst_tax': self.cgst_tax,
            'sgst_tax': self.sgst_tax,
            'igst_tax': self.igst_tax,
            'cess_tax': self.cess_tax,
            'utgst_tax': self.utgst_tax,
            'min_amt': self.min_amt,
            'max_amt': self.max_amt,
            'user_id': self.user.id
        }


class POLabels(models.Model):
    id = BigAutoField(primary_key=True)
    sku = models.ForeignKey(SKUMaster, blank=True, null=True)
    purchase_order = models.ForeignKey(PurchaseOrder, blank=True, null=True)
    job_order = models.ForeignKey(JobOrder, blank=True, null=True)
    label = models.CharField(max_length=128, default='')
    serial_number = models.IntegerField(default=0)
    custom_label = models.IntegerField(default=0)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PO_LABELS'
        unique_together = ('purchase_order', 'job_order', 'sku', 'label')
        index_together = (('purchase_order', 'sku', 'label'), ('job_order', 'sku', 'label'))

    def __unicode__(self):
        return str(self.label)


class SKUAttributes(models.Model):
    sku = models.ForeignKey(SKUMaster, blank=True, null=True)
    attribute_name = models.CharField(max_length=64, default='')
    attribute_value = models.CharField(max_length=128, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_ATTRIBUTES'
        unique_together = ('sku', 'attribute_name')
        index_together = ('sku', 'attribute_name')

    def __unicode__(self):
        return str(self.sku.sku_code) + '-' + str(self.attribute_name)


class OrderPOMapping(models.Model):
    sku = models.ForeignKey(SKUMaster, blank=True, null=True)
    order_id = models.CharField(max_length=64, default='')
    purchase_order_id = models.CharField(max_length=64, default='')
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_PO_MAPPING'
        index_together = ('order_id', 'purchase_order_id', 'sku')


class OrderTracking(models.Model):
    order = models.ForeignKey(OrderDetail, blank=True, null=True)
    quantity = models.FloatField(default=0)
    imei = models.CharField(max_length=128, default='')
    status = models.CharField(max_length=32, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_TRACKING'
        index_together = ('order', 'quantity')


class BarcodeSettings(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User)
    format_type = models.CharField(max_length=256)
    size = models.CharField(max_length=256, blank=True, null=True)
    show_fields = models.CharField(max_length=256, blank=True, null=True)
    rows_columns = models.CharField(max_length=64, blank=True, null=True)
    styles = models.TextField(blank=True, null=True)
    mapping_fields = models.CharField(max_length=256, blank=True, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'BARCODE_SETTINGS_TABLE'
        unique_together = (('user', 'format_type'),)

    def __unicode__(self):
        return "%s, %s %s" % (self.user, self.show_fields, self.rows_columns)


class InvoiceSequence(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User)
    marketplace = models.CharField(max_length=64)
    prefix = models.CharField(max_length=64)
    interfix = models.CharField(max_length=64, default='')
    date_type = models.CharField(max_length=32, default='')
    value = models.PositiveIntegerField()
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'INVOICE_SEQUENCE'
        index_together = ('user', 'marketplace')
        unique_together = ('user', 'marketplace')


class ChallanSequence(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User)
    marketplace = models.CharField(max_length=64)
    prefix = models.CharField(max_length=64)
    value = models.PositiveIntegerField()
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CHALLAN_SEQUENCE'
        index_together = ('user', 'marketplace')
        unique_together = ('user', 'marketplace')


class OrderAwbMap(models.Model):
    user = models.ForeignKey(User)
    original_order_id = models.CharField(max_length=128, default='')
    awb_no = models.CharField(max_length=128, default='')
    marketplace = models.CharField(max_length=128, default='')
    courier_name = models.CharField(max_length=128, default='')
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ORDER_AWB_MAP'
        index_together = ('original_order_id', 'awb_no')
        unique_together = ('original_order_id', 'awb_no')


class UserRoleMapping(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User, blank=True, null=True)
    role_id = models.CharField(max_length=64, default='')
    role_type = models.CharField(max_length=32, choices=ROLE_TYPE_CHOICES, default='supplier')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'USER_ROLE_MAPPING'
        index_together = ('user', 'role_id', 'role_type')
        unique_together = ('user', 'role_id', 'role_type')


import django
from django.core.validators import MaxLengthValidator
from django.utils.translation import ugettext as _
from django.db.models.signals import class_prepared
from django.conf import settings

'''
def longer_username_signal(sender, *args, **kwargs):
    if (sender.__name__ == "User" and
        sender.__module__ == "django.contrib.auth.models"):
        patch_user_model(sender)
class_prepared.connect(longer_username_signal)

def patch_user_model(model):
    field = model._meta.get_field("first_name")

    field.max_length = MAX_USERNAME_LENGTH()
    field.help_text = _("Required, %s characters or fewer. Only letters, "
                        "numbers, and @, ., +, -, or _ "
                        "characters." % MAX_USERNAME_LENGTH())

    # patch model field validator because validator doesn't change if we change
    # max_length
    for v in field.validators:
        if isinstance(v, MaxLengthValidator):
            v.limit_value = MAX_USERNAME_LENGTH()

from django.contrib.auth.models import User

if User._meta.get_field("first_name").max_length != MAX_USERNAME_LENGTH():
    patch_user_model(User)
'''


class NetworkMaster(models.Model):
    id = BigAutoField(primary_key=True)
    dest_location_code = models.ForeignKey(User)
    source_location_code = models.ForeignKey(User, related_name='source_location_code')
    lead_time = models.PositiveIntegerField(blank=True)
    sku_stage = models.CharField(max_length=50, blank=True)
    priority = models.IntegerField(blank=True)
    price_type = models.CharField(max_length=32, default='')
    charge_remarks = models.CharField(max_length=50, choices=REMARK_CHOICES, default='')
    supplier = models.ForeignKey(SupplierMaster, null=True, blank=True, default=None)

    def json(self):
        return {
            'id': self.id,
            'dest_location_code': self.dest_location_code.username,
            'source_location_code': self.source_location_code.username,
            'lead_time': self.lead_time,
            'sku_stage': self.sku_stage,
            'priority': self.priority,
            'price_type': self.price_type,
            'charge_remarks': self.charge_remarks,
        }

    class Meta:
        db_table = 'NETWORK_MASTER'
        unique_together = ('dest_location_code', 'source_location_code', 'sku_stage')


class OrderUploads(models.Model):
    id = BigAutoField(primary_key=True)
    uploaded_user = models.ForeignKey(User)
    po_number = models.CharField(max_length=128, default='')
    uploaded_date = models.DateField()
    customer_name = models.CharField(max_length=256, default='')
    uploaded_file = models.FileField(upload_to='static/customer_uploads/')
    verification_flag = models.CharField(max_length=54, default='to_be_verified')
    remarks = models.CharField(max_length=256, default='')

    class Meta:
        db_table = 'ORDER_UPLOADS'
        unique_together = ('uploaded_user', 'po_number', 'customer_name')


class CustomerPricetypes(models.Model):
    id = BigAutoField(primary_key=True)
    customer = models.ForeignKey(CustomerMaster)
    level = models.IntegerField(default=1)
    price_type = models.CharField(max_length=32, default='')
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CUSTOMER_PRICE_TYPES'
        unique_together = ('customer', 'level', 'price_type')
        index_together = (('customer', 'level'), ('customer', 'level', 'price_type'))


class EnquiryMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    enquiry_id = models.DecimalField(max_digits=50, decimal_places=0)
    customer_id = models.PositiveIntegerField(default=0)
    customer_name = models.CharField(max_length=256, default='')
    email_id = models.EmailField(max_length=64, default='')
    address = models.CharField(max_length=256, default='')
    telephone = models.CharField(max_length=128, default='', blank=True, null=True)
    vat_percentage = models.FloatField(default=0)
    city = models.CharField(max_length=60, default='')
    state = models.CharField(max_length=60, default='')
    pin_code = models.PositiveIntegerField(default=0)
    remarks = models.CharField(max_length=128, default='')
    extend_status = models.CharField(max_length=54, default='')
    extend_date = models.DateField()
    corporate_name = models.CharField(max_length=256, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ENQUIRY_MASTER'
        unique_together = ('enquiry_id', 'customer_id', 'user')

        # def __unicode__(self):
        #     return '{0} : {1}'.format(str(self.sku), str(self.enquiry_id))


class EnquiredSku(models.Model):
    id = BigAutoField(primary_key=True)
    sku = models.ForeignKey(SKUMaster)
    title = models.CharField(max_length=256, default='')
    enquiry = models.ForeignKey(EnquiryMaster)
    quantity = models.FloatField(default=0)
    invoice_amount = models.FloatField(default=0)
    status = models.CharField(max_length=32)
    sku_code = models.CharField(max_length=256, default='')
    levelbase_price = models.FloatField(default=0)
    warehouse_level = models.IntegerField(default=0)

    class Meta:
        db_table = 'EnquiredSKUS'
        # unique_together = ('sku', 'enquiry')


class ASNReserveDetail(models.Model):
    id = BigAutoField(primary_key=True)
    asnstock = models.ForeignKey(ASNStockDetail, blank=True, null=True)
    orderdetail = models.ForeignKey(OrderDetail, blank=True, null=True)
    enquirydetail = models.ForeignKey(EnquiredSku, blank=True, null=True)
    reserved_qty = models.IntegerField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ASN_RESERVE_DETAIL'
        unique_together = ('asnstock', 'orderdetail')


class TANDCMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    term_type = models.CharField(max_length=32, default='')
    terms = models.TextField(default='', max_length=256)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'TANDC_MASTER'


class SKUDetailStats(models.Model):
    id = BigAutoField(primary_key=True)
    sku = models.ForeignKey(SKUMaster, blank=True, null=True)
    transact_id = models.IntegerField(default=0)
    transact_type = models.CharField(max_length=36, default='')
    quantity = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_DETAIL_STATS'
        index_together = (('sku', 'transact_type'), ('sku', 'transact_type', 'transact_id'))

class StockStats(models.Model):
    id = BigAutoField(primary_key=True)
    sku = models.ForeignKey(SKUMaster, blank=True, null=True)
    opening_stock = models.FloatField(default=0)
    receipt_qty = models.FloatField(default=0)
    uploaded_qty = models.FloatField(default=0)
    produced_qty = models.FloatField(default=0)
    dispatch_qty = models.FloatField(default=0)
    return_qty = models.FloatField(default=0)
    adjustment_qty = models.FloatField(default=0)
    consumed_qty = models.FloatField(default=0)
    closing_stock = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'STOCK_STATS'
        index_together = (('sku',))


class IntransitOrders(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    customer_id = models.PositiveIntegerField()
    intr_order_id = models.DecimalField(max_digits=50, decimal_places=0)
    sku = models.ForeignKey(SKUMaster)
    quantity = models.FloatField(default=0)
    unit_price = models.FloatField(default=0)
    invoice_amount = models.FloatField(default=0)
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'INTRANSIT_ORDERS'
        unique_together = ('user', 'customer_id', 'intr_order_id', 'sku')


class StaffMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    staff_name = models.CharField(max_length=256, default='')
    phone_number = models.CharField(max_length=32)
    email_id = models.EmailField(max_length=64, default='')
    status = models.IntegerField(default=1)

    class Meta:
        db_table = 'STAFF_MASTER'
        unique_together = ('user', 'staff_name')
        index_together = ('user', 'staff_name')


class MastersMapping(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.PositiveIntegerField()
    master_id = models.CharField(max_length=32)
    mapping_id = models.CharField(max_length=32)
    mapping_type = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'MASTERS_MAPPING'
        unique_together = ('user', 'master_id', 'mapping_id', 'mapping_type')


class ManualEnquiry(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User)
    enquiry_id = models.DecimalField(max_digits=50, decimal_places=0)
    customer_name = models.CharField(max_length=256, default='')
    sku = models.ForeignKey(SKUMaster)
    quantity = models.PositiveIntegerField()
    customization_type =  models.CharField(max_length=64, default='',  choices=CUSTOMIZATION_TYPES)
    custom_remarks = models.TextField(default='')
    po_number = models.CharField(max_length=128, default='')
    status = models.CharField(max_length=32)
    smd_price = models.FloatField(default=0)
    rc_price = models.FloatField(default=0)
    client_po_rate = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'MANUAL_ENQUIRY'
        unique_together = ('enquiry_id', 'customer_name', 'user')


class ManualEnquiryDetails(models.Model):
    id = BigAutoField(primary_key=True)
    user_id = models.PositiveIntegerField()
    enquiry = models.ForeignKey(ManualEnquiry)
    ask_price = models.FloatField(default=0)
    expected_date = models.DateField(blank=True, null=True)
    remarks = models.TextField(default='')
    status = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'MANUAL_ENQUIRY_DETAILS'


class ManualEnquiryImages(models.Model):
    id = BigAutoField(primary_key=True)
    enquiry = models.ForeignKey(ManualEnquiry)
    image = models.ImageField(upload_to='static/images/manual_enquiry/')
    image_type = models.CharField(max_length=32, default='res_images')
    status = models.CharField(max_length=32)

    class Meta:
        db_table = 'MANUAL_ENQUIRY_IMAGES'


class GroupPermMapping(models.Model):
    id = BigAutoField(primary_key=True)
    group = models.ForeignKey(Group)
    perm_type = models.CharField(max_length=32)
    perm_value = models.CharField(max_length=64, default='')
    sequence = models.IntegerField(default=0)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'GROUP_PERM_MAPPING'
        unique_together = ('group', 'perm_type', 'perm_value')


class SellerTransfer(models.Model):
    id = BigAutoField(primary_key=True)
    source_seller = models.ForeignKey(SellerMaster)
    dest_seller = models.ForeignKey(SellerMaster, related_name='destination')
    transact_id = models.DecimalField(max_digits=20, decimal_places=0, db_index=True, default=0)
    transact_type = models.CharField(max_length=32)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SELLER_TRANSFER'
        unique_together = ('source_seller', 'dest_seller', 'transact_id')
        index_together = ('source_seller', 'dest_seller', 'transact_id')


class SellerStockTransfer(models.Model):
    id = BigAutoField(primary_key=True)
    seller_transfer = models.ForeignKey(SellerTransfer)
    sku = models.ForeignKey(SKUMaster)
    source_location = models.ForeignKey(LocationMaster)
    dest_location = models.ForeignKey(LocationMaster, related_name='dest_location')
    quantity = models.PositiveIntegerField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SELLER_STOCK_TRANSFER'
        unique_together = ('seller_transfer', 'sku', 'source_location', 'dest_location')
        index_together = ('seller_transfer', 'sku', 'source_location', 'dest_location')


class MailAlerts(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User, blank=True, null=True)
    alert_name = models.CharField(max_length=64, default='')
    alert_type = models.CharField(max_length=64, default='')
    alert_value = models.PositiveIntegerField()
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'MAIL_ALERTS'
        unique_together = ('user', 'alert_name')


class UserAttributes(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User, blank=True, null=True)
    attribute_model = models.CharField(max_length=32, default='')
    attribute_name = models.CharField(max_length=64, default='')
    attribute_type = models.CharField(max_length=64, default='')
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'USER_ATTRIBUTES'
        unique_together = ('user', 'attribute_model', 'attribute_name')


@reversion.register()
class PrimarySegregation(models.Model):
    id = BigAutoField(primary_key=True)
    purchase_order = models.ForeignKey(PurchaseOrder, blank=True, null=True)
    batch_detail = models.ForeignKey(BatchDetail, blank=True, null=True)
    quantity = models.FloatField(default=0)
    sellable = models.FloatField(default=0)
    non_sellable = models.FloatField(default=0)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PRIMARY_SEGREGATION'
        unique_together = ('purchase_order', 'batch_detail')



def get_path(instance, filename):
    return "static/master_docs/%s_%s/%s" %(instance.master_type, instance.master_id, filename)

class MasterDocs(models.Model):
    id = BigAutoField(primary_key=True)
    master_id = models.CharField(max_length=64, default='')
    master_type = models.CharField(max_length=64, default='')
    uploaded_file = models.FileField(upload_to=get_path, blank=True, null=True)
    extra_flag = models.CharField(max_length=32, default='')
    user = models.ForeignKey(User, blank=True, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'MASTER_DOCS'
        index_together = (('master_id', 'master_type', 'uploaded_file'),
                          ('user', 'master_id', 'master_type', 'extra_flag'))


class WarehouseSKUMapping(models.Model):
    id = BigAutoField(primary_key=True)
    warehouse = models.ForeignKey(User)
    sku = models.ForeignKey(SKUMaster)
    priority = models.CharField(max_length=32)
    moq = models.FloatField(default=0)
    price = models.FloatField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'WAREHOUSE_SKU_MAPPING'
        index_together = ('warehouse', 'sku')

    def __unicode__(self):
        return str(self.sku) + " : " + str(self.warehouse)


class SellerOrderTransfer(models.Model):
    id = BigAutoField(primary_key=True)
    seller_transfer = models.ForeignKey(SellerTransfer)
    seller_order = models.ForeignKey(SellerOrder)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SELLER_ORDER_TRANSFER'
        unique_together = ('seller_transfer', 'seller_order')
        index_together = ('seller_transfer', 'seller_order')


@reversion.register()
class ReturnToVendor(models.Model):
    id = BigAutoField(primary_key=True)
    rtv_number = models.CharField(max_length=32, default='')
    seller_po_summary = models.ForeignKey(SellerPOSummary, blank=True, null=True)
    location = models.ForeignKey(LocationMaster, blank=True, null=True)
    quantity = models.FloatField(default=0)
    status = models.IntegerField(default=1)
    return_type = models.CharField(max_length=32, default='Invoice')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'RETURN_TO_VENDOR'


class TargetMaster(models.Model):
    id = BigAutoField(primary_key=True)
    distributor = models.ForeignKey(User, related_name='distributor', blank=True, null=True)
    reseller = models.ForeignKey(User, related_name='reseller', blank=True, null=True)
    corporate_id = models.IntegerField(max_length=10)
    target_amt = models.FloatField(default=0)
    target_duration = models.IntegerField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'TARGET_MASTER'
        unique_together = ('distributor', 'reseller', 'corporate_id')


class OneSignalDeviceIds(models.Model):
    device_id = models.CharField(max_length = 125, null=False)
    user = models.ForeignKey(User, null=False)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ONESIGNAL_DEVICEIDS'


class RatingsMaster(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User)
    original_order_id = models.CharField(max_length=128, default='', blank=True, null=True)
    rating_product = models.IntegerField(max_length=10)
    rating_order = models.IntegerField(max_length=10)
    reason_product = models.CharField(max_length=128, default='')
    reason_order = models.CharField(max_length=128, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'RATINGS_MASTER'
        unique_together = ('user', 'original_order_id')


class RatingSKUMapping(models.Model):
    id = BigAutoField(primary_key=True)
    rating = models.ForeignKey(RatingsMaster, blank=True, null=True)
    sku = models.ForeignKey(SKUMaster)
    remarks = models.CharField(max_length=128, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'RATINGS_SKU_MAPPING'
        unique_together = ('rating', 'sku')


class PushNotifications(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User, blank=True, null=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'PUSH_NOTIFICATIONS'


class SellableSuggestions(models.Model):
    id = BigAutoField(primary_key=True)
    seller = models.ForeignKey(SellerMaster, blank=True, null=True)
    stock = models.ForeignKey(StockDetail, blank=True, null=True)
    location = models.ForeignKey(LocationMaster)
    quantity = models.FloatField(default=0)
    status = models.IntegerField(default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SELLABLE_SUGGESTIONS'
        index_together = (('seller', 'stock', 'status'), ('stock', 'status'))


class TableUpdateHistory(models.Model):
    id = BigAutoField(primary_key=True)
    user = models.ForeignKey(User, blank=True, null=True)
    model_id = models.PositiveIntegerField()
    model_name = models.CharField(max_length=32, default='')
    model_field = models.CharField(max_length=32, default='')
    previous_val = models.CharField(max_length=64, default='')
    updated_val = models.CharField(max_length=64, default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'TABLE_UPDATE_HISTORY'
        index_together = (('user', 'model_id'), ('user', 'model_id', 'model_name'),
                          ('user', 'model_id', 'model_name', 'model_field'))


class SKUPackMaster(models.Model):
    id = BigAutoField(primary_key=True)
    sku = models.ForeignKey(SKUMaster)
    pack_id = models.CharField(max_length=32, default='')
    pack_quantity = models.PositiveIntegerField()
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'SKU_PACK_MASTER'
        unique_together = ('sku', 'pack_id')


class TempJson(models.Model):
    id = BigAutoField(primary_key=True)
    model_id = models.PositiveIntegerField()
    model_name = models.CharField(max_length=32, default='')
    model_json = models.TextField(default='')
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'TEMP_JSON'
        index_together = ('model_id', 'model_name')
