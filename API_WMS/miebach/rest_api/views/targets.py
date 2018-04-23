import datetime
import json
from collections import OrderedDict
from operator import itemgetter

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from miebach_utils import GenericOrderDetailMapping, CustomerOrderSummary, UserProfile
# from miebach_admin.custom_decorators import get_admin_user, login_required
from miebach_admin.models import OrderDetail, CustomerUserMapping, UserGroups, \
    GenericOrderDetailMapping, User, CustomerMaster


def get_distributor_targets(start_index, stop_index, temp_data, search_term, order_term, col_num,
                                  request, user, filters={}):
    lis = ['date', 'order_id', 'zone', 'city', 'distributor', 'total_purchase_value', 'tax_amt', 'total_amt']
    up = UserProfile.objects.get(user_id=request.user.id)
    city_zone_mapping = {}
    if up.warehouse_type == 'CENTRAL_ADMIN':
        all_wh_dists_obj = UserGroups.objects.filter(admin_user=user.id)
        if request.user.userprofile.zone:
            all_wh_dists = all_wh_dists_obj.filter(user__userprofile__zone=request.user.userprofile.zone).values_list(
                'user_id', flat=True)
        else:
            all_wh_dists = all_wh_dists_obj.values_list('user_id', flat=True)
        cz_vals = all_wh_dists_obj.values_list('user_id', 'user__userprofile__city', 'user__userprofile__zone')
        for usr_id, city, zone in cz_vals:
            city_zone_mapping[usr_id] = (city, zone)
        customers = CustomerUserMapping.objects.filter(customer__user__in=all_wh_dists).values_list('customer_id',
                                                                                                    flat=True)
        gen_ords = GenericOrderDetailMapping.objects.filter(customer_id__in=customers)
        temp_data['recordsTotal'] = gen_ords.count()
        temp_data['recordsFiltered'] = temp_data['recordsTotal']
        for gen_ord in gen_ords:
            ord_det_id = gen_ord.orderdetail_id
            cm_id = gen_ord.customer_id
            distributor = User.objects.get(id=CustomerMaster.objects.get(id=cm_id).user).username
            ord_obj = OrderDetail.objects.get(id=ord_det_id)
            inv_amt = ord_obj.invoice_amount
            city, zone = city_zone_mapping[ord_obj.user]
            total_purchase_value = round(ord_obj.quantity * ord_obj.unit_price, 2)
            tax_amt = round(inv_amt - total_purchase_value, 2)
            order_id = '%s%s' % (ord_obj.order_code, ord_obj.order_id)
            temp_data['aaData'].append({'date': ord_obj.creation_date.strftime('%Y-%m-%d'),
                                        'order_id': order_id,
                                        'zone': zone, 'city': city, 'distributor': distributor,
                                        'total_purchase_value': total_purchase_value, 'tax_amt': tax_amt,
                                        'total_amt': inv_amt, 'id': ord_det_id})
        sort_col = lis[col_num]
        if order_term == 'asc':
            temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col))
        else:
            temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col), reverse=True)
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]