FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('StockSummaryPlantCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.industry_type = Session.user_profile.industry_type;
    // vm.date = new Date();
    vm.extra_width = {width:'1100px'};

    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.conf_disable = false;
    vm.datatable = Data.datatable;
    // vm.datatable = 'ReturnToVendor';
    vm.user_type = Session.user_profile.user_type;

    vm.filters = {'datatable': 'StockSummaryPlant', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': ''
                  , 'search5': '', 'search6': '', 'search7': ''};
    vm.model_data = {}
    vm.model_data['filters'] = {'datatable': 'StockSummaryPlant'};

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
     .withOption('drawCallback', function(settings) {
       vm.service.make_selected(settings, vm.selected);
     })
     .withOption('processing', true)
     .withOption('serverSide', true)
     .withOption('createdRow', function(row, data, dataIndex) {
          $compile(angular.element(row).contents())($scope);
      })
      .withOption('headerCallback', function(header) {
          if (!vm.headerCompiled) {
              vm.headerCompiled = true;
              $compile(angular.element(header).contents())($scope);
          }
      })
     .withPaginationType('full_numbers')
     .withOption('initComplete', function( settings ) {
       vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
     });
    vm.dtColumns = [
        DTColumnBuilder.newColumn('Plant Code').withTitle('Plant Code'),
        DTColumnBuilder.newColumn('Plant Name').withTitle('Plant Name'),
        DTColumnBuilder.newColumn('Total Stock Value').withTitle('Total Stock Value'),
        DTColumnBuilder.newColumn('Average Monthly Consumption Value').withTitle('Average Monthly Consumption Value'),
        DTColumnBuilder.newColumn('Days of Cover Value').withTitle('Days of Cover Value'),
        DTColumnBuilder.newColumn('Excess Stock Value').withTitle('Excess Stock Value')
    ];


    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    vm.reloadData = function () {
      $('.custom-table').DataTable().draw();
    };

    vm.filter_enable = true;
    vm.print_enable = false;
    vm.update = false;
    vm.dis = true;



    vm.reset_filters = function(){

      vm.model_data['filters'] = {};
      vm.model_data.filters['datatable'] = 'StockSummaryPlant';
    }

    vm.empty_filter_fields = function(){


      if (Data.rtv_filters) {

        vm.model_data['filters'] = Data.rtv_filters;
      } else {

        vm.model_data['filters'] = {};
        vm.model_data.filters['sku_code'] = '';
        vm.model_data.filters['datatable'] = 'StockSummaryPlant';
      }
    }

    vm.saveFilters = function(filters){
      Data.rtv_filters = filters;
    }


}

})();
