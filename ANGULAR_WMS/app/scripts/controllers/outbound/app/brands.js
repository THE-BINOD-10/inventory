'use strict';

function AppBrands($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams) {

  console.log($state);
  console.log($stateParams);
  var vm = this;

  vm.brands_images = {'6 Degree': 'six-degrees.jpg', 'AWG (All Weather Gear)': 'awg.jpg', 'BIO WASH': 'bio-wash.jpg',
    'Scala': 'scala.jpg','Scott International': 'scott.jpg', 'Scott Young': 'scott-young.jpg', 'Spark': 'spark.jpg',
    'Star - 11': 'star-11.jpg','Super Sigma': 'super-sigma-dryfit.jpg', 'Sulphur Cotton': 'sulphur-cottnt.jpg', 'Sulphur Dryfit': 'sulphur-dryfit.jpg', 'Spring': 'spring.jpg', '100% Cotton': '100cotton.jpg', 'Sprint': 'sprint.jpg', 'Supreme': 'supreme.jpg', 'Sport': 'sport.jpg'}

  //Order type
  vm.order_type = false;
  vm.order_type_value = "Offline"

  if($stateParams.through){
    vm.order_type_value = $stateParams.through;
  }

  if (vm.order_type_value == "Offline") {

    vm.order_type = false;
  } else {

    vm.order_type = true;
  }

  vm.get_order_type = function() {
      
    if(vm.order_type) {
      vm.order_type_value = "Online"
    } else {
      vm.order_type_value = "Offline";
    }
  }

  vm.brands = {};
  vm.get_brands = function() {

    vm.get_order_type();
    $stateParams.through = vm.order_type_value;
    var data = {is_catalog: true, sale_through: vm.order_type_value};
    Service.apiCall("get_sku_categories/", "GET",data).then(function(data){

      if(data.message) {

        vm.brands = data.data.brands;
      }
    })
  }

  vm.get_brands();

}

angular
  .module('urbanApp')
  .controller('AppBrands', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', AppBrands]);
