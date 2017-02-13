'use strict';

function AppStyle($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams) {

  console.log($state);
  console.log($stateParams);
  var vm = this;
  vm.styleId = "";
  if($stateParams.styleId){
    vm.styleId = $stateParams.styleId;
  }

  vm.style_open = false;
  vm.stock_quantity = 0;
  vm.style_data = [];
  vm.open_style = function() {

    vm.style_data = [];
    Service.apiCall("get_sku_variants/", "GET", {sku_class:vm.styleId, is_catalog: true}).then(function(data) {

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
}

angular
  .module('urbanApp')
  .controller('AppStyle', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', AppStyle]);
