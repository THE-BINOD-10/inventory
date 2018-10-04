'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('GRNEdit',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {

  var vm = this;
  vm.service = Service;
  vm.datatable = false;
  vm.industry_type = Session.user_profile.industry_type;
  vm.empty_data = {}
  vm.model_data = {};
  vm.filters_dt_data = {};

  vm.toggle_sku_wise = false;

  vm.title = "Purchase Order";

  vm.report_data = {};

  vm.row_call = function(aData) {
    // $http.get(Session.url+'get_grn_level_data/', {withCredential: true, 'po_number': aData['PO Number']}).success(function(data, status, headers, config) {
    //   console.log(data)
    // });
    vm.service.apiCall('get_grn_level_data/', 'GET', {po_number: aData['PO Number']}).then(function(data){
      vm.model_data = data.data;
      if (vm.industry_type == 'FMCG') {
        vm.extra_width = {
          'width': '1100px'
        };
      } else {
        vm.extra_width = {
          'width': '900px'
        };
      }
      console.log(data);
    })
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
            angular.copy(vm.empty_data, vm.filters_dt_data)
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

  vm.filters_dt_data = {};
  angular.copy(vm.empty_data, vm.filters_dt_data);

  vm.confirm_grn = function(form) {
    if (form.$valid) {
      // if (vm.permissions.receive_po_invoice_check && vm.model_data.invoice_value){
      //
      //   var abs_inv_value = vm.absOfInvValueTotal(vm.model_data.invoice_value, vm.skus_total_amount);
      //
      //   if (vm.permissions.receive_po_invoice_check && abs_inv_value <= 3){
      //
      //     vm.confirm_grn_api();
      //   } else if (vm.permissions.receive_po_invoice_check && abs_inv_value >= 3) {
      //
      //     colFilters.showNoty("Your entered invoice value and total value does not match");
      //   }
      // } else if (vm.permissions.receive_po_invoice_check && !(vm.model_data.invoice_value)){
      //
      //   colFilters.showNoty("Please Fill The Invoice Value Field");
      // } else {

        vm.confirm_grn_api();
      // }
    } else {
      colFilters.showNoty("Fill Required Fields");
    }
  }

  vm.confirm_grn_api = function(){

    // if(check_receive()){
      var that = vm;
      var elem = angular.element($('#update_grn_form'));
      elem = elem[0];

      var buy_price = parseInt($(elem).find('input[name="buy_price"]').val());
      var mrp = parseInt($(elem).find('input[name="mrp"]').val());

      if(buy_price > mrp) {
        pop_msg("Buy Price should be less than or equal to MRP");
        return false;
      }
      elem = $(elem).serializeArray();
      var url = "update_existing_grn/";
      // if(vm.po_qc) {
      //   url = "confirm_receive_qc/"
      // }
      vm.service.apiCall(url, 'POST', elem, true).then(function(data){
        if(data.message) {
          if(data.data.search("<div") != -1) {
            vm.extra_width = {}
            vm.html = $(data.data);
            vm.extra_width = {}
            //var html = $(vm.html).closest("form").clone();
            //angular.element(".modal-body").html($(html).find(".modal-body"));
            angular.element(".modal-body").html($(data.data));
            vm.print_enable = true;
            vm.service.refresh(vm.dtInstance);
            // if(vm.permissions.use_imei) {
            //   fb.generate = true;
            //   fb.remove_po(fb.poData["id"]);
            // }
          } else {
            pop_msg(data.data)
          }
        }
      });
    // }
  }

  function check_receive() {
    var status = false;
    for(var i=0; i<vm.model_data.data.length; i++)  {
      angular.forEach(vm.model_data.data[i], function(sku){
        if(sku.value > 0) {
          status = true;
        }
      });
    }

    if(status){
      return true;
    } else {
      pop_msg("Please Update the received quantity");
      return false;
    }
  }

  function pop_msg(msg) {
    vm.message = msg;
    $timeout(function () {
      vm.message = "";
    }, 2000);
    vm.service.refresh(vm.dtInstance);
  }

  vm.close = close;
  function close() {
    vm.title = "GRN Edit";
    $state.go('app.inbound.GrnEdit');
  }
}
