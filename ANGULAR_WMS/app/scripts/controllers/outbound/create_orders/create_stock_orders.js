'use strict';

function CreateStockOrders($scope, $http, $q, $state, Session, colFilters, Service) {

  $scope.msg = "start";
  var vm = this;
  vm.service = Service;
  vm.current_user = {[$scope.user.userName]: $scope.user.user_profile.state};
  vm.tax_cg_sg = false;
  vm.igst_enable = false;
  vm.dest_sellers_list = [];
  vm.model_data = {};
  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;
  var empty_data = {data: [{wms_code: "", order_quantity: "", price: "", capacity:0, tax_type: ""}], warehouse_name: "",
                            source_seller_id:"", dest_seller_id: ""};
  angular.copy(empty_data, vm.model_data);
  vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

  vm.update_data = update_data;
  function update_data(index, data, last) {
    console.log(data);
    if (last) {
      vm.model_data.data.push({wms_code: "", order_quantity: "", price: ""});
    } else {
      vm.model_data.data.splice(index,1);
    }
  }
vm.get_sku_details = function (data){
  vm.service.apiCall('get_mapping_values/', 'GET', {'wms_code':data.wms_code, 'supplier_id': 0}).then(function(resp){
    if(Object.values(resp).length) {
      data.price = resp.data.price;
    }
  });
}
vm.changeUnitPrice = function(data){
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
      cgst_percentage = (data.total_price * parseFloat(data.cgst)) / 100
  }
  if(data.sgst)
  {
     sgst_percentage = (data.total_price * parseFloat(data.sgst)) / 100
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
  vm.warehouse_dict = {};
  vm.service.apiCall('get_warehouses_list/').then(function(data){
    if(data.message) {
      vm.warehouse_dict = data.data.warehouse_mapping;
      vm.warehouse_list_states = data.data.states;
    }
  })

  vm.sellers_list = [];
  vm.service.apiCall('get_sellers_list/').then(function(data){
    if(data.message) {
      vm.sellers_list = data.data.sellers;
      if(vm.sellers_list.length > 0) {
        vm.model_data.source_seller_id = vm.sellers_list[0].id;
      }
    }
  });

  vm.bt_disable = false;
  vm.insert_order_data = function(data) {
    if (data.$valid) {
      vm.bt_disable = true;
      var elem = angular.element(form);
      elem = $(elem).serializeArray();
      vm.service.apiCall('create_stock_transfer/', 'POST', elem).then(function(data){
        if(data.message) {
          if("Confirmed Successfully" == data.data) {
            angular.copy(empty_data, vm.model_data);
          }
          colFilters.showNoty(data.data);
          vm.bt_disable = false;
        }
      })
    } else {
      colFilters.showNoty("Fill Required Fields");
    }
  }

  vm.update_availabe_stock = function(sku_data) {
     var send = {sku_code: sku_data.sku_id, location: ""}
     vm.service.apiCall("get_sku_stock_check/", "GET", send).then(function(data){
      sku_data["capacity"] = 0
      if(data.message) {
        if(data.data.available_quantity) {
          sku_data["capacity"] = data.data.available_quantity;
        }
        if (vm.industry_type == 'FMCG') {
          sku_data['price'] = data.data.data[Object.keys(data.data.data)[0]]['buy_price'];
        }
      }
    });
  }

  vm.get_sku_data = function(record, item, index) {
    record.sku_id = item.wms_code;
    angular.copy(empty_data.data[0], record);
    record.sku_id = item.wms_code;
    record["description"] = item.sku_desc;
    vm.changeUnitPrice(record);
    vm.get_customer_sku_prices(item.wms_code).then(function(data){
      if(data.length > 0) {
        data = data[0]
        record.mrp = data.mrp;
        // record["price"] = data.mrp;
          if(!(record.order_quantity)) {
            record.order_quantity = 1
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
           if(data.igst_tax){
            record.sgst_tax = data.igst_tax / 2;
            record.cgst_tax = data.igst_tax / 2 ;
            }else{
            record.sgst_tax = data.sgst_tax;
            record.cgst_tax = data.cgst_tax;
            }

          }


        record.invoice_amount = Number(record.price)*Number(record.quantity);
        vm.update_availabe_stock(record)
//        vm.change_brand(data)

      }
    })
  }
  vm.verifyTax = function() {
    var temp_ware_name = '';
    if (vm.warehouse_list_states[vm.model_data.selected] && vm.warehouse_list_states[vm.model_data.selected]){
      if (vm.warehouse_list_states[vm.model_data.selected] == vm.current_user[Object.keys(vm.current_user)[0]]) {
        vm.tax_cg_sg = true;
        vm.igst_enable = false;
      } else {
        vm.tax_cg_sg = false;
        vm.igst_enable = true;
      }
    } else {
      if (!vm.warehouse_list_states[vm.model_data.selected]){
        temp_ware_name = vm.model_data.selected;
        vm.model_data.selected = '';
        colFilters.showNoty(temp_ware_name +" - Please update state in Warehouse Mater");
      }
      if (!vm.current_user[Object.keys(vm.current_user)[0]]){
        vm.model_data.selected = '';
        colFilters.showNoty(Object.keys(vm.current_user)[0]+" - Please update state in Warehouse Mater");
      }
    }
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

  vm.get_customer_sku_prices = function(sku) {

    var d = $q.defer();
    var data = {sku_codes: sku}
    vm.service.apiCall("get_customer_sku_prices/", "POST", data).then(function(data) {
      if(data.message) {
        d.resolve(data.data);
      }
    });
    return d.promise;
  }

}

angular
  .module('urbanApp')
  .controller('CreateStockOrders', ['$scope', '$http', '$q', '$state', 'Session', 'colFilters', 'Service', CreateStockOrders]);
