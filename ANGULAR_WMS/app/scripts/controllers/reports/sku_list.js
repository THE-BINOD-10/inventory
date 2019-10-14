'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SKUListCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.service.print_enable = false;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'get_sku_filter/',
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
        DTColumnBuilder.newColumn('WMS Code').withTitle('WMS Code'),
        DTColumnBuilder.newColumn('SKU Group').withTitle('SKU Group'),
        DTColumnBuilder.newColumn('SKU Type').withTitle('SKU Type'),
        DTColumnBuilder.newColumn('SKU Category').withTitle('SKU Category'),
        DTColumnBuilder.newColumn('SKU Sub Category').withTitle('SKU Sub Category'),
        DTColumnBuilder.newColumn('SKU Brand').withTitle('SKU Brand'),
        DTColumnBuilder.newColumn('SKU Class').withTitle('SKU Class'),
        DTColumnBuilder.newColumn('Put Zone').withTitle('Put Zone'),
        DTColumnBuilder.newColumn('Threshold Quantity').withTitle('Threshold Quantity')
    ];

    vm.dtInstance = {};

    vm.empty_data = {
                    'sku_code': '',
                    'sku_category': '',
                    'sku_type': '',
                    'sku_class': '',
                    'wms_code': '',
                    'sub_category':'',
                    'sku_brand':'',
                    };

   vm.sku_groups = []

   vm.model_data = {};
   angular.copy(vm.empty_data, vm.model_data);

   vm.service.apiCall('sku_category_list/').then(function(data){
     if(data.message) {
       vm.sku_groups = data.data.categories;
     }
   })

  }
