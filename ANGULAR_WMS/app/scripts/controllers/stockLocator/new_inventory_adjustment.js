'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('NewInventoryModificationAdjustmentCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.permissions = Session.roles.permissions;
    vm.pallet_switch = (vm.permissions.pallet_switch == true) ? true: false;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              xhrFields: {
                withCredentials: true
              },
              data: {'datatable': 'InventoryModification', 'special_key':'adj'}
           })
       .withDataProp('data')
       .withOption('drawCallback', function(settings) {
         vm.service.make_selected(settings, vm.selected);
       })
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withOption('createdRow', function(row, data, dataIndex) {
            $compile(angular.element(row).contents())($scope);
        })
        .withOption('headerCallback', function(header) {
            if (!vm.headerCompiled) {
                vm.headerCompiled = true;
                $compile(angular.element(header).contents())($scope);
            }
        }).withPaginationType('full_numbers');

	vm.dtColumns = [
        DTColumnBuilder.newColumn('WMS Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('Product Description').withTitle('Description'),
        DTColumnBuilder.newColumn('SKU Class').withTitle('SKU Class'),
        DTColumnBuilder.newColumn('SKU Category').withTitle('Category'),
        DTColumnBuilder.newColumn('SKU Brand').withTitle('Brand'),
        DTColumnBuilder.newColumn('Available Quantity').withTitle('Available Qty'),
	    DTColumnBuilder.newColumn('Reserved Quantity').withTitle('Reserved Qty'),
		DTColumnBuilder.newColumn('Total Quantity').withTitle('Total Qty'),
		DTColumnBuilder.newColumn('Addition').withTitle('Addition'),
        DTColumnBuilder.newColumn('Reduction').withTitle('Reduction'),
        DTColumnBuilder.newColumn(' ').withTitle(''),
    ];

	vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
      vm.dtInstance.reloadData();
      vm.bt_disable = true;
    };
}
