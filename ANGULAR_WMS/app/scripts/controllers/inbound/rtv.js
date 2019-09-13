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
    // vm.date = new Date();
    vm.extra_width = {width:'1100px'};

    function getOS() {
      var userAgent = window.navigator.userAgent,
          platform = window.navigator.platform,
          macosPlatforms = ['Macintosh', 'MacIntel', 'MacPPC', 'Mac68K'],
          windowsPlatforms = ['Win32', 'Win64', 'Windows', 'WinCE'],
          iosPlatforms = ['iPhone', 'iPad', 'iPod'],
          os = null;

      if (macosPlatforms.indexOf(platform) !== -1) {
        os = 'Mac OS';
      } else if (iosPlatforms.indexOf(platform) !== -1) {
        os = 'iOS';
      } else if (windowsPlatforms.indexOf(platform) !== -1) {
        os = 'Windows';
      } else if (/Android/.test(userAgent)) {
        os = 'Android';
      } else if (!os && /Linux/.test(platform)) {
        os = 'Linux';
      }

      return os;
    }

    vm.date_format_convert = function(utc_date){

      var os_type = getOS();

      var date = utc_date.toLocaleDateString();
      var datearray = date.split("/");

      if (os_type == 'Windows') {

        if (datearray[1] < 10 && datearray[1].length == 1) {
          datearray[1] = '0'+datearray[1];
        }

        if (datearray[0] < 10 && datearray[0].length == 1) {
          datearray[0] = '0'+datearray[0];
        }

        vm.date = datearray[0] + '/' + datearray[1] + '/' + datearray[2];
      } else {

        vm.date = datearray[1] + '/' + datearray[0] + '/' + datearray[2];
      }
    }

    vm.date_format_convert(new Date());
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.conf_disable = false;
    vm.datatable = Data.datatable;
    // vm.datatable = 'ReturnToVendor';
    vm.user_type = Session.user_profile.user_type;

    vm.filters = {'datatable': 'ReturnToVendor', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': ''
                  , 'search5': '', 'search6': '', 'search7': '', 'from_date': vm.date};

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
        DTColumnBuilder.newColumn('Challan Number').withTitle('Challan Number'),
        DTColumnBuilder.newColumn('Invoice Date').withTitle('Invoice Date'),
        DTColumnBuilder.newColumn('Challan Date').withTitle('Challan Date'),
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
      vm.reloadData();
      vm.empty_filter_fields();
      vm.date_format_convert(new Date());
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
              vm.title = "Create RTV";
              vm.print_enable = false;
              $state.go('app.inbound.rtv.details');
          }
        });
      }
    }

    vm.reset_filters = function(){

      vm.model_data['filters'] = {};
      vm.model_data.filters['from_date'] = vm.date;
      vm.model_data.filters['datatable'] = 'ReturnToVendor';
    }

    vm.empty_filter_fields = function(){


      if (Data.rtv_filters) {

        vm.model_data['filters'] = Data.rtv_filters;
      } else {

        vm.model_data['filters'] = {};
        vm.model_data.filters['sku_code'] = '';
        vm.model_data.filters['supplier_id'] = '';
        vm.model_data.filters['from_date'] = vm.date;
        vm.model_data.filters['to_date'] = '';
        vm.model_data.filters['open_po'] = '';
        vm.model_data.filters['invoice_number'] = '';
        vm.model_data.filters['datatable'] = 'ReturnToVendor';
      }
    }

    vm.saveFilters = function(filters){
      Data.rtv_filters = filters;
      vm.enable_dc_return = filters.enable_dc_returns;
    }

    //RTV Pop Data
    vm.rtv_details = {supplier_id:'Supplier ID', supplier_name:'Supplier Name',
                      invoice_number:'Invoice Number', invoice_date:'Invoice Date'};
    vm.rtv_details_keys = Object.keys(vm.rtv_details);

    vm.update_data = update_data;
    function update_data(index, data) {
        if (index == data.length-1) {
          if (data[index].return_qty) {
            var total_qty = 0;

            angular.forEach(data, function(row){
              total_qty += Number(row.return_qty) ;
            });

            if (total_qty < Number(data[index].quantity)) {
              var new_dic = {};
              data[index].rest_qty = Number(data[index].quantity) - total_qty;
              angular.copy(data[index], new_dic);
              new_dic.location = '';
              new_dic.return_qty='';
              data.push(new_dic);
            } else {
              Service.showNoty("You don't have quantity to enter");
            }
          } else {
            Service.showNoty("Please enter returning quantity");
          }
        } else {
          data.splice(index,1);
        }
    }

    vm.check_quantity = function(index, data, sku){
      vm.total_qty = 0;
      vm.rest_qty = 0;
      sku.rest_qty = 0;
      vm.totol_qty_check(data);

      if (Number(vm.total_qty) > Number(sku.quantity) && !sku.rest_qty) {
        vm.check_rest_qty(sku, data);
        sku.return_qty = vm.rest_qty;
        Service.showNoty("You can enter "+sku.return_qty+" quantity");

        sku.rest_qty = 0;
      } else if (Number(vm.total_qty) > Number(sku.quantity) && sku.rest_qty) {
        vm.check_rest_qty(sku, data);
        sku.return_qty = vm.rest_qty;
        Service.showNoty("You can enter "+sku.return_qty+" quantity");
        sku.rest_qty = 0;
      } else {
        if (index && sku.return_qty > data[index-1].rest_qty) {
          Service.showNoty("You can enter "+sku.return_qty+" quantity");
          sku.rest_qty = 0;
        } else {
          sku.rest_qty = Number(sku.quantity) - Number(vm.total_qty);
        }
      }

    }

    vm.check_rest_qty = function(sku, data){
      var total_qty = 0;
      for (var i = 0; i < data.length; i++) {
        total_qty += Number(data[i].return_qty);
      }

      if(total_qty > sku.quantity){
          total_qty = total_qty - sku.return_qty;
          sku.return_qty = sku.quantity - total_qty;
      }

      vm.rest_qty = sku.quantity - total_qty;
    }

    vm.totol_qty_check = function(data){
      angular.forEach(data, function(row){
        if (!row.return_qty) {
          row.return_qty = '';
        }
        vm.total_qty += Number(row.return_qty);
      });

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

    vm.save = save;
    function save(form) {
      vm.conf_disable = true;
      var elem = [];
      elem.push({'name': 'seller_id', 'value': vm.model_data.seller_details.seller_id});
      elem.push({'name': 'enable_dc_returns', 'value': vm.enable_dc_return});
      elem.push({'name': 'rtv_reasons', 'value': vm.model_data.rtv_reasons});

      angular.forEach(vm.model_data.data, function(row){
        angular.forEach(row, function(sku){
          elem.push({'name': 'sku_code', 'value': sku.sku_code});
          elem.push({'name': 'order_id', 'value': sku.order_id});
          elem.push({'name': 'price', 'value': sku.price});
          elem.push({'name': 'quantity', 'value': sku.quantity});
          elem.push({'name': 'amount', 'value': sku.amount});
          elem.push({'name': 'sku_desc', 'value': sku.sku_desc});
          elem.push({'name': 'summary_id', 'value': sku.summary_id});
          elem.push({'name': 'tax_percent', 'value': sku.tax_percent});
          elem.push({'name': 'tax_value', 'value': sku.tax_value});
          elem.push({'name': 'location', 'value': sku.location});
          elem.push({'name': 'return_qty', 'value': sku.return_qty});
          elem.push({'name': 'batch_no', 'value': sku.batch_no});
          elem.push({'name': 'mrp', 'value': sku.mrp});
        });
      });

      vm.service.apiCall('save_rtv/', 'POST', elem, true).then(function(data){
        if(data.message) {
          if(data.data == 'Saved Successfully') {

            vm.close();
            vm.service.refresh(vm.dtInstance);
          }  else {
            pop_msg(data.data)
          }
        } else {
          pop_msg(data.data)
        }
        vm.conf_disable = false;
      });
    }

    vm.submit = submit;
    function submit(form) {
      vm.conf_disable = true;
      var elem = [];
      elem.push({'name': 'seller_id', 'value': vm.model_data.seller_details.seller_id});
      elem.push({'name': 'enable_dc_returns', 'value': vm.enable_dc_return});
      elem.push({'name': 'rtv_reasons', 'value': vm.model_data.rtv_reasons});

      angular.forEach(vm.model_data.data, function(row){
        angular.forEach(row, function(sku){
          elem.push({'name': 'sku_code', 'value': sku.sku_code});
          elem.push({'name': 'order_id', 'value': sku.order_id});
          elem.push({'name': 'price', 'value': sku.price});
          elem.push({'name': 'quantity', 'value': sku.quantity});
          elem.push({'name': 'amount', 'value': sku.amount});
          elem.push({'name': 'sku_desc', 'value': sku.sku_desc});
          elem.push({'name': 'summary_id', 'value': sku.summary_id});
          elem.push({'name': 'tax_percent', 'value': sku.tax_percent});
          elem.push({'name': 'tax_value', 'value': sku.tax_value});
          elem.push({'name': 'location', 'value': sku.location});
          elem.push({'name': 'return_qty', 'value': sku.return_qty});
          elem.push({'name': 'batch_no', 'value': sku.batch_no});
          elem.push({'name': 'mrp', 'value': sku.mrp});
        });
      });

      vm.service.apiCall('create_rtv/', 'POST', elem, true).then(function(data){
        if(data.message) {
          if(data.data == 'Success') {

            vm.close();
            vm.service.refresh(vm.dtInstance);
          } else {
            if(data.data.search("<div") != -1) {
              vm.title = "Debit Note";
              vm.extra_width = {}
              vm.html = $(data.data);
              vm.extra_width = {}
              angular.element(".modal-body").html($(data.data));
              vm.print_enable = true;
              vm.service.refresh(vm.dtInstance);
            } else {
              pop_msg(data.data)
            }
          }
        }
        vm.conf_disable = false;
      });
    }

    vm.print_rtv = function() {
      vm.service.print_data(vm.html, "Debit Note");
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
}

})();
