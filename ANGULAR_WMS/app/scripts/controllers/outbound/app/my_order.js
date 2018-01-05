;(function(){

'use strict';

function AppMyOrders($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, Data) {

  var vm = this;

  vm.your_orders = ($state.params.state == "orders")? true: false;
  vm.status = ($state.params.state == "orders")? "orders": "enquiry";

  var url = "get_customer_orders/";
  if (!vm.your_orders) {
    url = "get_enquiry_data/";
  }

  //you orders
  vm.you_orders = false;
  vm.orders_loading = false;
  vm.order_data = {data: []};
  vm.index = '';
  vm.show_no_data = false;
  vm.get_orders = function(key){

    vm.orders_loading = true;

    vm.index = vm.order_data.data.length  + ':' + (vm.order_data.data.length + 20)
    var data = {index: vm.index}
    Service.apiCall(url, 'GET', data).then(function(data){
      if(data.message) {

        console.log(data.data);
        vm.order_data.data = vm.order_data.data.concat(data.data.data);
        Data[key] = vm.order_data.data;
        if(data.data.data.length == 0) {
          vm.show_no_data = true
        }
      }
      vm.orders_loading = false;
    })
  }

  if (vm.your_orders && Data.my_orders.length == 0) {

    vm.get_orders('my_orders');
  } else if (!vm.your_orders && Data.enquiry_orders.length == 0) {

    vm.get_orders('enquiry_orders');
  } else if (vm.your_orders) {

    vm.order_data.data = Data.my_orders;
  } else if (!vm.your_orders) {

    vm.order_data.data = Data.enquiry_orders;
  }

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

  vm.moveToCart = function(order, index, event) {

    event.stopPropagation();

    Service.apiCall("move_enquiry_to_order/?enquiry_id="+order.order_id).then(function(data) {

      if(data.message) {

        console.log(data.data);
        if(data.data == 'Success') {

          vm.order_data.data.splice(index, 1);
          Data.enquiry_orders.splice(index, 1);
          Service.showNoty('Successfully Moved To Cart');
          $state.go('user.App.Cart');
        } else {

          Service.showNoty(data.data, 'warning');
        }
      } else {

        Service.showNoty('Something Went Wrong', 'warning');
      }
    });
  }

  vm.order_cancel = function(order, index, event) {
    event.stopPropagation();
    Service.apiCall("order_cancel/?order_id="+order.order_id).then(function(data) {
      if(data.message) {
        console.log(data.data);
        if(data.data == 'Success') {
          vm.order_data.data.splice(index, 1);
          Service.showNoty('Successfully Cancelled the Order');
        } else {
          Service.showNoty(data.data, 'warning');
        }
      } else {
        Service.showNoty('Something Went Wrong', 'warning');
      }
    });
  }
}

angular
  .module('urbanApp')
  .controller('AppMyOrders', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', 'Data', AppMyOrders]);

})();
