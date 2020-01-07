'use strict';

function BackorderPOPOP($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {

  var vm = this;
  vm.state_data = "";
  vm.service = Service;

  if(items){
     vm.state_data = items;
  }

  var url_get = "generate_po_data/";
  if ($state.current.name == "app.production.BackOrders") {

    url_get = "generate_rm_po_data/";
  } else if ($state.current.name != "app.outbound.BackOrders") {

    url_get = "generate_order_po_data/";
  }

  vm.model_data = {};

  vm.getPoData = function(data){

    Service.apiCall(url_get, "POST", data, true).then(function(data){
      if(data.message) {
        angular.copy(data.data, vm.model_data)
        angular.forEach(vm.model_data.data_dict, function(sku_data){
          if(sku_data.selected_item == ""){
            sku_data.selected_item = {id: "", name: "None"};
          }
        })
        vm.model_data.supplier_list.push({id: "", name: "None"});
        vm.model_data.filter = vm.state_data.filter
      };
    });
  }

  if(vm.state_data.data) {

    vm.getPoData(vm.state_data.data);
  }

  vm.change_supplier_data = function(form, index){
    if(form.$invalid) {
        return false;
      }
      var elem = vm.model_data.data_dict[index];
      Service.apiCall("backorder_supplier_data/", "POST", elem, true).then(function(data){
        if(data.message){
          if(data.data.taxes){
            vm.model_data.data_dict[index].taxes = data.data.taxes;
            vm.model_data.data_dict[index].price = data.data.price;
          }
        };

      });
  }

  vm.print_enable = false;
  vm.confirm_disable = false;
  vm.confirm_po = function(form) {
      if(form.$invalid) {
        return false;
      }
      var elem = $("form:visible").serializeArray();

      vm.confirm_disable = true
      Service.apiCall("confirm_back_order/", "POST", elem, true).then(function(data){
        if(data.message) {
          vm.message = data.data;

          if(data.data.search("<div") != -1) {
                vm.html = $(data.data)[0];
                var html = $(vm.html).closest("form").clone();
                angular.element(".modal-body").html($(html));
                vm.print_enable = true;
           } else {
             vm.service.pop_msg(data.data);
           }
        };
        vm.confirm_disable = false;
      });
  }

  vm.print_grn = function() {

    vm.service.print_data(vm.html, "Purchase Order");
  }

  vm.ok = function (msg) {
    $modalInstance.close(vm.status_data);
  };
}

angular
  .module('urbanApp')
  .controller('BackorderPOPOP', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', BackorderPOPOP]);
