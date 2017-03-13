'use strict';

function AppStyle($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams) {

  console.log($state);
  console.log($stateParams);
  var vm = this;
  vm.styleId = "";
  vm.service = Service;
  if($stateParams.styleId){
    vm.styleId = $stateParams.styleId;
  }

  vm.style_open = false;
  vm.stock_quantity = 0;
  vm.style_data = [];
  vm.open_style = function() {

    vm.style_data = [];
    Service.apiCall("get_sku_variants/", "GET", {sku_class:vm.styleId, customer_id: Session.userId, is_catalog: true}).then(function(data) {

      if(data.message) {
        vm.style_open = true;
        vm.check_stock=true;
        vm.style_data = data.data.data;
        if(vm.style_data.length > 0) {
            vm.stock_quantity = 0;
            angular.forEach(vm.style_data, function(record){
              vm.stock_quantity = vm.stock_quantity + Number(record.physical_stock);
            })
        }
      }
    });
    vm.style_total_quantity = 0;
  }
  vm.open_style()

  vm.style_total_quantity = 0;
  vm.change_style_quantity = function(data){
    vm.style_total_quantity = 0;
    angular.forEach(data, function(record){

      if(record.quantity) {
        vm.style_total_quantity += Number(record.quantity);
      }
    })
  }

  vm.make_empty = function(){

    $timeout(function() {
      angular.forEach(vm.style_data, function(record){
        record.quantity = "";
      })
    }, 1000);
    vm.style_total_quantity = 0;
  }

  var empty_data = {data: []}

  vm.add_to_cart = function(style_data) {
    if(vm.style_total_quantity != 0) {
      var send = []
      angular.forEach(style_data, function(data){

        if (data['quantity']) {
          var temp = {sku_id: data.wms_code, quantity: Number(data.quantity), invoice_amount: data.price*Number(data.quantity), price: data.price, tax: vm.tax, image_url: data.image_url}
          temp['total_amount'] = ((temp.invoice_amount/100)*vm.tax)+temp.invoice_amount;
          send.push(temp)
        }
      });
      vm.insert_customer_cart_data(send);
      vm.service.showNoty("Succesfully Added to Cart", "success", "bottomRight");
    } else {
      vm.service.showNoty("Please Enter Quantity", "success", "bottomRight");
    }
  }

  vm.insert_customer_cart_data = function(data){

    var send = JSON.stringify(data);
    vm.service.apiCall('insert_customer_cart_data/?data='+send).then(function(data){
       console.log(data);
    })
  }
  vm.tax = 0
  vm.get_create_order_data = function(){
    vm.service.apiCall("create_orders_data/").then(function(data){

      if(data.message) {
        vm.tax =  data.data.taxes['VAT'];
      }
    })
  }
  vm.get_create_order_data();

}

angular
  .module('urbanApp')
  .controller('AppStyle', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', AppStyle]);
