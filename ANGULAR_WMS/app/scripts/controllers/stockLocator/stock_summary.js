'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('StockSummaryCtrl',['$scope', '$http', '$state', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'colFilters' , 'Service', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, Data) {
    var vm = this;
    vm.service = Service;
    vm.g_data = Data.stock_summary;
    vm.apply_filters = colFilters;
    vm.filters = {'datatable': 'StockSummary', 'search0':'', 'search1':'', 'search2':'', 'search3':''}
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
       .withOption('rowCallback', rowCallback);

    vm.dtInstance = {};

    vm.reloadData = reloadData;
    function reloadData() {
        this.dtInstance.reloadData();
    }

    

    vm.dtColumns = vm.service.build_colums(vm.g_data.tb_headers);

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.reloadData();
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.service.apiCall('stock_summary_data', 'GET', {wms_code: aData['WMS Code']}).then(function(data){
                  if(data.message) {
                    vm.wms_code = aData['WMS Code'];
                    angular.copy(data.data, vm.model_data);
                    $state.go('app.stockLocator.StockSummary.Detail');
                  }
                });
            });
        });
        if(vm.filter_enable){
          vm.filter_enable = false;
          vm.apply_filters.add_search_boxes();
        }
        return nRow;
    } 

    vm.filter_enable = true;
    vm.model_data = {};
    vm.wms_code = "";

    vm.close = close;
    function close() {

      $state.go('app.stockLocator.StockSummary');
    }

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }
    vm.easyops_excel = function() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.search.datatable = "StockSummaryEasyops";
      colFilters.download_excel();
    }
  }

