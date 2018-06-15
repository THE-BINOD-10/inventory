FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('RTVCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {
    // var vm = this;
    // vm.permissions = Session.roles.permissions;
    // vm.apply_filters = colFilters;
    // vm.service = Service;
    // vm.self_life_ratio = Number(vm.permissions.shelf_life_ratio) || 0;
    // vm.industry_type = Session.user_profile.industry_type;
    // // vm.industry_type = 'FMCG';

    // //default values
    // if(!vm.permissions.grn_scan_option) {
    //   vm.permissions.grn_scan_option = "sku_serial_scan";
    // }
    // if(!vm.permissions.barcode_generate_opt) {
    //   vm.permissions.barcode_generate_opt = 'sku_code';
    // }
    // if(vm.permissions.barcode_generate_opt == 'sku_ean') {
    //   vm.permissions.barcode_generate_opt = 'sku_code';
    // }

    // //process type;
    // vm.po_qc = true;
    // vm.po_qc = (vm.permissions.receive_process == "receipt-qc")? true: false;
    // vm.g_data = Data.receive_po;

    // var sort_no = (vm.g_data.style_view)? 1: 0;
    // vm.filters = {'datatable': 'ReturnToVendor', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': ''};
    // vm.dtOptions = DTOptionsBuilder.newOptions()
    //    .withOption('ajax', {
    //           url: Session.url+'results_data/',
    //           type: 'POST',
    //           data: vm.filters,
    //           xhrFields: {
    //             withCredentials: true
    //           }
    //        })
    //    .withDataProp('data')
    //    .withOption('order', [sort_no, 'desc'])
    //    .withOption('processing', true)
    //    .withOption('serverSide', true)
    //    .withOption('createdRow', function(row, data, dataIndex) {
    //         $compile(angular.element(row).contents())($scope);
    //     })
    //     .withOption('headerCallback', function(header) {
    //         if (!vm.headerCompiled) {
    //             vm.headerCompiled = true;
    //             $compile(angular.element(header).contents())($scope);
    //         }
    //     })
    //    .withPaginationType('full_numbers')
    //    .withOption('rowCallback', rowCallback)
    //    .withOption('initComplete', function( settings ) {
    //      vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
    //    });

    // vm.dtColumns = [
    //     DTColumnBuilder.newColumn('Supplier ID').withTitle('Supplier ID'),
    //     DTColumnBuilder.newColumn('PO Number').withTitle('PO Number'),
    //     DTColumnBuilder.newColumn('PO Date').withTitle('PO Date'),
    //     DTColumnBuilder.newColumn('Invoice Number').withTitle('Invoice Number'),
    //     DTColumnBuilder.newColumn('Invoice Date').withTitle('Invoice Date'),
    // ];


    // // var columns = ['Supplier ID', 'PO Reference', 'Customer Name', 'Order Date', 'Expected Date', 'Total Qty', 'Receivable Qty', 'Received Qty',
    // //                'Remarks', 'Supplier ID/Name', 'Order Type', 'Receive Status'];
    // // var columns = ['PO No', 'PO Reference', 'Customer Name', 'Order Date', 'Expected Date', 'Total Qty', 'Receivable Qty', 'Received Qty',
    // //                'Remarks', 'Supplier ID/Name', 'Order Type', 'Receive Status'];
    // // vm.dtColumns = vm.service.build_colums(columns);

    // var row_click_bind = 'td';
    // if(vm.g_data.style_view) {
    //   var toggle = DTColumnBuilder.newColumn('PO No').withTitle(' ').notSortable()
    //              .withOption('width', '25px').renderWith(function(data, type, full, meta) {
    //                return "<i ng-click='showCase.addRowData($event, "+JSON.stringify(full)+")' class='fa fa-plus-square'></i>";
    //              })
    //   row_click_bind = 'td:not(td:first)';
    // } else {

    //   var toggle = DTColumnBuilder.newColumn('PO No').withTitle(' ').notSortable().notVisible();
    // }
    // vm.dtColumns.unshift(toggle);
    // vm.dtInstance = {};
    // vm.poDataNotFound = function() {
    //   $(elem).removeClass();
    //   $(elem).addClass('fa fa-plus-square');
    //   Service.showNoty('Something went wrong')
    // }
    // vm.addRowData = function(event, data) {
    //   console.log(data);
    //   var elem = event.target;
    //   if (!$(elem).hasClass('fa')) {
    //     return false;
    //   }
    //   var data_tr = angular.element(elem).parent().parent();
    //   if ($(elem).hasClass('fa-plus-square')) {
    //     $(elem).removeClass('fa-plus-square');
    //     $(elem).removeClass();
    //     $(elem).addClass('glyphicon glyphicon-refresh glyphicon-refresh-animate');
    //     Service.apiCall('get_receive_po_style_view/?order_id='+data['PO No'].split("_")[1]).then(function(resp){
    //       if (resp.message){

    //         if(resp.data.status) {
    //           var html = $compile("<tr class='row-expansion' style='display: none'><td colspan='13'><dt-po-data data='"+JSON.stringify(resp.data)+"' preview='showCase.preview'></dt-po-data></td></tr>")($scope);
    //           data_tr.after(html)
    //           data_tr.next().toggle(1000);
    //           $(elem).removeClass();
    //           $(elem).addClass('fa fa-minus-square');
    //         } else {
    //           vm.poDataNotFound();
    //         }
    //       } else {
    //         vm.poDataNotFound();
    //       }
    //     })
    //   } else {
    //     $(elem).removeClass('fa-minus-square');
    //     $(elem).addClass('fa-plus-square');
    //     data_tr.next().remove();
    //   }
    // }

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.date = new Date();

    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;

    vm.filters = {'datatable': 'ReturnToVendor', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': ''}
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: vm.filters,
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
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
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    // var columns = ["PO Number", "Seller Name", "Receipt Date", "Order Quantity", "Received Quantity", "Invoice Number"];
    // vm.dtColumns = vm.service.build_colums(columns);

    vm.dtColumns = [
        DTColumnBuilder.newColumn('Supplier ID').withTitle('Supplier ID'),
        DTColumnBuilder.newColumn('PO Number').withTitle('PO Number'),
        DTColumnBuilder.newColumn('PO Date').withTitle('PO Date'),
        DTColumnBuilder.newColumn('Invoice Number').withTitle('Invoice Number'),
        DTColumnBuilder.newColumn('Invoice Date').withTitle('Invoice Date'),
    ];

    vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
                .renderWith(function(data, type, full, meta) {
                  if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                    vm.selected = {};
                  }
                  vm.selected[meta.row] = vm.selectAll;
                  return vm.service.frontHtml + meta.row + vm.service.endHtml;
                }))

    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $(row_click_bind, nRow).unbind('click');
        $(row_click_bind, nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.service.apiCall('get_rtv_data/', 'GET', {supplier_id: aData['DT_RowId']}).then(function(data){
                  if(data.message) {
                    vm.serial_numbers = [];
                    angular.copy(data.data, vm.model_data);
                    vm.title = "Return to Vendor";
                    $state.go('app.inbound.rtv.details');
                  }
                });
            });
        });
        return nRow;
    }

    vm.filter_enable = true;
    vm.print_enable = false;
    vm.update = false;
    vm.model_data = {};
    vm.dis = true;

    vm.close = close;
    function close() {

      vm.model_data = {};
      $state.go('app.inbound.rtv');
    }

    vm.update_data = update_data;
    function update_data(index, data) {
      if (Session.roles.permissions['pallet_switch'] || vm.industry_type == 'FMCG') {
        if (index == data.length-1) {
          var new_dic = {};
          angular.copy(data[0], new_dic);
          new_dic.receive_quantity = 0;
          new_dic.value = "";
          new_dic.pallet_number = "";
          new_dic.batch_no = "";
          new_dic.manf_date = "";
          new_dic.exp_date = "";
          new_dic.tax_percent = "";
          data.push(new_dic);
        } else {
          data.splice(index,1);
        }
      }
    }
    
    vm.new_sku = false
    vm.add_wms_code = add_wms_code;
    function add_wms_code() {
      vm.model_data.data.push([{"wms_code":"", "po_quantity":"", "receive_quantity":"", "price":"", "dis": false,
                                "order_id": vm.model_data.data[0][0].order_id, is_new: true, "unit": "",
                                "sku_details": [{"fields": {"load_unit_handle": ""}}]}]);
      //vm.new_sku = true
    }
    vm.get_sku_details = function(data, selected) {

      data.sku_details[0].fields.load_unit_handle = selected.load_unit_handle;
      data.wms_code = selected.wms_code;
      $timeout(function() {$scope.$apply();}, 1000);
    }

    vm.submit = submit;
    function submit(form) {
      var data = [];

      for(var i=0; i<vm.model_data.data.length; i++)  {
        var temp = vm.model_data.data[i][0];
        if(!temp.is_new) {
          data.push({name: temp.order_id, value: temp.value});
        }
      }
      data.push({name: 'remarks', value: vm.model_data.remarks});
      data.push({name: 'expected_date', value: vm.model_data.expected_date});
      data.push({name: 'remainder_mail', value: vm.model_data.remainder_mail});
      vm.service.apiCall('update_putaway/', 'GET', data, true).then(function(data){
        if(data.message) {
          if(data.data == 'Updated Successfully') {
            vm.close();
            vm.service.refresh(vm.dtInstance);
          } else {
            pop_msg(data.data);
          }
        }
      });
    }

    function check_receive() {
      var status = false;
      for(var i=0; i<vm.model_data.data.length; i++)  {
        if(vm.model_data.data[i][0].value > 0) {
          status = true;
          break;
        }
      }
      if(status){
        return true;
      } else {
        pop_msg("Please Update the received quantity");
        return false;
      }
    }

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
        vm.message = "";
      }, 2000);
      vm.service.refresh(vm.dtInstance);
    }

    vm.goBack = function() {

      $state.go('app.inbound.RevceivePo.GRN');
    }

    vm.gen_barcode = function() {
      vm.barcode_title = 'Barcode Generation';
      vm.model_data['barcodes'] = [];

      angular.forEach(vm.model_data.data, function(barcode_data){
        var quant = barcode_data[0].po_quantity;
        var sku_det = barcode_data[0].wms_code;
        /*var list_of_sku = barcode_data[0].serial_number.split(',');
        angular.forEach(list_of_sku, function(serial) {
          console.log(vm.sku_det);
          var serial_number = vm.sku_det+'/00'+serial;
          vm.model_data['barcodes'].push({'sku_code': serial_number, 'quantity': 1})
        })*/
       vm.model_data['barcodes'].push({'sku_code': sku_det, 'quantity': quant})

      })

      vm.model_data['format_types'] = [];
      var key_obj = {};//{'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details', 'Bulk Barcode': 'Details'};
      vm.service.apiCall('get_format_types/').then(function(data){
        $.each(data['data']['data'], function(ke, val){
          vm.model_data['format_types'].push(ke);
          });
          key_obj = data['data']['data'];
      });

      vm.model_data.have_data = true;
      //$state.go('app.inbound.RevceivePo.barcode');
      var modalInstance = $modal.open({
        templateUrl: 'views/outbound/toggle/barcodes.html',
        controller: 'Barcodes',
        controllerAs: 'pop',
        size: 'lg',
        backdrop: 'static',
        keyboard: false,
        windowClass: 'z-2021',
        resolve: {
          items: function () {
            return vm.model_data;
          }
        }
      });

      modalInstance.result.then(function (selectedItem) {
        console.log(selectedItem);
      }); 
    }
}

/*stockone.directive('dtPoData', function() {
  return {
    restrict: 'E',
    scope: {
      po_data: '=data',
      preview: '=preview'
    },
    templateUrl: 'views/inbound/toggle/po_data_html.html',
    link: function(scope, element, attributes, $http){
      console.log(scope);
    }
  };
});
*/
})();