'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CorporateMapping',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
  var vm = this;
  vm.service = Service;

  vm.distributors = ['Distributor-1','Distributor-2','Distributor-3','Distributor-4'];
  vm.resellers = ['Reseller-1','Reseller-2','Reseller-3','Reseller-4'];
  vm.corporates = ['Corporate-1','Corporate-2','Corporate-3','Corporate-4','Corporate-5','Corporate-6','Corporate-7'];

  vm.checked_items = {};

  angular.forEach(vm.corporates, function(item){
    vm.checked_items[item] = false;
  });

  vm.base = function(){

    vm.title = "Reseller Corporate Mapping";

    vm.service.apiCall("get_distributors/").then(function(data){
      if(data.message) {

        vm.distributors = data.data.distributors;
      }
    });
  }

  vm.base();

  vm.get_resellers = function(){

    vm.service.apiCall("get_resellers/").then(function(data){
      if(data.message) {

        vm.resellers = data.data.resellers;
      }
    });
  }

  vm.get_corporates = function(){

    vm.service.apiCall("get_corporates/").then(function(data){
      if(data.message) {

        vm.corporates = data.data.corporates;
      }
    });
  }

  vm.submit = submit;
  function submit(data) {
    if (data.$valid) {
      
      vm.service.apiCall("corporate_mapping_data/").then(function(data){
        if(data.message) {

          // vm.corporates = data.data.corporates;
        }
      });
    } else {

      vm.service.pop_msg('Please fill required fields');
    }
  }

}

