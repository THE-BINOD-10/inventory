'use strict';

angular.module('urbanApp', ['angularjs-dropdown-multiselect'])
  .controller('ConfigCtrl',['$scope', '$http', '$state', '$compile', 'Session' , 'Auth', '$timeout', 'Service','$rootScope', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, Auth, $timeout, Service,$rootScope, $modal) {
  var vm = this;
  vm.service = Service;
  vm.marketplace_user = (Session.user_profile.user_type == "marketplace_user")? true: false;

  vm.model_data = {
                    'send_message': false, 'batch_switch': false, 'fifo_switch': false, 'show_image': false,'sku_sync': false,
                    'back_order': false, 'use_imei': false, 'pallet_switch': false, 'production_switch': false,'stock_sync': false,
                    'pos_switch': false, 'auto_po_switch': false, 'no_stock_switch': false, 'online_percentage': 0,
                    'mail_alerts': 0, 'prefix': '', 'all_groups': '', 'mail_options': [{'id': 1,'name': 'Default'}],
                    'mail_inputs':[], 'report_freq':'0', 'float_switch': false, 'automate_invoice': false, 'all_stages': '','all_order_fields':'','all_order_sku_fields':'',
                    'show_mrp': false, 'decimal_limit': 1,'picklist_sort_by': false, 'auto_generate_picklist': false,'grn_fields':'', 'po_fields':'', 'rtv_reasons':'',
                    'detailed_invoice': false, 'picklist_options': {}, 'scan_picklist_option':'', 'seller_margin': '',
                    'tax_details':{}, 'hsn_summary': false, 'display_customer_sku': false, 'create_seller_order': false,
                    'invoice_remarks': '','invoice_declaration':'', 'show_disc_invoice': false, 'serial_limit': '',
                    'increment_invoice': false, 'create_shipment_type': false, 'auto_allocate_stock': false,
                    'generic_wh_level': false, 'auto_confirm_po': false, 'create_order_po': false, 'shipment_sku_scan': false,
                    'disable_brands_view': false, 'sellable_segregation': false, 'display_styles_price': false,
                    'display_sku_cust_mapping': false, 'disable_categories_view': false, 'is_portal_lite': false,
                    'invoice_based_payment_tracker': false, 'receive_po_invoice_check': false,
                    'auto_raise_stock_transfer': false, 'inbound_supplier_invoice': false, 'customer_dc': false,
                    'mark_as_delivered': false, 'order_exceed_stock': false, 'receive_po_mandatory_fields': false,
                    'sku_pack_config': false, 'central_order_reassigning':false, 'po_sub_user_prefix': false,
                    'combo_allocate_stock': false, 'sno_in_invoice': false, 'unique_mrp_putaway': false,'block_expired_batches_picklist':false,
                    'generate_delivery_challan_before_pullConfiramation':false,'pos_remarks' :'',
                    'rtv_prefix_code': false, 'dispatch_qc_check':false,'sku_less_than_threshold':false,'decimal_limit_price':2,
                    'non_transacted_skus':false,'all_order_field_options':{}, 'weight_integration_name': '',
                    'update_mrp_on_grn': false,
                    'allow_rejected_serials':false,
                    'loc_serial_mapping_switch':false,
                    'brand_categorization':false,
                    'purchase_order_preview':false,
                    'picklist_sort_by_sku_sequence':false,
                    'stop_default_tax':false,
                    'delivery_challan_terms_condtions': '',
                    'order_prefix': false,
                    'supplier_mapping':false,
                    'show_mrp_grn': false,
                    'display_dc_invoice':false,
                    'display_order_reference':false,
                    'move_inventory_reasons':'',
                    'enable_pending_approval_pos':false,
                    'mandate_invoice_number':false,
                    'enable_pending_approval_prs': false,
                  };
  vm.all_mails = '';
  vm.switch_names = {1:'send_message', 2:'batch_switch', 3:'fifo_switch', 4: 'show_image', 5: 'back_order',
                     6: 'use_imei', 7: 'pallet_switch', 8: 'production_switch', 9: 'pos_switch',
                     10: 'auto_po_switch', 11: 'no_stock_switch', 12:'online_percentage', 13: 'mail_alerts',
                     14: 'invoice_prefix', 15: 'float_switch', 16: 'automate_invoice', 17: 'show_mrp', 18: 'decimal_limit',
                     19: 'picklist_sort_by', 20: 'stock_sync', 21: 'sku_sync', 22: 'auto_generate_picklist',
                     23: 'detailed_invoice', 24: 'scan_picklist_option', 25: 'stock_display_warehouse',
                     27: 'seller_margin', 28: 'style_headers', 29: 'receive_process', 30: 'tally_config', 31: 'tax_details',
                     32: 'hsn_summary', 33: 'display_customer_sku', 34: 'marketplace_model', 35: 'label_generation',
                     36: 'barcode_generate_opt', 37: 'grn_scan_option', 38: 'invoice_titles', 39: 'show_imei_invoice',
                     40: 'display_remarks_mail', 41: 'create_seller_order', 42: 'invoice_remarks', 43: 'show_disc_invoice',
                     44: 'increment_invoice', 45: 'serial_limit', 46: 'create_shipment_type', 47: 'auto_allocate_stock',
                     48: 'priceband_sync', 49: 'generic_wh_level', 50: 'auto_confirm_po', 51: 'create_order_po',
                     52: 'calculate_customer_price', 53: 'shipment_sku_scan', 54: 'disable_brands_view',
                     55: 'sellable_segregation', 56: 'display_styles_price', 57: 'show_purchase_history',
                     58: 'shelf_life_ratio', 59: 'display_sku_cust_mapping',  60: 'disable_categories_view', 61: 'is_portal_lite',
                     62: 'auto_raise_stock_transfer', 63: 'inbound_supplier_invoice', 64: 'customer_dc',
                     65: 'auto_expire_enq_limit', 66: 'invoice_based_payment_tracker', 67: 'receive_po_invoice_check',
                     68: 'mark_as_delivered', 69: 'receive_po_mandatory_fields', 70: 'central_order_mgmt',
                     71: 'order_exceed_stock',72:'invoice_declaration',73:'central_order_reassigning',
                     74: 'sku_pack_config', 75: 'po_sub_user_prefix', 76: 'combo_allocate_stock', 77:'sno_in_invoice',
                     79: 'generate_delivery_challan_before_pullConfiramation', 80: 'unique_mrp_putaway',
                     81: 'rtv_prefix_code',82:'pos_remarks', 83:'dispatch_qc_check', 84:'block_expired_batches_picklist', 85:'non_transacted_skus',
                     86:'sku_less_than_threshold', 87:'decimal_limit_price', 88: 'mandate_sku_supplier', 89: 'update_mrp_on_grn', 90: 'allow_rejected_serials',
                     91: 'weight_integration_name', 92:'repeat_po', 93:'brand_categorization', 94:'loc_serial_mapping_switch', 95:'purchase_order_preview',
                     96:'stop_default_tax', 97:'order_prefix',
                     98: 'delivery_challan_terms_condtions',
                     99: 'supplier_mapping',
                     100: 'show_mrp_grn',
                     101: 'display_dc_invoice',
                     102: 'display_order_reference',
                     103: 'picklist_sort_by_sku_sequence',
                     104: 'mandate_invoice_number',
                     105: 'enable_pending_approval_pos',
                     106: 'enable_pending_approval_prs',
                     }

  vm.check_box_data = [
    {
      name: "Tally Enable/Disable",
      model_name: "tally_config",
      param_no: 30,
      class_name: "fa fa-th",
      display: true
    },
    {
      name: "Auto Generate Picklist",
      model_name: "auto_generate_picklist",
      param_no: 22,
      class_name: "fa fa-envelope-o",
      display: true
    },
    {
      name: "Repeat PO",
      model_name: "repeat_po",
      param_no: 93,
      class_name: "fa fa-refresh",
      display: true
    },
    {
      name: "Batch Processing Required",
      model_name: "batch_switch",
      param_no: 2,
      class_name: "fa fa-th",
      display: true
    },
    {
      name: "First In First Out Required",
      model_name: "fifo_switch",
      param_no: 3,
      class_name: "glyphicon glyphicon-sort",
      display: true
    },
    {
      name: "Location Serial Mapping",
      model_name: "loc_serial_mapping_switch",
      param_no: 94,
      class_name: "glyphicon glyphicon-sort",
      display: true
    },
    {
      name: "Display HSN Summary In Invoice",
      model_name: "hsn_summary",
      param_no: 32,
      class_name: "glyphicon glyphicon-sort",
      display: true
    },
    {
      name: "Display Discount In Invoice",
      model_name: "show_disc_invoice",
      param_no: 43,
      class_name: "glyphicon glyphicon-sort",
      display: true
    },
    {
      name: "Display Customer SKU In Invoice",
      model_name: "display_customer_sku",
      param_no: 33,
      class_name: "glyphicon glyphicon-sort",
      display: true
    },
    {
      name: "Detail Invoice",
      model_name: "detailed_invoice",
      param_no: 23,
      class_name: "fa fa-rupee",
      display: true
    },
    {
      name: "Show MRP In Invoice",
      model_name: "show_mrp",
      param_no: 17,
      class_name: "fa fa-rupee",
      display: true
    },
    {
      name: "Show Images in Picklist",
      model_name: "show_image",
      param_no: 4,
      class_name: "fa fa-file-image-o",
      display: true
    },
    {
      name: "Enable/Disable Cross Stock",
      model_name: "back_order",
      param_no: 5,
      class_name: "fa fa-exchange",
      display: true
    },
    {
      name: "Use Serial Numbers for SKUs",
      model_name: "use_imei",
      param_no: 6,
      class_name: "fa fa-list-ol",
      display: true
    },
    {
      name: "Pallet Enable/Disable",
      model_name: "pallet_switch",
      param_no: 7,
      class_name: "fa fa-archive",
      display: true
    },
    {
      name: "Production Enable/Disable",
      model_name: "production_switch",
      param_no: 8,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "POS Enable/Disable",
      model_name: "pos_switch",
      param_no: 9,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "Auto PO Enable/Disable",
      model_name: "auto_po_switch",
      param_no: 10,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "Auto Confirm PO",
      model_name: "auto_confirm_po",
      param_no: 50,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "Display Place Sample option in Customer Portal",
      model_name: "create_order_po",
      param_no: 51,
      class_name: "fa fa-refresh",
      display: true
    },
    {
      name: "Generate Picklist for out of stock orders",
      model_name: "no_stock_switch",
      param_no: 11,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "Automatic Invoice Generation",
      model_name: "automate_invoice",
      param_no: 16,
      class_name: "fa fa-envelope",
      display: true
    },
    {
      name: "Picklist Sort By Order Sequence",
      model_name: "picklist_sort_by",
      param_no: 19,
      class_name: "fa fa-envelope",
      display: true
    },
    {
      name: "Picklist Sort By SKU Sequence",
      model_name: "picklist_sort_by_sku_sequence",
      param_no: 103,
      class_name: "fa fa-envelope",
      display: true
    },
    {
      name: "Sync WMS Stock Count",
      model_name: "stock_sync",
      param_no: 20,
      class_name: "fa fa-refresh",
      display: true
    },
    {
      name: "Sync SKU b/n Users",
      model_name: "sku_sync",
      param_no: 21,
      class_name: "fa fa-refresh",
      display: true
    },
    {
      name: "sync customer price grid b/n users.",
      model_name: "priceband_sync",
      param_no: 48,
      class_name: "fa fa-refresh",
      display: true
    },
    {
      name: "Label Generation",
      model_name: "label_generation",
      param_no: 35,
      class_name: "fa fa-refresh",
      display: true
    },
    {
      name: "Support Marketplace Model",
      model_name: "marketplace_model",
      param_no: 34,
      class_name: "fa fa-refresh",
      display: true
    },
    {
      name: "Display IMEI Numbers In Invoice",
      model_name: "show_imei_invoice",
      param_no: 39,
      class_name: "fa fa-refresh",
      display: true
    },
    {
      name: "Display Delivery Challan Number In Invoice",
      model_name: "display_dc_invoice",
      param_no: 101,
      class_name: "fa fa-refresh",
      display: true
    },
    {
      name: "Create Seller Order",
      model_name: "create_seller_order",
      param_no: 41,
      class_name: "fa fa-server",
      display: vm.marketplace_user
    },
    {
      name: "Display Remarks in Mail",
      model_name: "display_remarks_mail",
      param_no: 40,
      class_name: "fa fa-envelope",
      display: true
    },
    {
      name: "Decimal Quantity",
      model_name: "float_switch",
      param_no: 15,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "Invoice number generation",
      model_name: "increment_invoice",
      param_no: 44,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "Generic Warehouse Level",
      model_name: "generic_wh_level",
      param_no: 49,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "Shipment using AWB No.",
      model_name: "create_shipment_type",
      param_no: 46,
      class_name: "glyphicon glyphicon-sort",
      display: true
    },
    {
      name: "SKU Scan in Shipment",
      model_name: "shipment_sku_scan",
      param_no: 53,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "Auto allocate stock",
      model_name: "auto_allocate_stock",
      param_no: 47,
      class_name: "glyphicon glyphicon-sort",
      display: true
    },
    {
      name: "Disable Brands View",
      model_name: "disable_brands_view",
      param_no: 54,
      class_name: "glyphicon glyphicon-sort",
      display: true
    },
    {
      name: "Sellable Segregation Enable/Disable",
      model_name: "sellable_segregation",
      param_no: 55,
      class_name: "glyphicon glyphicon-sort",
      display: true
    },
    {
      name: "Display Price in Customer Portal",
      model_name: "display_styles_price",
      param_no: 56,
      class_name: "fa fa-rupee",
      display: true
    },
    {
      name: "Show Purchase History",
      model_name: "show_purchase_history",
      param_no: 57,
      class_name: "fa fa-rupee",
      display: true
    },
    {
      name: "Display Styles from Customer Mapping",
      model_name: "display_sku_cust_mapping",
      param_no: 59,
      class_name: "fa fa-rupee",
      display: true
    },
    {
      name: "Disable Categories View",
      model_name: "disable_categories_view",
      param_no: 60,
      class_name: "glyphicon glyphicon-sort",
      display: true
    },
    {
      name: "Portal Lite",
      model_name: "is_portal_lite",
      param_no: 61,
      class_name: "glyphicon glyphicon-sort",
      display: true
    },
    {
      name: "Auto Raise Stock Transfer Enable/Disable",
      model_name: "auto_raise_stock_transfer",
      param_no: 62,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "Supplier Invoice Enable/Disable",
      model_name: "inbound_supplier_invoice",
      param_no: 63,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "Customer DC Enable/Disable",
      model_name: "customer_dc",
      param_no: 64,
      class_name: "fa fa-server",
      display: true
    },
    {
      name: "Central Order Management",
      model_name: "central_order_mgmt",
      param_no: 70,
      class_name: "fa fa-server",
      display: true
    },
    {
     name: "Alternative Payment Tracker Enable/Disable",
     model_name: "invoice_based_payment_tracker",
     param_no: 66,
     class_name: "fa fa-server",
     display: true
    },
    {
     name: "Check Invoice Value In Receive PO",
     model_name: "receive_po_invoice_check",
     param_no: 67,
     class_name: "fa fa-server",
     display: true
    },
    {
     name: "Enable Ratings",
     model_name: "mark_as_delivered",
     param_no: 68,
     class_name: "fa fa-server",
     display: true
    },
    {
     name: "Restrict order to stock availability in customer portal",
     model_name: "order_exceed_stock",
     param_no: 71,
     class_name: "fa fa-server",
     display: true
    },
    {
      name: "SKU Pack Configuration",
      model_name: "sku_pack_config",
      param_no: 74,
      class_name: "fa fa-server",
      display: true
    },
   {
     name: "Central Order Reassigning",
     model_name: "central_order_reassigning",
     param_no: 73,
     class_name: "fa fa-server",
     display: true
   },
   {
      name: "User Prefix for PO Order ID",
      model_name: "po_sub_user_prefix",
      param_no: 75,
      class_name: "fa fa-server",
      display: true
   },
   {
      name: "Allocate Stock for Combo Products",
      model_name: "combo_allocate_stock",
      param_no: 76,
      class_name: "glyphicon glyphicon-sort",
      display: true
   },
   {
     name: "Sno(Sequence Number) in Invoice",
     model_name: "sno_in_invoice",
     param_no: 77,
     class_name: "fa fa-server",
     display: true
   },
   {
     name: "Unique MRP in Putaway",
     model_name: "unique_mrp_putaway",
     param_no: 80,
     class_name: "fa fa-server",
     display: true
   },
   {
     name: "Generate Delivery Challan Before PullConfiramation",
     model_name: "generate_delivery_challan_before_pullConfiramation",
     param_no: 79,
     class_name: "fa fa-server",
     display: true
   },
   {
    name: "Dispatch QC Check",
    model_name: "dispatch_qc_check",
    param_no: 83,
    class_name: "fa fa-server",
    display: true
  },
  {
    name: "Block Expired Batches In Picklist",
    model_name: "block_expired_batches_picklist",
    param_no: 84,
    class_name: "fa fa-server",
    display: true
  },
  {
    name: "Display NonTransacted SKU's In Stock Ledger",
    model_name: "non_transacted_skus",
    param_no: 85,
    class_name: "fa fa-server",
    display: true
  },
  {
    name: "Notify SKU below Threshold",
    model_name: "sku_less_than_threshold",
    param_no: 86,
    class_name: "fa fa-server",
    display: true
  },
  {
   name: "Mandate Sku Supplier Mapping in PO",
   model_name: "mandate_sku_supplier",
   param_no: 88,
   class_name: "fa fa-server",
   display: true
  },
  {
   name: "Update MRP On GRN",
   model_name: "update_mrp_on_grn",
   param_no: 89,
   class_name: "fa fa-server",
   display: true
  },
  {
   name: "Allow Rejected Serial Numbers",
   model_name: "allow_rejected_serials",
   param_no: 90,
   class_name: "fa fa-server",
   display: true
  },
  {
   name: "Enable Brand Categorization",
   model_name: "brand_categorization",
   param_no: 93,
   class_name: "fa fa-server",
   display: true
  },
  {
   name: "Enable Purchase Order Preview",
   model_name: "purchase_order_preview",
   param_no: 95,
   class_name: "fa fa-server",
   display: true
  },
  {
   name: "Stop Default Tax Type in Create Order",
   model_name: "stop_default_tax",
   param_no: 96,
   class_name: "fa fa-server",
   display: true
  },
  {
   name: "Disable Auto Supplier SKU Mapping",
   model_name: "supplier_mapping",
   param_no: 99,
   class_name: "fa fa-server",
   display: true
  },
  {
    name: "Show MRP in Goods Receipt Note",
    model_name: "show_mrp_grn",
    param_no: 100,
    class_name: "fa fa-rupee",
    display: true
  },
  {
   name: "Display Order Reference in Outbound",
   model_name: "display_order_reference",
   param_no: 102,
   class_name: "fa fa-server",
   display: true
  },
  {
   name: "Mandate Invoice Number in GRN",
   model_name: "mandate_invoice_number",
   param_no: 104,
   class_name: "fa fa-server",
   display: true
  },
  {
   name: "Enable Pending For Approval PRs",
   model_name: "enable_pending_approval_prs",
   param_no: 106,
   class_name: "fa fa-server",
   display: true
  },
  {
   name: "Enable Pending For Approval POs",
   model_name: "enable_pending_approval_pos",
   param_no: 105,
   class_name: "fa fa-server",
   display: true
  },

]

  vm.empty = {};
  vm.message = "";

  vm.save_pos_extra_fields = function(){

    vm.model_data['pos_extra_fields'] = [];
    vm.validation_err = false;
    var input_type = {'Input':'', 'Textarea':''};

    angular.forEach(vm.pos_extra_fields, function(data){

      if (!data.input_type || !data.field_name) {
        vm.service.showNoty('Please fill all the required fields which are selected', 'success', 'topRight');
        vm.validation_err = true;
      } else {
        if (input_type[data.input_type]) {
          input_type[data.input_type] += ','+data.field_name;
        } else {
          input_type[data.input_type] = data.field_name;
        }
      }
    });

    if (!vm.validation_err) {

      vm.model_data['pos_extra_fields'] = vm.pos_extra_fields;
      var send = {'pos_extra_fields':vm.pos_extra_fields};
      vm.service.apiCall("pos_extra_fields/", "POST", input_type).then(function(data) {
        if (data.data = 'Success') {
          Service.showNoty(data.data);
          vm.pos_extra_fields = [{input_type: "",field_name: ""}];
        }
      })
    }
  }
  vm.save_order_options = function(field)
  {
    var send_data = {}
    send_data['order_field_options'] = []
    angular.forEach(vm.model_data.all_order_field_options[field], function(data){

      if (!data.field_name) {
        vm.service.showNoty('Please fill all the required fields which are selected', 'success', 'topRight');
        vm.validation_err = true;
      } else {
        send_data['order_field_options'].push(data.field_name);
      }
    });
    if (!vm.validation_err) {
      send_data['field'] = field
      vm.service.apiCall("save_extra_order_options/", "POST",{'data':JSON.stringify(send_data)}).then(function(data) {
          Service.showNoty(data.data.message);
      })
    }

  }

  vm.pos_extra_fields = [{'input_type': "",'field_name': ""}];
  vm.add_pos_fields = function() {

    vm.pos_extra_fields.push({input_type: "",field_name: ""});
  }

  vm.remove_pos_fields = function(index){

    vm.pos_extra_fields.splice(index,1);
  }
  vm.model_data.all_order_field_options = {}
  vm.add_order_options = function (extra) {
    if (!vm.model_data.all_order_field_options[extra])
    {
       vm.model_data.all_order_field_options[extra]= []
    }
    vm.model_data.all_order_field_options[extra].push({field_name: ""})
  }
 vm.remove_order_options = function (extra,index) {
    vm.model_data.all_order_field_options[extra].splice(index,1)
   }


  vm.switches = switches;
  function switches(value, switch_num) {
    if(vm.switch_names[switch_num] === "auto_raise_stock_transfer" && vm.model_data["auto_po_switch"]) {
      value = false;
      vm.model_data[vm.switch_names[switch_num]] = value;
      Service.showNoty("Auto PO & Auto Raise Stock Transfer can't be enabled simultaneously", 'warning');
      return
    }
    if(vm.switch_names[switch_num] === "auto_po_switch" && vm.model_data["auto_raise_stock_transfer"]) {
      value = false;
      vm.model_data[vm.switch_names[switch_num]] = value;
      Service.showNoty("Auto PO & Auto Raise Stock Transfer can't be enabled simultaneously", 'warning');
      return
    }
    if(vm.switch_names[switch_num] === "sku_less_than_threshold" && vm.model_data["auto_po_switch"]) {
      value = false;
      vm.model_data[vm.switch_names[switch_num]] = value;
      Service.showNoty("Auto PO & Notify SKU below Threshold can't be enabled simultaneously", 'warning');
      return
    }
    if(vm.switch_names[switch_num] === "auto_po_switch" && vm.model_data["sku_less_than_threshold"]) {
      value = false;
      vm.model_data[vm.switch_names[switch_num]] = value;
      Service.showNoty("Auto PO & Notify SKU below Threshold can't be enabled simultaneously", 'warning');
      return
    }
    vm.service.apiCall("switches/?"+vm.switch_names[switch_num]+"="+String(value)).then(function(data){
      if(data.message) {
        Service.showNoty(data.data);
      }
    });
    Session.roles.permissions[vm.switch_names[switch_num]] = value;
    Session.changeUserData();
  }

  vm.alertPopup = function(){
      sweetAlert("Syncing b/n Users will take some time");
  }

  vm.example1model = [{'id': 1,'name': 'Default'}];
  vm.example1data = [];
  vm.show_mail_reports = false;

  vm.toggle_reports = function() {
    if (vm.show_mail_reports) {
      vm.show_mail_reports = false;
    } else {
      vm.show_mail_reports = true;
      $timeout(function () {
        $('#my-select').multiSelect();
        $("html, body").animate({ scrollTop: $(document).height() }, 1000);
      }, 500);
    }
  }
  vm.pr_save = function (data, type) {
    if(type =='save') {
      vm.add_empty_index('', 'save', 'pr_save');
      console.log(vm.model_data['selected_pr_config_data'])
      var toBeUpdateData = vm.model_data['selected_pr_config_data'];
      if (!toBeUpdateData[0].name) {
        Service.showNoty('Enter Configuration name');
      } else if (toBeUpdateData[0].min_Amt > (toBeUpdateData[0].max_Amt ? toBeUpdateData[0].max_Amt : 0)){
        Service.showNoty('Min Amt Should not Exceed Max Amt');
      } else if (!toBeUpdateData[0]['mail_id']['level0']) {
        Service.showNoty('Email required !');
      } else {
        vm.service.apiCall("add_update_pr_config/", "POST", {'data':JSON.stringify(toBeUpdateData), 'type': 'pr_save'}).then(function(data){
          if(data.message) {
            msg = data.data;
            $scope.showNoty();
            Auth.status();
            vm.baseFunction()
            vm.pr_selected = "";
          }
        });
      }
    } else {
      console.log(type)
      var toBeDeleteData = vm.model_data['selected_pr_config_data'];
      vm.service.apiCall("delete_pr_config/", "POST", {'data':JSON.stringify(toBeDeleteData), 'type': 'pr_save'}).then(function(data){
        if(data.message) {
          msg = data.data;
          $scope.showNoty();
          Auth.status();
          vm.baseFunction()
          vm.pr_selected = "";
        }
      });
    }
  }
  vm.actual_pr_save = function (data, type) {
    if(type =='save') {
      vm.add_empty_index('', 'save', 'actual_pr_save');
      console.log(vm.model_data['selected_actual_pr_config_data'])
      var toBeUpdateData = vm.model_data['selected_actual_pr_config_data'];
      if (!toBeUpdateData[0].name) {
        Service.showNoty('Enter Configuration name');
      } else if (toBeUpdateData[0].min_Amt > (toBeUpdateData[0].max_Amt ? toBeUpdateData[0].max_Amt : 0)){
        Service.showNoty('Min Amt Should not Exceed Max Amt');
      } else if (!toBeUpdateData[0]['mail_id']['level0']) {
        Service.showNoty('Email required !');
      } else {
        vm.service.apiCall("add_update_pr_config/", "POST", {'data':JSON.stringify(toBeUpdateData), 'type': 'actual_pr_save'}).then(function(data){
          if(data.message) {
            msg = data.data;
            $scope.showNoty();
            Auth.status();
            vm.baseFunction()
            vm.actual_pr_selected = "";
          }
        });
      }
    } else {
      console.log(type)
      var toBeDeleteData = vm.model_data['selected_actual_pr_config_data'];
      vm.service.apiCall("delete_pr_config/", "POST", {'data':JSON.stringify(toBeDeleteData), 'type': 'actual_pr_save'}).then(function(data){
        if(data.message) {
          msg = data.data;
          $scope.showNoty();
          Auth.status();
          vm.baseFunction()
          vm.actual_pr_selected = "";
        }
      });
    }
  }
  vm.input_fields = ['Input', 'Textarea'];
  vm.service.apiCall("configurations/").then(function(data){
    if(data.message) {
      angular.copy(data.data, vm.model_data);
      vm.model_data["tax_details"] = {'CST': {}};
      vm.model_data['prefix_data'] = [];
      vm.model_data['prefix_dc_data'] = [];
      vm.model_data['prefix_cn_data'] = [];
      angular.forEach(data.data.prefix_data, function(data){
        vm.model_data.prefix_data.push({marketplace_name: data.marketplace, marketplace_prefix: data.prefix,
                                        marketplace_interfix: data.interfix, marketplace_date_type: data.date_type});
      })
      angular.forEach(data.data.prefix_dc_data, function(data){
        vm.model_data.prefix_dc_data.push({marketplace_name: data.marketplace, marketplace_prefix: data.prefix});
      })
      angular.forEach(data.data.prefix_cn_data, function(data){
        vm.model_data.prefix_cn_data.push({marketplace_name: data.marketplace, marketplace_prefix: data.prefix});
      })
      angular.forEach(vm.model_data, function(value, key) {
        if (value == "true") {
          vm.model_data[key] = Boolean(true);
        } else if (value == "false") {
          vm.model_data[key] = Boolean(false);
        }
      });
    }
  });

  vm.add_empty_index = function(data, operation, pr_type) {
    var prConfigData = vm.model_data['selected_pr_config_data'];
    var totalData = vm.model_data['total_pr_config_ranges'];
    if(pr_type == 'actual_pr_save'){
      prConfigData = vm.model_data['selected_actual_pr_config_data'];
      totalData = vm.model_data['total_actual_pr_config_ranges'];
    }
    if (operation == 'delete') {
      angular.forEach(prConfigData, function(tuple, index){
        if(data.name == tuple.name) {
          prConfigData.splice(index,1)        
        }
      })
    } else if (operation == 'add_email' || operation == 'remove_email') {
      angular.forEach(prConfigData, function(tuple, index){
        if(data.name == tuple.name) {
          if (operation == 'add_email') {
            tuple['mail_id']['level'+Object.keys(tuple['mail_id']).length] = ""
          } else {
            if (Object.keys(tuple['mail_id']).length > 1) {
              delete tuple['mail_id'][Object.keys(tuple['mail_id'])[Object.keys(tuple['mail_id']).length -1]]
            }
          }
        }
      })
    } else if (operation == 'save') {
      angular.forEach(prConfigData, function(tuple, index){
        angular.forEach(Object.keys(tuple['mail_id']), function(level) {
          var values = tuple.name+level
          var emails = $("."+values).val();
          tuple['mail_id'][level] = emails;
        })
      })
    } else {
      var empty_dict = {'name': '', 'min_Amt': 0, 'max_Amt': '', 'mail_id': {'level0': ""}, 'remove': 0};
      if (prConfigData.length != 0) {
        var check_last_record = prConfigData[prConfigData.length -1]
        if (check_last_record['name'] == '') {
          Service.showNoty('please Fill Available One');
        }
      } else {
        if (totalData[totalData.length -1]) {
          var min_amt = totalData[totalData.length -1]['max_Amt']+1;
          empty_dict['min_Amt'] = min_amt;
          prConfigData.push(empty_dict);
          if(pr_type == 'actual_pr_save'){
            vm.actual_pr_add_show = true;
          } else {
            vm.pr_add_show = true;
          }
        } else {
          prConfigData.push(empty_dict);
          if(pr_type == 'actual_pr_save'){
            vm.actual_pr_add_show = true;
          } else {
            vm.pr_add_show = true;
          }
        }
      }
    }
  }
  vm.input_fields = ['Input', 'Textarea'];

  // vm.service.apiCall("configurations/").then(function(data){
  //   if(data.message) {
  //     angular.copy(data.data, vm.model_data);
  //     vm.model_data["tax_details"] = {'CST': {}};
  //     vm.model_data['prefix_data'] = [];
  //     vm.model_data['prefix_dc_data'] = [];
  //     vm.model_data['pr_approvals_conf_data'] = [];
  //     vm.model_data['selected_pr_config_data'] = [];
  //     vm.model_data['total_pr_config_ranges'] = [];
  //     angular.forEach(data.data.prefix_data, function(data){
  //       vm.model_data.prefix_data.push({marketplace_name: data.marketplace, marketplace_prefix: data.prefix,
  //                                       marketplace_interfix: data.interfix, marketplace_date_type: data.date_type});
  //     })
  //     angular.forEach(data.data.prefix_dc_data, function(data){
  //       vm.model_data.prefix_dc_data.push({marketplace_name: data.marketplace, marketplace_prefix: data.prefix});
  //     })
  //     angular.forEach(data.data.pr_approvals_conf_data, function(data){
  //       var data_dict = {}
  //       data_dict['name'] = data.name;
  //       data_dict['min_Amt'] = data.min_Amt;
  //       data_dict['max_Amt'] = data.max_Amt;
  //       data_dict['mail_id'] = data.mail_id;
  //       vm.model_data.total_pr_config_ranges.push(data_dict)
  //       vm.model_data.pr_approvals_conf_data.push({pr_name: data.name});
  //     })

  //     angular.forEach(vm.model_data, function(value, key) {
  //       if (value == "true") {
  //         vm.model_data[key] = Boolean(true);
  //       } else if (value == "false") {
  //         vm.model_data[key] = Boolean(false);
  //       }
  //     });
  //     vm.model_data["mail_alerts"] = parseInt(vm.model_data["mail_alerts"]);
  //     vm.model_data["online_percentage"] = parseInt(vm.model_data["online_percentage"]);
  //     vm.model_data["order_header_inputs"] = Session.roles.permissions["order_headers"].split(",")
  //     $timeout(function () {
  //       $('.selectpicker').selectpicker();
  //       $(".mail_notifications .bootstrap-select").change(function(){
  //         var data = $(".mail_notifications .selectpicker").val();
  //         var send = "";
  //         if (data) {
  //           for(var i = 0; i < data.length; i++) {
  //             send += data[i].slice(1)+",";
  //           }
  //         }
  //         vm.service.apiCall("enable_mail_reports/?data="+send.slice(0,-1)).then(function(data){
  //           if(data.message) {
  //             Auth.update();
  //           }
  //         });
  //         var build_data = send.split(",");
  //         var temp = [];
  //         angular.forEach(build_data, function(item){
  //           if(item) {
  //             temp.push(vm.model_data.mail_options[item]);
  //           }
  //         })
  //         vm.model_data.mail_inputs = temp;
  //       })

  //       $(".create_orders .bootstrap-select").change(function(){
  //         var data = $(".create_orders .selectpicker").val();
  //         var send = "";
  //         if (data) {
  //           for(var i = 0; i < data.length; i++) {
  //             send += data[i].slice(1)+",";
  //           }
  //         }
  //         vm.service.apiCall("switches/?order_headers="+send.slice(0,-1)).then(function(data){
  //           if(data.message) {
  //             Auth.update();
  //           }
  //         });
  //       })
  //     }, 500);
  //     $(".sku_groups").importTags(vm.model_data.all_groups);
  //     $(".stages").importTags(vm.model_data.all_stages);
  //     $(".order_fields").importTags(vm.model_data.all_order_fields);
  //     $(".order_sku_fields").importTags(vm.model_data.all_order_sku_fields);
  //     $(".grn_fields").importTags(vm.model_data.grn_fields);
  //     $(".po_fields").importTags(vm.model_data.po_fields);
  //     $(".rtv_reasons").importTags(vm.model_data.rtv_reasons);
  //     $(".move_inventory_reasons").importTags(vm.model_data.move_inventory_reasons);
  //     vm.model_data.all_order_fields_list = vm.model_data.all_order_fields.split(",")
  //     $(".extra_view_order_status").importTags(vm.model_data.extra_view_order_status);
  //     $(".bank_option_fields").importTags(vm.model_data.bank_option_fields);
  //     $(".invoice_types").importTags(vm.model_data.invoice_types);
  //     $(".mode_of_transport").importTags(vm.model_data.mode_of_transport||'');
  //     $(".sales_return_reasons").importTags(vm.model_data.sales_return_reasons||'');
  //     if (vm.model_data.invoice_titles) {
  //       $(".titles").importTags(vm.model_data.invoice_titles);
  //     }
  //     $('#my-select').multiSelect();
  //     vm.getRemarks(vm.model_data.invoice_remarks)
  //     vm.getDeclaration(vm.model_data.invoice_declaration)
  //     vm.getPosremarks(vm.model_data.pos_remarks)
  //     vm.getDeliveryChallanterms(vm.model_data.delivery_challan_terms_condtions)
  //   }
  // })
  vm.baseFunction = function(){
    console.log("Base Fucntion Called")
    vm.service.apiCall("configurations/").then(function(data){
      if(data.message) {
        angular.copy(data.data, vm.model_data);
        vm.model_data["tax_details"] = {'CST': {}};
        vm.model_data['prefix_data'] = [];
        vm.model_data['prefix_dc_data'] = [];
        vm.model_data['pr_approvals_conf_data'] = [];
        vm.model_data['actual_pr_approvals_conf_data'] = [];
        vm.model_data['selected_pr_config_data'] = [];
        vm.model_data['selected_actual_pr_config_data'] = [];
        vm.model_data['total_pr_config_ranges'] = [];
        vm.model_data['total_actual_pr_config_ranges'] = [];
        angular.forEach(data.data.prefix_data, function(data){
          vm.model_data.prefix_data.push({marketplace_name: data.marketplace, marketplace_prefix: data.prefix,
                                          marketplace_interfix: data.interfix, marketplace_date_type: data.date_type});
        })
        angular.forEach(data.data.prefix_dc_data, function(data){
          vm.model_data.prefix_dc_data.push({marketplace_name: data.marketplace, marketplace_prefix: data.prefix});
        })
        if (data.data.pr_approvals_conf_data.length > 0) {
          var temp_length = data.data.pr_approvals_conf_data.length;
          angular.forEach(data.data.pr_approvals_conf_data, function(data, index){
            var data_dict = {}
            data_dict['name'] = data.name;
            data_dict['min_Amt'] = data.min_Amt;
            data_dict['max_Amt'] = data.max_Amt;
            data_dict['mail_id'] = data.mail_id;
            temp_length == (index+1) ? data_dict['remove'] = 1 : data_dict['remove'] = 0;
            vm.model_data.total_pr_config_ranges.push(data_dict)
            vm.model_data.pr_approvals_conf_data.push({pr_name: data.name});
          })
        }
        if (data.data.actual_pr_approvals_conf_data.length > 0) {
          var temp_length = data.data.actual_pr_approvals_conf_data.length;
          angular.forEach(data.data.actual_pr_approvals_conf_data, function(data, index){
            var data_dict = {}
            data_dict['name'] = data.name;
            data_dict['min_Amt'] = data.min_Amt;
            data_dict['max_Amt'] = data.max_Amt;
            data_dict['mail_id'] = data.mail_id;
            temp_length == (index+1) ? data_dict['remove'] = 1 : data_dict['remove'] = 0;
            vm.model_data.total_actual_pr_config_ranges.push(data_dict)
            vm.model_data.actual_pr_approvals_conf_data.push({pr_name: data.name});
          })
        }
        angular.forEach(vm.model_data, function(value, key) {
          if (value == "true") {
            vm.model_data[key] = Boolean(true);
          } else if (value == "false") {
            vm.model_data[key] = Boolean(false);
          }
        });
        vm.model_data["mail_alerts"] = parseInt(vm.model_data["mail_alerts"]);
        vm.model_data["online_percentage"] = parseInt(vm.model_data["online_percentage"]);
        vm.model_data["order_header_inputs"] = Session.roles.permissions["order_headers"].split(",")
        $timeout(function () {
          $('.selectpicker').selectpicker();
          $(".mail_notifications .bootstrap-select").change(function(){
            var data = $(".mail_notifications .selectpicker").val();
            var send = "";
            if (data) {
              for(var i = 0; i < data.length; i++) {
                send += data[i].slice(1)+",";
              }
            }
            vm.service.apiCall("enable_mail_reports/?data="+send.slice(0,-1)).then(function(data){
              if(data.message) {
                Auth.update();
              }
            });
            var build_data = send.split(",");
            var temp = [];
            angular.forEach(build_data, function(item){
              if(item) {
                temp.push(vm.model_data.mail_options[item]);
              }
            })
            vm.model_data.mail_inputs = temp;
          })

          $(".create_orders .bootstrap-select").change(function(){
            var data = $(".create_orders .selectpicker").val();
            var send = "";
            if (data) {
              for(var i = 0; i < data.length; i++) {
                send += data[i].slice(1)+",";
              }
            }
            vm.service.apiCall("switches/?order_headers="+send.slice(0,-1)).then(function(data){
              if(data.message) {
                Auth.update();
              }
            });
          })
        }, 500);
        $(".sku_groups").importTags(vm.model_data.all_groups);
        $(".stages").importTags(vm.model_data.all_stages);
        $(".order_fields").importTags(vm.model_data.all_order_fields);
        $(".order_sku_fields").importTags(vm.model_data.all_order_sku_fields);
        $(".grn_fields").importTags(vm.model_data.grn_fields);
        $(".po_fields").importTags(vm.model_data.po_fields);
        $(".rtv_reasons").importTags(vm.model_data.rtv_reasons);
        $(".move_inventory_reasons").importTags(vm.model_data.move_inventory_reasons);
        vm.model_data.all_order_fields_list = vm.model_data.all_order_fields.split(",")
        $(".extra_view_order_status").importTags(vm.model_data.extra_view_order_status);
        $(".bank_option_fields").importTags(vm.model_data.bank_option_fields);
        $(".invoice_types").importTags(vm.model_data.invoice_types);
        $(".mode_of_transport").importTags(vm.model_data.mode_of_transport||'');
        $(".sales_return_reasons").importTags(vm.model_data.sales_return_reasons||'');
        if (vm.model_data.invoice_titles) {
          $(".titles").importTags(vm.model_data.invoice_titles);
        }
        $('#my-select').multiSelect();
        vm.getRemarks(vm.model_data.invoice_remarks)
        vm.getDeclaration(vm.model_data.invoice_declaration)
        vm.getPosremarks(vm.model_data.pos_remarks)
        vm.getDeliveryChallanterms(vm.model_data.delivery_challan_terms_condtions)
      }
    })    
  }

  vm.baseFunction();
  vm.mail_alerts_change = function(url, selector, item) {
    var data = $(selector).val();
    var send = "";
    for(var i = 0; i < data.length; i++) {
      send += data[i].slice(1)+",";
    }
    vm.service.apiCall(url+"/?"+ item +"="+send.slice(0,-1)).then(function(data){
      if(data.message) {
        Auth.status();
      }
    });
  }

  vm.multi_select_switch = function(selector, number) {
    var data = $(selector).val();
    if(!data) {
      data = [];
    }
    var send = data.join(",");
    vm.switches(send, number);
  }

  vm.check_selected = function(opt, name) {
    if(!vm.model_data[name]) {
      return false;
    } else {
      return (vm.model_data[name].indexOf(opt) > -1) ? true: false;
    }
  }

  vm.check_mail = function(opt) {
    return (vm.model_data.reports_data.indexOf(opt) > -1) ? true: false;
  }

  vm.update_sku_groups = function() {
    var data = $("#tags").val();
    vm.service.apiCall("save_groups?sku_groups="+data).then(function(data){
      if(data.message) {
        msg = data.data;
        $scope.showNoty();
        Auth.status();
      }
    });
  }

  vm.update_extra_order_status = function() {
    var data = $(".extra_view_order_status").val();
    vm.service.apiCall("switches?extra_view_order_status="+data).then(function(data){
      if(data.message) {
        msg = data.data;
        $scope.showNoty();
        Auth.status();
      }
    });
  }

  vm.update_bank_option_fields = function() {
    var data = $(".bank_option_fields").val();
    vm.service.apiCall("switches?bank_option_fields="+data).then(function(data){
      if(data.message) {
        msg = data.data;
        $scope.showNoty();
        Auth.status();
      }
    });
  }

  vm.update_invoice_type = function() {
    var data = $(".invoice_types").val();
    vm.service.apiCall("switches?invoice_types="+data).then(function(data){
      if(data.message) {
        msg = data.data;
        $scope.showNoty();
        Auth.status();
      }
    });
  }

  vm.update_mode_of_transport = function() {
    var data = $(".mode_of_transport").val();
    vm.service.apiCall("switches?mode_of_transport="+data).then(function(data){
      if(data.message) {
        msg = data.data;
        $scope.showNoty();
        Auth.status();
      }
    });
  }

  vm.update_sales_return_reasons = function() {
    var data = $(".sales_return_reasons").val();
    vm.service.apiCall("switches?sales_return_reasons="+data).then(function(data){
      if(data.message) {
        msg = data.data;
        $scope.showNoty();
        Auth.status();
      }
    });
  }

  vm.update_stages = function() {
    var data = $(".stages").val();
    vm.service.apiCall("save_stages/?stage_names="+data).then(function(data){
      if(data.message) {
        msg = data.data;
        $scope.showNoty();
        Auth.status();
      }
    });
  }
  vm.update_extra_order_sku_fields = function() {
    var data = $(".order_sku_fields").val();
    vm.service.apiCall("save_order_sku_extra_fields/?extra_order_sku_fields="+data).then(function(data){
      if(data.message) {
        msg = data.data;
        vm.model_data.all_order_sku_fields = $(".order_sku_fields").val().split(',');
        $scope.showNoty();
        Auth.status();
      }
    });
  }
  vm.update_extra_central_order_fields = function() {
    var data = $(".order_fields").val();
    vm.service.apiCall("save_order_extra_fields/?extra_order_fields="+data).then(function(data){
      if(data.message) {
        msg = data.data;
        vm.model_data.all_order_fields_list = $(".order_fields").val().split(',');
        $scope.showNoty();
        Auth.status();
      }
    });
  }
  vm.update_extra_fields = function(fields) {
    var data = $(fields).val();
    vm.service.apiCall("save_config_extra_fields/?config_extra_fields="+data+'&field_type='+fields).then(function(data){
      if(data.message) {
        msg = data.data;
        $scope.showNoty();
        Auth.status();
      }
    });
  }
  vm.update_invoice_titles = function() {
    var data = $(".titles").val();
    vm.switches(data, 38);
    Auth.status();
  }

  vm.update_internal_mails = function() {
    var data = $(".internal_mails").val();
    vm.service.apiCall("get_internal_mails/?internal_mails="+data).then(function(data){
      if(data.message) {
        msg = data.data;
        $scope.showNoty();
        Auth.status();
      }
    });
  }

  vm.save_mail_config = function() {
    var report_selected = [];
    var report_removed = [];
    var data = {};
    var date_val = $($('#datepicker11')[0]).val();
    var selected = $('#ms-my-select').find('.ms-elem-selection.ms-selected').find('span');
    var removed = $('#ms-my-select').find('.ms-elem-selection').not($('.ms-selected')).find('span');
    for(i=0; i<selected.length; i++) {
      report_selected.push($(selected[i]).text());
    }
    for(i=0; i<removed.length; i++) {
      report_removed.push($(removed[i]).text());
    }
    data['selected'] = report_selected;
    data['removed'] = report_removed;
    var mail_to = ""
    angular.forEach($(".mail-to .tagsinput .tag span"),function(data){
      mail_to = mail_to + $(data).text().slice(0,-2)+",";
    })
    if(mail_to) {
      mail_to = mail_to.slice(0,-1)
    }
    data['email'] = mail_to;
    data['frequency'] = $('#days_range').val();
    data['date_val'] = date_val;
    data['range'] = $('.time_data option:selected').val();
    $.ajax({url: Session.url+'update_mail_configuration/',
       method: 'POST',
       data: data,
       xhrFields: {
       withCredentials: true
       },
       'success': function(response) {
         msg = response;
         $scope.showNoty();
         Auth.status();
    }});
  }

  vm.mail_now = function() {
    var mail_to = ""
    angular.forEach($(".mail-to .tagsinput .tag span"),function(data){
      mail_to = mail_to + $(data).text().slice(0,-2)+",";
    })
    if(mail_to) {
       mail_to = mail_to.slice(0,-1)
    }
    vm.service.apiCall("send_mail_reports/?mails="+mail_to).then(function(data){
      if(data.message) {
        msg = data.data;
        $scope.showNoty();
        Auth.status();
      }
    });
  }

  var msg = "message",
      type = "success"
  var $layout = 'topRight';
  $scope.showNoty = function () {

    if (!msg) {
      msg = $scope.getMessage();
    }

    if (!type) {
      type = 'error';
    }

    noty({
      theme: 'urban-noty',
      text: msg,
      type: type,
      timeout: 3000,
      layout: $layout,
      closeWith: ['button', 'click'],
      animation: {
        open: 'in',
        close: 'out',
        easing: 'swing'
      },
    });
  };

  vm.order_manage = function (data) {
    vm.service.showLoader();
    var order_management;
    $.ajax({
      url: Session.url+'order_management_toggle?order_manage='+data,
      method: 'GET',
      xhrFields: {
        withCredentials: true
      },
      'success': function(response) {
        if (data){
            $('#channel_component').removeClass('ng-hide').css('display', 'block');
            order_management = "Order Management Enabled"
            localStorage.setItem("order_management", String(data));
        } else {
            $('#channel_component').addClass('ng-hide').css('display', 'none');
            order_management = "Order Management Disabled"
            localStorage.setItem("order_management", String(data));
        }
        vm.service.showNoty(order_management, 'success', 'topRight');
        vm.service.hideLoader();
      },
      'error': function(response) {
        console.log(response);
        vm.service.hideLoader();
      }
    });
  };


  vm.marketplace_add_show = false;

  vm.saveMarketplace = function(name, value) {

    if(!name) {

      Service.showNoty("Please Enter Name");
      return false;
    } else {
      vm.updateMarketplace(name, value, 'save')
      //vm.switches("{'tax_"+name+"':'"+value+"'}", 31);
      var found = false;
      for(var i = 0; i < vm.model_data.prefix_data.length; i++) {

        if(vm.model_data.prefix_data[i].marketplace_name == vm.model_data.marketplace_name) {

          vm.model_data.prefix_data[i].marketplace_name = vm.model_data.marketplace_name;
          vm.model_data.prefix_data[i].marketplace_prefix = vm.model_data.marketplace_prefix;
          vm.model_data.prefix_data[i].marketplace_interfix = vm.model_data.marketplace_interfix;
          vm.model_data.prefix_data[i].marketplace_date_type = vm.model_data.marketplace_date_type;
          found = true;
          break;
        }
      }
      if(!found) {

        vm.model_data.prefix_data.push({marketplace_name: vm.model_data.marketplace_name,
                                        marketplace_prefix: vm.model_data.marketplace_prefix,
                                        marketplace_interfix: vm.model_data.marketplace_interfix,
                                        marketplace_date_type: vm.model_data.marketplace_date_type});
      }
      vm.marketplace_add_show = false;
      vm.marketplace_selected = "";
      vm.model_data.marketplace_name = "";
      vm.model_data.marketplace_prefix = "";
      vm.model_data.marketplace_interfix = "";
      vm.model_data.marketplace_date_type = "";
      vm.model_data.marketplace_new = true;
    }
  }

  vm.model_data.marketplace_new = true;
  vm.marketplaceSelected = function(name) {

    if (name) {

      for(var i = 0; i < vm.model_data.prefix_data.length; i++) {

        if(vm.model_data.prefix_data[i].marketplace_name == name) {

          vm.model_data.marketplace_name = vm.model_data.prefix_data[i].marketplace_name;
          vm.model_data.marketplace_prefix = vm.model_data.prefix_data[i].marketplace_prefix;
          vm.model_data.marketplace_interfix = vm.model_data.prefix_data[i].marketplace_interfix;
          vm.model_data.marketplace_date_type = vm.model_data.prefix_data[i].marketplace_date_type;
          vm.model_data["marketplace_new"] = false;
          vm.marketplace_add_show = true;
          break;
        }
      }
    } else {

      vm.model_data["marketplace_new"] = true;
      vm.marketplace_add_show = false;
      vm.model_data.marketplace_name = "";
      vm.model_data.marketplace_prefix = "";
    }
  }

  vm.updateMarketplace = function(name, value, type) {

      var send = {marketplace_name : name, marketplace_prefix: value,
                  marketplace_interfix: vm.model_data.marketplace_interfix,
                  marketplace_date_type: vm.model_data.marketplace_date_type}
      if (type != 'save') {
        send['delete'] = true;

        for(var i = 0; i < vm.model_data.prefix_data.length; i++) {

          if(vm.model_data.prefix_data[i].marketplace_name == vm.model_data.marketplace_name) {

            vm.model_data.prefix_data.splice(i, 1);
            break;
          }
        }
        vm.marketplace_add_show = false;
        vm.marketplace_selected = "";
        vm.model_data.marketplace_name = "";
        vm.model_data.marketplace_prefix = "";
        vm.model_data.marketplace_new = true;
      }
      vm.service.apiCall("update_invoice_sequence/", "GET", send).then(function(data) {

        console.log(data);
      })
  }

  vm.saved_marketplaces = [];
  vm.filterMarkeplaces = function() {
    vm.saved_marketplaces = [];
    angular.forEach(vm.model_data.prefix_data, function(data){
      vm.saved_marketplaces.push(data.marketplace_name);
    })
    for(var i=0; i < vm.model_data.marketplaces.length; i++) {
      if (vm.saved_marketplaces.indexOf(vm.model_data.marketplaces[i]) == -1) {
        vm.model_data.marketplace_name = vm.model_data.marketplaces[i];
        break;
      }
    }
  }

  vm.model_data.pr_add_new = true;
  vm.PRSelected = function(name) {
    vm.model_data.selected_pr_config_data = []
    angular.forEach(vm.model_data.total_pr_config_ranges, function(data){
      if (name == data.name) {
        vm.model_data.selected_pr_config_data.push(data);
        vm.pr_add_show = true;
      }
    })
  }

  // vm.model_data.actual_pr_add_new = true;
  vm.ActualPRSelected = function(name) {
    vm.model_data.selected_actual_pr_config_data = []
    angular.forEach(vm.model_data.total_actual_pr_config_ranges, function(data){
      if (name == data.name) {
        vm.model_data.selected_actual_pr_config_data.push(data);
        vm.actual_pr_add_show = true;
      }
    })
  }

  vm.saved_pr_configs = [];
  vm.filterPRConfigs = function() {
    vm.saved_pr_configs = [];
    angular.forEach(vm.model_data.prefix_data, function(data){
      vm.saved_pr_configs.push(data.name);
    })
    for(var i=0; i < vm.model_data.pr_conf_names.length; i++) {
      if (vm.saved_pr_configs.indexOf(vm.model_data.pr_conf_names[i]) == -1) {
        vm.model_data.pr_name = vm.model_data.pr_conf_names[i];
        break;
      }
    }
  }

  vm.saved_actual_pr_configs = [];
  vm.filterActualPRConfigs = function() {
    vm.saved_pr_configs = [];
    angular.forEach(vm.model_data.prefix_data, function(data){
      vm.saved_actual_pr_configs.push(data.name);
    })
    for(var i=0; i < vm.model_data.actual_pr_conf_names.length; i++) {
      if (vm.saved_actual_pr_configs.indexOf(vm.model_data.actual_pr_conf_names[i]) == -1) {
        vm.model_data.actual_pr_name = vm.model_data.pr_conf_names[i];
        break;
      }
    }
  }

  vm.marketplace_add_show_dc = false;
  vm.saveMarketplaceDc = function(name, value) {

    if(!name) {

      Service.showNoty("Please Enter Name");
      return false;
    } else {
      vm.updateMarketplaceDc(name, value, 'save')
      //vm.switches("{'tax_"+name+"':'"+value+"'}", 31);
      var found = false;
      for(var i = 0; i < vm.model_data.prefix_dc_data.length; i++) {

        if(vm.model_data.prefix_dc_data[i].marketplace_name == vm.model_data.marketplace_name) {

          vm.model_data.prefix_dc_data[i].marketplace_name = vm.model_data.marketplace_name;
          vm.model_data.prefix_dc_data[i].marketplace_prefix = vm.model_data.marketplace_prefix;
          vm.model_data.prefix_dc_data[i].marketplace_interfix = vm.model_data.marketplace_interfix;
          vm.model_data.prefix_dc_data[i].marketplace_date_type = vm.model_data.marketplace_date_type;
          found = true;
          break;
        }
      }
      if(!found) {

        vm.model_data.prefix_dc_data.push({marketplace_name: vm.model_data.marketplace_name,
                                        marketplace_prefix: vm.model_data.marketplace_prefix,
                                        marketplace_interfix: vm.model_data.marketplace_interfix,
                                        marketplace_date_type: vm.model_data.marketplace_date_type});
      }
      vm.marketplace_add_show_dc = false;
      vm.marketplace_selected_dc = "";
      vm.model_data.marketplace_name = "";
      vm.model_data.marketplace_prefix = "";
      vm.model_data.marketplace_interfix = "";
      vm.model_data.marketplace_date_type = "";
      vm.model_data.marketplace_new = true;
    }
  }

   vm.marketplaceSelectedDc = function(name) {

    if (name) {

      for(var i = 0; i < vm.model_data.prefix_dc_data.length; i++) {

        if(vm.model_data.prefix_dc_data[i].marketplace_name == name) {

          vm.model_data.marketplace_name = vm.model_data.prefix_dc_data[i].marketplace_name;
          vm.model_data.marketplace_prefix = vm.model_data.prefix_dc_data[i].marketplace_prefix;
          vm.model_data.marketplace_interfix = vm.model_data.prefix_dc_data[i].marketplace_interfix;
          vm.model_data.marketplace_date_type = vm.model_data.prefix_dc_data[i].marketplace_date_type;
          vm.model_data["marketplace_new"] = false;
          vm.marketplace_add_show_dc = true;
          break;
        }
      }
    } else {

      vm.model_data["marketplace_new"] = true;
      vm.marketplace_add_show = false;
      vm.model_data.marketplace_name = "";
      vm.model_data.marketplace_prefix = "";
    }
  }

  vm.updateMarketplaceDc = function(name, value, type) {

      var send = {marketplace_name : name, marketplace_prefix: value,
                  marketplace_interfix: vm.model_data.marketplace_interfix,
                  marketplace_date_type: vm.model_data.marketplace_date_type}
      if (type != 'save') {
        send['delete'] = true;

        for(var i = 0; i < vm.model_data.prefix_dc_data.length; i++) {

          if(vm.model_data.prefix_dc_data[i].marketplace_name == vm.model_data.marketplace_name) {

            vm.model_data.prefix_dc_data.splice(i, 1);
            break;
          }
        }
        vm.marketplace_add_show_dc = false;
        vm.marketplace_selected_dc = "";
        vm.model_data.marketplace_name = "";
        vm.model_data.marketplace_prefix = "";
        vm.model_data.marketplace_new = true;
      }
      vm.service.apiCall("update_dc_sequence/", "GET", send).then(function(data) {

        console.log(data);
      })
  }
  vm.saved_marketplaces = [];
  vm.filterMarkeplacesDc = function() {
    vm.saved_marketplaces = [];
    angular.forEach(vm.model_data.prefix_dc_data, function(data){
      vm.saved_marketplaces.push(data.marketplace_name);
    })
    for(var i=0; i < vm.model_data.marketplaces.length; i++) {
      if (vm.saved_marketplaces.indexOf(vm.model_data.marketplaces[i]) == -1) {
        vm.model_data.marketplace_name = vm.model_data.marketplaces[i];
        break;
      }
    }
  }













  //Credit Note Config Code Started
  vm.marketplace_add_show_cn = false;
  vm.marketplace_selected_cn = '';
  vm.saveCreditNote = function(name, value) {

    if(!name) {

      Service.showNoty("Please Enter Name");
      return false;
    } else {
      vm.updateMarketplaceCn(name, value, 'save')
      //vm.switches("{'tax_"+name+"':'"+value+"'}", 31);
      var found = false;
      for(var i = 0; i < vm.model_data.prefix_cn_data.length; i++) {

        if(vm.model_data.prefix_cn_data[i].marketplace_name == vm.model_data.marketplace_name) {

          vm.model_data.prefix_cn_data[i].marketplace_name = vm.model_data.marketplace_name;
          vm.model_data.prefix_cn_data[i].marketplace_prefix = vm.model_data.marketplace_prefix;
          vm.model_data.prefix_cn_data[i].marketplace_interfix = vm.model_data.marketplace_interfix;
          vm.model_data.prefix_cn_data[i].marketplace_date_type = vm.model_data.marketplace_date_type;
          found = true;
          break;
        }
      }
      if(!found) {

        vm.model_data.prefix_cn_data.push({marketplace_name: vm.model_data.marketplace_name,
                                        marketplace_prefix: vm.model_data.marketplace_prefix,
                                        marketplace_interfix: vm.model_data.marketplace_interfix,
                                        marketplace_date_type: vm.model_data.marketplace_date_type});
      }
      vm.marketplace_add_show_cn = false;
      vm.marketplace_selected_cn = "";
      vm.model_data.marketplace_name = "";
      vm.model_data.marketplace_prefix = "";
      vm.model_data.marketplace_interfix = "";
      vm.model_data.marketplace_date_type = "";
      vm.model_data.marketplace_new = true;
    }
  }

   vm.marketplaceSelectedCn = function(name) {

    if (name) {

      for(var i = 0; i < vm.model_data.prefix_cn_data.length; i++) {

        if(vm.model_data.prefix_cn_data[i].marketplace_name == name) {

          vm.model_data.marketplace_name = vm.model_data.prefix_cn_data[i].marketplace_name;
          vm.model_data.marketplace_prefix = vm.model_data.prefix_cn_data[i].marketplace_prefix;
          vm.model_data.marketplace_interfix = vm.model_data.prefix_cn_data[i].marketplace_interfix;
          vm.model_data.marketplace_date_type = vm.model_data.prefix_cn_data[i].marketplace_date_type;
          vm.model_data["marketplace_new"] = false;
          vm.marketplace_add_show_cn = true;
          break;
        }
      }
    } else {

      vm.model_data["marketplace_new"] = true;
      vm.marketplace_add_show = false;
      vm.model_data.marketplace_name = "";
      vm.model_data.marketplace_prefix = "";
    }
  }

  vm.updateMarketplaceCn = function(name, value, type) {

      var send = {marketplace_prefix: value,
                  marketplace_interfix: vm.model_data.marketplace_interfix,
                  marketplace_date_type: vm.model_data.marketplace_date_type,
                  type_name: 'credit_note_sequence', type_value: name}
      if (type != 'save') {
        send['delete'] = true;

        for(var i = 0; i < vm.model_data.prefix_cn_data.length; i++) {

          if(vm.model_data.prefix_cn_data[i].marketplace_name == vm.model_data.marketplace_name) {

            vm.model_data.prefix_cn_data.splice(i, 1);
            break;
          }
        }
        vm.marketplace_add_show_cn = false;
        vm.marketplace_selected_cn = "";
        vm.model_data.marketplace_name = "";
        vm.model_data.marketplace_prefix = "";
        vm.model_data.marketplace_new = true;
      }
      vm.service.apiCall("update_user_type_sequence/", "GET", send).then(function(data) {

        console.log(data);
        Service.showNoty(data.data.status);
      })
  }
  vm.saved_marketplaces_cn = [];
  vm.filterMarkeplacesCn = function() {
    vm.saved_marketplaces_cn = [];
    angular.forEach(vm.model_data.prefix_cn_data, function(data){
      vm.saved_marketplaces_cn.push(data.marketplace_name);
    })
    for(var i=0; i < vm.model_data.marketplaces.length; i++) {
      if (vm.saved_marketplaces_cn.indexOf(vm.model_data.marketplaces[i]) == -1) {
        vm.model_data.marketplace_name = vm.model_data.marketplaces[i];
        break;
      }
    }
  }
  //Credit Note Config Code Ended















  vm.addClassfication = function(){
    var send_data = {}
    angular.copy(vm.attr_model_data, send_data);
    var modalInstance = $modal.open({
      templateUrl: 'views/classification.html',
      controller: 'ClassificationPOP',
      controllerAs: 'pop',
      size: 'lg',
      backdrop: 'static',
      keyboard: false,
      //windowClass: 'full-modal',
      resolve: {
        items: function () {
          return send_data;
        }
      }
    });

    modalInstance.result.then(function (result_dat) {
      vm.model_data.attributes = result_dat;
    });
  }

  vm.update_invoice_remarks = function(invoice_remarks) {

    var data = $("[name='invoice_remarks']").val().split("\n").join("<<>>");
    vm.switches(data, 42);
    Auth.status();
  }
  vm.update_invoice_declaration = function(invoice_declaration) {

    var data = $("[name='invoice_declaration']").val().split("\n").join("<<>>");
    vm.switches(data, 72);
    Auth.status();
  }
  vm.update_pos_remarks= function(pos_remarks) {

    var data = $("[name='pos_remarks']").val().split("\n").join("<<>>");
    vm.switches(data, 82);
    Auth.status();
  }
  vm.delivery_challan_terms_condtions = function(delivery_challan_terms_condtions){
    var data = $("[name='delivery_challan_terms_condtions']").val().split("\n").join("<<>>");
    vm.switches(data, 98);
    Auth.status();
  }

  vm.getRemarks = function(remarks) {

    $timeout(function() {
    if(remarks && remarks.split("<<>>").length > 1) {
      $("[name='invoice_remarks']").val( remarks.split("<<>>").join("\n") )
    } else {
      $("[name='invoice_remarks']").val( remarks );
    }
    }, 1000);
  }
  vm.getDeclaration= function(declaration) {

    $timeout(function() {
    if(declaration && declaration.split("<<>>").length > 1) {
      $("[name='invoice_declaration']").val( declaration.split("<<>>").join("\n") )
    } else {
      $("[name='invoice_declaration']").val( declaration );
    }
    }, 1000);
  }
  vm.getPosremarks= function(pos_remarks) {

    $timeout(function() {
    if(pos_remarks && pos_remarks.split("<<>>").length > 1) {
      $("[name='pos_remarks']").val( pos_remarks.split("<<>>").join("\n") )
    } else {
      $("[name='pos_remarks']").val( pos_remarks );
    }
    }, 1000);
  }
  vm.getDeliveryChallanterms = function(delivery_challan_terms_condtions) {
    $timeout(function() {
    if(delivery_challan_terms_condtions && delivery_challan_terms_condtions.split("<<>>").length > 1) {
      $("[name='delivery_challan_terms_condtions']").val( delivery_challan_terms_condtions.split("<<>>").join("\n") )
    } else {
      $("[name='delivery_challan_terms_condtions']").val( delivery_challan_terms_condtions );
    }
    }, 1000)
  }

      var keynum = "";
      vm.limitLines = function(rows, e) {
        var lines = $(e.target).val().split('\n').length;
        //if(lines > rows && e.keyCode != 8) {
        //  e.preventDefault();
        //  return false;
        //}
        if(window.event) {
          keynum = e.keyCode;
        } else if(e.which) {
          keynum = e.which;
        }

        if(keynum == 13) {
          if(lines == rows) {
            e.preventDefault();
            return false;
          }else{
            lines++;
          }
        }
      }

  vm.model_data["rem_alert_new"] = true;
  vm.remAlertSelected = function(name) {

    if (name) {

      for(var i = 0; i < vm.model_data.rem_saved_mail_alerts.length; i++) {

        if(vm.model_data.rem_saved_mail_alerts[i].alert_name == name) {

          vm.model_data.rem_alert_name = vm.model_data.rem_saved_mail_alerts[i].alert_name;
          vm.model_data.rem_alert_value = vm.model_data.rem_saved_mail_alerts[i].alert_value;
          vm.model_data["rem_alert_new"] = false;
          vm.rem_alert_add_show = true;
          break;
        }
      }
    } else {

      vm.model_data["rem_alert_new"] = true;
      vm.rem_alert_add_show = false;
      vm.model_data.rem_alert_name = "";
      vm.model_data.rem_alert_value = "";
    }
  }

  vm.saved_rem_alerts = [];
  vm.filterRemAlerts = function() {
    vm.model_data['rem_alerts']  = {};
    angular.copy(vm.model_data.rem_mail_alerts, vm.model_data.rem_alerts);
    angular.forEach(vm.model_data.rem_saved_mail_alerts, function(data){
    if(vm.rem_mail_alerts.indexOf(data.alert_name) > 0)
       vm.model_data.rem_alerts.pop(data.alert_name);
    });
    vm.model_data.rem_alert_new = true;
    if(Object.keys(vm.model_data.rem_alerts).length>0){
      vm.model_data.rem_alert_name = Object.keys(vm.model_data.rem_alerts)[0];
    }
    console.log(vm.model_data.rem_alerts);
  }

  vm.saveRemainderAlerts = function(name, value) {

    if(!name) {

      Service.showNoty("Please Enter Alert Name");
      return false;
    } else if(!value) {

      Service.showNoty("Please Enter Duration");
      return false;
    } else {
      vm.updateRemainder(name, value, 'save')
      //vm.switches("{'tax_"+name+"':'"+value+"'}", 31);
      var found = false;
      for(var i = 0; i < vm.model_data.rem_saved_mail_alerts.length; i++) {

        if(vm.model_data.rem_saved_mail_alerts[i].alert_name == vm.model_data.rem_alert_name) {

          vm.model_data.rem_saved_mail_alerts[i].alert_name = vm.model_data.rem_alert_name;
          vm.model_data.rem_saved_mail_alerts[i].alert_value = vm.model_data.rem_alert_value;
          found = true;
          break;
        }
      }
      if(!found) {
        vm.model_data.rem_saved_mail_alerts.push({alert_name: vm.model_data.rem_alert_name, alert_value: vm.model_data.rem_alert_value});
      }
      vm.rem_alert_add_show = false;
      vm.rem_alert_selected = "";
      vm.model_data.rem_alert_name = "";
      vm.model_data.rem_alert_value = "";
      vm.model_data.rem_alert_new = true;
    }
  }

  vm.updateRemainder = function(name, value, type) {

      var send = {alert_name : name, alert_value: value}
      if (type != 'save') {
        send['delete'] = true;

        for(var i = 0; i < vm.model_data.rem_saved_mail_alerts.length; i++) {

          if(vm.model_data.rem_saved_mail_alerts[i].alert_name == vm.model_data.rem_alert_name) {

            vm.model_data.rem_saved_mail_alerts.splice(i, 1);
            break;
          }
        }
        vm.rem_alert_add_show = false;
        vm.rem_alert_selected = "";
        vm.model_data.rem_alert_name = "";
        vm.model_data.rem_alert_value = "";
        vm.model_data.rem_alert_new = true;
      }
      vm.service.apiCall("update_mail_alerts/", "GET", send).then(function(data) {

        console.log(data);
      })
  }

}
