import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()
from miebach_admin.models import *
import datetime
from rest_api.views.utils import *
log = init_logger('logs/update_picklists.log')

update_user = 17
new_picklists = {}
def update_user_picklists(update_user):
    picklist_numbers = Picklist.objects.filter(order__user=17, creation_date__startswith='2017-03-28', picklist_number__range=[3540, 3593]).values_list('picklist_number', flat=True).distinct()
    for picklist_number in picklist_numbers:
        picklist_obj = Picklist.objects.filter(order__user=17, creation_date__startswith='2017-03-28', picklist_number=picklist_number)
        if not picklist_obj:
            print picklist_obj
            continue
        customer_name = picklist_obj[0].order.customer_name
        if int(picklist_number) in new_picklists.keys():
            pick_number = new_picklists[int(picklist_number)]
        else:
            pick_number = int(Picklist.objects.filter(order__user=17).order_by('-picklist_number')[0].picklist_number) + 1
            new_picklists[int(picklist_number)] = pick_number
        if not 'generat' in picklist_obj[0].remarks:
            picklist_obj.update(picklist_number=pick_number, remarks='Picklist_' + str(pick_number))
        else:
            picklist_obj.update(picklist_number=pick_number)

        log.info('old - ' + str(int(picklist_number)) + ' customer - ' + customer_name + 'new - ' + str(int(pick_number)))

update_user_picklists(update_user)

