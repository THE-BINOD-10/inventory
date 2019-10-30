'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('DispatchSummaryCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, Data) {

  var vm = this;
  vm.service = Service;
  vm.service.print_enable = false;
  vm.g_data = Data.dispatch_summary_report;
  vm.parent_username = Session.parent.userName
  vm.central_order_mgmt = Session.roles.permissions.central_order_mgmt
  vm.dispatch_summary_view_types = Data.dispatch_summary_view_types;
  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;
  vm.model_data = {'datatable': vm.g_data.view}
  vm.dtOptions = DTOptionsBuilder.newOptions()
     .withOption('ajax', {
            url: Session.url+'get_dispatch_filter/',
            type: 'GET',
            data: vm.model_data,
            xhrFields: {
              withCredentials: true
            },
            data: vm.model_data
         })
     .withDataProp('data')
     .withOption('processing', true)
     .withOption('serverSide', true)
     .withPaginationType('full_numbers');

  vm.dtColumns = vm.service.build_colums(vm.g_data.tb_headers[vm.g_data.view]);
  if(vm.parent_username == 'isprava_admin'){
      vm.dtColumns.push(DTColumnBuilder.newColumn('Warehouse').withTitle('Warehouse Name'))
    }

  vm.dtInstance = {};

  var fromDate = new Date(new Date().getFullYear(), new Date().getMonth() - 1, new Date().getDate()).toLocaleDateString('en-US');

  vm.empty_data = {
                    'from_date': fromDate,
                    'to_date': '',
                    'wms_code': '',
                    'sku_code': '',
                    'order_id': '',
                    'imei_number': '',
                    'sister_warehouse': '',
                    'datatable': vm.g_data.view
                    };
  vm.warehouse_groups = [];
  vm.service.apiCall('sku_category_list/').then(function(data){
    if(data.message) {
      vm.warehouse_groups = data.data.sister_warehouses;
    }
  })

  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);
  vm.change_datatable = function() {
    Data.dispatch_summary_report.view = vm.choose_view;
    vm.g_data.view = vm.choose_view;
    vm.model_data = {'datatable': vm.g_data.view}
    vm.dtInstance.DataTable.context[0].ajax.data = vm.model_data;
    $state.go($state.current, {}, {reload: true});
  }
  vm.temp_view_alternative_toggle = Data.dispatch_summary_report.view
  vm.change_table_view = function(key) {
    if (key) {
      vm.dtColumns.push(DTColumnBuilder.newColumn('Customer Name').withTitle('Customer Name'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('Batch Number').withTitle('Batch Number'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('MRP').withTitle('MRP'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('Manufactured Date').withTitle('Manufactured Date'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('Expiry Date').withTitle('Expiry Date'))
    } else {
      vm.dtColumns.pop(DTColumnBuilder.newColumn('Customer Name').withTitle('Customer Name'))
      vm.dtColumns.pop(DTColumnBuilder.newColumn('Batch Number').withTitle('Batch Number'))
      vm.dtColumns.pop(DTColumnBuilder.newColumn('MRP').withTitle('MRP'))
      vm.dtColumns.pop(DTColumnBuilder.newColumn('Manufactured Date').withTitle('Manufactured Date'))
      vm.dtColumns.pop(DTColumnBuilder.newColumn('Expiry Date').withTitle('Expiry Date'))
    }
  }

  vm.sku_groups = [0, 123, 23, 1234]
  vm.service.apiCall('sku_category_list/').then(function(data){
     if(data.message) {
       vm.sku_groups = data.data.categories;
     }
   })

}
