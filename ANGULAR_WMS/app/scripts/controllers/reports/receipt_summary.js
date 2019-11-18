'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ReceiptSummaryCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

    var vm = this;
    vm.service = Service;
    vm.service.print_enable = false;
    vm.permissions = Session.roles.permissions;
    vm.industry_type = Session.user_profile.industry_type;
    vm.user_type = Session.user_profile.user_type;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'get_receipt_filter/',
              type: 'GET',
              data: vm.model_data,
              xhrFields: {
                withCredentials: true
              },
              data: vm.model_data
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers');

    vm.dtColumns = [
        DTColumnBuilder.newColumn('Supplier').withTitle('Supplier'),
        DTColumnBuilder.newColumn('PO Reference').withTitle('PO Number'),
        DTColumnBuilder.newColumn('WMS Code').withTitle('WMS Code'),
        DTColumnBuilder.newColumn('SKU Category').withTitle('SKU Category'),
        DTColumnBuilder.newColumn('SKU Sub Category').withTitle('SKU Sub Category'),
        DTColumnBuilder.newColumn('Sku Brand').withTitle('Sku Brand'),
        DTColumnBuilder.newColumn('Description').withTitle('Description'),
        //DTColumnBuilder.newColumn('Received Quantity').withTitle('Received Quantity')
    ];

    if (vm.industry_type == "FMCG" && vm.user_type == "marketplace_user") {
      vm.dtColumns.splice(6, 0, DTColumnBuilder.newColumn('Manufacturer').withTitle('Manufacturer'))
      vm.dtColumns.splice(7, 0, DTColumnBuilder.newColumn('Searchable').withTitle('Searchable'))
      vm.dtColumns.splice(8, 0, DTColumnBuilder.newColumn('Bundle').withTitle('Bundle'))

    }

  if(vm.permissions.use_imei){
    vm.dtColumns.push(DTColumnBuilder.newColumn('Serial Number').withTitle('Serial Number'));
  }
  else {
    vm.dtColumns.push(DTColumnBuilder.newColumn('Received Quantity').withTitle('Received Quantity'));
  }
  vm.dtColumns.push(DTColumnBuilder.newColumn('Received Date').withTitle('Received Date'))
  vm.dtColumns.push(DTColumnBuilder.newColumn('Closing Reason').withTitle('Closing Reason'))
  vm.dtColumns.push(DTColumnBuilder.newColumn('Updated User').withTitle('Updated User'))
  vm.dtInstance = {};

  var fromDate = new Date(new Date().getFullYear(), new Date().getMonth() - 1, new Date().getDate()).toLocaleDateString('en-US');

  vm.empty_data = {
                    'from_date': fromDate,
                    'to_date': '',
                    'wms_code': '',
                    'supplier': '',
                    'sku_code': '',
                    'sku_category':'',
                    'sub_category':'',
                    'sku_brand':'',
                    'manufacturer':'',
                    'searchable':'',
                    'bundle':'',
                    };

  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);

  vm.suppliers = {};

  vm.service.apiCall('get_supplier_list/').then(function(data){
      if(data.message) {
        vm.suppliers = data.data.suppliers;
      }
   })
}
