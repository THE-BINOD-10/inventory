import copy,json,datetime
from django.template import loader, Context
from miebach_admin.models import *
from common import get_financial_year
from inbound_common_operations import *


def generate_discrepancy_data(user, po_new_data, print_des=True, **report_data_dict):
    for key, val in report_data_dict.items():
        exec(key + '=val')
    putaway_data = {'putaway_key': []}
    total_discrepency_amount = 0
    total_discrepency_qty = 0
    discrepency_dict = {}
    descrip_prefix = ''
    if not print_des:
        discrepency_prefix = MiscDetail.objects.filter(user=user.id, misc_type='discrepency_prefix')
        if discrepency_prefix.exists():
            descrip_prefix = discrepency_prefix[0].misc_value
    discrepency_report_dict = copy.deepcopy(report_data_dict)
    for key, value in po_new_data.iteritems():
        value = po_new_data[key].get('value', 0)
        price = 0
        if key[3]:
            price = key[3]
        entry_price = float(price) * float(value)
        purchase_order_dict = {'wms_code': key[1],
                               'measurement_unit': key[2],
                               'price': price, 'cgst_tax': key[4], 'sgst_tax': key[5],
                               'igst_tax': key[6], 'utgst_tax': key[7], 'amount': entry_price,
                               'sku_desc': key[8], 'apmc_tax': key[9], 'batch_no': key[12],
                               'mrp': key[13]}
        tax = 0
        if key[4]:
            tax += float(key[4])
        if key[5]:
            tax += float(key[5])
        if key[6]:
            tax += float(key[6])
        discrepency_quantity = float(po_new_data[key].get('discrepency_quantity', 0))
        discrepencey_reason = po_new_data[key].get('discrepency_reason', '')
        po_id = po_new_data[key].get('po_id', '')
        discrepencey_price = float(price) * float(discrepency_quantity)
        discrepencey_price_tax = discrepencey_price + (discrepencey_price * tax / 100)
        total_discrepency_amount += discrepencey_price_tax
        total_discrepency_qty += discrepency_quantity
        if discrepency_quantity and not print_des:
            purchase_order_text = json.dumps(purchase_order_dict)
            discrepency_dict = {'quantity': discrepency_quantity, 'return_reason': discrepencey_reason, }
            if po_id:
                discrepency_dict['purchase_order_id'] = po_id
                po_order = PurchaseOrder.objects.get(id=po_id)
                purchase_order = po_order
                purchase_order.received_quantity +=discrepency_quantity
                purchase_order.discrepancy_quantity = discrepency_quantity
                purchase_order.save()
            else:
                discrepency_dict['new_data'] = purchase_order_text
            if not print_des:
                incremental_object = IncrementalTable.objects.filter(user=user.id, type_name='discrepancy')
                if not incremental_object.exists():
                    discrepency_number = 1
                    incremental_object = IncrementalTable.objects.create(user_id=user.id,
                                                                         value=discrepency_number,
                                                                         type_name='discrepancy')
                else:
                    discrepency_number = incremental_object[0].value
                    incremental_object = incremental_object[0]

                full_discrepancy_number = descrip_prefix + get_financial_year(
                    datetime.datetime.now()) + '/' + str(discrepency_number).zfill(4)
                discrepency_dict['discrepancy_number'] = full_discrepancy_number
                discrepency_dict['po_number'] = po_number
                if receipt_number:
                    discrepency_dict['receipt_number'] = receipt_number
                discrepency_dict['user_id'] = user.id
                Discrepancy.objects.create(**discrepency_dict)
        discrpency_po_dict = {'discrepency_quantity': discrepency_quantity,
                              'discrepency_reason': discrepencey_reason,
                              'discrepencey_price': discrepencey_price,
                              'discrepencey_price_tax': discrepencey_price_tax, }
        purchase_order_dict.update(discrpency_po_dict)
        putaway_data['putaway_key'].append(purchase_order_dict)
    if not print_des:
        if incremental_object:
            incremental_update = incremental_object
            incremental_update.value = discrepency_number + 1
            incremental_update.save()
    sku_list = putaway_data[putaway_data.keys()[0]]
    sku_slices = generate_grn_pagination(sku_list)
    discrepency_data_dict = {'data': putaway_data, 'data_slices': sku_slices,
                             'discrepancy_number': full_discrepancy_number,
                             'total_discrepency_qty': total_discrepency_qty,
                             'total_discrepency_amount': total_discrepency_amount}
    if not print_des:
        supplier_dict = {'supplier_id': data_dict[1][1], 'supplier_name':data_dict[3][1], 'supplier_gst' : data_dict[4][1]}
        discrepency_report_dict.update(supplier_dict)
    discrepency_report_dict.update(discrepency_data_dict)
    t = loader.get_template('templates/toggle/discrepency_form.html')
    discrepency_rendered = t.render(discrepency_report_dict)
    if not print_des:
        data_dict_po = {'po_date': order_date, 'po_reference': po_number,
                        'invoice_number': bill_no, 'supplier_name': data_dict[1][1],
                        'number': discrepency_dict.get('discrepancy_number', ''), 'type': 'Discrepancy',}
    if print_des:
        return discrepency_rendered
    else:
        return discrepency_rendered, data_dict_po
