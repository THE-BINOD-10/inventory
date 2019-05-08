'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SupplierSKUMappingTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.filters = {'datatable': 'SupplierSKUMappingMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
        DTColumnBuilder.newColumn('supplier_id').withTitle('Supplier ID'),
        DTColumnBuilder.newColumn('wms_code').withTitle('WMS Code'),
        DTColumnBuilder.newColumn('supplier_code').withTitle("Supplier's SKU Code"),
        DTColumnBuilder.newColumn('preference').withTitle('Priority'),
        DTColumnBuilder.newColumn('moq').withTitle('MOQ'),
    ];

    vm.dtInstance = {};

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.model_data['create_login'] = false;
                angular.copy(aData, vm.model_data);
                vm.update = true;
                vm.title = "Update Supplier SKU";
                $state.go('app.masters.sourceSKUMapping.mapping');
            });
        });
        return nRow;
    }

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

  /**************************************/
  vm.update = false;
  var empty_data = {supplier_id: "", wms_code: "", supplier_code: "", preference: "", moq: "", price: ""};
  vm.model_data = {};
  angular.copy(empty_data, vm.model_data);

  //close popup
  vm.close = function() {

    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.sourceSKUMapping');
  }

  // open popup for new supplier sku mapping
  vm.add = function() {

    vm.title = "Add Supplier SKU Mapping";
    angular.copy(empty_data, vm.model_data);
    vm.update = false;
    get_suppliers();
    $state.go('app.masters.sourceSKUMapping.mapping');
  }

  vm.submit = function(data) {
    delete(vm.model_data.mrp)
    if (data.$valid) {
      if ("Add Supplier SKU Mapping" == vm.title) {
        vm.supplier_sku('insert_mapping/');
      } else {
        vm.model_data['data-id'] = vm.model_data.DT_RowId;
        vm.supplier_sku('update_sku_supplier_values/');
      }
    }
  }

  // add or update supplier sku mapping
  vm.supplier_sku = function(url) {
    vm.service.apiCall(url, 'POST', vm.model_data, true).then(function(data){
      if(data.message) {
        if(data.data == "Updated Successfully" || data.data == "Added Successfully") {
          vm.service.refresh(vm.dtInstance);
          vm.close();
        } else {
          vm.service.pop_msg(data.data);
        }
      }
    });
  }

  // Get all supplier list
  vm.supplier_list = [];
  vm.costing_type_list = ['Price Based', 'Margin Based'];
  function get_suppliers() {
    vm.service.apiCall('get_supplier_list/').then(function(data){
      if(data.message) {
        data = data.data;
        var list = [];
        angular.forEach(data.suppliers, function(d){
          list.push(d.id)
        });
        vm.supplier_list = list;
        vm.model_data.supplier_id = vm.supplier_list[0];
        vm.costing_type_list = data.costing_type;
        vm.model_data.costing_type = 'Price Based';
      }
    }); 
  }

}

