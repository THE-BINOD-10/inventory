'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('warehouseSKUMappingTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.filters = {'datatable': 'WarehouseSKUMappingMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
        DTColumnBuilder.newColumn('warehouse_name').withTitle('Warehouse Name'),
        DTColumnBuilder.newColumn('wms_code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('priority').withTitle('Priority'),
        DTColumnBuilder.newColumn('moq').withTitle('MOQ'),
        DTColumnBuilder.newColumn('price').withTitle('Price'),
    ];

    vm.dtInstance = {};

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.model_data['create_login'] = false;
                angular.copy(aData, vm.model_data);
                vm.update = true;
                vm.title = "Update Warehouse SKU";
                $state.go('app.masters.sourceSKUMapping.wh_mapping');
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
  var empty_data = {warehouse_name: "", wms_code: "", priority: "", moq: "", price: ""};
  vm.model_data = {};
  angular.copy(empty_data, vm.model_data);

  //close popup
  vm.close = function() {

    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.sourceSKUMapping');
  }

  // open popup for new supplier sku mapping
  vm.add = function() {

    vm.title = "Add Warehouse SKU Mapping";
    angular.copy(empty_data, vm.model_data);
    vm.update = false;
    get_warehouses();
    $state.go('app.masters.sourceSKUMapping.wh_mapping');
  }

  vm.submit = function(data) {

    if (data.$valid) {
      if ("Add Warehouse SKU Mapping" == vm.title) {
        vm.warehouse_sku('insert_wh_mapping/');
      } else {
        vm.model_data['data-id'] = vm.model_data.DT_RowId;
        vm.warehouse_sku('update_sku_warehouse_values/');
      }
    }
  }

  // add or update warehouse sku mapping
  vm.warehouse_sku = function(url) {

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

  // Get all warehouse list
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
        vm.model_data.warehouse_name = vm.warehouse_list[0].id;
      }
    });
  }

}

