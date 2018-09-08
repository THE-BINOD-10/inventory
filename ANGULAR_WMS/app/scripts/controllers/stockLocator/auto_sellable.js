'use strict';

var apps1 = angular.module('urbanApp', ['datatables']);
apps1.controller('AutoSellableCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.permissions = Session.roles.permissions;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              xhrFields: {
                withCredentials: true
              },
              data: {'datatable': 'AutoSellableSuggestion', 'special_key':'adj'}
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
		DTColumnBuilder.newColumn('Location').withTitle('Location'),
        DTColumnBuilder.newColumn('Product Description').withTitle('Description'),
        DTColumnBuilder.newColumn('SKU Class').withTitle('SKU Class'),
        DTColumnBuilder.newColumn('SKU Category').withTitle('Category'),
        DTColumnBuilder.newColumn('SKU Brand').withTitle('Brand'),
        DTColumnBuilder.newColumn('Available Quantity').withTitle('Available Qty').notSortable(),
	    DTColumnBuilder.newColumn('Reserved Quantity').withTitle('Reserved Qty').notSortable(),
		DTColumnBuilder.newColumn('Total Quantity').withTitle('Total Qty').notSortable(),
		DTColumnBuilder.newColumn('Addition').withTitle('Addition').notSortable(),
        DTColumnBuilder.newColumn('Reduction').withTitle('Reduction').notSortable(),
        DTColumnBuilder.newColumn(' ').withTitle('').notSortable(),
    ];

    vm.dtInstance = function(instance) {
   		vm.dtInstance = instance
	}

    vm.reloadData = reloadData;

    function reloadData () {
      vm.dtInstance.reloadData();
      //vm.bt_disable = true;
    };
}

apps1.directive("limitToMax", function() {
  return {
    link: function(scope, element, attributes) {
      element.on("keydown keyup", function(e) {
	  element.val(Math.abs(element.val()))
    if (Number(element.val()) > Number(attributes.max) &&
          e.keyCode != 46 // delete
          &&
          e.keyCode != 8 // backspace
        ) {
          e.preventDefault();
          element.val(attributes.max);
        }
      });
    }
  };
});
