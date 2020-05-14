'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ApprovalPOSummaryReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  vm.datatable = false;
  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;

  vm.empty_data = {};
  vm.model_data = {};

  vm.report_data = {};
  vm.service.get_report_data("aprroval_po_summary_report").then(function(data) {
    angular.copy(data, vm.report_data);
    vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(data) {
      vm.empty_data = data.empty_data;
      angular.copy(vm.empty_data, vm.model_data);
      vm.dtOptions = data.dtOptions;
      vm.dtColumns = data.dtColumns;
      vm.report_data["row_call"] = vm.row_call;

//    vm.dtColumns.push(DTColumnBuilder.newColumn('PO Date').withTitle('PO Date'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('PO Number').withTitle('PO Number'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Supplier ID').withTitle('Supplier ID'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Supplier Name').withTitle('Supplier Name'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Expected Delivery').withTitle('Expected Delivery'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Ordered Quantity').withTitle('Ordered Quantity'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Base Amount').withTitle('Base Amount'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Tax Amount').withTitle('Tax Amount'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Total Amount').withTitle('Total Amount'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Final Status').withTitle('Final Status'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Created by').withTitle('Created by'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Approver 1').withTitle('Approver 1'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Approver 1 Date').withTitle('Approver 1 Date'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Approver 1 Status').withTitle('Approver 1 Status'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Approver 2').withTitle('Approver 2'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Approver 2 Date').withTitle('Approver 2 Date'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Approver 2 Status').withTitle('Approver 2 Status'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Approver 3').withTitle('Approver 3'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Approver 3 Date').withTitle('Approver 3 Date'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Approver 3 Status').withTitle('Approver 3 Status'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Approver 4').withTitle('Approver 4'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Approver 4 Date').withTitle('Approver 4 Date'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Approver 4 Status').withTitle('Approver 4 Status'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Approver 5').withTitle('Approver 5'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Approver 5 Date').withTitle('Approver 5 Date'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Approver 5 Status').withTitle('Approver 5 Status'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('PO Release Date').withTitle('PO Release Date'))
//    //vm.dtColumns.push(DTColumnBuilder.newColumn('Remarks').withTitle('Remarks'))

      vm.datatable = true;
    })
  })

  vm.print_page = "";
  vm.dtInstance = {};


  vm.close = close;
  function close() {
    vm.title = "Approval PO Summary Report";
    $state.go('app.reports.ApprovalPOSummaryReport');
  }
  vm.empty_data = {
                    'from_date': '',
                    'to_date': '',
                    };

}
