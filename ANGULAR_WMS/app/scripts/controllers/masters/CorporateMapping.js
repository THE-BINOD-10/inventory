'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CorporateMapping',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
  var vm = this;
  vm.service = Service;
  vm.session = Session;

  vm.distributors = [];
  vm.resellers = [];
  vm.total_items = {};
  vm.reseller = '';
  vm.corp_dict = {};

  vm.get_corporates = function(res){
    var send = {'reseller': res};
    vm.service.apiCall("get_corporates/", 'GET', send).then(function(data){
      if(data.message) {
        
        if (data.data.checked_corporates) {
          vm.corp_dict = {};

          angular.forEach(data.data.checked_corporates, function(row){
            vm.corp_dict[row.corporate_id] = row.status;
          });
        }

        vm.corporates = data.data.data;
      }
      vm.def_checked_value();
    });
  }

  vm.def_checked_value = function(){

    angular.forEach(vm.corporates, function(item){
      if (vm.corp_dict[item.corporate_id]) {
        vm.total_items[item.corporate_id] = true;
      } else {
        vm.total_items[item.corporate_id] = false;
      }
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

  vm.selected = {};
  vm.get_corporate_data = function(item, model, label, event) {
    vm.corporates = [];
    vm.search_corporate = vm.service.search_key;
    vm.corporates = vm.service.search_res;
  }

  vm.submit = submit;
  function submit(data) {
    if (vm.reseller) {
      var checked_items = [];
      var send = $("#form").serializeArray();

      angular.forEach(vm.total_items, function(value, key){
        if (vm.total_items[key]) {
          checked_items.push(key);
        }
      });
      
      send.push({'name':'checked_items', 'value': checked_items});
      vm.service.apiCall("corporate_mapping_data/", 'POST', send).then(function(data){
        if(data.message) {

          vm.service.showNoty(data.data.success);
        }
      });
    } else {

      vm.service.showNoty('Please select distributor and reseller required fields');
    }
  }

}

