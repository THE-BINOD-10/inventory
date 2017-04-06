'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CreateShipmentCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'Service', 'colFilters', '$timeout', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, service, colFilters, $timeout, Data) {

    var vm = this;
    vm.service = service;
    vm.apply_filters = colFilters;
    vm.sku_group = false;
    vm.mk_user = (Session.user_profile.user_type == "marketplace_user") ? true: false;

    vm.g_data = Data.create_shipment;

    //table start
    vm.selected = {};
    vm.selectAll = false;

    vm.special_key = {customer: '', market_place:'', order_id: '', from_date: '', to_date: ''}
    vm.filters = {'datatable': vm.g_data.view, 'special_key': JSON.stringify(vm.special_key)}
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
       })
       .withOption('initComplete', function( settings ) {
         //vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    vm.dtColumns = vm.service.build_colums(vm.g_data.tb_headers[vm.g_data.view]);
    vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
                .renderWith(function(data, type, full, meta) {
                  if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                    vm.selected = {};
                  }
                  vm.selected[meta.row] = vm.selectAll;
                  return vm.service.frontHtml + meta.row + vm.service.endHtml;
                }))

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
      vm.dtInstance.reloadData();
    };
    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.reloadData();
    });

    //DATA table end



   vm.bt_disable = false;

    vm.close = close;
    function close() {
      $state.go('app.outbound.ShipmentInfo');
      angular.copy(vm.empty_data, vm.model_data);
      get_data();
    }

    vm.today_date = new Date();
    vm.customer_details = false;
    vm.add = add;
    function add(data) {
        vm.bt_disable = true;
        var table = vm.dtInstance.DataTable.data()

        var data = []
        var order_ids = [];
      	angular.forEach(vm.selected, function(key,value){
          if(key) {
            var temp = table[Number(value)]['order_id']
	        data.push({ name: "order_id", value: temp})
	        if(order_ids.indexOf(temp) == -1) {
              order_ids.push(temp);
	        }
          }
      	});

        if(vm.g_data.view == 'ShipmentPickedAlternative' && order_ids.length > 1) {
          vm.bt_disable = false;
          service.showNoty("Please Select Single Order");
          return;
        }
        data.push({name:'view', value:vm.g_data.view});
        service.apiCall("get_customer_sku/", "GET", data).then(function(data){
          if(data.message) {
            if(data.data["status"]) {

              service.showNoty(data.data.status);
            } else {
              vm.customer_details = (vm.model_data.customer_id) ? true: false;
              angular.copy(data.data, vm.model_data);
              angular.forEach(vm.model_data.data, function(temp) {

                var shipping_quantity = (vm.mk_user)? 0 : temp.picked;
                temp["sub_data"] = [{"shipping_quantity": shipping_quantity, "pack_reference":""}]
              });
              if(vm.mk_user) {
                vm.model_data.marketplace = Session.user_profile.company_name;
              }
              $state.go('app.outbound.ShipmentInfo.Shipment');
              $timeout(function() {
                $('#shipment_date').datepicker('setDate', vm.today_date);
              }, 1000)
              vm.serial_numbers = [];
            }
            vm.bt_disable = false;
          }
        });
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
        var quantity = data.picked - total;
        quantity = (vm.mk_user) ? 0 : quantity;
        clone.shipping_quantity = quantity;
        data.sub_data.push(clone);
      }
    } else {
      vm.remove_serials(data.sub_data[index]['imei_list']);
      data.sub_data.splice(index,1);
      vm.check_equal(data);
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
      if(vm.service.check_quantity(vm.model_data.data, 'sub_data', 'shipping_quantity'))  {
        vm.bt_disable = true;
        var data = $("#add-customer:visible").serializeArray();
        service.apiCall("insert_shipment_info/", "POST", data).then(function(data){

          if(data.message) {
            service.showNoty(data.data);
            if(data.data.indexOf("Success") != -1) {
              vm.close();
              vm.reloadData();
            }
            vm.bt_disable = false;
          };
        });
      } else {

        service.showNoty("Please Enter Quantity");
      }
    } else {
      service.showNoty("Please Fill Required Fields");
    }
  }

    vm.serial_numbers = [];
    vm.check_imei_exists = function(event, data1, data2) {
      event.stopPropagation();
      if (event.keyCode == 13 && data1.imei_number.length > 0) {
        if (vm.serial_numbers.indexOf(data1.imei_number) != -1){
            vm.service.pop_msg("Serial Number already Exist");
            data1.imei_number = "";
        } else {
          var send = {is_shipment: true};
          send[data2.id] = data1.imei_number
          vm.service.apiCall('check_imei/', 'GET',send).then(function(data){
            if(data.message) {
              if (data.data == "") {
                data1.shipping_quantity = parseInt(data1.shipping_quantity)+1;
                vm.serial_numbers.push(data1.imei_number);
                data1["imei_list"].push(data1.imei_number);
                vm.check_equal(data2);
              } else {
                vm.service.pop_msg(data.data);
              }
              data1.imei_number = "";
            }
          });
        }
      }
    }

    vm.check_equal = function(data) {

      data["equal"] = false;
      var total = 0;
      for(var i=0; i < data.sub_data.length; i++) {
        total = total + parseInt(data.sub_data[i].shipping_quantity);
      }
      if(data.picked == total){
        data["equal"] = true;
      }
    }

    vm.remove_serials = function(serials) {

      if(vm.serial_numbers.length > 0 && serials.length > 0) {
        angular.forEach(serials, function(serial){
          var index = vm.serial_numbers.indexOf(serial);
          vm.serial_numbers.splice(index, 1);
        });
      }
    }

    vm.change_datatable = function() {
      Data.create_shipment.view = (vm.g_data.alternate_view)? 'ShipmentPickedAlternative': 'ShipmentPickedOrders';
      $state.go($state.current, {}, {reload: true});
    }

    vm.apply = function() {

      vm.dtInstance.DataTable.context[0].ajax.data['special_key'] = JSON.stringify(vm.special_key);
      vm.reloadData();
    }
  }

