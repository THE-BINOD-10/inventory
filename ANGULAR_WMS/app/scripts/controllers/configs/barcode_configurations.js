;(function(){

'use strict';

var app = angular.module('urbanApp', [''])
app.controller('barcodeConfig',['$scope', 'Session', 'Service', '$modal', barcodeConfig]);

function barcodeConfig($scope, Session, Service, $modal) {

  var vm = this;
  vm.edit_form = false;
  vm.model_data = {};
  vm.model_data['scanning_type'] = 'sku_based';
  vm.orig_model_data = {};
  vm.model_barcode_config_data = {}

  vm.get_saved_barcodes= function() {
    vm.model_barcode_config_data = {}
    Service.apiCall('get_barcode_configurations/').then(function(data){
      if(data.message) {
        angular.copy(data.data, vm.model_barcode_config_data);
      }
    });
  }
  // vm.back = function() {
  //   angular.copy(vm.orig_model_data, vm.model_data);
  // }

  vm.emptyData = function () {
    vm.model_data = {};
    vm.model_data['scanning_type'] = 'sku_based';
  }

  vm.updateBarCodeConfiguration = function() {
    if (vm.model_data.scanning_type && vm.model_data.configuration_title) {
      Service.apiCall('update_barcode_configuration/', 'POST', vm.model_data).then(function(data){
        if(data.message) {
          if(data.data == 'Success') {
            vm.emptyData();
            vm.get_saved_barcodes();
            Service.showNoty('Successfully Updated');
          } else {
            Service.showNoty(data.data);
          }
        }
      });
    } else {
      Service.showNoty('Please Enter the required Fields');
    }
  }
}

})();
