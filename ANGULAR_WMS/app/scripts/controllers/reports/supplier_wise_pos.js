'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SupplierWisePOsCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

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
  var name = 'supplier_wise_po_report';
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
          vm.dtColumns = datam.dtColumns;
          vm.datatable = true;
          vm.dtInstance = {};
          vm.report_data['excel2'] = true;
  	      vm.report_data['row_click'] = true;
          vm.report_data['excel_name'] = 'supplier_wise_po_report';
        })
  	  }
  	}
  });


  vm.row_call = function(aData) {
    angular.copy(aData, vm.model_data);
    vm.update = true;
    vm.title = "Purchase Order";

    $http.get(Session.url+'print_purchase_order_form/?po_id='+aData['order_id']+'&prefix='+aData['prefix']+'&po_number='+aData['PO Number'], {withCredential: true})
    .success(function(data, status, headers, config) {
      $(".modal-body").html($(data).html());
      vm.print_page = $($(data).html()).clone();
      vm.print_enable = true;
    });
    $state.go("app.reports.SupplierWisePOs.POs");
  }

  vm.print_page = "";
  vm.dtInstance = {};

  vm.empty_data = {
                    'from_date': '',
                    'to_date': '',
                    'wms_code': ''
                    };

  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);

    vm.close = function() {

      angular.copy(vm.empty_data, vm.model_data);
      $state.go('app.reports.SupplierWisePOs');
    }

    vm.print = print;
    vm.print = function() {
      console.log(vm.print_page);
      vm.service.print_data(vm.print_page, "Purchase Order");
    }

}
