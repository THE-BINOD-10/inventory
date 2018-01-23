
from django.conf.urls import include, url
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings
from miebach_admin.views import *
from api_calls import urls as api_calls_urls
from rest_api import urls as rest_api_urls

admin.autodiscover()

#urlpatterns = patterns('miebach_admin.views',
urlpatterns =  [
    # Examples:
    # url(r'^$', 'miebach.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    #url(r'^grappelli/', include('grappelli.urls')), # grappelli URLS
    url(r'^admin/',  include(admin.site.urls)), # admin site

    # Login and logout
    url(r'^login/$', login),
    url(r'^wms_login/$', wms_login),
    url(r'^logout/$', logout),

    # miebach admin urls
    url(r'^home/$', home),
    url(r'^$', home),
    url(r'^uploads/$', uploads),
    url(r'^set_timezone/$', set_timezone),

    # Dashboard
    url(r'^track_orders/$', track_orders),
    url(r'^get_orders_count/$', get_orders_count),

    # Masters
    url(r'^sku_master/$', sku_master),
    url(r'^check_sku/$', check_sku),
    url(r'^location_master/$', location_master),
    url(r'^supplier_master/$', supplier_master),
    url(r'^supplier_sku_master/$', supplier_sku_mapping),
    url(r'^insert_mapping/$', insert_mapping),
    url(r'^add_location_data/$', add_location_data),
    url(r'^customer_master/$', customer_master),
    url(r'^insert_customer/$', insert_customer),
    url(r'^get_customer_update/$', get_customer_update),
    url(r'^update_customer_values/$', update_customer_values),
    url(r'^bom_master/$', bom_master),
    url(r'^add_bom_data/$', add_bom_data),
    url(r'^insert_bom_data/$', insert_bom_data),
    url(r'^get_bom_data/$', get_bom_data),
    url(r'^delete_bom_data/$', delete_bom_data),
    url(r'^get_sku_grid/$', get_sku_grid),
    url(r'^get_category_view/$', get_category_view),
    url(r'^customer_sku_mapping/$', customer_sku_mapping),
    url(r'^insert_customer_sku/$', insert_customer_sku),
    url(r'^delete_market_mapping/$', delete_market_mapping),
    url(r'^warehouse_master/$', warehouse_master),
    url(r'^add_warehouse_user/$', add_warehouse_user),
    url(r'^get_warehouse_user_data/$', get_warehouse_user_data),
    url(r'^update_warehouse_user/$', update_warehouse_user),
    url(r'^discount_master/$', discount_master),
    url(r'^insert_discount/$', insert_discount),
    url(r'^vendor_master/$', vendor_master),
    url(r'^insert_vendor/$', insert_vendor),
    url(r'^get_vendor_data/$', get_vendor_data),
    url(r'^update_vendor_values/$', update_vendor_values),

    # Inbound
    url(r'^raise_po/$', raise_po),
    url(r'^receive_po/$', receive_po),
    url(r'^quality_check/$', quality_check),
    url(r'^putaway_confirmation/$', putaway_confirmation),
    url(r'^putaway_data/$', putaway_data),
    url(r'^confirm_po/$', confirm_po),
    url(r'^add_po/$', add_po),
    url(r'^generated_po_data/$', generated_po_data),
    url(r'^modify_po_update/$', modify_po_update),
    url(r'^get_supplier_data/$', get_supplier_data),
    url(r'^update_receive_po/$', update_receive_po),
    url(r'^update_receiving/$', update_receiving),
    url(r'^confirm_grn/$', confirm_grn),
    url(r'^get_received_orders/$', get_received_orders),
    url(r'^update_putaway/$', update_putaway),
    url(r'^get_supplier_update/$', get_supplier_update),
    url(r'^get_sku_supplier_update/$', get_sku_supplier_update),
    url(r'^update_supplier_values/$', update_supplier_values),
    url(r'^update_sku_supplier_values/$', update_sku_supplier_values),
    url(r'^delete_po/$', delete_po),
    url(r'^confirm_po1/$', confirm_po1),
    url(r'^delete_po_group/$', delete_po_group),
    url(r'^confirm_add_po/$', confirm_add_po),
    url(r'^raise_po_toggle/$', raise_po_toggle),
    url(r'^add_lr_details/$', add_lr_details),
    url(r'^get_mapping_values/$', get_mapping_values),
    url(r'^quality_check_data/$', quality_check_data),
    url(r'^confirm_quality_check/$', confirm_quality_check),
    url(r'^sales_returns/$', sales_returns),
    url(r'^get_order_detail_data/$', get_order_detail_data),
    url(r'^close_po/$', close_po),
    url(r'^validate_wms/$', validate_wms),
    url(r'^get_returns_page/$', get_returns_page),
    url(r'^check_returns/$', check_returns),
    url(r'^confirm_sales_return/$', confirm_sales_return),
    url(r'^returns_putaway_data?/$', returns_putaway_data),
    url(r'^generate_po_data?/$', generate_po_data),
    url(r'^check_wms_qc?/$', check_wms_qc),
    url(r'^check_serial_exists?/$', check_serial_exists),
    url(r'^raise_st_toggle/$', raise_st_toggle),
    url(r'^save_st/$', save_st),
    url(r'^update_raised_st/$', update_raised_st),
    url(r'^confirm_st/$', confirm_st),
    url(r'^delete_st/$', delete_st),

    # Production
    url(r'^raise_jo/$', raise_jo),
    url(r'^raise_jo_toggle/$', raise_jo_toggle),
    url(r'^save_jo/$', save_jo),
    url(r'^generated_jo_data/$', generated_jo_data),
    url(r'^confirm_jo/$', confirm_jo),
    url(r'^delete_jo/$', delete_jo),
    url(r'^confirm_jo_group/$', confirm_jo_group),
    url(r'^delete_jo_group/$', delete_jo_group),
    url(r'^rm_picklist/$', rm_picklist),
    url(r'^view_rm_picklist/$', view_rm_picklist),
    url(r'^rm_picklist_confirmation/$', rm_picklist_confirmation),
    url(r'^print_rm_picklist/$', print_rm_picklist),
    url(r'^receive_jo/$', receive_jo),
    url(r'^confirmed_jo_data/$', confirmed_jo_data),
    url(r'^save_receive_jo/$', save_receive_jo),
    url(r'^confirm_jo_grn/$', confirm_jo_grn),
    url(r'^jo_putaway_confirmation/$', jo_putaway_confirmation),
    url(r'^received_jo_data/$', received_jo_data),
    url(r'^jo_putaway_data/$', jo_putaway_data),
    url(r'^back_orders_rm/$', back_orders_rm),
    url(r'^generate_rm_po_data/$', generate_rm_po_data),
    url(r'^get_material_codes/$', get_material_codes),
    url(r'^view_confirmed_jo/$', view_confirmed_jo),
    url(r'^jo_generate_picklist/$', jo_generate_picklist),
    url(r'^raise_rwo_toggle/$', raise_rwo_toggle),
    url(r'^save_rwo/$', save_rwo),
    url(r'^saved_rwo_data/$', saved_rwo_data),
    url(r'^confirm_rwo/$', confirm_rwo),
    url(r'^generate_rm_rwo_data/$', generate_rm_rwo_data),

    # Outbound
    url(r'^generate_picklist/$', generate_picklist),
    url(r'^view_manifest/$', view_manifest),
    url(r'^pull_confirmation/$', pull_confirmation),
    url(r'^view_picklist/$', view_picklist),
    url(r'^picklist_confirmation/$', picklist_confirmation),
    url(r'^view_picked_orders/$', view_picked_orders),
    url(r'^switches/$', switches),
    url(r'^batch_generate_picklist/$', batch_generate_picklist),
    url(r'^shipment_info/$', shipment_info),
    url(r'^get_customer_sku/$', get_customer_sku),
    url(r'^insert_shipment_info/$', insert_shipment_info),
    url(r'^shipment_info_data/$', shipment_info_data),
    url(r'^get_customer_results/$', get_customer_results),
    url(r'^print_shipment/$', print_shipment),
    url(r'^print_picklist/$', print_picklist),
    url(r'^print_picklist_excel/$', print_picklist_excel),
    url(r'^marketplace_segregation/$', marketplace_segregation),
    url(r'^create_orders/$', create_orders),
    url(r'^insert_order_data/$', insert_order_data),
    url(r'^get_customer_data/$', get_customer_data),
    url(r'^pullto_locate/$', pullto_locate),
    url(r'^batch_transfer_order/$', batch_transfer_order),
    url(r'^transfer_order/$', transfer_order),
    url(r'^confirm_transfer/$', confirm_transfer),
    url(r'^check_imei/$', check_imei),
    url(r'^check_imei_exists/$', check_imei_exists),
    url(r'^back_orders/$', back_orders),
    url(r'^confirm_back_order/$', confirm_back_order),
    url(r'^generate_jo_data?/$', generate_jo_data),
    url(r'^st_generate_picklist/$', st_generate_picklist),
    url(r'^create_stock_transfer/$', create_stock_transfer),
    url(r'^get_selected_skus/$', get_selected_skus),
    url(r'^update_shipment_status/$', update_shipment_status),

    # Stock Locator
    url(r'^stock_summary_data/$', stock_summary_data),
    url(r'^stock_summary/$', stock_summary),
    url(r'^stock_detail/$', stock_detail),
    url(r'^move_inventory/$', move_inventory),
    url(r'^cycle_count/$', cycle_count),
    url(r'^inventory_adjustment/$', inventory_adjustment),
    url(r'^add_move_inventory/$', add_move_inventory),
    url(r'^insert_move_inventory/$', insert_move_inventory),
    url(r'^add_inventory_adjust/$', add_inventory_adjust),
    url(r'^insert_inventory_adjust/$', insert_inventory_adjust),
    url(r'^delete_inventory/$', delete_inventory),
    url(r'^get_sku_stock_data/$', get_sku_stock_data),

    # Insert SKU
    url(r'^insert_sku/$', insert_sku),
    url(r'^insert_supplier/$', insert_supplier),
    url(r'^get_sku_data/$', get_sku_data),
    url(r'^update_sku/$', update_sku),
    url(r'^add_location/$', add_location),
    url(r'^add_zone/$', add_zone),
    url(r'^results_data/$', results_data),
    url(r'^get_customer_sku_data/$', get_customer_sku_data),
    url(r'^update_customer_sku_mapping/$', update_customer_sku_mapping),
    url(r'^search_customer_sku_mapping/$', search_customer_sku_mapping),

    #Location
    url(r'^get_location_data/$', get_location_data),
    url(r'^update_location/$', update_location),

    # Orders
    #url(r'^orders/$', orders),
    #url(r'^print_order_data/$', print_order_data),

    # Uploads
    url(r'^sku_upload/$', sku_upload),
    url(r'^sku_form/$', sku_form),
    url(r'^location_upload/$', location_upload),
    url(r'^process_orders/$', process_orders),
    url(r'^inventory_form/$', inventory_form),
    url(r'^location_form/$', location_form),
    url(r'^inventory_upload/$', inventory_upload),
    url(r'^supplier_upload/$', supplier_upload),
    url(r'^supplier_form/$', supplier_form),
    url(r'^confirm_cycle_count/$', confirm_cycle_count),
    url(r'^get_id_cycle/$', get_id_cycle),
    url(r'^submit_cycle_count/$', submit_cycle_count),
    url(r'^confirm_inventory_adjustment/$', confirm_inventory_adjustment),
    url(r'^supplier_sku_form/$', supplier_sku_form),
    url(r'^supplier_sku_upload/$', supplier_sku_upload),
    url(r'^marketplace_sku_form/$', marketplace_sku_form),
    url(r'^marketplace_sku_upload/$', marketplace_sku_upload),
    url(r'^confirm_move_inventory/$', confirm_move_inventory),
    url(r'^order_upload/$', order_upload),
    url(r'^order_form/$', order_form),
    url(r'^purchase_order_form/$', purchase_order_form),
    url(r'^purchase_order_upload/$', purchase_order_upload),
    url(r'^move_inventory_form/$', move_inventory_form),
    url(r'^move_inventory_upload/$', move_inventory_upload),
    url(r'^bom_form/$', bom_form),
    url(r'^bom_upload/$', bom_upload),
    url(r'^combo_sku_form/$', combo_sku_form),
    url(r'^combo_sku_upload/$', combo_sku_upload),
    url(r'^inventory_adjust_form/$', inventory_adjust_form),
    url(r'^inventory_adjust_upload/$', inventory_adjust_upload),

    # Reports
    url(r'^sku_list_report/$', sku_list_report),
    url(r'^location_wise_filter/$', location_wise_filter),
    url(r'^supplier_wise_pos/$', supplier_wise_pos),
    url(r'^get_supplier_details/$', get_supplier_details),
    url(r'^goods_receipt_note/$', goods_receipt_note),
    url(r'^receipt_summary_report/$', receipt_summary_report),
    url(r'^dispatch_summary_report/$', dispatch_summary_report),
    url(r'^sku_wise_stock/$', sku_wise_stock),
    url(r'^get_sku_filter/$', get_sku_filter),
    url(r'^get_po_filter/$', get_po_filter),
    url(r'^get_location_filter/$', get_location_filter),
    url(r'^print_po/$', print_po),
    url(r'^print_sku/$', print_sku),
    url(r'^print_stock_location/$', print_stock_location),
    url(r'^get_receipt_filter/$', get_receipt_filter),
    url(r'^print_supplier_pos/$', print_supplier_pos),
    url(r'^print_receipt_summary/$', print_receipt_summary),
    url(r'^print_po_reports/$', print_po_reports),
    url(r'^get_dispatch_filter/$', get_dispatch_filter),
    url(r'^print_dispatch_summary/$', print_dispatch_summary),
    url(r'^get_sku_stock_filter/$', get_sku_stock_filter),
    url(r'^print_sku_wise_stock/$', print_sku_wise_stock),
    url(r'^sales_return_report/$', sales_return_report),
    url(r'^get_sales_return_filter/$', get_sales_return_filter),
    url(r'^print_sales_returns/$', print_sales_returns),
    url(r'^sku_wise_purchases/$', sku_wise_purchases),
    url(r'^get_sku_purchase_filter/$', get_sku_purchase_filter),
    url(r'^print_sku_wise_purchase/$', print_sku_wise_purchase),
    url(r'^daily_stock_report/$', daily_stock_report),
    url(r'^update_mail_configuration/$', update_mail_configuration),
    url(r'^send_mail_reports/$', send_mail_reports),
    url(r'^excel_reports/$', excel_reports),
    url(r'^inventory_adjust_report/$', inventory_adjust_report),
    url(r'^get_inventory_adjust_filter/$', get_inventory_adjust_filter),
    url(r'^print_adjust_report/$', print_adjust_report),
    url(r'^inventory_aging_report/$', inventory_aging_report),
    url(r'^get_inventory_aging_filter/$', get_inventory_aging_filter),
    url(r'^print_aging_report/$', print_aging_report),

    # Issues
    url(r'^issues/$', raise_issue),
    url(r'^raise_issue/$', raise_issue),
    url(r'^insert_issue/$', insert_issue),
    url(r'^view_issues/$', view_issues),
    url(r'^results_issue/$', results_issue),
    url(r'^resolved_issues/$', resolved_issues),
    url(r'^edit_issue/$', edit_issue),
    url(r'^update_issues/$', update_issues),
    url(r'^display_resolved/?$', display_resolved),
    url(r'^configurations/$', configurations),
    url(r'^save_groups/$', save_groups),

]

#urlpatterns += patterns('miebach_admin.views',
urlpatterns += [
    # Error Pages
    url(r'^errorpage/$', errorpage),
    url(r'^print_excel/$', print_excel),

    # Manage Users
    url(r'^manage_users/$', manage_users),
    url(r'^get_user_data/$', get_user_data),
    url(r'^add_user_data/$', add_user_data),
    url(r'^add_user/$', add_user),
    url(r'^add_group_data/$', add_group_data),
    url(r'^add_group/$', add_group),
    url(r'^update_user/$', update_user),
    url(r'^enable_mail_reports/$', enable_mail_reports),

    url(r'^webhook/$', webhook),
    url(r'^mail_report_configuration/$', mail_report_configuration),
    url(r'^api/', include(api_calls_urls)),
    url(r'^rest_api/', include(rest_api_urls)),

    # POS
    url('^customers/$', get_customer_all_data),
    url('^get_sku_total_data/$', get_sku_total_data),
    url('^validate_sales_person/$', validate_sales_person),
    url('^update_returns_data/$', update_returns_data),
    url('^pos_tax_inclusive/$', pos_tax_inclusive),

    # Multiuploader
    url('^image_upload/$', image_upload),
    url('^upload_images/$', upload_images),

]
#+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
