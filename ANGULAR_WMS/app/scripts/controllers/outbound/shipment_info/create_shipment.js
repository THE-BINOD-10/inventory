'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CreateShipmentCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, service) {
    var vm = this;
    vm.service = service;
    vm.sku_group = false;

    //table start
    vm.selected = {};
    vm.selectAll = false;
    vm.toggleAll = toggleAll;
    vm.toggleOne = toggleOne;
    var titleHtml = '<input type="checkbox" class="data-select" ng-model="vm.selectAll" ng-change="vm.toggleAll(vm.selectAll, vm.selected); $event.stopPropagation();">';

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'ShipmentPickedOrders', 'ship_id':1},
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
        DTColumnBuilder.newColumn(null).withTitle(titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
                if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                  vm.selected = {};
                 }
                vm.selected[meta.row] = vm.selectAll;
                return '<input class="data-select" type="checkbox" ng-model="vm.selected[' + meta.row + ']" ng-change="vm.toggleOne(vm.selected);$event.stopPropagation();">';
            }).notSortable(),
        DTColumnBuilder.newColumn('Order ID').withTitle('Order ID'),
        DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('Title').withTitle('Title'),
        DTColumnBuilder.newColumn('Customer ID').withTitle('Customer ID'),
	DTColumnBuilder.newColumn('Customer Name').withTitle('Customer Name'),
	DTColumnBuilder.newColumn('Marketplace').withTitle('Marketplace'),
	DTColumnBuilder.newColumn('Picked Quantity').withTitle('Picked Quantity'),
    ];

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $compile(angular.element('td', nRow))($scope);
        $('td:not(td:first)', nRow).unbind('click');
        $('td:not(td:first)', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
                var data = {customer_id: aData['Customer ID'], shipment_number:aData['Shipment Number']}
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


	//DATA table end

    

    vm.close = close;
    function close() {
      $state.go('app.outbound.ShipmentInfo');
      angular.copy(vm.empty_data, vm.model_data);
      get_data();
    }

    vm.customer_details = false;
    vm.add = add;
    function add(data) {
      if(data.$valid) {
        var send = $(form).serializeArray();

	data = [];
      	angular.forEach(vm.selected, function(key,value){
        if(key) {
	  data.push([{ name: "order_id", value: vm.dtInstance.DataTable.context[0].aoData[parseInt(value)]._aData['Order ID']},{ name : "sku_code", value : vm.dtInstance.DataTable.context[0].aoData[parseInt(value)]._aData['SKU Code'] }])
        }
      	});
	var checkbox_data = {}
	checkbox_data['confirm_shipment'] = data
	send.push(checkbox_data)
	
        service.apiCall("get_customer_sku/", "GET", send).then(function(data){
          if(data.message) {
            if(data.data["status"]) {

              service.showNoty(data.data.status);
            } else {
              vm.customer_details = (vm.model_data.customer_id) ? true: false;
              angular.copy(data.data, vm.model_data);
              angular.forEach(vm.model_data.data, function(temp) {
  
                temp["sub_data"] = [{"shipping_quantity": temp.picked, "pack_reference":""}]
              });
              vm.title = "title";
              $state.go('app.outbound.ShipmentInfo.Shipment');
            }
          }
        });
      } else {

        service.showNoty("Please Fill Required Fields");     
      }
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
        vm.empty_data.market_list = data.data.marketplaces;
      }
    })

  function get_data() {
    service.apiCall("shipment_info/","GET").then(function(data){

      if(data.message) {
        vm.model_data.shipment_number = data.data.shipment_number;
      }
    })
  }
  get_data();

    vm.change_data = function(){

      if (vm.model_data.customer_id.indexOf(":") > -1) {
        vm.model_data.customer_id = vm.model_data.customer_id.split(":")[0]
      }
    }

  vm.update_data = function(index, data, last) {
    console.log(data);
    if (last) {
      var total = 0;
      for(var i=0; i < data.sub_data.length; i++) {
        total = total + parseInt(data.sub_data[i].shipping_quantity);
      }
      if(total < data.picked) {
        var clone = {};
        angular.copy(data.sub_data[index], clone);
        clone.shipping_quantity = data.picked - total;
        data.sub_data.push(clone);
      }
    } else {
      data.sub_data.splice(index,1);
    }
  }

    vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

  vm.cal_quantity = function (record, data) {
    console.log(record);
    var total = 0;
    for(var i=0; i < data.sub_data.length; i++) {
        total = total + parseInt(data.sub_data[i].shipping_quantity);
    }
    if(data.picked >= total){
      console.log(record.shipping_quantity)
    } else {
      var quantity = data.picked-total;
      if(quantity < 0) {
        quantity = total - parseInt(record.shipping_quantity);
        quantity = data.picked - quantity;
        record.shipping_quantity = quantity;
      } else {
        record.shipping_quantity = quantity;
      }
    }
  }

  vm.add_shipment = function(valid) {

    var data = $("#add-customer:visible").serializeArray();
    service.apiCall("insert_shipment_info/", "POST", data).then(function(data){

     if(data.message) {service.showNoty(data.data);};
    });
  }

  }

