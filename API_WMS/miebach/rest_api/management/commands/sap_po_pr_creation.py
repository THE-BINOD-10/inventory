from miebach_admin.models import *
import datetime
from django.db.models import Sum, F, Q, Count
from rest_api.views.common import get_misc_value, get_admin, get_uom_with_multi_skus, get_sku_wise_pr_amount_and_quantity
from rest_api.management.commands.analytics_script import *


po_nums = PurchaseOrder.objects.filter(open_po_id__isnull=False).exclude(status__in= ["deleted", "stock-transfer"]).values_list("po_number", flat=True).distinct()
po_nums = list(po_nums)

sku_codes_list = PurchaseOrder.objects.filter(open_po_id__isnull=False, po_number__in= po_nums).values_list("open_po__sku__sku_code", flat=True).distinct()
user = User.objects.get(username= "mhl_admin")
skus_uom_dict = get_uom_with_multi_skus(user, sku_codes_list, uom_type='purchase')




count = 0
po_numbers_list = \
    PendingPO.objects.filter().values_list('full_po_number',
        flat=True).distinct()
len(po_numbers_list)
po_list_temp = []
final_list = []
po_final_list= [] 




po_obj_result= PurchaseOrder.objects.filter().values( "po_number", "open_po__sku__sku_code", "open_po__order_quantity", "open_po__price").distinct().annotate(count=Count('open_po__order_quantity'))
duplicate_po_sku_codes= {}
for each_row in po_obj_result:
    if each_row["count"]>1:
        if each_row["po_number"] in duplicate_po_sku_codes:
            duplicate_po_sku_codes[each_row["po_number"]].append(each_row)
        else:
            duplicate_po_sku_codes[each_row["po_number"]] = [each_row]


exclude_po_numbers= duplicate_po_sku_codes.keys()



