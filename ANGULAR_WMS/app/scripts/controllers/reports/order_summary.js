'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('OrderSummaryCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;

  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  vm.datatable = false;
  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;
  vm.parent_username = Session.parent.parent_username;

  vm.empty_data = {}
  vm.model_data = {};

  vm.report_data = {};
  vm.service.get_report_data("order_summary_report").then(function(data){
    angular.copy(data, vm.report_data);
    vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(data){
      vm.empty_data = data.empty_data;
      angular.copy(vm.empty_data, vm.model_data);
      vm.dtOptions = data.dtOptions;
      vm.dtColumns = data.dtColumns;
      if (vm.permissions.dispatch_qc_check) {
        for (var i = 0; i < vm.dtColumns.length; i++) {
          if (vm.dtColumns[i].mData == 'Order ID'){
            vm.dtColumns[i].sTitle = 'Main SR Number';
          }
        }
      }
      if(vm.permissions.central_order_reassigning)
      {
        vm.dtColumns.push(DTColumnBuilder.newColumn('Serial Number').withTitle('Serial Number'))
      }
      vm.datatable = true;
      vm.dtInstance = {};
    })
  })

  vm.change_datatable = function() {
    if(vm.invoice_number_show) {
     vm.dtColumns.push(DTColumnBuilder.newColumn('Invoice Number').withTitle('Invoice Number'))
     vm.dtColumns.push(DTColumnBuilder.newColumn('Challan Number').withTitle('Challan Number'))
     vm.dtColumns.push(DTColumnBuilder.newColumn('Total Procurement Price').withTitle('Total Procurement Price'))
     vm.dtColumns.push(DTColumnBuilder.newColumn('Procurement Price').withTitle('Procurement Price'))
     vm.dtColumns.push(DTColumnBuilder.newColumn('Margin').withTitle('Margin'))
     vm.dtColumns.push(DTColumnBuilder.newColumn('Invoice Qty').withTitle('Invoice Qty'))
     vm.dtColumns.push(DTColumnBuilder.newColumn('Invoice Date').withTitle('Invoice Date'))
     vm.dtColumns.push(DTColumnBuilder.newColumn('Invoice Amt(w/o tax)').withTitle('Invoice Amt(w/o tax)'))
     vm.dtColumns.push(DTColumnBuilder.newColumn('Invoice Amount').withTitle('Invoice Amount'))
     vm.dtColumns.push(DTColumnBuilder.newColumn('Invoice Tax Amt').withTitle('Invoice Tax Amt'))
     vm.dtColumns.push(DTColumnBuilder.newColumn('EwayBill Number').withTitle('EwayBill Number'))
     vm.model_data.invoice = "true"
    } else {
      vm.dtColumns.pop(DTColumnBuilder.newColumn('Invoice Number').withTitle('Invoice Number'))
      vm.dtColumns.pop(DTColumnBuilder.newColumn('Challan Number').withTitle('Challan Number'))
      vm.dtColumns.pop(DTColumnBuilder.newColumn('Total Procurement Price').withTitle('Total Procurement Price'))
      vm.dtColumns.pop(DTColumnBuilder.newColumn('Procurement Price').withTitle('Procurement Price'))
      vm.dtColumns.pop(DTColumnBuilder.newColumn('Margin').withTitle('Margin'))
      vm.dtColumns.pop(DTColumnBuilder.newColumn('Invoice Qty').withTitle('Invoice Qty'))
      vm.dtColumns.pop(DTColumnBuilder.newColumn('Invoice Date').withTitle('Invoice Date'))
      vm.dtColumns.pop(DTColumnBuilder.newColumn('Invoice Amt(w/o tax)').withTitle('Invoice Amt(w/o tax)'))
      vm.dtColumns.pop(DTColumnBuilder.newColumn('Invoice Amount').withTitle('Invoice Amount'))
      vm.dtColumns.pop(DTColumnBuilder.newColumn('Invoice Tax Amt').withTitle('Invoice Tax Amt'))
      vm.dtColumns.pop(DTColumnBuilder.newColumn('EwayBill Number').withTitle('EwayBill Number'))
      vm.model_data.invoice = "false"
    }
  }
 vm.reset = function() {
  vm.invoice_number_show = false;
  vm.change_datatable ();
 }



  }
