'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PaymentTracker',['$scope', '$http', '$state', 'Session', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, Session, Service) {

  var vm = this;
  vm.service = Service;
  
  var empty_data = { payments: [{
                        channel: "Offline",
                        customer_name: "kannarao",
                        payment_received: 1000,
                        payment_receivable: 500,
                        data: [
                          {
                          order_id: "12345",
                          inv_amount: 1000,
                          pay: 500,
                          account: "Credit Card",
                          order_status: "Generte Picklist",
                          }
                        ]
                     }]
                   }

  vm.payment_data = {};
  angular.copy(empty_data, vm.payment_data);

  vm.model_data = {search:"Order Created",filters: ["Order Created", "Partially Invoiced", "Invoiced"]}

  vm.searching = function(data) {

    console.log(data);
  }

  vm.get_payment_tracker_data = function() {
    vm.service.apiCall("payment_tracker/","GET", {filter: vm.model_data.search}).then(function(data){

      if(data.message) {

        vm.payment_data.payments = data.data.data;
      }
    })
  }
  vm.get_payment_tracker_data();

  vm.get_customer_orders = function(payment) {

   console.log(payment) ;
    if(!(payment["data"])) {
      var send = {id:payment.customer_id, name:payment.customer_name, channel: payment.channel}
      vm.service.apiCall("get_customer_payment_tracker/", "GET", send).then(function(data){
  
        if(data.message) {
          payment["data"] = data.data.data;
        }
      })
    }
  }

}
