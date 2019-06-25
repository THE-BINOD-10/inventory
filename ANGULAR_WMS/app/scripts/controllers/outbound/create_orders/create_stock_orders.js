'use strict';

function CreateStockOrders($scope, $http, $q, $state, Session, colFilters, Service) {

  $scope.msg = "start";
  var vm = this;
  vm.service = Service;
  vm.model_data = {}
  var empty_data = {data: [{wms_code: "", order_quantity: "", price: "", capacity:0, tax_type: ""}], warehouse_name: ""};
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
  else{
    data.total_price += cgst_percentage + sgst_percentage;
  }
}
  vm.warehouse_list = [];
  vm.service.apiCall('get_warehouses_list/').then(function(data){
    if(data.message) {
      vm.warehouse_list = data.data.warehouses;
    }
  })
  vm.bt_disable = false;
  vm.insert_order_data = function(data) {
    if (data.$valid) {
      vm.bt_disable = true;
      console.log(form);
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
      }
    });
  }

  vm.get_sku_data = function(record, item, index) {

    record.sku_id = item.wms_code;
    angular.copy(empty_data.data[0], record);
    record.sku_id = item.wms_code;
    record["description"] = item.sku_desc;

    vm.get_customer_sku_prices(item.wms_code).then(function(data){
      if(data.length > 0) {
        data = data[0]
        // record["price"] = data.mrp;
          if(!(record.order_quantity)) {
            record.order_quantity = 1
          }
          if(!(record.price)) {
            record.price = data.mrp;
          }
          if(data.igst_tax){
            record.igst = data.igst_tax;
          }
          if(data.sgst_tax){
            record.sgst = data.sgst_tax;
          }
          if(data.cgst_tax){
            record.cgst = data.cgst_tax;
          }

        record.invoice_amount = Number(record.price)*Number(record.quantity);
        vm.update_availabe_stock(record)
        vm.change_brand(data)

      }
    })
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
