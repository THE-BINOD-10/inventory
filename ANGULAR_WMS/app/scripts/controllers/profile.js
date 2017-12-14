;(function(){

'use strict';

var app = angular.module('urbanApp', [''])
app.controller('Profile',['$scope', 'Session', 'Service', '$modal', Profile]);

function Profile($scope, Session, Service, $modal) {

  var vm = this;
  vm.edit_form = false;
  vm.model_data = {};

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
