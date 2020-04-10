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
  vm.milkbasket_users = ['milkbasket_test', 'NOIDA02', 'NOIDA01', 'GGN01', 'HYD01', 'BLR01','GGN02', 'NOIDA03', 'BLR02', 'HYD02'];
  vm.toggle_sku_wise = false;
  vm.parent_username = Session.parent.userName;

  vm.title = "Purchase Order";
  //GRN Pop Data
  vm.grn_details = {po_number: 'PO Reference', supplier_id: 'Supplier ID', supplier_name: 'Supplier Name',
                    order_date: 'Order Date'}
  vm.grn_details_keys = Object.keys(vm.grn_details);

  vm.report_data = {};

  vm.row_call = function(aData) {
    // $http.get(Session.url+'get_grn_level_data/', {withCredential: true, 'po_number': aData['PO Number']}).success(function(data, status, headers, config) {
    //   console.log(data)
    // });
    vm.service.apiCall('get_grn_level_data/', 'GET', {po_number: aData['PO Number']}).then(function(data){
      vm.model_data = data.data;
      if (vm.industry_type == 'FMCG') {
        vm.extra_width = {
          'width': '1200px'
        };
      } else {
        vm.extra_width = {
          'width': '900px'
        };
      }
      angular.forEach(vm.model_data.data, function(mainSku){
        angular.forEach(mainSku, function(subSku){
          subSku['total_amt'] = vm.sku_total_amt(subSku);
        })
      })
    })
    $state.go('app.inbound.GrnEdit.GrnEditPopup');
  }
  vm.reports = {}

  vm.validate_weight = function(event, data) {
     if(vm.milkbasket_users.indexOf(vm.parent_username) >= 0){
       data.weight = data.weight.toUpperCase().replace('UNITS', 'Units').replace(/\s\s+/g, ' ').replace('PCS', 'Pcs').replace('UNIT', 'Unit').replace('INCHES', 'Inches').replace('INCH', 'Inch');
       setTimeout(() => { data.weight = data.weight.trim(); }, 100);
     }
   }

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
          if(data.data == 'Success') {
          // if(data.data.search("<div") != -1) {
            // vm.extra_width = {}
            // vm.html = $(data.data);
            // vm.extra_width = {}
            // //var html = $(vm.html).closest("form").clone();
            // //angular.element(".modal-body").html($(html).find(".modal-body"));
            // angular.element(".modal-body").html($(data.data));
            // vm.print_enable = true;
            vm.close();
            vm.service.refresh(vm.dtInstance);
          } else {
            pop_msg(data.data)
          }
        }
      });
    // }
  }

  vm.sku_total_amt = function (sku_row_data) {
    if (vm.industry_type == 'FMCG') {
      var total_amt = Number(sku_row_data.quantity)*Number(sku_row_data.buy_price);
    } else {
      var total_amt = Number(sku_row_data.quantity)*Number(sku_row_data.price);
    }

    var total_amt_dis = Number(total_amt) * Number(sku_row_data.discount_percentage) / 100;
    var tot_tax = Number(sku_row_data.tax_percent) + Number(sku_row_data.cess_percent);
    // var tot_tax = Number(sku_row_data.tax_percent) + Number(sku_row_data.cess_percent);
    var wo_tax_amt = Number(total_amt)-Number(total_amt_dis);

    return wo_tax_amt + (wo_tax_amt * (tot_tax/100));
  }

  vm.skus_total_amount = 0;
  vm.calc_total_amt = function(event, data, index, parent_index) {
    var sku_row_data = {};
    angular.copy(data.data[parent_index][index], sku_row_data);
    if(sku_row_data.buy_price == ''){
      sku_row_data.buy_price = 0;
    }
    if(sku_row_data.quantity == ''){
      sku_row_data.quantity = 0;
    }
    if(sku_row_data.tax_percent == ''){
      sku_row_data.tax_percent = 0;
    }
    if(sku_row_data.cess_percent == ''){
      sku_row_data.cess_percent = 0;
    }
    if(sku_row_data.discount_percentage == ''){
      sku_row_data.discount_percentage = 0;
    }
    if (Number(sku_row_data.tax_percent)) {

      sku_row_data.tax_percent = Number(sku_row_data.tax_percent).toFixed(1)
    }
    if (Number(sku_row_data.cess_percent)) {

      sku_row_data.cess_percent = Number(sku_row_data.cess_percent).toFixed(1)
    }
    vm.singleDecimalVal(sku_row_data.tax_percent, 'tax_percent', index, parent_index);
    vm.singleDecimalVal(sku_row_data.cess_percent, 'cess_percent', index, parent_index);
    // if (vm.industry_type == 'FMCG') {
    //   var total_amt = Number(sku_row_data.quantity)*Number(sku_row_data.buy_price);
    // } else {
    //   var total_amt = Number(sku_row_data.quantity)*Number(sku_row_data.price);
    // }
    //
    // var total_amt_dis = Number(total_amt) * Number(sku_row_data.discount_percentage) / 100;
    // var tot_tax = Number(sku_row_data.tax_percent) + Number(sku_row_data.cess_percent);
    // var wo_tax_amt = Number(total_amt)-Number(total_amt_dis);
    // data.data[parent_index][index].total_amt = wo_tax_amt + (wo_tax_amt * (tot_tax/100));
    data.data[parent_index][index].total_amt = vm.sku_total_amt(sku_row_data);
    var totals = 0;
    for(var index in data.data) {
      var rows = data.data[index];
      for (var d in rows) {
          if(!isNaN(rows[d]['total_amt'])) {
              totals += rows[d]['total_amt'];
          }
      }
    }
    vm.skus_total_amount = totals;
    $('.totals').text('Totals: ' + totals);
    vm.model_data.round_off_total = Math.round(totals * 100) / 100;
  }

  vm.pull_cls = "pull-right";
  vm.margin_cls = {marginRight: '50px'};
  vm.round_off_effects = function(key){

    vm.pull_cls = key ? 'pull-left' : 'pull-right';
    vm.margin_cls = key ? {marginRight: '0px'} : {marginRight: '50px'};
  }

  vm.singleDecimalVal = function(value, field, inIndex, outIndex){

    if (Number(value)) {

      vm.model_data.data[outIndex][inIndex][field] = Number(value).toFixed(1);
    }
  }

  function check_receive() {
    var status = false;
    for(var i=0; i<vm.model_data.data.length; i++)  {
      angular.forEach(vm.model_data.data[i], function(sku){
        if(sku.quantity > 0) {
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
    vm.model_data.invoice_number = '';
    $state.go('app.inbound.GrnEdit');
  }
}
