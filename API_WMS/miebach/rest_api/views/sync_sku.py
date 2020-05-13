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
from collections import OrderedDict

log = init_logger('logs/sync_sku.log')


def insert_skus(user_id):
    """ This function syncs all sku among the connected Users for the first time"""
    from rest_api.views.common import get_related_users
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
    from rest_api.views.common import get_related_users

    all_users = get_related_users(user_id)
    new_skus = SKUMaster.objects.filter(user=user_id, sku_code__in=sku_codes)
    create_update_sku(new_skus, all_users)
    return "Success"


def get_all_skus(all_users):
    """ this function gates all skus related to the users """
    all_skus = []
    for user in all_users:
        all_skus_user = SKUMaster.objects.filter(user=user)

        all_skus.extend(all_skus_user)

    return all_skus


def create_update_sku(all_skus, all_users):
    """ creating SKU for other linked users """
    from rest_api.views.common import get_misc_value, bulk_create_in_batches, prepare_ean_bulk_data, update_sku_attributes_data
    from rest_api.views.masters import check_update_size_type
    dump_sku_codes = []
    wh_type = ''
    if all_skus:
        user_profile = UserProfile.objects.filter(user_id=all_skus[0].user)
        if user_profile:
            wh_type = user_profile[0].warehouse_type
    for user in all_users:
        exist_skus = list(SKUMaster.objects.filter(user=user).values_list('sku_code', flat=True))
        exist_skus = map(lambda x:str(x).upper(), exist_skus)
        new_sku_objs = []
        new_sku_eans = OrderedDict()
        new_sku_attrs = OrderedDict()
        new_sku_size_types = OrderedDict()
        create_sku_attrs, sku_attr_mapping = [], []
        exist_sku_eans = dict(SKUMaster.objects.filter(user=user, status=1).exclude(ean_number='').\
                              only('ean_number', 'sku_code').values_list('ean_number', 'sku_code'))
        exist_ean_list = dict(EANNumbers.objects.filter(sku__user=user, sku__status=1).\
                              only('ean_number', 'sku__sku_code').values_list('ean_number', 'sku__sku_code'))
        new_ean_objs = []
        for sku in all_skus:
            if not sku or sku.user == user:
                continue
            size_type = ''
            sku_size_type = sku.skufields_set.filter(field_type='size_type').only('field_value')
            if sku_size_type:
                size_type = sku_size_type[0].field_value
            update_sku_dict = {'sku_desc': sku.sku_desc, 'sku_group': sku.sku_group, 'sku_type': sku.sku_type,
                        'sku_category': sku.sku_category, 'sku_class': sku.sku_class, 'sku_brand': sku.sku_brand,
                        'style_name': sku.style_name, 'sku_size': sku.sku_size,
                        'product_type': sku.product_type, 'online_percentage': sku.online_percentage,
                        'mrp': sku.mrp, 'sequence': sku.sequence, 'status': sku.status,
                        'measurement_type': sku.measurement_type, 'sale_through': sku.sale_through,
                        'hsn_code': sku.hsn_code, 'youtube_url': sku.youtube_url,
                        }
            ean_numbers = list(sku.eannumbers_set.filter().values_list('ean_number', flat=True))
            if sku.ean_number and sku.ean_number != '0':
                ean_numbers.append(sku.ean_number)
            attr_dict = OrderedDict(sku.skuattributes_set.filter().values_list('attribute_name', 'attribute_value'))
            new_sku_dict = copy.deepcopy(update_sku_dict)
            new_sku_dict.update({'discount_percentage': sku.discount_percentage, 'price': sku.price,
                                 'relation_type': sku.relation_type,
                                 'creation_date': datetime.datetime.now().date(),
                                 'updation_date': datetime.datetime.now().date()})

            if sku.sku_code.upper() not in exist_skus:
                new_sku_dict['user'] = user
                new_sku_dict['sku_code'] = sku.sku_code
                new_sku_dict['wms_code'] = sku.wms_code
                new_sku_objs.append(SKUMaster(**new_sku_dict))
                if ean_numbers:
                    new_sku_eans[sku.sku_code] = ean_numbers
                if attr_dict:
                    new_sku_attrs[sku.sku_code] = attr_dict
                if size_type:
                    new_sku_size_types[sku.sku_code] = size_type
                exist_skus.append(sku.sku_code.upper())

            else:
                sku_obj = SKUMaster.objects.get(user=user, sku_code=sku.sku_code)
                #price_band_flag = get_misc_value('priceband_sync', sku.user)
                #if (price_band_flag == 'true' or wh_type == 'CENTRAL_ADMIN') and not created:
                sku_obj.__dict__.update(**update_sku_dict)
                sku_obj, new_ean_objs, update_sku_obj = prepare_ean_bulk_data(sku_obj, ean_numbers, exist_ean_list,
                                                                        exist_sku_eans, new_ean_objs=new_ean_objs)
                for attr_key, attr_val in attr_dict.iteritems():
                    create_sku_attrs, sku_attr_mapping = update_sku_attributes_data(sku_obj, attr_key, attr_val, is_bulk_create=True,
                                               create_sku_attrs=create_sku_attrs, sku_attr_mapping=sku_attr_mapping)
                sku_obj.save()
                if size_type:
                    check_update_size_type(sku_obj, size_type)
                if sku.sku_code not in dump_sku_codes:
                    dump_sku_codes.append(sku.sku_code)

            if sku.sku_code not in dump_sku_codes:
                dump_sku_codes.append(sku.sku_code)

        code_obj_dict = {}
        if new_sku_objs:
            bulk_create_in_batches(SKUMaster, new_sku_objs)
            for new_sku_code, new_sku_value in new_sku_eans.items():
                sku_obj = SKUMaster.objects.get(user=user, sku_code=new_sku_code)
                code_obj_dict[new_sku_code] = sku_obj
                sku_obj, new_ean_objs, update_sku_obj = prepare_ean_bulk_data(sku_obj, new_sku_value, exist_ean_list,
                                                                    exist_sku_eans, new_ean_objs=new_ean_objs)
            for new_sku_code, new_sku_attr in new_sku_attrs.items():
                if new_sku_code in code_obj_dict.keys():
                    sku_obj = code_obj_dict[new_sku_code]
                else:
                    sku_obj = SKUMaster.objects.get(user=user, sku_code=new_sku_code)
                for attr_key, attr_val in new_sku_attr.iteritems():
                    create_sku_attrs, sku_attr_mapping = update_sku_attributes_data(sku_obj, attr_key, attr_val, is_bulk_create=True,
                                               create_sku_attrs=create_sku_attrs, sku_attr_mapping=sku_attr_mapping)
            for new_sku_code, new_sku_size_type in new_sku_size_types.items():
                if new_sku_code in code_obj_dict.keys():
                    sku_obj = code_obj_dict[new_sku_code]
                else:
                    sku_obj = SKUMaster.objects.get(user=user, sku_code=new_sku_code)
                check_update_size_type(sku_obj, new_sku_size_type)

        if new_ean_objs:
            bulk_create_in_batches(EANNumbers, new_ean_objs)

        #Bulk Create SKU Attributes
        if create_sku_attrs:
            SKUAttributes.objects.bulk_create(create_sku_attrs)

        if dump_sku_codes and all_skus:
            dump_user_images(all_skus[0].user, user, sku_codes=dump_sku_codes)

    return "success"
