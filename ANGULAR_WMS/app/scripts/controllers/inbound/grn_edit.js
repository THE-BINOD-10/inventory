'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('GRNEdit',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.service = Service;
  vm.datatable = false;

  vm.empty_data = {}
  vm.model_data = {};

  vm.toggle_sku_wise = false;

  vm.title = "Purchase Order";

  vm.report_data = {};

  vm.row_call = function(aData) {
    $http.get(Session.url+'grn_edit_popup/', {withCredential: true, 'po_number': aData['PO Number']}).success(function(data, status, headers, config) {
      console.log(data)
    });
    $state.go('app.inbound.GrnEdit.GrnEditPopup');
  }
  vm.reports = {}
  vm.toggle_grn = function() {
    var send = {};
    var name = 'grn_edit';
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
            angular.copy(vm.empty_data, vm.model_data)
            vm.dtOptions = datam.dtOptions;
            vm.dtColumns = datam.dtColumns;
            vm.datatable = true;
            vm.dtInstance = {};
            vm.report_data['excel2'] = true;
    		    vm.report_data['row_click'] = true;
            if (vm.toggle_sku_wise) {
                vm.report_data['excel_name'] = 'sku_wise_goods_receipt'
            } else {
                vm.report_data['excel_name'] = 'goods_receipt'
            }
          })
        }
    	}
  	})
  }

  vm.toggle_grn()

  vm.print_page = "";
  vm.dtInstance = {};

  vm.empty_data = {
                  'from_date': '',
                  'to_date': '',
                  'po_number': '',
                  'invoice_number': '',
                  'supplier_id': '',
                  };

  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);

  vm.close = close;
  function close() {
    vm.title = "GRN Edit";
    $state.go('app.inbound.GrnEdit');
  }
}