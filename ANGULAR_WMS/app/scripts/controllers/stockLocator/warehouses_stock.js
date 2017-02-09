'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('WarehousesStockCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', 'Data', ServerSideProcessingCtrl]);

  function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, Service, Data) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.tb_data = {};
    vm.data_display = false;
    vm.go_data = ['Available', 'Avail + Intra', 'A + IT + R'];
    vm.view = '';

    vm.g_data = Data.stock_view;

    vm.service.apiCall('warehouse_headers/', 'GET').then(function(data){

    vm.selected = {};
    vm.selectAll = false;

    vm.filters = {'datatable': vm.g_data.view, 'search0':'', 'search1':'', 'search2': '', 'search3': ''}

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: vm.filters,
              xhrFields: {
                withCredentials: true
              },
              complete: function(jqXHR, textStatus) {
                          $scope.$apply(function(){
                            angular.copy(JSON.parse(jqXHR.responseText), vm.tb_data)
                          })
                        }
           })
       .withDataProp('data')
       .withOption('drawCallback', function(settings) {
         vm.service.make_selected(settings, vm.selected);
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
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    var columns = data.data;
    //var columns = ["SKU Code", "SKU Brand", "SKU Description", "SKU Category", "Warehouse 1", "Warehouse 2"];
    vm.dtColumns = vm.service.build_colums(columns);

    vm.dtInstance = {};

    function reloadData () {
        vm.bt_disable = true;
        vm.dtInstance.reloadData();
    };

  vm.change_datatable = function() {
    Data.stock_view.view =  vm.g_data.view;
    $state.go($state.current, {}, {reload: true});
  }

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    vm.bt_disable = true;
    vm.button_fun = function() {

      var enable = true
      for (var id in vm.selected) {
        if(vm.selected[id]) {
          vm.bt_disable = false
          enable = false
          break;
        }
      }
      if (enable) {
        vm.bt_disable = true;
      }
    }
    vm.data_display = true;
    })
}
