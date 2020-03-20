'use strict';

function AttributesPOP($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $q, $modalInstance, items) {

  var vm = this;
  vm.state_data = "";
  vm.service = Service;
  vm.input_types = ['Input', 'Number', 'Textarea', 'Dropdown'];

  vm.empty_data = {'id': '', 'attribute_name': '', 'attribute_type': 'Input'}

  vm.pop_data = {};
  vm.status_data = "";
  vm.status_data = [];

  vm.getAttrData = function(){
    vm.service.apiCall('get_user_attributes_list/', "GET", {attr_model: 'sku'}).then(function(data){
      data = data.data;
      if(data.status && data.data.length) {
        vm.status_data = vm.status_data.concat(data.data);
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
      var elem = angular.element($('form:visible'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      elem.push({name:"attr_model", value:"sku"})
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      Service.apiCall("save_update_attribute/", "POST", elem, true).then(function(data){
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
        Service.apiCall("delete_user_attribute/", "GET", temp_data, true).then(function(data){
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
  .controller('AttributesPOP', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$q', '$modalInstance', 'items', AttributesPOP]);
