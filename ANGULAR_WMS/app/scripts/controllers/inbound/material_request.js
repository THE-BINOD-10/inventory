'use strict';

function MaterialStockOrders($scope, $http, $q, $state, Session, colFilters, Service) {

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
  var empty_data = {data: [{wms_code: "", order_quantity: 0, price: "", capacity:0, tax_type: ""}], warehouse_name: "",
                            source_seller_id:"", dest_seller_id: "", total_qty: 0};
  angular.copy(empty_data, vm.model_data);
  vm.isLast = isLast;
    function isLast(check) {
      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

  vm.check_sku_dup = check_sku_dup;
  function check_sku_dup(index, data, last) {
    var status = true;
    var temp_skus = []
    angular.forEach(data, function(dat, indexs){
      if(temp_skus.includes(dat['sku_id'])){
        status = false;
        data.splice(indexs, 1)
      } else {
        temp_skus.push(dat['sku_id'])
      }
    })
    if (status) {
      vm.update_data(index, data, last);
    } else {
      colFilters.showNoty("Duplicate Sku Code !!");
    }
  }

  vm.update_data = update_data;
  function update_data(index, data, last) {
    if (last) {
      vm.model_data.data.push({wms_code: "", order_quantity: 0, price: ""});
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

vm.plants_list = {};
vm.department_type_list = {};
vm.department_type_mapping = {};
vm.get_staff_plants_list = get_staff_plants_list;
function get_staff_plants_list() {
  vm.service.apiCall("get_staff_plants_list/", "GET", {}).then(function(data) {
    if(data.message) {
      // vm.plants_list = data.data.plants_list;
      angular.forEach(Object.keys(data.data.plants_list).sort(), function(dat){
        vm.plants_list[dat] = data.data.plants_list[dat];
      })
      vm.department_type_list = data.data.department_type_list;
      vm.department_type_mapping = data.data.department_type_list;
    }
  });
}
vm.get_staff_plants_list();

vm.department_list = [];
vm.get_warehouse_department_list = get_warehouse_department_list;
function get_warehouse_department_list() {
  var wh_data = {};
  vm.department_type_list = {};
  wh_data['warehouse'] = vm.model_data.plant;
  wh_data['warehouse_type'] = 'DEPT';
  vm.service.apiCall("get_company_warehouses/", "GET", wh_data).then(function(data) {
    if(data.message) {
      angular.forEach(data.data.warehouse_list, function(dat){
        if(vm.department_type_mapping[dat.stockone_code]) {
          vm.department_type_list[dat.username] = vm.department_type_mapping[dat.stockone_code];
        }
      });
    }
  });
}

vm.changeUnitPrice = function(data){
  if (parseFloat(data.order_quantity) > 0) {
    data.conversion = parseFloat(data.order_quantity) * parseFloat(data.temp_conversion);
  }
  if (parseFloat(data.capacity) < parseFloat(data.order_quantity)) {
    data.total_qty = 0;
    data.order_quantity = 0;
    colFilters.showNoty("Total Qty Should be less then available Quantity");
  }
  data.total_price = (data.order_quantity * data.price)
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

  vm.warehouse_list = [];
  vm.service.apiCall('get_warehouses_list/').then(function(data){
    if(data.message) {
      vm.warehouse_list = data.data.warehouses;
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
  vm.validate_sku = function(elem){
    var status_flag = true;
    angular.forEach(elem, function(dat){
      if (dat['name'] == 'order_quantity' &&  (dat['value'] == '' || dat['value'] == 0)) {
        status_flag= false;
      }
    })
    return status_flag;
  }
  vm.bt_disable = false;
  vm.insert_order_data = function(data) {
    if (data.$valid) {
      vm.bt_disable = true;
      var elem = angular.element(form);
      elem = $(elem).serializeArray();
      elem.push ({'name': 'order_typ', 'value': 'MR'})
      if (vm.validate_sku(elem)) {
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
        vm.bt_disable = false;
        colFilters.showNoty("Please Fill Quantity ! ");  
      }
    } else {
      vm.bt_disable = false;
      colFilters.showNoty("Fill Required Fields");
    }
  }

  vm.update_data_order = function(index, data, last) {
    console.log(data);
    if (last) {
      var total = 0;
      for(var i=0; i < data.sub_data.length; i++) {
        total = total + parseInt(data.sub_data[i].picked_quantity);
      }
      if(total < data.reserved_quantity) {
        var clone = {};
        angular.copy(data.sub_data[index], clone);
        clone.picked_quantity = data.reserved_quantity - total;
        data.sub_data.push(clone);
      }
    } else {
      data.sub_data.splice(index,1);
    }
  }
  
  vm.update_availabe_stock = function(sku_data) {
     var send = {sku_code: sku_data.sku_id, location: "", source: vm.model_data.plant}
     vm.service.apiCall("get_sku_stock_check/", "GET", send).then(function(data){
      sku_data["capacity"] = 0
      if(data.message) {
        if(data.data.available_quantity) {
          sku_data["capacity"] = (parseFloat(data.data.available_quantity)).toFixed(2);
        }
      }
    });
  }

  vm.get_sku_data = function(record, item, index) {
    if (typeof(item) != "undefined") {
      angular.copy(empty_data.data[0], record);
      if (vm.model_data.plant && vm.model_data.department_type) {
        record.sku_id = item.wms_code;
        record["description"] = item.sku_desc;
        record.conversion = item.conversion;
        record.temp_conversion = item.conversion;
        record.base_uom = item.base_uom;
        record.measurement_unit = item.measurement_unit;
        vm.get_customer_sku_prices(item.wms_code, vm.model_data.plant).then(function(data){
          if(data.length > 0) {
            data = data[0]
            record.mrp = data.mrp;
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
            console.log(record);
          }
        })
      } else {
        colFilters.showNoty("Please select Plant and Department");
      }
    }
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

  vm.get_customer_sku_prices = function(sku, source='') {
    var d = $q.defer();
    var data = {sku_codes: sku}
    if (source) {
      data['source'] = source;
    }
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
  .controller('MaterialStockOrders', ['$scope', '$http', '$q', '$state', 'Session', 'colFilters', 'Service', MaterialStockOrders]);
