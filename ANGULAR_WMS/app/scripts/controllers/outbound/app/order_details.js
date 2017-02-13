'use strict';

function AppOrderDetails($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams) {

  console.log($state);
  console.log($stateParams);
  var vm = this;

  vm.order_id = ""
  if($stateParams.orderId) {
    vm.order_id = $stateParams.orderId;
  }
  vm.loading = true;
  vm.order_details = {}
  vm.open_order_detail = function(order){

    vm.order_details = {}
    Service.apiCall("get_customer_order_detail/?order_id="+vm.order_id).then(function(data){
      if(data.message) {

        console.log(data.data);
        angular.copy(data.data, vm.order_details);
        vm.order_details['order'] = order;
      }
      vm.loading = false;
    })
  }
  vm.open_order_detail();
}

angular
  .module('urbanApp')
  .controller('AppOrderDetails', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', AppOrderDetails]);
