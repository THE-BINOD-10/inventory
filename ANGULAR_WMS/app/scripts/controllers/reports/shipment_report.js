'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ShipmentReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.service = Service;
  vm.datatable = false;

  vm.empty_data = {};
  vm.model_data = {};

  vm.report_data = {};
  vm.service.get_report_data("shipment_report").then(function(data) {
    angular.copy(data, vm.report_data);
    vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(data) {
      vm.empty_data = data.empty_data;
      angular.copy(vm.empty_data, vm.model_data);
      vm.dtOptions = data.dtOptions;
      vm.dtColumns = data.dtColumns;
      vm.dtColumns.push(DTColumnBuilder.newColumn('Dispatched Date').withTitle('Dispatched Date'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('Delivered Date').withTitle('Delivered Date'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('Manifest Number').withTitle('Manifest Number'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('Serial Number').withTitle('Serial Number'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('ID Type').withTitle('ID Type'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('ID Proof Number').withTitle('ID Proof Number'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('ID Card').withTitle('ID Card'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('Signed Invoice Copy').withTitle('Signed Invoice Copy'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('Refused').withTitle('Refused'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('Refusal Reason').withTitle('Refusal Reason'))

      vm.datatable = true;
      vm.dtInstance = {};
    })
  })

  vm.print_page = "";
  vm.dtInstance = {};

  vm.empty_data = {
                    'from_date': '',
                    'to_date': '',
                    'sku_code': ''
                    };

  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);

}
