'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('targetsTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.user_type = Session.roles.permissions.user_type;
    vm.filters = {'datatable': 'Targets', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':''}
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: vm.filters,
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers');
    vm.dtColumns = [
        DTColumnBuilder.newColumn('date').withTitle('Date'),
        DTColumnBuilder.newColumn('order_id').withTitle('Order ID'),
        DTColumnBuilder.newColumn('zone').withTitle('Zone'),
        DTColumnBuilder.newColumn('city').withTitle('City'),
        DTColumnBuilder.newColumn('distributor').withTitle('Distributor'),
        DTColumnBuilder.newColumn('total_purchase_value').withTitle('Total Purchase Value'),
        DTColumnBuilder.newColumn('tax_amt').withTitle('Tax Value'),
        DTColumnBuilder.newColumn('total_amt').withTitle('Total Amount')
    ];
}