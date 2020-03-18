;(function(){

'use strict';

var app = angular.module('urbanApp', [''])
app.controller('Profile',['$scope', 'Session', 'Service', '$modal', Profile]);

function Profile($scope, Session, Service, $modal) {

  var vm = this;
  vm.edit_form = false;
  vm.model_data = {};
  vm.model_shipment_data = {};
  vm.host = Session.host;
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

  vm.base = function(){
    vm.orig_model_data = {};
    Service.apiCall('get_user_profile_data/').then(function(data){
      if(data.message) {
        data.data.data.sign_signature ? data.data.data['sign_signature'] = (Session.host+data.data.data.sign_signature).toString() : data.data.data['sign_signature'] = 'Image Not Available';
        angular.copy(data.data.data, vm.model_data);
        angular.copy(data.data.data, vm.orig_model_data);
      }
    });
  }
  vm.base();
  vm.reload_shipment_address= function() {
    vm.model_shipment_data = {}
    Service.apiCall('get_user_profile_shipment_addresses/').then(function(data){
      if(data.message) {
        angular.copy(data.data, vm.model_shipment_data);
      }
    });
  }
  vm.back = function() {

    angular.copy(vm.orig_model_data, vm.model_data);
  }
  vm.model_data.sign_signature = "";
  $scope.$on("fileSelected", function (event, args) {
    $scope.$apply(function () {
      vm.model_data.sign_signature = args.file;
    });
  });
  vm.process = false;
  vm.updateProfile = function(form) {
    if(form.$invalid) {
      return false;
    }
    vm.process = true;
    var formData = new FormData()
    var elem = angular.element($('form'));
    elem = elem[0];
    elem = $(elem).serializeArray();
    (vm.model_data.sign_signature) ? formData.append('signature_logo', vm.model_data.sign_signature) : formData.append('signature_logo', '');
    $.each(elem, function(i, val) {
        formData.append(val.name, val.value);
    });
    $.ajax({url: Session.url+'update_profile_data/',
      data: formData,
      method: 'POST',
      processData : false,
      contentType : false,
      xhrFields: {
        withCredentials: true
      },
      'success': function(data) {
        var data = JSON.parse(data)
        if(data.data == 'Success') {
          vm.edit_form = false;
          vm.base();
          Service.showNoty('Successfully Updated');
        }
        vm.process = false;
      },
      'error': function(data) {
        Service.showNoty('Something Went Wrong', 'warning');
        vm.process = false;
      }
    });
  }
  vm.emptyData = function () {
    vm.model_data.address_title = vm.model_data.address_name = vm.model_data.address_mobile_number = vm.model_data.address_pincode = vm.model_data.address_shipment = '';
  }
  vm.updateShipmentAddress = function() {
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
