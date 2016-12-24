'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PaymentTracker',['$scope', '$http', '$state', 'Session', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, Session, Service) {

  var vm = this;
  vm.service = Service;
  
  var empty_data = { payments: [],
                     total_invoice_amount: "", total_payment_receivable: "", total_payment_received: ""
                   }

  vm.payment_data = {};
  angular.copy(empty_data, vm.payment_data);

  vm.model_data = {search:"All",filters: ["All", "Order Created", "Partially Invoiced", "Invoiced"]}

  vm.searching = function(data) {

    console.log(data);
  }

  vm.get_payment_tracker_data = function() {
    vm.service.apiCall("payment_tracker/","GET", {filter: vm.model_data.search}).then(function(data){

      if(data.message) {

        angular.copy(data.data, vm.payment_data);
        vm.payment_data.payments = data.data.data;
      }
    })
  }
  vm.get_payment_tracker_data();

  vm.get_customer_orders = function(payment) {

   console.log(payment) ;
    if(!(payment["data"])) {
      var send = {id:payment.customer_id, name:payment.customer_name, channel: payment.channel, filter: vm.model_data.search}
      vm.service.apiCall("get_customer_payment_tracker/", "GET", send).then(function(data){
  
        if(data.message) {
          payment["data"] = data.data.data;
        }
      })
    }
  }

  //Upadate payment popup
  vm.order_data = {}
  vm.open_order_update = function() {

    $state.go("app.PaymentTracker.UpdateOrder");
  }

  vm.close = function() {
    $state.go("app.PaymentTracker");
  }

  vm.order_update = function(event){

    var temp = event.target;
    var parent = angular.element(temp).parents(".order-edit");
    angular.element(parent).find(".order-update").addClass("hide");
    angular.element(parent).find(".order-save").removeClass("hide");
  }

  vm.order_save = function(event, index1, index2, order, customer){

    var temp = event.target;
    var parent = angular.element(temp).parents(".order-edit");
    var value = $(parent).find("input").val();
    if(value) {
      var data = {order_id: order.order_id, amount: value}
      vm.service.apiCall("update_payment_status/", "GET", data).then(function(data){
        if(data.message) {

          $(parent).find("input").val("");
          angular.element(parent).find(".order-update").removeClass("hide");
          angular.element(parent).find(".order-save").addClass("hide");

          order.receivable = Number(order.receivable) - Number(value);
          order.received = Number(order.received) + Number(value);
          customer.payment_receivable = Number(customer.payment_receivable) - Number(value);
          customer.payment_received = Number(customer.payment_received) + Number(value);
          vm.payment_data.total_payment_receivable = Number(vm.payment_data.total_payment_receivable) - Number(value);
          vm.payment_data.total_payment_received = Number(vm.payment_data.total_payment_received) + Number(value);
          if(order.inv_amount == order.received) {
            customer.data.splice(index1, 1);
          }
          if (customer.payment_received == customer.invoice_amount) {
            vm.payment_data.payments.splice(index2, 1);
          }
        }
      })
    }
  }

  vm.change_amount = function(data) {

    if(Number(data.amount) > data.receivable) {
      data.amount = data.receivable;
    }
  }
}
