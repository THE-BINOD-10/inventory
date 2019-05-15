from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db.models import Q, F
from django.contrib.auth import authenticate
from django.contrib import auth
import datetime
import copy
from miebach_admin.models import *
from utils import *
from dump_user_images import *

log = init_logger('logs/sync_sku.log')


def insert_skus(user_id):
    """ This function syncs all sku among the connected Users for the first time"""
    st_time = datetime.datetime.now()
    log.info("first time sync process starting now")

    # user_id = request.user.id
    all_users = get_related_users(user_id)

    all_skus = get_all_skus(all_users)

    create_update_sku(all_skus, all_users)

    end_time = datetime.datetime.now()
    duration = end_time - st_time
    log.info("process completed")
    log.info("total time -- %s" % (duration))
    return 'Success'


def update_skus(user_id, sku_codes):
    """ Whenever new SKU is added it needed to update in all related warehouses """

    all_users = get_related_users(user_id)
    new_skus = SKUMaster.objects.filter(sku_code__in=sku_codes)
    create_update_sku(new_skus, all_users)
    return "Success"


def get_related_users(user_id):
    """ this function generates all users related to a user """
    all_users = []
    admin_user = UserGroups.objects.filter(admin_user_id=user_id)

    if not admin_user:
        admin_user_obj = UserGroups.objects.filter(user_id=user_id)
        if admin_user_obj:
            admin_user = admin_user_obj[0].admin_user_id
        else:
            admin_user = ''
    else:
        admin_user = user_id

    if admin_user:
        all_users.append(admin_user)
        all_normal_user = UserGroups.objects.filter(admin_user_id=admin_user).values_list('user_id', flat=True)
        all_users.extend(all_normal_user)

    log.info("all users %s" % all_users)
    return all_users


def get_all_skus(all_users):
    """ this function gates all skus related to the users """
    all_skus = []
    for user in all_users:
        all_skus_user = SKUMaster.objects.filter(user=user)

        all_skus.extend(all_skus_user)

    return all_skus


def create_update_sku(all_skus, all_users):
    """ creating SKU for other linked users """
    from rest_api.views.common import get_misc_value
    dump_sku_codes = []
    wh_type = ''
    if all_skus:
        user_profile = UserProfile.objects.filter(user_id=all_skus[0].user)
        if user_profile:
            wh_type = user_profile[0].warehouse_type
    for user in all_users:
        for sku in all_skus:
            if not sku or sku.user == user:
                continue
            update_sku_dict = {'sku_desc': sku.sku_desc, 'sku_group': sku.sku_group, 'sku_type': sku.sku_type,
                        'sku_category': sku.sku_category, 'sku_class': sku.sku_class, 'sku_brand': sku.sku_brand,
                        'style_name': sku.style_name, 'sku_size': sku.sku_size,
                        'product_type': sku.product_type, 'online_percentage': sku.online_percentage,
                        'mrp': sku.mrp, 'sequence': sku.sequence, 'status': sku.status,
                        'measurement_type': sku.measurement_type, 'sale_through': sku.sale_through,
                        'hsn_code': sku.hsn_code, 'youtube_url': sku.youtube_url,
                        }
            new_sku_dict = copy.deepcopy(update_sku_dict)
            new_sku_dict.update({'discount_percentage': sku.discount_percentage, 'price': sku.price,
                                 'relation_type': sku.relation_type,
                                 'creation_date': datetime.datetime.now().date(),
                                 'updation_date': datetime.datetime.now().date()})
            sku_obj, created = SKUMaster.objects.get_or_create(user=user, sku_code=sku.sku_code, wms_code=sku.wms_code,
                                                         defaults=new_sku_dict)
            if sku.sku_code not in dump_sku_codes and created:
                dump_sku_codes.append(sku.sku_code)
            price_band_flag = get_misc_value('priceband_sync', sku.user)
            if (price_band_flag == 'true' or wh_type == 'CENTRAL_ADMIN') and not created:
                sku_obj.__dict__.update(**update_sku_dict)
                print sku_obj.sku_desc, sku_obj.id
                sku_obj.save()
                if sku.sku_code not in dump_sku_codes:
                    dump_sku_codes.append(sku.sku_code)

        if dump_sku_codes and all_skus:
            dump_user_images(all_skus[0].user, user, sku_codes=dump_sku_codes)

    return "success"
