'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('LocationWiseFilterCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

    var vm = this;
    vm.service = Service;
    vm.service.print_enable = false;
    vm.industry_type = Session.user_profile.industry_type;
    vm.user_type = Session.user_profile.user_type;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'get_location_filter/',
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
        DTColumnBuilder.newColumn('Product Description').withTitle('Product Description'),
        DTColumnBuilder.newColumn('EAN').withTitle('EAN'),
        DTColumnBuilder.newColumn('Zone').withTitle('Zone'),
        DTColumnBuilder.newColumn('Location').withTitle('Location'),
        DTColumnBuilder.newColumn('Available Quantity').withTitle('Available Quantity'),
        DTColumnBuilder.newColumn('Reserved Quantity').withTitle('Reserved Quantity'),
        DTColumnBuilder.newColumn('Total Quantity').withTitle('Total Quantity'),
    ];
    if (vm.industry_type == "FMCG" && vm.user_type == "marketplace_user") {
    	vm.dtColumns.splice(3, 0, DTColumnBuilder.newColumn('MRP').withTitle('MRP'))
    }

  vm.dtInstance = {};

  vm.empty_data = {
                    'sku_code': '',
                    'sku_category': '',
                    'sku_type': '',
                    'sku_class': '',
                    'location': '',
                    'zone_id': '',
                    'wms_code': ''
                    };

  vm.sku_groups = [];

  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);

  vm.service.apiCall('sku_category_list/').then(function(data){
      if(data.message) {
        vm.sku_groups = data.data.categories;
      }
    })

  }

