'use strict';

function AppMyOrders($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth) {

  var vm = this;

  //you orders
  vm.you_orders = false;
  vm.orders_loading = false
  vm.order_data = {}
  vm.get_orders = function(){

    vm.orders_loading = true;
    vm.order_data = {}
    Service.apiCall("get_customer_orders/").then(function(data){
      if(data.message) {

        console.log(data.data);
        angular.copy(data.data, vm.order_data);
      }
      vm.orders_loading = false;
    })
  }
  vm.get_orders();
}

angular
  .module('urbanApp')
  .controller('AppMyOrders', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', AppMyOrders]);
