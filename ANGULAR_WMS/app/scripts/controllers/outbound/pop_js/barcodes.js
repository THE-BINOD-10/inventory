'use strict';

function Barcodes($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {

  var vm = this;
  vm.service = Service;

  var url_get = "get_order_labels/";
  vm.model_data = {};

  vm.getPoData = function(data){

    var send = {picklist_number: data.id}
    Service.apiCall(url_get, "GET", send, true).then(function(data){
      if(data.message) {
        angular.copy(data.data.data, vm.model_data.barcodes)
        if (data.data.data.length == 0) {

          Service.showNoty("No labels are there")
        }
      };
    });
  }

  vm.getPoData(items);

  vm.barcode_title = 'Barcode Generation';

  vm.model_data['format_types'] = ['format1', 'format2', 'format3']

  var key_obj = {'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details'}

  vm.model_data['barcodes'] = [{'sku_code':'', 'quantity':''}];

  vm.ok = function (msg) {
    $modalInstance.close(vm.status_data);
  };

  vm.generate_barcodes = function(form) {
    if(form.$valid) {
      var elem = $("form[name='barcodes']").serializeArray();
      vm.service.apiCall('generate_barcodes/', 'POST', elem, true).then(function(data){
        if(data.message) {
          console.log(data);
        }
      })
    }
  }
}

angular
  .module('urbanApp')
  .controller('Barcodes', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', BackorderPOPOP]);
