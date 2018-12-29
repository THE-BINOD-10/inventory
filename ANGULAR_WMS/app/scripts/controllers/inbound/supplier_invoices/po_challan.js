'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('POChallanCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, Service, $modal) {

    var vm = this;
    vm.apply_filters = colFilters;


    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.user_type = Session.roles.permissions.user_type;
    vm.industry_type = Session.user_profile.industry_type;
    vm.parent_username = Session.parent.userName;
    vm.milkbasket_users = ['milkbasket', 'milkbasket_noida', 'milkbasket_test', 'milkbasket_bangalore'];

    vm.selected = {};
    vm.checked_items = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.display = false;

    var send = {'tabType': 'POChallans'};
    vm.service.apiCall("supplier_invoice_data/", "GET", send).then(function(data) {
      if(data.message) {
        vm.filters = {'datatable': 'POChallans', 'search0':'', 'search1':'', 'search2': '', 'search3': ''}
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
          })
          .withOption('processing', true)
          .withOption('serverSide', true)
          .withOption('order', [5, 'desc'])
          .withOption('lengthMenu', [10, 100, 200, 300, 400, 500, 1000, 2000])
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
          .withOption('initComplete', function( settings ) {
            //vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
          });

        var columns = data.data.headers;
        var not_sort = ['Order Quantity', 'Picked Quantity']
        vm.dtColumns = vm.service.build_colums(columns, not_sort);
        vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle('').notSortable().withOption('width', '20px')
               .renderWith(function(data, type, full, meta) {
                 if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                   vm.selected = {};
                 }
                 vm.selected[meta.row] = vm.selectAll;
                 return vm.service.frontHtml + meta.row + vm.service.endHtml;
               }))

        vm.dtInstance = {};

        $scope.$on('change_filters_data', function(){
          if($("#"+vm.dtInstance.id+":visible").length != 0) {
            vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
            vm.service.refresh(vm.dtInstance);
          }
        });
        vm.display = true;
      }
    });

    vm.generate_invoice = function(click_type, DC='false', move_to_inv='false'){

      var supplier_name = '';
      var status = false;
      var field_name = "";
      var data = [];
      var send_data = {};
      if (vm.user_type == 'distributor') {
        data = vm.checked_ids;
      } else {
        angular.forEach(vm.selected, function(value, key) {
          if(value) {
            var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]['_aData'];
            if(!(supplier_name)) {
              supplier_name = temp['Supplier Name'];
            } else if (supplier_name != temp['Supplier Name']) {
              status = true;
            }
            field_name = temp['check_field'];
            var grn_no = temp['GRN No'];
            grn_no = grn_no.split('/');

            if(click_type == 'edit'){
              send_data = JSON.stringify({
                grn_no: grn_no, 
                seller_summary_name: temp['Supplier Name'], 
                seller_summary_id: temp['id'], 
                purchase_order__order_id: temp['purchase_order__order_id'],
                receipt_number: temp['receipt_number'],
                challan_id: temp['Challan ID'],
                data: 'true',
                edit_invoice: 'true',
                edit_poc: 'false',
                po_challan: DC
              });
            } else {
              send_data = JSON.stringify({
                grn_no: grn_no, 
                seller_summary_name: temp['Supplier Name'], 
                seller_summary_id: temp['id'], 
                purchase_order__order_id: temp['purchase_order__order_id'],
                receipt_number: temp['receipt_number'],
                challan_id: temp['Challan ID']
              });
            }

            data.push(send_data);
          }
        });
      }

      if(status) {
        vm.service.showNoty("Please select same "+field_name+"'s");
      } else {
        var send = data.join(",");
        send = {data: send}
        vm.delivery_challan = DC;
        vm.bt_disable = true;
        vm.service.apiCall("generate_supplier_invoice/", "GET", send).then(function(data){

          if(data.message) {
            if(click_type == 'generate') {
              vm.pdf_data = data.data;
	      vm.pdf_data["move_to_inv"] = move_to_inv;
              if(typeof(vm.pdf_data) == "string" && vm.pdf_data.search("print-invoice") != -1) {
                $state.go("app.inbound.SupplierInvoice.InvoiceE");
                $timeout(function () {
                  $(".modal-body:visible").html(vm.pdf_data)
                }, 3000);
              // } else if(Session.user_profile.user_type == "marketplace_user") {
              //   $state.go("app.inbound.SupplierInvoices.InvoiceM");
              // } else if(vm.permissions.detailed_invoice) {
              //   $state.go("app.inbound.SupplierInvoices.InvoiceD");
              } else {
                $state.go("app.inbound.SupplierInvoice.InvoiceN");
              }
            } else {
              var mod_data = data.data;
              var modalInstance = $modal.open({
              templateUrl: 'views/inbound/toggle/edit_invoice.html',
              controller: 'EditInvoice',
              controllerAs: 'pop',
              size: 'lg',
              backdrop: 'static',
              keyboard: false,
              resolve: {
                items: function () {
                  return mod_data;
                }
              }
              });

              modalInstance.result.then(function (selectedItem) {
                var data = selectedItem;
                vm.reloadData();
              })
            }
          }
          vm.bt_disable = false;
        });
      }
    }

    vm.move_to = function (click_type) {
    var supplier_name = '';
    var status = false;
    var field_name = "";
    var data = [];
    var send_data = {};
    if (vm.user_type == 'distributor') {
      data = vm.checked_ids;
    } else {
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]['_aData'];
          if(!(supplier_name)) {
            supplier_name = temp['Supplier Name'];
          } else if (supplier_name != temp['Supplier Name']) {
            status = true;
          }
          field_name = temp['check_field'];
          var grn_no = temp['GRN No'];
          grn_no = grn_no.split('/');

          if(click_type == 'cancel_poc'){
              send_data = JSON.stringify({
                grn_no: grn_no,
                invoice_number: temp['invoice_number'],
                seller_summary_name: supplier_name, 
                seller_summary_id: temp['id'], 
                purchase_order__order_id: temp['purchase_order__order_id'],
                receipt_number: temp['receipt_number'],
                cancel: 'true'
              });
            } else {
              send_data = JSON.stringify({
                grn_no: grn_no,
                invoice_number: temp['invoice_number'],
                seller_summary_name: supplier_name, 
                seller_summary_id: temp['id'], 
                purchase_order__order_id: temp['purchase_order__order_id'],
                receipt_number: temp['receipt_number']
              });
            }

          data.push(send_data);
        }
      });
    }

    if(status) {
      vm.service.showNoty("Please select same "+field_name+"'s");
    } else {

      if (click_type == 'move_to_inv') {

	vm.move_to_inv_data = data;
	vm.generate_invoice('generate', 'true', 'true');
      } else {
        vm.move_to_api(click_type, data);
      }
    }
  };

  vm.confirm_move_to_inv = function(){
    if(!vm.inv_number || !vm.inv_date){
      vm.service.showNoty("Please enter invoice number and invoice date");
    } else{
      vm.move_to_api("move_to_invoice/", vm.move_to_inv_data);
    }
  }

  vm.move_to_api = function(click_type, data){
    var send = data.join(",");
    send = {data: send, inv_number: vm.inv_number, inv_date: vm.inv_date}
    var url = click_type === 'cancel_poc' ? 'move_to_po_challan/' : 'move_to_invoice/';
    vm.bt_disable = true;
    var form_data = new FormData();
    angular.forEach(send, function(val, key) {
      form_data.append(key, val);
    });
    if(click_type == 'move_to_invoice/') {
      if(vm.milkbasket_users.indexOf(vm.parent_username) >= 0) {
        if($("body #add-customer").find('[name="files"]')[0].files.length < 1) {
          vm.service.showNoty("Uploading file is mandatory");
          return
        }
      }
      var files = $("body #add-customer").find('[name="files"]')[0].files;
      $.each(files, function(i, file) {
        form_data.append('files-' + i, file);
      });
    }
    vm.service.apiCall(url, 'POST', form_data, true, true).then(function(data){
      if(data.message) {
        console.log(data.data);
        var response_data = JSON.parse(data.data)
        if(response_data.message == 'success'){
          vm.invoice_number = '';
          vm.invoice_date = '';
          vm.close();
          vm.reloadData();
        }
        else {
          vm.service.showNoty(response_data.message);
        }
      } else {
        vm.service.showNoty("Something went wrong while moving to po challan !!!");
      }
    });
  }

  vm.reloadData = function () {
    $('.custom-table').DataTable().draw();
  };

    vm.edit_poc = function() {

      var send_data = '';
      var flag = false;
      var send = {};
      var sel_items = [];
      angular.forEach(vm.selected, function(value, key) {

        if(value) {
          sel_items.push(key);
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]['_aData'];
          var grn_no = temp['GRN No'];
          grn_no = grn_no.split('/');

          send_data = JSON.stringify({
            grn_no: grn_no, 
            seller_summary_name: temp['Supplier Name'], 
            seller_summary_id: temp['id'], 
            purchase_order__order_id: temp['purchase_order__order_id'],
            receipt_number: temp['receipt_number'],
            challan_id: temp['Challan ID']
          });
        }
      });

      if (sel_items.length == 1) {
        send = {data: send_data};
        vm.service.apiCall("generate_supplier_invoice/", "GET", send).then(function(data){

          if (data.message) {
          var mod_data = data.data;
          var modalInstance = $modal.open({
            templateUrl: 'views/inbound/toggle/edit_invoice.html',
            controller: 'EditPOChallan',
            controllerAs: 'pop',
            size: 'lg',
            backdrop: 'static',
            keyboard: false,
            resolve: {
              items: function () {
                return mod_data;
              }
            }
          });

          modalInstance.result.then(function (selectedItem) {
            var data = selectedItem;
            vm.reloadData();
            vm.bt_disable = true;
          })
          }
        })
      } else {
        vm.service.showNoty("Something went wrong while, Please select signle item at a time");
      }
    }

    vm.close = function() {
      $state.go("app.inbound.SupplierInvoice")
    };
}

