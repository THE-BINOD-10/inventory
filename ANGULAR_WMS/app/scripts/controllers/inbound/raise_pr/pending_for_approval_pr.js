'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PendingForApprovalPurchaseRequestCtrl',['$scope', '$http', '$q', '$state', '$rootScope', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', '$modal', 'Service', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $q, $state, $rootScope, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, $modal, Service, Data) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.extra_width = { 'width': '1450px' };
    vm.selected = {};
    vm.selectAll = false;
    vm.date = new Date();
    vm.update_part = true;
    vm.is_actual_pr = true;
    vm.permissions = Session.roles.permissions;
    vm.user_profile = Session.user_profile;
    vm.industry_type = vm.user_profile.industry_type;
    vm.display_purchase_history_table = false;
    vm.warehouse_type = vm.user_profile.warehouse_type;
    vm.warehouse_level = vm.user_profile.warehouse_level;
    vm.multi_level_system = vm.user_profile.multi_level_system;
    vm.is_contracted_supplier = false;
    vm.cleared_data = true;
    vm.blur_focus_flag = true;
    vm.quantity_editable = false;
    vm.current_pr_app_data = {};
    vm.current_pr_app_data_flag = true;
    vm.pending_tab_footer = true;
//    if(vm.permissions.change_pendinglineitems) {
//      vm.quantity_editable = true;
//    }
    vm.filters = {'datatable': 'PendingPRApproval', 'search0':'', 'search1':'', 'search2': '', 'search3': ''}
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: vm.filters,
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('drawCallback', function(settings) {
         vm.service.make_selected(settings, vm.selected);
         $scope.$apply(function() {vm.bt_disable = true;vm.selectAll = false;});
       })
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withOption('createdRow', function(row, data, dataIndex) {
            $compile(angular.element(row).contents())($scope);
        })
        .withOption('headerCallback', function(header) {
            if (!vm.headerCompiled) {
                vm.headerCompiled = true;
                $compile(angular.element(header).contents())($scope);
            }
        })
       .withPaginationType('full_numbers')
       .withOption('order', [0, 'desc'])
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    var columns = [ "PR Number", "Product Category", "Priority Type", "Category",
                    "Total Quantity", "PR Created Date", "Store", "Department", "Enquiry Status",
                    "PR Raise By",  "Validation Status", "Pending Level", 
                    "To Be Approved By", "Last Updated By", "Last Updated At"];
    vm.dtColumns = vm.service.build_colums(columns);
    // vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
    //             .renderWith(function(data, type, full, meta) {
    //               if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
    //                 vm.selected = {};
    //               }
    //               vm.selected[meta.row] = false;
    //               return vm.service.frontHtml + meta.row + vm.service.endHtml;
    //             }))

    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      if($("#"+vm.dtInstance.id+":visible").length != 0) {
        vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
        vm.service.refresh(vm.dtInstance);
      }
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
      $('td:not(td:first)', nRow).unbind('click');
      $('td:not(td:first)', nRow).bind('click', function() {
        $scope.$apply(function() {
          vm.extra_width = { 'width': '1450px' };
          vm.supplier_id = aData['Supplier ID'];
          var data = {requested_user: aData['Requested User'], pr_number:aData['PR Number'],
                      pending_level:aData['LevelToBeApproved']};
            vm.dynamic_route(aData);
        });
      });
      return nRow;
    }
  $scope.getkeys = function (event) {
        let key = event.keyCode;
        if (event.altKey && event.which == 78) { // alt + n  enter key
          let index= (vm.model_data.data.length)-1
          vm.update_data(index, true, true)
          $('input[name="wms_code"]').trigger('focus');
        }
    }
  $(document).on('keydown', 'input.detectTab', function(e) {
    var keyCode = e.keyCode || e.which;

    var fields_count = (this.closest('#tab_count').childElementCount-1);
    var cur_td_index = (this.parentElement.nextElementSibling.cellIndex);
    var sku_index = (this.parentNode.nextElementSibling.children[0].value);


    if ((keyCode == 9) && (fields_count === cur_td_index)) {
      e.preventDefault();
      vm.update_data(Number(sku_index), false);
    }
  });

    vm.update = false;
    vm.title = 'Raise PR';
    vm.bt_disable = true;
    vm.vendor_receipt = false;

    var empty_data = {"supplier_id":"",
                      "po_name": "",
                      "ship_to": "",
                      "receipt_types": ['Buy & Sell', 'Purchase Order', 'Hosted Warehouse'],
                      "receipt_type": 'Purchase Order',
                      "seller_types": [],
                      "total_price": 0,
                      "loss_expected": 0,
                      "tax": "",
                      "sub_total": "",
                      "supplier_sku_prices": "",
                      "terms_condition": "",
                      "data": [
                        {'fields':{"supplier_Code":"", "ean_number":"", "order_quantity":"", 'price':0, "measurement_unit":"",
                                   "dedicated_seller": "", "row_price": 0, 'sku': {"price":"", 'wms_code': ""},
                                   "sgst_tax": "", "cgst_tax": "", "igst_tax": "", "cess_tax": "", "apmc_tax": "",
                                   "utgst_tax": "", "tax": ""}}
                      ],
                      "company": Session.user_profile.company_name,
                      "wh_address": Session.user_profile.wh_address
                     };

    vm.model_data = {};
    angular.copy(empty_data, vm.model_data);

    vm.close = function () {
      vm.base();
      $state.go('app.inbound.RaisePr');
      vm.display_purchase_history_table = false;
    }

    vm.b_close = vm.close;
    vm.dynamic_route = function(aData) {
      vm.form = 'pending_for_approval';
      var p_data = {requested_user: aData['Requested User'], purchase_id:aData['Purchase Id'], current_approval: aData['To Be Approved By']};
      vm.service.apiCall('generated_actual_pr_data/', 'POST', p_data).then(function(data){
        vm.current_pr_app_data = {};
        vm.current_pr_app_data_flag = true;
        if (data.message && typeof(data.data) == 'object') {
          var receipt_types = ['Buy & Sell', 'Purchase Order', 'Hosted Warehouse'];
          vm.update_part = false;
          var empty_data = {
                  "po_name": "",
                  "ship_to": data.data.ship_to,
                  "terms_condition": data.data.terms_condition,
                  "receipt_type": data.data.receipt_type,
                  "seller_types": [],
                  'is_approval':data.data.is_approval,
                  "validateFlag": data.data.validateFlag,
                  "total_price": 0,
                  "loss_expected": 0,
                  "tax": "",
                  "cess_tax": 0,
                  "sub_total": "",
                  "pr_delivery_date": data.data.pr_delivery_date,
                  "pr_created_date": data.data.pr_created_date,
                  "product_category": data.data.product_category,
                  "priority_type": data.data.priority_type,
                  "sku_category": data.data.sku_category,
                  'uploaded_file_dict': data.data.uploaded_file_dict,
                  'pa_uploaded_file_dict': data.data.pa_uploaded_file_dict,
                  "is_purchase_approver": data.data.is_purchase_approver,
                  "store": data.data.store,
                  "store_id": data.data.store_id,
                  "dept_user_id": data.data.dept_user_id,
                  "department": data.data.department,
                  "data": data.data.data,
                  "is_auto_pr": data.data.is_auto_pr,
                  "tax_display": data.data.tax_display,
                  "warehouse_currency": data.data.warehouse_currency,
                  "display_suggested_qty": data.data.display_suggested_qty,
          };
          vm.model_data = {};
          vm.resubmitCheckObj = {};
          vm.is_resubmitted = false;
          vm.resubmitting_user = data.data.resubmitting_user;
          vm.is_pa_resubmitted = false;
          if (!vm.resubmitting_user) {
              vm.is_pa_resubmitted = true;
          }
          angular.copy(empty_data, vm.model_data);
          angular.forEach(vm.model_data.data, function(data) {
            data.fields.sku.pr_extra_data = data.fields.pr_extra_data;
          })
          if (vm.model_data.supplier_id){
            vm.model_data['supplier_id_name'] = vm.model_data.supplier_id + ":" + vm.model_data.supplier_name;
          } else {
            vm.model_data['supplier_id_name'] = '';
          }
          vm.model_data.approval_remarks_val = false;
          if(vm.model_data.uploaded_file_dict && Object.keys(vm.model_data.uploaded_file_dict).length > 0) {
            vm.model_data.uploaded_file_dict.file_url = vm.service.check_image_url(vm.model_data.uploaded_file_dict.file_url);
          }
          if(vm.model_data.pa_uploaded_file_dict && Object.keys(vm.model_data.pa_uploaded_file_dict).length > 0) {
            vm.model_data.pa_uploaded_file_dict.file_url = vm.service.check_image_url(vm.model_data.pa_uploaded_file_dict.file_url);
          }
          vm.model_data.seller_type = vm.model_data.data[0].fields.dedicated_seller;
          vm.dedicated_seller = vm.model_data.data[0].fields.dedicated_seller;

          vm.model_data.levelWiseRemarks = data.data.levelWiseRemarks;
          vm.model_data.enquiryRemarks = data.data.enquiryRemarks;
          vm.model_data.validated_users = data.data.validated_users;
          angular.forEach(vm.model_data.data, function(data){
            if (!data.fields.apmc_tax) {
              data.fields.apmc_tax = 0;
            }
            if (!data.fields.tax) {
              if (data.fields.temp_tax){
                data.fields.tax = data.fields.temp_tax;
              }
            }
            data.fields.sku['conversion'] = data.fields.conversion;
            vm.resubmitCheckObj[data.fields.sku.wms_code] = data.fields.order_quantity;
          });
          // vm.getTotals();
          vm.service.apiCall('get_sellers_list/', 'GET').then(function(data){
            if (data.message) {
              var seller_data = data.data.sellers;
              vm.model_data.tax = data.data.tax;
              vm.model_data.seller_supplier_map = data.data.seller_supplier_map;
              vm.model_data["receipt_types"] = data.data.receipt_types;
              vm.model_data.seller_type = vm.dedicated_seller;
              vm.model_data.warehouse_names = data.data.warehouse;
              vm.model_data.prodcatg_map = data.data.prodcatg_map;
              vm.model_data.product_categories = Object.keys(vm.model_data.prodcatg_map);
              angular.forEach(seller_data, function(seller_single){
                vm.model_data.seller_types.push(seller_single.id + ':' + seller_single.name);
              });

              angular.forEach(vm.model_data.data, function(data){
                data.fields.dedicated_seller = vm.dedicated_seller;
              })

              vm.default_status = (Session.user_profile.user_type == 'marketplace_user' && Session.user_profile.industry_type != 'FMCG')? true : false;
              vm.getCompany();
              vm.seller_change1 = function(type) {

                if(vm.model_data.receipt_type == 'Hosted Warehouse') {

                  angular.forEach(vm.model_data.data, function(data){

                    data.fields.dedicated_seller = type;
                  })
                } else {
                  vm.selected_seller = type;
                  vm.default_status = false;
                  vm.model_data.data[vm.model_data.data.length - 1].fields.dedicated_seller = vm.selected_seller;
                }
                vm.getCompany();
              }
            }
          });

          vm.checkResubmitPurchaseApprover = function(sku_data) {
            if (!vm.resubmitting_user) {
              vm.is_pa_resubmitted = true;
              return;
            }
            vm.is_pa_resubmitted = false;
            if (vm.permissions.change_pendinglineitems){
              angular.forEach(vm.model_data.data, function(eachField){
                if(eachField.fields.preferred_supplier != eachField.fields.supplier_id_name ||
                   eachField.fields.discount != eachField.fields.resubmit_discount ||
                   eachField.fields.order_quantity != eachField.fields.resubmit_quantity ||
                   eachField.fields.price != eachField.fields.resubmit_price){
                  vm.is_pa_resubmitted = true;
                }
              })
            }
          }
          vm.model_data.suppliers = [vm.model_data.supplier_id];
          vm.model_data.supplier_id = vm.model_data.suppliers[0];
          vm.model_data['po_number'] = aData['PO Number'];
          vm.model_data['pr_number'] = aData['PR Number'];
          vm.model_data['purchase_id'] = aData['Purchase Id']
          // vm.model_data.seller_type = vm.model_data.dedicated_seller;
          vm.vendor_receipt = (vm.model_data["Order Type"] == "Vendor Receipt")? true: false;
          vm.title = 'Validate PR';
          // vm.pr_number = aData['PR Number']
          vm.validated_by = aData['To Be Approved By']
          vm.requested_user = aData['Requested User']
          vm.pending_status = aData['Validation Status']
          vm.convertPoFlag = data.data.convertPoFlag
          vm.pending_level = aData['LevelToBeApproved']
          if (aData['Validation Status'] != 'Saved') {
            var temp_dict = {'pr_number': aData['PR Number']};
            vm.service.apiCall('next_approvals_with_staff_master_mails/', 'POST', temp_dict, true).then(function(data){
              if(data.message){
                if (Object.keys(data.data).length ==2) {
                  vm.current_pr_app_data = data.data;
                } else {
                  Service.showNoty(data.data);
                }
              }
              vm.current_pr_app_data_flag = false;
            })
          }
          if (aData['Validation Status'] == 'Approved'){
            vm.current_pr_app_data_flag = false;
            $state.go('app.inbound.RaisePr.ConvertPRtoPO');
          } else if (aData['Validation Status'] == 'Store_Sent'){
            vm.current_pr_app_data_flag = false;
            $state.go('app.inbound.RaisePr.ConvertPRtoPO');
          } else if (aData['Validation Status'] == 'Saved'){
            vm.current_pr_app_data_flag = false;
            vm.update = true;
            $state.go('app.inbound.RaisePr.SavedPurchaseRequest');
          } else {
            vm.current_pr_app_data_flag = false;
            $state.go('app.inbound.RaisePr.ApprovePurchaseRequest');
          }
        } else {
          Service.showNoty(data.data);
          vm.service.refresh(vm.dtInstance);
        }
      });
    }
    if ($rootScope.$current_pr != '') {
      vm.supplier_id = $rootScope.$current_pr['Supplier ID'];
      vm.current_pr = $rootScope.$current_pr
      if (vm.current_pr['approval_status'] == ''){
        vm.dynamic_route(vm.current_pr); 
      } else {
        Service.showNoty("PR doesn't need to be processed..Either resubmitted or approved.");
      }
      // vm.dynamic_route(vm.current_pr);
      $rootScope.$current_pr = '';
      $rootScope.$current_path = '';
    }
    vm.base = function() {
      vm.title = "Raise PR";
      vm.vendor_produce = false;
      vm.confirm_print = false;
      vm.update = false;
      vm.print_enable = false;
      vm.vendor_receipt = false;
      angular.copy(empty_data, vm.model_data);
      vm.model_data.seller_types = Data.seller_types;
      if (vm.service.is_came_from_raise_po) {
        vm.model_data.supplier_id_name = vm.service.searched_sup_code;
        vm.model_data = vm.service.raise_po_data;
        vm.vendor_receipt = Service.raise_po_vendor_receipt;
        Service.is_came_from_raise_po = false;
        vm.service.searched_sup_code = '';
        vm.service.searched_wms_code = '';
      }
    }
    vm.base();
    vm.refresh = function() {
        vm.service.refresh(vm.dtInstance)
    };
    vm.add = function () {
      vm.extra_width = { 'width': '1450px' };
      vm.model_data.seller_types = [];
      // vm.model_data.product_categories = ['Kits&Consumables', 'Services', 'Assets', 'OtherItems'];
      vm.model_data.priority_type = 'normal';

      vm.service.apiCall('get_sellers_list/', 'GET').then(function(data){
        if (data.message) {
          var seller_data = data.data.sellers;
          vm.model_data.tax = data.data.tax;
          vm.model_data.seller_supplier_map = data.data.seller_supplier_map
          vm.model_data.terms_condition = data.data.raise_po_terms_conditions
          vm.model_data.ship_addr_names = data.data.shipment_add_names
          vm.model_data.shipment_addresses = data.data.shipment_addresses
          vm.model_data.warehouse_names = data.data.warehouse
          vm.model_data["receipt_types"] = data.data.receipt_types;
          vm.model_data.prodcatg_map = data.data.prodcatg_map;
          vm.model_data.product_categories = Object.keys(vm.model_data.prodcatg_map);
          vm.model_data.sku_categories = vm.model_data.prodcatg_map[vm.model_data.product_categories[0]];
          angular.forEach(seller_data, function(seller_single){
              vm.model_data.seller_types.push(seller_single.id + ':' + seller_single.name);
          });
          Data.seller_types = vm.model_data.seller_types;

          vm.default_status = (Session.user_profile.user_type == 'marketplace_user') ? true: false;


          vm.model_data.receipt_type = 'Purchase Order';
          if (Session.user_profile.user_type == 'marketplace_user') {
            vm.model_data.receipt_type = 'Hosted Warehouse';
          }
          $state.go('app.inbound.RaisePr.PurchaseRequest');

        }
      });
    }
    vm.isFloat = function(n) {
    return n != "" && !isNaN(n) && Math.round(n) != n;
    }
    vm.sku_pack_validation = function(data) {
      for (var j = 0; j < data.length; j++) {
        if (data[j]["fields"]['sku']['skuPack_quantity']) {
          var skuPackQty = data[j]["fields"]["sku"]["skuPack_quantity"];
          var orderQty = data[j]["fields"]["order_quantity"];
          var response = vm.isFloat(orderQty/skuPackQty);
          if (response) {
            colFilters.showNoty(data[j]["fields"]["sku"]["wms_code"] +' - Sku Pack Quantity Mismatch');
            return false;
          }
        }
      }
    return true;
    }

    vm.ship_addr_change = function(name) {
      vm.model_data.shipment_address_select = name
      for (let i = 0; i < vm.model_data.shipment_addresses.length; i++) {
        if (vm.model_data.shipment_addresses[i].title == name) {
          let form_address = vm.model_data.shipment_addresses[i].addr_name +', '+ vm.model_data.shipment_addresses[i].address + '-' + vm.model_data.shipment_addresses[i].pincode + ', Mobile No:' + vm.model_data.shipment_addresses[i].mobile_number
          vm.model_data.ship_to = form_address
        }
      }
    }

    vm.seller_change = function(type) {
      vm.selected_seller = type;
      vm.default_status = false;
      vm.model_data.data[vm.model_data.data.length - 1].fields.dedicated_seller = vm.selected_seller;
      vm.getCompany();
      vm.populate_last_transaction('');
    }

    vm.getNoOfTests = function(order_quantity, data) {
      var ordQty = parseInt(order_quantity)
      if (ordQty > 0){
        data.conversion = data.sku.conversion * ordQty
        data.no_of_tests = ordQty * data.sku.no_of_tests;
      } else {
        data.conversion = 0
      }
    }

    vm.reset_model_data = function(product_category){
      vm.model_data.data = [];
      // vm.model_data.sku_category = "";
      var emptylineItems = {"wms_code":"", "ean_number": "", "order_quantity":"", "price":0,
                            "measurement_unit": "", "row_price": 0, "tax": "", "is_new":true,
                            "sgst_tax": "", "cgst_tax": "", "igst_tax": "", "utgst_tax": "",
                            "cess_tax": "",
                            "sku": {"wms_code": "", "price":""}
                          }
      vm.model_data.sku_categories = vm.model_data.prodcatg_map[product_category];
      if (product_category == 'Kits&Consumables'){
        vm.model_data.data.push({"fields": emptylineItems});
      } else if (product_category == 'Assets'){
        vm.model_data.data.push({"fields": emptylineItems});
      } else if(product_category == 'Services'){
        vm.model_data.data.push({"fields": emptylineItems});
      } else if(product_category == 'OtherItems'){
        vm.model_data.data.push({"fields": emptylineItems});
      }
    }
    
    vm.update_data = function (index, flag=true, plus=false, product_category='') {
      var emptylineItems = {}
      if (product_category == 'Kits&Consumables'){
        emptylineItems = {"wms_code":"", "ean_number": "", "order_quantity":"", "price":0,
                            "measurement_unit": "", "row_price": 0, "tax": "", "is_new":true,
                            "sgst_tax": "", "cgst_tax": "", "igst_tax": "", "utgst_tax": "",
                            "cess_tax": 0
                          }
      } else if (product_category == 'Assets'){
        emptylineItems = {"wms_code":"", "ean_number": "", "order_quantity":"", "price":0,
                            "measurement_unit": "", "row_price": 0, "tax": "", "is_new":true,
                            "sgst_tax": "", "cgst_tax": "", "igst_tax": "", "utgst_tax": "",
                            "cess_tax": 0
                          }
      }
      if (index == vm.model_data.data.length-1) {
        if (vm.model_data.data[index]["fields"]["sku"] && (vm.model_data.data[index]["fields"]["sku"]["wms_code"] && vm.model_data.data[index]["fields"]["order_quantity"]) && (vm.permissions.sku_pack_config ?  vm.sku_pack_validation(vm.model_data.data) : true)) {
          if (plus) {
            vm.model_data.data.push({"fields": emptylineItems});

          } 
        } else {
          Service.showNoty('SKU Code and Quantity are required fields. Please fill these first');
        }
      } else {
        vm.model_data.data.splice(index,1);
        // vm.getTotals();
      }
    }

    vm.check_sku_list = function(key, val, index) {

      for (var i=0;i < vm.model_data.data.length; i++) {
        if(vm.model_data.data[i].$$hashKey != key && val == vm.model_data.data[i].fields.sku.wms_code) {
          alert("This sku already exist in index");
          vm.model_data.data.splice(index,1);
        }
      }
    }

    vm.delete_data = function(key, id, index) {
      if(id) {
        var del_data = {}
        del_data[key] = id;
        vm.service.apiCall('delete_po/', 'GET', del_data).then(function(data){
          if(data.message) {
      vm.model_data.data[index].fields.row_price = (vm.model_data.data[index].fields.order_quantity * Number(vm.model_data.data[index].fields.price))
;
      vm.model_data.total_price = 0;
      vm.model_data.loss_expected =0;
      angular.forEach(vm.model_data.data, function(one_row){
        vm.model_data.total_price = vm.model_data.total_price + (one_row.fields.order_quantity * one_row.fields.price);
      });
            vm.service.pop_msg(data.data);
          }
        });
      }
    }

    vm.confirm_purchase_approval_request = function(data, validation_type) {
      var status = true;
      var sku_list = '';
      if (validation_type == "approved" && vm.permissions.change_pendinglineitems) {
        for (var i = 0; i < data.length; i++) {
          if (Object.keys(vm.model_data.data[i].fields.supplierDetails).length > 0 && vm.model_data.data[i].fields.supplier_id_name != '') {
            if (typeof(vm.model_data.data[i].fields.supplierDetails[vm.model_data.data[i].fields.supplier_id_name]) != "undefined") {
              var compare_gstin = vm.model_data.data[i].fields.supplierDetails[vm.model_data.data[i].fields.supplier_id_name].gstin
              if ((compare_gstin != '' || compare_gstin != 0) && vm.model_data.data[i].fields['order_quantity'] > 0) {
                if (!vm.model_data.data[i].fields.hsn_code || vm.model_data.data[i].fields.hsn_code == 0) {
                  status = false;
                  sku_list = sku_list + ', ' + vm.model_data.data[i].fields.sku.wms_code;
                }
              }
            } 
          }
          if (i+1 == data.length) {
            if (!status) {
              Service.showNoty('HSN Code Mandate for These Sku : ' + sku_list);
            }
            return status;
          }
        }
      } else {
        return status;
      }
    }

    vm.approve_pr = function(form, validation_type) {
      if (vm.model_data.approval_remarks_val && (vm.model_data.approval_remarks == '' || typeof(vm.model_data.approval_remarks) == 'undefined')) {
        Service.showNoty('Remarks Mandatory for Supplier Change, please Enter');
        return;
      }
      if (vm.confirm_purchase_approval_request(vm.model_data.data, validation_type)) {
        var elem = angular.element($("form[name='pending_for_approval']"));
        elem = elem[0];
        elem = $(elem).serializeArray();
        elem.push({name:'purchase_id', value:vm.model_data.purchase_id})
        if (vm.is_actual_pr){
          elem.push({name:'is_actual_pr', value:true})
        }
        var keepGoing = true;
        if(vm.permissions.change_pendinglineitems){
          angular.forEach(vm.model_data.data, function(row_data){
            var order_quantity = row_data.fields.order_quantity;
            if(order_quantity == ''){
              order_quantity = 0;
            }
            order_quantity = parseInt(order_quantity)
            if(!row_data.fields.supplier_id_name && validation_type !='rejected' && order_quantity) {
              keepGoing = false;
              Service.showNoty('Supplier Should be provided by Purchase');
              return;
            }
            if (row_data.fields.price =='') {
              keepGoing = false;
              Service.showNoty('Price Should be provided by Purchase');
              return;
            }
            if (order_quantity < 0) {
              keepGoing = false;
              Service.showNoty('Order Quantity cant be empty or negative');
              return;
            }
          });
        }
//        var keepGoing = true;
//        if (vm.permissions.change_pendinglineitems) {
//          debugger;
//          angular.forEach(elem, function(key, index) {
//            var order_quantity = parseInt(order_quantity);
//            if (key.name == 'supplier_id' && validation_type !='rejected' && order_quantity) {
//              if (!key.value) {
//                keepGoing = false;
//                Service.showNoty('Supplier Should be provided by Purchase');
//                return;
//              }
//            } else if (key.name == 'price') {
//              if (key.value == '') {
//                keepGoing = false;
//                Service.showNoty('Price Should be provided by Purchase');
//                return;
//              }
//            } else if (key.name == 'order_quantity') {
//              if (key.value == '' || parseInt(key.value) < 0) {
//                keepGoing = false;
//                Service.showNoty('Order Quantity cant be empty or negative');
//                return;
//              }
//            }
//          });
//        }
        if (vm.validated_by){
          elem.push({name:'validated_by', value:vm.validated_by})
        }
        if (vm.requested_user){
          elem.push({name:'requested_user', value:vm.requested_user})
        }
        if (vm.pending_level){
          elem.push({name:'pending_level', value:vm.pending_level})
        }
        if (validation_type == 'approved'){
          elem.push({name: 'validation_type', value: 'approved'})
        } else{
          elem.push({name: 'validation_type', value: 'rejected'})
        }
        var form_data = new FormData();
        if (vm.model_data.product_category != "Kits&Consumables" && $(".approve_form").find('[name="files"]').length > 0){
          var files = $(".approve_form").find('[name="files"]')[0].files;
          $.each(files, function(i, file) {
            form_data.append('files-' + i, file);
          });
        }
        $.each(elem, function(i, val) {
          form_data.append(val.name, val.value);
        });
        if (keepGoing) {
          vm.service.apiCall('approve_pr/', 'POST', form_data, true, true).then(function(data){
            if(data.message){
              if(data.data == 'Approved Successfully') {
                vm.close();
                vm.service.refresh(vm.dtInstance);
              } else {
                //vm.close();
                var response = JSON.parse(data.data)
                swal2({
                      title: 'Warning Message',
                      text: response.status,
                      icon: "success",
                      button: "OK",
                      allowOutsideClick: false
                    }).then(function (text) {
                      console.log("OK");
                });
                //vm.service.showNoty(data.data, 'warning');
              }
            }
          })
        }
      }
    }

    vm.submit_enquiry = function(form){
      // var elem = angular.element($('form'));
      if (vm.model_data.enquriy_remarks == '' || typeof(vm.model_data.enquriy_remarks)== 'undefined') {
        Service.showNoty('Enquiry Text Is Mandatory');
        return;
      }
      var elem = angular.element($("form[name='pending_for_approval']"));
      elem = elem[0];
      elem = $(elem).serializeArray();
      // if (vm.is_purchase_request){
      //   elem.push({name:'is_actual_pr', value:true})
      // }
      if (vm.model_data.purchase_id){
        elem.push({name:'purchase_id', value:vm.model_data.purchase_id})
      }
      if (vm.requested_user){
        elem.push({name:'requested_user', value:vm.requested_user})
      }
      vm.service.apiCall('submit_pending_approval_enquiry/', 'POST', elem, true).then(function(data){
        if(data.message){
          if(data.data == 'Submitted Successfully') {
            vm.close();
            vm.service.refresh(vm.dtInstance);
          } else {
            vm.service.showNoty(data.data);
          }
        }
      })
    }
    vm.customSelectAll = function(allSelected){
      angular.forEach(vm.preview_data.data, function(cbox) {
        allSelected?cbox.checkbox=true:cbox.checkbox=false;
      })      
    }

    vm.getColor = function(data){
      if (data.moq > data.quantity){
        return "label label-danger"
      } else {
        return "label label-success"
      }
    }

    vm.pr_to_po_preview = function(){
      vm.bt_disable = true;
      var prIds = [];
      var deptTypes = [];
      var prodCatgs = [];
      var catgs = [];

      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[Number(key)];
          var deptType = temp['_aData']['Department'];
          var prodCatg = temp['_aData']['Product Category'];
          var catg = temp['_aData']['Category'];
          prIds.push(temp['_aData']["Purchase Id"]);
          if (!deptTypes.includes(deptType)){
            deptTypes.push(deptType);
          }
          if (!prodCatgs.includes(prodCatg)){
            prodCatgs.push(prodCatg);
          }
          if (!catgs.includes(catg)){
            catgs.push(catg);
          }
        }
        if(Object.keys(vm.selected).length-1 == parseInt(key)){
          if (deptTypes.length > 1 || prodCatgs.length > 1 || catgs.length > 1) {
            prIds = [];
            vm.service.showNoty("Same Department/ProductCategory/Category PRs can be consolidated");
          }
          var data_dict = {
            'prIds': JSON.stringify(prIds)
          };
          if(prIds.length > 0){
            vm.service.apiCall('get_pr_preview_data/', 'POST', data_dict, true).then(function(data){
              if(data.message){
                vm.preview_data = data.data;
                $state.go("app.inbound.RaisePr.PRemptyPreview");
              }
            });
          } else {
            vm.bt_disable = false;
          }
        }
      });
    }
    vm.getFirstSupplier = function(data, line_level=''){
      if (typeof(data["preferred_supplier"]) != 'undefined' ) {
        vm.getsupBasedPriceDetails(data["preferred_supplier"], data, line_level);
        return data["preferred_supplier"];  
      }
    }
    vm.getsupBasedPriceDetails = function(supplier_id_name, sup_data, line_level=''){
      var supDetails = sup_data.supplierDetails[supplier_id_name];
      if (supDetails) {
        sup_data.moq = supDetails.moq;
        sup_data.tax = supDetails.tax;
        sup_data.cess_tax = supDetails.cess_tax;
        sup_data.price = supDetails.price;
        sup_data.final_price = parseFloat(sup_data.price) - parseFloat(sup_data.price) * parseFloat((sup_data.discount/100));
        var discount_amount = sup_data.price * sup_data.order_quantity - sup_data.final_price * sup_data.order_quantity
        sup_data.amount = (supDetails.amount - discount_amount).toFixed(2);
        sup_data.total = (supDetails.total - discount_amount).toFixed(2);
        sup_data.supplier_id = supDetails.supplier_id;
        sup_data.supplier_id_name = supplier_id_name;
        if (!('last_supplier' in Object.keys(sup_data.sku))) {
          sup_data["sku"]["last_supplier"] = sup_data.sku.pr_extra_data.last_supplier + "-" + sup_data.sku.pr_extra_data.last_supplier_price;
          sup_data["sku"]["least_supplier"] = sup_data.sku.pr_extra_data.least_supplier + "-" + sup_data.sku.pr_extra_data.least_supplier_price;
          sup_data["sku"]["least_supplier_pi"] = sup_data.sku.pr_extra_data.least_supplier_pi + "-" + sup_data.sku.pr_extra_data.least_supplier_price_pi;
        }
        vm.get_info_delta_value(sup_data);
        if (line_level) {
          vm.getTotals(line_level);  
        }
      }
    }
    vm.get_info_delta_value = function(sup_data) {
      if (typeof(sup_data['system_preferred_supplier']) != 'undefined' && sup_data['system_preferred_supplier'] != '') {
        (sup_data['preferred_supplier'] != sup_data['system_preferred_supplier']) ? sup_data['icon_color'] = { 'color': 'red' } : sup_data['icon_color'] = { 'color': 'seagreen' };
      } else if (sup_data['preferred_supplier'] && sup_data['preferred_supplier'] != sup_data['supplier_id_name']) {
        sup_data['sku_sku_comment'] = true;
        vm.model_data.approval_remarks_val = true;
        sup_data['icon_color'] = { 'color': 'red' };
      } else {
        sup_data['sku_sku_comment'] = false;
        sup_data['icon_color'] = { 'color': 'seagreen' };
      }
      if (typeof(sup_data['icon_color']) != 'undefined') {
        if (sup_data['icon_color']['color'] == 'red') {
          vm.model_data.approval_remarks_val = true;
        }
      }
    }
    vm.send_to_parent_store = function(form) {
      var selectedItems = [];
      angular.forEach(vm.preview_data.data, function(eachLineItem){
        if (eachLineItem.checkbox){
          // if (eachLineItem.moq > eachLineItem.quantity){
            selectedItems.push({name: "sku_code", value: eachLineItem.sku_code});
            selectedItems.push({name: 'pr_id', value:eachLineItem.pr_id});
            selectedItems.push({name: 'quantity', value: eachLineItem.quantity});
          // };
        }
      });   
      vm.service.alert_msg("Sending Selected SKUS to Parent Store").then(function(msg) {
        if (msg == "true") {
          vm.service.apiCall('send_pr_to_parent_store/', 'POST', selectedItems, true).then(function(data){
          if(data.message){
              if(data.data == 'Sent To Parent Store Successfully') {
                vm.close();
                vm.service.refresh(vm.dtInstance);
              } else {
                vm.service.pop_msg(data.data);
              }
            }
          });          
        }
      });
    }

    vm.move_to_sku_supplier = function (sku, lineItem, purchase_id) {
      vm.display_vision = {'display': 'none'};
      var data = {'sku_code': sku, 'purchase_id': purchase_id};
      var modalInstance = $modal.open({
        templateUrl: 'views/inbound/raise_po/supplier_sku_request.html',
        controller: 'skuSupplierCtrl',
        controllerAs: 'showCase',
        size: 'lg',
        backdrop: 'static',
        keyboard: false,
        resolve: {
          items: function () {
            return data;
          }
        }
      });
      modalInstance.result.then(function (selectedItem) {
        if (selectedItem){
          lineItem.is_doa_sent = true;          
        }
        vm.display_vision = {'display': 'block'};
      });
    }

    vm.extra_row_info = function (datum) {
      var data = {'line_data': datum};
      if (typeof(datum['fields']['sku']) == 'undefined') {
        vm.service.showNoty('Invalid Sku');
      } else if (datum['fields']['sku']['wms_code'] && datum['fields']['description']) {
        data['line_data']['store_id'] = vm.model_data.store_id
        data['line_data']['dept_user_id'] = vm.model_data.dept_user_id
        var modalInstance = $modal.open({
          templateUrl: 'views/inbound/raise_pr/sku_row_level_data.html',
          controller: 'skuRowCtrl',
          controllerAs: 'showCase',
          size: 'lg',
          backdrop: 'static',
          keyboard: false,
          resolve: {
            items: function () {
              return data;
            }
          }
        });
        modalInstance.result.then(function (selectedItem) {
          if (selectedItem) {
            console.log('');
          }
        });
      } else {
        vm.service.showNoty('Invalid Sku');
      }
    }

    vm.print_pending_po = function(form, validation_type) {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      var warehouse = '';
      angular.forEach(elem, function(key, index) {
        if(key.name == 'warehouse') {
          warehouse = key.value;
        }
      });
      $http.get(Session.url+'print_pending_po_form/?purchase_id='+vm.model_data.purchase_id+'&is_actual_pr=true'+'&warehouse='+warehouse, {withCredential: true})
      .success(function(data, status, headers, config) {
        vm.service.print_data(data, vm.model_data.pr_number);
      });
    }

    vm.validateSupplier = function(product) {
      vm.update_tax_details(product)
    }

    vm.barcode = function() {

      vm.barcode_title = 'Barcode Generation';

      vm.model_data['barcodes'] = [];

      angular.forEach(vm.model_data.data, function(barcode_data){

        var quant = barcode_data.fields.order_quantity;

       var sku_det = barcode_data.fields.sku.wms_code;

        if (barcode_data.fields.ean_number) {

            sku_det = barcode_data.fields.ean_number;
        }

        vm.model_data['barcodes'].push({'sku_code': sku_det, 'quantity': quant})

      })

      vm.model_data['format_types'] = ['format1', 'format2', 'format3']

      var key_obj = {'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details'}

      $state.go('app.inbound.RaisePo.barcode');
    }

    vm.update_raise_pr = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      if (vm.is_actual_pr){
        elem.push({name:'is_actual_pr', value:true})
      }

      var product_category = '';
      angular.forEach(elem, function(list_obj) {
        if (list_obj['name'] == 'product_category') {
          product_category = list_obj['value']
        }
      });


      var form_data = new FormData();
      if (product_category != "Kits&Consumables" && $(".pr_form").find('[name="files"]').length > 0) {
        var files = $(".pr_form").find('[name="files"]')[0].files;
        $.each(files, function(i, file) {
          form_data.append('files-' + i, file);
        });  
      }
      // var files = $(".pr_form").find('[name="files"]')[0].files;
      // $.each(files, function(i, file) {
      //   form_data.append('files-' + i, file);
      // });
      $.each(elem, function(i, val) {
        form_data.append(val.name, val.value);
      });

      vm.service.apiCall('validate_wms/', 'POST', elem, true).then(function(data){
        if(data.message){
          if(data.data == 'success') {
            vm.service.apiCall('save_pr/', 'POST', form_data, true, true).then(function(data){
              if(data.message){
                if(data.data == 'Saved Successfully') {
                  vm.close();
                  vm.service.refresh(vm.dtInstance);
                } else {
                  vm.service.pop_msg(data.data);
                }
              }
            })
          } else {
            vm.service.pop_msg(data.data);
          }
        }
      });
    }

    vm.confirm = function(data) {
      if (data.$valid) {
        if (vm.warehouse_type == 'CENTRAL_ADMIN') {
          var elem = angular.element($('form'))
          elem = elem[0]
          elem = $(elem).serializeArray()
          vm.common_confirm('confirm_central_po/', elem)
        } else {
          if(!(vm.update)) {
            vm.confirm_add_po();
          } else {
            vm.confirm_po();
          }
        }
      }
    }

    vm.confirm_add_po = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.common_confirm('confirm_add_po/', elem);
    }

    vm.confirm_pr = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.common_confirm('confirm_pr/', elem);
    }

    vm.common_confirm = function(url, elem) {
      var confirm_url = 'validate_wms/';
      if (vm.is_actual_pr){
        elem.push({name:'is_actual_pr', value:true})
      }
      // if (vm.pr_number){
      //   elem.push({name:'pr_number', value:vm.pr_number})
      // }
      vm.service.apiCall(confirm_url, 'POST', elem, true).then(function(data){
        if(data.message) {
          if (data.data == "success") {
            vm.raise_po(url, elem);
          } else{
            vm.service.pop_msg(data.data);
          }
        }
      });
    }

    vm.raise_po = function(url, elem) {
      vm.service.alert_msg("Do you want to Raise PO").then(function(msg) {
        if (msg == "true") {
          vm.service.apiCall(url, 'POST', elem).then(function(data){
            if(data.message) {
              vm.service.pop_msg(data.data);
              vm.service.refresh(vm.dtInstance);
              if(data.data.search("<div") != -1) {
                if (vm.model_data.receipt_type == 'Hosted Warehouse') {
                  vm.title = $(data.data).find('.modal-header h4').text().trim();

                }
                vm.extra_width = {'width': '990px'};
                vm.html = $(data.data);
                angular.element(".modal-body").html($(data.data));
                vm.print_enable = true;
              } else {
                vm.service.pop_msg(data.data);
              }
            }
        });
        }
      });
    }

    vm.confirm_print = false;
    vm.confirm_po1 = function() {
      vm.bt_disable = true;
      var that = vm;
      var data = [];
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[Number(key)];
          data.push({name: temp['_aData']["Order Type"], value :temp['_aData']['Supplier ID']});
        }
      });
      vm.service.alert_msg("Do you want to Raise PO").then(function(msg) {
        if (msg == "true") {
          vm.service.apiCall('confirm_po1/', 'POST', data, true).then(function(data){
            if(data.message) {
              vm.confirm_print = false;
              vm.print_enable = true;
              angular.element(".modal-body").html('');
              $state.go('app.inbound.RaisePr.PurchaseOrder');
              vm.service.pop_msg(data.data);
              vm.service.refresh(vm.dtInstance);
              if(data.data.search("<div") != -1) {
                if (vm.model_data.receipt_type == 'Hosted Warehouse') {
                  vm.title = $(data.data).find('.modal-header h4').text().trim();
                }
                vm.html = $(data.data)[0];
                vm.extra_width = {'width': '990px'};
                $timeout(function() {
                  $("#page-pop .modal-body.show").html(vm.html)
                  vm.confirm_print = false;
                }, 2000);
              } else {
                vm.service.pop_msg(data.data);
              }
            }
          });
        } else {
          vm.bt_disable = false;
        }
      });
    }

   vm.delete_po_group = delete_po_group;
   function delete_po_group() {
      vm.bt_disable = true;
      var that = vm;
      var data = [];
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[Number(key)];
          data.push({name: temp['_aData']["Order Type"], value:temp['_aData']['Supplier ID']});
        }
      });
      vm.service.apiCall('delete_po_group/', 'GET', data, true).then(function(data){
        if(data.message) {
           vm.bt_disable = true;
           vm.selectAll = false;
           vm.service.refresh(vm.dtInstance);
        }
      });
   }

   vm.cancel_pr = function cancel_pr() {
      vm.bt_disable = true;
      var that = vm;
      var data = [];
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[Number(key)];
          data.push({name: 'pr_number', value: temp['_aData']["Purchase Id"]});
          data.push({name: 'supplier_id', value:temp['_aData']['Supplier ID']});
          data.push({name: 'is_actual_pr', value:true});
        }
      });
      vm.service.apiCall('cancel_pr/', 'POST', data, true).then(function(data){
        if(data.message) {
          if (data.data == 'Deleted Successfully') {
            vm.bt_disable = true;
            vm.selectAll = false;
            vm.service.refresh(vm.dtInstance);
          } else {
            vm.service.showNoty(data.data);
          }
        }
      });
   }

   vm.get_supplier_sku_prices = function(sku) {
     vm.cleared_data = true;
     var d = $q.defer();
     var data = {sku_codes: sku, suppli_id: vm.model_data.supplier_id}
     vm.service.apiCall("get_supplier_sku_prices/", "POST", data).then(function(data) {

       if(data.message) {
	 if (!$.isEmptyObject(data.data)) {
           d.resolve(data.data);
	 }
       }
     });
     return d.promise;
   }

   vm.get_tax_value = function(sku_data) {
      var tax = 0;
      if (vm.cleared_data) {
            for(var i = 0; i < sku_data.taxes.length; i++) {
                if(sku_data.fields.price <= sku_data.taxes[i].max_amt && sku_data.fields.price >= sku_data.taxes[i].min_amt) {
                    if(vm.model_data.tax_type == "intra_state") {
                        tax = sku_data.taxes[i].sgst_tax + sku_data.taxes[i].cgst_tax;
                        sku_data.fields.sgst_tax = sku_data.taxes[i].sgst_tax;
                        sku_data.fields.cgst_tax = sku_data.taxes[i].cgst_tax;
                        sku_data.fields.igst_tax = 0;
                        sku_data.fields.cess_tax = sku_data.taxes[i].cess_tax;
                        sku_data.fields.apmc_tax = sku_data.taxes[i].apmc_tax;
                    } else if (vm.model_data.tax_type == "inter_state") {
                        sku_data.fields.sgst_tax = 0;
                        sku_data.fields.cgst_tax = 0;
                        sku_data.fields.igst_tax = sku_data.taxes[i].igst_tax;
                        sku_data.fields.cess_tax = sku_data.taxes[i].cess_tax;
                        sku_data.fields.apmc_tax = sku_data.taxes[i].apmc_tax;
                        tax = sku_data.taxes[i].igst_tax;
                    }
                    break;
                }
            }
        }
      sku_data.tax = tax;
      return tax;
   }
   vm.update_available_stock = function(sku_data) {
      var send = {sku_code: sku_data.wms_code, location: "", "includeStoreStock":"true"}
      vm.service.apiCall("get_sku_stock_check/", "GET", send).then(function(data){
        sku_data["capacity"] = 0;
        sku_data["intransit_quantity"] = 0;
        sku_data["skuPack_quantity"] = 0;
        sku_data["openpr_qty"] = 0;
        if(data.message) {
          // if(data.data.available_quantity) {
            sku_data["capacity"] = data.data.available_quantity;
            sku_data["intransit_quantity"] = data.data.intransit_quantity;
            sku_data["openpr_qty"] = data.data.openpr_qty;
            if (data.data.is_contracted_supplier) {
              vm.is_contracted_supplier = true;
            } else if ((!data.data.is_contracted_supplier) && vm.is_contracted_supplier){
              vm.service.showNoty('Contracted Supplier is already selected');
            }
          // }
          if (vm.permissions.sku_pack_config) {
            sku_data["skuPack_quantity"] = data.data.skuPack_quantity;
          }
        }
      });
    }

    vm.get_sku_details = function(product, item, index) {
      vm.clear_raise_po_data(product);
      vm.purchase_history_wms_code = item.wms_code;
      vm.blur_focus_flag = false;
      // if (!vm.model_data.supplier_id && Session.user_profile.user_type != 'marketplace_user' && Session.user_profile.industry_type != 'FMCG') {
      //   product.fields.sku.wms_code = ''
      //   vm.service.showNoty('Fill Supplier ID');
      //   return false;
      // }
      // if (vm.wh_purchase_order && (!vm.model_data.po_delivery_date || typeof(vm.model_data.po_delivery_date) == 'undefined')) {
      //   product.fields.sku.wms_code = ''
      //   vm.service.showNoty('Fill Delivery Date');
      //   return false;
      // }
      if(vm.permissions.show_purchase_history) {
	    $timeout( function() {
	        vm.populate_last_transaction('')
        }, 2000 );
      }
      product.fields.sku.no_of_tests = item.noOfTests;
      product.fields.sku.wms_code = item.wms_code;
      product.fields.measurement_unit = item.measurement_unit;
      product.fields.description = item.sku_desc;
      product.fields.description_edited = item.sku_desc;
      product.fields.hsn_code = item.hsn_code;
      product.fields.sku_brand = item.sku_brand;
      product.fields.sku_class = item.sku_class;
      product.fields.type = item.type;
      product.fields.gl_code = item.gl_code;
      product.fields.service_start_date = item.service_start_date;
      product.fields.service_end_date = item.service_end_date;
      product.fields.order_quantity = 1;
      product.fields.sku.conversion = item.conversion;
      product.fields.conversion = item.conversion * product.fields.order_quantity;
      product.fields.no_of_tests = item.noOfTests;
      product.fields.ean_number = item.ean_number;
      product.fields.price = 0;
      product.fields.mrp = item.mrp;
      product.fields.description = item.sku_desc;
      product.fields.blocked_sku = "";
      product.fields.sgst_tax = "";
      product.fields.cgst_tax = "";
      product.fields.igst_tax = "";
      product.fields.cess_tax = "";
      product.fields.apmc_tax = "";
      product.fields.utgst_tax = "";
      product.fields.tax = "";
      product.fields.openpr_qty = item.openpr_qty;
      product.fields.available_qty = item.available_qty;
      product.fields.openpo_qty = item.openpo_qty;
      product.fields.edit_tax = false;
      product.taxes = [];
      // vm.getTotals();
      if(vm.model_data.receipt_type == 'Hosted Warehouse') {
        vm.model_data.supplier_id = vm.model_data.seller_supplier_map[vm.model_data.seller_type.split(":")[0]];
      }
      if (vm.model_data.supplier_id) {
      vm.get_supplier_sku_prices(item.wms_code).then(function(sku_data){
            sku_data = sku_data[0];
            vm.model_data.tax_type = sku_data.tax_type.replace(" ","_").toLowerCase();
            // sku_data["price"] = product.fields.price;
            // vm.model_data.supplier_sku_prices = sku_data;
            product["taxes"] = sku_data.taxes;
            product["fields"]["edit_tax"] = sku_data.edit_tax;
            vm.get_tax_value(product);
        })
        var supplier = vm.model_data.supplier_id;
        $http.get(Session.url+'get_mapping_values/?wms_code='+product.fields.sku.wms_code+'&supplier_id='+supplier, {withCredentials : true}).success(function(data, status, headers, config) {
          if (data.hasOwnProperty('error_msg')) {
            vm.clear_raise_po_data(product);
            vm.service.showNoty(data['error_msg']);
          } else {
            if(Object.values(data).length) {
              if(data.supplier_mapping)
              {
                vm.clear_raise_po_data(product);
                vm.service.showNoty('Please Create Sku Supplier Mapping');
              }
              else
              {
                product.fields.blocked_sku = data.sku_block
                product.fields.price = data.price;
                product.fields.supplier_code = data.supplier_code;
                product.fields.weight = data.weight;
                vm.model_data.data[index].fields.row_price = (vm.model_data.data[index].fields.order_quantity * Number(vm.model_data.data[index].fields.price));
                // vm.getTotals();
              }
            }
          }
        });
      }
      vm.update_available_stock(product.fields.sku)
    }
    vm.update_wms_records = function(){
      var params_data = {}
      var notify_flag = false;
      if (vm.model_data.data[0].fields.sku.wms_code){
        params_data['supplier_id'] = vm.model_data.supplier_id;
        vm.service.apiCall('get_ep_supplier_value/', 'POST', params_data).then(function(data){
          if(data.message){
            vm.model_data['ep_supplier'] = data.data.ep_supplier_status
            if (vm.model_data['ep_supplier'] == 0) {
              for (var i = 0; i < vm.model_data.data.length; i++) {
                if(vm.model_data.data[i].fields.blocked_sku == 'PO') {
                  if(vm.model_data.data.length == 1){
                    vm.clear_raise_po_data(vm.model_data.data[i])
                    notify_flag = true;
                  }else {
                    vm.model_data.data.splice(i, 1);
                    notify_flag = true;
                  }
                }
              }
              if(notify_flag) {
                vm.service.showNoty('cleared the Blocked Sku');
                notify_flag = false;
              }
            }
          }
        })
      }
    }
    vm.clear_raise_po_data = function(product){
      product.fields.sku.wms_code = '';
      product.fields.measurement_unit = '';
      product.fields.description = '';
      product.fields.order_quantity = '';
      product.fields.ean_number = '';
      product.fields.price = 0;
      product.fields.mrp = '';
      product.fields.description = '';
      product.fields.sgst_tax = "";
      product.fields.cgst_tax = "";
      product.fields.igst_tax = "";
      product.fields.cess_tax = "";
      product.fields.apmc_tax = "";
      product.fields.utgst_tax = "";
      product.fields.tax = "";
      product.fields.blocked_sku = "";
      product.taxes = [];
      vm.cleared_data = false;
    }

    vm.key_event = function(product, item, index) {
      if (typeof(vm.model_data.supplier_id) == "undefined" || vm.model_data.supplier_id.length == 0 || vm.model_data.supplier_id_name == '') {
       return false;
      } else {
        var supplier = vm.model_data.supplier_id;
        $http.get(Session.url+'get_create_order_mapping_values/?wms_code='+product.fields.sku.wms_code, {withCredentials : true}).success(function(data, status, headers, config) {
          if(Object.keys(data).length){
          } else {
            Service.searched_sup_code = supplier;
            Service.searched_wms_code = product.fields.sku.wms_code;
            Service.is_came_from_raise_po = true;
            Service.raise_po_data = vm.model_data;
            Service.raise_po_vendor_receipt = vm.vendor_receipt;
            Service.sku_id_index = index;
            $state.go('app.masters.SKUMaster');
          }
        });
      }
    }

    vm.add_raise_pr = function(elem) {
      if (vm.is_actual_pr){
        elem.push({name:'is_actual_pr', value:true})
      }
      var product_category = '';
      angular.forEach(elem, function(list_obj) {
        if (list_obj['name'] == 'product_category') {
          product_category = list_obj['value']
        }
      });

      var form_data = new FormData();
      if (product_category != "Kits&Consumables" && $(".pr_form").find('[name="files"]').length > 0){
        var files = $(".pr_form").find('[name="files"]')[0].files;
        $.each(files, function(i, file) {
          form_data.append('files-' + i, file);
        });
      }
      $.each(elem, function(i, val) {
        form_data.append(val.name, val.value);
      });
      vm.service.apiCall('validate_wms/', 'POST', elem, true).then(function(data){
        if(data.message){
          if(data.data == 'success') {
            vm.service.apiCall('add_pr/', 'POST', form_data, true, true).then(function(data){
              if(data.message){
                if(data.data == 'Added Successfully') {
                  vm.close();
                  vm.service.refresh(vm.dtInstance);
                } else {
                  vm.service.pop_msg(data.data);
                }
              }
            })
          } else {
            vm.service.pop_msg(data.data);
          }
        }
      });
    }

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 2000);
    }

    vm.html = "";
    vm.print_enable = false;

    vm.print_grn = function() {

      vm.service.print_data(vm.html, "Purchase Order");
    }

    vm.taxChange = function(data) {
      data.fields.tax = Number(data.fields.cgst_tax) + Number(data.fields.sgst_tax) + Number(data.fields.igst_tax) + Number(data.fields.cess_tax) + Number(data.fields.apmc_tax) + Number(data.fields.utgst_tax);
      vm.getTotals(vm.model_data, true);
    }
    vm.check_price_comparision = function(data) {
      var check_array = []
      var min_unit_price_comparision = 0
      if (typeof(data.fields.sku.pr_extra_data.least_supplier_price) != 'undefined' && parseFloat(data.fields.sku.pr_extra_data.least_supplier_price) > 0) {
        check_array.push(parseFloat(data.fields.sku.pr_extra_data.least_supplier_price))
      }
      if (typeof(data.fields.sku.pr_extra_data.last_supplier_price) != 'undefined' && parseFloat(data.fields.sku.pr_extra_data.last_supplier_price) > 0) {
        check_array.push(parseFloat(data.fields.sku.pr_extra_data.last_supplier_price))
      }
      if (typeof(data.fields.sku.pr_extra_data.least_supplier_price_pi) != 'undefined' && parseFloat(data.fields.sku.pr_extra_data.least_supplier_price_pi) > 0) {
        check_array.push(parseFloat(data.fields.sku.pr_extra_data.least_supplier_price_pi))
      }
      min_unit_price_comparision = check_array.length > 0 ? Math.min.apply(null, check_array) : 0
      return min_unit_price_comparision;
    }

    vm.getTotals = function(data, type='') {
      // if(not_update_tax === undefined) {
      //   not_update_tax = false;
      // }
      if (data.fields.discount > 100) {
        Service.showNoty('Discount Percentage Between 0 - 100 ONLY');
        data.fields.discount = 0
        data.fields.final_price = 0
      } else if (type == 'change'){
        data.fields.final_price = parseFloat(data.fields.price) - parseFloat(data.fields.price) * parseFloat((data.fields.discount/100))
      }
      vm.model_data.total_price = 0;
      vm.model_data.sub_total = 0;
      vm.model_data.loss_expected = 0;
      if (data.fields.temp_price && data.fields.temp_price > 0) {
          if (Number(data.fields.price) > Number(data.fields.temp_price)) {
            Service.showNoty('Price cant be more than Base Price'); 
            data.fields.price = 0
        }
      }
      if (data.fields.order_quantity <= parseFloat(data.fields.resubmit_quantity) && parseInt(data.fields.order_quantity) > 0 && data.fields.order_quantity != '') {
        data.fields.order_quantity = data.fields.order_quantity;
      } else if (data.fields.order_quantity == ''){
        data.fields.order_quantity = 0;
      } else {
        data.fields.order_quantity = data.fields.resubmit_quantity;
        Service.showNoty('Quantity cannot be Greater than ' + data.fields.resubmit_quantity);
      }
      data.fields.amount = 0
      data.fields.total = 0
      data.fields.amount = data.fields.order_quantity * Number(parseFloat(data.fields.price) - parseFloat(data.fields.price) * parseFloat((data.fields.discount/100)));
      if (!data.fields.tax) {
          data.fields.tax = 0;
      }
      if (!data.fields.cess_tax) {
        data.fields.cess_tax = 0;
      }
      data.fields.total = ((data.fields.amount / 100) * data.fields.tax) + ((data.fields.amount / 100) * data.fields.cess_tax) + data.fields.amount;
      var min_price_value = vm.check_price_comparision(data);
      if (min_price_value != 0) {
        data.fields.delta = min_price_value - (parseFloat(data.fields.price) + ((parseFloat(data.fields.price) / 100) * parseFloat(data.fields.tax)));
        if (typeof(data.fields.final_price) != 'undefined') {
          if (parseFloat(data.fields.final_price) > 0) {
            data.fields.delta = min_price_value - (parseFloat(data.fields.final_price) + ((parseFloat(data.fields.final_price) / 100) * parseFloat(data.fields.tax)));    
          }
        }
        (data.fields.delta >= 0) ? data['fields']['delta_color'] = { 'color': 'seagreen' } : data['fields']['delta_color'] = { 'color': 'red' };
        data.fields.delta = data.fields.delta * data.fields.order_quantity;
      } else {
        data.fields.delta = 0;
        data.fields['delta_color'] = { 'color': 'darkgrey' };
      }
      angular.forEach(vm.model_data.data, function(sku_data){
        var temp = sku_data.fields.order_quantity * Number(parseFloat(sku_data.fields.price) - parseFloat(sku_data.fields.price) * parseFloat((sku_data.fields.discount/100)));
        sku_data.fields.amount = sku_data.fields.order_quantity * Number(parseFloat(sku_data.fields.price) - parseFloat(sku_data.fields.price) * parseFloat((sku_data.fields.discount/100)));
        if (!sku_data.fields.tax) {
          sku_data.fields.tax = 0;
        }
        if (sku_data.fields.delta < 0) {
          vm.model_data.loss_expected = vm.model_data.loss_expected + sku_data.fields.delta;
        }
        vm.model_data.total_price = vm.model_data.total_price + temp;
        vm.model_data.sub_total = vm.model_data.sub_total + ((temp / 100) * sku_data.fields.tax) + ((temp / 100) * sku_data.fields.cess_tax) +  temp;
      })
    }

    vm.getCompany = function() {

      var temp = vm.model_data.seller_type;
      if (!vm.model_data.seller_type) {
        vm.model_data.company = Session.user_profile.company_name;
        return false;
      }
      temp = temp.toLowerCase()
      if (temp.indexOf('shproc') != -1) {
        vm.model_data.company = 'SHPROC Procurement Pvt. Ltd.'
      } else {
        vm.model_data.company = Session.user_profile.company_name
      }
    }

    vm.last_transaction_table = {}
    vm.last_transaction_wms_code = []
	vm.supplier_level_last_transaction = false
	vm.supplier_wise_table = []
	vm.sku_wise_table = []

	vm.supplier_level = function(toggle_value) {
        vm.supplier_level_last_transaction = toggle_value
        if (vm.supplier_level_last_transaction) {
            vm.last_transaction_table = vm.supplier_wise_table;
        } else {
            vm.last_transaction_table = vm.sku_wise_table;
        }
    }

    vm.populate_last_transaction = function(delete_obj) {
      vm.last_transaction_details = {}
      var new_elem = []
	  var elem = angular.element($('form').find('input[name=supplier_id], select[name=seller_id]'));
      elem = $(elem).serializeArray();
      var wms_code_flag = true;
	  if (delete_obj == 'delete') {
		vm.purchase_history_wms_code = angular.element($('form').find('input[name=wms_code]')).val();
	  } else {
		angular.forEach(elem, function(list_obj) {
			if (list_obj['name'] == 'wms_code') {
				list_obj['value'] = vm.purchase_history_wms_code;
				wms_code_flag = false;
			}
			if (list_obj['value'] != '' && list_obj['value'] != '? undefined:undefined ?' ) {
				new_elem.push(list_obj)
			}
		})
	  }
      if (wms_code_flag) {
		var wms_code_dict = {'name':'wms_code', 'value':vm.purchase_history_wms_code}
		new_elem.push(wms_code_dict)
      }
	  vm.service.apiCall('last_transaction_details/', 'POST', new_elem, true).then(function(data) {
        if (data.message) {
			vm.display_purchase_history_table = true;
            vm.last_transaction_details = data.data;
			vm.supplier_wise_table = data.data.supplier_wise_table_data;
			vm.sku_wise_table = data.data.sku_wise_table_data;
			vm.supplier_level(vm.supplier_level_last_transaction);
        } else {
            vm.last_transaction_details = {};
        }
      });
    }

