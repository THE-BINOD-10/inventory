'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PendingMonthlyPutawayCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service',  '$q', 'Data', '$modal', '$log', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, Data, $modal, $log) {
var vm = this;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.filters = {'datatable': 'PendingMonthlyPutaway', 'search0':'', 'search1':'', 'search2': '', 'search3': ''}
    vm.model_data = {};
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
       .withOption('rowCallback', rowCallback);
       vm.dtColumns = [
          DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
          .renderWith(function(data, type, full, meta) {
              if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                vm.selected = {};
              }
              vm.selected[meta.row] = vm.selectAll;
              return vm.service.frontHtml + meta.row + vm.service.endHtml;
          }).notSortable(),
          DTColumnBuilder.newColumn('source_label').withTitle('GRN user'),
          DTColumnBuilder.newColumn('warehouse_label').withTitle('Plant Name'),
          DTColumnBuilder.newColumn('GRN Number').withTitle('GRN Number'),
          // DTColumnBuilder.newColumn('Order Quantity').withTitle('Order Quantity'),
          DTColumnBuilder.newColumn('Creation Date').withTitle('Confirmation Date&Time'),
        ];
    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {

    vm.ord_status = '';

    $('td:not(td:first)', nRow).unbind('click');
    $('td:not(td:first)', nRow).bind('click', function() {
      console.log('ok');
       //  $scope.$apply(function() {
       //    var data = {order_id: aData['Material Request ID'], warehouse_name: aData['Warehouse Name'], source_wh: aData['Source Name']};
       //    vm.model_data['material_id'] = aData['Material Request ID'];
       //    vm.model_data['source_plant'] = aData['source_label'];
       //    vm.model_data['destination_dept'] = aData['warehouse_label'];
       //    vm.model_data['order_date'] = aData['Creation Date'];
       //    vm.service.apiCall("view_pending_mr_details/","POST", data).then(function(datum) {
       //      if (datum.message) {
       //        $state.go("app.inbound.MaterialRequest.DetailMR");
       //        vm.model_data['records'] = datum.data;
       //      } else{
       //        vm.service.showNoty("Please Contact To Stockone Team !! ")
       //      }
       //    })
       // })
     })
   }
    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    function reloadData () {
      vm.bt_disable = true;
      vm.dtInstance.reloadData();
    };

    vm.close = function() {
      $state.go("app.inbound.PutAwayConfirmation");
      vm.model_data = {};
    }

    vm.confirm_grns = function() {
      vm.bt_disable = true;
      var selected_order_ids = []
      var selected_rows = []
      var valid = true
      for (var key in vm.selected) {
        if (vm.selected[key]) {
          var row_data = vm.dtInstance.DataTable.context[0].aoData[key]._aData
          var order_id = row_data ['GRN Number']
          var dest_dept = row_data ['Warehouse Name']
          var source_wh = row_data ['Source Name']
          // if (selected_order_ids.length == 1){
          //   valid = false
          // }
          // if (valid) {
          selected_order_ids.push(order_id)
          var elem = {}
          elem = { 'order_id' :order_id , 'dest_dept': dest_dept, 'source_wh': source_wh }
          selected_rows.push(elem)
          // }
        }
      }
      if (valid) {
        vm.service.apiCall('confirm_pending_grn_monthly_request/', 'POST', {'selected_orders': JSON.stringify(selected_rows)}).then(function(resp) {
          if(resp.data == "success") {
            vm.service.showNoty("Success")
            vm.dtInstance.reloadData();
          } else {
            vm.service.showNoty(resp.data);
            vm.dtInstance.reloadData();
          }
        })
      } else {
        vm.dtInstance.reloadData();
        vm.service.showNoty("Please Select Single Order");
      }
    }
}
