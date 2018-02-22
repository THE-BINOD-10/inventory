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
  if(vm.status == "orders") {
    url = "get_customer_enquiry_detail/?enquiry_id=";
  } else if (vm.status == "manual_enquiry") {
    url = "get_manual_enquiry_detail/?user_id="+Session.userId+"&enquiry_id=";
  }
  vm.loading = true;
  vm.order_details = {}
  vm.open_order_detail = function(){

    vm.order_details = {}
    Service.apiCall(url+vm.order_id).then(function(data){
      if(data.message) {

        console.log(data.data);
        vm.order_details = {}
        vm.order_details = data.data;
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

  vm.date = new Date()
  vm.disable_btn = false;
  vm.edit = function(form){
    if(form.$invalid) {
      Service.showNoty('Please fill required fields');
      return false;
    }
    vm.disable_btn = true;
    vm.model_data['user_id'] = Session.userId;
    vm.model_data['enquiry_id'] = vm.order_details.order.enquiry_id;
    Service.apiCall('save_manual_enquiry_data/', 'POST', vm.model_data).then(function(data) {
      if (data.message) {
        if (data.data == 'Success') {
          var temp = {};
          angular.copy(vm.model_data, temp);
          temp['username'] = Session.userName;
          temp['date'] = vm.date.getFullYear()+'-'+vm.date.getMonth()+'-'+vm.date.getDate();
          vm.order_details.data.push(temp)
          vm.model_data.ask_price = '';
          vm.model_data.extended_date = '';
          vm.model_data.remarks = '';
        }
        Service.showNoty(data.data);
      } else {
        Service.showNoty('Something went wrong');
      }
      vm.disable_btn = false;
    });
  }
}

angular
  .module('urbanApp')
  .controller('AppOrderDetails', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', AppOrderDetails]);

})();
