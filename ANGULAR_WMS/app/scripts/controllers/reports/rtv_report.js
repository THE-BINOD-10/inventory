'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('RTVReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.service = Service;
  vm.datatable = false;

  vm.empty_data = {};
  vm.model_data = {};

  vm.row_call = function(aData) {
    vm.title = 'Debit Note';
    $http.get(Session.url+'print_debit_note/?rtv_number='+aData['RTV Number'], {withCredential: true}).success(function(data, status, headers, config) {
      var html = $(data);
      vm.print_page = $(html).clone();
      $(".modal-body").html(html);
      vm.print_enable = true;
    });
    $state.go('app.reports.RTVReport.DebitNotePrint');
  }

  vm.close = close;
  function close() {
    vm.title = "Debit Note";
    $state.go('app.reports.RTVReport');
  }

  vm.print = print;
  vm.print = function() {
    console.log(vm.print_page);
    vm.service.print_data(vm.print_page, "Debit Note");
  }

  vm.report_data = {};
  vm.service.get_report_data("rtv_report").then(function(data) {
    angular.copy(data, vm.report_data);
    vm.report_data["row_call"] = vm.row_call;
    vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(data) {
      vm.empty_data = data.empty_data;
      angular.copy(vm.empty_data, vm.model_data);
      vm.dtOptions = data.dtOptions;
      vm.dtColumns = data.dtColumns;
      vm.datatable = true;
      vm.dtInstance = {};
    })
  })

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
