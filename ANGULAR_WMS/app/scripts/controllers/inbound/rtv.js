FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('RTVCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.date = new Date();

    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.datatable = 'ReturnToVendor';

    vm.filters = {'datatable': vm.datatable, 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': ''
                  , 'search5': '', 'search6': '', 'search7': ''};
    
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

    vm.dtColumns = [
        DTColumnBuilder.newColumn('Supplier ID').withTitle('Supplier ID'),
        DTColumnBuilder.newColumn('Supplier Name').withTitle('Supplier Name'),
        DTColumnBuilder.newColumn('PO Number').withTitle('PO Number'),
        DTColumnBuilder.newColumn('PO Date').withTitle('PO Date'),
        DTColumnBuilder.newColumn('Invoice Number').withTitle('Invoice Number'),
        DTColumnBuilder.newColumn('Invoice Date').withTitle('Invoice Date'),
        DTColumnBuilder.newColumn('Total Quantity').withTitle('Total Quantity'),
        DTColumnBuilder.newColumn('Total Amount').withTitle('Total Amount'),
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

    // function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
    //     $(row_click_bind, nRow).unbind('click');
    //     $(row_click_bind, nRow).bind('click', function() {
    //         $scope.$apply(function() {
    //             vm.service.apiCall('get_rtv_data/', 'GET', {supplier_id: aData['DT_RowId']}).then(function(data){
    //               if(data.message) {
    //                 vm.serial_numbers = [];
    //                 angular.copy(data.data, vm.model_data);
    //                 vm.title = "Return to Vendor";
    //                 $state.go('app.inbound.rtv.details');
    //               }
    //             });
    //         });
    //     });
    //     return nRow;
    // }

    vm.reloadData = function () {
      $('.custom-table').DataTable().draw();
    };

    vm.filter_enable = true;
    vm.print_enable = false;
    vm.update = false;
    // vm.model_data = {'sku_code':'','supplier_id':'','from_date':new Date(),'to_date':'','po_number':'','invoice_number':'',};
    vm.dis = true;

    vm.close = close;
    function close() {

      vm.model_data = {};
      $state.go('app.inbound.rtv');
    }

    vm.create_rtv = function(){
      // $state.go('app.inbound.rtv.details');
      // vm.title = "Generate RTV";
      vm.service.apiCall('get_rtv_data/', 'GET', {selected_items: vm.selected}).then(function(data){
        if(data.message) {
          vm.serial_numbers = [];
          angular.copy(data.data, vm.model_data);
            vm.title = "Generate RTV";
            $state.go('app.inbound.rtv.details');
        }
      });
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

})();