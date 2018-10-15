;(function(){

'use strict';

function Notifications($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams, $modal, Data) {

  var vm = this;
  vm.service = Service;
  var req_data = {}
  vm.load_notifications = function(){
    Service.apiCall("list_notifications/", "GET", req_data).then(function(resp){
      if(resp.message){
        vm.notifications = resp.data.data;
      } else {

      }

    });
  }
  vm.load_notifications();

  vm.mark_as_read = function(push_id, is_all_read){
    var req_data = {'push_id': push_id, 'is_all_read': is_all_read};
    Service.apiCall("make_notifications_read/", "POST", req_data).then(function(resp){
      if(resp.message){
        Service.showNoty(resp.data.msg);
        vm.load_notifications();
        if ($scope.user.notification_count) {
          $scope.user.notification_count = Number($scope.user.notification_count) - 1;
        }

      }
    });
  }

  vm.delete_notification = function(notification_id){
    var req_data = {'notification_id': notification_id};
    Service.apiCall("delete_notification/", "POST", req_data).then(function(resp){
      if(resp.message){
        Service.showNoty(resp.data.msg);
        vm.load_notifications();
      }
    });
  }

}
angular
  .module('urbanApp')
  .controller('Notifications', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout',
                  'Auth', '$stateParams', '$modal', 'Data', Notifications]);
})();
