from miebach_admin.models import *
import datetime
import dateutil.relativedelta
from django.db.models import Sum, F, Q
import datetime
from django.db import models
from django.contrib.auth.models import User, Group
from miebach_admin.miebach_utils import BigAutoField
from datetime import date
from reversion.models import Version

class BigIntegerField(models.fields.IntegerField):
    def db_type(self, connection):
        if 'mysql' in connection.__class__.__module__:
            return 'bigint '
        return super(BigIntegerField, self).db_type(connection)

class AnalyticsGRN(models.Model):
    id = BigAutoField(primary_key=True)
    grn_id= BigIntegerField(blank=True, null=True, default=0)
    grn_number = models.CharField(max_length=32, default='', db_index=True)
    invoice_date = models.DateField(blank=True, null=True)
    invoice_number = models.CharField(max_length=64, default='')
    grn_date = models.DateTimeField(blank=True, null=True)
    grn_user = models.CharField(max_length=128, default='')
    zone = models.CharField(max_length=64, default='')
    plant_code = models.CharField(max_length=64, default='', db_index=True)
    plant_name = models.CharField(max_length=128, default='')
    department_name = models.CharField(max_length=128, default='')
    department_code = models.CharField(max_length=64, default='')
    supplier_id = models.CharField(max_length=128, default='', db_index=True)
    supplier_name = models.CharField(max_length=256, db_index=True)
    supplier_state = models.CharField(max_length=64)
    supplier_country = models.CharField(max_length=64)
    supplier_gst_number = models.CharField(max_length=64, default='')
    sku_code = models.CharField(max_length=128, db_index=True)
    sku_desc = models.CharField(max_length=350, default='')
    sku_category = models.CharField(max_length=128, default='')
    sku_class = models.CharField(max_length=64, default='')
    sku_brand = models.CharField(max_length=64, default='')
    hsn_code = models.CharField(max_length=20, db_index=True, default='')
    sgst_tax = models.FloatField(default=0)
    cgst_tax = models.FloatField(default=0)
    igst_tax = models.FloatField(default=0)
    cess_tax = models.FloatField(default=0)
    price = models.FloatField(default=0)    
    base_quantity = models.FloatField(default=0)
    base_uom = models.CharField(max_length=64)
    pquantity = models.FloatField(default=0)
    puom = models.CharField(max_length=64)
    pcf = models.FloatField(default=0)
    overall_discount = models.FloatField(default=0)
    tcs_value = models.FloatField(default=0)
    remarks = models.CharField(max_length=64, default='')
    challan_number = models.CharField(max_length=64, default='')
    challan_date = models.DateField(blank=True, null=True)
    discount_percent = models.FloatField(default=0)
    round_off_total = models.FloatField(default=0)
    invoice_value = models.FloatField(default=0)
    invoice_quantity = models.FloatField(default=0)
    invoice_receipt_date = models.DateField(blank=True, null=True)
    credit_type = models.CharField(max_length=32, default='Invoice')
    credit_status = models.IntegerField(default=0)
    batch_no = models.CharField(max_length=64, default='')
    mrp = models.FloatField(default=0)
    manufactured_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    status = models.IntegerField(default=0)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ANALYTICS_GRN'


class AnalyticsPurchaseOrder(models.Model):
    id = BigAutoField(primary_key=True)
    po_id= BigIntegerField(blank=True, null=True, default=0)
    full_po_number = models.CharField(max_length=32, default='', db_index=True)
    po_date = models.DateTimeField(blank=True, null=True)
    po_raised_date = models.DateTimeField(blank=True, null=True)
    requested_user = models.CharField(max_length=128, default='')
    wh_user = models.CharField(max_length=128, default='')
    zone = models.CharField(max_length=64, default='')
    plant_code = models.CharField(max_length=64, default='')
    plant_name = models.CharField(max_length=128, default='')
    department_name = models.CharField(max_length=128, default='')
    department_code = models.CharField(max_length=64, default='')
    sku_code = models.CharField(max_length=128)
    sku_desc = models.CharField(max_length=350, default='')
    sku_category = models.CharField(max_length=128, default='')
    sku_class = models.CharField(max_length=64, default='')
    sku_brand = models.CharField(max_length=64, default='')
    hsn_code = models.CharField(max_length=20, db_index=True, default='')
    supplier_id = models.CharField(max_length=128, default='', db_index=True)
    supplier_name = models.CharField(max_length=256, db_index=True)
    supplier_state = models.CharField(max_length=64)
    supplier_country = models.CharField(max_length=64)
    supplier_gst_number = models.CharField(max_length=64, default='')
    payment_terms = models.CharField(max_length=256, default='')
    sgst_tax = models.FloatField(default=0)
    cgst_tax = models.FloatField(default=0)
    igst_tax = models.FloatField(default=0)
    cess_tax = models.FloatField(default=0)
    price = models.FloatField(default=0)    
    received_quantity = models.FloatField(default=0)
    base_quantity = models.FloatField(default=0)
    base_uom = models.CharField(max_length=64)
    pquantity = models.FloatField(default=0)
    puom = models.CharField(max_length=64)
    pcf = models.FloatField(default=0)
    currency = models.TextField(default='INR')
    currency_internal_id = models.IntegerField(default=1)
    currency_rate = models.FloatField(default=1)
    pending_at = models.CharField(max_length=1024, default='')
    po_status = models.CharField(max_length=64, default='')
    final_status = models.CharField(max_length=64, default='')
    delivery_date = models.DateField(blank=True, null=True)
    analytics_grn = models.ForeignKey(AnalyticsGRN, blank=True, null=True, related_name="analatics_pos")
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ANALYTICS_PURCHASE_ORDER'


