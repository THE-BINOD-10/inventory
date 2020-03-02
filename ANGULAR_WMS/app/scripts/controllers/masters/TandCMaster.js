'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('TandCMaster',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$modal', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $modal, Data) {

  var vm = this;
  vm.service = Service;
  vm.items = [];
  vm.markup_hide = true;
  vm.markuptext = '';
  vm.model_data = {};
  vm.btn_disable = false;
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

  vm.save_po_terms = function(term) {
    var send = {};
    vm.btn_disable = true;
    angular.copy(term, send);
    send['field_type'] = 'terms_conditions';
    var data = $.param(send);
    Service.apiCall("insert_po_terms/", 'POST', send).then(function(data){
      if(data.data.message || data.data.data) {
        if(data.data.message == 'Added Successfully') {
          vm.service.showNoty(data.data.message);
        } else if(data.data.message == 'Updated Successfully'){
          vm.service.showNoty(data.data.message);
        } else if(data.data.data || send['get_data'] == 'poTerms') {
          vm.po_iframe(data.data.data)
        } else {
          vm.service.showNoty(data.data.message);
        }
      }
      vm.btn_disable = false;
    });
  }

  vm.po_iframe = function(val){
    var mod_data = val;
    var modalInstance = $modal.open({
      templateUrl: 'views/masters/TandCMaster/view_purchase_order_tc.html',
      controller: 'poTermsConditions',
      controllerAs: 'pop',
      size: 'lg',
      backdrop: 'static',
      keyboard: false,
      resolve: {
        items: function () {
          return mod_data;
        }
      }
    });
    modalInstance.result.then(function (selectedItem) {
    });
  }
  vm.saveTermsConditions = function () {
    if ($('#markup').text()) {
      var poTerms = $('#markup').text().toString();
      vm.save_po_terms({'text_field': poTerms})
    } else {
      vm.save_po_terms({'text_field': ''})
    }
  }
}

function poTermsConditions($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items, Data) {
  var vm = this;
  vm.service = Service;
  vm.loader = true;
  vm.state_data = items;
  $timeout(function () {
    $("#poTerms").html(vm.state_data)
    vm.loader = false;
  }, 1000);
    vm.ok = function () {
      $modalInstance.close("close");
    };
  }
angular
  .module('urbanApp')
  .controller('poTermsConditions', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', poTermsConditions]);
