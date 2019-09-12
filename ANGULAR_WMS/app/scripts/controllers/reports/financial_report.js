'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('FinancalCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.service = Service;
  vm.datatable = false;

  vm.empty_data = {};
  vm.model_data = {};

  vm.report_data = {};
  vm.service.get_report_data("financial_report").then(function(data) {
    angular.copy(data, vm.report_data);
    vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(data) {
      vm.empty_data = data.empty_data;
      angular.copy(vm.empty_data, vm.model_data);
      vm.dtOptions = data.dtOptions;
      vm.dtColumns = data.dtColumns;
      vm.datatable = true;
      vm.dtInstance = {};
    })
  })

  vm.print_page = "";
  vm.dtInstance = {};

  vm.empty_data = {
                    'from_date': '',
                    'to_date': '',
                    'sku_code': '',
                    };

  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);

}
