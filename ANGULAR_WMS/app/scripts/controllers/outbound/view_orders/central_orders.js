'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CentralOrders',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'SweetAlert', 'colFilters', 'Service', 'Data', '$modal', '$log', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, SweetAlert, colFilters, Service, Data, $modal, $log) {
var vm = this;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.warehouse_type = Session.user_profile.warehouse_type
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
        DTColumnBuilder.newColumn('Status').withTitle('Status'),
        DTColumnBuilder.newColumn('Order Date').withTitle('Order Date')
    ];
    if(vm.permissions.dispatch_qc_check) {
      vm.dtColumns.splice(1, 0, DTColumnBuilder.newColumn('Loan Proposal ID').withTitle('Main SR Number'))
    } else {
      vm.dtColumns.splice(1, 0, DTColumnBuilder.newColumn('Loan Proposal ID').withTitle('Loan Proposal ID'))
    }
    if(vm.permissions.dispatch_qc_check && vm.warehouse_type == 'CENTRAL_ADMIN') {
      vm.dtColumns.push(DTColumnBuilder.newColumn('Alternative Sku').withTitle('Alt Sku Code'))
    } else {
      vm.dtColumns.pop(DTColumnBuilder.newColumn('Alternative Sku').withTitle('Alt Sku Code'))
    }
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

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td:not(td:first)', nRow).unbind('click');
        $('td:not(td:first)', nRow).bind('click', function() {
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
                  vm.model_data.data = [{"sel_warehouse":"", "wh_available":"", "wh_quantity":""}];
                  $state.go('app.outbound.ViewOrders.CentralOrderDetails');
                });
                vm.sel_warehouse_obj = {};
                vm.temp_warehouse_obj = {};
                vm.sel_warehouse_flag = false;
            });
        });
        return nRow;
    }

    vm.status_dropdown = {0: 'Reject', 1: 'Accept',2: 'Pending'};


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
      angular.forEach(vm.model_data.data, function(row){
        if(row.wh_quantity){
          sum += parseInt(row.wh_quantity);
        }
      })
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
        if (vm.model_data.data.length) {
          angular.forEach(vm.model_data.data, function(record){
            if (vm.model_data.wh_level_stock_map[record.sel_warehouse]) {
              record.wh_available = vm.model_data.wh_level_stock_map[record.sel_warehouse].available;
              record.wh_quantity = 0;
            }
          })
        }
      });
    }

    vm.change_wh_quantity = function(key, quantity, actual_quantity, index) {
      var tot_filled = 0;
      vm.model_data.wh_level_stock_map[key].quantity = quantity;
      angular.forEach(vm.model_data.data, function(row){
        tot_filled += parseInt(row.wh_quantity);
      })
      if(tot_filled > actual_quantity){
        var remain = actual_quantity - (tot_filled - parseInt(quantity));
        vm.model_data.wh_level_stock_map[key].quantity = Math.min(remain, parseInt(vm.model_data.wh_level_stock_map[key].available));
        vm.model_data.data[index].wh_quantity = Math.min(remain, parseInt(vm.model_data.wh_level_stock_map[key].available));
        return
      }
      if(actual_quantity >= parseInt(vm.model_data.wh_level_stock_map[key].available)) {
        if(parseInt(vm.model_data.wh_level_stock_map[key].available) <= parseInt(quantity)){
          vm.model_data.wh_level_stock_map[key].quantity = vm.model_data.wh_level_stock_map[key].available;
          vm.model_data.data[index].wh_quantity = vm.model_data.wh_level_stock_map[key].available;
        }
      } else {
        if(parseInt(vm.model_data.wh_level_stock_map[key].available) <= parseInt(quantity)){
          vm.model_data.wh_level_stock_map[key].quantity = actual_quantity;
          vm.model_data.data[index].wh_quantity = actual_quantity;
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

    vm.update_data = update_data;
    function update_data(data, index) {
      vm.model_data.data.splice(index,1);
      if (Object.keys(vm.sel_warehouse_obj).length) {
        delete vm.sel_warehouse_obj[index];
        delete vm.temp_warehouse_obj[data.sel_warehouse];
        if (vm.model_data.data.length) {
          vm.model_data.warehouse = vm.model_data.data[vm.model_data.data.length-1].sel_warehouse;
        } else {
          vm.model_data.warehouse = "";
        }
      }
      if (!Object.keys(vm.sel_warehouse_obj).length) {
        vm.sel_warehouse_flag = false;
      }
    }

    vm.sel_warehouse_obj = {};
    vm.temp_warehouse_obj = {};
    vm.change_warehouse = function(data, index) {
      var flag = false;
      if (Object.keys(vm.sel_warehouse_obj).length) {
        if (vm.sel_warehouse_obj[index]) {
          data.wh_available = vm.model_data.wh_level_stock_map[data.sel_warehouse].available;
          delete vm.temp_warehouse_obj[vm.sel_warehouse_obj[index]]
          angular.forEach(vm.sel_warehouse_obj, function(value){
            if (data.sel_warehouse == value) {
              vm.service.showNoty("<b>"+data.sel_warehouse+"</b> warehouse already selected plese try with another");
              data.sel_warehouse = "";
              data.wh_available = "";
            }
          })
          vm.sel_warehouse_obj[index] = data.sel_warehouse;
          vm.temp_warehouse_obj[data.sel_warehouse] = data.sel_warehouse;
        } else {
          if (vm.temp_warehouse_obj[data.sel_warehouse]) {
            vm.service.showNoty("<b>"+data.sel_warehouse+"</b> warehouse already selected plese try with another");
            data.sel_warehouse = "";
            data.wh_available = "";
            delete vm.sel_warehouse_obj[index];
            delete vm.temp_warehouse_obj[data.sel_warehouse];
          } else if (!vm.temp_warehouse_obj[data.sel_warehouse]) {
            vm.sel_warehouse_obj[index] = data.sel_warehouse;
            vm.temp_warehouse_obj[data.sel_warehouse] = data.sel_warehouse;;
            data.wh_available = vm.model_data.wh_level_stock_map[data.sel_warehouse].available;
            vm.model_data.warehouse = vm.model_data.data[vm.model_data.data.length-1].sel_warehouse;
          }
        }
      } else {
        vm.sel_warehouse_obj[index] = data.sel_warehouse;
        vm.temp_warehouse_obj[data.sel_warehouse] = data.sel_warehouse;
        data.wh_available = vm.model_data.wh_level_stock_map[data.sel_warehouse].available;
        vm.model_data.warehouse = data.sel_warehouse;
        vm.sel_warehouse_flag = true;
      }
    }

    vm.add_warehouse = function(index=0, flag=true) {
      if (index==vm.model_data.data.length-1 && !flag || !index && flag) {
        if (flag) {
          vm.model_data.data.push({"sel_warehouse":"", "wh_available":"", "wh_quantity":""});
        } else {
          $scope.$apply(function() {
            vm.model_data.data.push({"sel_warehouse":"", "wh_available":"", "wh_quantity":""});
          });
        }
        if (vm.model_data.data.length-1) {
          vm.model_data.warehouse = vm.model_data.data[vm.model_data.data.length-1].sel_warehouse;
        }
      }
    }

    vm.delegate_order = function() {
      vm.delegate_order_data = []
      for (var key in vm.selected) {
        if (vm.selected[key]) {
          var delegate_row = vm.dtInstance.DataTable.context[0].aoData[key]._aData
          //var elem = {'warehouse': JSON.stringify(vm.model_data.wh_level_stock_map),
          //'status': status,'interm_det_id': data_id, 'shipment_date': shipment_date,
          //'alt_sku_code': alt_sku_code};
          var elem = {
            'status': delegate_row['Status'], 'interm_det_id': delegate_row['data_id'],
            'shipment_date': delegate_row['Shipment Date'], 'alt_sku_code': delegate_row['SKU Code']
          }
          if (delegate_row['Status'] != 'Accept') {
            vm.delegate_order_data.push(elem);
          }
        }
      }
      if (vm.delegate_order_data.length) {
        vm.service.apiCall('do_delegate_orders/', 'POST', {'delegate_order_data': JSON.stringify(vm.delegate_order_data)}).then(function(resp) {
          if (resp.message) {
            vm.reloadData()
            SweetAlert.swal({
              title: 'Delegated Orders',
              text: resp.data.output_msg,
              type: 'success',
              confirmButtonColor: '#33cc66',
              confirmButtonText: 'Ok',
              closeOnConfirm: true,
            })
          }
        })
      }
    }
}
