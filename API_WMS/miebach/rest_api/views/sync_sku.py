from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db.models import Q, F
from django.contrib.auth import authenticate
from django.contrib import auth
from miebach_admin.models import *
import datetime
from utils import *
log = init_logger('logs/sync_sku.log')

def insert_skus(user_id):
    """ This function syncs all sku among the connected Users for the first time"""
    st_time = datetime.datetime.now()
    log.info("first time sync process starting now")

    #user_id = request.user.id
    all_users = get_related_users(user_id)

    all_skus = get_all_skus(all_users)

    create_sku(all_skus, all_users)

    end_time = datetime.datetime.now()
    duration = end_time - st_time
    log.info("process completed")
    log.info("total time -- %s" %(duration))
    return 'Success'

def update_skus(user_id, sku_codes):
    """ Whenever new SKU is added it needed to update in all related warehouses """

    all_users = get_related_users(user_id)
    new_skus = SKUMaster.objects.filter(sku_code__in = sku_codes)
    create_sku(new_skus, all_users)
    return "Success"


def get_related_users(user_id):
    """ this function generates all users related to a user """
    all_users  = []
    admin_user = UserGroups.objects.filter(admin_user_id = user_id)

    if not admin_user:
        admin_user = UserGroups.objects.filter(user_id = user_id)[0].admin_user_id
    else:
        admin_user = user_id

    all_users.append(admin_user)
    all_normal_user = UserGroups.objects.filter(admin_user_id = admin_user).values_list('user_id', flat=True)
    all_users.extend(all_normal_user)

    log.info("all users %s" % all_users)
    return all_users

def get_all_skus(all_users):
    """ this function gates all skus related to the users """
    all_skus = []
    for user in all_users:
        all_skus_user = SKUMaster.objects.filter(user = user)

        all_skus.extend(all_skus_user)

    return all_skus

def create_sku(all_skus, all_users):
    """ creating SKU for other linked users """
    for user in all_users:
        for sku in all_skus:
            p, created = SKUMaster.objects.get_or_create(user = user, sku_code = sku.sku_code, wms_code = sku.wms_code,
                defaults={'sku_desc' : sku.sku_desc, 'sku_group' : sku.sku_group, 'sku_type' : sku.sku_type,
                'sku_category' : sku.sku_category, 'sku_class' : sku.sku_class, 'sku_brand' : sku.sku_brand,
                'style_name' : sku.style_name, 'sku_size' : sku.sku_size, 'sku_size' : sku.sku_size,
                'product_group' : sku.product_group, 'zone' : sku.zone, 'threshold_quantity' : sku.threshold_quantity,
                'online_percentage' : sku.online_percentage, 'discount_percentage' : sku.discount_percentage,
                'price' : sku.price, 'mrp' : sku.mrp, 'image_url' : sku.image_url, 'qc_check' : sku.qc_check,
                'sequence' : sku.sequence, 'status' : sku.status, 'relation_type' : sku.relation_type,
                'measurement_type' : sku.measurement_type, 'sale_through' : sku.sale_through,
                'creation_date' : datetime.datetime.now().date(), 'updation_date' : datetime.datetime.now().date()})

    return "success"





