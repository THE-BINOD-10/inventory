from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = patterns('rest_api.views',

    # Login and logout
    url(r'^wms_login/$', 'wms_login'),
    url(r'^status/$', 'status'),
    url(r'^logout/$', 'logout'),
    url(r'^get_trial_user_data/$', 'get_trial_user_data'),
    url(r'^sku_master/$', 'sku_master'),
    url(r'^location_master/$', 'location_master'),
    url(r'^results_data/$', 'results_data'),
    url(r'^home/$', 'home'),
    url(r'^get_update_setup_state/$', 'get_update_setup_state'),
    url(r'^load_demo_data/$', 'load_demo_data'),
    url(r'^clear_demo_data/$', 'clear_demo_data'),

    #Dashboard
    url(r'^dashboard/$', 'dashboard'),
    url(r'^daily_stock_report/$', 'daily_stock_report'),

    # Master
    url(r'^get_sku_data/$','get_sku_data'),
    url(r'^update_sku/$','update_sku'),
    url(r'^get_supplier_update/$','get_supplier_update'),
    url(r'^get_bom_data/$','get_bom_data'),
    url(r'^update_supplier_values/$', 'update_supplier_values'),
    url(r'^insert_supplier/$', 'insert_supplier'),
    url(r'^update_sku_supplier_values/$', 'update_sku_supplier_values'),
    url(r'^insert_mapping/$', 'insert_mapping'),
    url(r'^update_customer_values/$', 'update_customer_values'),
    url(r'^insert_customer/$', 'insert_customer'),
    url(r'^insert_customer_sku/$', 'insert_customer_sku'),
    url(r'^update_customer_sku_mapping/$', 'update_customer_sku_mapping'),
    url(r'^insert_bom_data/$', 'insert_bom_data'),
    url(r'^insert_discount/$', 'insert_discount'),
    url(r'^add_warehouse_user/$', 'add_warehouse_user'),
    url(r'^update_warehouse_user/$', 'update_warehouse_user'),
    url(r'^get_warehouse_user_data/$', 'get_warehouse_user_data'),
    url(r'^create_user/$', 'create_user'),
    url(r'^get_supplier_list/$', 'get_supplier_list'),
    url(r'^search_customer_sku_mapping/$', 'search_customer_sku_mapping'),
    url(r'^delete_bom_data/$', 'delete_bom_data'),
    url(r'^delete_market_mapping/$', 'delete_market_mapping'),
    url(r'^quality_check_data/$', 'quality_check_data'),
    url(r'^check_wms_qc/$', 'check_wms_qc'),
    url(r'^confirm_quality_check/$', 'confirm_quality_check'),
    url(r'^get_vendor_data/$', 'get_vendor_data'),
    url(r'^update_vendor_values/$', 'update_vendor_values'),
    url(r'^insert_vendor/$', 'insert_vendor'),
    url(r'^add_zone/$', 'add_zone'),
    url(r'^add_location/$', 'add_location'),
    url(r'^update_location/$', 'update_location'),
    url(r'^get_zones_list/$', 'get_zones_list'),
    url(r'^insert_sku/$', 'insert_sku'),
    url(r'^upload_images/$', 'upload_images'),
    url(r'^get_sku_field_names/$', 'get_sku_field_names'),
    url(r'^create_custom_sku_template/$', 'create_custom_sku_template'),
    url(r'^update_custom_sku_template/$', 'update_custom_sku_template'),
    url(r'^delete_product_attribute/$', 'delete_product_attribute'),
    url(r'^add_size/$', 'add_size'),
    url(r'^update_size/$', 'update_size'),

    # Inbound
    url(r'^generated_po_data/$', 'generated_po_data'),
    url(r'^validate_wms/$', 'validate_wms'),
    url(r'^modify_po_update/$', 'modify_po_update'),
    url(r'^confirm_po/$', 'confirm_po'),
    url(r'^confirm_po1/$', 'confirm_po1'),
    url(r'^delete_po_group/$', 'delete_po_group'),
    url(r'^confirm_add_po/$', 'confirm_add_po'),
    url(r'^raise_po_toggle/$', 'raise_po_toggle'),
    url(r'^get_mapping_values/$', 'get_mapping_values'),
    url(r'^add_po/$', 'add_po'),
    url(r'^insert_inventory_adjust/$', 'insert_inventory_adjust'),
    url(r'^delete_po/$', 'delete_po'),
    url(r'^search_supplier/$', 'search_supplier'),
    url(r'^search_vendor/$', 'search_vendor'),
    url(r'^search_wms_codes/$', 'search_wms_codes'),
    url(r'^get_supplier_data/$', 'get_supplier_data'),
    url(r'^update_putaway/$', 'update_putaway'),
    url(r'^close_po/$', 'close_po'),
    url(r'^check_returns/$', 'check_returns'),
    url(r'^check_sku/$', 'check_sku'),
    url(r'^confirm_sales_return/$', 'confirm_sales_return'),
    url(r'^get_received_orders/$', 'get_received_orders'),
    url(r'^putaway_data/$', 'putaway_data'),
    url(r'^raise_st_toggle/$', 'raise_st_toggle'),
    url(r'^save_st/$', 'save_st'),
    url(r'^update_raised_st/$', 'update_raised_st'),
    url(r'^confirm_st/$', 'confirm_st'),
    url(r'^get_po_data/$', 'get_po_data'),
    url(r'^get_so_data/$', 'get_so_data'),
    url(r'^get_suppliers_data/$', 'get_suppliers_data'),
    url(r'^order_status/$', 'order_status'),
    url(r'^check_serial_exists/$', 'check_serial_exists'),
    url(r'^returns_putaway_data/$', 'returns_putaway_data'),
    url(r'^check_imei_exists/$', 'check_imei_exists'),
    url(r'^confirm_grn/$', 'confirm_grn'),
    url(r'^transfer_order/$', 'transfer_order'),
    url(r'^batch_transfer_order/$', 'batch_transfer_order'),
    url(r'^generate_picklist/$', 'generate_picklist'),
    url(r'^st_generate_picklist/$', 'st_generate_picklist'),
    url(r'^confirm_vendor_received/$', 'confirm_vendor_received'),
    url(r'^track_orders/$', 'track_orders'),
    url(r'^cancelled_putaway_data/$', 'cancelled_putaway_data'),
    url(r'^get_location_capacity/$', 'get_location_capacity'),

    # Production
    url(r'^generated_jo_data/$', 'generated_jo_data'),
    url(r'^save_jo/$', 'save_jo'),
    url(r'^delete_jo/$', 'delete_jo'),
    url(r'^confirm_jo/$', 'confirm_jo'),
    url(r'^get_material_codes/$', 'get_material_codes'),
    url('^jo_generate_picklist/$', 'jo_generate_picklist'),
    url(r'^view_rm_picklist/$', 'view_rm_picklist'),
    url(r'^rm_picklist_confirmation/$', 'rm_picklist_confirmation'),
    url(r'^view_confirmed_jo/$', 'view_confirmed_jo'),
    url(r'^confirmed_jo_data/$', 'confirmed_jo_data'),
    url(r'^save_receive_jo/$', 'save_receive_jo'),
    url(r'^confirm_jo_grn/$', 'confirm_jo_grn'),
    url(r'^received_jo_data/$', 'received_jo_data'),
    url(r'^jo_putaway_data/$', 'jo_putaway_data'),
    url(r'^check_imei/$', 'check_imei'),
    url(r'^delete_st/$', 'delete_st'),
    url(r'^confirm_transfer/$', 'confirm_transfer'),
    url(r'^delete_jo_group/$', 'delete_jo_group'),
    url(r'^confirm_jo_group/$', 'confirm_jo_group'),
    url(r'^print_rm_picklist/$', 'print_rm_picklist'),
    url(r'^generate_rm_po_data/$', 'generate_rm_po_data'),
    url(r'^confirm_back_order/$', 'confirm_back_order'),
    url(r'^generate_rm_rwo_data/$', 'generate_rm_rwo_data'),
    url(r'^save_rwo/$', 'save_rwo'),
    url(r'^confirm_rwo/$', 'confirm_rwo'),
    url(r'^saved_rwo_data/$', 'saved_rwo_data'),
    url(r'^generate_vendor_picklist/$', 'generate_vendor_picklist'),
    url(r'^get_vendor_types/$', 'get_vendor_types'),

    # Stock Locator
    url(r'^insert_move_inventory/$', 'insert_move_inventory'),
    url(r'^confirm_cycle_count/$', 'confirm_cycle_count'),
    url(r'^submit_cycle_count/$', 'submit_cycle_count'),
    url(r'^get_id_cycle/$', 'get_id_cycle'),
    url(r'^stock_summary_data/$', 'stock_summary_data'),
    url(r'^confirm_move_inventory/$', 'confirm_move_inventory'),
    url(r'^confirm_inventory_adjustment/$', 'confirm_inventory_adjustment'),
    url(r'^delete_inventory/$', 'delete_inventory'),

    # OutBound
    url(r'^batch_generate_picklist/$', 'batch_generate_picklist'),
    url(r'^picklist_confirmation/$', 'picklist_confirmation'),
    url(r'^view_picklist/$', 'view_picklist'),
    url(r'^view_picked_orders/$', 'view_picked_orders'),
    url(r'^get_customer_sku/$', 'get_customer_sku'),
    url(r'^print_picklist_excel/$', 'print_picklist_excel'),
    url(r'^print_picklist/$', 'print_picklist'),
    url('^marketplace_segregation/$', 'marketplace_segregation'),
    url('^get_customer_data/$', 'get_customer_data'),
    url('^insert_order_data/$', 'insert_order_data'),
    url('^get_warehouses_list/$', 'get_warehouses_list'),
    url('^create_stock_transfer/$', 'create_stock_transfer'),
    url('^get_marketplaces_list/$', 'get_marketplaces_list'),
    url('^generate_po_data/$', 'generate_po_data'),
    url('^generate_jo_data/$', 'generate_jo_data'),
    url('^shipment_info/$', 'shipment_info'),
    url('^insert_shipment_info/$', 'insert_shipment_info'),
    url('^shipment_info_data/$', 'shipment_info_data'),
    url('^update_shipment_status/$', 'update_shipment_status'),
    url('^print_shipment/$', 'print_shipment'),
    url('^get_sku_categories/$', 'get_sku_categories'),
    url('^get_sku_catalogs/$', 'get_sku_catalogs'),
    url('^get_sku_variants/$', 'get_sku_variants'),
    url('^generate_order_invoice/$', 'generate_order_invoice'),
    url('^get_product_properties/$', 'get_product_properties'),
    url(r'^create_custom_sku/$', 'create_custom_sku'),
    url(r'^generate_order_jo_data/$', 'generate_order_jo_data'),
    url(r'^search_customer_data/$', 'search_customer_data'),
    url(r'^generate_order_po_data/$', 'generate_order_po_data'),
    url(r'^get_view_order_details/$', 'get_view_order_details'),
    url(r'^get_stock_location_quantity/$', 'get_stock_location_quantity'),
    url(r'^payment_tracker/$', 'payment_tracker'),
    url(r'^get_customer_payment_tracker/$', 'get_customer_payment_tracker'),
    url(r'^get_customer_master_id/$', 'get_customer_master_id'),
    url(r'^search_wms_data/$', 'search_wms_data'),
    url(r'^update_payment_status/$', 'update_payment_status'),

    # Reports
    #url(r'^location_wise_filter/$','location_wise_filter'),
    url(r'^get_report_data/$', 'get_report_data'),
    url(r'^get_supplier_details/$', 'get_supplier_details'),
    url(r'^get_sku_filter/$', 'get_sku_filter'),
    url(r'^get_po_filter/$', 'get_po_filter'),
    url(r'^get_location_filter/$', 'get_location_filter'),
    url(r'^get_receipt_filter/$', 'get_receipt_filter'),
    url(r'^get_dispatch_filter/$', 'get_dispatch_filter'),
    url(r'^get_order_summary_filter/$', 'get_order_summary_filter'),
    url(r'^get_sku_stock_filter/$', 'get_sku_stock_filter'),
    url(r'^get_sales_return_filter/$','get_sales_return_filter'),
    url(r'^get_sku_purchase_filter/$','get_sku_purchase_filter'),
    url(r'^get_inventory_adjust_filter/$','get_inventory_adjust_filter'),
    url(r'^get_inventory_aging_filter/$','get_inventory_aging_filter'),
    url(r'^sku_category_list/$','sku_category_list'),
    url(r'^print_po_reports/$', 'print_po_reports'),
    url(r'^print_sku/$', 'print_sku'),
    url(r'^excel_reports/$', 'excel_reports'),
    url(r'^print_stock_location/$', 'print_stock_location'),
    url(r'^print_receipt_summary/$', 'print_receipt_summary'),
    url(r'^print_dispatch_summary/$', 'print_dispatch_summary'),
    url(r'^print_sku_wise_stock/$', 'print_sku_wise_stock'),
    url(r'^print_sku_wise_purchase/$', 'print_sku_wise_purchase'),
    url(r'^print_supplier_pos/$', 'print_supplier_pos'),
    url(r'^print_sales_returns/$', 'print_sales_returns'),
    url(r'^get_inventory_adjust_filter/$', 'get_inventory_adjust_filter'),
    url(r'^print_adjust_report/$', 'print_adjust_report'),
    url(r'^print_aging_report/$', 'print_aging_report'),
    url(r'^get_stock_summary_report/$', 'get_stock_summary_report'),
    url(r'^print_stock_summary_report/$', 'print_stock_summary_report'),
    url(r'^get_daily_production_report/$', 'get_daily_production_report'),
    url(r'^print_daily_production_report/$', 'print_daily_production_report'),
    url(r'^print_order_summary_report/$', 'print_order_summary_report'),

    #uploads
    url(r'^order_form/$', 'order_form'),
    url(r'^order_upload/$', 'order_upload'),
    url(r'^sku_form/$', 'sku_form'),
    url(r'^sku_upload/$', 'sku_upload'),
    url(r'^inventory_form/$', 'inventory_form'),
    url(r'^inventory_upload/$', 'inventory_upload'),
    url(r'^supplier_form/$', 'supplier_form'),
    url(r'^supplier_upload/$', 'supplier_upload'),
    url(r'^supplier_sku_form/$', 'supplier_sku_form'),
    url(r'^supplier_sku_upload/$', 'supplier_sku_upload'),
    url(r'^location_form/$', 'location_form'),
    url(r'^location_upload/$', 'location_upload'),
    url(r'^purchase_order_form/$', 'purchase_order_form'),
    url(r'^purchase_order_upload/$', 'purchase_order_upload'),
    url(r'^move_inventory_form/$', 'move_inventory_form'),
    url(r'^move_inventory_upload/$', 'move_inventory_upload'),
    url(r'^marketplace_sku_form/$', 'marketplace_sku_form'),
    url(r'^marketplace_sku_upload/$', 'marketplace_sku_upload'),
    url(r'^bom_form/$', 'bom_form'),
    url(r'^bom_upload/$', 'bom_upload'),
    url(r'^combo_sku_form/$', 'combo_sku_form'),
    url(r'^combo_sku_upload/$', 'combo_sku_upload'),
    url(r'^inventory_adjust_form/$', 'inventory_adjust_form'),
    url(r'^inventory_adjust_upload/$', 'inventory_adjust_upload'),
    url(r'vendor_form/$', 'vendor_form'),
    url(r'vendor_upload/$', 'vendor_upload'),
    url(r'customer_form/$', 'customer_form'),
    url(r'customer_upload/$', 'customer_upload'),

    #configurations
    url(r'^configurations/$', 'configurations'),
    url(r'^switches/$', 'switches'),
    url(r'^enable_mail_reports/$', 'enable_mail_reports'),
    url(r'^save_groups/$', 'save_groups'),
    url(r'^update_mail_configuration/$', 'update_mail_configuration'),
    url(r'^send_mail_reports/$', 'send_mail_reports'),
    url(r'^save_stages/$', 'save_stages'),

    #manage users
    url(r'^add_user/$', 'add_user'),
    url(r'^add_group_data/$', 'add_group_data'),
    url(r'^add_group/$', 'add_group'),
    url(r'^get_user_data/$', 'get_user_data'),
    url(r'^update_user/$', 'update_user'),
    url(r'^get_group_data/$', 'get_group_data'),

    #common
    url(r'^set_timezone/$', 'set_timezone'),
    url(r'^get_file_checksum/$', 'get_file_checksum'),
    url(r'^get_file_content/$', 'get_file_content'),

    #Retailone
    url(r'^get_marketplace_data/$', 'get_marketplace_data'),
    url(r'^update_market_status/$', 'update_market_status'),
    url(r'^pull_market_data/$', 'pull_market_data'),
    url(r'^add_market_credentials/$', 'add_market_credentials'),

    #stockone
    url(r'^book_trial/$','book_trial'),
    )
