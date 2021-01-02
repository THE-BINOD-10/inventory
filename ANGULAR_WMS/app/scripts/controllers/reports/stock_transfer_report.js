'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('StockTransferReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.service = Service;
  vm.datatable = false;
  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;

  vm.empty_data = {};
  vm.model_data = {};
  vm.report_data = {};
  vm.toggle_batch_wise =  false;

  vm.print = print;
  vm.print = function() {
    vm.service.print_data(vm.print_page, "Debit Note");
  }

  vm.reports = {}
  vm.toggle_batch_sku_wise = function() {
    var send = {};
	var name = 'stock_transfer_report';
    vm.service.apiCall("get_report_data/", "GET", {report_name: name}).then(function(data) {
	if(data.message) {
	  if ($.isEmptyObject(data.data.data)) {
		vm.datatable = false;
		vm.dtInstance = {};
	  } else {
	  vm.reports[name] = data.data.data;
	  angular.copy(data.data.data, vm.report_data);
      vm.report_data['special_key'] = 'ST_INTRA';
      vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(datam) {
        vm.empty_data = datam.empty_data;
        angular.copy(vm.empty_data, vm.model_data);
        vm.dtOptions = datam.dtOptions;
        vm.dtColumns = datam.dtColumns;
        if(vm.industry_type =='FMCG'){
        vm.dtColumns.push(DTColumnBuilder.newColumn('Batch Number').withTitle('Batch Number'))
        vm.dtColumns.push(DTColumnBuilder.newColumn('Manufactured Date').withTitle('Manufactured Date'))
        vm.dtColumns.push(DTColumnBuilder.newColumn('Expiry Date').withTitle('Expiry Date'))
        vm.dtColumns.push(DTColumnBuilder.newColumn('Destination Receive PO Status').withTitle('Destination Receive PO Status'))
        vm.dtColumns.push(DTColumnBuilder.newColumn('Destination Received Quantity').withTitle('Destination Received Quantity'))
        }
        vm.datatable = true;
        vm.dtInstance = {};
      })
	}
	}
	})
  }

  vm.toggle_st_sku_wise = function() {
    var send = {};
  var name = 'stock_transfer_report_main';
    vm.service.apiCall("get_report_data/", "GET", {report_name: name}).then(function(data) {
  if(data.message) {
    if ($.isEmptyObject(data.data.data)) {
    vm.datatable = false;
    vm.dtInstance = {};
    } else {
    vm.reports[name] = data.data.data;
    angular.copy(data.data.data, vm.report_data);
      vm.report_data['special_key'] = 'ST_INTRA';
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

  vm.set_filter_function = function() {
    if (vm.toggle_batch_wise) {
      vm.toggle_batch_sku_wise();
    } else {
      vm.toggle_st_sku_wise();
    }
  }

  vm.set_filter_function();
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
