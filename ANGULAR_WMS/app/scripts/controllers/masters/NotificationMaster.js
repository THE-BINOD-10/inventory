'use strict';

angular.module('urbanApp', ['datatables'], ["checklist-model"])
  .controller('NotificationMasterCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
  var vm = this;
  vm.apply_filters = colFilters;
  vm.service = Service;
  vm.model_data = {'notification_types':[], 'notification_receivers':[]};
  vm.btn_desabled = false;

  vm.model_data.notification_types = ['Mail', 'SMS'];
  vm.model_data.notification_receivers = ['Distributors', 'Resellers'];

  vm.selectedTypes = {'mail_notifications':{}, 'notification_receivers':{}};
  vm.checkedItems = function(type, mail_notification=false){

    if (mail_notification) {

      if (vm.selectedTypes.mail_notifications[type]) {

        delete vm.selectedTypes.mail_notifications[type];
      } else {

        vm.selectedTypes.mail_notifications[type] = true;
      }
    } else {

      if (vm.selectedTypes.notification_receivers[type]) {

        delete vm.selectedTypes.notification_receivers[type];
      } else {

        vm.selectedTypes.notification_receivers[type] = true;
      }
    }
  }

  vm.saveNotifications = saveNotifications;
  function saveNotifications() {

    if (Object.keys(vm.selectedTypes.mail_notifications).length || Object.keys(vm.selectedTypes.notification_receivers).length) {

      vm.btn_desabled = true;

      var send = {'notification_types':JSON.stringify(vm.selectedTypes.mail_notifications),
                  'notification_receivers':JSON.stringify(vm.selectedTypes.notification_receivers), 
                  'remarks':vm.model_data.remarks};

      vm.service.apiCall('push_message_notification/', 'POST', send).then(function(data){

        if(data.message) {
          vm.service.pop_msg(data.data);
          vm.btn_desabled = false;
        }
      });
    } else {

      vm.service.showNoty("Please select notification or receiver type");
    }
  }

}

