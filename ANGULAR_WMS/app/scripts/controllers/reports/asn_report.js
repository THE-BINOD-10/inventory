'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ASNDataCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.service = Service;
  vm.datatable = false;

  vm.empty_data = {}
  vm.model_data = {};

  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;

  vm.toggle_sku_wise = true;

  vm.title = "ASN Report";
  vm.download_invoice_url = Session.url + 'download_grn_invoice_mapping/';

  vm.row_call = function(aData) {
    if (!vm.toggle_sku_wise) {
        if(aData.receipt_type == "Hosted Warehouse") {

          vm.title = "Stock transfer Note";
        }
        $http.get(Session.url+'print_po_reports/?'+aData.key+'='+aData.DT_RowAttr["data-id"]+'&receipt_no='+aData.receipt_no+'&prefix='+aData.prefix+'&warehouse_id='+aData.warehouse_id, {withCredential: true}).success(function(data, status, headers, config) {
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
  	// if (vm.toggle_sku_wise) {
   //    name = 'sku_wise_consumption_report';
   //  } else {
    name = 'get_asn_detail';
    // }
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
          var qr_button = DTColumnBuilder.newColumn(null).withTitle('').notSortable().withOption('width', '20px').renderWith(function(data, type, full, meta) {return "<button type='submit' class='btn btn-success pull-right'" +"style='margin: auto;display: block;'" +"ng-click='showCase.print_qr($event, data)'" +">Print QRCode</button>";})
          vm.dtColumns.push(qr_button)
          vm.datatable = true;
          vm.dtInstance = {};
          vm.report_data['excel2'] = false;
  		    vm.report_data['row_click'] = true;
          vm.report_data['excel_name'] = 'get_asn_detail'
          // if (vm.toggle_sku_wise) {
          //     vm.report_data['excel_name'] = 'get_sku_wise_consumption_report'
          // } else {
          // vm.report_data['excel_name'] = 'consumption_data'
          // }
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
                    'wms_code': ''
                    };

  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);

  vm.close = close;
  function close() {
    vm.title = "Purchase Order";
    $state.go('app.reports.ASNReports');
  }

  vm.print = print;
  function print() {
    console.log(vm.print_page);
    vm.service.print_data(vm.print_page, "Good Receipt Note");
  }
  function print_qr(event, data) {
    var dataDict = {
          'asn_number': data['ASN Number'],
          'warehouse_name': aData['Plant'] ,
          'po_number': aData['PO Number']
        }
        vm.service.apiCall('get_asn_qr_code/', 'GET', dataDict).then(function(res){
          if(res.message) {
            if (res.data.status == 'failed') {
             vm.service.pop_msg(res.data.message);
            }
            else {
              const file = new Blob([res.data], { type: 'application/pdf' })
              const fileURL = URL.createObjectURL(file)
              $('#proceedModal').modal('hide');
              window.open(fileURL)
            }
          }
        });
  }

}
