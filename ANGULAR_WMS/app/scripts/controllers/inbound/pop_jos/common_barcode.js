function Barcodes($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items, Data) {

  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;

  var url_get = "get_order_labels/";
  vm.model_data = {};
  vm.model_data['format_types'] = [];
  var key_obj = {};//{'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details', 'Bulk Barcode': 'Details'};
  vm.service.apiCall('get_format_types/').then(function(data){
    $.each(data['data']['data'], function(ke, val){
        vm.model_data['format_types'].push(ke);
        console.log(data['data']['data']);
    });
  });
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

  //vm.barcode_title = 'Barcode Generation';

  if (items.have_data) {
    angular.copy(items, vm.model_data)
  } else {
    vm.getPoData(items);
  }

  vm.ok = function (msg) {

    $modalInstance.close(vm.status_data);
  };

  vm.generate_barcodes = function(form) {
    if(form.$valid) {
      var elem = $("form[name='barcodes']").serializeArray();
      var url = "generate_barcodes/";
      if (vm.permissions.barcode_generate_opt == "sku_serial" && !Data.receive_jo_barcodes) {
        url = "generate_po_labels/";
      } else if (vm.permissions.barcode_generate_opt == "sku_serial" && Data.receive_jo_barcodes) {
        url = "generate_jo_labels/";
      }
      vm.service.apiCall(url, 'POST', elem, true).then(function(data){
        if(data.message && data.data !== '"Failed"') {
          var href_url = Session.host.concat(data.data.slice(1, -1));
          var downloadpdf = $('<a id="downloadpdf" target="_blank" href='+href_url+' >');
          $('body').append(downloadpdf);
          document.getElementById("downloadpdf").click();
          $("#downloadpdf").remove();
        }else{
            vm.service.showNoty("Failed", 'warning');
        }
      })
    }
  }
}

angular
  .module('urbanApp')
  .controller('Barcodes', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', 'Data', Barcodes]);
