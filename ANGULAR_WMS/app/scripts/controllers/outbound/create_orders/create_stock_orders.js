'use strict';

function CreateStockOrders($scope, $http, $state, Session, colFilters, Service) {

  $scope.msg = "start";
  var vm = this;
  vm.service = Service;
  vm.model_data = {}
  var empty_data = {data: [{wms_code: "", order_quantity: "", price: ""}], warehouse_name: ""};
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
  if(data.cgst)
  {
    data.total_price += parseFloat(data.cgst)
  }
  if(data.sgst)
  {
   data.total_price += parseFloat(data.cgst)
  }
  if(data.igst)
  {
   data.total_price += parseFloat(data.cgst)
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
}

angular
  .module('urbanApp')
  .controller('CreateStockOrders', ['$scope', '$http', '$state', 'Session', 'colFilters', 'Service', CreateStockOrders]);
