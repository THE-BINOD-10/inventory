'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('AgingReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

    var vm = this;
    vm.service = Service;
    vm.service.print_enable = false;
    vm.industry_type = Session.user_profile.industry_type;
    vm.user_type = Session.user_profile.user_type;


    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'get_ageing_data_filter/',
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
      DTColumnBuilder.newColumn('Plant Code').withTitle('Plant Code'),
      DTColumnBuilder.newColumn('Plant Name').withTitle('Plant Name'),
      DTColumnBuilder.newColumn('SKU Code').withTitle('Material Code'),
//        DTColumnBuilder.newColumn('WMS Code').withTitle('WMS Code'),
      DTColumnBuilder.newColumn('Product Description').withTitle('Material Description'),
      DTColumnBuilder.newColumn('SKU Category').withTitle('SKU Category'),
      DTColumnBuilder.newColumn('Sku Brand').withTitle('Sku Brand'),
      DTColumnBuilder.newColumn('pcf').withTitle('Conversion Factor'),
      DTColumnBuilder.newColumn('Purchase UOM').withTitle('Purchase UOM'),
      DTColumnBuilder.newColumn('Purchase Quantity').withTitle('Purchase Quantity'),
      DTColumnBuilder.newColumn('Base UOM').withTitle('Base UOM'),
      DTColumnBuilder.newColumn('Base Quantity').withTitle('Base Quantity'),
      DTColumnBuilder.newColumn('Batch Number').withTitle('Batch Number'),
      DTColumnBuilder.newColumn('Expiry Range').withTitle('Expiry Range'),
    ];
    if (vm.industry_type == "FMCG" && vm.user_type == "marketplace_user") {
      vm.dtColumns.splice(5, 0, DTColumnBuilder.newColumn('Manufacturer').withTitle('Manufacturer'))
      vm.dtColumns.splice(6, 0, DTColumnBuilder.newColumn('Searchable').withTitle('Searchable'))
      vm.dtColumns.splice(7, 0, DTColumnBuilder.newColumn('Bundle').withTitle('Bundle'))

    }

    vm.dtInstance = {};

    vm.empty_data = {
                    'sku_code': '',
                    'sku_category': '',
                    'sku_type': '',
                    'sku_class': '',
//                    'wms_code': '',
                    'sub_category':'',
                    'sku_brand':'',
                    'manufacturer':'',
                    'searchable':'',
                    'bundle':'',
                    'plant_code': ''
                    };

   vm.sku_groups = [0, 123, 23, 1234]

   vm.model_data = {};
   angular.copy(vm.empty_data, vm.model_data);

   vm.service.apiCall('sku_category_list/').then(function(data){
      if(data.message) {
        vm.sku_groups = data.data.categories;
      }
    })
  }
