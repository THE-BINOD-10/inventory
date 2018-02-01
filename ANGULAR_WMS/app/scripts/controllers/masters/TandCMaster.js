'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('TandCMaster',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.service = Service;
  vm.items = [];

  vm.model_data = {};

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
    angular.copy(term, send);
    send['term_type'] = 'sales';
    var data = $.param(send);
    Service.apiCall("insert_update_terms/", 'POST', send).then(function(data){
      if(data.data.message) {
        if(data.data.message == 'Added Successfully') {
          vm.items.push({'id': data.data.data.id, 'terms': send['terms']});
          vm.new_terms = '';
          vm.new_tc_status = false;
          vm.service.showNoty(data.data.message);
        }
        else if(data.data.message == 'Updated Successfully'){
          term.edit_status = false;
        } else {
          vm.service.showNoty(data.data.message);
        }
      }
    });
  }

    vm.deleteTC = function(term, index) {
    var send = {}
    angular.copy(term, send);
    send['term_type'] = 'sales';
    var data = $.param(send);
    Service.apiCall("delete_terms/", 'POST', send).then(function(data){
      if(data.data.message) {
        if(data.data.message == 'Deleted Successfully'){
          vm.service.showNoty(data.data.message);
          vm.items.splice(index, 1);
        } else {
          vm.service.showNoty(data.data.message);
        }
      }
    });
  }
}

