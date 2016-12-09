'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ShipmentInfoCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, service) {
    var vm = this;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'ShipmentInfo', 'ship_id':1},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

    vm.dtColumns = [
        DTColumnBuilder.newColumn('customer_id').withTitle('Customer ID'),
        DTColumnBuilder.newColumn('customer_name').withTitle('Customer Name'),
        DTColumnBuilder.newColumn('tatal_quantity').withTitle('Total Quantity')
    ];

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        // Unbind first in order to avoid any duplicate handler (see https://github.com/l-lin/angular-datatables/issues/87)
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
                /*$http.get('http://176.9.181.43:7878/rest_api/get_sku_data/?data_id='+aData.DT_RowAttr["data-id"]).success(function(data, status, headers, config) {

                  console.log(data);
                });*/
                $state.go('app.production.RaiseJO.JO');
            });
        });
        return nRow;
    } 

    vm.close = close;
    function close() {
      $state.go('app.outbound.ShipmentInfo');
    }

    vm.add = add;
    function add(data) {
      if(data.$valid) {
        vm.model_data.customer_id = vm.model_data.customer_id.split(":")[0];
        vm.model_data.shipment_date = ""+vm.model_data.shipment_date;
        $("input[name=customer_id]").val(vm.model_data.customer_id);
        var send = $(form).serializeArray();
        service.apiCall("get_customer_sku/", "GET", send).then(function(data){
          if(data.message) {
            angular.copy(data.data, vm.model_data);
            vm.title = "title";
            $state.go('app.outbound.ShipmentInfo.Shipment');
          }
        });
      } else {

        service.showNoty("Please Fill Required Fields");     
      }
    }

    vm.confirm_shipment = confirm_shipment;
    function confirm_shipment() {
      $state.go('app.outbound.ShipmentInfo.ConfirmShipment');
    }

    vm.title = "Update Job Order"

    vm.print = function() {
      $state.go('app.production.RaiseJO.JobOrderPrint');
    }

    vm.empty_data = {"shipment_number":"", "shipment_date":"","truck_number":"","shipment_reference":"","customer_id":"", "marketplace":"",
                     "market_list":[]};
    vm.model_data = {};
    angular.copy(vm.empty_data, vm.model_data);

    $scope.getLocation = function(val) {
    return $http.get(Session.url+'search_customer_sku_mapping', {
      params: {
        q: val
      }
      }).then(function(response){
        return response.data.map(function(item){
          return item;
        });
      });
    };

    service.apiCall("get_marketplaces_list/").then(function(data){
      if(data.message) {
        vm.model_data.market_list = data.data.marketplaces;
      }
    })
  }

