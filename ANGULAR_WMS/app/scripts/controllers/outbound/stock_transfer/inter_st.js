'use strict';

function CreateStockOrdersInter($scope, $http, $q, $state, Session, colFilters, Service) {

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
  if (parseFloat(data.order_quantity) > 0) {
    data.total_qty = parseFloat(data.order_quantity) * parseFloat(data.conversion);
  }
  if (parseFloat(data.capacity) < parseFloat(data.order_quantity)) {
    data.total_qty = 0;
    data.order_quantity = 0;
    colFilters.showNoty("Total Qty Should be less then available Quantity");
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

  vm.bt_disable = false;
  vm.insert_order_data = function(data) {
    if (data.$valid) {
      vm.bt_disable = true;
      var elem = angular.element($('form#add_st_intra'));
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
     var send = {sku_code: sku_data.sku_id, location: "", source: vm.model_data.selected}
     vm.service.apiCall("get_sku_stock_check/", "GET", send).then(function(data){
      sku_data["capacity"] = 0
      if(data.message) {
        if(data.data.available_quantity) {
          sku_data["capacity"] = data.data.available_quantity;
          sku_data['price'] = data.data.avg_price;
          vm.changeUnitPrice(sku_data);
        }
//        if (vm.industry_type == 'FMCG') {
//          sku_data['price'] = data.data.data[Object.keys(data.data.data)[0]]['buy_price'];
//        }
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
           if(data.igst){
            record.sgst = data.igst_tax / 2;
            record.cgst = data.igst_tax / 2 ;
            }else{
            record.sgst = data.sgst_tax;
            record.cgst = data.cgst_tax;
            }
          }
        record.invoice_amount = Number(record.price)*Number(record.quantity);
        vm.update_availabe_stock(record);
//        vm.change_brand(data)

      }
    })
  }
  vm.verifyTax = function() {
    var temp_ware_name = '';
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
        vm.model_data.selected = '';
        colFilters.showNoty(temp_ware_name +" - Please update state in Destination Plant");
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

  vm.company_list = [];
  vm.get_company_list = function() {
    vm.company_list = [];
    vm.service.apiCall("get_company_list/", "GET", {'send_parent': false}).then(function(data) {
      if(data.message) {
        //vm.company_list = data.data.company_list;
        angular.forEach(data.data.company_list, function(company){
          if(company.id!=vm.model_data.company_id){
            vm.company_list.push(company)
          }
        });
      }
    });
  }

  vm.changeDestCompany = function() {
    console.log(vm.model_data);
    angular.forEach(vm.warehouse_dict, function(wh){
      if(wh.username == vm.model_data.selected){
        vm.model_data.company_id = wh['userprofile__company_id'];
      }
    });
    vm.get_company_list();
  }

  vm.changeDestWarehouse = function(){
      var wh_data = {};
      vm.dest_wh_list = {};
      wh_data['company_id'] = vm.model_data.dest_company_id;
      wh_data['warehouse_type'] = 'STORE,SUB_STORE';
      vm.service.apiCall("get_company_warehouses/", "GET", wh_data).then(function(data) {
        if(data.message) {
        vm.dest_wh_list = data.data.warehouse_list;
      }
    });
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

}

angular
  .module('urbanApp')
  .controller('CreateStockOrdersInter', ['$scope', '$http', '$q', '$state', 'Session', 'colFilters', 'Service', CreateStockOrdersInter]);
