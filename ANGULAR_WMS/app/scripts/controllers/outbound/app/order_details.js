;(function(){

'use strict';

function AppOrderDetails($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams) {

  console.log($state);
  console.log($stateParams);
  var vm = this;
  vm.service = Service;

  vm.order_id = "";
  vm.status = "";
  if($stateParams.orderId && $stateParams.state) {
    vm.order_id = $stateParams.orderId;
    vm.status = $stateParams.state;
  } else {
    $state.go("user.App.MyOrders");
  }

  var url = "get_customer_order_detail/?order_id=";
  if(vm.status != "orders") {
    url = "get_customer_enquiry_detail/?enquiry_id=";
  }
  vm.loading = true;
  vm.order_details = {}
  vm.open_order_detail = function(order){

    vm.order_details = {}
    Service.apiCall(url+vm.order_id).then(function(data){
      if(data.message) {

        console.log(data.data);
        vm.order_details = {}
        vm.order_details = data.data;
        vm.order_details['order'] = order;
      }
      vm.loading = false;
    })
  }
  vm.open_order_detail();

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
  .controller('AppOrderDetails', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', AppOrderDetails]);

})();
