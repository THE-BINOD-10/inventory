'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('RaiseStockTransferCtrl',['$scope', '$http', '$q', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $q, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.apply_filters = colFilters;
    vm.permissions = Session.roles.permissions;
    vm.industry_type = Session.user_profile.industry_type;
    vm.user_type = Session.user_profile.user_type;
    vm.filters = {'datatable': 'RaiseST', 'search0':'', 'search1':''};
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
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });
    var columns = ['Warehouse Name', 'Total Quantity']
    vm.dtColumns = vm.service.build_colums(columns);

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        // Unbind first in order to avoid any duplicate handler (see https://github.com/l-lin/angular-datatables/issues/87)
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                $http.get(Session.url+'update_raised_st?warehouse_name='+aData['Warehouse Name']).success(function(data, status, headers, config) {
                  console.log(data);
                  vm.update = true;
                  vm.get_sellers_list(true);
                  vm.title = "Update Stock Transfer";
                  angular.copy(data, vm.model_data);
                  vm.changeDestSeller();
                  $state.go('app.inbound.TransferOrder.StockTransfer');
                });
            });
        });
        return nRow;
    } 

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    $scope.$on('change_filters_data', function(){
      if($("#"+vm.dtInstance.id+":visible").length != 0) {
        vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
        vm.reloadData();
      }
    });

    vm.update = true;
    vm.status_data = ["Active","Inactive"];
    vm.status= vm.status_data[0];
    vm.model_data = {};
    var empty_data = {data: [{wms_code: "", order_quantity: "", price: "", capacity:0,  to_capacity:0, tax_type: ""}], warehouse_name: "",
                              source_seller_id:"", dest_seller_id: ""};
    angular.copy(empty_data, vm.model_data);
    // var empty_data = {"Supplier_ID":"",
    //                   "POName": "",
    //                   "ShipTo": "",
    //                   "warehouse_name": "",
    //                   "source_seller_id": "",
    //                   "dest_seller_id": "",
    //                   "data": [
    //                     {"WMS_Code":"", "Supplier_Code":"", "Quantity":"", "Price":""}
    //                   ]
    //                  };
    // vm.model_data = {};
    // angular.copy(empty_data, vm.model_data);

    vm.get_sellers_list = get_sellers_list;
    function get_sellers_list(is_update) {
      vm.sellers_list = [];
      vm.service.apiCall('get_sellers_list/').then(function(data){
      if(data.message) {
        vm.sellers_list = data.data.sellers;
        // if(vm.sellers_list && !is_update) {
        //   vm.model_data.source_seller_id = vm.sellers_list[0].id;
        // }
      }
    });
    }
    vm.warehouse_dict = {};
    var wh_filter = {'warehouse_type': 'STORE'};
    vm.service.apiCall('get_warehouses_list/', 'GET',wh_filter).then(function(data){
      if(data.message) {
        vm.warehouse_dict = data.data.warehouse_mapping;
        vm.warehouse_list_states = data.data.states;
      }
    });

    vm.sellers_list = [];
    vm.service.apiCall('get_sellers_list/').then(function(data){
      if(data.message) {
        vm.sellers_list = data.data.sellers;
        if(vm.sellers_list.length > 0) {
          vm.model_data.source_seller_id = vm.sellers_list[0].id;
        }
      }
    });
    vm.verifyTax = function() {
      var temp_ware_name = '';
      if (vm.model_data.selected != vm.model_data.warehouse_name) {
        if (vm.warehouse_list_states[vm.model_data.selected] && vm.warehouse_list_states[vm.model_data.warehouse_name]){
          if (vm.warehouse_list_states[vm.model_data.selected] == vm.warehouse_list_states[vm.model_data.warehouse_name]) {
            vm.tax_cg_sg = true;
            vm.igst_enable = false;
          } else {
            vm.tax_cg_sg = false;
            vm.igst_enable = true;
          }
        } else if (!vm.warehouse_list_states[vm.model_data.selected]){
            temp_ware_name = vm.model_data.selected;
            vm.model_data.selected = '';
            colFilters.showNoty(temp_ware_name +" - Please update state in Source Plant");
        } else if (!vm.warehouse_list_states[vm.model_data.warehouse_name]){
            temp_ware_name = vm.model_data.warehouse_name;
            vm.model_data.warehouse_name = '';
            colFilters.showNoty(temp_ware_name +" - Please update state in Destination Plant");
        }
      } else {
        colFilters.showNoty("Request To & Request From Cannot be Same !");
        vm.model_data.selected = ''
        vm.model_data.warehouse_name = ''
      }
    }
    vm.close = close;
    function close() {
      vm.model_data = {};
      angular.copy(empty_data, vm.model_data);
      $state.go('app.inbound.TransferOrder');
    }
    vm.add = add;
    function add() {
      $http.get(Session.url+'raise_st_toggle/').success(function(data, status, headers, config) {
        vm.model_data['warehouse_list'] = data.user_list;
      });
      vm.get_sellers_list();
      vm.title = "Raise Stock Transfer";
      vm.model_data = {};
      angular.copy(empty_data, vm.model_data);
      vm.update = false;
      $state.go('app.inbound.TransferOrder.StockTransfer');
    } 
    vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }
    vm.update_data = update_data;
    function update_data(index) {

      if (index == vm.model_data.data.length-1) {
        vm.model_data.data.push({"wms_code":"", "quantity":"", "price":""});
      } else {
        vm.delete_st(vm.model_data.data[index]);
        vm.model_data.data.splice(index,1);
      }
    }

    vm.save_stock = save_stock;
    function save_stock(data) {
      if (data.$valid) {
        var elem = angular.element($('form'));
        elem = $(elem).serializeArray();
        vm.service.apiCall('save_st/', 'POST', elem, true).then(function(data){
          if(data.message){
            if(data.data == 'Added Successfully') {
              vm.close();
              vm.reloadData();
            } else {
              pop_msg(data.data);
            }
          }
        });
      }
    }

    vm.confirm_stock = confirm_stock;
    function confirm_stock(data) {

     if (data.$valid) {
      var elem = angular.element($('form'));
      elem = $(elem).serializeArray();
      vm.service.apiCall('confirm_st/', 'POST', elem, true).then(function(data){
        if(data.message){
          if(data.data == 'Confirmed Successfully') {
            vm.close();
            vm.reloadData();
          } else {
            pop_msg(data.data);
          }
        }
      });
     }
    }

    vm.delete_st = delete_st;
    function delete_st(data){
      console.log(data);
      if(typeof(data.id) == "number") {
        $http.get(Session.url+"delete_st/?data_id="+data.id, {withCredential: true}).success(function(data){
          pop_msg(data);
        })
      }
    }

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 2000);
      reloadData();
    }

    vm.changeDestSeller = function() {
      vm.dest_sellers_list = [];
      var temp_data = {warehouse: vm.model_data.warehouse_name}
      vm.service.apiCall("get_sellers_list/", "GET", temp_data).then(function(data){
      if(data.message) {
        vm.dest_sellers_list = data.data.sellers;
        if(vm.dest_sellers_list) {
          vm.model_data.dest_seller_id = vm.sellers_list[0].id;
        }
      }
    });
  }
  vm.update_availabe_stock = function(sku_data) {
     var send = {sku_code: sku_data.sku_id, location: "", source: vm.model_data.warehouse_name, dept: vm.model_data.selected}
     vm.service.apiCall("get_sku_stock_check/", "GET", send).then(function(data){
      sku_data["capacity"] = 0
      sku_data["to_capacity"] = 0
      if(data.message) {
        if(data.data.available_quantity) {
          sku_data["capacity"] = data.data.available_quantity;
          sku_data["to_capacity"] = data.data.dept_avail_qty
          sku_data['price'] = data.data.avg_price;
          vm.changeUnitPrice(sku_data);
        }
      }
    });
  }

  vm.get_sku_data = function(record, item, index) {
    if (!vm.model_data.selected || !vm.model_data.warehouse_name) {
      record.sku_id ='';
      colFilters.showNoty("Please select Source and Destination Plant");
      return
    }
    record.sku_id = item.wms_code;
    angular.copy(empty_data.data[0], record);
    record.sku_id = item.wms_code;
    record["description"] = item.sku_desc;
    record.conversion = item.conversion;
    record.base_uom = item.base_uom;
    record.measurement_unit = item.measurement_unit;
    vm.get_customer_sku_prices(item.wms_code).then(function(data){
      if(data.length > 0) {
        data = data[0]
        record.mrp = data.mrp;
          if(!(record.order_quantity)) {
            record.order_quantity = ''
          }
          if(!(record.price)) {
            record.price = data.cost_price;
          }
          if(vm.igst_enable){
            if(data.igst_tax){
            record.igst = data.igst_tax;
            }else{
            record.igst = data.sgst_tax+data.cgst_tax;
            }
          }else {
           if(data.igst){
            record.sgst = data.igst_tax / 2;
            record.cgst = data.igst_tax / 2 ;
            }else{
            record.sgst = data.sgst_tax;
            record.cgst = data.cgst_tax;
            }
          }
        record.sgst = 0;
        record.cgst = 0;
        record.igst = 0;
        record.invoice_amount = Number(record.price)*Number(record.quantity);
        vm.update_availabe_stock(record);
      }
    })
  }
  vm.changeDestSeller = function() {
    vm.dest_sellers_list = [];
    var temp_data = {warehouse: vm.model_data.selected}
    vm.service.apiCall("get_sellers_list/", "GET", temp_data).then(function(data){
      if(data.message) {
        vm.dest_sellers_list = data.data.sellers;
        if(vm.sellers_list.length>0) {
          vm.model_data.dest_seller_id = vm.sellers_list[0].id;
        }
      }
    });
  }
  vm.changeUnitPrice = function(data){
    if (parseFloat(data.order_quantity) > 0) {
      data.total_qty = parseFloat(data.order_quantity) * parseFloat(data.conversion);
    }
    if (parseFloat(data.capacity) < parseFloat(data.order_quantity)) {
      data.total_qty = 0;
      data.order_quantity = '';
      colFilters.showNoty("Total Qty Should be less than available Quantity");
    }
    var order_quantity = data.order_quantity;
    var price = data.price;
    if(!order_quantity) {
      order_quantity = 0
    }
    if(!price) {
      price = 0
    }
    data.total_price = (order_quantity * price)
    var cgst_percentage = 0;
    var sgst_percentage = 0;

    if(data.cgst)
    {
        cgst_percentage = (data.total_price * parseFloat(data.cgst)) / 100;
        data.total_price += cgst_percentage;
    }
    if(data.sgst)
    {
       sgst_percentage = (data.total_price * parseFloat(data.sgst)) / 100;
       data.total_price += sgst_percentage;
    }
    if(data.igst)
    {
      var igst_percentage = (data.total_price * parseFloat(data.igst)) / 100
      data.total_price += igst_percentage;
    }
     if(data.cess)
    {
      var cess_percentage = (data.total_price * parseFloat(data.cess)) / 100
      data.total_price += cess_percentage;
    }
    else{
      data.total_price += cgst_percentage + sgst_percentage;
    }
    data.total_price = (data.total_price).toFixed(3).slice(0,-1);
  }
  vm.changeDestWarehouse = function() {
    angular.forEach(vm.warehouse_dict, function(wh){
      console.log(wh);
      if(wh.username == vm.model_data.selected){
        vm.model_data.company_id = wh['userprofile__company_id'];
      }
    });
    if(vm.model_data.company_id){
      var wh_data = {};
      vm.dest_wh_list = {};
      wh_data['company_id'] = vm.model_data.company_id;
      wh_data['warehouse_type'] = 'STORE,SUB_STORE';
      vm.service.apiCall("get_company_warehouses/", "GET", wh_data).then(function(data) {
        if(data.message) {
        vm.dest_wh_list = data.data.warehouse_list;
      }
    });
    }
  }
  vm.get_customer_sku_prices = function(sku) {
    var d = $q.defer();
    var data = {sku_codes: sku, source: vm.model_data.selected}
    if(vm.igst_enable){
      data['tax_type'] = 'inter_state';
    } else if (vm.tax_cg_sg) {
      data['tax_type'] = 'inter_state';
    }
    vm.service.apiCall("get_customer_sku_prices/", "POST", data).then(function(data) {
      if(data.message) {
        d.resolve(data.data);
      }
    });
    return d.promise;
  }
  vm.validate = function (elem) {
    angular.forEach(elem, function(wh, index){
      if (wh['name'] == 'source_plant') {
        wh['value'] = vm.model_data['warehouse_name'];
      } else if (wh['name'] == 'warehouse_name') {
        wh['value'] = vm.model_data['selected'];
      }
      if (elem.length == index+1) {
        vm.service.apiCall('create_stock_transfer/', 'POST', elem).then(function(data){
          if(data.message) {
            if("Confirmed Successfully" == data.data.status) {
              vm.close();
              vm.reloadData();
              angular.copy(empty_data, vm.model_data);
              swal2({
                title: 'Confirmed ST Number',
                text: data.data.id,
                icon: "success",
                button: "OK",
                allowOutsideClick: false
              }).then(function (text) {
              });
            }
            vm.bt_disable = false;
          }
        })
      }
    })
  }
  vm.bt_disable = false;
  vm.insert_order_data = function(data) {
    if (data.$valid) {
      vm.bt_disable = true;
      var elem = angular.element($('form#add_st_intra'));
      elem = $(elem).serializeArray();
      vm.validate(elem);
    } else {
      vm.bt_disable = false;
      colFilters.showNoty("Fill Required Fields");
    }
  }
  // vm.get_sku_data = function(record, item, index) {
  //   record.wms_code = item.wms_code;
  //   var get_data = {sku_codes: record.wms_code}
  //   vm.service.apiCall("get_customer_sku_prices/", "POST", get_data).then(function(data) {
  //     if(data.message) {
  //       data = data.data;
  //       if(data.length > 0) {
  //         data = data[0]
  //         record.mrp = data.mrp;
  //         if(!(record.order_quantity)) {
  //           record.order_quantity = 1
  //         }
  //         if(!(record.price)) {
  //           record.price = data.mrp;
  //         }
  //       }
  //     }
  //   });
  // }

}