'use strict';

function CreateOrders($scope, $http, Session, colFilters, Service) {

  $scope.msg = "start";
  var vm = this;
  vm.service = Service;
  vm.model_data = {}
  var empty_data = {data: [{sku_id: "", quantity: "", invoice_amount: ""}], customer_id: ""};
  angular.copy(empty_data, vm.model_data);
  vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

  vm.update_data = update_data;
  function update_data(index, data, last) {
    console.log(data);
    if (last) {
      vm.model_data.data.push({sku_id: "", quantity: "", invoice_amount: ""});
    } else {
      vm.model_data.data.splice(index,1);
    }
  }

  vm.get_customer_data = function(id) {
    if(id && id != "") {
      vm.service.apiCall('get_customer_data/', 'GET', {id: id}).then(function(data){
        if(data.message) {
          if(data.data == "") {
            make_empty();
          } else {
            vm.model_data["customer_name"] = data.data.name;
            vm.model_data["telephone"] = parseInt(data.data.phone_number);
            vm.model_data["email_id"] = data.data.email_id;
            vm.model_data["address"] = data.data.address;
          }
        }
      })
    } else {
      make_empty()
    }
  }

  function make_empty() {
    vm.model_data["customer_name"] = "";
    vm.model_data["telephone"] = "";
    vm.model_data["email_id"] = "";
    vm.model_data["address"] = "";
  }

  vm.bt_disable = false;
  vm.insert_order_data = function(form) {
    if (vm.model_data.shipment_date) {
      vm.bt_disable = true;
      console.log(form);
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('insert_order_data/', 'GET', elem).then(function(data){
        if(data.message) {
          if("Success" == data.data) {
            angular.copy(empty_data, vm.model_data);
          }
          colFilters.showNoty(data.data);
        }
        vm.bt_disable = false;
      })
    } else {
      colFilters.showNoty("Fill Required Fields");
    }
  }

}

angular
  .module('urbanApp')
  .controller('CreateOrders', ['$scope', '$http', 'Session', 'colFilters', 'Service', CreateOrders]);
