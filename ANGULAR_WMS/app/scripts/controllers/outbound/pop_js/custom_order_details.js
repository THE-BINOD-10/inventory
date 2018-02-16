function customOrderDetails($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {

  var vm = this;
  vm.customData = items[0].sku_extra_data;
  vm.service = Service;

  vm.ok = function (msg) {
    $modalInstance.close("Close");
  };
  var single = {}

  var value = items[0];
  vm.customer_id = value.cust_id;
  vm.customer_name = value.cust_name;
  vm.phone = value.phone;
  vm.email = value.email;
  vm.address = value.address;
  vm.city = value.city;
  vm.state = value.state;
  vm.order_id_code = value.order_id_code;
  vm.pin = value.pin;
  vm.product_title = value.product_title;
  vm.quantity = value.quantity;
  vm.invoice_amount = value.invoice_amount;
  vm.shipment_date = value.shipment_date;
  vm.remarks = value.remarks;
  vm.cust_data = value.cus_data;
  vm.item_code = value.item_code;
  vm.order_id = value.order_id;
  vm.market_place = value.market_place;

  var image_url = value.image_url;
  vm.img_url = vm.service.check_image_url(image_url); 

  vm.get_image_url = function(type, place, status) {

    if(status) {
      console.log(place);
      if (!single[type]) {
        var url = "";
        angular.forEach(vm.customData.image_data, function(value, key){
          if(key.indexOf(type) != -1) {
            url = value;
          }
        })
        url = vm.service.check_image_url(url);
        single[type] = url;
      } else {
        return single[type];
      }
    } else {
      if(vm.customData.image_data[type+"_"+place]) {
        return vm.service.check_image_url(vm.customData.image_data[type+"_"+place]);
      }
    }
  }
}

angular
  .module('urbanApp')
  .controller('customOrderDetails', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', customOrderDetails]);
