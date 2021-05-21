'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ConsumptionReversalCtrl',['$rootScope', '$compile','$q', '$timeout', '$scope', '$http', '$state', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($rootScope, $compile, $q, $timeout, $scope, $http, $state, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
  var vm = this;
  vm.service = Service;
  vm.colFilters = colFilters;
  vm.datatable = false;
  vm.label = 'Consumption Reversal Confirm';
  vm.empty_data = {}
  vm.model_data = {};

  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;

  vm.toggle_sku_wise = true;

  vm.title = "Consumption Reversal";
  vm.get_consumption_month = function get_consumption_month() {
    var curdate = new Date();
    var day = curdate.getDate();
    var newdate = curdate;
    if(day < 5){
      newdate = new Date(curdate.getFullYear(), curdate.getMonth()-1, 1);
    }
    vm.month_name = newdate.toLocaleString('default', { month: 'long' });
    vm.month_no = newdate.getMonth()+1;
    vm.year = newdate.getFullYear();
  }
  vm.get_consumption_month();
  // vm.row_call = function(aData) {
  //   if (!vm.toggle_sku_wise) {
  //       if(aData.receipt_type == "Hosted Warehouse") {

  //         vm.title = "Stock transfer Note";
  //       }
  //       $http.get(Session.url+'print_po_reports/?'+aData.key+'='+aData.DT_RowAttr["data-id"]+'&receipt_no='+aData.receipt_no+'&prefix='+aData.prefix+'&warehouse_id='+aData.warehouse_id, {withCredential: true}).success(function(data, status, headers, config) {
  //           var html = $(data);
  //           vm.print_page = $(html).clone();
  //           $(".modal-body").html(html);
  //         });
  //         $state.go('app.reports.GoodsReceiptNote.PurchaseOrder');
  //   }
  // }

  vm.report_data = {};
  vm.reports = {}
  vm.toggle_grn = function() {
    var send = {};
    vm.selected = {};
    vm.selectAll = false;
  	var name;
    name = 'get_sku_wise_consumption_reversal';
    vm.service.apiCall("get_report_data/", "GET", {report_name: name}).then(function(data) {
  	if(data.message) {
  	  if ($.isEmptyObject(data.data.data)) {
  		  vm.datatable = false;
  		  vm.dtInstance = {};
  	  } else {
  	    vm.reports[name] = data.data.data;
  	    angular.copy(data.data.data, vm.report_data);
        vm.report_data["row_call"] = vm.row_call;
        var send = {dtOptions: '', dtColumns: '', empty_data: {}};
        angular.forEach(vm.report_data.filters, function(data){
          send.empty_data[data.name] = ""
        });
        vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url + vm.report_data.dt_url + '/',
              type: 'POST',
              data: send.empty_data,
              xhrFields: {
                withCredentials: true
              },
              complete: function(jqXHR, textStatus) {
                vm.totals_tb_data = {};
                $rootScope.$apply(function(){
                  vm.tb_data = JSON.parse(jqXHR.responseText);
                  vm.totals_tb_data = vm.tb_data.totals;
                })
              }
           })
       .withDataProp('data')
       .withOption('order', [1, 'desc'])
       .withOption('lengthMenu', [10, 25, 50, 100, 200, 300, 400, 500, 1000, 2000, 3000, 5000])
       .withOption('drawCallback', function(settings) {
          vm.service.make_selected(settings, vm.selected);
        })
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withOption('createdRow', function(row, data, dataIndex) {
            $compile(angular.element(row).contents())($scope);
        })
        .withOption('headerCallback', function(header) {
            if (!vm.headerCompiled) {
                vm.headerCompiled = true;
                $compile(angular.element(header).contents())($scope);
            }
        })
       .withPaginationType('full_numbers')
        vm.dtColumns = [
          DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
              .renderWith(function(data, type, full, meta) {
                  if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                    vm.selected = {};
                  }
                  vm.selected[meta.row] = vm.selectAll;
                  return vm.service.frontHtml + meta.row + vm.service.endHtml;
              }).notSortable(),
          DTColumnBuilder.newColumn('Consumption ID').withTitle('Consumption ID'),
          DTColumnBuilder.newColumn('Date').withTitle('Date'),
          DTColumnBuilder.newColumn('Plant Code').withTitle('Plant Code'),
          DTColumnBuilder.newColumn('Department').withTitle('Department'),
          DTColumnBuilder.newColumn('Warehouse Username').withTitle('Warehouse Username'),
          DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
          DTColumnBuilder.newColumn('SKU Conversion').withTitle('SKU Conversion'),
          DTColumnBuilder.newColumn('Base Quantity').withTitle('Base Quantity'),
          DTColumnBuilder.newColumn('Purchase Uom Quantity').withTitle('Purchase Uom Quantity'),
          DTColumnBuilder.newColumn('Stock Value').withTitle('Stock Value'),
          DTColumnBuilder.newColumn('Type').withTitle('Type').notSortable(),
        ];
        vm.datatable = true;
        vm.dtInstance = {};
        vm.report_data['excel2'] = false;
        vm.report_data['row_click'] = true;
        vm.report_data['excel_name'] = 'get_sku_wise_consumption_reversal';
  	  }
  	}
    })
  }
  vm.toggle_grn()
  vm.print_page = "";
  vm.dtInstance = {};
  vm.empty_data = {
                    "wms_code": "",
                    "plant_code":"",
                    "plant_name":"",
                    "sister_warehouse":"","zone_code":"","consumption_type":"","order_id":""
                    };
  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);
  vm.close = close;
  vm.confirm_reversal = function () {
    vm.reversal_bt_disable = true;
    vm.label = 'Consumption Reversal Processing ... Please Wait until Success Notfication';
    vm.generate_data = [];
    for (var key in vm.selected) {
      if(vm.selected[key]) {
        vm.generate_data.push(vm.dtInstance.DataTable.context[0].aoData[key]._aData['id']);
      }
    }
    if (vm.generate_data.length > 0) {
      swal({
        title: "Do you want cancel these Consumptions",
        text: "Are you sure?",
        type: "warning",
        showCancelButton: true,
        confirmButtonColor: "#DD6B55",
        confirmButtonText: "Yes, delete it!",
        cancelButtonText: "No, Cancel",
        closeOnConfirm: true,
        closeOnCancel: true
     },
     function(isConfirm){
        if (isConfirm) {
          vm.common_confirm_reversal();       
        } else {
          $scope.$apply(function(){
            vm.label = 'Consumption Reversal Confirm';
            vm.reversal_bt_disable = false;
          })
        }
     });
    } else {
      vm.label = 'Consumption Reversal Confirm';
      vm.reversal_bt_disable = false;
      vm.service.showNoty('please select the ConsumptionIds');
    }
  }

  vm.common_confirm_reversal = function () {
    vm.service.apiCall('delete_consumption_data/', 'POST', {'data':JSON.stringify(vm.generate_data)}, true).then(function(data){
      if (data.data == "Success") {
        vm.label = 'Consumption Reversal Confirm';
        vm.reversal_bt_disable = false;
        vm.dtInstance.reloadData();
        swal("Cancelled!", "Consumptions are deleted", "success");
      } else {
        vm.label = 'Consumption Reversal Confirm';
        vm.reversal_bt_disable = false;
        vm.dtInstance.reloadData();
        swal("OOPS!", "Consumption Deletion Failed", "error");
      }
    });
  }

}
