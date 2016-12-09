'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ConfirmCycleCountCtrl',['$scope', '$state', '$http', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $state, $http, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.filters = {'datatable': 'ConfirmCycleCount'}

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
       .withOption('order', [1, 'desc'])
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
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
        .withOption('rowCallback', rowCallback);

    vm.dtColumns = [
        DTColumnBuilder.newColumn('Cycle Count ID').withTitle('Cycle Count ID'),
        DTColumnBuilder.newColumn('Date').withTitle('Date')
    ];

    vm.seleted_rows = []
    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.reloadData();
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
              vm.service.apiCall('get_id_cycle/', 'GET', {data_id: aData.DT_RowId}).then(function(data){
                if(data.message) {
                  angular.copy(data.data,vm.model_data);
                  $state.go('app.stockLocator.CycleCount.ConfirmCycle');
                }
              });
            });
        });
        return nRow;
    }

    vm.close = close;
    function close() {
      $state.go('app.stockLocator.CycleCount')
    }

    vm.model_data = {};
    vm.update = true;
    vm.confirm_disable = false;
    vm.confirm_cycle = confirm_cycle;
    function confirm_cycle() {
      var data = {}
      for(var i=0;i<vm.model_data.data.length; i++) {
        data[vm.model_data.data[i].id] = vm.model_data.data[i].seen_quantity;
      }
      vm.service.apiCall('submit_cycle_count/', 'GET', data).then(function(data){
        if(data.message) {
          if(data.data == "Updated Successfully") {
            reloadData();
            vm.close();
          } else {
            colFilters.showNoty(data);
          }
        }
      });
    }

    vm.print = function() {
      var clone = $(".modal:eq(1) #print").clone();
      $(clone).removeClass("hide");
      vm.service.print_data(clone);
    }
  }