class AnalyticsPurchaseRequest(models.Model):
    id = BigAutoField(primary_key=True)
    full_pr_number = models.CharField(max_length=32, default='', db_index=True)
    pr_date = models.DateTimeField(blank=True, null=True)
    requested_user = models.CharField(max_length=128, default='')
    wh_user = models.CharField(max_length=128, default='')
    zone = models.CharField(max_length=64, default='')
    plant_code = models.CharField(max_length=64, default='')
    plant_name = models.CharField(max_length=128, default='')
    department_name = models.CharField(max_length=128, default='')
    department_code = models.CharField(max_length=64, default='')
    sku_code = models.CharField(max_length=128)
    sku_desc = models.CharField(max_length=350, default='')
    sku_category = models.CharField(max_length=128, default='')
    sku_class = models.CharField(max_length=64, default='')
    sku_brand = models.CharField(max_length=64, default='')
    hsn_code = models.CharField(max_length=20, db_index=True, default='')
    supplier_id = models.CharField(max_length=128, default='', db_index=True)
    supplier_name = models.CharField(max_length=256, db_index=True)
    supplier_state = models.CharField(max_length=64)
    supplier_country = models.CharField(max_length=64)
    supplier_gst_number = models.CharField(max_length=64, default='')
    sgst_tax = models.FloatField(default=0)
    cgst_tax = models.FloatField(default=0)
    igst_tax = models.FloatField(default=0)
    cess_tax = models.FloatField(default=0)
    price = models.FloatField(default=0)    
    base_quantity = models.FloatField(default=0)
    base_uom = models.CharField(max_length=64)
    pquantity = models.FloatField(default=0)
    puom = models.CharField(max_length=64)
    pcf = models.FloatField(default=0)
    pending_at = models.CharField(max_length=1024, default='')
    final_status = models.CharField(max_length=64, default='')
    delivery_date = models.DateField(blank=True, null=True)
    priority_type = models.CharField(max_length=32, default='')
    purchase_orders = models.ManyToManyField(AnalyticsPurchaseOrder, blank=True, null=True, related_name="analatics_prs")
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ANALYTICS_PURCHASE_REQUEST'


def get_pr_detail_report_data(search_params, user, sub_user):
    final_list= []
    from rest_api.views.inbound import findLastLevelToApprove
    from rest_api.views.common import get_misc_value, get_admin, get_uom_with_multi_skus, get_sku_wise_pr_amount_and_quantity
    from rest_api.views.common import get_sku_master, get_local_date, get_filtered_params, \
        get_warehouse_user_from_sub_user, get_plant_and_department, get_all_department_data, get_related_users_filters, check_and_get_plants_depts_wo_request
    now =  datetime.datetime.now()
#    last_year = now + dateutil.relativedelta.relativedelta(years=-1)
    last_hour = now + dateutil.relativedelta.relativedelta(hours=-275)
