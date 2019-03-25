'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('DispatchSummaryCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, Data) {

  var vm = this;
  vm.service = Service;
  vm.service.print_enable = false;
  vm.g_data = Data.dispatch_summary_report;
  vm.dispatch_summary_view_types = Data.dispatch_summary_view_types;
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

  vm.dtInstance = {};

  vm.empty_data = {
                    'from_date': '',
                    'to_date': '',
                    'wms_code': '',
                    'sku_code': '',
                    'order_id': '',
                    'imei_number': '',
                    'datatable': vm.g_data.view
                    };

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

}
