'use strict';

function AppMyOrders($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth) {

  var vm = this;

  //you orders
  vm.you_orders = false;
  vm.orders_loading = false
  vm.order_data = {data: []}
  vm.index = ''
  vm.show_no_data = false
  vm.get_orders = function(){

    vm.orders_loading = true;

    vm.index = vm.order_data.data.length  + ':' + (vm.order_data.data.length + 20)
    var data = {index: vm.index}
    Service.apiCall("get_customer_orders/", 'GET', data).then(function(data){
      if(data.message) {

        console.log(data.data);
        vm.order_data.data = vm.order_data.data.concat(data.data.data)
        if(data.data.data.length == 0) {
          vm.show_no_data = true
        }
      }
      vm.orders_loading = false;
    })
  }
  vm.get_orders();

  // Scrolling Event Function
  vm.scroll = function(e) {
    console.log("scroll")
    if($(".your_orders:visible").length && !vm.orders_loading && !vm.show_no_data) {
        vm.get_orders();
    }
  }

  vm.getStatus = function(order_qty, pick_qty) {

    if(pick_qty == 0) {

      return "Open";
    } else if ((order_qty - pick_qty) == 0) {

      return "Dispatched";
    } else {

      return "Partially Dispatched";
    }
  }
}

angular
  .module('urbanApp')
  .controller('AppMyOrders', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', AppMyOrders]);