#    last_month = now + dateutil.relativedelta.relativedelta(months=-1)
    search_parameters = {'purchase_type': 'PR'}
    from_date = search_params.get("from_date", {})
    if from_date:
        search_parameters.update({'pending_pr__updation_date__gte': from_date})
    values_list = ['pending_pr__requested_user', 'pending_pr__requested_user__first_name', 'pending_po__po_number',
                   'pending_pr__requested_user__username', 'pending_pr__pr_number', 'pending_pr__final_status',
                   'pending_pr__pending_level', 'pending_pr__remarks', 'pending_pr__delivery_date', 'pending_pr__wh_user', 'pending_pr__wh_user__first_name','pending_pr__wh_user__userprofile__zone',
                   'pending_pr__sku_category', 'pending_pr__full_pr_number', 'pending_pr__creation_date',
                   'pending_pr__product_category', 'pending_pr__priority_type', 'pending_pr_id', 'measurement_unit',
                   'pending_pr__sub_pr_number', 'pending_pr__prefix','sku__sku_code', 'sku__sku_desc',
                   'sku__sku_category', 'sku__sku_class', 'sku__sku_brand','sku__style_name', 'sku__price',
                   'cgst_tax', 'sgst_tax', 'igst_tax', 'cess_tax',
                   'sku__mrp', 'sku__sub_category', 'sku__sku_group','quantity', 'price', 'sku__hsn_code', 'pending_pr_id']
    search_parameters1 = {}
    for spk, spv in search_parameters.items():
        if 'pending_pr__' in spk:
            search_parameters1[spk.replace('pending_pr__', '')] = spv
    if 'purchase_type' in search_parameters1:
        del search_parameters1['purchase_type']
    pl_main = PendingPR.objects.filter(**search_parameters1)
    pending_data = PendingLineItems.objects.filter(**search_parameters).values(*values_list).distinct(). \
        annotate(total_qty=Sum('quantity')).annotate(total_amt=Sum(F('quantity') * F('price')))
    resultsWithDate = dict(pl_main.values_list('pr_number', 'creation_date'))
    results = pending_data
    sku_codes_list = []
    for each_rw in  results:
        sku_codes_list.append(each_rw['sku__sku_code'])
    skus_uom_dict = get_uom_with_multi_skus(user, sku_codes_list, uom_type='purchase')
    count = 0
    print("Pending PR Total Count",len(results))
    for result in results:
        pr_obj = PendingPR.objects.get(id=result['pending_pr_id'])
        po_numbers = ','.join(pr_obj.pendingpo_set.filter().values_list('full_po_number', flat=True))
        pr_supplier_id, pr_supplier_name, pr_supplier_gst, pr_supplier_state, pr_supplier_country = '', '', '', '', ''
        approver_1_details, approver_2_details, approver_3_details, approver_4_details, approver_5_details = '', '', '', '', ''
        pr_created_date = resultsWithDate.get(result['pending_pr__pr_number'])
        pr_date = pr_created_date.strftime('%d-%m-%Y')
        final_status =  result['pending_pr__final_status']
        requested_user = result['pending_pr__requested_user']
        product_category = result['pending_pr__product_category']
        if requested_user:
            pr_user = get_warehouse_user_from_sub_user(requested_user)
            warehouse = pr_user.first_name
            warehouse_type = pr_user.userprofile.warehouse_type
        product_category = result['pending_pr__product_category']
        sku_category = result['pending_pr__sku_category']
        sku_category_val = sku_category
        if sku_category == 'All':
            sku_category_val = ''
        pr_user = get_warehouse_user_from_sub_user(requested_user)
        warehouse = pr_user.first_name
        storeObj = get_admin(pr_user)
        store = storeObj.first_name
        warehouse_type = pr_user.userprofile.stockone_code
        last_updated_by, last_updated_time, last_remarks = '', '', ''
        if result['pending_pr__sub_pr_number']:
            full_pr_number = '%s/%s' % (result['pending_pr__full_pr_number'], result['pending_pr__sub_pr_number'])
        else:
            full_pr_number = result['pending_pr__full_pr_number']
        dateInPR = str(pr_date).split(' ')[0].replace('-', '')
        pr_sub_date = get_local_date(user, result['pending_pr__creation_date'])
        plant, department, department_code,plant_zone, pr_plant_code = '', '', '', '', ''
        req_user = User.objects.filter(id = result['pending_pr__wh_user'])[0]
        if req_user:
            req_user= req_user
            if req_user.userprofile.warehouse_type.lower() == 'dept':
                department= req_user.first_name
                department_code = req_user.userprofile.stockone_code
                admin_user = get_admin(req_user)
                pr_plant_code = admin_user.userprofile.stockone_code
                plant = admin_user.userprofile.user.first_name
                plant_zone = admin_user.userprofile.zone
            else:
                pr_plant_code = req_user.userprofile.stockone_code
                plant = req_user.first_name
                plant_zone = req_user.userprofile.zone
        # department, plant = get_plant_and_department(req_user)
        pending_approval = PurchaseApprovals.objects.filter(
            pending_pr__full_pr_number=result['pending_pr__full_pr_number'],
            status='', pending_pr__final_status='pending')
        next_approver_mail, pending_level, approval_type = [''] * 3
        if pending_approval.exists():
            pending_approval = pending_approval[0]
            next_approver_mail = pending_approval.validated_by
            pending_level = pending_approval.level
            approval_type = pending_approval.approval_type
        final_status = result['pending_pr__final_status']
        total_quantity, total_amount, total_tax_amount =0,0, 0
        total_quantity, total_amount, total_tax_amount = get_sku_wise_pr_amount_and_quantity(full_pr_number, result['sku__sku_code'])
        lineItemId = PendingLineItems.objects.filter(pending_pr__full_pr_number = result['pending_pr__full_pr_number'], sku__sku_code= result['sku__sku_code'])[0]
        pr_supplier_data = TempJson.objects.filter(model_name='PENDING_PR_PURCHASE_APPROVER', model_id= lineItemId.id)
        if pr_supplier_data.exists():
            json_data = eval(pr_supplier_data[0].model_json)
            pr_supplier_id = json_data['supplier_id']
            storeObj = get_admin(lineItemId.pending_pr.wh_user)
            supplierQs = SupplierMaster.objects.filter(user=storeObj.id, supplier_id=pr_supplier_id)
            if supplierQs.exists():
                pr_supplier_name = supplierQs[0].name
                pr_supplier_gst = supplierQs[0].tin_number
        else:
            pr_supplier_data = PendingPO.objects.filter(pending_prs__full_pr_number = result['pending_pr__full_pr_number'], pending_prs__sub_pr_number=result['pending_pr__sub_pr_number'])
            if pr_supplier_data.exists():
                try:
                    pr_supplier_id = pr_supplier_data[0].supplier.supplier_id
                    pr_supplier_name = pr_supplier_data[0].supplier.name
                    pr_supplier_gst = pr_supplier_data[0].supplier.tin_number
                    pr_supplier_country = pr_supplier_data[0].supplier.country
                    pr_supplier_state = pr_supplier_data[0].supplier.state
                except:
                    pr_supplier_id = ''
                    pr_supplier_name = ''
                    pr_supplier_gst = ''
        data = {"price":0, "pquantity": 0}
        uom_dict = skus_uom_dict.get(result['sku__sku_code'])
        pcf = uom_dict.get('sku_conversion', 1)
        if full_pr_number:
            data['full_pr_number'] = full_pr_number
        if pr_plant_code:
            data['plant_code'] = pr_plant_code
        if result['pending_pr__creation_date']:
            data['pr_date'] =  result['pending_pr__creation_date']
        if 'pending_pr__requested_user__first_name' in result and result['pending_pr__requested_user__first_name']:
            data['requested_user'] = result['pending_pr__requested_user__first_name']
        if 'pending_pr__wh_user__first_name' in result and result['pending_pr__wh_user__first_name']:
            data['wh_user'] = result['pending_pr__wh_user__first_name']
        if 'pending_pr__wh_user__userprofile__zone' in result and result['pending_pr__wh_user__userprofile__zone']:
            data['zone'] = result['pending_pr__wh_user__userprofile__zone']
        if plant:
            data['plant_name']= plant
        if department:
            data['department_name'] = department
        if department_code:
            data['department_code'] = department_code
        if result['sku__sku_code']:
            data['sku_code'] = result['sku__sku_code']
        if result['sku__sku_desc']:
            data['sku_desc'] = result['sku__sku_desc']
        if result['sku__sku_category']:
            data['sku_category']= result['sku__sku_category']
        if result['sku__sku_class']:
            data['sku_class']= result['sku__sku_class']
        if result['sku__sku_brand']:
            data['sku_brand']= result['sku__sku_brand']
        if result['sku__hsn_code']:
            data['hsn_code']= result['sku__hsn_code']
        if pr_supplier_id:
            data['supplier_id'] =pr_supplier_id
        if pr_supplier_name:
            data['supplier_name'] = pr_supplier_name
        if pr_supplier_gst:
            data['supplier_gst_number'] = pr_supplier_gst
        if pr_supplier_state:
            data['supplier_state'] = pr_supplier_state
        if pr_supplier_country:
            data['supplier_country'] = pr_supplier_country
        if result['sgst_tax']:
            data['sgst_tax']= result['sgst_tax']
        if result['cgst_tax']:
            data['cgst_tax']= result['cgst_tax']
        if result['igst_tax']:
            data['igst_tax']= result['igst_tax']
        if result['cess_tax']:
            data['cess_tax']= result['cess_tax']
        if result['price']:
            data['price']= result['price']
        if result['quantity']:
            data['pquantity']= result['quantity']
            data['base_quantity'] =  result['quantity']* pcf
        if result['measurement_unit']:
            data['puom']= result['measurement_unit']
        if result['pending_pr__priority_type']:
            data['priority_type']= result['pending_pr__priority_type']
        if result['sku__hsn_code']:
            data['hsn_code']= result['sku__hsn_code']
        data['base_uom'] = uom_dict['base_uom']
        data['pcf'] = pcf
        if next_approver_mail:
            data['pending_at'] = next_approver_mail
        if final_status.title():
            data['final_status'] = final_status.title()
        if result['pending_pr__delivery_date']:
            data['delivery_date'] = result['pending_pr__delivery_date']
        #final_list.append(data)
        purchase_request_date = data
    #for purchase_request_date in final_list:
	try:
	    print(AnalyticsPurchaseRequest.objects.using('mhl_analytics').update_or_create(full_pr_number= purchase_request_date['full_pr_number'], pr_date= purchase_request_date['pr_date'], sku_code= purchase_request_date['sku_code'],price= purchase_request_date['price'], pquantity = purchase_request_date['pquantity'],defaults= purchase_request_date))
	except Exception as err:
	    print(".....", str(err))
	    print(purchase_request_date)
        count+= 1
        print("Pending PR Total Count = ",len(results), " and completed = ", count)



