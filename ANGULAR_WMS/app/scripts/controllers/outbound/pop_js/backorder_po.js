'use strict';

function BackorderPOPOP($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams) {

  var vm = this;
  vm.state_data = ""; 
  vm.service = Service;

  if($stateParams.data){
     vm.state_data = $stateParams.data;
  }

  vm.pop_data = {};

  vm.getPoData = function(data){

    data = JSON.parse(data);
    Service.apiCall("generate_order_po_data/", "POST", data, true).then(function(data){
      if(data.message) {
        angular.copy(data.data, vm.pop_data)
        $state.go("app.outbound.ViewOrders.PO");
      };
    });
  }

  if(vm.state_data) {

    vm.getPoData(vm.state_data);
  }

  vm.print_enable = false;
  vm.confirm_po = function() {
      var elem = $("form:visible").serializeArray();

      Service.apiCall("confirm_back_order/", "POST", elem, true).then(function(data){
        if(data.message) {
          vm.confirm_disable = true; vm.message = data.data;

          if(data.data.search("<div") != -1) {
                vm.html = $(data.data)[0];
                var html = $(vm.html).closest("form").clone();
                angular.element(".modal-body").html($(html));
                //angular.element(".modal-body").html($(html).find(".modal-body > .form-group"));
                //angular.element(".modal-body").html($(html));
                vm.print_enable = true;
           } else {
             vm.service.pop_msg(data.data);
           }
        };
      });
  }

  vm.print_grn = function() {

    vm.service.print_data(vm.html, "Purchase Order");
  }
}

angular
  .module('urbanApp')
  .controller('BackorderPOPOP', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', BackorderPOPOP]);
