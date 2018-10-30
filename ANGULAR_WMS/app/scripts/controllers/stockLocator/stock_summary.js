'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('StockSummaryCtrl',['$scope', '$http', '$state', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'colFilters' , 'Service', 'Data', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, Data, $modal) {
    var vm = this;
    vm.service = Service;
    vm.g_data = Data.stock_summary;
    vm.apply_filters = colFilters;
    vm.permissions = Session.roles.permissions;
    vm.data_display = false;
    vm.tb_data = {};
    vm.selected_size = vm.g_data.size_type;
    vm.industry_type = Session.user_profile.industry_type;

    vm.dt_display = false;
    vm.build_dt = function() {
      vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': vm.g_data.view, 'size_name': vm.g_data.size_type, 'search0':'', 'search1':'', 'search2':'', 'search3':''},
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
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

      //vm.dtColumns = vm.service.build_colums(vm.g_data.selected_value);
      var columns = vm.g_data.tb_headers[vm.g_data.view].concat(vm.extra_c);
      vm.dtColumns = vm.service.build_colums(columns);
      vm.dt_display = true;
    }

    vm.extra_c = [];
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

    vm.dtInstance = {};

    vm.reloadData = reloadData;
    function reloadData() {
        this.dtInstance.reloadData();
    }

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.reloadData();
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            if (vm.g_data.view == 'StockSummary'){
            $scope.$apply(function() {
                vm.service.apiCall('stock_summary_data', 'GET', {wms_code: aData['WMS Code']}).then(function(data){
                  if(data.message) {
                    vm.wms_code = aData['WMS Code'];
                    angular.copy(data.data, vm.model_data);
                    vm.model_data["sku_data"] = aData;
                    $state.go('app.stockLocator.StockSummary.Detail');
                  }
                });
            });
            }
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
    vm.serials_excel = function() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.search.datatable = "StockSummarySerials";
      colFilters.download_excel();
    }
    vm.change_datatable = function() {
      Data.stock_summary.view = (vm.g_data.stock_2d)? 'StockSummaryAlt': 'StockSummary';
      $state.go($state.current, {}, {reload: true});
    }
    vm.change_view = function(view_name) {
      //vm.selected = view_name;
      //vm.service.apiCall('get_size_names', 'GET').then(function(data){
      //  vm.headers = data.data[vm.selected];
      //  for (var i=0; i<vm.headers.length; i++){
      //    vm.g_data.selected_value.push(vm.headers[i]);
      //  }
        Data.stock_summary.size_type = view_name;
        $state.go($state.current, {}, {reload: true});
      //});
    }
    vm.data_display = true;

    vm.open = function (size) {
      var mod_data = {columns: vm.dtColumns, instance: vm.dtInstance};
      var modalInstance = $modal.open({
        templateUrl: 'views/stockLocator/toggles/seller_stock_download.html',
        controller: 'SellerStockDownload',
        controllerAs: 'pop',
        size: size,
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

    }, function () {
      //$log.info('Modal dismissed at: ' + new Date());
      console.log('Modal dismissed at: ' + new Date());
    });
  };
  //$scope.open('sm');
  }

function SellerStockDownload($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {
  var vm = this;
  vm.state_data = items;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  vm.ok = function () {
    $modalInstance.close("close");
  };
  vm.seller_data = {};
  vm.service.apiCall('get_sellers_list/', 'GET').then(function(data){
    if (data.message) {
      vm.seller_data = data.data.sellers;
    }
  })
  vm.download_excel = function() {
    vm.service.print_excel({seller_id: vm.seller_id}, vm.state_data.instance, vm.state_data.columns, 'seller_stock_summary_replace', true)
  }
  }
angular
  .module('urbanApp')
  .controller('SellerStockDownload', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', SellerStockDownload]);
