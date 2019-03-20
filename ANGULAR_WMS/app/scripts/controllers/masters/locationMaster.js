'use strict';

function LocationMasterCtrl($scope, $state, $http, $timeout, Session, Service) {

  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  vm.segregation_list = {};
  vm.segregation_selected = 'sellable';

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
    vm.zone_title = "Update Zone";
    vm.update = false;
    vm.zone = "";
    vm.level = 0;
    vm.marketplace_selected = [];
    vm.service.apiCall('get_marketplaces_list/?status=all_marketplaces').then(function(mk_data){
      if(mk_data.message) {
        vm.market_list = mk_data.data.marketplaces;
        vm.segregation_list = mk_data.data.segregation_options;
        $state.go('app.masters.LocationMaster.Zone');
        $timeout(function() {
          $('.selectpicker').selectpicker();
        }, 500);
      }
    })
  }
  vm.get_zone_details = function(zone)
  {
    vm.service.apiCall('get_zone_details/','GET',{'zone':zone}).then(function(zone_data){
      vm.zone_data = zone_data.data.location_data
    });
  }

  vm.zone = "";
  vm.marketplaces = [];
  vm.zone_adding = function(zone) {

   if (zone.length> 0) {
     if(vm.permissions.marketplace_model) {
       var marketplaces = vm.marketplaces.join(",");
     } else {
       var marketplaces = vm.marketplace_selected.join(",");
     }
     vm.service.apiCall('add_zone/', 'GET', {zone: zone, marketplaces: marketplaces, update: vm.update, level: vm.level, segregation: vm.segregation}, true).then(function(data){
       if(data.message){
         if(data.data == "Added Successfully") {
           vm.zone = "";
           vm.level = 0;
           location_data();
           vm.close();
         } else {
           vm.service.pop_msg(data.data);
         }
       }
     })
   }else{
     vm.service.pop_msg("Please Enter Zone Name");
   }
  }

  vm.location_adding = function(data) {

    if(data.$valid) {
      var url = (vm.update)? 'update_location/' : 'add_location/'
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      var data = $('.selectpicker').val();
      var send = "";
      if (data != null) {
        for(var i = 0; i < data.length; i++) {
          send += data[i]+",";
        }
      }
      send = send.slice(0,-1);
      elem.push({name: 'location_group', value: send})
      vm.service.apiCall(url, "GET", elem, true).then(function(data) {
        if(data.data == 'Updated Successfully' || data.data == 'Added Successfully') {
          location_data();
          vm.close();
        } else {
          vm.service.pop_msg(data.data);
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
    vm.service.apiCall('get_zones_list', "GET").then(function(data) {
      if(data.message) {
        vm.all_zones_list = data.data.zones;
        $state.go('app.masters.LocationMaster.Location');
        $timeout(function () {
        $('.selectpicker').selectpicker();}, 300);
      }
    });
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

  vm.edit_zone = function(zone, e) {
    e.preventDefault();
    vm.zone_title = "Update Zone";
    vm.update = true;
    vm.zone = zone.zone;
    vm.marketplace_selected = [];
    vm.service.apiCall('get_zone_data/?zone='+vm.zone).then(function(data){
      if(data.message) {
      vm.level = data.data.level;
      vm.segregation_selected = data.data.segregation;
      vm.service.apiCall('get_marketplaces_list/?status=all_marketplaces').then(function(mk_data){
        if(mk_data.message) {
          vm.market_list = mk_data.data.marketplaces;
          vm.marketplace_selected = data.data.marketplaces;
	  vm.segregation = data.data.segregation;
	  vm.segregation_list = mk_data.data.segregation_options;
          $state.go('app.masters.LocationMaster.Zone');
          $timeout(function() {
            $('.selectpicker').selectpicker();
          }, 500);
        }
      })
      }
    })
  }

  vm.check_zone_level = function(opt) {
    if(opt=='') {
      opt = 0;
    }
    opt = Number(opt);
    if(opt > 2) {
      vm.level = 1;
    }
  }

  vm.add_sub_zone_mapping = add_sub_zone_mapping;
  function add_sub_zone_mapping() {
    vm.sub_zone_data = {}
    vm.sub_zone_data['zone'] = '';
    vm.sub_zone_data['sub_zone'] = '';
    vm.service.apiCall('get_zones/?level=0&exclude_mapped=true').then(function(zone_data){
      if(zone_data.message) {
        vm.sub_zone_data['zones_list'] = zone_data.data.zones_list;
        vm.service.apiCall('get_zones/?level=1&exclude_mapped=true').then(function(zone_data){
          if(zone_data.message) {
            vm.sub_zone_data['sub_zones_list'] = zone_data.data.zones_list;
            $state.go('app.masters.LocationMaster.SubZoneMapping');
          }
        });
      }
    });
  }

  vm.sub_zone_mapping = function(mapping_data) {
    if (mapping_data.zone && mapping_data.sub_zone) {
      vm.service.apiCall('add_sub_zone_mapping/', 'GET', {zone: mapping_data.zone, sub_zone: mapping_data.sub_zone}, true).then(function(data){
        if(data.message){
          if(data.data == "Added Successfully") {
            vm.sub_zone_data = {};
            location_data();
            vm.close();
          } else {
            vm.service.pop_msg(data.data);
          }
        }
      })
    }else{
      vm.service.pop_msg("Please Enter Zone and Sub Zone");
    }
  }

  vm.market_list = [];
  /*
  vm.service.apiCall('get_marketplaces_list/?status=all_marketplaces').then(function(data){
    if(data.message) {
      vm.market_list = data.data.marketplaces;
      vm.segregation_list = data.data.segregation_options;
    }
  })
  */
}

angular.module('urbanApp', [])
  .controller('LocationMasterCtrl',['$scope', '$state', '$http', '$timeout', 'Session', 'Service', LocationMasterCtrl]);
