'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('BatchLevelStockCtrl',['$scope', '$http', '$state', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, Session, DTOptionsBuilder, DTColumnBuilder, colFilters) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.industry_type = Session.user_profile.industry_type;
    
    vm.filters = {'datatable': 'BatchLevelStock', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':'', 'search6':'', 'search7': '', 'search8': ''}
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
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });
    vm.dtInstance = {};

    vm.reloadData = reloadData;
    function reloadData() {
        this.dtInstance.reloadData();
    }

    vm.dtColumns = [
        DTColumnBuilder.newColumn('Receipt Number').withTitle('Receipt Number'),
        DTColumnBuilder.newColumn('Receipt Date').withTitle('Receipt Date'),
        DTColumnBuilder.newColumn('WMS Code').withTitle('WMS Code'),
        DTColumnBuilder.newColumn('Product Description').withTitle('Product Description'),
        DTColumnBuilder.newColumn('Batch Number').withTitle('Batch Number'),
        DTColumnBuilder.newColumn('MRP').withTitle('MRP'),
        DTColumnBuilder.newColumn('Zone').withTitle('Zone'),
        DTColumnBuilder.newColumn('Location').withTitle('Location'),
        DTColumnBuilder.newColumn('Pallet').withTitle('Pallet'),
        DTColumnBuilder.newColumn('Quantity').withTitle('Quantity'),
        DTColumnBuilder.newColumn('Receipt Type').withTitle('Receipt Type')
    ];

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    // if (vm.permissions.pallet_switch) {
    //   vm.dtColumns.push(DTColumnBuilder.newColumn('Pallet Code').withTitle('Pallet Code'))
    // }

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.reloadData();
    });

  }

