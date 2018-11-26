'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('OrderSummaryCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;

  vm.service = Service;
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
      vm.datatable = true;
      vm.dtInstance = {};
    })
  })
  vm.change_datatable = function()
  {
     if(vm.invoice_number)
     {
      vm.dtColumns.push(DTColumnBuilder.newColumn('Invoice Number').withTitle('Invoice Number'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('Quantity').withTitle('Quantity'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('Invoice Date').withTitle('Invoice Date'))
     }
     else{
       vm.dtColumns.pop(DTColumnBuilder.newColumn('Invoice Number').withTitle('Invoice Number'))
       vm.dtColumns.pop(DTColumnBuilder.newColumn('Quantity').withTitle('Quantity'))
       vm.dtColumns.pop(DTColumnBuilder.newColumn('Invoice Date').withTitle('Invoice Date'))
     }
  }




  }
