'use strict';

var apps1 = angular.module('urbanApp', ['datatables']);
apps1.controller('NewInventoryModificationAdjustmentCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.permissions = Session.roles.permissions;
    vm.pallet_switch = (vm.permissions.pallet_switch == true) ? true: false;

    vm.reduction_edit = true;
    vm.addition_edit = true;
	vm.available_qty_edit = true;
    vm.button_edit = true;

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

	var pallet_column;
	if (vm.pallet_switch) {
		pallet_column = DTColumnBuilder.newColumn('Pallet Code').withTitle('Pallet Code');
	} else {
		pallet_column = DTColumnBuilder.newColumn('Pallet Code').withTitle('Pallet Code').notVisible();
	}

	vm.dtColumns = [
        DTColumnBuilder.newColumn('WMS Code').withTitle('SKU Code'),
		DTColumnBuilder.newColumn('Location').withTitle('Location'),
        pallet_column,
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
      vm.bt_disable = true;
    };

    vm.add_inventory = function() {
        vm.addition_edit = false;
        vm.button_edit = false;
        vm.reduction_edit = true;
		vm.available_qty_edit = true;
    }
    vm.subtract_inventory = function() {
        vm.reduction_edit = false;
        vm.button_edit = false;
        vm.addition_edit = true;
		vm.available_qty_edit = true;
    }
    vm.modify_inventory = function() {
        vm.available_qty_edit = false;
		vm.reduction_edit = true;
		vm.addition_edit = true;
        vm.button_edit = false;
    }
	vm.inv_adj_save_qty = function(id, available_qty, old_available_qty, added_qty, sub_qty) {
		var inventory_adj_data = {}
        var row_data = vm.dtInstance.DataTable.context[0].aoData[id]._aData
		inventory_adj_data['wms_code'] = row_data['WMS Code']
		inventory_adj_data['available_qty'] = available_qty
        inventory_adj_data['old_available_qty'] = old_available_qty
		inventory_adj_data['added_qty'] = added_qty
		inventory_adj_data['sub_qty'] = sub_qty
        inventory_adj_data['pallet_code'] = row_data['Pallet Code']
        inventory_adj_data['location'] = row_data['Location']
		if ( (available_qty != parseInt(old_available_qty)) || (added_qty != 0) || (sub_qty != 0) ) {
			vm.service.apiCall('inventory_adj_modify_qty/', 'POST', inventory_adj_data).then(function(resp) {
              if (resp.data.status) {
				vm.addition_edit = true;
				vm.button_edit = true;
				vm.reduction_edit = true;
				vm.available_qty_edit = true;
				var page = vm.dtInstance.DataTable.page()
				$timeout(function() {
					vm.dtInstance.DataTable.page(page).draw(false);
				},1000)
              }
          })
		}
	}
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
