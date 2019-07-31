'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ReplenushmentTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.filters = {'datatable': 'ReplenushmentMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
        DTColumnBuilder.newColumn('classification').withTitle('Classification'),
        DTColumnBuilder.newColumn('size').withTitle('Size'),
        DTColumnBuilder.newColumn('min_days').withTitle('SA Min Days'),
        DTColumnBuilder.newColumn('max_days').withTitle('SA Max Days'),

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
                vm.title = "Update Replenushment";
                vm.message ="";
                $state.go('app.masters.Replenushment.update');
                $timeout(function () {
                  $(".customer_status").val(vm.model_data.status);
                }, 500);
            });
        });
    }

  var empty_data = {classification: "", size: "",min_days: "",max_days :''};
  vm.model_data = {};

  vm.base = function() {

    vm.title = "Add Replenushment";
    vm.update = false;
    angular.copy(empty_data, vm.model_data);
  }
  vm.base();

  vm.close = function() {

    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.Replenushment');
  }

  vm.add = add;
  function add() {

    vm.base();
    $state.go('app.masters.Replenushment.update');
  }

  vm.replenushment_insert = function(url) {
    var send = {}
    var send = $("form").serializeArray()
    var data = $.param(send);
    vm.service.apiCall(url, 'POST', send, true).then(function(data){
      if(data.message) {
        if(data.data == 'Added Successfully' || data.data == 'Updated Successfully') {
          vm.service.refresh(vm.dtInstance);
          vm.close();
        } else {
          vm.service.pop_msg(data.data);
        }
      }
    });
  }

  vm.submit = function(data) {

    if (data.$valid) {
      if ("Add Replenushment" == vm.title) {
        vm.replenushment_insert('insert_replenushment/');
      } else {
        vm.model_data['data-id'] = vm.model_data.DT_RowId;
        vm.replenushment_insert('insert_replenushment/');
      }
    }
  }
}