def get_po_detail_report_data(search_params, user, sub_user):
    po_list= []
    from rest_api.views.inbound import findLastLevelToApprove
    from rest_api.views.common import get_misc_value, get_admin, get_uom_with_multi_skus, get_sku_wise_pr_amount_and_quantity
    from rest_api.views.common import get_sku_master, get_local_date, get_filtered_params, \
        get_warehouse_user_from_sub_user, get_plant_and_department, get_all_department_data, get_related_users_filters, check_and_get_plants_depts_wo_request
    now =  datetime.datetime.now()
#    last_year = now + dateutil.relativedelta.relativedelta(years=-1)
    last_hour = now + dateutil.relativedelta.relativedelta(hours=-275)
#    last_month = now + dateutil.relativedelta.relativedelta(months=-2)
    search_parameters = {'purchase_type': 'PO'}
    from_date = search_params.get("from_date", {})
    if from_date:
        search_parameters.update({"pending_po__updation_date__gte": from_date})
    #search_parameters.update(search_params)
    values_list = ['pending_po__requested_user', 'pending_po__requested_user__first_name', 'pending_po__po_number',
                   'pending_po__requested_user__username', 'pending_po__full_po_number', 'pending_po__final_status',
                   'pending_po__pending_level', 'pending_po__remarks', 'pending_po__delivery_date', 'pending_po__wh_user','pending_po__wh_user__first_name','pending_po__wh_user__userprofile__zone',
                   'pending_po__sku_category', 'pending_po__creation_date',
                   'pending_po__product_category', 'pending_po_id', 'measurement_unit',
                   'pending_po__prefix','sku__sku_code', 'sku__sku_desc',
                   'sku__sku_category', 'sku__sku_class', 'sku__sku_brand','sku__style_name', 'sku__price',
                   'cgst_tax', 'sgst_tax', 'igst_tax', 'cess_tax',
                   'pending_po__supplier__supplier_id', 'pending_po__supplier__name',
                   'pending_po__supplier__country','pending_po__supplier__state','pending_po__supplier__tin_number',
                   'pending_po__supplier_payment__payment_description',
                   'pending_po__pending_prs__full_pr_number','pending_po__pending_prs__creation_date',
                   'sku__mrp', 'sku__sub_category', 'sku__sku_group','quantity', 'price', 'sku__hsn_code', 'pending_po_id']
    search_parameters1 = {}
    for spk, spv in search_parameters.items():
        if 'pending_po__' in spk:
            search_parameters1[spk.replace('pending_po__', '')] = spv
    if 'purchase_type' in search_parameters1:
        del search_parameters1['purchase_type']
    pl_main = PendingPR.objects.filter(**search_parameters1)
    results = PendingLineItems.objects.filter(**search_parameters).values(*values_list).distinct()
    sku_codes_list = []
    po_numbers_list= []
    for each_rw in  results:
        sku_codes_list.append(each_rw['sku__sku_code'])
        po_numbers_list.append(each_rw['pending_po__full_po_number'])
    skus_uom_dict = get_uom_with_multi_skus(user, sku_codes_list, uom_type='purchase')
    count = 0
    print("Pending PO Count", len(results))
    for result in results:
        plant_code, plant_name, plant_zone , department, department_code = '', '', '', '', ''
        req_user = User.objects.filter(id = result['pending_po__wh_user'])[0]
        if req_user:
            req_user= req_user
            if req_user.userprofile.warehouse_type.lower() == 'dept':
                department= req_user.first_name
                department_code = req_user.userprofile.stockone_code
                admin_user = get_admin(req_user)
                plant_code = admin_user.userprofile.stockone_code
                plant_name = admin_user.userprofile.user.first_name
                plant_zone = admin_user.userprofile.zone
            else:
                plant_code = req_user.userprofile.stockone_code
                plant_name = req_user.first_name
                plant_zone = req_user.userprofile.zone
        pending_approval = PurchaseApprovals.objects.filter(
            pending_po__full_po_number=result['pending_po__full_po_number'],
            status='', pending_po__final_status='pending')
        next_approver_mail, pending_level, approval_type = [''] * 3
        if pending_approval.exists():
            pending_approval = pending_approval[0]
            next_approver_mail = pending_approval.validated_by
            pending_level = pending_approval.level
            approval_type = pending_approval.approval_type
        final_status = result['pending_po__final_status']
        data = {"price":0, "pquantity": 0, "po_date": ""}
        uom_dict = skus_uom_dict.get(result['sku__sku_code'])
        pcf = uom_dict.get('sku_conversion', 1)
        if result["pending_po__pending_prs__full_pr_number"]:
            data["full_pr_number"] = result["pending_po__pending_prs__full_pr_number"]
        if result['pending_po__pending_prs__creation_date']:
            data["pr_date"] = result["pending_po__pending_prs__creation_date"].isoformat()
        if result['pending_po__full_po_number']:
            data['full_po_number'] = result['pending_po__full_po_number']
        if plant_code:
            data['plant_code'] = plant_code
        if result['pending_po__creation_date']:
            data['po_date'] =  result['pending_po__creation_date'].isoformat()
            data['po_raised_date'] = data['po_date']
        if 'pending_po__requested_user__first_name' in result and result['pending_po__requested_user__first_name']:
            data['requested_user'] = result['pending_po__requested_user__first_name']
        if 'pending_po__wh_user__first_name' in result and result['pending_po__wh_user__first_name']:
            data['wh_user'] = result['pending_po__wh_user__first_name']
        if 'pending_po__wh_user__userprofile__zone' in result and result['pending_po__wh_user__userprofile__zone']:
            data['zone'] = result['pending_po__wh_user__userprofile__zone']
        if plant_name:
            data['plant_name']= plant_name
        if department:
            data['department_name'] = department
        if department_code:
            data['department_code'] = department_code
        if result['sku__sku_code']:
            data['sku_code'] = result['sku__sku_code']
        if result['sku__sku_desc']:
            data['sku_desc'] = result['sku__sku_desc']
        if result['sku__sku_category']:
            data['sku_category']= result['sku__sku_category']
        if result['sku__sku_class']:
            data['sku_class']= result['sku__sku_class']
        if result['sku__sku_brand']:
            data['sku_brand']= result['sku__sku_brand']
        if result['sku__hsn_code']:
            data['hsn_code']= result['sku__hsn_code']
        if result['pending_po__supplier__supplier_id']:
            data['supplier_id'] =result['pending_po__supplier__supplier_id']
        if result['pending_po__supplier__name']:
            data['supplier_name'] = result['pending_po__supplier__name']
        if result['pending_po__supplier__tin_number']:
            data['supplier_gst_number'] = result['pending_po__supplier__tin_number']
        if result['pending_po__supplier__state']:
            data['supplier_state'] = result['pending_po__supplier__state']
        if result['pending_po__supplier__country']:
            data['supplier_country'] = result['pending_po__supplier__country']
        if result['pending_po__supplier_payment__payment_description']:
            data['payment_terms'] = result['pending_po__supplier_payment__payment_description']
        if result['sgst_tax']:
            data['sgst_tax']= result['sgst_tax']
        if result['cgst_tax']:
            data['cgst_tax']= result['cgst_tax']
        if result['igst_tax']:
            data['igst_tax']= result['igst_tax']
        if result['cess_tax']:
            data['cess_tax']= result['cess_tax']
        if result['price']:
            data['price']= result['price']
        if result['quantity']:
            data['pquantity']= result['quantity']
            data['base_quantity'] =  result['quantity'] * pcf
        if result['measurement_unit']:
            data['puom']= result['measurement_unit']
        # if result['pending_po__pending_prs__priority_type']:
        #     data['priority_type']= result['pending_po__pending_prs__priority_type']
        if result['sku__hsn_code']:
            data['hsn_code']= result['sku__hsn_code']
        data['base_uom'] = uom_dict['base_uom']
        data['pcf'] = pcf
        if next_approver_mail:
            data['pending_at'] = next_approver_mail
        if final_status.title():
            data['final_status'] = final_status.title()
        if result['pending_po__delivery_date']:
            data['delivery_date'] = result['pending_po__delivery_date'].isoformat()
        po_list.append(data)
        purchase_order_data = data
    #for purchase_order_data in po_list:
        try:
            full_pr_number = purchase_order_data.get("full_pr_number", "")
            pr_date = purchase_order_data.get("pr_date", "")
            if 'full_pr_number' in purchase_order_data:
                del purchase_order_data["full_pr_number"]
            if 'pr_date' in purchase_order_data:
                del purchase_order_data["pr_date"]
            if 'priority_type' in  purchase_order_data:
                del purchase_order_data["priority_type"]
            if "po_date" in purchase_order_data and not purchase_order_data.get("po_date", None):
            	del purchase_order_data["po_date"]
            po_object= AnalyticsPurchaseOrder.objects.using('mhl_analytics').update_or_create(
                full_po_number= purchase_order_data['full_po_number'],
                sku_code= purchase_order_data['sku_code'],
                price= purchase_order_data['price'],
                pquantity = purchase_order_data['pquantity'],
                defaults= purchase_order_data)
            pr_objects = AnalyticsPurchaseRequest.objects.using('mhl_analytics').filter(
               full_pr_number= full_pr_number,
               sku_code= purchase_order_data['sku_code'],
               pquantity = purchase_order_data['pquantity'],
               pr_date= pr_date,
               )
            #.exclude(purchase_orders__full_po_number=purchase_order_data['full_po_number'],
            #       purchase_orders__po_raised_date= purchase_order_data['po_raised_date'],
            #       purchase_orders__sku_code= purchase_order_data['sku_code'],
            #       purchase_orders__pquantity = purchase_order_data['pquantity'],
            #       purchase_orders__price= purchase_order_data['price'],
            #   )
            if pr_objects.exists():
            	for pr_obj in pr_objects:
            		pr_obj.purchase_orders.add(po_object[0])
        except Exception as err:
            print(".....", str(err))
            print(purchase_order_data)
            continue
    print("Pending PO completed")
    #last_hour = now + dateutil.relativedelta.relativedelta(hours=-275)
    #search_parameters = {'updation_date__gte': last_hour, "open_po_id__isnull":False}
    search_parameters = {"open_po_id__isnull":False}
    if from_date:
        search_parameters.update({'updation_date__gte': from_date})
    po_values_list = ["po_number", "creation_date", "received_quantity",
     "status", "id",
     "expected_date", "currency", "currency_internal_id", "currency_rate",
     "open_po__supplier__supplier_id", "open_po__supplier__name",
     "open_po__supplier__country", "open_po__supplier__state",
     "open_po__supplier__tin_number",  "open_po__sku__sku_code",
     "open_po__sku__sku_desc", "open_po__sku__sku_category",
     "open_po__sku__sku_class", "open_po__sku__sku_brand", "open_po__sku__user",
     "open_po__cgst_tax", "open_po__sgst_tax", "open_po__igst_tax", "open_po__cess_tax",
     "open_po__order_quantity", "open_po__price", "open_po__sku__hsn_code"
     ]
    exclude_perms= {"status__in": ["deleted", "stock-transfer"]}
    po_results = PurchaseOrder.objects.filter(**search_parameters).exclude(**exclude_perms).values(*po_values_list)
    po_sku_codes_list = []
    # po_numbers_list= []
    for each_row in  po_results:
        po_sku_codes_list.append(each_row['open_po__sku__sku_code'])
        # po_numbers_list.append(each_rw['pending_po__full_po_number'])
    skus_uom_dict = get_uom_with_multi_skus(user, po_sku_codes_list, uom_type='purchase')
    count = 0
    print(len(po_results))
    new_po_list = []
    # po_obj_result= PurchaseOrder.objects.filter().values( "po_number", "open_po__sku__sku_code", "open_po__order_quantity", "open_po__price").distinct().annotate(count=Count('open_po__order_quantity'))
    # duplicate_po_sku_codes= {}
    # for each_row in po_obj_result:
    #     if each_row["count"]>1:
    #         if each_row["po_number"] in duplicate_po_sku_codes:
    #             duplicate_po_sku_codes[each_row["po_number"]].append(each_row)
    #         else:
    #             duplicate_po_sku_codes[each_row["po_number"]] = [each_row]
    # exclude_po_numbers= duplicate_po_sku_codes.keys()
    for result in po_results:
        # if result["po_number"] in exclude_po_numbers: continue
        plant_code, plant_name, plant_zone , department, department_code = '', '', '', '', ''
        req_user = User.objects.filter(id = result['open_po__sku__user'])[0]
        if req_user:
            if req_user.userprofile.warehouse_type.lower() == 'dept':
                department= req_user.first_name
                department_code = req_user.userprofile.stockone_code
                admin_user = get_admin(req_user)
                plant_code = admin_user.userprofile.stockone_code
                plant_name = admin_user.userprofile.user.first_name
                plant_zone = admin_user.userprofile.zone
            else:
                plant_code = req_user.userprofile.stockone_code
                plant_name = req_user.first_name
                plant_zone = req_user.userprofile.zone
        next_approver_mail, pending_level, approval_type = [''] * 3
        data = {"price":0, "pquantity": 0, "po_date": "", "full_pr_number": "", "pr_date": ""}
        uom_dict = skus_uom_dict.get(result['open_po__sku__sku_code'])
        pcf = uom_dict.get('sku_conversion', 1)
        # if result["pending_po__pending_prs__full_pr_number"]:
        #     data["full_pr_number"] = result["pending_po__pending_prs__full_pr_number"]
        # if result['pending_po__pending_prs__creation_date']:
        #     data["pr_date"] = result["pending_po__pending_prs__creation_date"]
        if result['po_number']:
            data['full_po_number'] = result['po_number']
        if plant_code:
            data['plant_code'] = plant_code
        if result['creation_date']:
            data['po_date'] =  result['creation_date'].isoformat()
        if result["received_quantity"]:
            data["received_quantity"] = result["received_quantity"]
        # if 'pending_po__requested_user__first_name' in result and result['pending_po__requested_user__first_name']:
        #     data['requested_user'] = result['pending_po__requested_user__first_name']
        # if 'pending_po__wh_user__first_name' in result and result['pending_po__wh_user__first_name']:
        #     data['wh_user'] = result['pending_po__wh_user__first_name']
        if 'pending_po__wh_user__userprofile__zone' in result and result['pending_po__wh_user__userprofile__zone']:
            data['zone'] = result['pending_po__wh_user__userprofile__zone']
        if 'id':
        	data['po_id'] = result['id']
        if plant_name:
            data['plant_name']= plant_name
        if department:
            data['department_name'] = department
        if department_code:
            data['department_code'] = department_code
        if result['open_po__sku__sku_code']:
            data['sku_code'] = result['open_po__sku__sku_code']
        if result['open_po__sku__sku_desc']:
            data['sku_desc'] = result['open_po__sku__sku_desc']
        if result['open_po__sku__sku_category']:
            data['sku_category']= result['open_po__sku__sku_category']
        if result['open_po__sku__sku_class']:
            data['sku_class']= result['open_po__sku__sku_class']
        if result['open_po__sku__sku_brand']:
            data['sku_brand']= result['open_po__sku__sku_brand']
        if result['open_po__sku__hsn_code']:
            data['hsn_code']= result['open_po__sku__hsn_code']
        if result['open_po__supplier__supplier_id']:
            data['supplier_id'] =result['open_po__supplier__supplier_id']
        if result['open_po__supplier__name']:
            data['supplier_name'] = result['open_po__supplier__name']
        if result['open_po__supplier__tin_number']:
            data['supplier_gst_number'] = result['open_po__supplier__tin_number']
        if result['open_po__supplier__state']:
            data['supplier_state'] = result['open_po__supplier__state']
        if result['open_po__supplier__country']:
            data['supplier_country'] = result['open_po__supplier__country']
        if result['open_po__sgst_tax']:
            data['sgst_tax']= result['open_po__sgst_tax']
        if result['open_po__cgst_tax']:
            data['cgst_tax']= result['open_po__cgst_tax']
        if result['open_po__igst_tax']:
            data['igst_tax']= result['open_po__igst_tax']
        if result['open_po__cess_tax']:
            data['cess_tax']= result['open_po__cess_tax']
        if result['open_po__price']:
            data['price']= result['open_po__price']
        if result['open_po__order_quantity']:
            data['pquantity']= result['open_po__order_quantity']
            data['base_quantity'] =  result['open_po__order_quantity'] * pcf
        if uom_dict['measurement_unit']:
            data['puom']= uom_dict['measurement_unit']
        if result["status"]:
            data['po_status']= result['status']
        # if result['pending_po__pending_prs__priority_type']:
        #     data['priority_type']= result['pending_po__pending_prs__priority_type']
        data['base_uom'] = uom_dict['base_uom']
        data['pcf'] = pcf
        # if next_approver_mail:
        #     data['pending_at'] = next_approver_mail
        # if final_status:
        #     data['final_status'] = final_status.title()
        if result['expected_date']:
            data['delivery_date'] = result['expected_date'].isoformat()
        #new_po_list.append(data)
        purchase_order_data =data
    #for purchase_order_data in new_po_list:
        try:
            full_pr_number = purchase_order_data.get("full_pr_number", "")
            pr_date = purchase_order_data.get("pr_date", "")
            if 'full_pr_number' in purchase_order_data:
                del purchase_order_data["full_pr_number"]
            if 'pr_date' in purchase_order_data:
                del purchase_order_data["pr_date"]
            if 'priority_type' in  purchase_order_data:
                del purchase_order_data["priority_type"]
            po_object= AnalyticsPurchaseOrder.objects.using('mhl_analytics').update_or_create(
                full_po_number= purchase_order_data['full_po_number'],
                sku_code= purchase_order_data['sku_code'],
                price= purchase_order_data['price'],
                pquantity = purchase_order_data['pquantity'],
                defaults= purchase_order_data)
            print(po_object)
        except Exception as err:
	    po_object= AnalyticsPurchaseOrder.objects.using('mhl_analytics').update_or_create(
                po_id= purchase_order_data['po_id'],
                full_po_number= purchase_order_data['full_po_number'],
                sku_code= purchase_order_data['sku_code'],
                price= purchase_order_data['price'],
                pquantity = purchase_order_data['pquantity'],
                defaults= purchase_order_data)
            print(".....", str(err))
            print(purchase_order_data)
            continue











