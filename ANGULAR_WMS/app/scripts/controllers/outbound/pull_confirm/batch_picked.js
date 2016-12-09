'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('BatchPicked',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.selected = {};
    vm.selectAll = false;

    vm.special_key = {status: 'batch_picked'}
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'BatchPicked', 'special_key': JSON.stringify(vm.special_key)},
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
       .withOption('createdRow', function(row, data, dataIndex) {
            $compile(angular.element(row).contents())($scope);
        })
        .withOption('headerCallback', function(header) {
            if (!vm.headerCompiled) {
                vm.headerCompiled = true;
                $compile(angular.element(header).contents())($scope);
            }
        })
       .withPaginationType('full_numbers');

    vm.dtColumns = [
        DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
                if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                  vm.selected = {};
                }
                vm.selected[meta.row] = vm.selectAll;
                return vm.service.frontHtml + meta.row + vm.service.endHtml;
            }).notSortable(), 
        DTColumnBuilder.newColumn('picklist_id').withTitle('Picklist ID'),
        DTColumnBuilder.newColumn('picklist_note').withTitle('Picklist Note'),
        DTColumnBuilder.newColumn('date').withTitle('Date')
    ];

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        $('.custom-table').DataTable().draw();
    };

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

  vm.print_segregation = print_segregation;
  function print_segregation() {
    var data = [];
    angular.forEach(vm.selected, function(k,v){
      if(k) {
        data.push({'id': vm.dtInstance.DataTable.context[0].aoData[Number(v)]['_aData']["picklist_id"]})
      }
    });
    var send = "";
    for(var i=0; i < data.length; i++) {
      send = send+data[i].id+",";
    }
    var elem = {data_id: send.slice(0,-1)}
    vm.service.apiCall('marketplace_segregation/', 'GET', elem).then(function(data){
      if(data.message) {
        vm.service.print_data(data.data, 'Marketplace Segregation');
      }
    })
  }

  }

