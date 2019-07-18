'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('InventoryAgingCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.service.print_enable = false;
    vm.parent_username = Session.parent.userName

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'get_inventory_aging_filter/',
              type: 'POST',
              data: {'datatable': 'InventoryAging'},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers');

    vm.dtColumns = [
        DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('SKU Description').withTitle('SKU Description'),
        DTColumnBuilder.newColumn('SKU Category').withTitle('SKU Category'),
        DTColumnBuilder.newColumn('Location').withTitle('Location'),
        DTColumnBuilder.newColumn('Quantity').withTitle('Quantity'),
        DTColumnBuilder.newColumn('As on Date(Days)').withTitle('As on Date(Days)')
    ];
    if(vm.parent_username == 'isprava_admin'){
      vm.dtColumns.push(DTColumnBuilder.newColumn('Warehouse').withTitle('Warehouse Name'))
    }

    vm.dtInstance = {};

    var fromDate = new Date(new Date().getFullYear(), new Date().getMonth() - 1, new Date().getDate()).toLocaleDateString('en-US');

    vm.empty_data = { 
                    'from_date': fromDate,
                    'to_date': '',
                    'sku_code': '',
                    'sku_category': '',
                    'sister_warehouse': ''
                    };
    vm.model_data = {};
    angular.copy(vm.empty_data, vm.model_data);

    vm.sku_groups = [];
    vm.warehouse_groups = [];
    vm.service.apiCall('sku_category_list/').then(function(data){
      if(data.message) {
        vm.sku_groups = data.data.categories;
        vm.warehouse_groups = data.data.sister_warehouses;
      }
    })
  }

