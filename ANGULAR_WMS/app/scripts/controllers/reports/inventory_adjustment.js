'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('InventoryAdjustmentCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
  var vm = this;
  vm.service = Service;
  vm.service.print_enable = false;

  vm.dtOptions = DTOptionsBuilder.newOptions()
     .withOption('ajax', {
            url: Session.url+'get_inventory_adjust_filter/',
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
    DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
    DTColumnBuilder.newColumn('Location').withTitle('Location'),
    DTColumnBuilder.newColumn('Quantity').withTitle('Quantity'),
    DTColumnBuilder.newColumn('Pallet Code').withTitle('Pallet Code'),
    DTColumnBuilder.newColumn('Date').withTitle('Date'),
    DTColumnBuilder.newColumn('Remarks').withTitle('Remarks')
  ];

  vm.dtInstance = {};

  var fromDate = new Date(new Date().getFullYear(), new Date().getMonth() - 1, new Date().getDate()).toLocaleDateString('en-US');


  vm.empty_data = {
                    'from_date': fromDate,
                    'to_date': '',
                    'sku_code': '',
                    'wms_code': '',
                    'location': ''
                    };
  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data); 
}