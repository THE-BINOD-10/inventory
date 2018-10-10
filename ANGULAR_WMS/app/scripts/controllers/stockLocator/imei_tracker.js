'use strick';

function IMEITrackerCtrl($scope, $http, Service) {

  var vm = this;

  vm.model_data = {};
  vm.scan_item_type = '';
  vm.scan_imei = function(event, field) {
      if ( event.keyCode == 13 && field) {

        Service.apiCall('get_imei_data/', 'GET', {imei:field}, true).then(function(data){
          vm.scan_item_type = 'JO';
          if(data.data.message == "Success") {
            vm.model_data = data.data;
          } else {

            vm.model_data = {}
            Service.showNoty(data.data.message);
          }
        })
        vm.imei="";
      }
    }
}

angular.module('urbanApp')
  .controller('IMEITrackerCtrl', ['$scope', '$http', 'Service', IMEITrackerCtrl])
