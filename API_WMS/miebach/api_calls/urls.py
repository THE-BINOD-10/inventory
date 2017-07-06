from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = patterns('api_calls.views',

    # Login and logout
    url(r'^authenticate_user/$', 'authenticate_user'),
    url(r'^dashboard_api/$', 'dashboard_api'),
    url(r'^stock_search/$', 'stock_search'),
    url(r'^shipment_search/$', 'shipment_search'),
    url(r'^receipt_search/$', 'receipt_search'),
    url(r'^today_returns/$', 'get_transactions_data'),
    url(r'^create_password/$', 'create_password'),
    url(r'^get_order_detail/$', 'get_order_detail'),
    url(r'^open_po/$', 'open_po'),
    url(r'^free_location_list/$', 'get_zones_count'),
    url(r'^shipment_tracker_level1/$','shipment_tracker_level1'),
    url(r'^shipment_tracker_level2/$','shipment_tracker_level2'),
    #url(r'^po_level1','po_level1'),
    #url(r'^po_level2','po_level2'),
    url(r'^sales_return_level1/$','sales_return_level1'),
    url(r'^sales_return_level2/$','sales_return_level2'),
    url(r'^get_stock_count/$', 'get_stock_count'),
    url(r'^get_shipment_info/$', 'get_shipment_info'),
    url(r'^picklist/$', 'picklist'),
    url(r'^picklist_data/$', 'picklist_data'),
    url(r'^inandout_stats/$', 'get_inbound_outbound_stats'),
    url(r'^putaway_list/$', 'putaway_list'),
    url(r'^putaway_detail/$', 'putaway_detail'),
    url(r'^get_confirmed_po/$', 'get_confirmed_po'),
    url(r'^get_supplier_data/$', 'get_supplier_data'),
    url(r'^get_misc_value/$', 'get_misc_value'),
    url(r'^get_api_misc_value/$', 'get_api_misc_value'),
    url(r'^get_skus/$', 'get_skus'),
    url(r'^get_user_skus/$', 'get_user_skus'),
    url(r'^update_orders_data/$', 'update_orders_data'),
    )
