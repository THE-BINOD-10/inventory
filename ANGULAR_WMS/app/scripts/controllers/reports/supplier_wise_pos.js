'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SupplierWisePOsCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

    var vm = this;
    vm.service = Service;
    vm.service.print_enable = false;
    vm.tb_data = {}
    vm.total_data = {positions:[7], keys:{7: 'total_charge'}}
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'get_supplier_details/',
              type: 'GET',
              data: vm.model_data,
              xhrFields: {
                withCredentials: true
              },
              data: vm.model_data,
              complete: function(jqXHR, textStatus) {
                $scope.$apply(function(){
                  angular.copy(JSON.parse(jqXHR.responseText), vm.tb_data)
                })
              }
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('initComplete', function( settings ) {
         var html = vm.service.add_totals(settings.aoColumns.length, vm.total_data)
         $(".dataTable > thead").prepend(html)
         $compile(angular.element(".totals_row").contents())($scope);
       });

    vm.dtColumns = [
        DTColumnBuilder.newColumn('Order Date').withTitle('Order Date'),
        DTColumnBuilder.newColumn('PO Number').withTitle('PO Number'),
        DTColumnBuilder.newColumn('Supplier Name').withTitle('Supplier Name'),
        DTColumnBuilder.newColumn('WMS Code').withTitle('WMS Code'),
        DTColumnBuilder.newColumn('Design').withTitle('Design'),
        DTColumnBuilder.newColumn('Ordered Quantity').withTitle('Ordered Quantity'),
        DTColumnBuilder.newColumn('Received Quantity').withTitle('Received Quantity'),
        DTColumnBuilder.newColumn('Amount').withTitle('Amount'),
        DTColumnBuilder.newColumn('Status').withTitle('Status')
    ];

   vm.dtInstance = {};

   vm.empty_data = {
                    'supplier': ''
                    };

   vm.model_data = {};

   angular.copy(vm.empty_data, vm.model_data);

   vm.suppliers = {};
   vm.service.apiCall('get_supplier_list/').then(function(data){
      if(data.message) {
        vm.suppliers = data.data.suppliers;
      }
   })

  }