vm.excel = function(data) {
    vm.headers = ['Supplier', 'WMS Code', 'SKU Desc - HSN code', 'Qty', 'Unit rate', 'Dis', 'Final Unit Price', 'Amount', 'Tax %', 'Cess Tax %', 'Total', 'Last Supplier-Price', 'Least Supplier-Price', 'Least Supplier-Price(Pan India)', 'Reason', 'Delta With Tax', 'Suggested PR qty', 'SKU Brand', 'GL Code', 'UOM', 'Cess Tax', 'No.Of Base Units', 'Base UOM', 'OpenPR Qty', 'Available Stock', 'OpenPO Qty']
    var data = [] 
    data.push(vm.headers)
    for(var i=0; i<vm.model_data.data.length; i++)  {
        let temp_data = [String(vm.model_data.data[i].fields.supplier_id_name), String(vm.model_data.data[i].fields.sku.wms_code), String(vm.model_data.data[i].fields.description + ' -' + vm.model_data.data[i].fields.hsn_code), String(vm.model_data.data[i].fields.order_quantity),
                    String(vm.model_data.data[i].fields.price), String(vm.model_data.data[i].fields.discount), String(vm.model_data.data[i].fields.final_price), String(vm.model_data.data[i].fields.amount), String(vm.model_data.data[i].fields.tax),
                    String(vm.model_data.data[i].fields.cess_tax), String(vm.model_data.data[i].fields.total), String(vm.model_data.data[i].fields.pr_extra_data.last_supplier + ' -' + vm.model_data.data[i].fields.pr_extra_data.last_supplier_price), 
                    String(vm.model_data.data[i].fields.pr_extra_data.least_supplier + ' -' + vm.model_data.data[i].fields.pr_extra_data.least_supplier_price), String(vm.model_data.data[i].fields.pr_extra_data.least_supplier_pi + ' -' + vm.model_data.data[i].fields.pr_extra_data.least_supplier_price_pi), 
                    String(vm.model_data.data[i].fields.sku_comment), String(vm.model_data.data[i].fields.delta), String(vm.model_data.data[i].fields.sku.suggested_pr_qty),
                    String(vm.model_data.data[i].fields.sku_brand), String(vm.model_data.data[i].fields.gl_code), String(vm.model_data.data[i].fields.measurement_unit), String(vm.model_data.data[i].fields.temp_cess_tax), String(vm.model_data.data[i].fields.conversion),
                    String(vm.model_data.data[i].fields.base_uom), String(vm.model_data.data[i].fields.sku.openpr_qty), String(vm.model_data.data[i].fields.sku.capacity), String(vm.model_data.data[i].fields.sku.intransit_quantity)]
        data.push(temp_data)
}
    let file_name = 'Pending_for_Approval_Pr_' +  vm.model_data.pr_number
	vm.service.export_to_excel(data, file_name)
}
  vm.checkSupplierExist = function (sup_id) {
    $http.get(Session.url + 'search_supplier?', {
      params: {
        q: sup_id,
        type: ''
      }
    }).then(function(resp){
      if (resp.data.length == 0) {
        Service.searched_sup_code = sup_id;
        Service.is_came_from_raise_po = true;
        $state.go('app.masters.SupplierMaster.supplier');
      };
    });
  }

