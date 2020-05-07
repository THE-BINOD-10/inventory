'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('OpenPOApprovalReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

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
  vm.service.get_report_data("open_po_aprroval_report").then(function(data) {
    angular.copy(data, vm.report_data);
    vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(data) {
      vm.empty_data = data.empty_data;
      angular.copy(vm.empty_data, vm.model_data);
      vm.dtOptions = data.dtOptions;
      vm.dtColumns = data.dtColumns;
      vm.report_data["row_call"] = vm.row_call;

    vm.dtColumns.push(DTColumnBuilder.newColumn('PO Number').withTitle('PO Number'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Supplier ID').withTitle('Supplier ID'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Supplier Name').withTitle('Supplier Name'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Total Quantity').withTitle('Total Quantity'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Total Amount').withTitle('Total Amount'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('PO Created Date').withTitle('PO Created Date'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('PO Delivery Date').withTitle('PO Delivery Date'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Warehouse').withTitle('Warehouse'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('PO Raise By').withTitle('PO Raise By'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Validation Status').withTitle('Validation Status'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Pending Level').withTitle('Pending Level'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('To Be Approved By').withTitle('To Be Approved By'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Last Updated By').withTitle('Last Updated By'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Last Updated At').withTitle('Last Updated At'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Remarks').withTitle('Remarks'))

      vm.datatable = true;
    })
  })

  vm.print_page = "";
  vm.dtInstance = {};


  vm.close = close;
  function close() {
    vm.title = "Open PO Approval Report";
    $state.go('app.reports.OpenPOApprovalReport');
  }
  vm.empty_data = {
                    'from_date': '',
                    'to_date': '',
                    };

}