for row in po_nums:
    if str(row) not in po_numbers_list and str(row) not in ['12-27001-BIOCHE00010', '16-27001-BIOCHE00006']:
        po_list_temp.append(str(row))
        po_obj = PurchaseOrder.objects.filter(po_number=str(row))
        full_pr_number = 'SAP-PR-' + str(row)
        for each_po in po_obj:
            data = {'price': 0, 'pquantity': 0}
            uom_dict = skus_uom_dict.get(each_po.open_po.sku.sku_code)
            pcf = uom_dict.get('sku_conversion', 1)
            if full_pr_number:
                data['full_pr_number'] = full_pr_number
            if each_po.creation_date:
                data['pr_date'] = each_po.creation_date.isoformat()
            request_user = \
                User.objects.filter(id=each_po.open_po.sku.user)[0]
            if request_user:
                data['requested_user'] = request_user.first_name
                data['wh_user'] = request_user.first_name
            plant, department, department_code, plant_zone,pr_plant_code = '', '', '', '', ''
            req_user = request_user
            if req_user:
                if req_user.userprofile.warehouse_type.lower() == 'dept':
                    department = req_user.first_name
                    department_code = req_user.userprofile.stockone_code
                    admin_user = get_admin(req_user)
                    pr_plant_code = admin_user.userprofile.stockone_code
                    plant = admin_user.userprofile.user.first_name
                    plant_zone = admin_user.userprofile.zone
                else:
                    pr_plant_code = req_user.userprofile.stockone_code
                    plant = req_user.first_name
                    plant_zone = req_user.userprofile.zone
            data['zone'] = plant_zone
            if plant:
                data['plant_name'] = plant
            if pr_plant_code:
                data['plant_code'] = pr_plant_code
            if department:
                data['department_name'] = department
            if department_code:
                data['department_code'] = department_code
            if each_po.open_po.sku.sku_code:
                data['sku_code'] = each_po.open_po.sku.sku_code
            if each_po.open_po.sku.sku_desc:
                data['sku_desc'] = each_po.open_po.sku.sku_desc
            if each_po.open_po.sku.sku_category:
                data['sku_category'] = each_po.open_po.sku.sku_category
            if each_po.open_po.sku.sku_class:
                data['sku_class'] = each_po.open_po.sku.sku_class
            if each_po.open_po.sku.sku_brand:
                data['sku_brand'] = each_po.open_po.sku.sku_brand
            if each_po.open_po.sku.hsn_code:
                data['hsn_code'] = each_po.open_po.sku.hsn_code
            if each_po.open_po.supplier.supplier_id:
                data['supplier_id'] = each_po.open_po.supplier.supplier_id
            if each_po.open_po.supplier.name:
                data['supplier_name'] = each_po.open_po.supplier.name
            if each_po.open_po.supplier.tin_number:
                data['supplier_gst_number'] = \
                    each_po.open_po.supplier.tin_number
            if each_po.open_po.supplier.state:
                data['supplier_state'] = each_po.open_po.supplier.state
            if each_po.open_po.supplier.country:
                data['supplier_country'] = each_po.open_po.supplier.country
            if each_po.open_po.sgst_tax:
                data['sgst_tax'] = each_po.open_po.sgst_tax
            if each_po.open_po.cgst_tax:
                data['cgst_tax'] = each_po.open_po.cgst_tax
            if each_po.open_po.igst_tax:
                data['igst_tax'] = each_po.open_po.igst_tax
            if each_po.open_po.cess_tax:
                data['cess_tax'] = each_po.open_po.cess_tax
            if each_po.open_po.price:
                data['price'] = each_po.open_po.price
            if each_po.open_po.order_quantity:
                data['pquantity'] = each_po.open_po.order_quantity
                data['base_quantity'] = each_po.open_po.order_quantity * pcf
            if uom_dict['measurement_unit']:
                data['puom'] = uom_dict['measurement_unit']
            data['base_uom'] = uom_dict['base_uom']
            data['pcf'] = pcf
            data['final_status'] = 'pr_converted_to_po'
            final_list.append(data)
            po_dict = data.copy()
            po_dict['full_po_number'] = str(row)
            po_dict['po_date'] = each_po.creation_date.isoformat()
            po_dict["po_raised_date"] = each_po.creation_date.isoformat()
            po_dict["po_id"] = each_po.id
            del po_dict["final_status"]
            po_final_list.append(po_dict)




po_final_list1 = po_final_list


for purchase_order_data_pr in po_final_list:
    try:
        purchase_order_data = purchase_order_data_pr.copy()
        del purchase_order_data_pr["full_po_number"] 
        del purchase_order_data_pr["po_date"]
        del purchase_order_data_pr["po_raised_date"]
        del purchase_order_data_pr["po_id"] 
        try:
            pr_obj= AnalyticsPurchaseRequest.objects.using('mhl_analytics').update_or_create(
                full_pr_number=purchase_order_data_pr['full_pr_number'],
                pr_date=purchase_order_data_pr['pr_date'],
                sku_code=purchase_order_data_pr['sku_code'],
                price=purchase_order_data_pr['price'],
                pquantity=purchase_order_data_pr['pquantity'],
                defaults=purchase_order_data_pr,
                )
        except Exception, err:
            print ('.....', str(err))
            print purchase_order_data_pr
        full_pr_number = purchase_order_data.get("full_pr_number", "")
        pr_date = purchase_order_data.get("pr_date", "")
        if 'full_pr_number' in purchase_order_data:
            del purchase_order_data["full_pr_number"]
        if 'pr_date' in purchase_order_data:
            del purchase_order_data["pr_date"]
        if 'priority_type' in  purchase_order_data:
            del purchase_order_data["priority_type"]
        if "po_date" in purchase_order_data and not purchase_order_data.get("po_date", None):
            del purchase_order_data["po_date"]
        po_object= AnalyticsPurchaseOrder.objects.using('mhl_analytics').update_or_create(
            po_id= purchase_order_data["po_id"],
            full_po_number= purchase_order_data['full_po_number'],
            sku_code= purchase_order_data['sku_code'],
            price= purchase_order_data['price'],
            pquantity = purchase_order_data['pquantity'],
            defaults= purchase_order_data)
        pr_obj[0].purchase_orders.add(po_object[0])
        # pr_objects = AnalyticsPurchaseRequest.objects.using('mhl_analytics').filter(
        #    full_pr_number=full_pr_number,
        #    sku_code= purchase_order_data['sku_code'],
        #    pquantity = purchase_order_data['pquantity'],
        #    price = purchase_order_data['price'],
        #    pr_date= pr_date,
        #    )
        # if pr_objects.exists():
        # for pr_obj in pr_objects:
        # pr_obj.purchase_orders.add(po_object[0])
    except Exception as err:
        print(".....", str(err))
        print(purchase_order_data)






