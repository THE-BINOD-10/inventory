import json
import logging
from dateutil import tz
from dateutil.relativedelta import relativedelta

from django.http import HttpResponse, HttpResponseRedirect
from django.core import serializers
from django.contrib.auth import authenticate
from django.contrib import auth

from miebach_admin.custom_decorators import login_required, get_admin_user
from miebach_admin.models import GenericOrderDetailMapping, CustomerMaster

# Create your views here.
#log = init_logger('logs/qssi.log')


def update_linked_consignee_data(order_detail_id, data):
    generic_order = GenericOrderDetailMapping.objects.filter(orderdetail_id=order_detail_id)
    if generic_order:
        generic_order = generic_order[0]
        customer_master = CustomerMaster.objects.get(id=generic_order.customer_id)
        data["Buyer"]["AddressInfo"]["ShippingAddress"]["Name"] =  customer_master.name
        data["Buyer"]["AddressInfo"]["ShippingAddress"]["address"] =  customer_master.address
        data["Buyer"]["AddressInfo"]["ShippingAddress"]["city"] = customer_master.city
        data["Buyer"]["AddressInfo"]["ShippingAddress"]["state"] =  customer_master.state
        data["Buyer"]["AddressInfo"]["ShippingAddress"]["zip"] = customer_master.pincode


def integration_get_order(order_id, user, order_status = "NEW"):
    from rest_api.views.integrations import *
    WarehouseId = user.username
    get_order = get_order(order_id, user)
    if get_order["status"] == "success":
        order = get_order["data"]
        sku_data = []
        data = {"Order":
                    {"Id": ('%s_%s') % (WarehouseId, str(order["order_id"])),
                     "Status": order_status,
                     "WarehouseId": WarehouseId,
                     "StatusDateTime": order["order_date"],
                     "Financials":
                        {
                            "PRICE": str(order["total_amount"]),
                            "MRP": str(order["total_mrp"]),#what to send
                            "GST": str(order["total_gst"]),
                            "VAT":"0"
                        },

                    },#end order
                "OrderLines": [],
                "Buyer":
                    {
                        "Person":
                            {
                                "Name": order["customer_data"]["Name"],
                                "Email": order["customer_data"]["Email"],
                                "Phone": order["customer_data"]["Number"]
                            },
                        "AddressInfo":
                            {
                                "BillingAddress":
                                    {
                                        "Name": order["customer_data"]["Name"],
                                        "Address": order["customer_data"]["address"],
                                        "AddressStreet": order["customer_data"]["address"],
                                        "City": order["customer_data"]["city"],
                                        "State": order["customer_data"]["state"] if order["customer_data"]["state"] else ' ',
                                        "Zip": str(order["customer_data"]["zip"]) if order["customer_data"]["zip"] !=0 else ''
                                    },
                                "ShippingAddress":
                                    {
                                        "Name": order["customer_data"]["Name"],
                                        "Address": order["customer_data"]["address"],
                                        "AddressStreet": order["customer_data"]["address"],
                                        "City": order["customer_data"]["city"],
                                        "State": order["customer_data"]["state"] if order["customer_data"]["state"] else ' ',
                                        "Zip": str(order["customer_data"]["zip"]) if order["customer_data"]["zip"] !=0 else ''
                                    }
                            }
                    },
                "Seller":
                    {
                        "Code": ''#what to send
                    }
               }
        for ind, sku in enumerate(order["sku_data"]):
            if ind == 0:
                update_linked_consignee_data(sku["id"], data)
            sku_data.append({"SKUID": sku["sku_code"],
                             "Quantity": str(sku["quantity"]),
                             "Offer": {}
                           })
        data["OrderLines"] = sku_data
    return data


def integration_get_inventory(sku_ids, user):
    data = {"SKUIds": []}
    #sku_ids = ['AA-BATTERY', 'AAA-BATTERY', 'AC1SMK']
    for sku in sku_ids:
	temp = {"SKUId": sku,
                #"warehouseId": user.username
               }
	data["SKUIds"].append(temp)
    return data


def integration_get_order_status(order_ids, user):
    data = {
            "StartDate": "",
            "EndDate": "",
            "OrderIds": []
           }
    for order_id in order_ids:
        temp_order_id = ("%s_%s") % (user.username, str(order_id))
        data["OrderIds"].append({"OrderId": temp_order_id})
    return data
