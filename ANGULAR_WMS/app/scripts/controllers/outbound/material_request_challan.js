'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('MaterialRequestChallanCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'SweetAlert', 'colFilters', 'Service', 'Data', '$modal', '$log', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, SweetAlert, colFilters, Service, Data, $modal, $log) {
var vm = this;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.filters = {'datatable': 'MaterialRequestChallan', 'search0':'', 'search1':'', 'search2': '', 'search3': ''}
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
    // MATERIAL_REQUEST_CHALLAN_HEADERS = ['Material Request ID', 'Destination Department', 'Order Quantity', 'Picked Quantity', 'Material Request Date&Time']
    vm.dtColumns = [
        DTColumnBuilder.newColumn('Material Request ID').withTitle('Material Request ID'),
        DTColumnBuilder.newColumn('pick_number').withTitle('Pick Receipt Number'),
        DTColumnBuilder.newColumn('Destination Department').withTitle('Destination Department'),
        DTColumnBuilder.newColumn('Order Quantity').withTitle('Order Quantity'),
        DTColumnBuilder.newColumn('Picked Quantity').withTitle('Picked Quantity'),
        DTColumnBuilder.newColumn('Material Request Date&Time').withTitle('Material Request Date&Time'),
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
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    var empty_data = {"order_id": "", "sku_class": ""}
    vm.model_data = {};
    angular.copy(empty_data, vm.model_data);




    vm.close = close;
    function close() {
      vm.model_data = {};
      vm.display_style_stock_table = false;
      vm.sku_level_qtys = [];
      $state.go('app.outbound.CustomerInvoicesMain');
    }

    vm.generat_dc = function() {
      var selected_order_ids = []
      var selected_rows = []
      var valid = true
      for (var key in vm.selected) {
        if (vm.selected[key]) {
          var row_data = vm.dtInstance.DataTable.context[0].aoData[key]._aData
          var order_id = row_data ['Material Request ID']
          var pick_id = row_data ['pick_number']
          if (selected_order_ids.length == 1)
           {
               valid = false
           }
          if(valid)
          {
            selected_order_ids.push(order_id)
            var elem = {}
            elem = {'order_id' :order_id , 'pick_number': pick_id}
            selected_rows.push(elem)

          }

        }
      }
      if (valid) {
        vm.service.apiCall('generate_mr_dc/', 'POST', {'selected_orders': JSON.stringify(selected_rows)}).then(function(resp) {
          if(resp.message) {
            vm.pdf_data = resp.data;
            $state.go("app.outbound.CustomerInvoicesMain.dc");
            $timeout(function () {
              $(".modal-body:visible").html(vm.pdf_data)
            }, 1000);
          }
          vm.bt_disable = false;
        })
      }
      else
      {
        vm.service.showNoty("Please Select Single Order")
      }
    }


}
