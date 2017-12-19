'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ViewShipmentCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, Service) {
    var vm = this;
    vm.service = Service
    vm.selected = {};
    vm.selectAll = false;
    vm.toggleAll = toggleAll;
    vm.toggleOne = toggleOne;
    vm.permissions = Session.roles.permissions;
    vm.awb_ship_type = (vm.permissions.create_shipment_type == true) ? true: false;
    var titleHtml = '<input type="checkbox" class="data-select" ng-model="vm.selectAll" ng-change="vm.toggleAll(vm.selectAll, vm.selected); $event.stopPropagation();">';

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'ShipmentInfo', 'ship_id':1, 'gateout':0},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
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
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback)
       .withOption('RecordsTotal', function( settings ) {
         console.log("complete") 
       });

    vm.dtColumns = [
        /*DTColumnBuilder.newColumn(null).withTitle(titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
                if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                  vm.selected = {};
                 }
                vm.selected[meta.row] = vm.selectAll;
                return '<input class="data-select" type="checkbox" ng-model="vm.selected[' + meta.row + ']" ng-change="vm.toggleOne(vm.selected);$event.stopPropagation();">';
            }).notSortable(),*/
        DTColumnBuilder.newColumn('Shipment Number').withTitle('Shipment Number'),
        DTColumnBuilder.newColumn('Customer ID').withTitle('Customer ID'),
        DTColumnBuilder.newColumn('Customer Name').withTitle('Customer Name'),
        DTColumnBuilder.newColumn('Total Quantity').withTitle('Total Quantity')
    ];

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $compile(angular.element('td', nRow))($scope);
        /*$('td:not(td:first)', nRow).unbind('click');
        $('td:not(td:first)', nRow).bind('click', function() {*/
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
                var data = { gateout : 0 ,customer_id: aData['Customer ID'], shipment_number:aData['Shipment Number']}
                vm.service.apiCall("shipment_info_data/","GET", data).then(function(data){
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

    function reloadAllData () {
      $('.custom-table').DataTable().draw();
    };

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
      vm.service.apiCall("print_shipment/", "GET", data).then(function(data){
        if(data.message) {
          vm.service.print_data(data.data, 'Confirm Shipment');
        }
      })
    }

    vm.empty_data = {"shipment_number":"", "shipment_date":"","truck_number":"","shipment_reference":"","customer_id":"", "marketplace":"",
                     "market_list":[], "courier_name" : []};
    vm.model_data = {};
    angular.copy(vm.empty_data, vm.model_data);

    vm.submit = function(data) {
      var send = $("form").eq(3);
      send = $(send).serializeArray();
      vm.service.apiCall("update_shipment_status/", "GET", send).then(function(data) {
        if(data.message) {
          if(data.data["status"]) {
              vm.service.showNoty(data.data.message);  
          } else {
              vm.service.showNoty(data.data.message, 'error', 'topRight');
          }
          vm.close();
          reloadData();
        }
      });
    }

    vm.service.apiCall("get_awb_marketplaces/?status=2").then(function(data) {
      if(data.data.status) {
        vm.model_data.market_list = data.data.marketplaces;
        vm.empty_data.market_list = data.data.marketplaces;
        vm.model_data.courier_name = data.data.courier_name;
        vm.empty_data.courier_name = data.data.courier_name;
      }
    })

    vm.scanAwb = function(event, sku) {
      if (event.keyCode == 13 && sku.length > 0) {
        vm.bt_disable = true;
        vm.awb_no = sku;
        var apiUrl = "get_awb_view_shipment_info/";
        if (vm.awb_no.length) {
          var data=[];
          data.push({ name: 'awb_no', value: vm.awb_no });
          data.push({ name: 'market_place', value: vm.market_place });
          data.push({ name: 'courier_name', value: vm.courier_name });
        } else {
          vm.bt_disable = false;
          vm.service.showNoty("Fill Mandatory Fields", 'error', 'topRight');
          return;
        }
        vm.service.apiCall( apiUrl, "GET", data).then(function(data) {
          if(data.message) {
            if(data.data["status"]) {
                vm.service.showNoty(data.data.message);  
              } else {
                vm.service.showNoty(data.data.message, 'error', 'topRight');
              }
            }
          reloadAllData();
          vm.awb_no = '';
          vm.bt_disable = true;
        });
      }
    }

  }
