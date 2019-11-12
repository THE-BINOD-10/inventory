'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('LocationMasterTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.filters = {'datatable': 'LocationMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: vm.filters,
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    vm.button_edit = true;
    vm.dtInstance = {};
    vm.dtColumns = [
        DTColumnBuilder.newColumn('zone').withTitle('Zone'),
        DTColumnBuilder.newColumn('location').withTitle('Location'),
        DTColumnBuilder.newColumn('max_capacity').withTitle('Capacity'),
        DTColumnBuilder.newColumn('fill_sequence').withTitle('Put Sequence'),
        DTColumnBuilder.newColumn('pick_sequence').withTitle('Get Sequence'),
        DTColumnBuilder.newColumn('status').withTitle('Status'),
        DTColumnBuilder.newColumn(' ').withTitle('').notSortable(),
      ]
    if(vm.permissions.add_subzonemapping)
    {
      vm.dtColumns.push(DTColumnBuilder.newColumn('sub_zone').withTitle('SubZone'))
    }


    vm.status_data = ["Inactive","Active"];
    vm.lock_fields =  ['Inbound', 'Outbound','Inbound and Outbound']

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
      $(nRow["cells"][6]).bind('click',function(){
        vm.zone_title = "Update Zone";
        vm.update = true;
        vm.zone = aData['zone'];
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
        });
      });
      $('td:not(td:first)', nRow).bind('click', function()  {
            $scope.$apply(function() {
              vm.title = "Update Location"
              vm.update = true;
              angular.copy(aData, vm.model_data);
              vm.model_data['zone_id'] = aData['zone'];
              vm.model_data.status = vm.status_data[vm.model_data.status];
              vm.model_data.lock_status = vm.lock_fields[vm.lock_fields.indexOf(vm.model_data.lock_status)];
              $state.go('app.masters.LocationMaster.Location');
              $timeout(function () {
                $('.selectpicker').selectpicker();
                $(".lock_loc").val(vm.model_data.lock_status);
              }, 300);
            });
        });
   }

    vm.check_selected = function(opt) {
      return (vm.model_data.location_group.indexOf(opt) > -1) ? true: false;
    }

  vm.status_data = ["Inactive", "Active"];
  vm.customer_roles = ["User", "HOD", "Admin"];
  var empty_data = {sku: "", pack_id: "",pack_quantity: ""};
  vm.model_data = {};


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
          vm.service.refresh(vm.dtInstance);
          vm.close();
        } else {
          vm.service.pop_msg(data.data);
        }
      })
    } else {
      vm.service.pop_msg("Please fill Required fields");
    }
  }

  vm.close = function() {
    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.LocationMaster');
  }


  vm.add_location = function() {
    angular.copy({}, vm.model_data);
    vm.update = false
    vm.model_data['status'] = "Active";
    vm.model_data['location_group'] = [];
    vm.model_data['lock_status'] = 'none';
    vm.service.apiCall('get_zones_list', "GET").then(function(data) {
      if(data.message) {
        vm.all_zones_list = data.data.zones;
        vm.model_data['all_groups'] = data.data.sku_groups
        $state.go('app.masters.LocationMaster.Location');
        $timeout(function () {
        $('.selectpicker').selectpicker();}, 300);
      }
    });
  }

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


}
