'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PRReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
  var vm = this;
  vm.service = Service;
  vm.datatable = false;

  vm.empty_data = {}
  vm.model_data = {};

  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;
  vm.toggle_detail = false;
  vm.report_data = {};
  vm.reports = {}
  vm.title = "PR Report";
  vm.toggle_po = function() {
    var send = {};
    var name ='';
  	if (vm.toggle_detail) {
      name = 'pr_detail_report';
    } else {
      name = 'pr_report';
    }
    vm.service.apiCall("get_report_data/", "GET", {report_name: name}).then(function(data) {
    	if (data.message) {
    	  if ($.isEmptyObject(data.data.data)) {
    		  vm.datatable = false;
    		  vm.dtInstance = {};
    	  } else {
      	  vm.reports[name] = data.data.data;
      	  angular.copy(data.data.data, vm.report_data)
          vm.report_data["row_call"] = vm.row_call;
          vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(datam) {
             vm.empty_data = datam.empty_data;
             angular.copy(vm.empty_data, vm.model_data);
//            vm.empty_data = datam.empty_data;
//            angular.copy(vm.empty_data, vm.filters_dt_data)
            vm.dtOptions = datam.dtOptions;
            vm.dtOptions.order = [2, 'desc']
            vm.dtColumns = datam.dtColumns;
            vm.datatable = true;
            vm.dtInstance = {};
    		vm.report_data['row_click'] = true;
    		if (name =="pr_detail_report")
    		{
            vm.report_data['excel_name'] = 'get_pr_detail_report'
            }
            else{
            vm.report_data['excel_name'] = 'get_pr_report'
            }
          })
        }
    	}
    	$state.go('app.reports.PRReport');
  	})

  }

  vm.toggle_po()

  vm.print_page = "";
  vm.dtInstance = {};

  vm.empty_data = {
                  'from_date': '',
                  'to_date': '',
                  'po_number': '',
                  'sister_warehouse': '',
                  'supplier_id': '',
                  };
    vm.model_data = {};
    angular.copy(vm.empty_data, vm.model_data);

//  vm.filters_dt_data = {};
//  angular.copy(vm.empty_data, vm.filters_dt_data);

  vm.close = close;
  function close() {
    vm.title = "PR Report";
    $state.go('app.reports.PRReport');
  }

  vm.print = print;
  function print() {
    console.log(vm.print_page);
    vm.service.print_data(vm.print_page, "PR Report");
  }


}
