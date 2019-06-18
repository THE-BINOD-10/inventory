FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('MarketEnqTbl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.display = true;
    vm.extended_date = '';
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
    vm.filters = {'datatable': 'MarketEnqTbl', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': ''};
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
    vm.dtColumns = [
      DTColumnBuilder.newColumn('Enquiry ID').withTitle('Enquiry ID'),
      DTColumnBuilder.newColumn('Date').withTitle('Date'),
      DTColumnBuilder.newColumn('Quantity').withTitle('Quantity').notSortable(),
      DTColumnBuilder.newColumn('Amount').withTitle('Amount').notSortable(),
      DTColumnBuilder.newColumn('Days Left').withTitle('Days Left').notSortable(),
      DTColumnBuilder.newColumn('Corporate Name').withTitle('Corporate Name'),
      DTColumnBuilder.newColumn('Extend Date').withTitle('Extend Date').notSortable(),
      // DTColumnBuilder.newColumn('Input Div').withTitle('Extend Date').notSortable(),
      DTColumnBuilder.newColumn('Move to Cart').withTitle('Move to Cart').notSortable(),
    ];
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
        $('td:not(td:last)', nRow).unbind('click');
        $('td:not(td:last)', nRow).bind('click', function() {
            $scope.$apply(function() {
              console.log("markets")
                vm.service.apiCall('get_customer_enquiry_detail/', 'GET', {enquiry_id: aData['Enquiry ID']}).then(function(data){
                  if(data.message) {
                    angular.copy(data.data, vm.model_data);
                    vm.title = "Market Enquiry";
                    $state.go('user.App.MyOrders.OrderDetails');
                  }
                });
            });
        });
        $('td:last', nRow).prev().unbind('click');
        return nRow;
    }
    vm.extend_order_date = function(order){
      $('#'+order+"_extdate").addClass('hide')
      $('#'+order+"_save").removeClass('hide')
    }
    vm.confirm_to_extend = function(order){
      var send = []
      $('#'+order+"_save").addClass('hide')
      $('#'+order+"_extdate").removeClass('hide')
      if (this.extended_date) {
        send.push({'name':'extended_date', 'value':this.extended_date})
        send.push({'name':'order_id', 'value':order})
        Service.apiCall('extend_enquiry_date/', 'GET', send).then(function(data) {
          if (data.message) {
            if (data.data == 'Success') {
              vm.dtInstance.reloadData();
              Service.showNoty('Your request sent, pleae wait warehouse conformation');
            }
          } else {
            Service.showNoty('Something went wrong');
          }
        });
      } else {
        Service.showNoty('Please fill with extend date');
      }
    }
    vm.close = function() {

    //  angular.copy(empty_data, vm.model_data);
      $state.go('user.App.MyOrders')
    }
    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    vm.print_pdf_my_orders_swiss = function(){
      // vm.model_data['market_enquiry'] = true;
      vm.service.apiCall("print_pdf_my_orders_swiss/", "POST", {"data":JSON.stringify(vm.model_data)}).then(function(data){
        if(data){
          vm.service.print_data(data.data, '');
        }
      })
    }
}

})();
