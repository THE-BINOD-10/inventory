'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SellerStockCtrl',['$scope', '$http', '$state', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.industry_type = Session.user_profile.industry_type;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.filters = {'datatable': 'SellerStockTable', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':''}
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

    var columns = ['Seller ID', 'Seller Name', 'SKU Code', 'SKU Desc', 'SKU Class', 'SKU Brand', 'SKU Category', 'Available Qty', 'Reserved Qty', 'Damaged Qty', 'Total Qty', 'Stock Value']
    vm.dtColumns = vm.service.build_colums(columns);

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.reloadData();
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
                vm.service.apiCall('seller_stock_summary_data', 'GET', {data_id: aData['id']}).then(function(data){
                  if(data.message) {
                    vm.wms_code = aData['SKU Code'];
                    angular.copy(data.data, vm.model_data);
                  }
                });
                $state.go('app.stockLocator.SellerStock.StockDetails')
            });
        });
        return nRow;
    }

    vm.close = function() {

      $state.go('app.stockLocator.SellerStock');
    }

    vm.model_data = {};
  }

