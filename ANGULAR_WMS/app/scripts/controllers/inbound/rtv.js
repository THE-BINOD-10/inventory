FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('RTVCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.industry_type = Session.user_profile.industry_type;
    vm.date = new Date();
    vm.extra_width = {width:'1100px'};

    vm.date_format_convert = function(utc_date){
      var date = utc_date.toLocaleDateString();
      var datearray = date.split("/");
      vm.date = datearray[1] + '/' + datearray[0] + '/' + datearray[2];
    }

    vm.date_format_convert(vm.date);
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.datatable = Data.datatable;
    vm.user_type = Session.user_profile.user_type;

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

    vm.reloadData = function () {
      $('.custom-table').DataTable().draw();
    };

    vm.filter_enable = true;
    vm.print_enable = false;
    vm.update = false;
    vm.dis = true;

    vm.close = close;
    function close() {
      $state.go('app.inbound.rtv');
    }

    vm.create_rtv = function(){
      var flag = false;
      var id = '';
      angular.forEach(vm.selected, function(value, key){
        if (value && !flag) {
          flag = true;
          id = vm.dtInstance.DataTable.context[0].aoData[key]._aData.data_id;
        } else if (value && flag) {
          Service.showNoty('You can select one sku at a time');
          flag = false;
          return false;
        }
      });

      if (flag) {

        vm.service.apiCall('get_po_putaway_summary/', 'GET', {data_id: id}).then(function(data){
          if(data.message) {
            angular.copy(data.data, vm.model_data);
              vm.title = "Generate RTV";
              $state.go('app.inbound.rtv.details');
          }
        });
      }
    }

    //RTV Pop Data
    vm.rtv_details = {supplier_id:'Supplier ID', supplier_name:'Supplier Name', 
                      invoice_number:'Invoice Number', invoice_date:'Invoice Date'};
    vm.rtv_details_keys = Object.keys(vm.rtv_details);

    vm.update_data = update_data;
    function update_data(index, data) {
      // if (Session.roles.permissions['pallet_switch'] || vm.industry_type == 'FMCG') {
        if (index == data.length-1) {
          var total_qty = 0;

          angular.forEach(data, function(row){
            total_qty += row.return_qty ;
          });

          if (total_qty < data[index].quantity) {
            var new_dic = {};
            angular.copy(data[index], new_dic);
            new_dic.location = '';
            new_dic.return_qty='';
            data.push(new_dic);
          } else {
            Service.showNoty("You don't have quantity to enter");
          }
        } else {
          data.splice(index,1);
        }
      // }
    }

    vm.check_quantity = function(index, data){
      var total_qty = 0;
      angular.forEach(data, function(row){
        total_qty += Number(row.return_qty) ;
      });

      if (total_qty > data[index].quantity) {
        data[index].return_qty = data[index].quantity - total_qty;

        Service.showNoty("You can enter only "+(data[index].quantity - total_qty)+" quantity");
      }
    }
    
    vm.new_sku = false
    vm.add_wms_code = add_wms_code;
    function add_wms_code() {
      if (vm.industry_type == 'FMCG') {
        vm.model_data.data.push([{"wms_code":"", "sku_desc":"", "received_quantity":"", "batch_no":"", "mrp": '',
                                "location": '', is_new: true, "return_qty": ""}]);
      } else {
        vm.model_data.data.push([{"wms_code":"", "sku_desc":"", "received_quantity":"", "location": '', 
                                  is_new: true, "return_qty": ""}]);
      }
    }

    vm.get_sku_details = function(data, selected) {

      data.sku_details[0].fields.load_unit_handle = selected.load_unit_handle;
      data.wms_code = selected.wms_code;
      $timeout(function() {$scope.$apply();}, 1000);
    }

    vm.submit = submit;
    function submit(form) {
      var elem = [];
      elem.push({'name': 'seller_id', 'value': vm.model_data.seller_details.seller_id});

      angular.forEach(vm.model_data.data, function(row){
        elem.push({'name': 'sku_code', 'value': row.sku_code});
        elem.push({'name': 'order_id', 'value': row.order_id});
        elem.push({'name': 'price', 'value': row.price});
        elem.push({'name': 'quantity', 'value': row.quantity});
        elem.push({'name': 'amount', 'value': row.amount});
        elem.push({'name': 'sku_desc', 'value': row.sku_desc});
        elem.push({'name': 'summary_id', 'value': row.summary_id});
        elem.push({'name': 'tax_percent', 'value': row.tax_percent});
        elem.push({'name': 'tax_value', 'value': row.tax_value});
        elem.push({'name': 'location', 'value': row.location});
        elem.push({'name': 'return_qty', 'value': row.return_qty});
        elem.push({'name': 'batch_no', 'value': row.batch_no});
        elem.push({'name': 'mrp', 'value': row.mrp});
      });

      vm.service.apiCall('create_rtv/', 'POST', elem, true).then(function(data){
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