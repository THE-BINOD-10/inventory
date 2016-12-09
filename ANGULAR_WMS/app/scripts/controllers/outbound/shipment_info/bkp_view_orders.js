'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ViewShipmentCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'Service', 'colFilters', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, service, colFilters) {
    var vm = this;
    vm.service = Service;
    vm.selected = {};
    vm.selectAll = false;
    vm.toggleAll = toggleAll;
    vm.toggleOne = toggleOne;
    var titleHtml = '<input type="checkbox" style="display: block;margin: auto;" ng-model="showCase.selectAll" ng-change="showCase.toggleAll(showCase.selectAll, showCase.selected); $event.stopPropagation();">';
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
                vm.selected[meta.row] = false;
                return '<input style="display: block;margin: auto;" type="checkbox" ng-model="showCase.selected[' + meta.row + ']" ng-change="showCase.toggleOne(showCase.selected)">';;
            }).notSortable(),
        DTColumnBuilder.newColumn('Shipment Number').withTitle('Shipment Number'),
        DTColumnBuilder.newColumn('Customer ID').withTitle('Customer ID'),
        DTColumnBuilder.newColumn('Customer Name').withTitle('Customer Name'),
        DTColumnBuilder.newColumn('Total Quantity').withTitle('Total Quantity')
    ];

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td:not(td:first)', nRow).unbind('click');
        $('td:not(td:first)', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
                var data = {customer_id: aData['Customer ID'], shipment_number:aData['Shipment Number']}
                service.apiCall("shipment_info_data/","GET", data).then(function(data){

                  if(data.message) {
                    angular.copy(data.data, vm.model_data);
                    $state.go('app.outbound.ShipmentInfo.ConfirmShipment');
                  }                  
                });
            });
        });
        return nRow;
    } 

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.selectAll = false;
        vm.dtInstance.reloadData();
    };

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

    vm.close = close;
    function close() {
      vm.save_disable = false;
      $state.go('app.outbound.ShipmentInfo');
    }

    vm.confirm_shipment = confirm_shipment;
    function confirm_shipment() {
      var data = $("input[name=shipment_number]").val();
      data = [];
      angular.forEach(vm.selected, function(key,value){
        if(key) {
          data.push({name: "ship_id", value: vm.dtInstance.DataTable.context[0].aoData[parseInt(value)]._aData['Shipment Number']})
        }
      });
      service.apiCall("print_shipment/", "GET", data).then(function(data){
        if(data.message) {
          colFilters.print_data(data.data); 
        }
      })
    }

    vm.empty_data = {"shipment_number":"", "shipment_date":"","truck_number":"","shipment_reference":"","customer_id":"", "marketplace":"",
                     "market_list":[]};
    vm.model_data = {};
    angular.copy(vm.empty_data, vm.model_data);

    vm.save_disable = false;
    vm.submit = function(data) {

      var send = $("form").eq(2);
      send = $(send).serializeArray();
      service.apiCall("update_shipment_status/", "GET", send).then(function(data){
        if(data.message) {
          if(data.data == "Updated Successfully") {
            vm.save_disable = true;
          }
          service.showNoty(data.data);
          reloadData();
        }
      });
    }
  }
