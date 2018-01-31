'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('TandCMaster',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.servie = Service;
  vm.items = [];

  var empty_data = {seller: "", sku_code: "", margin: ""};
  vm.model_data = {};

  vm.base = function() {

    vm.title = "Add Mapping";
    vm.update = false;
    angular.copy(empty_data, vm.model_data);
  }
  vm.base();

  vm.close = function() {

    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.SellerMarginMapping');
  }

  vm.sellers = [];
  vm.get_data = function() {

    Service.apiCall("get_terms_and_conditions/?tc_type=sales").then(function(data){
      if(data.message) {

        vm.items = data.data.tc_list;
      }
    });
  }

  vm.get_data();

  vm.saveTC = function(term) {
    var send = {}
    angular.copy(term, send)
    var data = $.param(send);
    Service.apiCall("confirm_terms_and_conditions/", 'POST', send).then(function(data){
      if(data.message) {
        if(data.data == 'Added Successfully' || data.data == 'Updated Successfully') {
          vm.service.refresh(vm.dtInstance);
          vm.close();
        } else {
          vm.service.pop_msg(data.data);
        }
      }
    });
  }
}

