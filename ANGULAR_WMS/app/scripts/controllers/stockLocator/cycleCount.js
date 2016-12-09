'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CycleCountCtrl',['$scope', '$state', '$http', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $state, $http, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.filters = {'datatable': 'CycleCount', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
    vm.selected = {};
    vm.selectAll = false;
    vm.toggleAll = toggleAll;
    vm.toggleOne = toggleOne;

    var titleHtml = '<input type="checkbox" ng-model="showCase.selectAll" ng-change="showCase.toggleAll(showCase.selectAll, showCase.selected)">';

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
        DTColumnBuilder.newColumn(null).withTitle(titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
              vm.selected[full.id] = false;
              vm.seleted_rows.push(full);
              return '<input type="checkbox" ng-model="showCase.selected[' + data.id + ']" ng-change="showCase.toggleOne(showCase.selected)">';
            }),
        DTColumnBuilder.newColumn('wms_code').withTitle('WMS Code'),
        DTColumnBuilder.newColumn('zone').withTitle('Zone'),
        DTColumnBuilder.newColumn('location').withTitle('Location'),
        DTColumnBuilder.newColumn('quantity').withTitle('Quantity')
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
        if(vm.filter_enable){
          vm.filter_enable = false;
          vm.apply_filters.add_search_boxes();
        }
        return nRow;
    }

  function toggleAll (selectAll, selectedItems, event) {
    for (var id in selectedItems) {
      if (selectedItems.hasOwnProperty(id)) {
        selectedItems[id] = selectAll;
      }
    }
    vm.button_fun();
  }
  function toggleOne (selectedItems) {
    for (var id in selectedItems) {
      if (selectedItems.hasOwnProperty(id)) {
        if(!selectedItems[id]) {
          vm.selectAll = false;
          vm.button_fun();
          return;
        }
      }
    }
   vm.selectAll = true;
   vm.button_fun();
  }

  vm.bt_disable = true;
  vm.button_fun = function() {

    var enable = true
    for (var id in vm.selected) {
      if(vm.selected[id]) {
        vm.bt_disable = false;
        enable = false;
        break;
      }
    }
    if (enable) {
      vm.bt_disable = true;
    }
  }

    vm.filter_enable = true;

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
           console.log("success");$state.go('app.stockLocator.CycleCount.Generate')
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
           console.log("success");$state.go('app.stockLocator.CycleCount.Generate')
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
          vm.reloadData();
        });
    }

    vm.print = function() {
      var clone = $("#print").clone();
      $(clone).removeClass("hide");
      colFilters.print_data(clone);
    }
  }


