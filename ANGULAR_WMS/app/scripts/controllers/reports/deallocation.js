'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('DeAllocationReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  vm.datatable = false;
  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;

  vm.empty_data = {};
  vm.model_data = {};

  vm.report_data = {};
  vm.service.get_report_data("deallocation_report").then(function(data) {
    angular.copy(data, vm.report_data);
    vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(data) {
      vm.empty_data = data.empty_data;
      angular.copy(vm.empty_data, vm.model_data);
      vm.dtOptions = data.dtOptions;
      vm.dtColumns = data.dtColumns;
      vm.datatable = true;
    })
  })

  vm.print_page = "";
  vm.dtInstance = {};

  vm.close = close;
  function close() {
    vm.title = "DeAllocation Report";
    $state.go('app.reports.DeAllocationReport');
  }
  vm.empty_data = {
                    'from_date': '',
                    'to_date': '',
                    'sku_code': '',
                    'customer_id' :'',
                    'order_id':'',
                    };

}