vm.checkWHSupplierExist  = function (sup_id) {
    console.log(sup_id);
    $http.get(Session.url + 'search_wh_supplier?', {
      params: {
        q: sup_id,
        type: ''
      }
    }).then(function(resp){
      if (resp.data.length == 0) {
        console.log("No Warehouse Supplier")
      };
    });
  }

  vm.update_tax_details = function(product) {
    if (product.fields.supplier_id_name.includes(':')) {
      product.fields.supplier_id = vm.service.change_search_value(product.fields.supplier_id_name);
      var data = {sku_codes: product.fields.sku.wms_code, suppli_id: product.fields.supplier_id, warehouse_id: vm.model_data.store_id}
      vm.service.apiCall("get_supplier_sku_prices/", "POST", data).then(function(data) {
        if(data.message && data.data.length > 0) {
          data = data.data[0]
          var taxes = data.taxes;
          product.fields.tax = 0;
          product.fields.cess_tax = 0;
          if(taxes.length > 0){
            product.fields.tax = taxes[0].cgst_tax + taxes[0].sgst_tax + taxes[0].igst_tax;
            product.fields.cess_tax = taxes[0].cess_tax;
          }
        }
      });
    }
//    if (vm.model_data.supplier_id) {
//    vm.get_supplier_sku_prices(item.wms_code).then(function(sku_data){
//            sku_data = sku_data[0];
//            vm.model_data.tax_type = sku_data.tax_type.replace(" ","_").toLowerCase();
//            // sku_data["price"] = product.fields.price;
//            // vm.model_data.supplier_sku_prices = sku_data;
//            product["taxes"] = sku_data.taxes;
//            product["fields"]["edit_tax"] = sku_data.edit_tax;
//            vm.get_tax_value(product);
//        })
//        var supplier = vm.model_data.supplier_id;
//        $http.get(Session.url+'get_mapping_values/?wms_code='+product.fields.sku.wms_code+'&supplier_id='+supplier, {withCredentials : true}).success(function(data, status, headers, config) {
//          if (data.hasOwnProperty('error_msg')) {
//            vm.clear_raise_po_data(product);
//            vm.service.showNoty(data['error_msg']);
//          } else {
//            if(Object.values(data).length) {
//              if(data.supplier_mapping)
//              {
//                vm.clear_raise_po_data(product);
//                vm.service.showNoty('Please Create Sku Supplier Mapping');
//              }
//              else
//              {
//                product.fields.blocked_sku = data.sku_block
//                product.fields.price = data.price;
//                product.fields.supplier_code = data.supplier_code;
//                product.fields.weight = data.weight;
//                vm.model_data.data[index].fields.row_price = (vm.model_data.data[index].fields.order_quantity * Number(vm.model_data.data[index].fields.price));
//                // vm.getTotals();
//              }
//            }
//          }
//        });
//      }
//      vm.update_available_stock(product.fields.sku)
    }
}

