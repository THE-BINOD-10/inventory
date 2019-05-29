'use strick';

function IMEITrackerCtrl($scope, $http, Service) {

  var vm = this;

  vm.model_data = {};
  vm.scan_stock_item_type = '';
  vm.scan_item_type = 'PO';
  vm.scan_imei = function(event, field) {
      if ( event.keyCode == 13 && field) {
        field = field.toUpperCase();
        Service.apiCall('get_imei_data/', 'GET', {imei:field}, true).then(function(data){
          if(data.data.message == "Success") {
            if (data.data.data.length){
              if (data.data.data[0]["jo_details"]) {
                vm.scan_item_type = 'JO';
              } else if (data.data.data[0]["stock_transfer"]) {
                vm.scan_stock_item_type = 'ST';
              } else {
                vm.scan_item_type = 'PO';
              }
            }
            vm.model_data = data.data;
          } else {
            vm.model_data = {};
            Service.showNoty(data.data.message);
          }
        })
        vm.imei="";
      }
    }
}

angular.module('urbanApp')
  .controller('IMEITrackerCtrl', ['$scope', '$http', 'Service', IMEITrackerCtrl])
