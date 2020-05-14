'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ApprovalPOReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
  var vm = this;
  vm.service = Service;
  vm.datatable = false;

  vm.empty_data = {}
  vm.model_data = {};

  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;

  vm.toggle_sku_wise = false;

  vm.title = "Purchase Order";
  vm.download_invoice_url = Session.url + 'download_grn_invoice_mapping/';

  vm.row_call = function(aData) {
    if (!vm.toggle_sku_wise) {
        if(aData.receipt_type == "Hosted Warehouse") {

          vm.title = "Stock transfer Note";
        }
        $http.get(Session.url+'print_po_reports/?'+aData.key+'='+aData.DT_RowAttr["data-id"]+'&receipt_no='+aData.receipt_no+'&st_grn='+1+'&prefix='+aData.prefix, {withCredential: true}).success(function(data, status, headers, config) {
            var html = $(data);
            vm.print_page = $(html).clone();
            //html = $(html).find(".modal-body > .form-group");
            //$(html).find(".modal-footer").remove()
            $(".modal-body").html(html);
          });
          $state.go('app.reports.ApprovalPOReport');
    }
  }

  vm.report_data = {};

  vm.reports = {}
  vm.toggle_grn = function() {
    var send = {};
  	var name;
  	if (vm.toggle_po_sku_wise) {
      name = 'approval_po_summary_report';
    } else {
      name = 'approval_po_detail_report';
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
              vm.report_data['excel_name'] = 'approval_po_summary_report'
          } else {
              vm.report_data['excel_name'] = 'approval_po_detail_report'
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
                    'invoice_number': '',
                    'wms_code': ''
                    };

  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);

  vm.close = close;
  function close() {
    vm.title = "Purchase Order";
    $state.go('app.reports.');
  }

  vm.print = print;
  function print() {
    console.log(vm.print_page);
    vm.service.print_data(vm.print_page, "Good Receipt Note");
  }

  vm.download_invoice_zip = function() {
    console.log(vm.model_data);
    var filt_string = ''
    angular.forEach(vm.model_data, function(val, key){
      if(filt_string) {
        filt_string += '&' + key + '=' + val
      }
      else {
        filt_string = key + '=' + val
      }
    });
    vm.download_invoice_url = Session.url + 'download_grn_invoice_mapping/' + '?' + filt_string;
  }

}
