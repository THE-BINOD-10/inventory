'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PendingMaterialRequestCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'SweetAlert', 'colFilters', 'Service', 'Data', '$modal', '$log', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, SweetAlert, colFilters, Service, Data, $modal, $log) {
var vm = this;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.filters = {'datatable': 'PendingMaterialRequest', 'search0':'', 'search1':'', 'search2': '', 'search3': ''}
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
       .withOption('order', [1, 'desc'])
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
          //vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
        });
    vm.dtColumns = [
        DTColumnBuilder.newColumn('source_label').withTitle('Source Plant'),
        DTColumnBuilder.newColumn('warehouse_label').withTitle('Destination Department'),
        DTColumnBuilder.newColumn('Material Request ID').withTitle('Material Request ID'),
        // DTColumnBuilder.newColumn('Order Quantity').withTitle('Order Quantity'),
        DTColumnBuilder.newColumn('Creation Date').withTitle('Confirmation Date&Time'),
    ];
    var row_click_bind = 'td';
    vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
      .renderWith(function(data, type, full, meta) {
      if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
        vm.selected = {};
      }
      vm.selected[meta.row] = vm.selectAll;
      return vm.service.frontHtml + meta.row + vm.service.endHtml;
    }))
    row_click_bind = 'td:not(td:first)';
    vm.dtInstance = {};
    vm.reloadData = reloadData;

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }
    
    function reloadData () {
        vm.dtInstance.reloadData();
    };

    var empty_data = {"order_id": ""}
    vm.model_data = {};
    angular.copy(empty_data, vm.model_data);

    vm.confirm_mr = function() {
      var selected_order_ids = []
      var selected_rows = []
      var valid = true
      for (var key in vm.selected) {
        if (vm.selected[key]) {
          var row_data = vm.dtInstance.DataTable.context[0].aoData[key]._aData
          var order_id = row_data ['Material Request ID']
          var dest_dept = row_data ['Warehouse Name']
          var source_wh = row_data ['Source Name']
          if (selected_order_ids.length == 1)
           {
               valid = false
           }
          if(valid)
          {
            selected_order_ids.push(order_id)
            var elem = {}
            elem = {'order_id' :order_id , 'dest_dept': dest_dept, 'source_wh': source_wh}
            selected_rows.push(elem)

          }
        }
      }
      if (valid) {
        vm.service.apiCall('confirm_mr_request/', 'POST', {'selected_orders': JSON.stringify(selected_rows)}).then(function(resp) {
          if(resp.data == "success") {
            vm.service.showNoty("Success")
            vm.dtInstance.reloadData();
          } else {
            vm.service.showNoty("Failed !!")
            vm.dtInstance.reloadData();
          }
          vm.bt_disable = false;
        })
      }
      else {
        vm.service.showNoty("Please Select Single Order")
      }
    }
}
