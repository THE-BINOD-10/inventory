'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CancelGRNReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.service = Service;
  vm.datatable = false;

  vm.empty_data = {};
  vm.model_data = {};
  vm.report_data = {};

  vm.toggle_detail = false;

  vm.close = close;
  function close() {
    vm.title = "Cancel GRN Report";
    $state.go('app.reports.CancelGRNReport');
  }

  vm.print = print;
  vm.print = function() {
    console.log(vm.print_page);
    vm.service.print_data(vm.print_page, "Cancel GRN Report");
  }

  /*vm.report_data = {};
  vm.service.get_report_data("rtv_report").then(function(data) {
    angular.copy(data, vm.report_data);
    vm.report_data["row_call"] = vm.row_call;
    vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(data) {
      vm.empty_data = data.empty_data;
      angular.copy(vm.empty_data, vm.model_data);
      vm.dtOptions = data.dtOptions;
      vm.dtColumns = data.dtColumns;
      vm.datatable = true;
      vm.dtInstance = {};
    })
  })*/

  vm.reports = {}

  vm.title = "Cancel GRN Report";
  vm.toggle_po = function() {
    var send = {};
	var name='';
	if (vm.toggle_detail) {
      name = 'sku_wise_cancel_grn_report';
    } else {
      name = 'cancel_grn_report';
    }
    vm.service.apiCall("get_report_data/", "GET", {report_name: name}).then(function(data) {
	if(data.message) {
	  if ($.isEmptyObject(data.data.data)) {
		vm.datatable = false;
		vm.dtInstance = {};
	  } else {
	  vm.reports[name] = data.data.data;
	  angular.copy(data.data.data, vm.report_data);
	  if(name=='cancel_grn_report') {
        vm.report_data["row_call"] = vm.row_call;
      }
      vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(datam) {
        vm.empty_data = datam.empty_data;
        angular.copy(vm.empty_data, vm.model_data);
        vm.dtOptions = datam.dtOptions;
        vm.dtColumns = datam.dtColumns;
        vm.datatable = true;
        vm.dtInstance = {};
        vm.report_data['excel2'] = true;
        if (vm.toggle_sku_wise) {
            vm.report_data['excel_name'] = 'sku_wise_cancel_grn_report'
        } else {
            vm.report_data['excel_name'] = 'get_cancel_grn_report'
        }
      })
	}
	}
	})
  }

  vm.toggle_po()

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
