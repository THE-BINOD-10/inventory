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
    vm.permissions = Session.roles.permissions;

    vm.g_data = Data.warehouse_view;
    vm.alternate_view_value = Data.warehouse_toggle_value;

    vm.size_types = [];
    vm.warehouse_names = [];
    vm.warehouse_value = ''

    function getOS() {
      var userAgent = window.navigator.userAgent,
          platform = window.navigator.platform,
          macosPlatforms = ['Macintosh', 'MacIntel', 'MacPPC', 'Mac68K'],
          windowsPlatforms = ['Win32', 'Win64', 'Windows', 'WinCE'],
          iosPlatforms = ['iPhone', 'iPad', 'iPod'],
          os = null;

      if (macosPlatforms.indexOf(platform) !== -1) {
        os = 'Mac OS';
      } else if (iosPlatforms.indexOf(platform) !== -1) {
        os = 'iOS';
      } else if (windowsPlatforms.indexOf(platform) !== -1) {
        os = 'Windows';
      } else if (/Android/.test(userAgent)) {
        os = 'Android';
      } else if (!os && /Linux/.test(platform)) {
        os = 'Linux';
      }

      return os;
    }

    vm.date_format_convert = function(utc_date){

      var os_type = getOS();

      var date = utc_date.toLocaleDateString();
      var datearray = date.split("/");

      if (os_type == 'Windows') {

        if (datearray[1] < 10 && datearray[1].length == 1) {
          datearray[1] = '0'+datearray[1];
        }

        if (datearray[0] < 10 && datearray[0].length == 1) {
          datearray[0] = '0'+datearray[0];
        }

        vm.date = datearray[0] + '/' + datearray[1] + '/' + datearray[2];
        return datearray[0] + '/' + datearray[1] + '/' + datearray[2];
      } else {
        
        vm.date = datearray[1] + '/' + datearray[0] + '/' + datearray[2];
        return datearray[1] + '/' + datearray[0] + '/' + datearray[2];
      }
    }

    // vm.date_format_convert(new Date());

    //From and To Date
    var abc = new Date()
    // vm.date_format_convert = function(utc_date) {
    //       var date = utc_date.toLocaleDateString();
    //       var datearray = date.split("/");
    //       return datearray[1] + '/' + datearray[0] + '/' + datearray[2];
    // }
    vm.from_date = vm.date_format_convert(new Date(abc.setDate(abc.getDate()-30)));
    vm.to_date = vm.date_format_convert(new Date());

    vm.layout_loading = true;
    if(!Session.roles.permissions.add_networkmaster && !Session.roles.permissions.priceband_sync) {
      vm.g_data.level = "";
    }
    vm.service.apiCall('warehouse_headers/?level='+vm.g_data.level+'&alternate_view='+Data.warehouse_toggle_value+'&warehouse_name='+vm.warehouse_value+'&size_type_value='+vm.size_type_value+ '&marketplace='+vm.marketplace_value, 'GET').then(function(data){
      vm.size_types = data.data.size_types;
      vm.warehouse_names = data.data.warehouse_names;

      vm.warehouse_value = vm.warehouse_names[0]
      vm.size_type_value = vm.size_types[0];
      vm.marketplaces = data.data.market_places;

      vm.excel = excel;
      function excel() {
        angular.copy(vm.dtColumns,colFilters.headers);
        angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
        colFilters.download_excel()
      }

      if (Data.warehouse_toggle_value) {
          vm.filters = {'datatable': 'WarehouseStockAlternative', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 
        'from_date' : vm.from_date, 'to_date' : vm.to_date, 'size_type_value' : vm.size_type_value, 'warehouse_name' : vm.warehouse_value, 'view_type' : vm.g_data.view }
        } else {
          vm.filters = {'datatable': vm.g_data.view, 'search0':'', 'search1':'', 'search2': '', 'search3': '', 
        'from_date' : vm.from_date, 'to_date' : vm.to_date, 'size_type_value' : vm.size_type_value, 'warehouse_name' : vm.warehouse_value}
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
      var columns = data.data.table_headers;
      vm.dtColumns = vm.service.build_colums(columns);
      vm.data_display = true;
      vm.dtInstance = {};

      vm.build_datatable = function (data, flag) {
        if (Data.warehouse_toggle_value) {
          vm.filters = {'datatable': 'WarehouseStockAlternative', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 
        'from_date' : vm.from_date, 'to_date' : vm.to_date, 'size_type_value' : vm.size_type_value, 'warehouse_name' : vm.warehouse_value,  'marketplace': vm.marketplace_value,'view_type' : vm.g_data.view }
        } else {
          vm.filters = {'datatable': vm.g_data.view, 'search0':'', 'search1':'', 'search2': '', 'search3': '', 
        'from_date' : vm.from_date, 'to_date' : vm.to_date, 'size_type_value' : vm.size_type_value, 'warehouse_name' : vm.warehouse_value}
        }
        var columns = data.data.table_headers;
        if (flag) {
          vm.dtInstance.DataTable.context[0].ajax.data = {'from_date': vm.from_date, 'to_date': vm.to_date, 'view_type': vm.g_data.view, 'alternate_view': vm.alternate_view_value, 'warehouse_name' : vm.warehouse_value, 'size_type_value' : vm.size_type_value, 'datatable' : 'WarehouseStockAlternative' }
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
        vm.dtColumns = vm.service.build_colums(columns);
      }
      vm.build_datatable(data, false);

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

      vm.generate_warehouse_stock = function() {
        if (Data.warehouse_toggle_value) {
          vm.service.apiCall('warehouse_headers/?level='+vm.g_data.level+'&alternate_view='+Data.warehouse_toggle_value+'&warehouse_name='+vm.warehouse_value+'&size_type_value='+vm.size_type_value + '&marketplace='+vm.marketplace_value, 'GET').then(function(data){
            vm.dtInstance.DataTable.context[0].ajax.data = {'from_date': vm.from_date, 'to_date': vm.to_date, 'view_type': vm.g_data.view, 'alternate_view': vm.alternate_view_value, 'warehouse_name' : vm.warehouse_value, 'size_type_value' : vm.size_type_value, 'datatable' : 'WarehouseStockAlternative' }
            vm.build_datatable(data, true);
          })
        }
      }

      vm.get_sizetypes_for_warehouses = function() {
        if (Data.warehouse_toggle_value) {
          vm.service.apiCall('warehouse_headers/?level='+vm.g_data.level+'&alternate_view='+Data.warehouse_toggle_value+'&warehouse_name='+vm.warehouse_value+'&size_type_value='+vm.size_type_value+ '&marketplace='+vm.marketplace_value, 'GET').then(function(data) {
            //var columns = data.data.table_headers;
            vm.size_types = data.data.size_types;
            vm.size_type_value = vm.size_types[0];
            vm.marketplaces = data.data.market_places;
          })
        }
      }

  })
}
