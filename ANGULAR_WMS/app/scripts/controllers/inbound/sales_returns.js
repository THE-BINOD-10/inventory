'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SalesReturnsCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'SweetAlert', 'COLORS', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, SweetAlert, COLORS, Service) {
    var vm = this;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.industry_type = Session.user_profile.industry_type;
    vm.awb_ship_type = (vm.permissions.create_shipment_type == true) ? true: false;
    vm.scan_imei_readonly = false;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'SalesReturns'},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers');

    vm.dtColumns = [
        DTColumnBuilder.newColumn('Return ID').withTitle('Return ID'),
        DTColumnBuilder.newColumn('Order ID').withTitle('Order ID'),
        DTColumnBuilder.newColumn('Return Date').withTitle('Return Date'),
        DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('Product Description').withTitle('Product Description'),
        DTColumnBuilder.newColumn('Market Place').withTitle('Market Place'),
        DTColumnBuilder.newColumn('Quantity').withTitle('Quantity')
    ];

    vm.dtInstance = {};
    vm.reloadData = reloadData;
    vm.allocate_order = false;
    vm.excl_order_map = {};

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    vm.close = close;
    function close() {

      vm.scan_returns = [];
      vm.scan_orders = [];
      vm.scan_skus = [];
      vm.scan_imeis = [];
      vm.scan_awb_order_no = [];
      vm.confirm_disable = false;
      vm.imei_data.reason = "";
      vm.imei_data.scanning = false;
      vm.excl_order_map = {};
      $state.go('app.inbound.SalesReturns');
    }

    vm.scan_pop = scan_pop;
    function scan_pop() {
      vm.model_data = {data:[]};
      vm.service.apiCall('get_sellers_list/', 'GET').then(function(data){
        vm.model_data.seller_types = []
        if (data.message) {
          var seller_data = data.data.sellers;
          angular.forEach(seller_data, function(seller_single){
              vm.model_data.seller_types.push(seller_single.id + ':' + seller_single.name);
          });
        }
      });
      $state.go('app.inbound.SalesReturns.ScanReturns');
    }

    vm.model_data = {'data':[]}
    vm.scan_orders = [];
    vm.orders_data = {};
    vm.scan_track = function(event, field) {
       if (event.keyCode == 13 && field) {
             if(vm.scan_orders.indexOf(field) == -1) {
               vm.service.apiCall('check_returns/', 'GET', {order_id: field}).then(function(data){
                 if(data.message) {
                   if ('Order Id is invalid' == data.data) {
                     check_data(field);
                   } else if (field+' is already confirmed' == data.data){
                     pop_msg(data.data);
                   } else if (data.data.indexOf("Already Returned") >= 0) {
                     pop_msg(data.data);
                     vm.model_data.scan_order_id = ''
                   } else {
                     angular.forEach(data.data, function(sku_data){
                       vm.model_data.data.push(sku_data);
                       var name = sku_data.order_id+"<<>>"+sku_data.sku_code;
                       vm.orders_data[name] = {};
                       angular.copy(sku_data, vm.orders_data[name]);
                     })
                   vm.scan_orders.push(field);
                   }
                 }
                 vm.model_data.scan_order_id = "";
               });
             } else {
               pop_msg("Already Added In List");
               vm.model_data.scan_order_id = "";
             }
         }
     }

    vm.scan_returns = []
    vm.scan_return = function(event, field) {
      if ( event.keyCode == 13 && field) {
        if(vm.scan_returns.indexOf(field) == -1) {
          vm.service.apiCall('check_returns/', 'GET', {return_id: field}).then(function(data){
            if(data.message) {
              if (field+' is invalid' == data.data) {
                check_data(field);
              } else if (field+' is already confirmed' == data.data){
                pop_msg(data.data);
              } else if (data.data.indexOf("Already Returned") >= 0) {
                pop_msg(data.data);
                vm.model_data.scan_return_id = ''
              } else {
                vm.model_data.data.push(data.data[0]);
                vm.scan_returns.push(field);
              }
            }
            vm.model_data.scan_return_id = "";
          });
        } else {
          pop_msg("Already Added In List");
          vm.model_data.scan_return_id = "";
        }
      }
    }

    vm.check_data = check_data;
    function check_data(field) {
        var temp = true;
        for(var i=0; i<vm.model_data.data.length; i++) {
          if(vm.model_data.data[i].order_id == field) {
            temp = false;
            break;
          }
        }
        if(temp) {
          $scope.demo5(field);
        }
    }

    vm.scan_skus = [];
    vm.sku_mapping = {};
    vm.scan_sku = function(event, field) {
      if(vm.permissions.user_type == 'marketplace_user')
      {
        if(vm.model_data.seller_type) {
          vm.scan_sku_marketplace_user = true;
        }
        else {
          vm.scan_sku_marketplace_user = false;
          pop_msg("Please Select Seller ID")
        }
      }
      else {
        vm.scan_sku_marketplace_user = true;
      }
      if(vm.scan_sku_marketplace_user)
       {
       if ( event.keyCode == 13 && field) {
        var check_sku_dict = {'sku_code': field, 'allocate_order': vm.allocate_order,
                           'marketplace': vm.model_data.marketplace, 'mrp': vm.model_data.mrp,
                           'seller_id': vm.model_data.seller_type}
        if(vm.excl_order_map[field]) {
          check_sku_dict['exclude_order_ids'] = vm.excl_order_map[field].join(',');
        }
        console.log(check_sku_dict);
        vm.service.apiCall('check_sku/', 'GET', check_sku_dict).then(function(data){
          field = data.data.sku_code;
          if(vm.scan_skus.indexOf(field) == -1) {
            if ('confirmed'==data.data.status) {
              vm.add_new_sku(data.data);
              vm.scan_skus.push(field);
              vm.add_excl_orders(data.data);
            } else {
              pop_msg(data.data);
            }
          } else {
            var status = true;
            for(var i = 0; i < vm.model_data.data.length; i++) {
              var temp_mrp = 0;
              if(vm.model_data.mrp) {
                temp_mrp = vm.model_data.mrp;
              }
              else if(data.data['batch_data'] && data.data.batch_data.length > 0 && data.data.batch_data[0]['mrp']) {
                temp_mrp = data.data.batch_data[0]['mrp'];
              }
              if(field == vm.model_data.data[i].sku_code && vm.model_data.data[i].is_new &&
                    vm.model_data.marketplace == vm.model_data.data[i].marketplace &&
                     (vm.model_data.data[i].ship_quantity > vm.model_data.data[i].return_quantity || vm.model_data.data[i].ship_quantity=="")
                     && (vm.permissions.user_type != 'marketplace_user' || (vm.permissions.user_type == 'marketplace_user' && vm.model_data.data[i].seller_id == vm.model_data.seller_type))
                     && (vm.industry_type != 'FMCG' || (vm.industry_type == 'FMCG' && vm.model_data.data[i].mrp == temp_mrp))) {
                vm.model_data.data[i].return_quantity = Number(vm.model_data.data[i].return_quantity) + 1;
                status = false;
                vm.add_excl_orders(vm.model_data.data[i]);
                break;
              }
              if(vm.sku_mapping[field] == vm.model_data.data[i].sku_code && vm.model_data.data[i].is_new &&
                    vm.model_data.marketplace == vm.model_data.data[i].marketplace &&
                     (vm.model_data.data[i].ship_quantity > vm.model_data.data[i].return_quantity || vm.model_data.data[i].ship_quantity=="")
                     && (vm.permissions.user_type != 'marketplace_user' || (vm.permissions.user_type == 'marketplace_user' && vm.model_data.data[i].seller_id == vm.model_data.seller_type))
                     && (vm.industry_type != 'FMCG' || (vm.industry_type == 'FMCG' && vm.model_data.data[i].mrp == temp_mrp))) {
                vm.model_data.data[i].return_quantity = Number(vm.model_data.data[i].return_quantity) + 1;
                status = false;
                break;
              }
              console.log(vm.excl_order_map);
            }
            if (status) {
              vm.add_new_sku(data.data);
            }
          }
          vm.model_data.mrp = '';
        });
        vm.model_data.return_sku_code = '';

      }
     }
    }

    vm.add_new_sku = function(new_sku) {
      var temp_mrp = 0;
      if(vm.model_data.mrp){
        temp_mrp = vm.model_data.mrp;
      }
      if (!$.isEmptyObject(new_sku.batch_data)) {
        if (new_sku.batch_data.length) {
          vm.model_data.data.push({'sku_code': new_sku.sku_code, 'sku_desc': new_sku.description, 'ship_quantity': new_sku.ship_quantity,
                                   'order_id': new_sku.order_id, 'return_quantity': 1, 'damaged_quantity': 0, 'track_id_enable': false,
                                   'is_new': true, 'marketplace':vm.model_data.marketplace, 'sor_id': new_sku.sor_id,
                                   'unit_price': new_sku.unit_price, 'old_order_id': new_sku.order_id, 'mrp': new_sku.batch_data[0].mrp,
                                   'manufactured_date': new_sku.batch_data[0].manufactured_date, 'expiry_date': new_sku.batch_data[0].expiry_date,'sgst': new_sku.sgst,'cgst': new_sku.cgst,'igst': new_sku.igst,
                                   'seller_id':  vm.model_data.seller_type})
        }
      } else {
        vm.model_data.data.push({'sku_code': new_sku.sku_code, 'sku_desc': new_sku.description, 'ship_quantity': new_sku.ship_quantity,
                               'order_id': new_sku.order_id, 'return_quantity': 1, 'damaged_quantity': 0, 'track_id_enable': false,
                               'is_new': true, 'marketplace':vm.model_data.marketplace, 'sor_id': new_sku.sor_id,
                               'unit_price': new_sku.unit_price, 'old_order_id': new_sku.order_id, 'mrp': temp_mrp,
                               'manufactured_date': '', 'expiry_date': '','sgst': new_sku.sgst,'cgst': new_sku.cgst,'igst': new_sku.igst,
                               'seller_id': vm.model_data.seller_type})
      }
      if(new_sku.order_id){
        var name = new_sku.order_id+"<<>>"+new_sku.sku_code;
        vm.orders_data[name] = {};
        angular.copy(new_sku, vm.orders_data[name]);
      }
    }

    vm.add_excl_orders = function(data_dict) {
      if(Number(data_dict.ship_quantity) <= Number(data_dict.return_quantity)) {
        if(vm.excl_order_map[data_dict.sku_code] == undefined) {
          vm.excl_order_map[data_dict.sku_code] = [];
        }
        if(data_dict.order_id != '') {
          vm.excl_order_map[data_dict.sku_code].push(data_dict.order_id);
        }
      }
    }

    vm.confirm_disable = false;
    vm.confirm_return = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('confirm_sales_return/', 'POST', elem, true).then(function(data, status, headers, config){
        if(typeof(data.data) == "string" && data.data == 'Updated Successfully') {
          pop_msg(data.data);
          vm.confirm_disable = true;
            Service.showNoty(data.data);
            vm.reloadData();
            vm.close();
            vm.orders_data = {};
        } else {
          vm.title = 'SCAN RETURNED ORDERS PRINT';

          if(typeof(data.data) == "string" && data.data.search("print-invoice") != -1) {

          var html = $(data.data);
          vm.print_page = $(html).clone();

            $state.go('app.inbound.SalesReturns.ScanReturnsPrint');
            $timeout(function () {
              $(".modal-body:visible").html(data.data);
            }, 3000);
          }

        }
        /*if(data.message) {
          pop_msg(data.data);
          vm.confirm_disable = true;
          if(data.data == 'Updated Successfully') {

            // Service.showNoty(data.data);
            // vm.reloadData();
            // vm.close();
            // vm.orders_data = {};
          }
        }*/
      });
    }

    vm.print = print;
    vm.print = function() {
      console.log(vm.print_page);
      vm.service.print_data(vm.print_page, "SCAN RETURNED ORDERS PRINT");
    }

    vm.print_page = "";

    vm.barcode = function() {

      vm.barcode_title = 'Barcode Generation';

      vm.model_data['barcodes'] = [];

      var elem = angular.element($('form'));

      elem = elem[0];

      elem = $(elem).serializeArray();

      var sku_list = [];

      var quant_list = [];

      angular.forEach(elem, function(barcode_data){

        if (barcode_data.name == "sku_code") {

          sku_list.push(barcode_data.value);

        }

        if (barcode_data.name == "return") {

          quant_list.push(barcode_data.value);

        }

      })

      for (var i=0; i<sku_list.length; i++){

        vm.model_data['barcodes'].push({'sku_code': sku_list[i], 'quantity': quant_list[i]});

      }


      vm.model_data['format_types'] = [];
      var key_obj =  {};
      vm.service.apiCall('get_format_types/').then(function(data){
        $.each(data['data']['data'], function(ke, val){
          vm.model_data['format_types'].push(ke);
          });
          key_obj = data['data']['data'];
      });



      $state.go('app.inbound.SalesReturns.barcode');
    }

  vm.market_list = [];
  vm.service.apiCall('get_marketplaces_list/?status=picked').then(function(data){
    if(data.message) {
      vm.market_list = data.data.marketplaces;
    }
  })

    vm.message = '';
    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 2000);
    }

    $scope.demo5 = function (field) {
    var title_value = 'Invalid Order Id';
    if (field == 'AWB No.') {
      title_value = 'Invalid ' + field
    }
    SweetAlert.swal({
        title: title_value,
        //text: 'Do you Want to add it',
        type: 'warning',
        //showCancelButton: true,
        confirmButtonColor: COLORS.danger,
        confirmButtonText: 'Ok',
        closeOnConfirm: true,
      },
      function (status) {
        //swal('Added!', 'Return Tracking ID added to index!', 'success');
        /*if (status) {
          vm.model_data.data.push({'sku_code': '', 'product_description':'', 'shipping_quantity': '',
                                           'return_quantity': 1, 'damaged_quantity': '', 'track_id_enable': true,
                                           'return_id': data, 'is_new': true});
          data = "";
        }*/
      });
    };

    vm.update_data = function(index , record, data) {
      vm.imei_data.scanning = false;
      if ((vm.scan_awb_order_no).length) {
        vm.scan_awb_order_no.splice($.inArray(vm.model_data.data[index]['awb_no'], vm.scan_awb_order_no),1);
      }
      vm.remove_serials(data);
      if(vm.excl_order_map[data[index].sku_code] && vm.excl_order_map[data[index].sku_code].indexOf(data[index].order_id) > -1) {
        vm.excl_order_map[data[index].sku_code].splice(vm.excl_order_map[data[index].sku_code].indexOf(data[index].order_id), 1);
      }

      data.splice(index, 1);
      vm.calOrdersData(record);
      if(data.length > 0 && !(record.order_id)) {

        var status = true;
        for(var i = 0; i < data.length; i++) {
          if(data[i].sku_code == record.sku_code && !(data[i].order_id)) {

            status = false;
            break;
          }
        }
        if(status) {
          var ind = vm.scan_skus.indexOf(record.sku_code);
          if(ind != -1) {
            vm.remove_serials(vm.scan_skus[ind]);
            vm.scan_skus.splice(ind,1);
          }
        }
      }
    }

   Array.prototype.insert = function(index, item) {
     this.splice(index, 0, item);
   }

    vm.add_next = function(index , record, data) {
      var temp_data = vm.orders_data[record.order_id+"<<>>"+record.sku_code];
      if(temp_data && temp_data.ship_quantity <= temp_data.return_quantity) {
        Service.showNoty("Ship Quantiy Equal To Return Quantity");
        return false;
      }
      if ((vm.scan_awb_order_no).length) {
        vm.scan_awb_order_no.push(vm.model_data.data[index]['awb_no']);
      }
      var temp = {order_id: record.order_id, sku_code: record.sku_code, sku_desc: record.sku_desc,
                  ship_quantity: record.ship_quantity, return_quantity: "",
                  damaged_quantity: "", is_new: true, sor_id: record.sor_id,
                  marketplace: record.marketplace, track_id_enable: record.track_id_enable,
                  invoice_number: record.invoice_number
                  };
      data.insert(index+1, temp);
    }

    vm.add_new_imei = function(data, field) {
      vm.model_data.data.push({'sku_code': data.data.sku_code, 'sku_desc': data.data.sku_desc,
                               'shipping_quantity': data.data.shipping_quantity, 'order_id': data.data.order_id,
                               'return_quantity': 1, 'damaged_quantity': '', 'track_id_enable': false,
                               'is_new': true, 'marketplace': '', 'return_type': '', 'sku_desc': data.data.sku_desc,
                               'invoice_number': data.data.invoice_number, 'returns_imeis': [field], 'damaged_imeis': [],
                               'damaged_imeis_reason': [], 'id': data.data.id, 'sor_id': data.data.sor_id, 'quantity': data.data.quantity,
                               'order_imei_id': data.data.order_imei_id});
      vm.imei_data["index"] = vm.model_data.data.length-1;
    }


    vm.return_types = ['Return to Origin(RTO)', 'Customer Initiated Return']
    vm.scan_imeis = []

    vm.imei_data = {};

    vm.scan_imei = function(event, field) {
      if ( event.keyCode == 13 && field) {
        vm.scan_imei_readonly = true;
        if(vm.scan_imeis.indexOf(field) == -1) {
          vm.service.apiCall('check_return_imei/', 'GET', {imei: field}).then(function(data){
            if(data.message) {
              if ('Success'==data.data.status) {
                vm.scan_imeis.push(field);
                //vm.return_serials(field);
                if(vm.scan_skus.indexOf(data.data.data.sku_code) == -1){
                    vm.scan_skus.push(data.data.data.sku_code);
                }
                status = "true";
                for(var i = 0; i < vm.model_data.data.length; i++) {
                  var temp = vm.model_data.data[i]
                  if(data.data.data.sku_code == temp.sku_code && temp.is_new && data.data.data.invoice_number == temp.invoice_number && data.data.data.order_id == temp.order_id) {
                    /*if(vm.user_type == 'marketplace_user' && temp.quantity < (vm.model_data.data[i].return_quantity + 1)) {
                      pop_msg("Quantity Exceeding the return quantity");
                    }
                    else {*/
                      vm.model_data.data[i].return_quantity += 1;
                      vm.model_data.data[i].returns_imeis.push(field);
                      vm.imei_data["index"] = vm.model_data.data.length-1;
                      vm.scan_imeis.push(field);
                      //vm.return_serials(field);
                      if(vm.scan_skus.indexOf(data.data.data.sku_code) == -1){
                        vm.scan_skus.push(data.data.data.sku_code);
                      }
                    //}
                    status = "false";
                    break;
                  }
                }
                if(status == "true"){
                  vm.add_new_imei(data.data, field);
                }
                vm.imei_data.scanning = true;

              } else {
                pop_msg(data.data.status);
              }
            }
            vm.scan_imei_readonly = false;
          });
        } else {
          pop_msg("Scanned Imei exists");
          vm.scan_imei_readonly = false;
        }
        vm.model_data.return_imei = '';
      }
    }

    vm.add_to_damage = function() {

      vm.imei_data.scanning = false;
      if(vm.imei_data.index > -1) {

        var data = vm.model_data.data[vm.imei_data.index];
        var index = data.returns_imeis.length -1;
        var imei = vm.model_data.data[vm.imei_data.index].returns_imeis[index];
        var reason = (vm.imei_data.reason)? vm.imei_data.reason: "";
        vm.model_data.data[vm.imei_data.index].returns_imeis.splice(index, 1);
        vm.model_data.data[vm.imei_data.index].damaged_imeis.push(imei);
        vm.model_data.data[vm.imei_data.index].damaged_imeis_reason.push(imei+"<<>>"+reason);
        vm.model_data.data[vm.imei_data.index].damaged_quantity = Number(data.damaged_quantity)+1;
        //vm.model_data.data[vm.imei_data.index].return_quantity = Number(data.return_quantity)-1;
        vm.imei_data.reason = "";
      }
    }

    vm.remove_serials = function(data) {

      console.log(data);
      data = data[0];
      if(data.returns_imeis && data.returns_imeis.length > 0) {
        angular.forEach(data.returns_imeis, function(imei){
          if (vm.scan_imeis.indexOf(imei) != -1) {
            vm.scan_imeis.splice(vm.scan_imeis.indexOf(imei), 1);
          }
        })
      }
      if(data.damaged_imeis && data.damaged_imeis.length > 0) {
        angular.forEach(data.damaged_imeis, function(imei){
          if (vm.scan_imeis.indexOf(imei) != -1) {
            vm.scan_imeis.splice(vm.scan_imeis.indexOf(imei), 1);
          }
        })
      }
    }

    vm.calOrdersData = function(data) {
      var temp_data = vm.orders_data[data.order_id+"<<>>"+data.sku_code];
      if (!temp_data) {
        return false;
      }
      var return_quantity = 0;
      angular.forEach(vm.model_data.data, function(sku_data, position){
        if(sku_data.order_id == data.order_id && sku_data.sku_code == data.sku_code) {
          return_quantity += Number(sku_data.return_quantity);
        }
      });
      temp_data.return_quantity = return_quantity;
    }

    vm.calOrdersDamagedData = function(data) {
      var temp_data = vm.orders_data[data.order_id+"<<>>"+data.sku_code];
      if (!temp_data) {
        return false;
      }
      var damaged_quantity = 0;
      angular.forEach(vm.model_data.data, function(sku_data, position){
        if(sku_data.order_id == data.order_id && sku_data.sku_code == data.sku_code) {
          damaged_quantity += Number(sku_data.damaged_quantity);
        }
      });
      temp_data.damaged_quantity = damaged_quantity;
    }

    vm.changeReturnQty = function(qty, index, data) {

      if(!data.order_id){
        return false;
      } else if(!data.return_quantity) {
        return false;
        vm.calOrdersData(data);
      }
      var temp_data = vm.orders_data[data.order_id+"<<>>"+data.sku_code];
      if(temp_data) {
        var return_quantity = 0;
        angular.forEach(vm.model_data.data, function(sku_data, position){
          if(sku_data.order_id == data.order_id && sku_data.sku_code == data.sku_code && position != index) {
            return_quantity += Number(sku_data.return_quantity);
          }
        });
        if(return_quantity < temp_data.ship_quantity) {
          if(Number(data.return_quantity) > (temp_data.ship_quantity - return_quantity)) {
            data.return_quantity = temp_data.ship_quantity - return_quantity;
          }
        } else {
          data.return_quantity = 0;
        }
        temp_data.return_quantity = Number(data.return_quantity) + return_quantity;
      }
      if(vm.return_process == 'sku_code') {
        vm.add_excl_orders(vm.model_data.data[index]);
      }
    }

    vm.changeDamagedQty = function(qty, index, data) {
      if(!data.order_id) {
        return false;
      } else if(!data.damaged_quantity) {
        return false;
        vm.calOrdersDamagedData(data);
      }
      var temp_data = vm.orders_data[data.order_id+"<<>>"+data.sku_code];
      if(temp_data) {
        var damaged_quantity = 0;
        angular.forEach(vm.model_data.data, function(sku_data, position) {
          if(sku_data.order_id == data.order_id && sku_data.sku_code == data.sku_code && position != index) {
            damaged_quantity += Number(sku_data.damaged_quantity);
          }
        });
        if(damaged_quantity < temp_data.ship_quantity) {
          if(Number(data.damaged_quantity) > (temp_data.return_quantity - damaged_quantity)) {
            data.damaged_quantity = temp_data.return_quantity - damaged_quantity;
          }
        } else {
          data.damaged_quantity = 0;
        }
        temp_data.damaged_quantity = Number(data.damaged_quantity) + damaged_quantity;
      }
    }

    vm.changeOrderId = function(qty, index, data) {

      if(vm.return_process != 'sku_code' || !vm.allocate_order || data.order_id == data.old_order_id){
        return false;
      }
      for(var ind=0;ind<vm.model_data.data.length;ind++){
        if(vm.model_data.data[ind].order_id == data.order_id && ind != index){
          data.order_id = data.old_order_id;
          pop_msg("Order Id already added in the list");
          return false
        }
      }
      var check_sku_dict = {'sku_code': data.sku_code, 'allocate_order': vm.allocate_order,
                            'marketplace': vm.model_data.marketplace, 'order_id': data.order_id}
      vm.service.apiCall('check_sku/', 'GET', check_sku_dict).then(function(api_data){
        if ('confirmed'==api_data.data.status && api_data.data.order_id) {
           console.log(api_data.data);
           if(api_data.data.ship_quantity < data.return_quantity){
             vm.service.alert_msg("Return quantity is more than shipped quantity.Confirm to Overwrite").then(function(msg) {
               if(msg == 'true') {
                 vm.update_order_det(data, api_data);
               }
               else {
                 data.order_id = data.old_order_id;
               }
             });
           }
           else {
             vm.update_order_det(data, api_data);
           }
          //vm.scan_skus.push(field);
        } else if(!api_data.data.order_id){
          pop_msg("Invalid Order Id");
          data.order_id = data.old_order_id;
        } else {
          pop_msg(api_data.data);
        }
        /*var temp_data = vm.orders_data[data.old_order_id+"<<>>"+data.sku_code];
        if(temp_data) {
          var return_quantity = 0;
          angular.forEach(vm.model_data.data, function(sku_data, position){
            if(sku_data.old_order_id == data.old_order_id && sku_data.sku_code == data.sku_code) {
              return_quantity += Number(sku_data.return_quantity);
            }
          });
          temp_data.return_quantity = Number(data.return_quantity) + return_quantity;
        }*/
      });
    }

    vm.update_order_det = function(data, api_data){
      if(vm.orders_data[data.old_order_id+'<<>>'+data.sku_code]){
        vm.orders_data[data.order_id+'<<>>'+data.sku_code] = data;
        delete vm.orders_data[data.old_order_id+'<<>>'+data.sku_code];
      }
      data.ship_quantity = api_data.data.ship_quantity;
      data.order_id = api_data.data.order_id;
      data.old_order_id = api_data.data.order_id;
      data.unit_price = api_data.data.unit_price;
      if(data.return_quantity>data.ship_quantity){
        data.return_quantity = data.ship_quantity;
      }
      if(data.damaged_quantity>data.ship_quantity){
        data.damaged_quantity = data.ship_quantity;
      }
      vm.add_excl_orders(data);
    }

    vm.return_processes = {return_id: 'Return ID', order_id: 'Order ID'};
    vm.return_process = 'order_id';
    if(vm.permissions.use_imei) {
      vm.return_processes['scan_imei'] = 'Scan IMEI';
      vm.return_process = 'scan_imei';
    }

    if(vm.awb_ship_type) {
      vm.return_processes['scan_awb'] = 'Scan AWB';
      vm.return_process = 'scan_awb';
    }

    vm.return_processes['sku_code'] = 'SKU Code';

    vm.scan_awb_order_no = []
    vm.scan_awb = function(event, field) {
      if (event.keyCode == 13 && field) {
        if(vm.scan_awb_order_no.indexOf(field) == -1) {
          vm.service.apiCall('check_returns/', 'GET', {awb_no: field}).then(function(data) {
            if(data.message) {
              if ('AWB No. is Invalid' == data.data) {
                $scope.demo5('AWB No.')
                vm.model_data.scan_awb_no = ''
              } else if (field+' is already confirmed' == data.data) {
                pop_msg(data.data);
                vm.model_data.scan_awb_no = ''
              } else if (data.data.indexOf("Already Returned") >= 0) {
                pop_msg(data.data);
                vm.model_data.scan_awb_no = ''
              } else {
                vm.model_data.scan_awb_no = ''
                angular.forEach(data.data, function(sku_data) {
                  sku_data['awb_no'] = field;
                  vm.model_data.data.push(sku_data);
                  var name = sku_data.order_id+"<<>>"+sku_data.sku_code;
                  vm.orders_data[name] = {};
                  angular.copy(sku_data, vm.orders_data[name]);
                })
                vm.scan_awb_order_no.push(field);
              }
            }
            vm.model_data.scan_order_id = "";
          });
        } else {
          pop_msg("Already Added In List");
          vm.model_data.scan_awb_no = ''
        }
      }
    }
  }
