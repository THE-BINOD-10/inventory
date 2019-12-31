'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('StockSummaryReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.service.print_enable = false;
    vm.central_order_mgmt = Session.roles.permissions.central_order_mgmt
    vm.parent_username = Session.parent.userName
    vm.industry_type = Session.user_profile.industry_type;
    vm.user_type = Session.user_profile.user_type;
    vm.warehouse_type = Session.user_profile.warehouse_type;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'get_stock_summary_report/',
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
        DTColumnBuilder.newColumn('Description').withTitle('Description'),
        DTColumnBuilder.newColumn('Brand').withTitle('Brand'),
        DTColumnBuilder.newColumn('Category').withTitle('Category'),
        DTColumnBuilder.newColumn('SKU Sub Category').withTitle('SKU Sub Category'),
        DTColumnBuilder.newColumn('Stage').withTitle('Stage'),
        DTColumnBuilder.newColumn('Stage Quantity').withTitle('Stage Quantity')

    ];
    if(vm.warehouse_type == 'admin'){
      vm.dtColumns.push(DTColumnBuilder.newColumn('Stock Value').withTitle('Stock Value'),
        DTColumnBuilder.newColumn('Warehouse Name').withTitle('Warehouse Name'))
    }

    if (vm.industry_type == "FMCG" && vm.user_type == "marketplace_user") {
      vm.dtColumns.splice(5, 0, DTColumnBuilder.newColumn('Manufacturer').withTitle('Manufacturer'))
      vm.dtColumns.splice(6, 0, DTColumnBuilder.newColumn('Searchable').withTitle('Searchable'))
      vm.dtColumns.splice(7, 0, DTColumnBuilder.newColumn('Bundle').withTitle('Bundle'))

    }

    vm.dtInstance = {};

    vm.empty_data = {
                    'sku_code': '',
                    'brand': '',
                    'stage': '',
                    'sister_warehouse': ''
                    };

   vm.data = {brands: [], stages_list: [], warehouse_groups: [], sku_category:[]}

   vm.model_data = {};
   angular.copy(vm.empty_data, vm.model_data);

   vm.service.apiCall('get_sku_categories_list/').then(function(data){
     if(data.message) {
       angular.copy(data.data, vm.data)
     }
   })

   vm.service.apiCall('sku_category_list/').then(function(data){
      if(data.message) {
        vm.sku_groups = data.data.categories;
      }
    })

  }
