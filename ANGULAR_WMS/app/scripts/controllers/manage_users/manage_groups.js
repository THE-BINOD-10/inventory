'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ManageGroups',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'ManageGroups'},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers');
    vm.dtColumns = [
        DTColumnBuilder.newColumn('Group Name').withTitle('Group Name'),
        DTColumnBuilder.newColumn('Members Count').withTitle('Members Count')
    ];

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
    };  
 
    vm.update = true;
    vm.message = "";
    vm.model_data = {};

    vm.close = close;
    function close() {

      vm.model_data = {};
      angular.extend(vm.model_data, {});
      vm.multipleSelect = "";
      $state.go('app.ManageUsers');
    }

    vm.add_group = add_group;
    function add_group() {
      $state.go('app.ManageUsers.AddGroup');
    }

  function pop_msg(msg) {
    vm.message = msg;
    $timeout(function () {
        vm.message = "";
    }, 2000);
  }

  vm.group_names = [];

  vm.group_permissions = [];
  Service.apiCall("add_group_data/","GET").then(function(data){

    if(data.message) {
      var index = 1
      angular.forEach(data.data.perms_list, function(item){
        vm.group_permissions.push({id: index, name: item}); index++;
      });
    }
  });

  vm.add_group_permission = function(form){

    if(form.$valid && $("input[name=group_name]:visible").val()) {
      var data = {"name":"","selected":[]};
      angular.forEach($('.permission').next().find(".chosen-choices > li:visible"), function(record){
        if($(record).text()) {
          data.selected.push($(record).text())
        }
      })
      data.selected = data.selected.join(",");
      data.name = $("input[name=group_name]:visible").val();
      Service.apiCall("add_group/","POST", data).then(function(data){

        if(data.message) {

          pop_msg(data.data);
          if(data.data == "Updated Successfully") {
            vm.close();
            vm.reloadData();
          }
        }
      })
    } else {
      pop_msg("Please Fill Required Fields");
    } 
  }

}

