'use strict';

var apps1 = angular.module('urbanApp', ['datatables']);
apps1.controller('AutoSellableCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.selected = {};
    vm.generate_data = [];
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.permissions = Session.roles.permissions;
    vm.industry_type = Session.user_profile.industry_type;
    vm.user_type = Session.user_profile.user_type;

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
        }).withPaginationType('full_numbers')

	vm.dtColumns = [
      DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
          .renderWith(function(data, type, full, meta) {
              if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                vm.selected = {};
              }
              vm.selected[meta.row] = vm.selectAll;
              return vm.service.frontHtml + meta.row + vm.service.endHtml;
              // return vm.frontHtml + meta.row + vm.endHtml;
          }).notSortable(),
      DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
      DTColumnBuilder.newColumn('Product Description').withTitle('Product Description'),
      DTColumnBuilder.newColumn('Source Location').withTitle('Source Location'),
      DTColumnBuilder.newColumn('Suggested Quantity').withTitle('Suggested Quantity'),
      DTColumnBuilder.newColumn('Destination Location').withTitle('Destination Location').notSortable(),
		  DTColumnBuilder.newColumn('Quantity').withTitle('Quantity').notSortable(),
    ];

    if (vm.user_type == 'marketplace_user') {
        vm.dtColumns.splice(1, 0, DTColumnBuilder.newColumn('Seller ID').withTitle('Seller ID'));
        vm.dtColumns.splice(2, 0, DTColumnBuilder.newColumn('Seller Name').withTitle('Seller Name'));
    }

    if (vm.industry_type == 'FMCG') {
        vm.dtColumns.splice(3, 0, DTColumnBuilder.newColumn('Batch No').withTitle('Batch No'));
        vm.dtColumns.splice(4, 0, DTColumnBuilder.newColumn('MRP').withTitle('MRP'));
    }

    vm.dtInstance = function(instance) {
   		vm.dtInstance = instance
	}

    vm.reloadData = reloadData;

    function reloadData () {
      vm.dtInstance.reloadData();
      //vm.bt_disable = true;
    };

  vm.confirm = confirm;
  function confirm() {
    vm.bt_disable = true;
    for(var key in vm.selected){
      console.log(vm.selected[key]);
      if(vm.selected[key]) {
        vm.generate_data.push(vm.dtInstance.DataTable.context[0].aoData[key]._aData);
      }
    }
    if(vm.generate_data.length > 0) {
      var elem = {selctedData: vm.generate_data};
      vm.service.apiCall('auto_sellable_confirm/', 'POST', elem).then(function(data){
        if(data.message) {
          colFilters.showNoty(data.data);
          reloadData();
          vm.bt_disable = true;
        }
      });
      vm.generate_data = [];
    } else {

      vm.bt_disable = false;
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
