;(function(){

'use strict';

var app = angular.module('urbanApp', [''])
app.controller('Profile',['$scope', 'Session', 'Service', '$modal', Profile]);

function Profile($scope, Session, Service, $modal) {

  var vm = this;
  vm.edit_form = false;
  vm.model_data = {};
  vm.model_shipment_data = {}

  vm.changePassword = function() {

    var mod_data = {};
    var modalInstance = $modal.open({
      templateUrl: 'views/profile/change_password.html',
      controller: 'changePassword',
      controllerAs: '$ctrl',
      size: 'md',
      backdrop: 'static',
      keyboard: false,
      resolve: {
        items: function () {
          return mod_data;
        }
      }
    });

    modalInstance.result.then(function (selectedItem) {
      vm.marginData = selectedItem;
    })
  }

  vm.orig_model_data = {};
  Service.apiCall('get_user_profile_data/').then(function(data){

    if(data.message) {

      console.log(data.data);
      angular.copy(data.data.data, vm.model_data);
      angular.copy(data.data.data, vm.orig_model_data);
    }
  });
  vm.reload_shipment_address= function() {
    Service.apiCall('get_user_profile_shipment_addresses/').then(function(data){
      if(data.message) {
        if (data.data == 'null') {
          vm.model_data.empty_div = true
        } else {
          vm.model_data.empty_div = false
          angular.copy(data.data, vm.model_shipment_data);
        }
      }
    });
  }
  vm.back = function() {

    angular.copy(vm.orig_model_data, vm.model_data);
  }

  vm.process = false;
  vm.updateProfile = function(form) {

    if(form.$invalid) {
      return false;
    }
    vm.process = true;
    Service.apiCall('update_profile_data/', 'POST', vm.model_data).then(function(data){

      if(data.message) {
        if(data.data == 'Success') {
          angular.copy(vm.model_data, vm.orig_model_data);
          vm.edit_form = false;
          Service.showNoty('Successfully Updated');
        } else {
          Service.showNoty(data.data);
        }
      }
      vm.process = false;
    });
  }
  vm.emptyData = function () {
    vm.model_data.address_title = vm.model_data.address_name = vm.model_data.address_mobile_number = vm.model_data.address_pincode = vm.model_data.address_shipment = '';
  }
  vm.updateShipmentAddress = function(form) {
    if (vm.model_data.address_title && vm.model_data.address_name && vm.model_data.address_mobile_number && vm.model_data.address_pincode && vm.model_data.address_shipment) {
      Service.apiCall('update_profile_shipment_address/', 'POST', vm.model_data).then(function(data){
        if(data.message) {
          if(data.data == 'Success') {
            vm.emptyData();
            Service.showNoty('Successfully Updated');
          } else {
            Service.showNoty(data.data);
          }
        }
      });
    } else {
      Service.showNoty('Please Enter the required Fields');
    }
  }
}
app.controller('changePassword', function($scope, $modalInstance, items, Service, $state, Session){

  console.log(items);
  var vm = this;

  vm.close = function() {
    $modalInstance.close('close');
  }

  vm.process = false;
  vm.model_data = {old_password: '', new_password: '', retype_password: ''}
  vm.changePassword = function(form){

    if(form.$valid) {

      if(vm.model_data.new_password != vm.model_data.retype_password){
        Service.showNoty('New Password and Retype New Password Should Be Same', 'warning')
        return false;
      }

      vm.process = true;
      Service.apiCall('change_user_password/', 'POST', vm.model_data).then(function(data){

        if(data.message) {

          if(!data.data.msg) {

            Service.showNoty(data.data.data, 'warning');
          } else {
            Service.showNoty(data.data.data);
            vm.close();
            Session.unset();
            $state.go('user.signin');
          }
        } else {

          Service.showNoty('Something went wrong', 'warning');
        }
        vm.process = false;
      })
    }
  }
});

})();
