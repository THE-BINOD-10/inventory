'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('DailyProductionCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.service.print_enable = false;
    vm.industry_type = Session.user_profile.industry_type;
    vm.user_type = Session.user_profile.user_type;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'get_daily_production_report/',
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
        DTColumnBuilder.newColumn('Date').withTitle('Date'),
        DTColumnBuilder.newColumn('Job Order').withTitle('Job Order'),
        DTColumnBuilder.newColumn('JO Creation Date').withTitle('JO Creation Date'),
        DTColumnBuilder.newColumn('SKU Class').withTitle('SKU Class'),
        DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('Brand').withTitle('Brand'),
        DTColumnBuilder.newColumn('SKU Category').withTitle('SKU Category'),
        DTColumnBuilder.newColumn('SKU Sub Category').withTitle('SKU Sub Category'),
        DTColumnBuilder.newColumn('Total JO Quantity').withTitle('Total JO Quantity'),
        DTColumnBuilder.newColumn('Reduced Quantity').withTitle('Reduced Quantity'),
        DTColumnBuilder.newColumn('Stage').withTitle('Stage')
    ];

    if (vm.industry_type == "FMCG" && vm.user_type == "marketplace_user") {
      vm.dtColumns.splice(8, 0, DTColumnBuilder.newColumn('Manufacturer').withTitle('Manufacturer'))
      vm.dtColumns.splice(9, 0, DTColumnBuilder.newColumn('Searchable').withTitle('Searchable'))
      vm.dtColumns.splice(10, 0, DTColumnBuilder.newColumn('Bundle').withTitle('Bundle'))

    }

    vm.dtInstance = {};

    var fromDate = new Date(new Date().getFullYear(), new Date().getMonth() - 1, new Date().getDate()).toLocaleDateString('en-US');

    vm.empty_data = {
                    'from_date': fromDate,
                    'to_date': '',
                    'sku_code': '',
                    'sku_brand': '',
                    'sku_category': '',
                    };


    vm.data = {brands: [], stages_list: []}

    vm.model_data = {};
    angular.copy(vm.empty_data, vm.model_data);

    vm.service.apiCall('get_sku_categories_list/').then(function(data){
      if(data.message) {
        angular.copy(data.data, vm.data)
      }
    })
  }
