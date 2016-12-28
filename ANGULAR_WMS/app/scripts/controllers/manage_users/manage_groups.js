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
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);;
    vm.dtColumns = [
        DTColumnBuilder.newColumn('Group Name').withTitle('Group Name'),
        DTColumnBuilder.newColumn('Members Count').withTitle('Members Count')
    ];

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
    };  

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.service.apiCall("get_group_data/","get",{data_id:aData['DT_RowId']}).then(function(data){
                  $state.go("app.ManageUsers.GroupDetails");
                  angular.copy(data.data, vm.group_data);
                });
            });
        });
        return nRow;
    };
 
    vm.update = true;
    vm.message = "";
    vm.model_data = {};

    vm.group_data = {}

    vm.close = close;
    function close() {

      vm.model_data = {};
      angular.extend(vm.model_data, {});
      vm.group_name = "";
      vm.BrandmultipleSelect = "";
      vm.StageMultipleSelect = "";
      vm.PermMultipleSelect = "";
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

  vm.group_names = []

  vm.PermMultipleSelect = []
  vm.StageMultipleSelect = []
  vm.BrandMultipleSelect = []

  vm.group_permissions = [];
  vm.prod_stages = [];
  vm.brands_list = [];
  Service.apiCall("add_group_data/","GET").then(function(data){

    if(data.message) {
      var index = 1
      angular.forEach(data.data.perms_list, function(item){
        vm.group_permissions.push({id: index, name: item}); index++;
      });
      angular.forEach(data.data.prod_stages, function(item){
	vm.prod_stages.push({id: index, name: item}); index++;
      });
      angular.forEach(data.data.brands, function(item){
	vm.brands_list.push({id: index, name: item}); index++;
      });
    }
  });

  vm.add_group_permission = function(form){
    if(form.group_name.$valid) {
      var data = {"name":"", "perm_selected":"", "stage_selected":"", "brand_selected":""};
      angular.forEach($('.permission').next().find(".chosen-choices > li > span"), function(single_data){	
        data.perm_selected += $(single_data).text()+"," 
      })
      angular.forEach($('.stage').next().find(".chosen-choices > li > span"), function(single_data_one){
        data.stage_selected += $(single_data_one).text()+","
      })
      angular.forEach($('.brand').next().find(".chosen-choices > li > span"), function(single_data_two){
        data.brand_selected += $(single_data_two).text()+","
      })
      if(form.brand.$valid) {
        data.brand_selected = data.brand_selected.slice(0,-1);
      } 
      if(form.stage.$valid) {
        data.stage_selected = data.stage_selected.slice(0,-1);
      }
      if(form.stage.$valid) {
        data.perm_selected = data.perm_selected.slice(0,-1);
      } 
      data.name = $($('input[name=group_name]')[1]).val();
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

