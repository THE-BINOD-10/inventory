'use strict';

function CreateAllocations($scope, $filter, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Data, SweetAlert) {

  $scope.msg = "start";
  var vm = this;
  vm.order_type_value = "offline";
  vm.service = Service;
  vm.g_data = Data.create_orders
  vm.company_name = Session.user_profile.company_name;
  vm.order_exceed_stock = Boolean(Session.roles.permissions.order_exceed_stock);
  vm.permissions = Session.roles.permissions;
  vm.brand_categorization = Session.roles.permissions.brand_categorization;
  vm.model_data = {}
  vm.dispatch_data = []
  var empty_data = {data: [{sku_id: "", quantity: ""}],
                    customer_id: "", customer_name: ""};

  angular.copy(empty_data, vm.model_data);

  function check_exist(sku_data, index) {

    for(var i = 0; i < vm.model_data.data.length; i++) {

      if((vm.model_data.data[i].sku_id == sku_data.sku_id) && (index != i)) {

        sku_data.sku_id = "";
        vm.service.showNoty("It is already exist in index");
        return false;
      }
    }
    return true;
  }


  // Fill Customer Info Code Start
  vm.get_customer_data = function(item, model, label, event) {
    vm.model_data["customer_id"] = item.customer_id;
    vm.model_data["customer_name"] = item.name;
  }
  // Fill Customer Info Code Ends

  //Fill SKU Info Code Starts
  vm.get_sku_data = function(record, item, index) {

    record.sku_id = item.wms_code;
    if(!vm.model_data.blind_order && !(check_exist(record, index))){
      return false;
    }
    angular.copy(empty_data.data[0], record);
    record.sku_id = item.wms_code;
    record["description"] = item.sku_desc;
    record["quantity"] = 1;
  }
  //Fill SKU Info Code Ends

  //Create Allocation Code Starts
  vm.bt_disable = false;
  vm.insert_allocation_data = function(event, form) {
    if (event.keyCode != 13) {
      if (form.$valid) {
        if (vm.model_data.blind_order) {
          for (var i = 0; i < vm.model_data.data.length; i++) {
            if (vm.model_data.data[i].sku_id && (!vm.model_data.data[i].location)) {
              colFilters.showNoty("Please locations");
              return false;
              break;
            }
          }
        }
        vm.bt_disable = true;
        var elem = angular.element($('form'));
        elem = elem[0];
        elem = $(elem).serializeArray();
        vm.service.apiCall('insert_allocation_data/', 'POST', elem).then(function(data){
          if(data.message) {
            if(data.data.indexOf("Success") != -1) {
              angular.copy(empty_data, vm.model_data);
              vm.final_data = {total_quantity:0,total_amount:0};
              vm.from_custom_order = false;
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
  //Create Allocation Code Ends


  vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
  }

  vm.update_data = update_data;
  function update_data(index, data, last) {
    if (last && (!vm.model_data.data[index].sku_id)) {
      return false;
    }
    if (last) {
      vm.model_data.data.push({sku_id: "", quantity: ""});
    } else {
      vm.model_data.data.splice(index,1);
    }
  }

}
angular
  .module('urbanApp')
  .controller('CreateAllocations', ['$scope', '$filter','$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Data', 'SweetAlert', CreateAllocations]);
