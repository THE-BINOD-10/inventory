from django import template
from miebach_admin.views import get_misc_value, get_permission

import base64, os
from django.conf import settings

register = template.Library()

@register.filter
def get_id(data, item):
    data_item = getattr(data, item)
    if not data_item:
        data_item = ''
    return data_item

@register.filter
def get_value(data, item):
    return data.get(item, '')

@register.filter
def get_count(data, item):
    return data.get(item, 0)

@register.filter
def get_variable_type(item):
    if isinstance(item, list):
        item_type = 'list'
    else:
        item_type = 'string'
    return item_type

@register.filter
def is_quality_check(user):
    return get_permission(user, 'add_qualitycheck')

@register.filter
def is_sales_returns(user):
    return get_permission(user, 'add_orderreturns')

@register.filter
def is_online_offline(user):
    return get_permission(user, 'add_skustock')

@register.filter
def is_shipment_info(user):
    return get_permission(user, 'add_shipmentinfo')

@register.filter
def is_pullto_locate(user):
    return user.groups.filter(name='Pull to locate').exists()

@register.filter
def is_pallet_detail(user):
    pallet = get_misc_value('pallet_switch', user.id)
    if pallet == 'true':
        return True
    else:
        return False

@register.filter
def is_inbound(user):
    is_open = get_permission(user, 'add_openpo')
    is_po = get_permission(user, 'add_purchaseorder')
    return is_open or is_po or user.is_staff or user.is_superuser

@register.filter
def is_open_po(user):
    is_open = get_permission(user, 'add_openpo')
    return is_open or user.is_staff or user.is_superuser

@register.filter
def is_purchase_order(user):
    is_po = get_permission(user, 'add_purchaseorder')
    return is_po or user.is_staff or user.is_superuser

@register.filter
def is_po_location(user):
    is_po = get_permission(user, 'add_purchaseorder')
    return is_po or user.is_staff or user.is_superuser

@register.filter
def is_production(user):
    production = get_misc_value('production_switch', user.id)
    if production == 'true':
        return True
    else:
        return False

@register.filter
def is_pos(user):
    production = get_misc_value('pos_switch', user.id)
    if production == 'true':
        return True
    else:
        return False

@register.filter
def is_job_order(user):
    return get_permission(user, 'add_joborder') or user.is_staff or user.is_superuser

@register.filter
def is_rm_picklist(user):
    return get_permission(user, 'add_materialpicklist') or user.is_staff or user.is_superuser

@register.filter
def is_jo_putaway(user):
    is_po = get_permission(user, 'add_polocation')
    is_jo = get_permission(user, 'add_joborder')
    return is_po or is_jo or user.is_staff or user.is_superuser


@register.filter
def is_stock_detail(user):
    is_stock = get_permission(user, 'add_stockdetail')
    is_cycle = get_permission(user, 'add_cyclecount')
    return is_stock or is_cycle or user.is_staff or user.is_superuser

@register.filter
def is_cycle_count(user):
    return get_permission(user, 'add_cyclecount') or user.is_staff or user.is_superuser

@register.filter
def is_inventory(user):
    return get_permission(user, 'add_inventoryadjustment') or user.is_staff or user.is_superuser

@register.filter
def is_orderdetail(user):
    return get_permission(user, 'add_orderdetail') or user.is_staff or user.is_superuser

@register.filter
def is_picklist(user):
    return get_permission(user, 'add_picklist') or user.is_staff or user.is_superuser

@register.filter
def is_outbound(user):
    return get_permission(user, 'add_orderdetail') or user.is_staff or user.is_superuser

@register.filter
def get_image_code(image_url):
    if not os.path.exists(image_url):
        if os.path.exists(image_url.strip("/")):
            image_url = os.path.realpath('.') +  image_url
            return image_url
            with open(image_url, "rb") as image_file:
                image = base64.b64encode(image_file.read())
            return image
    return image_url

@register.filter
def get_price_code(price):
    price = int(price)
    if len(str(price)) == 2:
        return "DN-80"+str(price)
    else:
        return "DN-8"+str(price)

@register.filter
def get_size_wise_stock(data):

    quantity_list = [];
    for size in data:
        quantity_list.append(size['sku_size'] + "-" + str(int(size['physical_stock'])))
    return ", ".join(quantity_list)

@register.filter
def get_variant_total_stock(data):
    sum = 0
    for size in data:
        sum += int(size['physical_stock'])
    return sum

@register.filter
def get_page_break(count):
    if (count+1)%10 == 0:
        return True
    else:
        return False

@register.filter
def get_page_break_8(count):
    if (count+1)%8 == 0:
        return True
    else:
        return False

@register.filter
def get_header_status(count):
    if (count)%10 == 0:
        return True
    else:
        return False

@register.filter
def get_header_status_8(count):
    if (count)%8 == 0:
        return True
    else:
        return False

@register.filter
def get_style_quantity(name, quantities):
    if quantities.get(name, ''):
        return str(quantities[name])
    else:
        return ''

@register.filter
def get_quantity_based_price(obj, quantities):
    quantity = int(quantities[obj['sku_class']])
    if not obj['variants'][0].get('price_ranges',''):
        return obj['variants'][0]['price']*quantity
    for rg in obj['variants'][0]['price_ranges']:
        if rg['max_unit_range'] >= quantity and quantity >= rg['min_unit_range']:
            return rg['price']*quantity

@register.filter
def get_page_number(index, total):

    for i in range(total):
        if i*10 <= index and (i+1)*10 > index:
            return i+1

@register.filter
def get_page_number_8(index, total):

    for i in range(total):
        if i*8 <= index and (i+1)*8 > index:
            return i+1

@register.filter(name='lookup')
def lookup(value, arg):
    try:
        lookup_value = value[arg]
    except:
        lookup_value = ''
    return lookup_value