def get_grn_detail_report_data(search_params, user, sub_user):
    new_grn_list= []
    from rest_api.views.inbound import findLastLevelToApprove
    from rest_api.views.common import get_misc_value, get_admin, get_uom_with_multi_skus, get_sku_wise_pr_amount_and_quantity
    from rest_api.views.common import get_sku_master, get_local_date, get_filtered_params, \
        get_warehouse_user_from_sub_user, get_plant_and_department, get_all_department_data, get_related_users_filters, check_and_get_plants_depts_wo_request
    now =  datetime.datetime.now()
#    last_year = now + dateutil.relativedelta.relativedelta(years=-1)
    last_month = now + dateutil.relativedelta.relativedelta(months=-1)
    # last_hour = now + dateutil.relativedelta.relativedelta(hours=-275)
    search_parameters = {"purchase_order__open_po_id__isnull":False}
    from_date = search_params.get("from_date", {})
    if from_date:
        search_parameters.update({'updation_date__gte': from_date})
    grn_values_list = ["purchase_order__po_number", "purchase_order__creation_date",
     "purchase_order__open_po__supplier__supplier_id", "purchase_order__open_po__supplier__name",
     "purchase_order__open_po__supplier__country", "purchase_order__open_po__supplier__state",
     "purchase_order__open_po__supplier__tin_number",  "purchase_order__open_po__sku__sku_code",
     "purchase_order__open_po__sku__sku_desc", "purchase_order__open_po__sku__sku_category",
     "purchase_order__open_po__sku__sku_class", "purchase_order__open_po__sku__sku_brand", "purchase_order__open_po__sku__user",
     "purchase_order__open_po__cgst_tax", 
     "purchase_order__open_po__sgst_tax", "purchase_order__open_po__igst_tax", 
     "purchase_order__open_po__cess_tax", "purchase_order__open_po__sku__hsn_code",
     "purchase_order__id",

     'grn_number','id','creation_date', "price", "quantity", 'remarks',  'invoice_number','invoice_date',
     "challan_number", 'challan_date', 'discount_percent', 'round_off_total', 'tcs_value',
     "overall_discount", "invoice_value", "invoice_quantity", "credit_status", "credit_type", "status",
     'batch_detail__batch_no', 'batch_detail__pquantity', 'batch_detail__pcf', 'batch_detail__puom', 
     'batch_detail__expiry_date', 'batch_detail__manufactured_date' , 'batch_detail__mrp'
     ]
    exclude_perms= {"purchase_order__status__in": ["deleted", "stock-transfer"]}
    grn_results = SellerPOSummary.objects.filter(**search_parameters).exclude(**exclude_perms).values(*grn_values_list)
    grn_sku_codes_list = []
    # po_numbers_list= []
    for each_row in  grn_results:
        grn_sku_codes_list.append(each_row['purchase_order__open_po__sku__sku_code'])
        # po_numbers_list.append(each_rw['pending_po__full_po_number'])
    skus_uom_dict = get_uom_with_multi_skus(user, grn_sku_codes_list, uom_type='purchase')
    count = 0
    print("GRN Total count = ",len(grn_results))
    for result in grn_results:
        # if result["po_number"] in exclude_po_numbers: continue
        plant_code, plant_name, plant_zone , department, department_code = '', '', '', '', ''
        req_user = User.objects.filter(id = result['purchase_order__open_po__sku__user'])[0]
        if req_user:
            if req_user.userprofile.warehouse_type.lower() == 'dept':
                department= req_user.first_name
                department_code = req_user.userprofile.stockone_code
                admin_user = get_admin(req_user)
                plant_code = admin_user.userprofile.stockone_code
                plant_name = admin_user.userprofile.user.first_name
                plant_zone = admin_user.userprofile.zone
            else:
                plant_code = req_user.userprofile.stockone_code
                plant_name = req_user.first_name
                plant_zone = req_user.userprofile.zone
        next_approver_mail, pending_level, approval_type = [''] * 3
        data = {"price":0, "pquantity": 0}
        uom_dict = skus_uom_dict.get(result['purchase_order__open_po__sku__sku_code'])
        pcf= result.get("batch_detail__pcf", None)
        if not pcf:
        	pcf = uom_dict.get('sku_conversion', 1)
        # if result["pending_po__pending_prs__full_pr_number"]:
        #     data["full_pr_number"] = result["pending_po__pending_prs__full_pr_number"]
        # if result['pending_po__pending_prs__creation_date']:
        #     data["pr_date"] = result["pending_po__pending_prs__creation_date"]
        if result['purchase_order__po_number']:
            data['full_po_number'] = result['purchase_order__po_number']
        if result["grn_number"]:
        	data['grn_number'] = result['grn_number']
        if plant_code:
            data['plant_code'] = plant_code
        if result['creation_date']:
            data['grn_date'] =  result['creation_date'].isoformat()
        # if result["received_quantity"]:
        #     data["received_quantity"] = result["received_quantity"]
        # if 'pending_po__requested_user__first_name' in result and result['pending_po__requested_user__first_name']:
        #     data['requested_user'] = result['pending_po__requested_user__first_name']
        # if 'pending_po__wh_user__first_name' in result and result['pending_po__wh_user__first_name']:
        #     data['wh_user'] = result['pending_po__wh_user__first_name']
        if plant_zone:
            data['zone'] = plant_zone
        if result['id']:
            data["grn_id"] = result["id"]
        if result['purchase_order__id']:
            data['po_id'] = result['purchase_order__id']
        if plant_name:
            data['plant_name']= plant_name
        if department:
            data['department_name'] = department
        if department_code:
            data['department_code'] = department_code
        if result['purchase_order__open_po__sku__sku_code']:
            data['sku_code'] = result['purchase_order__open_po__sku__sku_code']
        if result['purchase_order__open_po__sku__sku_desc']:
            data['sku_desc'] = result['purchase_order__open_po__sku__sku_desc']
        if result['purchase_order__open_po__sku__sku_category']:
            data['sku_category']= result['purchase_order__open_po__sku__sku_category']
        if result['purchase_order__open_po__sku__sku_class']:
            data['sku_class']= result['purchase_order__open_po__sku__sku_class']
        if result['purchase_order__open_po__sku__sku_brand']:
            data['sku_brand']= result['purchase_order__open_po__sku__sku_brand']
        if result['purchase_order__open_po__sku__hsn_code']:
            data['hsn_code']= result['purchase_order__open_po__sku__hsn_code']
        if result['purchase_order__open_po__supplier__supplier_id']:
            data['supplier_id'] =result['purchase_order__open_po__supplier__supplier_id']
        if result['purchase_order__open_po__supplier__name']:
            data['supplier_name'] = result['purchase_order__open_po__supplier__name']
        if result['purchase_order__open_po__supplier__tin_number']:
            data['supplier_gst_number'] = result['purchase_order__open_po__supplier__tin_number']
        if result['purchase_order__open_po__supplier__state']:
            data['supplier_state'] = result['purchase_order__open_po__supplier__state']
        if result['purchase_order__open_po__supplier__country']:
            data['supplier_country'] = result['purchase_order__open_po__supplier__country']
        if result['purchase_order__open_po__sgst_tax']:
            data['sgst_tax']= result['purchase_order__open_po__sgst_tax']
        if result['purchase_order__open_po__cgst_tax']:
            data['cgst_tax']= result['purchase_order__open_po__cgst_tax']
        if result['purchase_order__open_po__igst_tax']:
            data['igst_tax']= result['purchase_order__open_po__igst_tax']
        if result['purchase_order__open_po__cess_tax']:
            data['cess_tax']= result['purchase_order__open_po__cess_tax']
        if result['price']:
            data['price']= result['price']
        if result['quantity']:
            data['pquantity']= result['quantity']
            data['base_quantity'] =  result['quantity'] * pcf
        if uom_dict['measurement_unit']:
            data['puom']= uom_dict['measurement_unit']
        data['status']= result["status"]
        if result["tcs_value"]:
            data["tcs_value"]= result["tcs_value"]
        if result["remarks"]:
            data["remarks"]= result["remarks"]
        if result["challan_number"]:
            data["challan_number"]= result["challan_number"]
        if result["challan_date"]:
            data["challan_date"]= result["challan_date"].isoformat()
        if result["discount_percent"]:
            data["discount_percent"]= result["discount_percent"]
        if result["round_off_total"]:
            data["round_off_total"]= result["round_off_total"]
        if result["invoice_value"]:
            data["invoice_value"]= result["invoice_value"]
        if result["invoice_date"]:
            data["invoice_date"]= result["invoice_date"].isoformat()
        if result["invoice_number"]:
            data["invoice_number"]= result["invoice_number"]
        if result["invoice_quantity"]:
            data["invoice_quantity"]= result["invoice_quantity"]
        data["credit_status"]=  result["credit_status"]
        if result["batch_detail__mrp"]:
            data["mrp"]= result["batch_detail__mrp"]
        if result["batch_detail__manufactured_date"]:
            data["manufactured_date"]= result["batch_detail__manufactured_date"].isoformat()
        if result["batch_detail__expiry_date"]:
            data["expiry_date"]= result["batch_detail__expiry_date"].isoformat()
        if result["batch_detail__batch_no"]:
            data["batch_no"]= result["batch_detail__batch_no"]
        # if result['pending_po__pending_prs__priority_type']:
        #     data['priority_type']= result['pending_po__pending_prs__priority_type']
        data['base_uom'] = uom_dict['base_uom']
        data['pcf'] = pcf
        version_obj = Version.objects.using('reversion').get_for_object(SellerPOSummary.objects.get(id=result["id"])).\
                                                    filter(revision__comment='generate_grn')
        if version_obj.exists():
       	    data['grn_user'] = version_obj.order_by('-revision__date_created')[0].revision.user.username
        #new_grn_list.append(data)
        grn_data = data
    #for grn_data in new_grn_list:
        try:
            full_po_number = grn_data.get("full_po_number", "")
            po_id = grn_data.get("po_id", "")
            if 'full_po_number' in grn_data:
                del grn_data["full_po_number"]
            if 'po_id' in grn_data:
                del grn_data["po_id"]
            if 'priority_type' in  grn_data:
                del grn_data["priority_type"]
            grn_obj= AnalyticsGRN.objects.using('mhl_analytics').update_or_create(grn_id= grn_data["grn_id"], grn_number= grn_data['grn_number'],sku_code= grn_data['sku_code'], price= grn_data['price'], pquantity = grn_data['pquantity'], defaults= grn_data)
            print(grn_obj)
            AnalyticsPurchaseOrder.objects.using('mhl_analytics').filter(
                full_po_number= full_po_number,
                po_id = po_id,
                ).update(analytics_grn_id= grn_obj[0].id)
        except Exception as err:
            print(".....\n", str(err))
            print(grn_data)
        count+=1
        print("GRN total_count= ", len(grn_results), " completed = ",count)
