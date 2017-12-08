'use strict';

function StockTransferPOP($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams) {

  var vm = this;
  vm.state_data = "";
  vm.service = Service;

  if($stateParams.data){
     vm.state_data = $stateParams.data;
  }

  vm.pop_data = {};
  var empty_data = {data: [{wms_code: "", order_quantity: "", price: ""}], warehouse_name: ""};
  angular.copy(empty_data, vm.pop_data);
  if(vm.state_data)  {

    angular.copy(JSON.parse(vm.state_data), vm.pop_data.data);
  } else {
    $state.go($state.$current.parent);
  }

  vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

  vm.update_data = update_data;
  function update_data(index, data, last) {
    console.log(data);
    if (last) {
      vm.pop_data.data.push({wms_code: "", order_quantity: "", price: ""});
    } else {
      vm.pop_data.data.splice(index,1);
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
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      Service.apiCall("confirm_st/", "POST", elem, true).then(function(data){
        if(data.message) {
          if(data.data == 'Confirmed Successfully') {
            vm.service.pop_msg(data.data);
          } else {
            vm.service.pop_msg(data.data);
          }
        }
      });
    }
  }

  vm.get_product_data = function(item, sku_data, index) {

      check_exist(sku_data).then(function(data){
        if(data) {
          var elem = $.param({'sku_code': item});
          vm.service.apiCall('get_material_codes/', 'POST', {'sku_code': item}).then(function(data){
            if(data.message) {
              sku_data.sub_data = data.data.materials;
              sku_data.product_description = 1;
              sku_data.description = data.data.product.description;
            }
          });
        }
      });
    }

}

angular
  .module('urbanApp')
  .controller('StockTransferPOP', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', StockTransferPOP]);
