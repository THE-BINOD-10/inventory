'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('InventoryAgingCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.service.print_enable = false;
    vm.industry_type = Session.user_profile.industry_type;
    vm.user_type = Session.user_profile.user_type;
    vm.parent_username = Session.parent.userName
    vm.central_order_mgmt = Session.roles.permissions.central_order_mgmt
    vm.warehouse_type = Session.user_profile.warehouse_type;
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
        DTColumnBuilder.newColumn('SKU Sub Category').withTitle('SKU Sub Category'),
        DTColumnBuilder.newColumn('Sku Brand').withTitle('Sku Brand'),
        DTColumnBuilder.newColumn('Location').withTitle('Location'),
        DTColumnBuilder.newColumn('Quantity').withTitle('Quantity'),
        DTColumnBuilder.newColumn('As on Date(Days)').withTitle('As on Date(Days)')
    ];
    if(vm.warehouse_type == 'admin'){
      vm.dtColumns.push(DTColumnBuilder.newColumn('Warehouse').withTitle('Warehouse Name'))
    }
    if (vm.industry_type == "FMCG" && vm.user_type == "marketplace_user") {
      vm.dtColumns.splice(5, 0, DTColumnBuilder.newColumn('Manufacturer').withTitle('Manufacturer'))
      vm.dtColumns.splice(6, 0, DTColumnBuilder.newColumn('Searchable').withTitle('Searchable'))
      vm.dtColumns.splice(7, 0, DTColumnBuilder.newColumn('Bundle').withTitle('Bundle'))

    }


    vm.dtInstance = {};

    var fromDate = new Date(new Date().getFullYear(), new Date().getMonth() - 1, new Date().getDate()).toLocaleDateString('en-US');

    vm.empty_data = {
                    'from_date': fromDate,
                    'to_date': '',
                    'sku_code': '',
                    'sku_category': '',
                    'sister_warehouse': '',
                    'sub_category':'',
                    'sku_brand':'',
                    'manufacturer':'',
                    'searchable':'',
                    'bundle':'',
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
