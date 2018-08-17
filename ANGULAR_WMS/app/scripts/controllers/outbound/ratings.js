'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('RatingsCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
  var vm = this;
  vm.apply_filters = colFilters;
  vm.service = Service;
  vm.priceband_sync = Session.roles.permissions.priceband_sync;

  vm.filters = {'datatable': 'RatingsTable', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':'',
                'search6':''}
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
     .withPaginationType('full_numbers')
     .withOption('rowCallback', rowCallback)
     .withOption('initComplete', function( settings ) {
       vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
     });

  vm.dtColumns = [
      DTColumnBuilder.newColumn('Order Id').withTitle('Order Id'),
      DTColumnBuilder.newColumn('Customer Name').withTitle('Customer Name'),
      DTColumnBuilder.newColumn('Invoice Value').withTitle('Invoice Value'),
      DTColumnBuilder.newColumn('Rating For Order Experience').withTitle('Rating For Order Experience'),
      DTColumnBuilder.newColumn('Reason For Order Experience').withTitle('Reason For Order Experience'),
      DTColumnBuilder.newColumn('Rating For Product').withTitle('Rating For Product'),
      DTColumnBuilder.newColumn('Reason For Product').withTitle('Reason For Order Experience'),
  ];

  vm.dtInstance = {};

  $scope.$on('change_filters_data', function(){
    vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
    vm.service.refresh(vm.dtInstance);
  });

  function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
    $('td', nRow).unbind('click');
    $('td', nRow).bind('click', function() {
      $scope.$apply(function() {

        vm.service.apiCall('get_ratings_details/', 'POST', aData).then(function(data){

          if(data.message) {

            vm.title = 'Rating Details';
            vm.model_data.data = data.data.data;
            $state.go('app.outbound.Ratings.Details');
          }
        });
      });
    });
  }

  vm.model_data = {};

  vm.close = function() {

    $state.go('app.outbound.Ratings');
  }
}

