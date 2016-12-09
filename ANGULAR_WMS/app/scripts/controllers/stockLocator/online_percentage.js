'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('OnlinePercentageCtrl',['$scope', '$http', '$state', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, Session, DTOptionsBuilder, DTColumnBuilder) {
    var vm = this;
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'OnlinePercentage'}
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

    vm.dtColumns = [
        DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('Total Quantity').withTitle('Total Quantity'),
        DTColumnBuilder.newColumn('Suggested Online Quantity').withTitle('Suggested Online Quantity'),
        DTColumnBuilder.newColumn('Current Online Quantity').withTitle('Current Online Quantity'),
        DTColumnBuilder.newColumn('Offline Quantity').withTitle('Offline Quantity')
    ];

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

