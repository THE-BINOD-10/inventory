'use strict';

function ClassificationPOP($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $q, $modalInstance, items) {

  var vm = this;
  vm.state_data = "";
  vm.service = Service;

  vm.empty_data = {'id': '', 'classifcation': '', 'units_per_day': ''}

  vm.pop_data = {};
  vm.status_data = "";
  vm.status_data = [];

  vm.getAttrData = function(){
    vm.service.apiCall('get_classfication_settings/', "GET",'').then(function(data){
      if(data.data) {
        vm.status_data = vm.status_data.concat(data.data.data);
      }
      else {
        vm.status_data.push(vm.empty_data);
      }
      console.log(vm.status_data);
    });
  }
    vm.getAttrData();

  vm.add_attribute = function () {
      var temp = {};
      angular.copy(vm.empty_data,temp);
      vm.status_data.push(temp);
  }


  vm.save_attribute = function() {
      var elem = $(form).serializeArray();
      Service.apiCall("save_update_classification/", "POST", elem, true).then(function(data){
        if(data.data.message == 'Updated Successfully') {
          $modalInstance.close(vm.status_data);
        }
        else {
              vm.service.pop_msg(data.data)
        }
      });
  }

  vm.delete_attr = function(data, index) {
      if (data.id) {
        var temp_data = {};
        temp_data['data_id'] = data.id;
        $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
        Service.apiCall("delete_classification/", "GET", temp_data, true).then(function(data){
          if(data.data.message == 'Updated Successfully') {
            vm.status_data.splice(index,1);
          }
          else {
            vm.service.pop_msg(data.data)
          }
        });
      }
      else {
        vm.status_data.splice(index,1);
      }
  }

  vm.ok = function (msg) {
    $modalInstance.close(vm.status_data);
  };
}

angular
  .module('urbanApp')
  .controller('ClassificationPOP', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$q', '$modalInstance', 'items', ClassificationPOP]);
