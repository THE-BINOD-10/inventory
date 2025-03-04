'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('InventoryAdjustmentCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.permissions = Session.roles.permissions;
    vm.pallet_switch = (vm.permissions.pallet_switch == true) ? true: false;
    vm.user_type = Session.user_profile.user_type;
    vm.industry_type = Session.user_profile.industry_type;
    vm.batch_nos = [];
    vm.batches = {};
    vm.weight_list = [];
    vm.weights = {};
    vm.update = false;
    vm.wh_type = 'Store';
    vm.wh_type_list = ['Store', 'Department'];
    vm.reasons_list = ['Pooling', 'Breakdown', 'Consumption', 'Caliberation',
                       'Damaged/Disposed']

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              xhrFields: {
                withCredentials: true
              },
              data: {'datatable': 'InventoryAdjustment', 'special_key':'adj'}
           })
       .withDataProp('data')
       .withOption('drawCallback', function(settings) {
         vm.service.make_selected(settings, vm.selected);
       })
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withOption('order', [0, 'desc'])
       .withOption('rowCallback', rowCallback)
       .withOption('createdRow', function(row, data, dataIndex) {
            $compile(angular.element(row).contents())($scope);
        })
        .withOption('headerCallback', function(header) {
            if (!vm.headerCompiled) {
                vm.headerCompiled = true;
                $compile(angular.element(header).contents())($scope);
            }
        })
       .withPaginationType('full_numbers');

    vm.dtColumns = [
//        DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
//            .renderWith(function(data, type, full, meta) {
//                if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
//                  vm.selected = {};
//                }
//                vm.selected[meta.row] = vm.selectAll;
//                return vm.service.frontHtml + meta.row + vm.service.endHtml;//+full[""];
//            }).notSortable(),
        DTColumnBuilder.newColumn('Created Date').withTitle('Created Date'),
        DTColumnBuilder.newColumn('Requested User').withTitle('Requested User'),
        DTColumnBuilder.newColumn('Store').withTitle('Store'),
        DTColumnBuilder.newColumn('Department').withTitle('Department'),
        DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('Adjustment Quantity').withTitle('Adjustment Quantity'),
        DTColumnBuilder.newColumn('Reason').withTitle('Reason'),
        DTColumnBuilder.newColumn('Status').withTitle('Status'),
    ];

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
      vm.dtInstance.reloadData();
      vm.bt_disable = true;
    };

    function excel() {
    angular.copy(vm.dtColumns,colFilters.headers);
    angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
    colFilters.download_excel()
  }

    vm.add = add;
    function add() {
      angular.copy(vm.empty_data, vm.model_data);
      vm.date = new Date();
      vm.date_format_convert(vm.date);
      vm.bt_disable = false;
      $state.go('app.stockLocator.InventoryAdjustment.Adjustment');
    }

    vm.date_format_convert = function(utc_date){
      var date = utc_date.toLocaleDateString();
      var datearray = date.split("/");
      vm.date = datearray[1] + '/' + datearray[0] + '/' + datearray[2];
    }

    vm.close = close;
    function close() {
      vm.update = false;
      $state.go('app.stockLocator.InventoryAdjustment');
    }

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
                console.log(aData);
                var inv_data = {id: aData['DT_RowId']}
                vm.service.apiCall('get_inventory_adjustment_doa/', "GET", inv_data).then(function(data){
                if(data.message) {
                  angular.copy(data.data.data, vm.model_data);
                  vm.wh_type = 'Department';
                  vm.model_data.data_id = data.data.id;
                  //vm.model_data.reason = data.data.data.reason;
                  vm.model_data.action_buttons = false;
                  if(aData['Status'] == 'Rejected'){
                    vm.model_data.action_buttons = true;
                  }
                  vm.model_data.plant = data.data.plant;
                  vm.model_data.plant_name = data.data.plant_name;
                  vm.model_data.warehouse = data.data.warehouse;
                  vm.model_data.warehouse_name = data.data.warehouse_name;
                  vm.batch_mandatory = data.data.data.batch_mandatory;
                  vm.mfg_readonly = data.data.data.mfg_readonly;
                  //if(data.data.data.batch_mandatory == 'true'){
                  //  vm.batch_mandatory = true;
                  //}
                  vm.update = true;
                  $state.go('app.stockLocator.InventoryAdjustment.Adjustment');
                }
              });
            });
        });
    }

    vm.message = "";
    vm.sku_empty = {'wms_code': '', 'description': '', 'batch_no': '', 'manufactured_date': '', 'expiry_date': '',
                    'uom': '', 'quantity': '', 'mfg_readonly': true, 'available_stock': 0}
    vm.empty_data = {
                      'wms_code':'',
                      'location': '',
                      'quantity': '',
                      'price': '',
                      'reason': '',
                      'data_id': '',
                      'data': [vm.sku_empty]
                    }
    vm.model_data = {};
    angular.copy(vm.empty_data, vm.model_data);
    vm.submit =submit;
    function submit(data) {
      vm.bt_disable = true;
      if(data.$valid) {
        var elem = angular.element($('form'));
        elem = elem[0];
        elem = $(elem).serializeArray();
        vm.service.apiCall('insert_inventory_adjust/', 'POST', elem, true).then(function(data){
          if(data.message) {
            if (data.data == "Added Successfully") {
              angular.extend(vm.model_data, vm.empty_data);
              vm.bt_disable = false;
              reloadData();
              vm.close();
            } else {
              vm.bt_disable = false;
              pop_msg(data.data);
            }
          }
        });
      } else {
        colFilters.showNoty('Please Fill * Fileds !');
        vm.bt_disable = false;
      }
    }
    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
        vm.message = "";
      }, 3000);
    } 

  vm.confirm_adjustment = confirm_adjustment;
  function confirm_adjustment() {
    console.log(vm.selected);
    var data = [];
    var rows = $(".custom-table").find("tbody tr");
    angular.forEach(vm.selected, function(k,v){
      if(k) {
        var row = rows[v];
        data.push({'id':$(row).find("input[type='hidden']").val(),
                   'reason':$(row).find("input[name='reason']").val()})
      }
    });
    var elem = "";
    for(var i=0; i < data.length; i++) {
      elem = elem+data[i].id+"="+data[i].reason+"&";
    }
    vm.service.apiCall('confirm_inventory_adjustment/?'+elem.slice(0,-1)).then(function(data){
      if(data.message) {
        colFilters.showNoty(data.data);
        reloadData();
      }
    })
  }

  vm.delete_adjustment = delete_adjustment;
  function delete_adjustment() {
    console.log(vm.selected);
    var data = [];
    var rows = $(".custom-table").find("tbody tr");
    angular.forEach(vm.selected, function(k,v){
      if(k) {
        var row = rows[Number(v)];
        data.push({'id':$(row).find("input[type='hidden']").val()})
      }
    });
    var elem = "";
    for(var i=0; i < data.length; i++) {
      elem = elem+data[i].id+"="+data[i].id+"&";
    }
    vm.service.apiCall('delete_inventory/?'+elem.slice(0,-1)).then(function(data){
      if(data.message) {
        colFilters.showNoty(data.data);
        reloadData();
      }
    })
  }

  vm.getReasons = function(key){

    if (key) {
      var send = {'key': 'sales_return_reasons'};
      vm.service.apiCall('inventory_adj_reasons/', 'POST', send).then(function(resp) {

        if (resp.message) {

          vm.reasons = resp.data.data.reasons;
        }
      });
    }
  }

  vm.get_machine_details = function(data, item) {
    data.machine_brand = item.brand;
  }

  vm.get_sku_batches = function(sku_code){
    if(sku_code && vm.industry_type==="FMCG"){
      vm.service.apiCall('get_sku_batches/?sku_code='+sku_code).then(function(data){
        if(data.message) {
          vm.batches = data.data.sku_batches;
          vm.batch_nos = Object.keys(vm.batches);
          vm.weights = data.data.sku_weights;
          vm.weight_list = Object.keys(vm.weights);
        }
      });
    }
  }

  vm.warehouse_dict = {};
  var wh_filter = {'warehouse_type': 'STORE'};
  vm.service.apiCall('get_warehouses_list/', 'GET',wh_filter).then(function(data){
    if(data.message) {
      vm.warehouse_dict = data.data.warehouse_mapping;
      vm.warehouse_list_states = data.data.states;
    }
  });

  vm.get_warehouse_department_list = get_warehouse_department_list;
  function get_warehouse_department_list() {
    var wh_data = {};
    vm.department_list = [];
    wh_data['warehouse'] = vm.model_data.plant;
    wh_data['warehouse_type'] = 'DEPT';
    vm.service.apiCall("get_company_warehouses/", "GET", wh_data).then(function(data) {
      if(data.message) {
        vm.department_list = data.data.warehouse_list;
      }
    });
  }

  vm.get_sku_details = function(data, selected) {
    if(!vm.model_data.warehouse){
      data.wms_code = '';
      if(vm.wh_type == 'Store'){
        colFilters.showNoty("Please select Store first");
      }
      else {
        colFilters.showNoty("Please select Department first");
      }
      return
    }
    if(!vm.model_data.reason){
      data.wms_code = '';
      colFilters.showNoty("Please Select Reason");
      return
    }
    data.wms_code = selected.wms_code;
    data.description = selected.sku_desc;
    data.uom = selected.base_uom;
    if(!vm.batch_mandatory){
      vm.update_availabe_stock(data);
    }
  }

   vm.get_batch_details = function(data, selected) {
    data.batch_no = selected.batch_no;
    data.manufactured_date = selected.manufactured_date;
    data.expiry_date = selected.expiry_date;
    data.available_stock = selected.quantity;
    data.uom = selected.uom;
  }

  vm.check_selected_batch = function(data) {
    if(!vm.batch_mandatory){
      return
    }
    var batch_check = {'wms_code': data.wms_code, 'warehouse': vm.model_data.warehouse, 'q': data.batch_no, 'commit': 'inventory'}
    vm.service.apiCall("search_batch_data/", "GET", batch_check).then(function(result) {
      if(result.message) {
        if(result.data.length){
          data.mfg_readonly = true;
        }
        else {
          data.mfg_readonly = false;
          data.manufactured_date = '';
          data.expiry_date = '';
          data.available_stock = 0;
          vm.update_final_stock(data);
        }
      }
    });
  }

    vm.update_availabe_stock = function(sku_data) {
     var send = {sku_code: sku_data.wms_code, location: "", source: vm.model_data.warehouse, 'comment': 'inventory'}
     vm.service.apiCall("get_sku_stock_check/", "GET", send).then(function(data){
      sku_data["available_stock"] = 0
      if(data.message) {
        if(data.data.available_quantity) {
          sku_data["available_stock"] = data.data.available_quantity;
          sku_data.quantity = 0;
        }
        else {
          sku_data.quantity = 0;
        }
        vm.update_final_stock(sku_data);
      }
    });
  }

  vm.update_qty_on_final_qty = function(sku_data){
        var final_qty = 0;
      if(sku_data.final_stock != ''){
        final_qty = parseFloat(sku_data.final_stock);
      }
      if((['Pooling']).indexOf(vm.model_data.reason) != -1){
        if(final_qty < sku_data.available_stock){
          sku_data.final_stock = sku_data.available_stock;
          colFilters.showNoty("Final Stock should be more than or equal to available stock");
          return
        }
        sku_data.quantity = parseFloat((final_qty - sku_data.available_stock).toFixed(3));
      }
      else{
        if(sku_data.available_stock < final_qty){
          colFilters.showNoty("Entered Final stock is less than available stock");
          sku_data.final_stock = sku_data.available_stock - sku_data.quantity;
          return
        }
        sku_data.quantity = parseFloat((sku_data.available_stock - final_qty).toFixed(3));
      }
  }

  vm.update_final_stock = function(sku_data, key){
    if(key == 'final_stock'){
      vm.update_qty_on_final_qty(sku_data);
    }
    else {
      var temp_qty = 0;
      if(sku_data.quantity!=''){
        temp_qty = parseFloat(sku_data.quantity);
      }
      if((['Pooling']).indexOf(vm.model_data.reason) != -1){
        sku_data.final_stock = temp_qty + sku_data.available_stock;
      }
      else{
        sku_data.final_stock = sku_data.available_stock - temp_qty;
      }
    }
  }

  vm.add_new_row = function(sku_data){
    if(sku_data.wms_code){
      var sku_empty={};
      angular.copy(vm.sku_empty, sku_empty);
      vm.model_data.data.push(sku_empty);
    }
  }

  vm.update_sku_data = function(){
    angular.forEach(vm.model_data.data, function(sku_data){
      vm.update_final_stock(sku_data);
    });
  }

    vm.check_quantity = function(sku_data){
    if(vm.model_data.reason != 'Pooling'){
      var qty = sku_data.quantity;
      if(!qty){
        qty = 0;
      }
      else {
        qty = parseFloat(qty);
      }
      if(qty > parseFloat(sku_data.available_stock)){
        sku_data.quantity = 0;
        colFilters.showNoty("Entered Quantity is more than available stock");
      }

    }
  }

    vm.send_for_approval = send_for_approval;
    function send_for_approval(data) {
      if(data.$valid) {
        var elem = angular.element($('form'));
        elem = elem[0];
        elem = $(elem).serializeArray();
        vm.service.apiCall('insert_inventory_adjust_approval/', 'POST', elem, true).then(function(data){
          if(data.message) {
            if (data.data == "Added Successfully") {
              angular.extend(vm.model_data, vm.empty_data);
              reloadData();
              vm.close();
            } else {
              pop_msg(data.data);
            }
          }
        });
      }
    }

    vm.reject_adjustment = reject_adjustment;
    function reject_adjustment(data) {
      if(data.$valid) {
        var elem = angular.element($('form'));
        elem = elem[0];
        elem = $(elem).serializeArray();
        vm.service.apiCall('reject_inventory_adjustment/', 'POST', elem, true).then(function(data){
          if(data.message) {
            if (data.data == "Updated Successfully") {
              angular.extend(vm.model_data, vm.empty_data);
              reloadData();
              vm.close();
            } else {
              pop_msg(data.data);
            }
          }
        });
      }
    }

}

