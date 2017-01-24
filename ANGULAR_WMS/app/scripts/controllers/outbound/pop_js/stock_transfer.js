'use strict';

function StockTransferPOP($scope, $http, $state, $timeout, Session, colFilters, Service) {

  var vm = this;
  var state_data = Service.stock_transfer;
  vm.service = Service;
  vm.pop_data = {};
  var empty_data = {data: [{wms_code: "", order_quantity: "", price: ""}], warehouse_name: ""};
  angular.copy(empty_data, vm.pop_data);
  if(state_data)  {

    angular.copy(JSON.parse(state_data), vm.pop_data.data);
  } else {
    $state.go($state.$current.parent);
  }

  vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

  vm.update_data = update_data;
  function update_data(index, data, last) {
    console.log(data);
    if (last) {
      vm.pop_data.data.push({wms_code: "", order_quantity: "", price: ""});
    } else {
      vm.pop_data.data.splice(index,1);
    }
  }

  vm.warehouse_list = [];
  vm.service.apiCall('get_warehouses_list/').then(function(data){
    if(data.message) {
      vm.warehouse_list = data.data.warehouses;
    }
  })
  vm.bt_disable = false; 
  /*vm.insert_order_data = function(data) {
    if (data.$valid) {
      vm.bt_disable = true;
      console.log(form);
      var elem = angular.element(form);
      elem = $(elem).serializeArray();
      vm.service.apiCall('create_stock_transfer/', 'POST', elem).then(function(data){
        if(data.message) {
          if("Confirmed Successfully" == data.data) {
            angular.copy(empty_data, vm.pop_data);
            Service.stock_transfer = "";
            colFilters.showNoty("Confirmed Successfully");
          }
          vm.service.pop_msg(data.data);
          vm.bt_disable = false;
        }
      })
    } else {
      vm.service.pop_msg("Fill Required Fields");
    }
  }*/

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 2000);
      //reloadData();
    }

    /*vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
    };*/


  vm.insert_order_data = function(data) {
     if (data.$valid) {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serialize();
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
        $http({
               method: 'POST',
               url:Session.url+'confirm_st/',
               withCredential: true,
               data: elem
               }).success(function(data, status, headers, config) {
                  if(data == 'Confirmed Successfully') {
                    //vm.close();
                    //vm.reloadData();
                    pop_msg(data);
                  } else {
                    pop_msg(data);
                  }
              });
     }
  }

}

angular
  .module('urbanApp')
  .controller('StockTransferPOP', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', StockTransferPOP]);
