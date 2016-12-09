'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('RaisePOCtrl',['$scope', '$http', '$state', 'DTOptionsBuilder', 'DTColumnBuilder', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state,DTOptionsBuilder, DTColumnBuilder) {
    var vm = this;
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: 'http://176.9.181.43:7878/rest_api/results_data/',
              type: 'POST',
              data: {'datatable': 'RaisePO'}
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

    vm.dtColumns = [
        DTColumnBuilder.newColumn('Supplier ID').withTitle('Supplier ID'),
        DTColumnBuilder.newColumn('Supplier Name').withTitle('Supplier Name'),
        DTColumnBuilder.newColumn('Total Quantity').withTitle('Total Quantity')
    ];

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        // Unbind first in order to avoid any duplicate handler (see https://github.com/l-lin/angular-datatables/issues/87)
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
                $http.get('http://176.9.181.43:7878/rest_api/get_sku_data/?data_id='+aData.DT_RowAttr["data-id"]).success(function(data, status, headers, config) {

                  console.log(data);
                });
                $state.go('app.masters.SKUMaster.update');
            });
        });
        return nRow;
    } 

    vm.closeUpdate = closeUpdate;
    function closeUpdate() {

      $state.go('app.masters.SKUMaster');
    }

  }

