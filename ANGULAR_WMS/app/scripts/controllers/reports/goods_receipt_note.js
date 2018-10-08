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

  vm.toggle_sku_wise = false;

  vm.title = "Purchase Order";

  vm.row_call = function(aData) {
    if (!vm.toggle_sku_wise) {
        if(aData.receipt_type == "Hosted Warehouse") {

          vm.title = "Stock transfer Note";
        }
        $http.get(Session.url+'print_po_reports/?'+aData.key+'='+aData.DT_RowAttr["data-id"]+'&receipt_no='+aData.receipt_no, {withCredential: true}).success(function(data, status, headers, config) {
            var html = $(data);
            vm.print_page = $(html).clone();
            //html = $(html).find(".modal-body > .form-group");
            //$(html).find(".modal-footer").remove()
            $(".modal-body").html(html);
          });
          $state.go('app.reports.GoodsReceiptNote.PurchaseOrder');
    }
  }

  vm.report_data = {};

  vm.reports = {}
  vm.toggle_grn = function() {
    var send = {};
  	var name;
  	if (vm.toggle_sku_wise) {
      name = 'sku_wise_grn_report';
    } else {
      name = 'grn_report';
    }
    vm.service.apiCall("get_report_data/", "GET", {report_name: name}).then(function(data) {
  	if(data.message) {
  	  if ($.isEmptyObject(data.data.data)) {
  		  vm.datatable = false;
  		  vm.dtInstance = {};
  	  } else {
  	    vm.reports[name] = data.data.data;
  	    angular.copy(data.data.data, vm.report_data);
        vm.report_data["row_call"] = vm.row_call;
        vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(datam) {
          vm.empty_data = datam.empty_data;
          angular.copy(vm.empty_data, vm.model_data);
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
                    'open_po': '',
                    'wms_code': ''
                    };

  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);

  vm.close = close;
  function close() {
    vm.title = "Purchase Order";
    $state.go('app.reports.GoodsReceiptNote');
  }

  vm.print = print;
  function print() {
    console.log(vm.print_page);
    vm.service.print_data(vm.print_page, "Good Receipt Note");
  }

  }

