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
        DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
                if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                  vm.selected = {};
                }
                vm.selected[meta.row] = vm.selectAll;
                return vm.service.frontHtml + meta.row + vm.service.endHtml+full[""];
            }).notSortable(),
        DTColumnBuilder.newColumn('Location').withTitle('Location'),
        DTColumnBuilder.newColumn('WMS Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('Description').withTitle('Description'),
        DTColumnBuilder.newColumn('Total Quantity').withTitle('Total Quantity'),
        DTColumnBuilder.newColumn('Physical Quantity').withTitle('Physical Quantity'),
        DTColumnBuilder.newColumn('Reason').withTitle('Reason'),
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
      $state.go('app.stockLocator.InventoryAdjustment.Adjustment');
    }

    vm.close = close;
    function close() {

      $state.go('app.stockLocator.InventoryAdjustment');
    }

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
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
                      'data': [vm.sku_empty]
                    }
    vm.model_data = {};
    angular.copy(vm.empty_data, vm.model_data);
    vm.submit =submit;
    function submit(data) {
      if(data.$valid) {
        var elem = angular.element($('form'));
        elem = elem[0];
        elem = $(elem).serializeArray();
        vm.service.apiCall('insert_inventory_adjust/', 'POST', elem, true).then(function(data){
          if(data.message) {
            if (data.data == "Added Successfully") {
              angular.extend(vm.model_data, vm.empty_data);
              vm.close();
            } else {
              pop_msg(data.data);
            }
          }
        });
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
    data.uom = selected.measurement_unit;
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
    var batch_check = {'wms_code': data.wms_code, 'warehouse': vm.model_data.warehouse, 'q': data.batch_no}
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
        }
      }
    });
  }

    vm.update_availabe_stock = function(sku_data) {
     var send = {sku_code: sku_data.wms_code, location: "", source: vm.model_data.warehouse}
     vm.service.apiCall("get_sku_stock_check/", "GET", send).then(function(data){
      sku_data["available_stock"] = 0
      if(data.message) {
        if(data.data.available_quantity) {
          sku_data["available_stock"] = data.data.available_quantity;
          sku_data.quantity = 1;
        }
        else {
          sku_data.quantity = 0;
        }
        vm.update_final_stock(sku_data);
      }
    });
  }

  vm.update_final_stock = function(sku_data){
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

}

