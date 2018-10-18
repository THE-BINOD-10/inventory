'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CentralOrders',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', 'Data', '$modal', '$log', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, Data, $modal, $log) {
var vm = this;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.display_style_stock_table = false;
    vm.sku_level_qtys = [];

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'CentralOrders'},
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
            /*if (angular.element(row)[dataIndex].children[6].outerHTML == "<td>1</td>") {
              angular.element(row)[dataIndex].children[6].outerHTML == "<td>Accepted</td>";
            } else if (angular.element(row)[dataIndex].children[6].outerHTML == "<td>0</td>") {
              angular.element(row)[dataIndex].children[6].outerHTML == "<td>Rejected</td>";
            }*/

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
        DTColumnBuilder.newColumn('Order ID').withTitle('Order ID'),
        DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('SKU Desc').withTitle('SKU Desc'),
        DTColumnBuilder.newColumn('Product Quantity').withTitle('Product Quantity'),
        DTColumnBuilder.newColumn('Shipment Date').withTitle('Shipment Date'),
        DTColumnBuilder.newColumn('Project Name').withTitle('Project Name'),
        DTColumnBuilder.newColumn('Remarks').withTitle('Remarks'),
        DTColumnBuilder.newColumn('Warehouse').withTitle('Warehouse'),
        DTColumnBuilder.newColumn('Status').withTitle('Status')
    ];

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    var empty_data = {"order_id": "", "sku_class": ""}
    vm.model_data = {};
    angular.copy(empty_data, vm.model_data);

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.service.apiCall('get_central_order_detail/', 'GET', {central_order_id: aData.data_id}).then(function(data){
                  var resp_data = data.data;
                  vm.model_data.order_id = resp_data.interm_order_id;
                  vm.model_data.sku_code = resp_data.sku_code;
                  vm.model_data.sku_desc = resp_data.sku_desc;
                  vm.model_data.alt_sku_code = resp_data.alt_sku_code;
                  vm.model_data.alt_sku_desc = resp_data.alt_sku_desc;
                  vm.model_data.warehouses = resp_data.warehouses;
                  vm.model_data.wh_level_stock_map = resp_data.wh_level_stock_map;
                  vm.model_data.already_assigned = resp_data.already_assigned;
                  vm.model_data.already_picked = resp_data.already_picked;
                  vm.model_data.status = resp_data.status;
                  vm.model_data.quantity = resp_data.quantity;
                  vm.model_data.data_id = resp_data.data_id;
                  vm.model_data.warehouse = resp_data.warehouse;
                  vm.model_data.shipment_date = resp_data.shipment_date;
                  vm.model_data.project_name = resp_data.project_name;
                  $state.go('app.outbound.ViewOrders.CentralOrderDetails');
                });
            });
        });
        return nRow;
    }

    vm.status_dropdown = {0: 'Reject', 1: 'Accept'};


    vm.close = close;
    function close() {
      vm.model_data = {};
      vm.display_style_stock_table = false;
      vm.sku_level_qtys = [];
      $state.go('app.outbound.ViewOrders');
    }

    function change_data(data) {
      angular.copy(data, vm.model_data);
      vm.model_data["sku_total_quantities"] = data.sku_total_quantities;
      console.log(data);
      angular.copy(vm.model_data.sku_total_quantities ,vm.remain_quantity);
      vm.count_sku_quantity();
    }

    vm.submit = submit;
    function submit(wh, status, data_id, shipment_date, alt_sku_code){

      var sum = 0;
      for( var item in vm.model_data.wh_level_stock_map){
          if(vm.model_data.wh_level_stock_map[item]['quantity']){
              sum += parseInt(vm.model_data.wh_level_stock_map[item]['quantity']);
          }
      }
      if(vm.model_data.quantity != sum){
          Service.showNoty('Filled quantity is not matching actual quantity');
          return
      }

      if (status) {

        var elem = {'warehouse': JSON.stringify(vm.model_data.wh_level_stock_map), 'status': status,
                    'interm_det_id': data_id, 'shipment_date': shipment_date, 'alt_sku_code': alt_sku_code};
        vm.service.apiCall('create_order_from_intermediate_order/', 'POST', elem, true).then(function(data){
          if(data.message) {
            if(data.data.indexOf('Success') != -1) {
              vm.service.refresh(vm.dtInstance);
              vm.close();
            } else {
              Service.showNoty(data.data);
              //vm.service.pop_msg(data.data);
            }
          }
        });
      } else {

        Service.showNoty('Please select status');
      }
    }


    vm.get_sku_details = function(product, item, index) {
      console.log(item);
      vm.model_data.alt_sku_code = item.wms_code;
      vm.model_data.alt_sku_desc = item.sku_desc;
      vm.service.apiCall('get_central_order_detail/', 'GET', {central_order_id: vm.model_data.data_id, alt_sku_code: vm.model_data.alt_sku_code}).then(function(data){
        var resp_data = data.data;
        vm.model_data.warehouses = resp_data.warehouses;
        vm.model_data.wh_level_stock_map = resp_data.wh_level_stock_map;
        //vm.model_data.warehouse = resp_data.warehouse;
      });
    }

    vm.change_wh_quantity = function(key, quantity, actual_quantity) {
      var tot_filled = 0;
      for(var dat in vm.model_data.wh_level_stock_map) {
        tot_filled += parseInt(vm.model_data.wh_level_stock_map[dat].quantity);
      }
      if(tot_filled > actual_quantity){
        var remain = actual_quantity - (tot_filled - parseInt(quantity));
        vm.model_data.wh_level_stock_map[key].quantity = Math.min(remain, parseInt(vm.model_data.wh_level_stock_map[key].available));
        return
      }
      if(actual_quantity >= parseInt(vm.model_data.wh_level_stock_map[key].available)) {
        if(parseInt(vm.model_data.wh_level_stock_map[key].available) <= parseInt(quantity)){
          vm.model_data.wh_level_stock_map[key].quantity = vm.model_data.wh_level_stock_map[key].available;
        }
      } else {
        if(parseInt(vm.model_data.wh_level_stock_map[key].available) <= parseInt(quantity)){
          vm.model_data.wh_level_stock_map[key].quantity = actual_quantity;
        }
      }
    }

    vm.get_sku_qty_details = function(product, item, index) {
      console.log(item);
      vm.service.apiCall('get_style_level_stock/', 'GET', {sku_class: item['sku_class'], warehouse: vm.model_data.warehouse}).then(function(data){
        var resp_data = data.data;
        vm.display_style_stock_table = true;
        angular.copy(resp_data, vm.sku_level_qtys);
      });
    }


}
