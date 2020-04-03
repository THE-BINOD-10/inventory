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
    vm.bt_disable = true;

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
       .withOption('order', [1, 'asc'])
       .withOption('drawCallback', function(settings) {
         vm.service.make_selected(settings, vm.selected);
       })
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
        DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
              if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                  vm.selected = {};
                }
              vm.selected[meta.row] = vm.selectAll;
              vm.seleted_rows.push(full);
              return vm.service.frontHtml + meta.row + vm.service.endHtml;
            }),
        DTColumnBuilder.newColumn('wms_code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('zone').withTitle('Zone'),
        DTColumnBuilder.newColumn('location').withTitle('Location'),
        DTColumnBuilder.newColumn('quantity').withTitle('Quantity')
    ];

    vm.seleted_rows = []
    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
      $('.custom-table').DataTable().draw();
    };

    $scope.$on('change_filters_data', function(){
      if($("#"+vm.dtInstance.id+":visible").length != 0) {
        vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
        vm.bt_disable = false;
        vm.reloadData();
      }
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        if(vm.filter_enable){
          vm.filter_enable = false;
          vm.apply_filters.add_search_boxes();
        }
        return nRow;
    }

    vm.filter_enable = true;

    vm.close = close;
    function close() {
      vm.bt_disable = true;
      $state.go('app.stockLocator.CycleCount')
    }

    vm.update = true;
    vm.model_data = {};
    vm.generate_filter = {'wms_code':'','zone':'','location':'','quantity':''}
    vm.generate_filter_en = false;
    vm.generate_data = []
    vm.generate_cycle = generate_cycle;
    function generate_cycle() {
      vm.bt_disable = true;
      for(var key in vm.selected){
        if(vm.selected[key]) {
          vm.generate_data.push(vm.dtInstance.DataTable.context[0].aoData[Number(key)]["_aData"]);
        }
      }
      if(vm.generate_data.length > 0) {
        vm.confirm_disable = false;
        console.log("call");
        vm.generate_filter_en = false;
        var data = '';
        for(var i=0; i< vm.generate_data.length; i++) {
          data += $.param(vm.generate_data[i])+"&";
        }
        vm.service.apiCall('confirm_cycle_count/?'+data).then(function(data){
          if(data.message) {
            angular.copy(data.data, vm.model_data);
            $state.go('app.stockLocator.CycleCount.Generate')
            vm.reloadData();
          }
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
        vm.service.apiCall('confirm_cycle_count/', 'GET', vm.generate_filter).then(function(data){
          if(data.message) {
            angular.copy(data.data, vm.model_data);
            $state.go('app.stockLocator.CycleCount.Generate');
            vm.reloadData();
          }
        });
      }
    }

    vm.confirm_disable = false; 
    vm.confirm_cycle = confirm_cycle;
    function confirm_cycle() {
      var data = {}
      for(var i=0;i<vm.model_data.data.length; i++) {
        data[vm.model_data.data[i].id] = vm.model_data.data[i].seen_quantity;
      }
      vm.service.apiCall('submit_cycle_count/', 'GET', data, true).then(function(data){
        if(data.message) {
          if(data.data == "Updated Successfully") {
            vm.close();
            vm.reloadData();
          } else {
            colFilters.showNoty(data.data);
          }
        }
      });
    }

    vm.print = function() {
      var clone = $("#print").clone();
      $(clone).removeClass("hide");
      vm.service.print_data(clone);
    }
  }


