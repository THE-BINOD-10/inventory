'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PRAODCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.service = Service;
  vm.datatable = false;

  vm.empty_data = {}
  vm.model_data = {};

  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;


  //vm.title = "Closing Stock";

  vm.report_data = {};

  vm.reports = {}
  var send = {};
  var name = 'PRAOD_report';
  vm.service.apiCall("get_report_data/", "GET", {report_name: name}).then(function(data) {
  	if(data.message) {
  	  if ($.isEmptyObject(data.data.data)) {
  		  vm.datatable = false;
  		  vm.dtInstance = {};
  	  } else {
  	    vm.reports[name] = data.data.data;
  	    angular.copy(data.data.data, vm.report_data);
        vm.report_data["row_call"] = vm.row_call;
        vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(datam) {
          vm.empty_data = datam.empty_data;
          angular.copy(vm.empty_data, vm.model_data);
          vm.dtOptions = datam.dtOptions;
          vm.dtOptions.order = [0, 'desc']
          vm.dtColumns = datam.dtColumns;
          vm.datatable = true;
          vm.dtInstance = {};
          vm.report_data['excel2'] = true;
  	      vm.report_data['row_click'] = true;
          vm.report_data['excel_name'] = 'PRAOD_report'
        })
  	  }
  	}
  });

  vm.print_page = "";
  vm.dtInstance = {};

  vm.empty_data = {
                    'from_date': '',
                    'to_date': '',
                    'wms_code': '',
                    'status': '',
                    'zone': ''
                    };

  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);
vm.statuses = ['saved', 'pending', 'approved', 'pending under enquiry']
vm.zones = [];
vm.service.apiCall('zones_list/').then(function(data){
  if(data.message) {
    vm.zones = data.data.zones;
  }
})
}
