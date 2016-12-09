'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('StockDetailCtrl',['$scope', '$http', '$state', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, Session, DTOptionsBuilder, DTColumnBuilder, colFilters) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.filters = {'datatable': 'StockDetail', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':'', 'search6':'', 'search7': '', 'search8': ''}
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
       .withOption('rowCallback', rowCallback);

    vm.dtInstance = {};

    vm.reloadData = reloadData;
    function reloadData() {
        this.dtInstance.reloadData();
    }

    vm.dtColumns = [
        DTColumnBuilder.newColumn('Receipt ID').withTitle('Receipt ID'),
        DTColumnBuilder.newColumn('Receipt Date').withTitle('Receipt Date'),
        DTColumnBuilder.newColumn('WMS Code').withTitle('WMS Code'),
        DTColumnBuilder.newColumn('Product Description').withTitle('Product Description'),
        DTColumnBuilder.newColumn('Zone').withTitle('Zone'),
        DTColumnBuilder.newColumn('Location').withTitle('Location'),
        DTColumnBuilder.newColumn('Quantity').withTitle('Quantity'),
        DTColumnBuilder.newColumn('Receipt Type').withTitle('Receipt Type')
    ];

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    if (vm.permissions.pallet_switch == "true") {
      vm.dtColumns.push(DTColumnBuilder.newColumn('Pallet Code').withTitle('Pallet Code'))
    }

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.reloadData();
    });

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
        if(vm.filter_enable){
          vm.filter_enable = false;
          vm.apply_filters.add_search_boxes();
        }
        return nRow;
    } 

    vm.filter_enable = true;

    vm.closeUpdate = closeUpdate;
    function closeUpdate() {

      $state.go('app.masters.SKUMaster');
    }

    addSearchBox();
    vm.addSearchBox = addSearchBox;
    function addSearchBox () {
    $("thead > tr > th").each( function () {
        $(this).addClass("rm-blur")
        var title = $("thead > tr > th").eq( $(this).index() ).text();
        $(this).html( '<span>'+title+'</span><input style="width: 94%;border: 1px solid #AAA; padding: 5px;margin-right: 24px;" type="text" data-column="'+$(this).index()+'"class=" hide search-input-text" placeholder="Search '+title+'" />' );
    });
  }
  }

