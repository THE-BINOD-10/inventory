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
                console.log(aData);
                $http.get(Session.url+'get_id_cycle/?data_id='+aData.DT_RowId).success(function(data, status, headers, config) {
                   console.log(data)
                   angular.copy(data,vm.model_data);
                   $state.go('app.stockLocator.CycleCount.ConfirmCycle');
                });
            });
        });
        return nRow;
    }

    vm.close = close;
    function close() {
      $state.go('app.stockLocator.CycleCount')
    }

    vm.update = true;
    vm.model_data = {};
    vm.generate_filter = {'wms_code':'','zone':'','location':'','quantity':''}
    vm.generate_filter_en = false;
    vm.generate_data = []
    vm.generate_cycle = generate_cycle;
    function generate_cycle() {
      for(var key in vm.selected){
        console.log(vm.selected[key]);
        if(vm.selected[key]) {
          vm.generate_data.push(vm.seleted_rows[key-1]);
        }
      }
      if(vm.generate_data.length > 0) {
        console.log("call");
        vm.generate_filter_en = false;
        var data = '';
        for(var i=0; i< vm.generate_data.length; i++) {
          data += $.param(vm.generate_data[i])+"&";
        }
        $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
        $http({
               method: 'GET',
               url:Session.url+"confirm_cycle_count/?"+data
               }).success(function(data, status, headers, config) {
               angular.copy(data, vm.model_data);
           console.log("success");$state.go('app.stockLocator.CycleCount.ConfirmCycle')
        });
        console.log(vm.generate_data);
        vm.generate_data = [];
      } else {
        for(var key in vm.dtInstance.DataTable.context[0].ajax.data) {
          if(key != "datatable" ) {
            var value = vm.dtInstance.DataTable.context[0].ajax.data[key]
            if (key == 'search0') {
              vm.generate_filter['wms_code'] = value;
            } else if (key == 'search1') {
              vm.generate_filter['zone'] = value;
            } else if (key == 'search2') {
              vm.generate_filter['location'] = value;
            } else if (key == 'search3') {
              vm.generate_filter['quantity'] = value;
            }
            if (value.length > 0) {
              vm.generate_filter_en = true;
            }
          }
        }
      }
      if (vm.generate_filter_en) {
        vm.generate_filter_en = false;
        var data = $.param(vm.generate_filter);
        $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
        $http({
               method: 'GET',
               url:Session.url+"confirm_cycle_count/?"+data
               }).success(function(data, status, headers, config) {
               angular.copy(data, vm.model_data);
           console.log("success");$state.go('app.stockLocator.CycleCount.ConfirmCycle')
        });  
      }
    }
 
    vm.confirm_cycle = confirm_cycle;
    function confirm_cycle() {
      var data = {}
      for(var i=0;i<vm.model_data.data.length; i++) {
        data[vm.model_data.data[i].id] = vm.model_data.data[i].seen_quantity;
      }
      var data = $.param(data);
        $http({
               method: 'GET',
               url:Session.url+"submit_cycle_count/?"+data
               }).success(function(data, status, headers, config) {
          console.log("succss");
          colFilters.showNoty(data);
        });
    }

    vm.print = function() {
      var clone = $(".modal:eq(1) #print").clone();
      $(clone).removeClass("hide");
      colFilters.print_data(clone);
    }
  }


