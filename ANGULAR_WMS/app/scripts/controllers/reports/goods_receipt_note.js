'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('GoodsReceiptNoteCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

    /*var vm = this;
    vm.colFilters = colFilters;
    vm.service = Service;
    vm.service.print_enable = false;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'get_po_filter/',
              type: 'GET',
              data: vm.model_data,
              xhrFields: {
                withCredentials: true
              },
              data: vm.model_data
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

    vm.dtColumns = [
        DTColumnBuilder.newColumn('PO Number').withTitle('PO Number'),
        DTColumnBuilder.newColumn('Supplier ID').withTitle('Supplier ID'),
        DTColumnBuilder.newColumn('Supplier Name').withTitle('Supplier Name'),
        DTColumnBuilder.newColumn('Total Quantity').withTitle('Total Quantity')
    ];

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        // Unbind first in order to avoid any duplicate handler (see https://github.com/l-lin/angular-datatables/issues/87)
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
                $http.get(Session.url+'print_po_reports/?data='+aData.DT_RowAttr["data-id"], {withCredential: true}).success(function(data, status, headers, config) {

                  console.log(data);
                  var html = $(data);
                  vm.print_page = $(html).clone();
                  html = $(html).find(".modal-body > .form-group");
                  $(html).find(".modal-footer").remove()
                  $(".modal-body").html(html);
                });
                $state.go('app.reports.GoodsReceiptNote.PurchaseOrder');
            });
        });
        return nRow;
    }

  */
  var vm = this;
  vm.service = Service;
  vm.datatable = false;

  vm.empty_data = {}
  vm.model_data = {};

  vm.row_call = function(aData) {

    console.log(aData);
    $http.get(Session.url+'print_po_reports/?data='+aData.DT_RowAttr["data-id"], {withCredential: true})
      .success(function(data, status, headers, config) {
        console.log(data);
        var html = $(data);
        vm.print_page = $(html).clone();
        html = $(html).find(".modal-body > .form-group");
        $(html).find(".modal-footer").remove()
        $(".modal-body").html(html);
      });
      $state.go('app.reports.GoodsReceiptNote.PurchaseOrder');
  }

  vm.report_data = {};
  vm.service.get_report_data("grn_report").then(function(data){

    angular.copy(data, vm.report_data);
    vm.report_data["row_call"] = vm.row_call;
    vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(data){

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
                    'open_po': '',
                    'wms_code': ''
                    };

  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);

  vm.close = close;
  function close() {
    $state.go('app.reports.GoodsReceiptNote');
  }

  vm.print = print;
  function print() {
    console.log(vm.print_page);
    vm.service.print_data(vm.print_page, "Good Receipt Note");
  }

  }

