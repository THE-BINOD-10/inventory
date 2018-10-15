;(function(){

'use strict';

function AppMyOrders($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, Data, $modal) {

  var vm = this;
  vm.page_url = $state.href($state.current.name, $state.params, {absolute: true})
  vm.your_orders = $state.params.state;
  vm.status = $state.params.state;
  vm.state_name = $state.current.name;

  var url = "";
  if (vm.your_orders == 'enquiry') {
    url = "get_enquiry_data/";
  } else if (vm.your_orders == 'manual_enquiry') {
    url = "get_manual_enquiry_data/";
  } else {
    url = "get_customer_orders/";
  }

  if (vm.state_name == 'app.inbound.AutoBackOrders') {
    Data.my_orders = [];
  }

  //you orders
  vm.you_orders = false;
  vm.orders_loading = false;
  vm.order_data = {data: []};
  vm.index = '';
  vm.show_no_data = false;
  vm.disable_brands_view = Session.roles.permissions.disable_brands_view;
  vm.date = new Date();
  vm.is_portal_lite = Session.roles.permissions.is_portal_lite;

  vm.get_orders = function(key){

    vm.orders_loading = true;
    vm.index = vm.order_data.data.length  + ':' + (vm.order_data.data.length + 20)
    var data = {index: vm.index, autobackorder: false}
    if(vm.page_url.indexOf('AutoBackOrders') > 0){
      data['autobackorder'] = true;
    }
    Service.apiCall(url, 'GET', data).then(function(data){
      if(data.message) {

        console.log(data.data);
        vm.order_data.data = vm.order_data.data.concat(data.data.data);
        angular.forEach(vm.order_data.data, function(item){
          item['extended_date'] = '';
        });
        vm.show_extend_date = false;

//        Data[key] = vm.order_data.data;
        angular.copy(vm.order_data.data, Data[key])
        if(data.data.data.length == 0) {
          vm.show_no_data = true
        }
      }
      // For testing static data
      // vm.order_data.data = [{corporate_name:"",customer_id:16498,date:"23/01/2018",days_left:-16,extend_status:"pending",order_id:10002,total_inv_amt:0,total_quantity:1}];
      vm.orders_loading = false;
    })
  }

  if (vm.your_orders == 'orders' && Data.my_orders.length == 0) {

    vm.get_orders('my_orders');
  } else if (vm.your_orders == 'enquiry' && Data.enquiry_orders.length == 0) {

    vm.get_orders('enquiry_orders');
  } else if (vm.your_orders == 'manual_enquiry' && Data.manual_orders.length == 0) {

    vm.get_orders('manual_orders');
  } else if (vm.your_orders == 'orders') {

    vm.order_data.data = Data.my_orders;
  } else if (vm.your_orders == 'enquiry') {

    vm.order_data.data = Data.enquiry_orders;
  } else if (vm.your_orders == 'manual_enquiry') {

    vm.order_data.data = Data.manual_orders;
  }

  // Scrolling Event Function
  vm.scroll = function(e) {
    console.log("scroll")
    if(!vm.orders_loading && !vm.show_no_data) {
        vm.get_orders();
    }
  }

  vm.getStatus = function(order_qty, pick_qty, status_) {

    status_ = status_ || ''
    if(status_ == 'Waiting For Approval') {
      return status_
    } else {
        if(pick_qty == 0) {

          return "Open";
        } else if ((order_qty - pick_qty) == 0) {

          return "Dispatched";
        } else {

          return "Partially Dispatched";
        }
    }
  }

  vm.extend_order_date = function(order){
    order['show_extend_date'] = true;
  }

  vm.confirm_to_extend = function(order, form){
    
    if (form.$valid) {
      var send = angular.element($('form'));
          send = send[0];
          send = $(send).serializeArray();

      Service.apiCall('extend_enquiry_date/', 'GET', send).then(function(data) {
        if (data.message) {
          if (data.data == 'Success') {
            order.extend_status = 'pending';
            order.show_extend_date = false;
            Service.showNoty('Your request sent, pleae wait warehouse conformation');
          }
        } else {
          Service.showNoty('Something went wrong');
        }
      });
    } else {
      Service.showNoty('Please fill with extend date');
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
    if(order.intermediate_order) {
        Service.apiCall("intermediate_order_cancel/?order_id="+order.interm_order_id).then(function(data) {
          if(data.message) {
            console.log(data.data);
            if(data.data == 'Success') {
              vm.order_data.data.splice(index, 1);
              Service.showNoty('Successfully Cancelled the Order');
            } else {
              Service.showNoty(data.data, 'warning');
            }
          }
        });
    } else {
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

  vm.open_details = function(data) {

    if (Session.user_profile.request_user_type == 'warehouse_user') {

      var mod_data = {order_id: data['orderId'], url: 'get_customer_order_detail', customer_id: data['customerId']};
      var page_url = window.location.href
      if(page_url.indexOf('AutoBackOrders') > 0){
        mod_data['autobackorder'] = true;
      }
      var modalInstance = $modal.open({
        templateUrl: 'views/inbound/toggle/order_details.html',
        controller: 'EnquiryOrderDetails',
        controllerAs: 'order',
        size: 'lg',
        backdrop: 'static',
        keyboard: false,
        resolve: {
          items: function () {
            return mod_data;
          }
        }
      });
      modalInstance.result.then(function (selectedItem) {
        var data = selectedItem;
      })
    } else {
      $state.go('user.App.OrderDetails', data);
    }
  }
  
}

angular
  .module('urbanApp')
  .controller('AppMyOrders', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', 'Data', '$modal', AppMyOrders]);

})();
