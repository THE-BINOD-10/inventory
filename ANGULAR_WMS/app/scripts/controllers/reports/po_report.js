'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('POReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

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
  vm.service.get_report_data("po_report").then(function(data) {
    angular.copy(data, vm.report_data);
    vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(data) {
      vm.empty_data = data.empty_data;
      angular.copy(vm.empty_data, vm.model_data);
      vm.dtOptions = data.dtOptions;
      vm.dtColumns = data.dtColumns;
      if(vm.permissions.dispatch_qc_check) {
        vm.dtColumns.push(DTColumnBuilder.newColumn('Customer Name').withTitle('Customer Name').notSortable())
        vm.dtColumns.push(DTColumnBuilder.newColumn('SR Number').withTitle('Main SR Number').notSortable())
      }
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
                    'sister_warehouse' :''
                    };

  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);

}
