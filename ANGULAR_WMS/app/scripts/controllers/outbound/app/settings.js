;(function(){

'use strict';

function settingsForm($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams, $modal, Data) {

  var vm = this;
  vm.service = Service;
  vm.session = Session;
  vm.title = 'Customer Profile';
  vm.first_name = vm.session.user_profile.first_name;
  vm.email = vm.session.user_profile.email;
  vm.user_id = vm.session.userId;
  vm.is_portal_lite = Session.roles.permissions.is_portal_lite;
  vm.permissions = Session.roles.permissions

  vm.base = function(){
    if(vm.permissions.customer_portal_prefered_view) {
      vm.viewType = vm.permissions.customer_portal_prefered_view
    }else if (vm.permissions.customer_portal_prefered_view == '') {
      vm.viewType = 'None'
    }
    vm.settingsType = ['None', 'Brand View', 'Category View', 'Product View']
  }
  vm.base();
  vm.change_config = function(switch_value, switch_name) {
    Service.apiCall("switches/?"+switch_name+"="+String(switch_value)).then(function(data){
      if(data.data == 'Success') {
        $window.location.reload();
      } else {
        Service.showNoty("Something Went Wrong", "danger")
      }
    });
  }
}

angular
  .module('urbanApp')
    .controller('settingsForm', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', '$modal', 'Data', settingsForm]);
})();
