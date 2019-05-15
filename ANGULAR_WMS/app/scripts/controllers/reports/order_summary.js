'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('OrderSummaryCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;

  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  vm.datatable = false;

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
      if(vm.permissions.central_order_reassigning)
      {
        vm.dtColumns.push(DTColumnBuilder.newColumn('Serial Number').withTitle('Serial Number'))
      }
      vm.dtColumns.push(DTColumnBuilder.newColumn('Order Number').withTitle('Order Number'))

      vm.datatable = true;
      vm.dtInstance = {};
    })
  })

  vm.change_datatable = function()
  {
     if(vm.invoice_number_show)
     {
      vm.dtColumns.push(DTColumnBuilder.newColumn('Invoice Number').withTitle('Invoice Number'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('Quantity').withTitle('Quantity'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('Invoice Date').withTitle('Invoice Date'))
      vm.model_data.invoice = "true"
     }
     else{
       vm.dtColumns.pop(DTColumnBuilder.newColumn('Invoice Number').withTitle('Invoice Number'))
       vm.dtColumns.pop(DTColumnBuilder.newColumn('Quantity').withTitle('Quantity'))
       vm.dtColumns.pop(DTColumnBuilder.newColumn('Invoice Date').withTitle('Invoice Date'))
       vm.model_data.invoice = "false"
     }
  }
 vm.reset = function()
 {

  vm.invoice_number_show = false;
   vm.change_datatable ();
 }



  }
