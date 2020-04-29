;(function(){

'use strict';

var app = angular.module('urbanApp', [''])
app.controller('newBarcodeConfig',['$scope', 'Session', 'Service', '$modal', newBarcodeConfig]);

function newBarcodeConfig($scope, Session, Service, $modal) {
    var vm = this;
    vm.edit_form = false;
    vm.model_data = {};
    vm.dropdown_entities = [
      { "name": "GTIN (EAN Number)", "value": "GTIN"},
      { "name": "SKU", "value": "SKU"},
      { "name": "MFG DATE", "value": "MFG_Date" },
      { "name": "EXPIRY DATE", "value": "EXPIRY_Date"},
      { "name": "BATCH NUMBER (LOT)", "value": "LOT"}
    ]
    vm.entities_data = [
      {
        "entity_type": '',
        "start": '',
        "end": '',
        "format": '',
        "regular_expression": ''
      }
    ];
    vm.orig_model_data = {};
    vm.model_barcode_config_data = {}
    vm.barcode_config_headers=[]

    vm.get_saved_barcodes = function () {
        vm.model_barcode_config_data = {}
        Service.apiCall('get_new_barcode_configurations/').then(function (data) {
          if (data.message) {
            angular.copy(data.data, vm.model_barcode_config_data);
          }
        });
      }

    vm.append_entitie = function () {
      vm.entities_data.push({
        "entity_type": '',
        "start": '',
        "end": '',
        "format": '',
       "regular_expression": ''
      })
    }

    vm.remove_entitie = function (index) {
      vm.entities_data.splice(index,1);
    }

    vm.emptyData = function () {
      vm.model_data = {};
      vm.entities_data = [{
        "entity_type": '',
        "start": '',
        "end": '',
        "format": '',
        "regular_expression": ''
      }]
    }

    vm.updateBarCodeConfiguration = function () {
      let validation=false
      let sku_count=0
      console.log(vm.entities_data, vm.model_data)
      if (vm.model_data.string_length) {
        vm.model_data.string_length = Number(vm.model_data.string_length)
      }
      if (vm.model_data.brand && vm.model_data.configuration_title && Number(vm.model_data.string_length) > 0) {
        angular.forEach(vm.entities_data, function (entity, entity_ind) {

          entity.start = Number(entity.start)
          entity.end = Number(entity.end)
          if (entity.entity_type && ((entity.start > 0 && entity.end > 0) || entity.regular_expression)) {
            if (  entity.regular_expression || entity.start < entity.end) {
              if(entity.entity_type=="GTIN"){
                sku_count=sku_count+1
              }
              validation=true
            }
            else {
              Service.showNoty('Please Enter end value, Greater than start value');
              return 0;
            }
           }
          else {
            Service.showNoty('Please Enter the Entity Type and start and end Fields');
            return 0;
          }
        });
        if(validation && sku_count==1)
        {
          vm.model_data["data"]=JSON.stringify(vm.entities_data);
          Service.apiCall('update_new_barcode_configuration/', 'POST', vm.model_data).then(function(data){
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
        }
        else {
          Service.showNoty('Please Enter the required Fields');
          return 0;
        }
      }
      else {
        Service.showNoty('Please Enter the required Fields');
        return 0;
      }
    }
  }

})();

