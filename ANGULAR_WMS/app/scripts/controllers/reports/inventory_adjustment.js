'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('InventoryAdjustmentCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
  var vm = this;
  vm.service = Service;
  vm.service.print_enable = false;
  vm.user_type = Session.user_profile.user_type;
  vm.industry_type = Session.user_profile.industry_type;

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


  if(vm.user_type == 'marketplace_user' && vm.industry_type == 'FMCG') {

    vm.dtColumns = [
      DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
      DTColumnBuilder.newColumn('Name').withTitle('Name'),
      DTColumnBuilder.newColumn('Weight').withTitle('Weight'),
      DTColumnBuilder.newColumn('MRP').withTitle('MRP'),
      DTColumnBuilder.newColumn('Manufacturer').withTitle('Manufacturer'),
      DTColumnBuilder.newColumn('Vendor').withTitle('Vendor'),
      DTColumnBuilder.newColumn('Sheet').withTitle('Sheet'),
      DTColumnBuilder.newColumn('Brand').withTitle('Brand'),
      DTColumnBuilder.newColumn('Category').withTitle('Category'),
      DTColumnBuilder.newColumn('Sub Category').withTitle('Sub Category'),
      DTColumnBuilder.newColumn('Sub Category type').withTitle('Sub Category type'),
      DTColumnBuilder.newColumn('Location').withTitle('Location'),
      DTColumnBuilder.newColumn('Quantity').withTitle('Quantity'),
      DTColumnBuilder.newColumn('Average Cost').withTitle('Average Cost'),
      DTColumnBuilder.newColumn('Value').withTitle('Value'),
      DTColumnBuilder.newColumn('Remarks').withTitle('Reason'),
      DTColumnBuilder.newColumn('User').withTitle('User'),
      DTColumnBuilder.newColumn('Date').withTitle('Transaction Date'),
    ];


  }else {
    vm.dtColumns = [
      DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
      DTColumnBuilder.newColumn('Location').withTitle('Location'),
      DTColumnBuilder.newColumn('Quantity').withTitle('Quantity'),
      DTColumnBuilder.newColumn('Pallet Code').withTitle('Pallet Code'),
      DTColumnBuilder.newColumn('Date').withTitle('Date'),
      DTColumnBuilder.newColumn('Remarks').withTitle('Remarks')
    ];

  }



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
