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
                          Account: "Credit Card",
                          order_status: "Generte Picklist",
                          }
                        ]
                     }]
                   }

  vm.payment_data = {};
  angular.copy(empty_data, vm.payment_data);

  vm.searching = function(data) {

    console.log(data);
  }


  vm.scroll_data = true;
  $scope.$on('scroll-bottom', function(event){
    console.log("scroll")
    if($("#track_orders:visible").length && vm.scroll_data) {

      vm.scroll_data = false;
      var index = vm.order_data.orders.length-1;
      var id = vm.order_data.orders[index].index;
      vm.get_orders(id, true)
    }
  })
}
