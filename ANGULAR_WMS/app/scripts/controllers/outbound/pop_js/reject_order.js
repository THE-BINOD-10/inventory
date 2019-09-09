'use strict';

function Rejectorderpop($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {

  var vm = this;
  vm.state_data = "";
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  if(items){
     vm.state_data = items;
  }


  vm.model_data = {};

  vm.get_sku_data = function(record, item, index) {

    record.sku_id = item.wms_code;
    if(!vm.model_data.blind_order){
      return false;
    }
    angular.copy(empty_data.data[0], record);
    record.sku_id = item.wms_code;
    record["description"] = item.sku_desc;

    vm.get_customer_sku_prices(item.wms_code).then(function(data){
      if(data.length > 0) {
        data = data[0]
        record["price"] = data.price;
        record["description"] = data.sku_desc;
        if (! vm.model_data.blind_order) {
          if(!(record.quantity)) {
            record.quantity = 1
          }
        }
        record["taxes"] = data.taxes;
        record["mrp"] = data.mrp;
        record.invoice_amount = Number(record.price)*Number(record.quantity);
        record["priceRanges"] = data.price_bands_map;
        vm.cal_percentage(record);
        vm.update_availabe_stock(record)
      }
    })
  }
  vm.key_event = function($event, product, item, index) {
    if ($event.keyCode == 13) {
      if (typeof(vm.model_data.customer_id) == "undefined" || vm.model_data.customer_id.length == 0){
        return false;
      } else {
        var customer_id = vm.model_data.customer_id;
        $http.get(Session.url+'get_create_order_mapping_values/?wms_code='+product.sku_id, {withCredentials : true}).success(function(data, status, headers, config) {
          if(Object.keys(data).length){
            vm.model_data.data[index].sku_id = product.sku_id;
          } else {
            Service.searched_cust_id = customer_id;
            Service.searched_wms_code = product.sku_id;
            Service.is_came_from_create_order = true;
            Service.create_order_data = vm.model_data;
            Service.sku_id_index = index;
            Service.create_order_auto_shipment = vm.auto_shipment;
            Service.create_order_custom_order = vm.custom_order;
            $state.go('app.masters.SKUMaster');
          }
        });
      }
    }
  }
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


  vm.delete_central_order = function(form) {
      if(form.$invalid) {
        return false;
      }
      var elem = $("form:visible").serializeArray();

      vm.confirm_disable = true
      vm.service.apiCall("delete_central_order/", "POST", elem, true).then(function(data){
          vm.service.pop_msg(data.data.status);
          vm.confirm_disable = false;
          $timeout(function() {
          vm.ok("succes")
        }, 2000);
      });
  }


  vm.ok = function (msg) {
    $modalInstance.close(vm.status_data);
  };
}

angular
  .module('urbanApp')
  .controller('Rejectorderpop', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', Rejectorderpop]);
