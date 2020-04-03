'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ReturnsPutawayCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state , $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'ReturnsPutaway'},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('drawCallback', function(settings) {
         vm.service.make_selected(settings, vm.selected);
       })
       .withOption('lengthMenu', [100, 200, 300, 400, 500, 1000, 2000])
       .withOption('pageLength', 100)
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
                return vm.service.frontHtml + meta.row + vm.service.endHtml +'<input type="hidden" name="id" value="'+full.DT_RowAttr['data-id']+'">';
            }).notSortable(),
        DTColumnBuilder.newColumn('Return ID').withTitle('Return ID'),
        DTColumnBuilder.newColumn('Return Date').withTitle('Return Date'),
        DTColumnBuilder.newColumn('WMS Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('Product Description').withTitle('Product Description'),
        DTColumnBuilder.newColumn('Zone').withTitle('Zone')
          .renderWith(function(data, type, full, meta) {
            return "<input type='text' name='zone' value='"+full.Zone+"' class='smallbox'>"
          }),
        DTColumnBuilder.newColumn('Location').withTitle('Location')
          .renderWith(function(data, type, full, meta) {
            return "<input type='text' name='location' value='"+full.Location+"' class='smallbox'>"
          }),
        DTColumnBuilder.newColumn('Quantity').withTitle('Quantity')
          .renderWith(function(data, type, full, meta) {
            return "<input type='text' name='quantity' value='"+full.Quantity+"' class='smallbox'>"
          })
    ];

  vm.dtInstance = {};
  vm.reloadData = reloadData;

  function reloadData () {
    vm.dtInstance.reloadData();
    vm.bt_disable = true;
  };

  vm.process = false;
  vm.confirm_putaway = confirm_putaway;
  function confirm_putaway() {
    console.log(vm.selected);
    var data = [];
    var rows = $($(".custom-table:visible")).find("tbody tr");
    angular.forEach(vm.selected, function(k,v){
      if(k) {
        var row = rows[v];
        data.push({name: 'id', value: $(row).find("input[name='id']").val()})
        data.push({name: 'zone', value: $(row).find("input[name='zone']").val()})
        data.push({name: 'location', value: $(row).find("input[name='location']").val()})
        data.push({name: 'quantity', value: $(row).find("input[name='quantity']").val()})
      }
    });
    vm.process = true;
    vm.service.apiCall('returns_putaway_data/', 'POST', data).then(function(data){
      if(data.message) {
        console.log(data.data);
        colFilters.showNoty(data.data);
        reloadData();
        vm.process = false;
      }
    })
  }
}

