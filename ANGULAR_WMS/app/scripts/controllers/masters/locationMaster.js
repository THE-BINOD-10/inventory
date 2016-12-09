'use strict';

function LocationMasterCtrl($scope, $state, $http, $timeout, Session, Service) {

  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;

  vm.data = [];
  function location_data() {
    vm.service.apiCall('location_master/').then(function(data){
      if(data.message) {
        angular.copy(data.data, vm.data);
      }
    });
  }

  location_data();
 
  vm.add_zone = add_zone;
  function add_zone() {
    $state.go('app.masters.LocationMaster.Zone');
  }

  vm.zone = "";
  vm.zone_adding = function(zone) {

   if (zone.length> 0) {
     vm.service.apiCall('add_zone/', 'GET', {zone: zone}).then(function(data){
       if(data.message){
         vm.service.pop_msg(data.data);
         vm.zone = "";
         location_data();
         vm.close();
       }
     })
   }else{
     vm.service.pop_msg("Please Enter Zone Name");
   }
  }

  vm.location_adding = function(data) {

    if(data.$valid) {
      var url = (vm.update)? 'update_location/?' : 'add_location/?'
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      elem = $.param(elem);
      var data = $('.selectpicker').val();
      var send = "";
      if (data != null) {
        for(var i = 0; i < data.length; i++) {
          send += data[i]+",";
        }
      }
      send = send.slice(0,-1);
      elem = elem+"&location_group="+send;
      $http.get(Session.url+url+elem, {withCredential: true})
      .success(function(data, status) {
        if(data == 'Updated Successfully' || data == 'Added Successfully') {
          location_data();
          vm.close();
        } else {
          vm.service.pop_msg(data);
        }
      })
    } else {
      vm.service.pop_msg("Please fill Required fields");
    }
  }

  vm.add_location = function() {

    vm.base();
    angular.copy({}, vm.model_data);
    vm.model_data['status'] = "Active";
    vm.model_data['location_group'] = [];
    vm.model_data['lock_status'] = 'none';
    vm.model_data['zone_id'] = vm.data.location_data[0].zone;
    $state.go('app.masters.LocationMaster.Location');
    $timeout(function () {
      $('.selectpicker').selectpicker();
    }, 300);
  }

  vm.close = function() {

    $state.go('app.masters.LocationMaster');
    vm.zone = "";
    angular.copy({}, vm.model_data);
  }

  vm.base = function() {

    vm.update = false;
    vm.title = "Add Location"
  }

  vm.update = false;
  vm.title = ""
  vm.status_data = ["Inactive","Active"];
  vm.model_data = {};

  vm.open_location = open_location;
  function open_location(data, zone) {
    vm.title = "Update Location"
    vm.update = true;
    angular.copy(data, vm.model_data);
    vm.model_data['zone_id'] = zone;
    vm.model_data.status = vm.status_data[vm.model_data.status];
    vm.model_data.lock_status = vm.data.lock_fields[vm.data.lock_fields.indexOf(vm.model_data.lock_status)];
    $state.go('app.masters.LocationMaster.Location');
    $timeout(function () {
      $('.selectpicker').selectpicker();
      $(".lock_loc").val(vm.model_data.lock_status);
    }, 300);
  }

  vm.check_selected = function(opt) {

    return (vm.model_data.location_group.indexOf(opt) > -1) ? true: false;
  }
}

angular.module('urbanApp', [])
  .controller('LocationMasterCtrl',['$scope', '$state', '$http', '$timeout', 'Session', 'Service', LocationMasterCtrl]);
