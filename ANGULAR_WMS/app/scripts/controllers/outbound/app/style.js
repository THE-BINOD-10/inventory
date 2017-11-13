'use strict';

function AppStyle($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams) {

  console.log($state);
  console.log($stateParams);
  var vm = this;
  vm.styleId = "";
  vm.tax_type = Session.roles.tax_type;
  vm.service = Service;
  if($stateParams.styleId){
    vm.styleId = $stateParams.styleId;
  }

  vm.style_headers = {};
  vm.style_detail_hd = [];
  if (Session.roles.permissions["style_headers"]) {
    vm.en_style_headers = Session.roles.permissions["style_headers"].split(",");
  } else {
    vm.en_style_headers = [];
  }
  if(vm.en_style_headers.length == 0) {

    vm.en_style_headers = ["wms_code", "sku_desc"]
  }

  vm.style_open = false;
  vm.stock_quantity = 0;
  vm.style_data = [];
  vm.style_total_counts = {};
  vm.open_style = function() {

    vm.style_data = [];
    Service.apiCall("get_sku_variants/", "GET", {sku_class:vm.styleId, customer_id: Session.userId, is_catalog: true}).then(function(data) {

      if(data.message) {
        vm.style_open = true;
        vm.check_stock=true;
        vm.style_data = data.data.data;
        vm.style_total_counts = data.data.total_qty;
        if(vm.style_data.length > 0) {
            vm.stock_quantity = 0;
            angular.forEach(vm.style_data, function(record){
              vm.stock_quantity = vm.stock_quantity + Number(record.physical_stock) + Number(record.all_quantity);
            })
        }
        vm.style_headers = data.data.style_headers;
        vm.style_detail_hd = Object.keys(vm.style_headers);
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
  /*vm.get_create_order_data = function(){
    vm.service.apiCall("create_orders_data/").then(function(data){

      if(data.message) {
          if (vm.tax_type == '' || (! data.data.taxes[vm.tax_type])) {
            vm.tax =  data.data.taxes['DEFAULT'];
          }
          else {
            vm.tax =  data.data.taxes[vm.tax_type];
          }
      }
    })
  }
  vm.get_create_order_data();*/

  vm.includeDesktopTemplate = false;
  vm.includeMobileTemplate = false;
  vm.screenSize = function() {

    var screenWidth = $window.innerWidth;

    if (screenWidth < 768){

      vm.includeMobileTemplate = true;
      vm.includeDesktopTemplate = false;
    }else{

      vm.includeDesktopTemplate = true;
      vm.includeMobileTemplate = false;
    }
  }
  vm.screenSize();
  angular.element($window).bind('resize', function(){

    vm.screenSize();
  });
}

angular
  .module('urbanApp')
  .controller('AppStyle', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', AppStyle]);
