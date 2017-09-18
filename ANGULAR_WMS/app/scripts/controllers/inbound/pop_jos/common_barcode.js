function Barcodes($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {

  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;

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

  vm.barcode_title = 'Barcode Generation';

  if (items.have_data) {

    angular.copy(items, vm.model_data)
  } else {
    vm.model_data['format_types'] = ['format1', 'format2', 'format3', 'format4']

    var key_obj = {'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details', 'format4': 'Details'}

    vm.model_data['barcodes'] = [{'sku_code':'', 'quantity':''}];
    vm.getPoData(items);
  }

  vm.ok = function (msg) {
    $modalInstance.close(vm.status_data);
  };

  vm.generate_barcodes = function(form) {
    if(form.$valid) {
      var elem = $("form[name='barcodes']").serializeArray();
      var url = "generate_barcodes/";
      if (vm.permissions.barcode_generate_opt == "sku_serial") {
        url = "generate_po_labels/";
      }
      vm.service.apiCall(url, 'POST', elem, true).then(function(data){
        if(data.message) {
          console.log(data);
          var href_url = data.data;

          var downloadpdf = $('<a id="downloadpdf" target="_blank" href='+href_url+' >');
          $('body').append(downloadpdf);
          document.getElementById("downloadpdf").click();
          $("#downloadpdf").remove();
        }
      })
    }
  }
}

angular
  .module('urbanApp')
  .controller('Barcodes', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', Barcodes]);
