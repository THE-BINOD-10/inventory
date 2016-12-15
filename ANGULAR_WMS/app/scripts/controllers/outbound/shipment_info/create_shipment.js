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

    vm.filters_data = {customer: '', market_place:''}
    vm.filters = {'datatable': 'ShipmentPickedOrders', 'ship_id':1/*, 'special_key': JSON.stringify(vm.filters_data)*/}
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
       .withOption('RecordsTotal', function( settings ) {
         console.log("complete")
       });

    var columns = ["Order ID", "SKU Code","Title", "Customer ID", "Customer Name", "Marketplace", "Picked Quantity"]
    vm.dtColumns = vm.service.build_colums(columns);
    vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
                .renderWith(function(data, type, full, meta) {
                  if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                    vm.selected = {};
                  }
                  vm.selected[meta.row] = vm.selectAll;
                  return vm.service.frontHtml + meta.row + vm.service.endHtml;
                }))

    vm.dtInstance = {};

    //DATA table end

   vm.bt_disable = true; 

    vm.close = close;
    function close() {
      $state.go('app.outbound.ShipmentInfo');
      angular.copy(vm.empty_data, vm.model_data);
      get_data();
    }

    vm.customer_details = false;
    vm.add = add;
    function add(data) {
        var table = vm.dtInstance.DataTable.data()

        var data = []
      	angular.forEach(vm.selected, function(key,value){
          if(key) {
	    data.push({ name: "order_id", value: $($.parseHTML(table[Number(value)][""])).attr('name')})
          }
      	});
	
        service.apiCall("get_customer_sku/", "GET", data).then(function(data){
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
        $state.go('app.outbound.ShipmentInfo.Shipment');
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

    if(valid.$valid) {
      var data = $("#add-customer:visible").serializeArray();
      service.apiCall("insert_shipment_info/", "POST", data).then(function(data){
  
        if(data.message) {service.showNoty(data.data);};
      });
    }
  }

  vm.apply_filters = function() {

    vm.dtInstance.DataTable.context[0].ajax.data['special_key'] = JSON.stringify(vm.filters_data);
    vm.dtInstance.reloadData();  
  }

  }

