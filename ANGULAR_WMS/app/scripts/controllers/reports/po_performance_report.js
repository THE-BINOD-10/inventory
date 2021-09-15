'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('POReportPerCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

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
  vm.title = "PO Performance Report";

  vm.row_call = function(aData) {
    console.log('PO Print Blocked');
  }
  vm.toggle_po = function() {
    var send = {};
    var name ='';
  	if (vm.toggle_detail) {
      name = 'po_detail_report';
    } else {
      name = 'get_po_performance_report_dat';
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
            vm.dtOptions = datam.dtOptions;
            vm.dtOptions.order = [2, 'desc']
            vm.dtColumns = datam.dtColumns;
            vm.datatable = true;
            vm.dtInstance = {};
    		    vm.report_data['row_click'] = true;
        		if (name =="po_detail_report")
        		{
                vm.report_data['excel_name'] = 'get_po_detail_report'
            }
            else{
                vm.report_data['excel_name'] = 'get_po_performance_report_dat'
            }
          })
        }
    	}
    	$state.go('app.reports.POReportPerformance');
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
}
