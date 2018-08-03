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

    vm.g_data = Data.warehouse_view;
    vm.alternate_view_value = Data.warehouse_toggle_value;

    vm.size_types = [];
    vm.warehouse_names = [];

    vm.layout_loading = true;
    if(!Session.roles.permissions.add_networkmaster && !Session.roles.permissions.priceband_sync) {
      vm.g_data.level = "";
    }
    vm.service.apiCall('warehouse_headers/?level='+vm.g_data.level+'&alternate_view='+Data.warehouse_toggle_value, 'GET').then(function(data){
      vm.size_types = data.data.size_types;
      vm.warehouse_names = data.data.warehouse_names;

      vm.filters = {'datatable': vm.g_data.view, 'search0':'', 'search1':'', 'search2': '', 'search3': ''}

      vm.excel = excel;
      function excel() {
        angular.copy(vm.dtColumns,colFilters.headers);
        angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
        colFilters.download_excel()
      }

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
          vm.layout_loading = false;
        });

      var columns = data.data.table_headers;
      vm.dtColumns = vm.service.build_colums(columns);

      vm.dtInstance = {};
      vm.data_display = true;

      function reloadData () {
        vm.bt_disable = true;
        vm.dtInstance.reloadData();
      };

      vm.change_datatable = function() {
        Data.stock_view.view =  vm.g_data.view;
        Data.stock_view.level = vm.g_data.level;
        $state.go($state.current, {}, {reload: true});
      }

      vm.alternate_view = function() {
        Data.warehouse_toggle_value = vm.alternate_view_value;
        Data.warehouse_view = (vm.alternate_view_value) ? Data.warehouse_alternative_stock_view : Data.stock_view;
        $state.go($state.current, {}, {reload: true});
      }

      vm.get_size_type = function() {
        if(vm.g_data.view == 'StockSummary') {
          vm.build_dt();
        } else {
          vm.service.apiCall('get_size_names', 'GET').then(function(data){
            if (data.message){
              vm.drop_data = data.data['size_names'];
              vm.selected_default = vm.drop_data[vm.drop_data.length - 1];
              if(vm.g_data.size_type) {
                vm.extra_c = data.data[vm.g_data.size_type];
                vm.build_dt();
              }
            }
          });
        }
      }

      $scope.$on('change_filters_data', function(){
        vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
        vm.service.refresh(vm.dtInstance);
      });

    })
}
