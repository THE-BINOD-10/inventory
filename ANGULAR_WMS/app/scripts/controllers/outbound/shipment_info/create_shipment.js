'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CreateShipmentCtrl',['$scope', '$http', '$state', '$compile', '$rootScope', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'Service', 'colFilters', '$timeout', 'Data', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $rootScope, Session, DTOptionsBuilder, DTColumnBuilder, service, colFilters, $timeout, Data, $modal) {

    var vm = this;
    vm.service = service;
    vm.apply_filters = colFilters;
    vm.sku_group = false;
    vm.permissions = Session.roles.permissions;
    vm.mk_user = (vm.permissions.use_imei == true) ? true: false;
    vm.awb_ship_type = (vm.permissions.create_shipment_type == true) ? true: false;

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
          vm.carton_code = "";
          vm.bt_disable = vm.service.toggleOne(vm.selectAll, vm.selected, vm.bt_disable);
          vm.selectAll = vm.service.select_all(vm.selectAll, vm.selected);
        })
      })
    }

    //DATA table end
    vm.carton_code = "";
    vm.carton = "";
    vm.box_num = "";
    vm.add_carton = function() {
      var carton_code = '';
      vm.service.apiCall('shipment_pack_ref').then(function(data){
        if(data.message) {
          console.log(data);
          swal2({
            title: 'Please enter your carton code',
            text: '',
            // input: 'text',
            html:
              '<input class="swal2-input" name="carton_num" id="carton_num" placeholder="Enter Carton" type="text" style="display: block;" value="'+data.data.pack_ref_no+'"  readonly>' +
              '<input class="swal2-input" name="box_num" id="box_num" placeholder="Enter Box Number" value="" type="text" style="display: block;">',
            confirmButtonColor: '#33cc66',
            // cancelButtonColor: '#d33',
            confirmButtonText: 'Save',
            cancelButtonText: 'Cancel',
            showLoaderOnConfirm: true,
            inputOptions: 'Testing',
            inputPlaceholder: 'Enter Carton',
            confirmButtonClass: 'btn btn-success',
            cancelButtonClass: 'btn btn-default',
            showCancelButton: true,
            preConfirm: function () {
              return new Promise(function (resolve) {
                resolve([
                  $('#carton_num').val(),
                  $('#box_num').val()
                ])
              })
            },
            allowOutsideClick: false,
            // buttonsStyling: false
          }).then(function (text) {
            $scope.$apply(function() {
              $('#scan_sku').focus();
              vm.carton = $('#carton_num').val();
              vm.box_num = $('#box_num').val();
              // angular.forEach(vm.model_data.data, function(data){
                // angular.forEach(data.sub_data, function(record){
                  // if (vm.carton == record.pack_reference) {
                    // record.pack_reference = vm.carton;
                    // record.box_num = vm.box_num;
                    vm.update_carton_code(vm.carton);
                    // resolve();
                  // }
                });
              }).catch(function(error) {
                $('#scan_sku').focus();
                // vm.service.apiCall("shipment_pack_ref_decrease/", "GET", {'pack_ref_no': $('#carton_num').val()})
                vm.service.apiCall('shipment_pack_ref_decrease', "GET", {'pack_ref_no': $('#carton_num').val()}).then(function(data){
                });
              });
            }
          });
    }

    vm.update_carton_code = function(carton_code){
      // $scope.$apply(function() {
        vm.carton_code = carton_code;

        if (!vm.model_data.sel_cartons[carton_code]) {
          vm.model_data.sel_cartons[carton_code] = 0;
        }
      // });
    }

    vm.update_sku_carton_exist = function(event, scanned_carton) {
      var flag = false;
      if (event.keyCode == 13) {
        for (var i = 0; i < Object.keys(vm.model_data.sel_cartons).length; i++) {
          if (Object.keys(vm.model_data.sel_cartons)[i] == scanned_carton) {
            vm.carton_code = scanned_carton;
            vm.scan_carton_exist = '';
            $('#scan_sku').focus();
            flag = false;
            break;
          } else {
              flag = true;
          }
        }
      }
      if(flag) {
        vm.service.showNoty("Scanned Pack Reference carton Not Found !");
        vm.scan_carton_exist = '';
      }
    }

    vm.close = close;
    function close() {
      $state.go('app.outbound.ShipmentInfo');
      angular.copy(vm.empty_data, vm.model_data);
      get_data();
    }

    vm.today_date = new Date();
    vm.customer_details = false;
    vm.add = function (data) {
        vm.bt_disable = true;
        var table = vm.dtInstance.DataTable.data()
        var apiUrl = "get_customer_sku/";
        var data = []
        var order_ids = [];
        var mk_places = [];
        var cust_details = {}
        angular.forEach(vm.selected, function(key,value){
          if(key) {
            var temp = table[Number(value)]['order_id']
            var temp2 = table[Number(value)]['Marketplace']
            cust_details['cust_name'] = table[Number(value)]['Customer Name']
            cust_details['cust_id'] = table[Number(value)]['Customer ID']
            cust_details['order_id'] = temp
            cust_details['marketplace'] = temp2
          data.push({ name: "order_id", value: temp})
          if(order_ids.indexOf(temp) == -1) {
              order_ids.push(temp);
          }
          if(mk_places.indexOf(temp2) == -1) {
            mk_places.push(temp2);
          }
          }
        });
        vm.model_data['cust_details'] = cust_details;
        if(order_ids.length == 0) {
          vm.service.showNoty("Please Select Orders First");
          vm.bt_disable = false;
          return false;
        }

        if(vm.g_data.view == 'ShipmentPickedAlternative'){
          if (vm.group_by == 'order' && order_ids.length > 1) {
            vm.bt_disable = false;
            vm.service.showNoty("Please Select Single Order");
            return;
          } else if(vm.group_by == 'marketplace' && mk_places.length > 1) {
            vm.bt_disable = false;
            vm.service.showNoty("Please Select Single Marketplace");
            return;
          }
        }

        data.push({name:'view', value:vm.g_data.view});
        vm.service.apiCall(apiUrl, "GET", data).then(function(data){
          if(data.message) {
            if(data.data["status"]) {

              vm.service.showNoty(data.data.status);
            } else {
              vm.customer_details = (vm.model_data.customer_id) ? true: false;
              angular.extend(vm.model_data, data.data);
              angular.forEach(vm.model_data.data, function(temp) {

                var shipping_quantity = (vm.mk_user || vm.permissions.shipment_sku_scan)? 0 : temp.picked;
                temp["sub_data"] = [{"shipping_quantity": shipping_quantity, "pack_reference":""}]
              });
              if(vm.mk_user) {
                vm.model_data.marketplace = Session.user_profile.company_name;
              }
              vm.carton_code = "";
              vm.model_data.sel_cartons = {};
              vm.print_enable = false;
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
                     "market_list":[], "courier_name" : []};
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

    vm.create_shipment_awb_filter = function() {
      vm.service.apiCall("get_awb_marketplaces/?status=1").then(function(data) {
        vm.special_key.market_place = '';
        vm.special_key.courier_name = '';
        vm.model_data.market_list = [];
        vm.model_data.courier_name = [];
        if(data.data.status) {
          vm.model_data.market_list = data.data.marketplaces;
          vm.empty_data.market_list = data.data.marketplaces;
          vm.model_data.courier_name = data.data.courier_name;
          vm.empty_data.courier_name = data.data.courier_name;
          vm.special_key.market_place = '';
          vm.special_key.courier_name = '';
        }
      })
    }
    vm.create_shipment_awb_filter();

    function get_data() {
      vm.service.apiCall("shipment_info/","GET").then(function(data){
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
        quantity = (vm.mk_user || vm.permissions.shipment_sku_scan) ? 0 : quantity;
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

  vm.print_barcodes  = function() {
      vm.barcode_title = 'Barcode Generation';
      vm.model_data['barcodes'] = [];

      vm.model_data['format_types'] = [];
      var key_obj = {};//{'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details', 'Bulk Barcode': 'Details'};
      vm.service.apiCall('get_format_types/').then(function(data){
        $.each(data['data']['data'], function(ke, val){
          vm.model_data['format_types'].push(ke);
          });
          key_obj = data['data']['data'];
      });
      var elem = angular.element($('#add-customer'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      var list = [];
      var dict = {};
      var onetime_data = {};
      var masters = ['courier_name', 'invoice_number', 'scan_sku', 'shipment_date', 'shipment_number',
                    'shipment_reference', 'truck_number', 'view_name', 'cust_name', 'customer_name',
                    'customer_id', 'package_reference'];
      $.each(elem, function(num, key){
        if(masters.indexOf(key['name']) != -1){
            onetime_data[key['name']] = key['value'];
        }
        if(!dict.hasOwnProperty(key['name'])){
          dict[key['name']] = key['value'];
        }else{
          angular.extend(dict, onetime_data)
          list.push(dict);
          dict = {}
          dict[key['name']] = key['value'];
        }
      });
      if(dict.hasOwnProperty('sku_code')){
          angular.extend(dict, onetime_data)
          list.push(dict);
      }
      vm.model_data['barcodes'] = list;
      vm.model_data.have_data = true;
      //$state.go('app.inbound.RevceivePo.barcode');
      var modalInstance = $modal.open({
        templateUrl: 'views/outbound/toggle/shipment_barcodes.html',
        controller: 'Barcodes',
        controllerAs: 'pop',
        size: 'lg',
        backdrop: 'static',
        keyboard: false,
        windowClass: 'z-2021',
        resolve: {
          items: function () {
            return vm.model_data;
          }
        }
      });

      modalInstance.result.then(function (selectedItem) {
        console.log(selectedItem);
      });
    }

  vm.add_shipment = function(valid) {
    if(valid.$valid) {
      if(vm.service.check_quantity(vm.model_data.data, 'sub_data', 'shipping_quantity'))  {
        vm.bt_disable = true;
        var data = $("#add-customer:visible").serializeArray();
        vm.service.apiCall("insert_shipment_info/", "POST", data, true).then(function(data){
          if(data.data.status) {
            vm.service.showNoty(data.data.message);
            vm.close();
            vm.reloadData();
            vm.awb_no = '';
            vm.bt_disable = false;
          };
        });
      } else {
        vm.service.showNoty("Please Enter Quantity");
      }
    } else {
      vm.service.showNoty("Please Fill Required Fields");
    }
  }

    vm.serial_numbers = [];
    vm.check_imei_exists = function(event, imei) {
      event.stopPropagation();
      if (event.keyCode == 13 && imei.length > 0) {
        if (vm.serial_numbers.indexOf(imei) != -1){
            vm.service.showNoty("IMEI Number Already Exist");
            vm.imei_number = "";
        } else {
          var imei_order_id = ''
          if(vm.model_data.data.length > 0 && vm.model_data.data[0].order_id)
          {
              if(vm.model_data.data[0].original_order_id != '')
              {
                imei_order_id = vm.model_data.data[0].original_order_id;
              }
              else {
                imei_order_id = vm.model_data.data[0].order_id;
              }
          }
          var check_imei_dict = {is_shipment: true, imei: imei, order_id: imei_order_id, groupby: vm.group_by}
          vm.service.apiCall('check_imei/', 'GET', check_imei_dict).then(function(data){
            if(data.message) {
              if (data.data.status == "Success") {
                vm.update_imei_data(data.data, imei);
                //vm.check_equal(data2);
              } else {
                vm.service.showNoty(data.data.status);
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

    vm.scanAwb = function(event, sku) {
      if (event.keyCode == 13 && sku.length > 0) {
        vm.bt_disable = true;
        vm.awb_no = sku;
        var apiUrl = "get_awb_shipment_details/";
        if (vm.awb_no.length) {
          var data=[];
          data.push({ name: 'awb_no', value: vm.awb_no });
        } else {
          vm.bt_disable = false;
          service.showNoty("Fill Mandatory Fields", 'error', 'topRight');
          return;
        }
        data.push({ name:'view', value:vm.g_data.view })
        data.push({ name:'marketplace', value: vm.special_key.market_place })
        data.push({ name:'courier_name', value: vm.special_key.courier_name })
        vm.service.apiCall( apiUrl, "GET", data).then(function(data) {
        if(data.message) {
          if(data.data["status"]) {
            vm.service.showNoty(data.data.message);
            $scope.refreshViewShipment();
            vm.reloadData();
          } else {
            vm.service.showNoty(data.data.message, 'error', 'topRight');
          }
        }
        vm.awb_no = '';
        vm.bt_disable = true;
        });
      }
    }
    vm.bt_disable = false;

    $scope.refreshViewShipment = function() {
      vm.create_shipment_awb_filter();
      $rootScope.$emit("CallParentMethod", {});
    }

    vm.get_courier_for_marketplace = function() {
      service.apiCall("get_courier_name_for_marketplaces/?status=1&marketplace="+vm.special_key.market_place).then(function(data) {
        vm.model_data.courier_name = [];
        if(data.data.status) {
          vm.model_data.courier_name = data.data.courier_name;
          vm.empty_data.courier_name = data.data.courier_name;
          vm.special_key.courier_name = '';
        }
      })
    }

    vm.update_sku_quan = function(event, scanned_sku) {
      event.stopPropagation();
      if (event.keyCode == 13 && scanned_sku.length > 0) {
          console.log(vm);
        vm.service.apiCall("create_orders_check_ean", "GET", {ean: scanned_sku}).then(function(api_data){
        if(api_data.message) {
          var found_sku = false;
          var is_updated = false;
          scanned_sku = api_data.data.sku;
          for(var i=0;i<vm.model_data.data.length;i++) {
            var data_sku = String(vm.model_data.data[i].sku__sku_code).toLocaleLowerCase();
            if(data_sku==String(scanned_sku).toLocaleLowerCase()) {
              found_sku = true;
              var tot_ship = 0
              angular.forEach(vm.model_data.data[i].sub_data, function(sb_data){
                var sb_shipped = isNaN(sb_data.shipping_quantity)? 0: sb_data.shipping_quantity;
                tot_ship = Number(tot_ship) + Number(sb_shipped);
              });

              if(vm.model_data.data[i].picked > tot_ship)
              {
                var last_index = vm.model_data.data[i].sub_data.length - 1;
                var exist_quan = vm.model_data.data[i].sub_data[last_index].shipping_quantity;
                exist_quan = (!isNaN(exist_quan)) ? exist_quan: 0;

               for(var p_ref=0; p_ref<vm.model_data.data[i].sub_data.length; p_ref++){
                  if (vm.carton_code == vm.model_data.data[i].sub_data[p_ref].pack_reference) {
                    last_index = p_ref;
                 }
                }

                if (vm.carton_code == vm.model_data.data[i].sub_data[last_index].pack_reference ||
                  !vm.model_data.data[i].sub_data[last_index].pack_reference ||
                  (!vm.model_data.data[i].sub_data[last_index].shipping_quantity && vm.model_data.data[i].sub_data[last_index].pack_reference)) {

                  vm.model_data.data[i].sub_data[last_index].shipping_quantity = Number(exist_quan) + 1;

                  if (vm.model_data.data[i].sub_data[last_index].shipping_quantity) {

                    if(vm.model_data.sel_cartons[vm.carton_code]){
                        vm.model_data.sel_cartons[vm.carton_code] += 1;
                    } else {
                      vm.model_data.sel_cartons[vm.carton_code] = 1;
                    }
                    vm.model_data.data[i].sub_data[last_index].pack_reference = vm.carton_code;
                    vm.model_data.data[i].sub_data[last_index].box_num = vm.box_num;
                  }

                  // if (!vm.model_data.data[i].sub_data[last_index].pack_reference) {
                  //   vm.model_data.data[i].sub_data[last_index].pack_reference = vm.carton_code;
                  // }
                } else {
                  vm.update_data(i, vm.model_data.data[i], true);

                  if (vm.model_data.data[i].sub_data[last_index+1].pack_reference) {
                    vm.model_data.data[i].sub_data[last_index+1].pack_reference = '';
                  }
                  vm.update_sku_quan(event, scanned_sku);
                }

                is_updated = true;
                break;
              }
            }
          }
          if(!found_sku){ vm.service.showNoty("Scanned SKU Code not found");}
            else if(!is_updated){ vm.service.showNoty("Scanned SKU Code exceeded the quantity");}
            vm.scan_sku = '';
          }
        });
      }
    }

    vm.add_carton_code = function(data){
      if(!vm.carton_code || data.pack_reference != vm.carton_code){
        vm.carton_code = data.pack_reference;
      }
      if (!vm.model_data.sel_cartons[data.pack_reference] && data.cal_quantity) {
        vm.model_data.sel_cartons[data.pack_reference] = data.cal_quantity;
      }
    }

    vm.cartonPrintData = {};
    vm.print_pdf = function(form, excel=false) {
      if (vm.model_data.sel_cartons) {
        var sel_cartons_len = Object.keys(vm.model_data.sel_cartons);
        var sel_cartons = JSON.stringify(vm.model_data.sel_cartons);
        var total_items = 0;
        angular.forEach(vm.model_data.sel_cartons, function(row){
          total_items += row;
        });
        var elem = angular.element($('#add-customer'));
        elem = elem[0];
        elem = $(elem).serializeArray();
        elem.push({'name':'sel_cartons', 'value':sel_cartons});
        elem.push({'name':'total_cartons', 'value':sel_cartons_len.length});
        elem.push({'name':'total_items', 'value':total_items});
        if (excel) {
          elem.push({'name':'is_excel', 'value': true});
        }
        vm.service.apiCall("print_cartons_data/", "POST", elem).then(function(data) {
          if(data.message) {
            if (excel) {
              $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
              window.location = Session.host+data.data.path;
            } else {
              if(data.data.search("<div") != -1) {
                vm.service.print_data(data.data, 'Packaging Slip');
              } else {
                vm.service.pop_msg(data.data);
              }
            }
          }
        });
      } else {
        vm.service.showNoty("No cartons codes are entered");
      }
    }
  }
