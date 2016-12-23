'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SupplierWisePOsCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

    var vm = this;
    vm.service = Service;
    vm.service.print_enable = false;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'get_supplier_details/',
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
        DTColumnBuilder.newColumn('Order Date').withTitle('Order Date'),
        DTColumnBuilder.newColumn('PO Number').withTitle('PO Number'),
        DTColumnBuilder.newColumn('Supplier Name').withTitle('Supplier Name'),
        DTColumnBuilder.newColumn('WMS Code').withTitle('WMS Code'),
        DTColumnBuilder.newColumn('Design').withTitle('Design'),
        DTColumnBuilder.newColumn('Ordered Quantity').withTitle('Ordered Quantity'),
        DTColumnBuilder.newColumn('Received Quantity').withTitle('Received Quantity'),
        DTColumnBuilder.newColumn('Status').withTitle('Status')
    ];

   vm.dtInstance = {};

   vm.empty_data = {
                    'supplier': ''
                    };

   vm.model_data = {};

   vm.model_data = {};
   angular.copy(vm.empty_data, vm.model_data);

   vm.suppliers = {};
   vm.service.apiCall('get_supplier_list/').then(function(data){
      if(data.message) {
        vm.suppliers = data.data.suppliers;
      }
   })

  }

