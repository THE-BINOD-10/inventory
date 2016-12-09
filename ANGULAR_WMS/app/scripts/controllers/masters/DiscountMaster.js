'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('DiscountMasterTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.filters = {'datatable': 'DiscountMaster', 'search0': '', 'search1':'','search2':'','search3':''}
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
        DTColumnBuilder.newColumn('sku').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('category').withTitle('Category'),
        DTColumnBuilder.newColumn('sku_discount').withTitle('SKU Discount'),
        DTColumnBuilder.newColumn('category_discount').withTitle('Category Discount'),
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
                angular.copy(aData, vm.model_data);
                vm.update = true;
                vm.title = "Update Discount";
                $state.go('app.masters.DiscountMaster.Discount');
            });
        });
        return nRow;
    };

    vm.update = false;
    var empty_data = {"sku":"","category":"", "sku_discount":"", "category_discount":""};
    vm.model_data = {};

    vm.base = function() {

      vm.update = false;
      vm.title = "Add Discount";
      angular.copy(empty_data, vm.model_data);
    }
    vm.base();

    vm.close = function() {

      angular.copy(empty_data, vm.model_data);
      $state.go('app.masters.DiscountMaster');
    }

    vm.add = function() {

      vm.base();
      $state.go('app.masters.DiscountMaster.Discount');
    }

  vm.submit = submit;
  function submit(data) {
    if (data.$valid) {
      vm.service.apiCall('insert_discount/', 'POST', vm.model_data).then(function(data){
        if(data.message) {
          if(data.data == 'Updated Successfully') {
            vm.service.refresh(vm.dtInstance);
            vm.close();
          } else {
            vm.service.pop_msg(data.data);
          }
        }
      });
    }
  }

}

