'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CreditNoteReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

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
  vm.service.get_report_data("credit_note_report").then(function(data) {
    angular.copy(data, vm.report_data);
    vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(data) {
      vm.empty_data = data.empty_data;
      angular.copy(vm.empty_data, vm.model_data);
      vm.dtOptions = data.dtOptions;
      vm.dtColumns = data.dtColumns;
      vm.report_data["row_call"] = vm.row_call;

    vm.dtColumns.push(DTColumnBuilder.newColumn('Credit Note Number').withTitle('Credit Note Number'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Customer ID').withTitle('Customer ID'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Customer Name').withTitle('Customer Name'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Order ID').withTitle('Order ID'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Invoice Number').withTitle('Invoice Number'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Return Date').withTitle('Return Date'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Reason').withTitle('Reason'))
    vm.dtColumns.push(DTColumnBuilder.newColumn('Updated User').withTitle('Updated User'))

      vm.datatable = true;
    })
  })

  vm.print_page = "";
  vm.dtInstance = {};

//  function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
//        $('td', nRow).unbind('click');
//        $('td', nRow).bind('click', function() {
//        vm.service.apiCall("reprint_credit_note_report/", "POST", {"credit_note_number":aData.credit_note_number}).then(function(data){
//        console.log(aData)
//            $state.go('app.inbound.SalesReturns.ScanReturnsPrint');
//            $timeout(function () {
//              $(".modal-body:visible").html(data.data);
//            }, 3000);
//      })
//    })
//        return nRow;
//    }
 vm.row_call = function(aData) {
    vm.title = 'Credit Note Report';
    vm.service.apiCall('print_credit_note_report/?credit_note_number='+aData['Credit Note Number']).then(function(data){
      var html = $(data.data);
      vm.print_page = $(html).clone();
      $(".modal-body").html(html);
      vm.print_enable = true;
    });
    $state.go('app.reports.CreditNoteReport.CreditNoteReportPrint');

  }
  vm.close = close;
  function close() {
    vm.title = "Credit Note Report";
    $state.go('app.reports.CreditNoteReport');
  }
  vm.print = print;
  vm.print = function() {
    console.log(vm.print_page);
    vm.service.print_data(vm.print_page, "Credit Note Report");
  }

  vm.empty_data = {
                    'from_date': '',
                    'to_date': '',
                    'sku_code': '',
                    'customer_id' :'',
                    'invoice_number':'',
                    'order_id':'',
                    };

}
