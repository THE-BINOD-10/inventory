'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('DeliveryChallanCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, Service, $modal) {

    var vm = this;
    vm.apply_filters = colFilters;


    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.user_type = Session.roles.permissions.user_type;

    vm.selected = {};
    vm.checked_items = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.display = false;

    var send = {'tabType': 'DeliveryChallans'};
    vm.service.apiCall("customer_invoice_data/", "GET", send).then(function(data) {
      if(data.message) {
        vm.filters = {'datatable': 'DeliveryChallans', 'search0':'', 'search1':'', 'search2': '', 'search3': ''}
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

    vm.edit_dc = function() {
      var data = [];
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]['_aData'];
          data.push(temp['id']);
        }
      });
      var ids = data.join(",");
      var send = {seller_summary_id: ids, data: true, edit_dc: true};
      
      vm.service.apiCall("generate_customer_invoice/", "GET", send).then(function(data){
        
        if (data.message) {
          vm.mod_data = {};
          angular.copy(data.data, vm.mod_data);
          var modalInstance = $modal.open({
          templateUrl: 'views/outbound/customer_invoices/edit_delivery_challan.html',
          controller: 'EditDeliveryChallan',
          controllerAs: 'pop',
          size: 'lg',
          backdrop: 'static',
          keyboard: false,
          resolve: {
            items: function () {
              return vm.mod_data;
            }
          }
          });

          modalInstance.result.then(function (selectedItem) {
            var data = selectedItem;
          })
        }
      });
    }

    vm.move_to = function (click_type) {
      var po_number = '';
      var status = false;
      var field_name = "";
      var data = [];
      if (vm.user_type == 'distributor') {
        data = vm.checked_ids;
      } else {
        angular.forEach(vm.selected, function(value, key) {
          if(value) {
            var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]['_aData'];
            if(!(po_number)) {
              po_number = temp[temp['check_field']];
            } else if (po_number != temp[temp['check_field']]) {
              status = true;
            }
            field_name = temp['check_field'];
            data.push(temp['id']);
          }
        });
      }

      if(status) {
        vm.service.showNoty("Please select same "+field_name+"'s");
      } else {

        var ids = data.join(",");
        var url = click_type === 'cancel_dc' ? 'move_to_dc/' : 'move_to_inv/';
        var send = {seller_summary_id: ids};
        if (click_type === 'cancel_dc') {
          send['cancel'] = true;
        }
        vm.bt_disable = true;
        vm.service.apiCall(url, "GET", send).then(function(data){
          if(data.message) {
            console.log(data.message);
            vm.reloadData();
          } else {
            vm.service.showNoty("Something went wrong while moving to DC !!!");
          }
        })
      }
    };

    vm.reloadData = function () {
      $('.custom-table').DataTable().draw();
    };

    vm.generate_invoice = function(click_type, DC=false){

      var po_number = '';
      var status = false;
      var field_name = "";
      var data = [];
      if (vm.user_type == 'distributor') {
        data = vm.checked_ids;
      } else {
        angular.forEach(vm.selected, function(value, key) {
          if(value) {
            var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]['_aData'];
            if(!(po_number)) {
              po_number = temp[temp['check_field']];
            } else if (po_number != temp[temp['check_field']]) {
              status = true;
            }
            field_name = temp['check_field'];
            data.push(temp['id']);
          }
        });
      }

      if(status) {
        vm.service.showNoty("Please select same "+field_name+"'s");
      } else {

        var ids = data.join(",");
        var send = {seller_summary_id: ids};
        if(po_number && field_name == 'SOR ID') {
          send['sor_id'] = po_number;
        }
        if(click_type == 'edit'){
          send['data'] = true;
          send['edit_invoice'] = true;
        }
        send['delivery_challan'] = DC;
        vm.delivery_challan = DC;
        vm.bt_disable = true;
        vm.service.apiCall("generate_customer_invoice/", "GET", send).then(function(data){

          if(data.message) {
            if(click_type == 'generate') {
              vm.pdf_data = data.data;
              if(typeof(vm.pdf_data) == "string" && vm.pdf_data.search("print-invoice") != -1) {
                $state.go("app.outbound.CustomerInvoices.InvoiceE");
                $timeout(function () {
                  $(".modal-body:visible").html(vm.pdf_data)
                }, 3000);
              } else if(Session.user_profile.user_type == "marketplace_user") {
                $state.go("app.outbound.CustomerInvoices.InvoiceM");
              } else if(vm.permissions.detailed_invoice) {
                $state.go("app.outbound.CustomerInvoices.InvoiceD");
              } else {
                $state.go("app.outbound.CustomerInvoices.InvoiceN");
              }
            } else {
              var mod_data = data.data;
              var modalInstance = $modal.open({
              templateUrl: 'views/outbound/toggle/edit_invoice.html',
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
              })
            }
          }
          vm.bt_disable = false;
        });
      }
    }

    vm.close = function() {
      $state.go("app.outbound.CustomerInvoices")
    };
}

function EditDeliveryChallan($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {

  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  vm.priceband_sync = Session.roles.permissions.priceband_sync;

  vm.model_data = items;

  vm.ok = function () {
    $modalInstance.close("close");
  };

  vm.update_data = function (index) {
    console.log(index);
    if (index == vm.model_data.data.length-1) {
      vm.model_data.data.push({"sku_code": "", "sku_class": "", "pkng": "", "quantity": ""});
    } else {
      if(vm.model_data.data[index].order_id){
        vm.delete_data('order_id', vm.model_data.data[index].order_id, index);
      } else {
        vm.delete_data('id', vm.model_data.data[index].id, index);
      }
      vm.model_data.data.splice(index,1);
      vm.getTotals();
    }
  };

  vm.delete_data = function(key, id, index) {
    if(id) {
      var del_data = {}
      del_data[key] = id;
      vm.service.apiCall('delete_po/', 'GET', del_data).then(function(data){
        if(data.message) {
    vm.model_data.data[index].row_price = (vm.model_data.data[index].order_quantity * Number(vm.model_data.data[index].price))
;
    vm.model_data.total_price = 0;

    angular.forEach(vm.model_data.data, function(one_row){
      vm.model_data.total_price = vm.model_data.total_price + (one_row.order_quantity * one_row.price);
    });
          vm.service.pop_msg(data.data);
        }
      });
    }
  };

  vm.getTotals = function(data) {
    vm.model_data.total_price = 0;
    vm.model_data.sub_total = 0;
    angular.forEach(vm.model_data.data, function(sku_data){
      var temp = sku_data.order_quantity * sku_data.price;
      if (!sku_data.tax) {
        sku_data.tax = Number(sku_data.cgst_tax) + Number(sku_data.sgst_tax) + Number(sku_data.igst_tax) + Number(sku_data.utgst_tax);
      }
      vm.model_data.total_price = vm.model_data.total_price + temp;
      vm.model_data.sub_total = vm.model_data.sub_total + ((temp / 100) * sku_data.tax) + temp;
    })
  }

  vm.get_sku_details = function(product, item, index) {
    product.wms_code = item.wms_code;
    product.measurement_unit = item.measurement_unit;
    product.description = item.sku_desc;
    product.order_quantity = 1;
    product.price = "";
    product.description = item.sku_desc;
    product.sgst_tax = "";
    product.cgst_tax = "";
    product.igst_tax = "";
    product.utgst_tax = "";
    product.tax = "";
    vm.getTotals();

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

}

stockone = angular.module('urbanApp');

stockone.controller('EditDeliveryChallan', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', EditDeliveryChallan]);