# for purchase_request_date in final_list:
#     try:
#         print AnalyticsPurchaseRequest.objects.using('mhl_analytics').update_or_create(
#             full_pr_number=purchase_request_date['full_pr_number'],
#             pr_date=purchase_request_date['pr_date'],
#             sku_code=purchase_request_date['sku_code'],
#             price=purchase_request_date['price'],
#             pquantity=purchase_request_date['pquantity'],
#             defaults=purchase_request_date,
#             )
#     except Exception, err:
#         print ('.....', str(err))
#         print purchase_request_date



# po_obj_result= PendingLineItems.objects.filter(pending_po__full_po_number__isnull=False).values( "pending_po__full_po_number", "sku__sku_code", "quantity", "price").distinct().annotate(count=Count('quantity'))
# duplicate_po_sku_codes= {}
# for each_row in po_obj_result:
#     if each_row["count"]>1:
#         if each_row["pending_po__full_po_number"] in duplicate_po_sku_codes:
#             duplicate_po_sku_codes[each_row["pending_po__full_po_number"]].append(each_row)
#         else:
#             duplicate_po_sku_codes[each_row["pending_po__full_po_number"]] = [each_row]


# exclude_po_numbers= duplicate_po_sku_codes.keys()

# from miebach_admin.models import *
# import datetime
# from django.db.models import Sum, F, Q, Count
# po_obj_result= PurchaseOrder.objects.filter().values( "po_number", "open_po__sku__sku_code", "open_po__order_quantity", "open_po__price").distinct().annotate(count=Count('open_po__order_quantity'))
# duplicate_po_sku_codes= {}
# for each_row in po_obj_result:
#     if each_row["count"]>1:
#         if each_row["po_number"] in duplicate_po_sku_codes:
#             duplicate_po_sku_codes[each_row["po_number"]].append(each_row)
#         else:
#             duplicate_po_sku_codes[each_row["po_number"]] = [each_row]


# # st = []
# # for row in exclude_po_numbers:
# #   if len(row)>12:
# #     st.append(row)

