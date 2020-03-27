'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('DiscrepancyReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
  var vm = this;
  vm.service = Service;
  vm.datatable = false;
  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;
  vm.empty_data = {};
  vm.model_data = {};
  vm.report_data = {};
  vm.toggle_sku_wise = false;
  vm.print = print;
  vm.print = function() {
    vm.service.print_data(vm.print_page, "Debit Note");
  }
  vm.reports = {}
  vm.toggle_rtv_sku_wise = function() {
    var send = {};
    var name = 'discrepancy_report';
    vm.service.apiCall("get_report_data/", "GET", {report_name: name}).then(function(data) {
	  if (data.message) {
	  if ($.isEmptyObject(data.data.data)) {
		vm.datatable = false;
		vm.dtInstance = {};
	  } else {
	  vm.reports[name] = data.data.data;
	  angular.copy(data.data.data, vm.report_data);
      vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(datam) {
        vm.empty_data = datam.empty_data;
        angular.copy(vm.empty_data, vm.model_data);
        vm.dtOptions = datam.dtOptions;
        vm.dtColumns = datam.dtColumns;
        vm.datatable = true;
        vm.dtInstance = {};
      })
	}
	}
	})
  }
  vm.toggle_rtv_sku_wise()
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