angular.module('urbanApp').controller('skuSupplierCtrl', function ($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items, Data) {
  var vm = this;
  vm.user_type = Session.roles.permissions.user_type;
  vm.service = Service;
  vm.title = 'ADD SUPPLIER SKU MAPPING';
  vm.costing_type_list = ['Price Based', 'Margin Based','Markup Based'];
  vm.permissions = Session.roles.permissions;
  vm.user_profile = Session.user_profile;
  vm.warehouse_level = vm.user_profile.warehouse_level;
  vm.industry_type = vm.user_profile.industry_type;
  vm.model_data = {}
  vm.model_data.costing_type = 'Price Based';
  vm.requestData = items;
  vm.warehouse_list = [];
  function get_warehouses() {
    vm.service.apiCall('get_warehouse_list/').then(function(data){
      if(data.message) {
        data = data.data;
        var list = [];
        angular.forEach(data.warehouses, function(d){
          list.push({"id": d.warehouse_id, "name": d.warehouse_name})
        });
        vm.warehouse_list = list;
      }
    });
  }
  get_warehouses();
  vm.send_supplier_doa = function(form) {
    vm.model_data['purchase_id'] = vm.requestData['purchase_id'];
    vm.service.apiCall('send_supplier_doa/', 'POST', vm.model_data, true).then(function(data){
      if(data.message) {
        if(data.data == "Added Successfully") {
          vm.close('data');
        } else {
          vm.service.pop_msg(data.data);
        }
      }
    });
  }

  vm.get_sku_mrp = function(wms_code){
    vm.model_data.wms_code = wms_code
    vm.service.apiCall('get_sku_mrp/','POST' ,{'wms_code':JSON.stringify(wms_code)}).then(function(data){
      if(data.message) {
        vm.model_data.mrp = data.data['mrp'];
      }
    })
  }
  vm.get_sku_mrp(vm.requestData['sku_code']);
  vm.close = function (value) {
    $modalInstance.close(value);
  };

});

angular.module('urbanApp').controller('skuRowCtrl', function ($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items, Data) {
  var vm = this;
  vm.user_type = Session.roles.permissions.user_type;
  vm.service = Service;
  vm.service.apiCall('get_extra_row_data/','POST' ,{'wms_code': items['line_data']['fields']['sku']['wms_code'], 'store_id': items['line_data']['store_id'], 'dept_user_id': items['line_data']['dept_user_id']}).then(function(data){
    if(data.message) {
      items['line_data']['fields']['sku']['openpr_qty'] = data.data['openpr_qty'];
      items['line_data']['fields']['sku']['capacity'] = data.data['capacity'];
      items['line_data']['fields']['sku']['intransit_quantity'] = data.data['intransit_quantity'];
      items['line_data']['fields']['sku']['consumption_dict'] = data.data['consumption_dict']
    }
  }) 
  vm.line_data = items['line_data']['fields']
  vm.title = vm.line_data['sku']['wms_code'];
  vm.model_data = {}
  vm.requestData = items;
  vm.warehouse_list = [];
  vm.close = function () {
    $modalInstance.close(vm.line_data);
  };
});