function EditPOChallan($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {

  var vm = this;
  vm.service = Service;
  vm.process = false;
  vm.permissions = Session.roles.permissions;
  vm.priceband_sync = Session.roles.permissions.priceband_sync;

  vm.model_data = items;
  vm.model_data.total_qty = 0;
  vm.model_data.total_items = 0;

  vm.ok = function () {
    $modalInstance.close("close");
  };

  vm.removed_data = [];
  vm.update_data = function (index) {
    console.log(index);
    if (index == vm.model_data.data.length-1) {
      vm.model_data.data.push({"sku_code": "", "sku_desc": "", "pkng": "", "quantity": 0,
                "unit_price": 0, "taxes": {"cgst_tax": 0, "sgst_tax": 0,
                "igst_tax": 0}, "amt": 0, "tax": 0, "invoice_amount": 0});

      /*vm.model_data.data.push(
        "sku_code":"",
        "taxes":{"igst_tax":0,"cgst_amt":0,"cgst_tax":0,"sgst_amt":0,"igst_amt":0,"utgst_tax":0,"utgst_amt":0,"sgst_tax":0},
        "amt":0,
        "open_po_id":0,
        "title":"",
        "tax_type":"",
        "seller_summary_id":0,
        "unit_price":0,
        "hsn_code":"",
        "shipment_date":"",
        "invoice_amount":0,
        "quantity":0,
        "tax":0,
      );*/
    } else {
      vm.model_data.data[index].quantity = 0;
      vm.removed_data.push(vm.model_data.data[index]);
      vm.model_data.data.splice(index,1);
      vm.getTotals();
    }
  };

  vm.getTotals = function(data) {
    vm.model_data.total_items = vm.model_data.data.length;
    vm.model_data.total_qty = 0;
    angular.forEach(vm.model_data.data, function(sku_data){
      if (sku_data.quantity != "" || typeof sku_data.quantity != 'undefined') {
        // sku_data.quantity = ''
        vm.model_data.total_qty += parseInt(sku_data.quantity);
      }
    })
  }

  vm.change_quantity = function(data) {

    var flag = false;
    if(data.priceRanges && data.priceRanges.length > 0) {

      for(var skuRec = 0; skuRec < data.priceRanges.length; skuRec++){
    
        if(data.quantity >= data.priceRanges[skuRec].min_unit_range && data.quantity <= data.priceRanges[skuRec].max_unit_range){
    
          data.unit_price = data.priceRanges[skuRec].price;
          flag = true;
        }
      }

      if (!flag) {
    
        data.unit_price = data.priceRanges[data.priceRanges.length-1].price;
      }
    }

    data.base_price = vm.service.multi(data.quantity, data.unit_price);
    vm.changeUnitPrice(data);
  }

  vm.changeUnitPrice = function(data) {

    var total = data.quantity * Number(data.unit_price);
    // data.discount = (data.base_price/100)*Number(data.discount_percentage) | 0;
    data.amt = total;
    var taxes = {cgst_amt: 'cgst_tax', sgst_amt: 'sgst_tax', igst_amt: 'igst_tax', utgst_amt: 'utgst_tax'};
    data.tax = 0;

    angular.forEach(taxes, function(tax_name, tax_amount){

      if (data.taxes[tax_name] > 0){ 

        data.taxes[tax_amount] = (total/100)*data.taxes[tax_name];
      } else {

        data.taxes[tax_amount] = 0;
      }   
       data.tax += data.taxes[tax_amount];
    })  
    data.invoice_amount = (total) + (data.tax);
  }

  angular.forEach(vm.model_data.data, function(sku){
    vm.changeUnitPrice(sku);
  });

  vm.get_sku_details = function(product, item, index) {
    product.wms_code = item.wms_code;
    product.measurement_unit = item.measurement_unit;
    product.sku_desc = item.sku_desc;
    product.title = item.sku_desc;
    product.order_quantity = 1;
    product.price = "";
    product.sgst_tax = "";
    product.cgst_tax = "";
    product.igst_tax = "";
    product.utgst_tax = "";
    product.tax = "";
    product.unit_price = 0;

    var tax_dict = {0:"intra_state", 1:"inter_state", 2:"default"};
    var data = {sku_codes: item.wms_code, cust_id: vm.model_data.customer_id, tax_type: tax_dict[vm.model_data.tax_type]}
    vm.service.apiCall("get_customer_sku_prices/", "POST", data).then(function(data) {

      if(data.message) {
        product.unit_price = data.data[0].price;
      }
    product.quantity = 1;
    product.taxes = {"sgst_tax": 0, "cgst_tax": 0, "igst_tax": 0};
    vm.getTotals();
    vm.changeUnitPrice(product);
    });

    if(vm.model_data.receipt_type == 'Hosted Warehouse') {

      vm.model_data.supplier_id = vm.model_data.seller_supplier_map[vm.model_data.seller_type.split(":")[0]];
    }

    if (!vm.model_data.supplier_id){
      return false;
    } else {
      var supplier = vm.model_data.supplier_id;
      $http.get(Session.url+'get_mapping_values/?wms_code='+product.wms_code+'&supplier_id='+supplier, {withCredentials : true}).success(function(data, status, headers, config) {
        if(Object.values(data).length) {
          product.price = data.price;
          product.supplier_code = data.supplier_code;
          product.ean_number = data.ean_number;

          vm.model_data.data[index].row_price = (vm.model_data.data[index].order_quantity * Number(vm.model_data.data[index].price));
          vm.getTotals();
        }
      });
    }
  }

  vm.getTotals();

  vm.update_poc = function(form_data) {
    var update_poc_data = {};
    update_poc_data.form_data = {
      'challan_date': form_data.challan_date.$modelValue,
      'challan_no': form_data.challan_no.$modelValue,
      'rep': form_data.rep.$modelValue,
      'order_no': form_data.order_no.$modelValue,
      'pick_number': form_data.pick_number.$modelValue,
      'supplier_id': form_data.supplier_id.$modelValue,
      'lr_no': form_data.lr_no.$modelValue,
      'carrier': form_data.carrier.$modelValue,
      'terms': form_data.terms.$modelValue,
      'pkgs': form_data.pkgs.$modelValue,
      'address': form_data.address.$modelValue,
      'wms_code': form_data.wms_code.$modelValue
    };

    angular.forEach(vm.removed_data, function(data){
      vm.model_data.data.push(data);
    });

    update_poc_data.data = JSON.stringify(vm.model_data.data);
    vm.process = true;

    vm.service.apiCall('update_poc/', 'POST', update_poc_data).then(function(resp){
      if(resp.message) {
        console.log(resp);
        if(resp.data.message == 'success') {
          console.log('success');
          Service.showNoty("Updated Successfully");
          $modalInstance.close("saved");
        }
      } else {
        Service.showNoty("Something went wrong !");
      }
    });
  };

}

stockone = angular.module('urbanApp');

stockone.controller('EditPOChallan', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', EditPOChallan]);
