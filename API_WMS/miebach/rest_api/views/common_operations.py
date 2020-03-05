from miebach_admin.models import *


def get_sku_attributes(user, sku_code):
    attributes_dict = dict(
        SKUAttributes.objects.filter(sku__user=user.id, sku__wms_code=sku_code).values_list('attribute_name',
                                                                                            'attribute_value'))
    return attributes_dict