# # st= [u'42-22017-ALLDE00188', u'12-7003-IMMUN00586', u'12-19011-IMMUN00631', u'42-24008-SCMMM00314', u'42-27093-ALLDE00020', u'42-24100-SCMMM00063', u'12-27133-SCMMM00032', u'12-27133-SCMMM00033', u'12-27133-SCMMM00031', u'12-27133-SCMMM00036', u'12-33004-SCMMM01252', u'42-32142-SCMMM00062', u'12-7003-MOLBI00867', u'42-24008-SCMMM00307', u'42-32141-ALLDE00062', u'12-27007-SEROL00332', u'12-27007-HEMAT00299', u'16-33004-ADMIN00299', u'12-33004-HEMAT01227', u'42-32152-SCMMM00097', u'42-24008-SCMMM00641', u'12-27001-IMMUN03441', u'12-27038-SCMMM00013', u'12-24010-SCMMM00269', u'12-36053-ALLDE00201', u'PO-51822003/452', u'12-10034-ALLDE00308', u'42-32012-HEMAT00569', u'45-24045-ITTEC00010', u'16-27001-ADMIN00429', u'12-3046-ALLDE00104', u'42-27016-IMMUN00194', u'25-27041-ITTEC00007', u'42-24008-SCMMM00599', u'12-33004-SCMMM01921', u'42-32142-SCMMM00065', u'12-33075-ALLDE00094', u'42-27016-BIOCHE00196', u'45-32056-ALLDE00010', u'12-7058-ALLDE00154', u'42-24092-SCMMM00013', u'12-27007-CLPAT00295', u'42-33044-ALLDE00033', u'12-10076-BIOCHE00054', u'12-24032-IMMUN00282', u'12-27073-ALLDE00041', u'12-24032-IMMUN00280', u'12-9057-ALLDE00119', u'42-32138-ALLDE00066', u'42-24008-SCMMM00311', u'12-33036-ALLDE00086', u'12-24032-BIOCHE00207', u'42-32138-ALLDE00193', u'42-32006-RADIO00394', u'12-33004-SEROL01241', u'42-24008-SCMMM00309', u'16-99930-ITTEC00022', u'16-99930-ITTEC00025', u'12-27007-ALLDE00318', u'12-27007-ALLDE00315', u'16-27062-ALLDE00004', u'42-32142-ALLDE00051', u'16-19011-ADMIN00059', u'45-29005-SCMMM00123', u'12-27082-ALLDE00033', u'12-27025-CLITRL00218', u'12-7003-HRDDE00906', u'42-32140-SCMMM00100', u'16-33004-SCMMM00344', u'12-9095-ALLDE00080', u'12-27025-CLITRL00136', u'12-19011-BIOCHE00629', u'12-24039-SCMMM00037', u'12-27002-NACOP00053', u'12-7003-IFADE00890', u'12-6074-ALLDE00331', u'45-24008-SCMMM00129', u'12-27007-IMMUN00326', u'12-24072-SCMMM00056', u'16-99927-ADMIN00086', u'16-99927-ITTEC00207', u'12-24039-SCMMM00146', u'22-27127-NACOP00058', u'12-3094-ALLDE00083', u'12-33075-BIOCHE00087', u'42-32140-SCMMM00093', u'12-36053-SCMMM00134', u'12-27007-SEROL00481', u'12-27028-ALLDE00139', u'12-99927-MARKE00033', u'12-99927-MARKE00032', u'42-24070-BIOCHE00106', u'16-99927-ITTEC00082', u'16-99927-ITTEC00084', u'12-33004-BIOCHE01239', u'12-27007-HEMAT00300', u'12-7003-IMMUN00525', u'12-7003-HEMAT00574', u'12-10034-IMMUN00065', u'16-33004-MARKE00323', u'16-33004-MARKE00325', u'16-33004-MARKE00324', u'42-24040-SCMMM00125', u'12-24039-SCMMM00139', u'12-27023-SCMMM00078', u'12-3051-ADMIN00146', u'12-27025-CLITRL00212', u'12-27028-SEROL00041', u'12-33004-SCMMM01354', u'12-33004-SCMMM01352', u'12-33004-MICRO01407', u'12-27007-ALLDE00523', u'12-4031-ALLDE00158', u'12-99927-MARKE00102', u'16-24010-ITTEC00072', u'42-24008-SCMMM00310', u'12-24032-BIOCHE00138', u'12-33081-SCMMM00093', u'16-27030-ITTEC00012', u'16-27030-ITTEC00011', u'16-33004-ADMIN00330', u'45-32043-ALLDE00009', u'12-33085-ALLDE00034', u'45-27016-ITTEC00039', u'12-27001-LOGIS01251', u'12-27007-MICRO00338', u'12-24032-HEMAT00278', u'12-27001-HEMAT03193', u'12-33004-BIOCHE01846', u'16-33004-SCMMM00345', u'12-99927-MARKE00025', u'12-27001-HISTO02142', u'12-10034-ALLDE00125', u'42-22017-ALLDE00316', u'12-33066-BIOCHE00147', u'42-27018-SCMMM00404', u'12-27023-ALLDE00094', u'12-24010-SCMMM00258', u'12-24032-HEMAT00277', u'12-27007-ALLDE00510', u'42-24008-SCMMM00658']

