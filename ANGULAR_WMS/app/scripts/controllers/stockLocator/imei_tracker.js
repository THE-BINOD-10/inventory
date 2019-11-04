'use strick';

function IMEITrackerCtrl($scope, $http, Service, $state, $timeout, Session, $log, colFilters, $rootScope, $modal) {

  var vm = this;

  vm.service = Service;
  vm.api_url = Session.host;
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
            $.each(data.data['format_types'], function(ke, val){
              vm.model_data['format_types'].push(ke);
              });
          } else {
            vm.model_data = {};
            Service.showNoty(data.data.message);
          }
        })
        vm.imei="";
      }
    }

    vm.generate_barcodes = function(form) {
      if(form.$valid) {
        var elem = $("form").serializeArray();
         elem.push({name: 'wms_code', value: vm.model_data['sku_details']['sku_code']})
         elem.push({name: 'quantity', value: 1})
         elem.push({name: 'imei', value: vm.model_data['imei']})
        vm.service.apiCall('generate_barcodes/', 'POST', elem, true).then(function(data){
        if (data.message && data.data !== '"Failed"'){
          url = data.data
          var href_url =  vm.api_url+url.slice(1, -1);
          console.log(href_url);
          var downloadpdf = $('<a id="downloadpdf" target="_blank" href='+href_url+' >');

          $('body').append(downloadpdf);

          document.getElementById("downloadpdf").click();

          $("#downloadpdf").remove();
          console.log(data);

        }else{
          Service.showNoty("Failed");
        }
        })
      }
    }

}

angular.module('urbanApp')
  .controller('IMEITrackerCtrl', ['$scope', '$http', 'Service', '$state', '$timeout', 'Session', '$log', 'colFilters', '$rootScope', '$modal', IMEITrackerCtrl])
