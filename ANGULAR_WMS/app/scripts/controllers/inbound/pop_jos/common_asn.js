'use strict';

function ASNPOP($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {

  var vm = this;
  vm.state_data = "";
  vm.service = Service;
  vm.date = new Date();

  if(items){
     vm.state_data = items;
  }

  var url_get = "get_purchase_orders/";

  vm.model_data = {};

  vm.getPoData = function(data){

    Service.apiCall(url_get, "GET", data, true).then(function(data){
      if(data.message) {
        angular.copy(data.data, vm.model_data)
        angular.forEach(vm.model_data.data_dict, function(sku_data){
          if(sku_data.selected_item == ""){
            sku_data.selected_item = {id: "", name: "None"};
          }
        })
      };
    });
  }

  if(vm.state_data.data) {

    vm.getPoData(vm.state_data.data);
  }

  vm.print_enable = false;
  vm.confirm_disable = false;
  vm.asn_confirmation = function(form) {
      if(form.$invalid) {
        return false;
      }
      var elem = $("form:visible").serializeArray();

      vm.confirm_disable = true
      Service.apiCall("confirm_asn_order/", "POST", elem, true).then(function(data){
        if(data.message) {
          vm.message = data.data;
          if (data.data.status == 'failed') {
	         vm.service.pop_msg(data.data);
          }
          else {
            const file = new Blob([data.data], { type: 'application/pdf' })
            const fileURL = URL.createObjectURL(file)
            $('#proceedModal').modal('hide');
            window.open(fileURL)
          }
          vm.ok();

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

  vm.check_qty = function(record) {
    var avilable_qty = record.ordered_quantity - record.received_quantity;
    if (record.current_quantity > avilable_qty) {
      record.current_quantity = avilable_qty;
    }
  }

  vm.ok = function (msg) {
    $modalInstance.close(vm.status_data);
  };
}

angular
  .module('urbanApp')
  .controller('ASNPOP', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', ASNPOP]);