# # dd= []
# # for s_t in st:
# #   if str(s_t) in dd:
# #      print(s_t)
# #   else:
# #      dd.append(str(s_t))

# final_list= []
# p_po= PendingLineItems.objects.filter(pending_po__full_po_number__in=st)
# for row in p_po:
#     s_po= PurchaseOrder.objects.filter(po_number=row.pending_po.full_po_number, open_po__sku__sku_code=row.sku.sku_code).values("sellerposummary__grn_number",
#     	"sellerposummary__creation_date", "sellerposummary__price", 
#     	"sellerposummary__quantity", "received_quantity",
#     	"open_po__order_quantity", "open_po__price", "creation_date"
#     	)
#     count = 0
#     if s_po.exists():
#         for e_row in s_po:
#             if count==0:
#                 data_dict= {'PO Number': row.pending_po.full_po_number, 'Pending PO Quantity': row.quantity, 
#      'SKU Code': row.sku.sku_code, 'SKU Desc': row.sku.sku_desc,
#     'Supplier Code': row.pending_po.supplier.supplier_id,
#     'Supplier Name': row.pending_po.supplier.name, "Received Quantity": e_row["received_quantity"], 
#      "Confirmed PO Quantity": e_row["open_po__order_quantity"],
#      "PO Date": e_row["creation_date"].isoformat(),
#      "PO Price": e_row["open_po__price"],
#      "GRN Number": e_row["sellerposummary__grn_number"],
#      "GRN Date": e_row["sellerposummary__creation_date"].isoformat() if e_row["sellerposummary__creation_date"] else "",
#      "GRN Quantity": e_row["sellerposummary__quantity"],
#       "GRN Price": e_row["sellerposummary__price"],
#      }
#                 final_list.append(data_dict)
#             else:
#                 data_dict= {'PO Number': row.pending_po.full_po_number, 'Pending PO Quantity': "",
#           'SKU Code': row.sku.sku_code, 'SKU Desc': row.sku.sku_desc,
#            'Supplier Code': "",
#          'Supplier Name': "", 
#          "Received Quantity": e_row["received_quantity"], 
#      "Confirmed PO Quantity": e_row["open_po__order_quantity"],
#      "PO Date": e_row["creation_date"].isoformat(),
#      "PO Price": e_row["open_po__price"],
#      "GRN Number": e_row["sellerposummary__grn_number"],
#      "GRN Date": e_row["sellerposummary__creation_date"].isoformat() if e_row["sellerposummary__creation_date"] else "",
#      "GRN Quantity": e_row["sellerposummary__quantity"],
#       "GRN Price": e_row["sellerposummary__price"],
#           }
#                 final_list.append(data_dict)
#             count+=1



# import pandas as pd
# from datetime import datetime
# file_name = "Excess_quantity_POs" + datetime.now().strftime("%d_%m_%Y") 
# pd.DataFrame(final_list).to_excel(file_name +".xlsx", index=False, columns=["PO Number", "Supplier Code",
#  "Supplier Name", "SKU Code", "SKU Desc", "Pending PO Quantity", "PO Date", "Confirmed PO Quantity", "Received Quantity", "PO Price","GRN Number", "GRN Date", "GRN Quantity", "GRN Price"])
# print(file_name+ '.xlsx')   
# pd.DataFrame(final_list).to_csv(file_name + ".csv", index=False)

    









