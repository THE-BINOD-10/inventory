'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PRPOGRNCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
  var vm = this;
  vm.host = Session.host;
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
        vm.file_url = "";
        vm.consolated_file_url = "";
        vm.FileDownload(aData);
        $http.get(Session.url+'print_po_reports/?'+aData.key+'='+aData.DT_RowAttr["data-id"]+'&receipt_no='+aData.receipt_no+'&prefix='+aData.prefix+'&warehouse_id='+aData.warehouse_id+'&grn_number='+aData['GRN Number'], {withCredential: true}).success(function(data, status, headers, config) {
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
    name = 'pr_po_grn_dict';
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
              vm.report_data['excel_name'] = 'pr_po_grn_dict'
          }
        })
  	  }
  	}
    })
  }

  vm.toggle_grn()
  vm.FileDownload = function(aData,type=''){
    if(type){
      var src = (type == 'download') ? vm.host+vm.file_url : vm.host+vm.consolated_file_url;
      var mywindow = window.open(src, 'height=400,width=600');
      mywindow.focus();
      return true;
    } else if (aData){
      var data_dict = {
        'receipt_no':aData.receipt_no,
        'prefix':aData.prefix,
        'warehouse_id':aData.warehouse_id,
        'po_id':aData.DT_RowAttr["data-id"],
        'grn_number': aData['GRN Number'],
        'po_number': aData['PO Number']
      }
      vm.service.apiCall('download_invoice_file/', 'GET', data_dict).then(function(data) {
        if (data.data) {
          if (typeof(data.data) == "string") {
            vm.file_url = data.data;
          } else if (typeof(data.data) == "object") {
            vm.consolated_file_url = data.data[0];
            vm.file_url = data.data[1];
          } else {
            vm.file_url = data.data;
          }
        }
      });
    }
  }

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
    $state.go('app.reports.GoodsReceiptNote');
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
