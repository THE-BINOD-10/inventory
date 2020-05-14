'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ApprovalPODetailReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

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
  vm.service.get_report_data("aprroval_po_detail_report").then(function(data) {
    angular.copy(data, vm.report_data);
    vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(data) {
      vm.empty_data = data.empty_data;
      angular.copy(vm.empty_data, vm.model_data);
      vm.dtOptions = data.dtOptions;
      vm.dtColumns = data.dtColumns;
      vm.report_data["row_call"] = vm.row_call;

//    vm.dtColumns.push(DTColumnBuilder.newColumn('PO Created Date').withTitle('PO Created Date'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('PO Release Date').withTitle('PO Release Date'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('PO Number').withTitle('PO Number'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('PO Created by').withTitle('PO Created by'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Status').withTitle('Status'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Supplier ID').withTitle('Supplier ID'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Supplier Name').withTitle('Supplier Name'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('SKU Description').withTitle('SKU Description'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('SKU Class').withTitle('SKU Class'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('SKU Style Name').withTitle('SKU Style Name'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('SKU Brand').withTitle('SKU Brand'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('SKU Category').withTitle('SKU Category'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Sub Category').withTitle('Sub Category'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('PO Qty').withTitle('PO Qty'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Unit Price without tax').withTitle('Unit Price without tax'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Unit Price with tax').withTitle('Unit Price with tax'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('MRP').withTitle('MRP'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Pre-Tax PO Amount').withTitle('Pre-Tax PO Amount'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Tax').withTitle('Tax'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('After Tax PO Amount').withTitle('After Tax PO Amount'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Qty received').withTitle('Qty received'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Status').withTitle('Status'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Warehouse Name').withTitle('Warehouse Name'))
//    vm.dtColumns.push(DTColumnBuilder.newColumn('Report Generation Time').withTitle('Report Generation Time'))

      vm.datatable = true;
    })
  })

  vm.print_page = "";
  vm.dtInstance = {};


  vm.close = close;
  function close() {
    vm.title = "Approval PO Detail Report";
    $state.go('app.reports.ApprovalPODetailReport');
  }
  vm.empty_data = {
                    'from_date': '',
                    'to_date': '',
                    };

}
