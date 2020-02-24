'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('MoveInventoryReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
  var vm = this;
  vm.service = Service;
  vm.datatable = false;
  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;
  vm.empty_data = {};
  vm.model_data = {};
  vm.report_data = {};
  vm.print = print;
  vm.reports = {}
  vm.get_report_data = function() {
    var send = {};
    var name = 'move_inventory_report';
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
        if(Session.user_profile.user_type === 'marketplace_user') {
          vm.dtColumns.push(DTColumnBuilder.newColumn('Weight').withTitle('Weight'))
          vm.dtColumns.push(DTColumnBuilder.newColumn('MRP').withTitle('MRP'))
        }
        if(Session.user_profile.industry_type === 'FMCG'){
          vm.dtColumns.push(DTColumnBuilder.newColumn('Seller').withTitle('Seller'))
        }
        if (vm.industry_type == "FMCG" && vm.user_type == "marketplace_user") {
            vm.dtColumns.splice(8, 0, DTColumnBuilder.newColumn('Manufacturer').withTitle('Manufacturer'))
            vm.dtColumns.splice(9, 0, DTColumnBuilder.newColumn('Searchable').withTitle('Searchable'))
            vm.dtColumns.splice(10, 0, DTColumnBuilder.newColumn('Bundle').withTitle('Bundle'))
             }

        vm.datatable = true;
        vm.dtInstance = {};
      })
	}
	}
	})
  }
  vm.get_report_data()
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
