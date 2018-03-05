'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CorporateMapping',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
  var vm = this;
  vm.service = Service;

  vm.distributors = [];
  vm.resellers = [];
  vm.checked_items = {};
  vm.reseller = '';

  vm.get_corporates = function(res){
    var send = {'reseller': res};
    vm.service.apiCall("get_corporates/", 'GET', send).then(function(data){
      if(data.message) {

        vm.corporates = data.data.data;
      }
    });

    angular.forEach(vm.corporates, function(item){
      vm.checked_items[item.corporate_id] = false;
    });
  }

  vm.base = function(){

    vm.title = "Reseller Corporate Mapping";
    var res = 0;
    vm.get_corporates(res);
    vm.service.apiCall("get_distributors/").then(function(data){
      if(data.message) {

        vm.distributors = data.data.data;
      }
    });
  }

  vm.base();

  vm.get_resellers = function(dist){
    var send = {'distributor': dist};
    vm.service.apiCall("get_resellers/", 'GET', send).then(function(data){
      if(data.message) {

        vm.resellers = data.data.data;
      }
    });
  }

  vm.submit = submit;
  function submit(data) {
    if (vm.reseller) {
      var send = $("#form").serializeArray();
      angular.forEach(vm.checked_items, function(row){
        if (row) {
          
        }
      });

      vm.service.apiCall("corporate_mapping_data/", 'POST', send).then(function(data){
        if(data.message) {

          // vm.corporates = data.data.corporates;
        }
      });
    } else {

      vm.service.showNoty('Please select distributor and reseller required fields');
    }
  }

}

