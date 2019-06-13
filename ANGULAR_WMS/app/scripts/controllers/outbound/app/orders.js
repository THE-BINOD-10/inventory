FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('MyOrdersTbl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.user_type = vm.permissions.user_type;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.display = true;

    //default values
    if(!vm.permissions.grn_scan_option) {
      vm.permissions.grn_scan_option = "sku_serial_scan";
    }
    if(!vm.permissions.barcode_generate_opt) {
      vm.permissions.barcode_generate_opt = 'sku_code';
    }
    if(vm.permissions.barcode_generate_opt == 'sku_ean') {
      vm.permissions.barcode_generate_opt = 'sku_code';
    }

    //process type;
    vm.po_qc = true;
    vm.po_qc = (vm.permissions.receive_process == "receipt-qc")? true: false;
    vm.g_data = Data.receive_po;

    var sort_no = (vm.g_data.style_view)? 1: 0;
    vm.filters = {'datatable': 'MyOrdersTbl', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': '', 'search5': '',
                  'search6': ''};
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
       .withOption('order', [sort_no, 'desc'])
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
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    //var columns = ['Order ID',, ];
    //vm.dtColumns = vm.service.build_colums(columns);
    vm.dtColumns = [
      DTColumnBuilder.newColumn('Order ID').withTitle('Order ID'),
      DTColumnBuilder.newColumn('Ordered Qty').withTitle('Ordered Qty').notSortable(),
      DTColumnBuilder.newColumn('Delivered Qty').withTitle('Delivered Qty').notSortable(),
      DTColumnBuilder.newColumn('Pending Qty').withTitle('Pending Qty').notSortable(),
      DTColumnBuilder.newColumn('Order Value').withTitle('Order Value').notSortable(),
      DTColumnBuilder.newColumn('Order Date').withTitle('Order Date'),
      DTColumnBuilder.newColumn('Receive Status').withTitle('Receive Status').notSortable(),
    ];
    //var empty_data = {Order ID:"",Ordered Qty :"", Delivered Qty:"", Pending Qty:"", Order Value:"", Order Date:"", Receive Status:""};
     vm.model_data = {};
    var row_click_bind = 'td';
    /*if(vm.g_data.style_view) {
      var toggle = DTColumnBuilder.newColumn('PO No').withTitle(' ').notSortable()
                 .withOption('width', '25px').renderWith(function(data, type, full, meta) {
                   return "<i ng-click='showCase.addRowData($event, "+JSON.stringify(full)+")' class='fa fa-plus-square'></i>";
                 })
      row_click_bind = 'td:not(td:first)';
    } else {

      var toggle = DTColumnBuilder.newColumn('PO No').withTitle(' ').notSortable().notVisible();
    }
    vm.dtColumns.unshift(toggle);*/
    vm.dtInstance = {};
    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $(row_click_bind, nRow).unbind('click');
        $(row_click_bind, nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.service.apiCall('get_customer_order_detail/', 'GET', {order_id: aData['Order ID']}).then(function(data){
                  if(data.message) {
                    angular.copy(data.data, vm.model_data);
                    //console.log(data.data)
                    vm.title = "My Orders";
                    $state.go('user.App.MyOrders.OrderDetails');
                  }
                });
            });
        });
        return nRow;
    }
    vm.close = function() {

    //  angular.copy(empty_data, vm.model_data);
      $state.go('user.App.MyOrders')
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
    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }


    vm.html = "";
    vm.confirm_grn = function(form) {
      // var data = [];
      // data.push({name: 'batch_no', value: form.batch_no.$viewValue});
      // data.push({name: 'mrp', value: form.mrp.$viewValue});
      // data.push({name: 'manf_date', value: form.manf_date.$viewValue});
      // data.push({name: 'exp_date', value: form.exp_date.$viewValue});
      // data.push({name: 'po_unit', value: form.po_unit.$viewValue});
      // data.push({name: 'tax_per', value: form.tax_per.$viewValue});

     if(check_receive()){
      var that = vm;
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      var url = "confirm_grn/"
      if(vm.po_qc) {
        url = "confirm_receive_qc/"
      }
      vm.service.apiCall(url, 'POST', elem, true).then(function(data){
        if(data.message) {
          if(data.data.search("<div") != -1) {
            vm.extra_width = {}
            vm.html = $(data.data);
            vm.extra_width = {}
            //var html = $(vm.html).closest("form").clone();
            //angular.element(".modal-body").html($(html).find(".modal-body"));
            angular.element(".modal-body").html($(data.data));
            vm.print_enable = true;
            vm.service.refresh(vm.dtInstance);
            if(vm.permissions.use_imei) {
              fb.generate = true;
              fb.remove_po(fb.poData["id"]);
            }
          } else {
            pop_msg(data.data)
          }
        }
      });
     }
    }

    vm.print_pdf_my_orders_swiss = function(){
      vm.service.apiCall("print_pdf_my_orders_swiss/", "POST", {"data":JSON.stringify(vm.model_data)}).then(function(data){
        if(data){
          vm.service.print_data(data.data, '');
        }
      })
    }

}

stockone.directive('dtPoData', function() {
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

})();
