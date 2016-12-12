'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('TrackOrders',['$scope', '$http', '$state', 'Session', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, Session, Service) {

  var vm = this;
  vm.service = Service;
  
  var empty_data = { orders: [{
                        index: "",
                        stage: {},
                        order: 1550,
                        invoice: 0,
                        order_data: [
                          {
                          image_url: "",
                          name: "",
                          order_date: "",
                          sku_desc: "",
                          price: 0,
                          quantity: 1,
                          order: "",
                          sku_code: ""
                          }
                        ]
                     }]
                   }

  angular.copy(empty_data, vm.order_data);
  vm.send = {order_id: ''}
  vm.get_orders = function(id, search, first){
    var send = {};
    if (vm.send.order_id) {
      send["order_id"] = vm.send.order_id;
    }
    if(id) {
      send["orders"] = id;
      send["search"] = search;
    }
    if(first) {
      vm.order_data = {orders: []}
    }
    vm.service.apiCall('track_orders/', 'GET', send).then(function(data){

      if(data.message) {
        angular.forEach(data.data.orders, function(record) {
          vm.order_data.orders.push(record);
        })
      }
      vm.scroll_data = true;
    })
  }
  vm.get_orders(false, false, true);

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
