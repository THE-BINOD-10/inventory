'use strict';

function Rejectorderpop($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {

  var vm = this;
  vm.state_data = "";
  vm.service = Service;

  if(items){
     vm.state_data = items;
  }

  // var url_get = "generate_po_data/";
  // if ($state.current.name == "app.production.BackOrders") {
  //
  //   url_get = "generate_rm_po_data/";
  // } else if ($state.current.name != "app.outbound.BackOrders") {
  //
  //   url_get = "generate_order_po_data/";
  // }

  vm.model_data = {};

  // vm.getPoData = function(data){
  //
  //   Service.apiCall(url_get, "POST", data, true).then(function(data){
  //     if(data.message) {
  //       angular.copy(data.data, vm.model_data)
  //       angular.forEach(vm.model_data.data_dict, function(sku_data){
  //         if(sku_data.selected_item == ""){
  //           sku_data.selected_item = {id: "", name: "None"};
  //         }
  //       })
  //       vm.model_data.supplier_list.push({id: "", name: "None"});
  //       vm.model_data.filter = vm.state_data.filter
  //     };
  //   });
  // }
  vm.print_enable = false;
  vm.confirm_disable = false;
  vm.confirm_send_back = function(form) {
      if(form.$invalid) {
        return false;
      }
      var elem = $("form:visible").serializeArray();

      vm.confirm_disable = true
      vm.service.apiCall("send_order_back/", "POST", elem, true).then(function(data){
        if(data.data.data.length == 0) {
          vm.message = data.data.status;
          vm.service.pop_msg(data.data.status);
          $timeout(function() {
          vm.ok("succes")
        }, 2000);


        }
        else{
          vm.service.pop_msg('These orders IDs are  not send back'+data.data);
          $timeout(function() {
          vm.ok("Failed")
        }, 2000);

        }
        vm.confirm_disable = false;
      });
  }


  vm.ok = function (msg) {
    $modalInstance.close(vm.status_data);
  };
}

angular
  .module('urbanApp')
  .controller('Rejectorderpop', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', Rejectorderpop]);
