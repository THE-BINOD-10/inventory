from miebach_admin.models import *
from common import *


def get_sku_attributes(user, sku_code):
    attributes_dict = dict(
        SKUAttributes.objects.filter(sku__user=user.id, sku__wms_code=sku_code).values_list('attribute_name',
                                                                                            'attribute_value'))
    return attributes_dict


def get_previous_order(user, sku_code):
    orders_dict = list(
        OrderDetail.objects.filter(user=user.id, sku__wms_code=sku_code).order_by('-creation_date')[:3].values(
            'original_order_id', 'original_quantity', 'unit_price', 'creation_date', 'sku__wms_code'))
    for order in orders_dict:
        order['order_date'] = get_local_date(user, order['creation_date'])
        del order['creation_date']
    return orders_dict


def get_unique_customer_types(user):
    customer_types = list(CustomerMaster.objects.filter(user=user.id).values_list('customer_type', flat=True).distinct())
    return customer_types
