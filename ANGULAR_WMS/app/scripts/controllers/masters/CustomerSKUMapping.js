'use strict';

angular.module('urbanApp', ['datatables', 'ngAnimate', 'ui.bootstrap'])
  .controller('CustomerSKUMappingTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder',  'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.apply_filters = colFilters;

    vm.filters = {'datatable': 'CustomerSKUMapping', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    vm.dtColumns = [
        DTColumnBuilder.newColumn('customer_id').withTitle('Customer ID'),
        DTColumnBuilder.newColumn('customer_name').withTitle('Customer Name'),
        DTColumnBuilder.newColumn('sku_code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('price').withTitle('Price')
    ];

    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                angular.copy(aData, vm.model_data);
                vm.update = true;
                vm.title = "Update Customer SKU";
                $state.go("app.masters.Customer-SKUMapping.CustomerSKU");
            });
        });
        return nRow;
    }

    var empty_data = {"customer_id":"", "customer_name":"", "sku_code":"", "price":""};
    vm.model_data = {};

    vm.base = function() {

      vm.title = "Add Customer SKU";
      vm.update = false;
      angular.copy(empty_data, vm.model_data);
    }
    vm.base();

    vm.close = function() {

      angular.copy(empty_data, vm.model_data);
      $state.go('app.masters.Customer-SKUMapping');
    }

    vm.add = function() {

      vm.base();
      $state.go('app.masters.Customer-SKUMapping.CustomerSKU');
    }

  vm.customer = function(url) {
    vm.service.apiCall(url, 'POST', vm.model_data, true).then(function(data){
      if(data.message) {
        if(data.data == 'New Customer SKU Mapping Added' || data.data == 'Updated Successfully') {
          vm.service.refresh(vm.dtInstance);
          vm.close();
        } else {
          vm.service.pop_msg(data.data);
        }
      }
    });
  }

  vm.submit = function(data) {

    if (data.$valid) {
      if ("Add Customer SKU" == vm.title) {
        delete vm.model_data.customer_name
        vm.customer('insert_customer_sku/');
      } else {
        vm.model_data['data-id'] = vm.model_data.DT_RowId;
        vm.customer('update_customer_sku_mapping/');
      }
    }
  }

}

