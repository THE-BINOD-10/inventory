'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('POChallanCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', '$modal', ServerSideProcessingCtrl]);

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

    vm.move_to = function (click_type) {
    var supplier_name = '';
    var status = false;
    var field_name = "";
    var data = [];
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

          var send_data = JSON.stringify({grn_no: grn_no, seller_summary_name: supplier_name, seller_summary_id: temp['id']});

          data.push(send_data);
        }
      });
    }

    if(status) {
      vm.service.showNoty("Please select same "+field_name+"'s");
    } else {

      var send = data.join(",");
      send = {data: send}
      var url = click_type === 'move_to_po_challan' ? 'move_to_po_challan/' : 'move_to_inv/';
      vm.bt_disable = true;
      vm.service.apiCall(url, "GET", send).then(function(data){
        if(data.message) {
          console.log(data.message);
          vm.reloadData();
        } else {
          vm.service.showNoty("Something went wrong while moving to po challan !!!");
        }
      })
    }
  };

    vm.edit_poc = function() {

      var data = [];
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]['_aData'];
          data.push(temp['id']);
        }
      });
      var ids = data.join(",");
      ids = ids.split('/');
      var send = {grn_numbers: angular.toJson(ids), data: true};
      vm.service.apiCall("generate_supplier_invoice/", "GET", send).then(function(data){

        // if (data.message) {
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
        })
        // }
      })
    }

}

function EditInvoice($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {

  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  vm.priceband_sync = Session.roles.permissions.priceband_sync;

  vm.model_data = items;
  vm.model_data.temp_sequence_number = vm.model_data.sequence_number;

  vm.model_data.default_charge = function(){

    if (vm.model_data.order_charges.length == 1) {

      vm.model_data.flag = true;
    }
  }

  vm.delete_charge = function(id){

    if (id) {

      vm.service.apiCall("delete_order_charges?id="+id, "GET").then(function(data){

        if(data.message){

          Service.showNoty(data.data.message);
        }
      });
    }
  }

  $timeout(function() {

    $('[name="invoice_date"]').datepicker("setDate", new Date(vm.model_data.inv_date) );
  },1000);
  vm.ok = function () {

    $modalInstance.close("close");
  };

  vm.process = false;
  vm.save = function(form) {

    if (vm.permissions.increment_invoice && vm.model_data.sequence_number && form.invoice_number.$invalid) {

      Service.showNoty("Please Fill Invoice Number");
      return false;
    } else if (!form.$valid) {

      Service.showNoty("Please Fill the Mandatory Fields");
      return false;
    }
    vm.process = true;
    var data = $("form:visible").serializeArray()
    Service.apiCall("update_invoice/", "POST", data).then(function(data) {

      if(data.message) {

        if(data.data.msg == 'success') {

          Service.showNoty("Updated Successfully");
          $modalInstance.close("saved");
        } else {

          Service.showNoty(data.data.msg);
        }
      } else {

        Service.showNoty("Update fail");
      }
      vm.process = false;
    })
  }

  vm.changeUnitPrice = function(data) {

    data.base_price = data.quantity * Number(data.unit_price);
    data.discount = (data.base_price/100)*Number(data.discount_percentage);
    data.amt = data.base_price - data.discount;
    var taxes = {cgst_amt: 'cgst_tax', sgst_amt: 'sgst_tax', igst_amt: 'igst_tax', utgst_amt: 'utgst_tax'};
    data.total_tax_amount = 0;

    angular.forEach(taxes, function(tax_name, tax_amount){

      if (data.taxes[tax_name] > 0){

        data.taxes[tax_amount] = (data.amt/100)*data.taxes[tax_name];
      } else {

        data.taxes[tax_amount] = 0;
      }
       data.total_tax_amount += data.taxes[tax_amount];
    })
    data.invoice_amount = (data.amt + data.total_tax_amount);
  }
}
stockone = angular.module('urbanApp');

stockone.controller('EditInvoice', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', EditInvoice]);

/*stockone.directive('genericCustomerInvoiceData', function() {
  return {
    restrict: 'E',
    scope: {
      invoice_data: '=data',
    },
    templateUrl: 'views/outbound/toggle/invoice_data_html.html',
    link: function(scope, element, attributes, $http, Service){
      console.log(scope);
    }
  };
});*/