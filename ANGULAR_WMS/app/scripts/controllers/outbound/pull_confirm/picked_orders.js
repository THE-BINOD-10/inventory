'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PickedOrders',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.special_key = {status: 'picked', market_place: ""}
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'PickedOrders', 'special_key': JSON.stringify(vm.special_key)},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('order', [1, 'desc'])
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

    vm.dtColumns = [
        DTColumnBuilder.newColumn('picklist_id').withTitle('Picklist ID'),
        DTColumnBuilder.newColumn('picklist_note').withTitle('Picklist Note'),
        DTColumnBuilder.newColumn('date').withTitle('Date')
    ];

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
              vm.service.apiCall('view_picked_orders/', 'GET', {data_id: aData.DT_RowAttr["data-id"], market_place: vm.market}).then(function(data){
                if(data.message) {
                  angular.copy(data.data, vm.model_data);
                  $state.go('app.outbound.PullConfirmation.Picked');
                }
              });
            });
        });
        return nRow;
    } 

    vm.dtInstance = {};

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    vm.model_data = {};

    vm.close = close;
    function close() {
      $state.go('app.outbound.PullConfirmation');
    }

    vm.market_places = [];
    vm.service.apiCall("get_marketplaces_list/?status=picked").then(function(data){
      if(data.message) {
        vm.market_places = data.data.marketplaces;
      }
    })

    vm.market = "";
    vm.change_market = function(data) {

      vm.special_key.market_place = data;
      vm.dtInstance.DataTable.context[0].ajax.data['special_key'] = JSON.stringify(vm.special_key);
      vm.dtInstance.reloadData();
    }

    vm.pdf_data = {};
    vm.generate_invoice = function() {

      var send = ""
      angular.forEach(vm.model_data.data, function(record){
        send = send + record.order_detail_id + ","
      })
      send = send.slice(0,-1);
      vm.service.apiCall("generate_order_invoice/?order_ids="+send).then(function(data){
      if(data.message) {
        angular.copy(data.data, vm.pdf_data)
        $state.go('app.outbound.PullConfirmation.GenerateInvoice');
      }
    })
    }
  }

