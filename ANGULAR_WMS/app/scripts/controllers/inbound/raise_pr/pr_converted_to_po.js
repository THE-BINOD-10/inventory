'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PRConvertedtoPO',['$scope', '$http', '$q', '$state', '$rootScope', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', '$modal', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $q, $state, $rootScope, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, Service, $modal, Data) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.extra_width = { 'width': '1250px' };
    vm.selected = {};
    vm.selectAll = false;
    vm.date = new Date();
    vm.update_part = true;
    vm.is_purchase_request = true;
    vm.permissions = Session.roles.permissions;
    vm.user_profile = Session.user_profile;
    vm.industry_type = vm.user_profile.industry_type;
    vm.display_purchase_history_table = false;
    vm.warehouse_type = vm.user_profile.warehouse_type;
    vm.warehouse_level = vm.user_profile.warehouse_level;
    vm.multi_level_system = vm.user_profile.multi_level_system;
    vm.send_sku_dict = {};
    vm.cleared_data = true;
    vm.blur_focus_flag = true;
    vm.supplier_mail_flag = true;
    vm.filters = {'datatable': 'PRConvertedPO', 'search0':'', 'search1':'', 'search2': '', 'search3': ''}
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

    var columns = [ "PR No", "Product Category", "PR Raise By", "PR Created Date",  "Store", "Department", "PO Number",  "Supplier ID", "Supplier Name",
                    "Category", "Total Quantity", "Total Amount",
                    "PO Created Date", "PO Delivery Date",
                     "PO Raise By",  "PO Validation Status", "PO Pending Level", "PO To Be Approved By",
                    "PO Last Updated By", "PO Last Updated At", "Remarks"];
    vm.dtColumns = vm.service.build_colums(columns);
    vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
                .renderWith(function(data, type, full, meta) {
                  if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                    vm.selected = {};
                  }
                  vm.selected[meta.row] = false;
                  return vm.service.frontHtml + meta.row + vm.service.endHtml;
                }))

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
          vm.extra_width = { 'width': '1250px' };
          vm.supplier_id = aData['Supplier ID'];
          var data = {requested_user: aData['Requested User'], purchase_id:aData['Purchase Id'], 
                      pending_level:aData['LevelToBeApproved']};
          vm.dynamic_route(aData);
        });
      });
      return nRow;
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
    vm.title = 'Raise PO';
    vm.bt_disable = true;
    vm.vendor_receipt = false;

    var empty_data = {"supplier_id":"",
                      "po_name": "",
                      "ship_to": "",
                      "supplier_payment_terms": "",
                      "receipt_types": ['Buy & Sell', 'Purchase Order', 'Hosted Warehouse'],
                      "receipt_type": 'Purchase Order',
                      "seller_types": [],
                      "total_price": 0,
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
      var p_data = {requested_user: aData["PR Request User"], purchase_id:aData['Purchase Id'],
                    po_number : aData["PO Number"],
                    pr_number : aData["PR No"],
                    type: "pr_converted_to_po",
                    };
      vm.service.apiCall('generated_actual_pr_data/', 'POST', p_data).then(function(data){
        if (data.message) {
          if (typeof(data.data) == 'string') {
            vm.service.showNoty(data.data);
            return
          }
          var receipt_types = ['Buy & Sell', 'Purchase Order', 'Hosted Warehouse'];
          vm.update_part = false;
          var empty_data = { //"supplier_id":vm.supplier_id,
                  "po_name": "",
                  "ship_to": data.data.ship_to,
                  "terms_condition": data.data.terms_condition,
                  "receipt_type": data.data.receipt_type,
                  "seller_types": [],
                  'is_approval':data.data.is_approval,
                  "validateFlag": data.data.validateFlag,
                  "total_price": 0,
                  "tax": "",
                  "sub_total": "",
                  "pr_delivery_date": data.data.pr_delivery_date,
                  "pr_created_date": data.data.pr_created_date,
                  "product_category": data.data.product_category,
                  "priority_type": data.data.priority_type,
                  "sku_category": data.data.sku_category,
                  'uploaded_file_dict': data.data.uploaded_file_dict,
                  // "supplier_name": data.data.supplier_name,
                  "store": data.data.store,
                  "store_id": data.data.store_id,
                  "department": data.data.department,
                  "data": data.data.data,
          };
          vm.model_data = {};
          vm.resubmitCheckObj = {};
          vm.is_resubmitted = false;
          vm.is_pa_resubmitted = false;
          if (!vm.resubmitting_user) {
              vm.is_pa_resubmitted = true;
          }
          vm.resubmitting_user = data.data.resubmitting_user;
          angular.copy(empty_data, vm.model_data);

          if (vm.model_data.supplier_id){
            vm.model_data['supplier_id_name'] = vm.model_data.supplier_id + ":" + vm.model_data.supplier_name;
          } else {
            vm.model_data['supplier_id_name'] = '';
          }

          if(vm.model_data.uploaded_file_dict && Object.keys(vm.model_data.uploaded_file_dict).length > 0) {
            vm.model_data.uploaded_file_dict.file_url = vm.service.check_image_url(vm.model_data.uploaded_file_dict.file_url);
          }
          vm.model_data.seller_type = vm.model_data.data[0].fields.dedicated_seller;
          vm.dedicated_seller = vm.model_data.data[0].fields.dedicated_seller;

          vm.model_data.levelWiseRemarks = data.data.levelWiseRemarks;
          vm.model_data.enquiryRemarks = data.data.enquiryRemarks;
          vm.model_data.validated_users = data.data.validated_users;
          vm.model_data.approval_remarks = data.data.approval_remarks;
          angular.forEach(vm.model_data.data, function(data){
//            if (!data.fields.cess_tax) {
//              if (data.fields.temp_cess_tax){
//                data.fields.cess_tax = data.fields.temp_cess_tax;
//              }
//            }
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
          console.log(vm.resubmitCheckObj);

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
          vm.resubmit_sku_check = function() {
            vm.is_resubmitted = false;
            var status = true;
            var saved_sku_list = Object.keys(vm.resubmitCheckObj)
            if (saved_sku_list.length != vm.model_data.data.length){
              vm.is_resubmitted = true;
              status = false;
            } else {
              angular.forEach(vm.model_data.data, function(eachField){
                if (!saved_sku_list.includes(eachField.fields.sku.wms_code)) {
                  vm.is_resubmitted = true;
                  status = false;
                }
              })
            }
            return status;
          }

          vm.checkResubmit = function(sku_data){
            if (sku_data.order_quantity && vm.resubmit_sku_check()){
              angular.forEach(vm.model_data.data, function(eachField){
                var oldQty = vm.resubmitCheckObj[eachField.fields.sku.wms_code];
                if (oldQty != parseInt(eachField.fields.order_quantity)){
                  vm.is_resubmitted = true
                  vm.update = true;
                }
              })
            }
          }

          vm.checkResubmitPurchaseApprover = function(sku_data) {
            if (!vm.resubmitting_user) {
              vm.is_pa_resubmitted = true;
              return;
            }
            vm.is_pa_resubmitted = false;
            if (vm.permissions.change_pendinglineitems){
              angular.forEach(vm.model_data.data, function(eachField){
                if (sku_data.preferred_supplier != eachField.fields.supplier_id_name){
                  vm.is_pa_resubmitted = true;
                }
              })
            }
          }

          vm.model_data.suppliers = [vm.model_data.supplier_id];
          vm.model_data.supplier_id = vm.model_data.suppliers[0];
          vm.model_data['po_number'] = aData['PO Number'];
          vm.model_data['pr_number'] = aData['PR No'];
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
          vm.update = true;
          vm.print_enable = true
          $state.go('app.inbound.RaisePr.SavedPurchaseRequest');
          // if (aData['Validation Status'] == 'Approved'){
          //   $state.go('app.inbound.RaisePr.ConvertPRtoPO');
          // } else if (aData['Validation Status'] == 'Store_Sent'){
          //   $state.go('app.inbound.RaisePr.ConvertPRtoPO');
          // } else if (aData['Validation Status'] == 'Saved'){
          //   vm.update = true;
          //   $state.go('app.inbound.RaisePr.SavedPurchaseRequest');
          // } else {
          //   $state.go('app.inbound.RaisePr.ApprovePurchaseRequest');
          // }
        }
    });

    }
    if ($rootScope.$current_po != '') {
      vm.supplier_id = $rootScope.$current_po['Supplier ID'];
      vm.dynamic_route($rootScope.$current_po);
    }
    vm.base = function() {
      vm.title = "Raise PO";
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
    
    vm.sku_record_updation = function(data, records) {
      data.order_quantity = 0;
      angular.forEach(records, function(rows, index){
        if (rows['warehouse_loc']){
          data.order_quantity += parseInt(rows['order_qty']);
        }
        if (index == records.length-1){
          vm.getTotals();
        }
      })
    }
    vm.remove_location_sku = function(main_data, sku, location, datum) {
      for(var i=0; i<vm.send_sku_dict[sku].length; i++) {
        if (vm.send_sku_dict[sku][i]['warehouse_loc'] == location){
          main_data.order_quantity -= parseInt(vm.send_sku_dict[sku][i]['order_qty']);
          vm.send_sku_dict[sku][i]['order_qty'] = 0
          vm.send_sku_dict[sku].splice(i,1);
        }
      }
    }
    vm.reset_warehouse_sku_dict = function(sku, map){
      var temp_data = {
                    'warehouse_loc': '',
                    'available_quantity': 0,
                    'intransit_quantity': 0,
                    'skuPack_quantity': 0,
                    'order_qty': 0
                  }
      if (map) {
        for(var i=0; i<vm.send_sku_dict[sku].length; i++) {
          if (vm.send_sku_dict[sku][i]['warehouse_loc'] == ''){
            vm.service.showNoty('New Record Available for ' + sku);
            break;
          }
          if (i == vm.send_sku_dict[sku].length-1) {
            vm.send_sku_dict[sku].push(temp_data);
            break;
          }
        }
      } else {
        vm.send_sku_dict[sku] = [temp_data];
      }
    }
    vm.confirm_location = function(sku_code, datum, location, record){
      var count = 0;
      for(var i=0; i<vm.send_sku_dict[sku_code].length; i++) {
        if (vm.send_sku_dict[sku_code][i]['warehouse_loc'] == location){
          count = count+1;
          if (count > 1) {
            vm.send_sku_dict[sku_code][i]['warehouse_loc'] = '';
            vm.send_sku_dict[sku_code][i]['available_quantity'] = 0;
            vm.send_sku_dict[sku_code][i]['intransit_quantity'] = 0;
            vm.send_sku_dict[sku_code][i]['skuPack_quantity'] = 0;
            vm.service.showNoty('Location Already Assined for ' + sku_code);
            break;
          }
        }
        if (i == vm.send_sku_dict[sku_code].length-1) {
          record['available_quantity'] = datum['warehouse_data'][location]['available_quantity'];
          record['intransit_quantity'] = datum['warehouse_data'][location]['intransit_quantity'];
          record['skuPack_quantity'] = datum['warehouse_data'][location]['skuPack_quantity'];
          break;
        }
      }
    }
    vm.generate_sku_warehouses = function(record, wms_code) {
      if (wms_code) {
        var data_dict = {
          'sku_code': wms_code,
          'location': '',
          'all_users': JSON.stringify(vm.model_data.warehouse_names)
        }
        vm.service.apiCall('get_warehouse_level_data/', 'GET', data_dict).then(function(data){
          if (data.message) {
            record['warehouses'] = Object.keys(data.data);
            record['warehouse_data'] = data.data;
            vm.reset_warehouse_sku_dict(wms_code, false);
          }
        });
      } else {
        vm.service.showNoty('First Enter The SKU Code *');
      }
    }
    vm.add = function () {
      vm.final_send_sku_dict = {};
      vm.send_sku_dict = {};
      vm.extra_width = { 'width': '1250px' };
      vm.model_data.seller_types = [];
      vm.model_data.product_categories = ['Kits&Consumables', 'Services', 'Assets', 'OtherItems'];

      vm.service.apiCall('get_sellers_list/', 'GET').then(function(data){
        if (data.message) {
          vm.confirm_disabled = false;
          var seller_data = data.data.sellers;
          vm.model_data.tax = data.data.tax;
          vm.model_data.seller_supplier_map = data.data.seller_supplier_map
          vm.model_data.ship_addr_names = data.data.shipment_add_names
          vm.model_data.shipment_addresses = data.data.shipment_addresses
          vm.model_data.warehouse_names = data.data.warehouse
          vm.model_data["receipt_types"] = data.data.receipt_types;
          vm.model_data.terms_condition = (data.data.raise_po_terms_conditions == 'false' ? '' : data.data.raise_po_terms_conditions);
          angular.forEach(seller_data, function(seller_single){
              vm.model_data.seller_types.push(seller_single.id + ':' + seller_single.name);
          });
          Data.seller_types = vm.model_data.seller_types;

          vm.default_status = (Session.user_profile.user_type == 'marketplace_user') ? true: false;


          vm.model_data.receipt_type = 'Purchase Order';
          if (Session.user_profile.user_type == 'marketplace_user') {
            vm.model_data.receipt_type = 'Hosted Warehouse';
          }
          $state.go('app.inbound.RaisePo.PurchaseRequest');
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

    vm.reset_model_data = function(product_category){
      vm.model_data.data = [];
      var emptylineItems = {"wms_code":"", "ean_number": "", "order_quantity":"", "price":0,
                            "measurement_unit": "", "row_price": 0, "tax": "", "is_new":true,
                            "sgst_tax": "", "cgst_tax": "", "igst_tax": "", "utgst_tax": "",
                            "sku": {"wms_code": "", "price":""}
                          }
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

    vm.update_data = function (index, flag=true, plus=false) {
      if (index == vm.model_data.data.length-1) {
        if (vm.model_data.data[index]["fields"]["sku"] && (vm.model_data.data[index]["fields"]["sku"]["wms_code"] && vm.model_data.data[index]["fields"]["order_quantity"]) && (vm.permissions.sku_pack_config ?  vm.sku_pack_validation(vm.model_data.data) : true)) {

          if (plus) {

            vm.model_data.data.push({"fields": {"wms_code":"", "ean_number": "", "supplier_code":"", "order_quantity":"", "price":0,
                                     "measurement_unit": "", "dedicated_seller": vm.model_data.seller_type, "order_quantity": "","row_price": 0,
                                     "sgst_tax": "", "cgst_tax": "", "igst_tax": "", "cess_tax": "", "apmc_tax": "", "utgst_tax": "", "tax": "", "is_new":true
                                     }});

          } else {

            $scope.$apply(function() {

              vm.model_data.data.push({"fields": {"wms_code":"", "ean_number": "", "supplier_code":"", "order_quantity":"", "price":0,
                                       "measurement_unit": "", "dedicated_seller": vm.model_data.seller_type, "order_quantity": "","row_price": 0,
                                       "sgst_tax": "", "cgst_tax": "", "igst_tax": "", "cess_tax": "", "apmc_tax": "","utgst_tax": "", "tax": "", "is_new":true
                                       }});

            });
          }
        } else {

          Service.showNoty('SKU Code and Quantity are required fields. Please fill these first');
        }
      } else {
        if (flag) {
          if (Object.keys(vm.send_sku_dict).includes(vm.model_data.data[index].fields.sku.wms_code)) {
            delete vm.send_sku_dict[vm.model_data.data[index].fields.sku.wms_code];
          }
          if(vm.model_data.data[index].seller_po_id){
              vm.delete_data('seller_po_id', vm.model_data.data[index].seller_po_id, index);
          } else {
              vm.delete_data('id', vm.model_data.data[index].pk, index);
          }
          if(vm.permissions.show_purchase_history) {
              $timeout( function() {
                  vm.populate_last_transaction('delete')
              }, 2000 );
          }
          vm.model_data.data.splice(index,1);
          vm.getTotals();
        }
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

      angular.forEach(vm.model_data.data, function(one_row){
        vm.model_data.total_price = vm.model_data.total_price + (one_row.fields.order_quantity * one_row.fields.price);
      });
            vm.service.pop_msg(data.data);
          }
        });
      }
    }
    vm.confirm_validation = function(type) {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      var confirm_api = vm.permissions.sku_pack_config ?  vm.sku_pack_validation(vm.model_data.data) : true;
      if (type == 'save'){
        confirm_api ? vm.update_raise_pr() : '';
      } else {
        confirm_api ? vm.add_raise_pr(elem) : '';
      }
    }
    vm.save_raise_pr = function(data, type) {
      if (Object.keys(vm.send_sku_dict).length > 0 && vm.permissions.central_admin_level_po) {
        vm.final_send_sku_dict = {}
        angular.forEach(vm.send_sku_dict, function(data, key){
          vm.final_send_sku_dict[key] = {}
          var temp_dict = {}
          for (var i = 0; i < data.length; i++) {
            temp_dict[data[i]['warehouse_loc']] = {
                                           'warehouse_loc': data[i]['warehouse_loc'],
                                           'available_quantity': data[i]['available_quantity'],
                                           'intransit_quantity': data[i]['intransit_quantity'],
                                           'skuPack_quantity': data[i]['skuPack_quantity'],
                                           'order_qty': parseInt(data[i]['order_qty'])
                                          }
            if (i == data.length-1){
              vm.final_send_sku_dict[key] = temp_dict;
            }
          }
        })
      }
      if (data.$valid) {
        if (vm.permissions.central_admin_level_po) {
          if (data.supplier_id.$viewValue && data.pr_delivery_date.$viewValue) {
            vm.confirm_validation(type);
          } else {
            vm.service.showNoty('Please fill required Fields');
          }
        } else if (data.supplier_id.$viewValue && data.pr_delivery_date.$viewValue) {
          vm.confirm_validation(type);
        } else {
          data.supplier_id.$viewValue == '' ? vm.service.showNoty('Please Fill Supplier ID') : '';
          typeof(data.pr_delivery_date.$viewValue) == "undefined" ? vm.service.showNoty('Please Fill PO Delivery Date') : '';
          if (!vm.permissions.central_admin_level_po && typeof(vm.permissions.central_admin_level_po) != 'undefined') {
            vm.model_data.ship_addr_names.length == 0 ? vm.service.showNoty('Please create Shipment Address') : (data.ship_to.$viewValue == '' ? vm.service.showNoty('Please select Ship to Address') : '');
          }
        }
      } else {
        vm.service.showNoty('Please fill * Fields');
      }
    }

    vm.send_back_to_pr = function(form){
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      elem.push({name:'purchase_id', value:vm.model_data.purchase_id})      
      vm.service.apiCall('send_back_po_to_pr/', 'POST', elem, true).then(function(data){
        if(data.message){
          if(data.data == 'Sent Back Successfully') {
            vm.data_id = '';
            vm.close();
            vm.service.refresh(vm.dtInstance);
          } else {
            vm.service.showNoty(data.data);
          }
        }
      });
    }

    vm.approve_pr = function(form, validation_type) {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      elem.push({name:'purchase_id', value:vm.model_data.purchase_id})
      if (vm.is_purchase_request){
        elem.push({name:'is_purchase_request', value:true})
      }
      // if (vm.model_data.pr_number){
      //   elem.push({name:'pr_number', value:vm.model_data.pr_number})
      // }
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
      if (vm.permissions.central_admin_level_po){
        elem.push({name:'data_id', value:vm.data_id});
      }
      vm.service.apiCall('approve_pr/', 'POST', elem, true).then(function(data){
        if(data.message){
          if(data.data == 'Approved Successfully') {
            vm.data_id = '';
            vm.close();
            vm.service.refresh(vm.dtInstance);
          } else {
            vm.service.showNoty(data.data);
          }
        }
      })
    }
  vm.submit_enquiry = function(form){
    var elem = angular.element($('form'));
    elem = elem[0];
    elem = $(elem).serializeArray();
    if (vm.is_purchase_request){
      elem.push({name:'is_purchase_request', value:true})
    }
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

    vm.print_pending_po = function(form, validation_type) {
      if (form.$valid) {
        $http.get(Session.url+'print_pending_po_form/?purchase_id='+vm.model_data.purchase_id + '&currency_rate='+ vm.model_data.supplier_currency_rate +'&supplier_payment_terms='+ vm.model_data.supplier_payment_terms + '&ship_to='+ vm.model_data.shipment_address_select + '&remarks=' + vm.model_data.approval_remarks, {withCredential: true})
        .success(function(data, status, headers, config) {
          vm.service.print_data(data, vm.model_data.purchase_id);
        });
      } else {
        vm.service.showNoty('Please Fill * fields !!');
      }
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

      console.log(vm.barcode_print_data);

      vm.model_data['format_types'] = ['format1', 'format2', 'format3']

      var key_obj = {'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details'}

      $state.go('app.inbound.RaisePo.barcode');
    }

    vm.update_raise_pr = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      if (vm.pr_number){
        elem.push({name:'pr_number', value:vm.pr_number})
      }

      var product_category = '';
      angular.forEach(elem, function(list_obj) {
        if (list_obj['name'] == 'product_category') {
          product_category = list_obj['value']
        }
      });


      var form_data = new FormData();
      if(product_category != "Kits&Consumables" && $(".pr_form").find('[name="files"]').length > 0) {
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
        vm.confirm_disabled = true;
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
      } else {
        vm.service.showNoty('Please Fill * fields !!');
      }
    }
    vm.supplier_notify = function (elems){
      vm.supplier_mail_flag = elems;
    }
    vm.confirm_add_po = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      if (vm.model_data.send_sku_dict && vm.permissions.central_admin_level_po) {
        elem.push({name:"data_id", value: vm.data_id})
        vm.common_confirm('confirm_central_add_po/', elem);
      } else {
        elem.push({'name':'supplier_notify', 'value':vm.supplier_mail_flag})
        vm.common_confirm('confirm_add_po/', elem);
      }
    }

    vm.confirm_pr = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.common_confirm('confirm_pr/', elem);
    }

    vm.common_confirm = function(url, elem) {
      var confirm_url = 'validate_wms/';
      if (vm.is_purchase_request){
        elem.push({name:'is_purchase_request', value:true})
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
                vm.extra_width = {'width': '1150px'};
                vm.html = $(data.data);
                angular.element(".modal-body").html($(data.data));
                vm.print_enable = true;
              } else {
                vm.service.pop_msg(data.data);
              }
            }
            vm.confirm_disabled = false;
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
              $state.go('app.inbound.RaisePo.PurchaseOrder');
              vm.service.pop_msg(data.data);
              vm.service.refresh(vm.dtInstance);
              if(data.data.search("<div") != -1) {
                if (vm.model_data.receipt_type == 'Hosted Warehouse') {
                  vm.title = $(data.data).find('.modal-header h4').text().trim();
                }
                vm.html = $(data.data)[0];
                vm.extra_width = {'width': '1150px'};
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
      var send = {sku_code: sku_data.wms_code, location: ""}
      vm.service.apiCall("get_sku_stock_check/", "GET", send).then(function(data){
        sku_data["capacity"] = 0;
        sku_data["intransit_quantity"] = 0;
        sku_data["skuPack_quantity"] = 0;
        if(data.message) {
          // if(data.data.available_quantity) {
            sku_data["capacity"] = data.data.available_quantity;
            sku_data["intransit_quantity"] = data.data.intransit_quantity;
          // }
          if (vm.permissions.sku_pack_config) {
            sku_data["skuPack_quantity"] = data.data.skuPack_quantity;
          }
        }
      });
    }
	vm.validate_sku_check = function(product, item, index, sku, type){
      if (vm.model_data.data.length ==1 && type=='add' && typeof(sku) !="undefined") {
        vm.get_sku_details(product, item, index);
      } else if (typeof(sku) !="undefined"){
        for (var i = 0; i < vm.model_data.data.length; i++) {
          if (Object.keys(vm.model_data.data[i]['fields']['sku']).includes('capacity')) {
            if (vm.model_data.data[i]['fields']['sku']['wms_code'] == sku.split(' :')[0]) {
              product.fields.sku.wms_code = '';
              vm.service.showNoty('Duplicate Sku Code !!');
              break;
            }
          } else if (i == vm.model_data.data.length-1 && type=='add'){
            vm.get_sku_details(product, item, index);
          }
        }
      } else if (typeof(sku) =="undefined") {
        product.fields.sku = {'price':0, 'wms_code':''}
      }
    }

    vm.validate_sku_check = function(product, item, index, sku, type){
      if (vm.model_data.data.length ==1 && type=='add' && typeof(sku) !="undefined") {
        vm.get_sku_details(product, item, index);
      } else if (typeof(sku) !="undefined"){
        for (var i = 0; i < vm.model_data.data.length; i++) {
          if (Object.keys(vm.model_data.data[i]['fields']['sku']).includes('capacity')) {
            if (vm.model_data.data[i]['fields']['sku']['wms_code'] == sku.split(' :')[0]) {
              product.fields.sku.wms_code = '';
              vm.service.showNoty('Duplicate Sku Code !!');
              break;
            }
          } else if (i == vm.model_data.data.length-1 && type=='add'){
            vm.get_sku_details(product, item, index);
          }
        }
      } else if (typeof(sku) =="undefined") {
        product.fields.sku = {'price':0, 'wms_code':''}
      }
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
      if (vm.permissions.central_admin_level_po) {
        product.fields.order_quantity = '';
      } else {
        product.fields.order_quantity = 1;
      }
      product.fields.sku.wms_code = item.wms_code;
      product.fields.measurement_unit = item.measurement_unit;
      product.fields.description = item.sku_desc;
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
      product.fields.edit_tax = false;
      product.taxes = [];
      vm.getTotals();
      if(vm.model_data.receipt_type == 'Hosted Warehouse') {
        vm.model_data.supplier_id = vm.model_data.seller_supplier_map[vm.model_data.seller_type.split(":")[0]];
      }
      if (vm.model_data.supplier_id) {
      vm.get_supplier_sku_prices(item.wms_code).then(function(sku_data){
            sku_data = sku_data[0];
            vm.model_data.tax_type = sku_data.tax_type.replace(" ","_").toLowerCase();
            //sku_data["price"] = product.fields.price;
            //vm.model_data.supplier_sku_prices = sku_data;
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
                vm.getTotals();
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
      if (vm.model_data.supplier_id) {
        var supplier_data = {'supplier_id':vm.model_data.supplier_id, 'warehouse_id': vm.model_data.warehouse_id}
        vm.service.apiCall('get_supplier_payment_terms/', 'POST', supplier_data).then(function(data){
          if (data.data) {
            vm.model_data.supplier_payment_terms = data.data;
          } else {
            vm.model_data.supplier_payment_terms = '';
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
      product.fields.price = '';
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
      if (vm.is_purchase_request){
        elem.push({name:'is_purchase_request', value:true})
      }
      if (vm.permissions.central_admin_level_po && Object.keys(vm.final_send_sku_dict).length > 0 ) {
        elem.push({name:'ship_to', value:''});
        elem.push({name:'location_sku_data', value:JSON.stringify(vm.final_send_sku_dict)});
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
                  vm.final_send_sku_dict = {};
                  vm.send_sku_dict = {};
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

      data.fields.tax = Number(data.fields.cgst_tax) + Number(data.fields.sgst_tax) + Number(data.fields.igst_tax) + Number(data.fields.apmc_tax) + Number(data.fields.utgst_tax);
      vm.getTotals(vm.model_data, true);
    }

    vm.getTotals = function(data, not_update_tax) {
      if(not_update_tax === undefined) {
        not_update_tax = false;
      }
      vm.model_data.total_price = 0;
      vm.model_data.sub_total = 0;

      angular.forEach(vm.model_data.data, function(sku_data){
        var temp = sku_data.fields.order_quantity * sku_data.fields.price;
        //vm.model_data.supplier_sku_prices.price = sku_data.fields.price;
        if(sku_data.taxes && !not_update_tax) {
            vm.get_tax_value(sku_data);
        }
        if (!sku_data.fields.tax) {
          sku_data.fields.tax = Number(sku_data.fields.cgst_tax) + Number(sku_data.fields.sgst_tax) + Number(sku_data.fields.igst_tax) + Number(sku_data.fields.apmc_tax) +Number(sku_data.fields.utgst_tax);
        }
        vm.model_data.total_price = vm.model_data.total_price + temp;
        vm.model_data.sub_total = vm.model_data.sub_total + ((temp / 100) * sku_data.fields.tax) + ((temp / 100) * sku_data.fields.cess_tax) + temp;
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

  vm.checkSupplierExist = function (sup_id) {
    console.log(sup_id);
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
  vm.sku_delivery_date = function(datam) {
    datam['status'] = vm.pop_up_status;
    var data = datam;
    var modalInstance = $modal.open({
      templateUrl: 'views/inbound/toggle/ApprovalPendingLineItems/po_sku_delivery_date_popup.html',
      controller: 'SkuDeliveryCtrl',
      controllerAs: '$ctrl',
      size: 'md',
      backdrop: 'static',
      keyboard: false,
      resolve: {
        items: function () {
          return data;
        }
      }
    });
    modalInstance.result.then(function (selectedItem) {
      if (selectedItem['status'] == 'success') {
        selectedItem['datum']['price_request'] = true;
      }
    });
  }
}

angular.module('urbanApp').controller('SkuDeliveryCtrl', function ($modalInstance, $modal, items, Service, Session) {
  var vm = this;
  vm.user_type = Session.roles.permissions.user_type;
  vm.date = new Date();
  vm.lineData = items.fields;
  vm.line_id = items.pk;
  vm.status = items.status
  vm.model_data = {}
  vm.service = Service;
  vm.base = function () {
    if (vm.status == 'Saved') {
      vm.status = true;
    } else {
      vm.status = false;
    }
    vm.model_data['sku_code'] = vm.lineData.sku.wms_code;
    vm.model_data['sku_desc'] = vm.lineData['description'];
    vm.model_data['price'] = vm.lineData['price'];
    vm.model_data['order_quantity'] = vm.lineData['order_quantity'];
    vm.model_data['details'] = [];
    var data_to_send = {
      'id': vm.line_id
    }
    vm.service.apiCall('get_po_delivery_schedule/', 'POST', data_to_send, true).then(function(data){
      if(data.message) {
        if (data.data.length > 0) {
          vm.model_data['details'] = data.data;
        } else {
          vm.model_data['details'].push({'delivery_date': '', 'quantity': 0});
        }
      }
    });
  }
  vm.base();
  vm.send_delivery_data = function() {
    if (vm.validation_checks()) {
      var data_to_send = {
        'id': vm.line_id,
        'data': JSON.stringify(vm.model_data['details'])
      }
      vm.service.apiCall('save_po_delivery_schedule/', 'POST', data_to_send, true).then(function(data){
        if(data.message) {
          vm.service.showNoty(data.data);
          vm.cancel('');
        }
      });
    }
  }
  vm.validation_checks = function() {
    var status = false;
    var temp_delivery_date = [];
    var total_count = 0;
    for (var i = 0; i < vm.model_data['details'].length; i++) {
      if (vm.model_data['details'][i]['delivery_date'] && vm.model_data['details'][i]['quantity'] != 0) {
        if (temp_delivery_date.includes(vm.model_data['details'][i]['delivery_date'])) {
          vm.service.showNoty('Delivery Date Should Not be Same !');
          return false;
          break;
        } else {
          temp_delivery_date.push(vm.model_data['details'][i]['delivery_date']);
          total_count = vm.model_data['details'][i]['quantity'] ? parseFloat(total_count) + parseFloat(vm.model_data['details'][i]['quantity']) : parseFloat(total_count);
        }
      } else {
        vm.service.showNoty('Delivery Date (or) Quantity Should Not be Empty !');
        return false;
        break;
      }
      if (i+1 == vm.model_data['details'].length) {
        if (parseFloat(vm.model_data['order_quantity']) == parseFloat(total_count)) {
          return true;
        }else {
          vm.service.showNoty('Quantity Mismatch !');
          return false;
          break;
        }
      }
    }
  }
  vm.cancel = function (data) {
    var temp_dict = '';
    if (data) {
      temp_dict = data;
    } else {
      temp_dict = {
            'status': 'cancel'
          }
    }
    $modalInstance.close(temp_dict);
  };

});
