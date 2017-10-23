'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CreateShipmentCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'Service', 'colFilters', '$timeout', 'Data', '$q', 'SweetAlert', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, service, colFilters, $timeout, Data, $q, SweetAlert) {

    var vm = this;
    vm.service = service;
    vm.apply_filters = colFilters;
    vm.sku_group = false;
    vm.permissions = Session.roles.permissions;
    vm.mk_user = (vm.permissions.use_imei == true) ? true: false;

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
       .withOption('lengthMenu', [100, 200, 300, 400, 500, 1000, 2000])
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
        $('.custom-table').DataTable().draw();
    };
    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.reloadData();
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {

      $('td:not(td:first)', nRow).unbind('click');
      $('td:not(td:first)', nRow).bind('click', function() {

        $scope.$apply(function() {
          console.log(vm.selected, nRow, aData, iDisplayIndex, iDisplayIndexFull);
          if (vm.selected[iDisplayIndex]) {
            vm.selected[iDisplayIndex] = false;
          } else {
            vm.selected[iDisplayIndex] = true;
          }

          vm.bt_disable = vm.service.toggleOne(vm.selectAll, vm.selected, vm.bt_disable);
          vm.selectAll = vm.service.select_all(vm.selectAll, vm.selected);
        })
      })
    }

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
    vm.add = function (data) {
        var table = vm.dtInstance.DataTable.data()

        var data = []
        var order_ids = [];
        var mk_places = [];
      	angular.forEach(vm.selected, function(key,value){
          if(key) {
            var temp = table[Number(value)]['order_id']
            var temp2 = table[Number(value)]['Marketplace']
	        data.push({ name: "order_id", value: temp})
	        if(order_ids.indexOf(temp) == -1) {
              order_ids.push(temp);
	        }
	        if(mk_places.indexOf(temp2) == -1) {
	          mk_places.push(temp2);
	        }
          }
      	});

        if(order_ids.length == 0) {
          service.showNoty("Please Select Orders First");
          return false;
        }

        if(vm.g_data.view == 'ShipmentPickedAlternative'){
          if (vm.group_by == 'order' && order_ids.length > 1) {
            vm.bt_disable = false;
            service.showNoty("Please Select Single Order");
            return;
          } else if(vm.group_by == 'marketplace' && mk_places.length > 1) {
            vm.bt_disable = false;
            service.showNoty("Please Select Single Marketplace");
            return;
          }
        }
        vm.bt_disable = true;
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
              if(vm.permissions.use_imei) {
                fb.start(vm.model_data);
              }
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

    service.apiCall("get_marketplaces_list/?status=picked").then(function(data){
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
      //vm.check_equal(data);
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
        service.apiCall("insert_shipment_info/", "POST", data, true).then(function(data){

          if(data.message) {
            service.showNoty(data.data);
            if(data.data.indexOf("Success") != -1) {
              vm.close();
              vm.reloadData();
              if(vm.permissions.use_imei) {
                fb.delete_order(fb.orderData.order_id);
              }
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
    vm.check_imei_exists = function(event, imei) {
      event.stopPropagation();
      if (event.keyCode == 13 && imei.length > 0) {
        if (vm.serial_numbers.indexOf(imei) != -1){
            service.showNoty("IMEI Number Already Exist");
            vm.imei_number = "";
        } else {
          var imei_order_id = ''
          if(vm.model_data.data.length > 0 && vm.model_data.data[0].order_id)
          {
              imei_order_id = vm.model_data.data[0].order_id
          }
          vm.service.apiCall('check_imei/', 'GET',{is_shipment: true, imei: imei, order_id: imei_order_id}).then(function(data){
            if(data.message) {
              if (data.data.status == "Success") {
                vm.update_imei_data(data.data, imei);
                //vm.check_equal(data2);
              } else {
                service.showNoty(data.data.status);
              }
              vm.imei_number = "";
            }
          });
        }
      }
    }

    vm.update_imei_data = function(data, imei) {

      var status = false;
      var sku_status = false;
      for(var i = 0; i < vm.model_data.data.length; i++) {

        if(vm.model_data.data[i].sku__sku_code == data.data.sku_code) {

          sku_status = true;
          if(vm.model_data.data[i].picked > vm.model_data.data[i]['sub_data'][0].shipping_quantity) {
            vm.model_data.data[i]['sub_data'][0].shipping_quantity += 1;
            vm.model_data.data[i]['sub_data'][0].imei_list.push(imei);
            vm.serial_numbers.push(imei);
            fb.push_serial(vm.model_data.data[i],imei);
            status = true;
            break;
          }
        }
      }
      if(sku_status && (!status)) {

        service.showNoty(data.data.sku_code+" SKU picked quantity equal shipped quantity");
      } else if(!status) {

        service.showNoty("Entered Imei Number Not Matched With Any SKU's");
      }
    }

    /*vm.check_equal = function(data) {

      data["equal"] = false;
      var total = 0;
      for(var i=0; i < data.sub_data.length; i++) {
        total = total + parseInt(data.sub_data[i].shipping_quantity);
      }
      if(data.picked == total){
        data["equal"] = true;
      }
    }*/

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

    vm.updateDate = function() {

      $('.shipment-date').datepicker('update');
    }

  //firebase
  var fb = {}
  fb.orderData = {};

  fb.change_order_data = function(data) {

    vm.serial_numbers = [];
    angular.forEach(vm.model_data.data, function(data){
      var name= data.sku__sku_code;
      if(fb.orderData[name]) {
        if(!fb.orderData[name]['serials']){fb.orderData[name]['serials'] = {}}
        data.sub_data[0].shipping_quantity = Object.keys(fb.orderData[name]['serials']).length;
        data.sub_data[0].imei_list = Object.values(fb.orderData[name]['serials']);
        vm.serial_numbers = vm.serial_numbers.concat(data.sub_data[0].imei_list);
        $timeout(function() {$scope.$apply();}, 500);
      }
    })
    fb.add_new = true;
    fb.data_update(data);
    fb.order_delete_event();
  } 

  fb.push = function(data){
    var order_data = {};
    order_data['order_id'] = data.data[0].order_id
    
    angular.forEach(data.data, function(sku){
      var name = sku.sku__sku_code;
      order_data[name] = {};
      order_data[name]["sku_code"] = name;
      order_data[name]["serials"] = "";
    }) 
    console.log(order_data);
    firebase.database().ref("/ShipmentInfo/"+Session.parent.userId+"/"+order_data.order_id+"/").push(order_data).then(function(data){
      fb.orderData = order_data;
      fb.orderData['key'] = data.key;
      fb.data_update(fb.orderData);
      fb.order_delete_event();
    })
  }

  fb.exists = function(data) {
      var d = $q.defer();
      firebase.database().ref("/ShipmentInfo/"+Session.parent.userId+"/"+data.data[0].order_id+"/").once("value", function(snapshot) {
        if(snapshot.val()) {
          var order_data = {};
          angular.forEach(snapshot.val(), function(data,v){
            order_data = data;
            order_data['key'] = v;
          })
          order_data.order_id = data.data[0].order_id;
          d.resolve({status: true, data: order_data});
        } else {
          d.resolve({status: false});
        }
      });
      return d.promise;
    }

  fb.start = function(data) {

    fb.exists(data).then(function(po){
      console.log(po);
      if(!po.status) {
        fb.push(data);
      } else {
        fb.orderData = po.data;
        fb.change_order_data(fb.orderData);
      }
    })
  }

  fb.push_serial = function(data, serial) {
    firebase.database().ref("/ShipmentInfo/"+Session.parent.userId+"/"+fb.orderData.order_id+"/"+fb.orderData.key+"/"+ data.sku__sku_code +"/serials/").push(serial).then(function(snapshot){

      console.log(snapshot);
    });
  }

  fb.data_update = function(order_data) {
    angular.forEach(vm.model_data.data, function(data) {
      firebase.database().ref("/ShipmentInfo/"+Session.parent.userId+"/"+order_data.order_id+"/"+order_data.key+"/"+data.sku__sku_code+"/serials/").on("child_added", function(snapshot) {
        console.log("changes", data.sku__sku_code);
        if (data.sub_data[0].imei_list.indexOf(snapshot.val()) == -1) {
          data.sub_data[0].imei_list.push(snapshot.val());
          data.sub_data[0].shipping_quantity = Number(data.sub_data[0].shipping_quantity) + 1;
        }
        if(vm.serial_numbers.indexOf(snapshot.val()) == -1) {
          vm.serial_numbers.push(snapshot.val());
        }
        $timeout(function() {$scope.$apply();}, 500);
      });
    });
  }

  fb.order_delete_event = function() {

    firebase.database().ref("/ShipmentInfo/"+Session.parent.userId+"/"+fb.orderData.order_id+"/").on("child_removed", function(order) {
      console.log("deleted", order, fb.orderData);
      if(order.key == fb.orderData.key) {
        fb.orderData = {};
        SweetAlert.swal({
          title: '',
          text: 'Shipment Created Successfully',
          type: 'success',
          showCancelButton: false,
          confirmButtonColor: '#33cc66',
          confirmButtonText: 'Ok',
          closeOnConfirm: true,
          },
          function (status) {
           vm.close();
          }
        );
      }
    })
  }

  fb.delete_order = function(order_id) {

      if(order_id) {
        firebase.database().ref("/ShipmentInfo/"+Session.parent.userId+"/"+fb.orderData.order_id+"/").off();
        firebase.database().ref("/ShipmentInfo/"+Session.parent.userId+"/"+order_id).once("value", function(data){
          data.ref.remove()
            .then(function() {
              console.log("Remove succeeded.");
              fb.orderData = {};
            })
            .catch(function(error) {
              console.log("Remove failed: " + error.message)
            });
          console.log(data.ref.remove())
        })
      }
    } 

  }

