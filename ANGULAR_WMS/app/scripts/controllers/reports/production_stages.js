'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('StockSummaryReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.service.print_enable = false;
    vm.central_order_mgmt = Session.roles.permissions.central_order_mgmt
     vm.parent_username = Session.parent.userName

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
        DTColumnBuilder.newColumn('Stage').withTitle('Stage'),
        DTColumnBuilder.newColumn('Stage Quantity').withTitle('Stage Quantity')
        
    ];
    if(vm.parent_username == 'isprava_admin'){
      vm.dtColumns.push(DTColumnBuilder.newColumn('Stock Value').withTitle('Stock Value'),
        DTColumnBuilder.newColumn('Warehouse').withTitle('Warehouse Name'))
    }

    vm.dtInstance = {};

    vm.empty_data = {
                    'sku_code': '',
                    'brand': '',
                    'stage': '',
                    'sister_warehouse': ''
                    };

   vm.data = {brands: [], stages_list: [], warehouse_groups: []}

   vm.model_data = {};
   angular.copy(vm.empty_data, vm.model_data);

   vm.service.apiCall('get_sku_categories_list/').then(function(data){
     if(data.message) {
       angular.copy(data.data, vm.data)
     }
   })

  }

