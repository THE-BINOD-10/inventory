'use strict';

function VendorStockTransferCtrl($scope, $http, $state, Session, colFilters, Service) {
  $scope.msg = "start";
  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  vm.model_data = {}
  var empty_data = {data: [{wms_code: "", quantity: "", location: ""}], vendor: ""};
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
      vm.model_data.data.push({wms_code: "", order_quantity: "", price: ""});
    } else {
      vm.model_data.data.splice(index,1);
    }
  }
vm.get_sku_details = function (data){
  vm.service.apiCall('get_mapping_values/', 'GET', {'wms_code':data.wms_code, 'supplier_id': 0}).then(function(resp){
    if(Object.values(resp).length) {
      data.price = resp.data.price;
    }
  });
}

  vm.warehouse_list = [];
  vm.service.apiCall('get_vendor_list/').then(function(data){
    if(data.message) {
      vm.vendor_list = data.data;
    }
  })
  vm.bt_disable = false;
  vm.insert_order_data = function(data) {
    if (data.$valid) {
      vm.bt_disable = true;
      console.log(form);
      var elem = angular.element(form);
      elem = $(elem).serializeArray();
      vm.service.apiCall('create_vendor_stock_transfer/', 'POST', elem).then(function(data){
        if(data.message) {
          if("Success" == data.data) {
            angular.copy(empty_data, vm.model_data);
          }
          colFilters.showNoty(data.data);
          vm.bt_disable = false;
        }
      })
    } else {
      colFilters.showNoty("Fill Required Fields");
    }
  }
  vm.check_location_stock = function(row){
  var send = {sku_code: row.wms_code, location: row.location, pallet_code:''}
  vm.service.apiCall("get_sku_stock_check/", "GET", send).then(function(data){

    if(data.message) {

      if(data.data.status == 0) {

        vm.service.showNoty(data.data.message);

        if(data.data.message== "Invalid Location") {

          row_data.location = "";
          angular.element(element.target).focus();
        } else if (data.data.message == "Invalid Location and Pallet code Combination") {

          row_data.pallet_code = "";
          angular.element(element.target).focus();
        }
        row_data.picked_quantity = 0;
        row_data.labels = [];
       }
     }
   });
  }




}

angular
  .module('urbanApp')
  .controller('VendorStockTransferCtrl', ['$scope', '$http', '$state', 'Session', 'colFilters', 'Service', VendorStockTransferCtrl]);
