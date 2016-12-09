'use strict';

function CreateStockOrders($scope, $http, Session, colFilters) {

  $scope.msg = "start";
  var vm = this;
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

  vm.warehouse_list = [];
  $http.get(Session.url+"get_warehouses_list/", {withCredential: true}).success(function(data){
    vm.warehouse_list = data.warehouses;
  })
  vm.bt_disable = false; 
  vm.insert_order_data = function(form) {
    if (vm.model_data.customer_id != "") {
      vm.bt_disable = true;
      console.log(form);
      var elem = angular.element($('form'));
      elem = elem[1];
      elem = $(elem).serializeArray();
      elem = $.param(elem);
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      $http.post(Session.url+"create_stock_transfer/",elem, {withCredential: true}).success(function(data){
        console.log(data);
        if("Confirmed Successfully" == data) {
          angular.copy(empty_data, vm.model_data);
        }
        colFilters.showNoty(data);
        vm.bt_disable = false;
      })
    } else {
      colFilters.showNoty("Fill Required Fields");
    }
  }
}

angular
  .module('urbanApp')
  .controller('CreateStockOrders', ['$scope', '$http', 'Session', 'colFilters', CreateStockOrders]);
