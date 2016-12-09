from django import template
from miebach_admin.views import get_misc_value, get_permission

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

