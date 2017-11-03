'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SalesReturnsCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'SweetAlert', 'COLORS', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, SweetAlert, COLORS, Service) {
    var vm = this;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.user_type = Session.user_profile.user_type
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

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    vm.close = close;
    function close() {

      vm.scan_returns = [];
      vm.scan_orders = [];
      vm.scan_skus = [];
      vm.scan_imeis = [];
      vm.confirm_disable = false;
      vm.imei_data.reason = "";
      vm.imei_data.scanning = false;
      $state.go('app.inbound.SalesReturns');
    }

    vm.scan_pop = scan_pop;
    function scan_pop() {
      vm.model_data = {data:[]};
      $state.go('app.inbound.SalesReturns.ScanReturns'); 
    }

    vm.model_data = {'data':[]}

    vm.scan_orders = []
    vm.scan_track = function(event, field) {
      if ( event.keyCode == 13 && field) {
        if(vm.scan_orders.indexOf(field) == -1) {
          vm.service.apiCall('check_returns/', 'GET', {order_id: field}).then(function(data){
            if(data.message) {
              if ('Order Id is invalid' == data.data) {
                check_data(field);
              } else if (field+' is already confirmed' == data.data){
                pop_msg(data.data);
              } else {
              vm.model_data.data.push(data.data[0])
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
      if ( event.keyCode == 13 && field) {
        vm.service.apiCall('check_sku/', 'GET',{'sku_code': field}).then(function(data){
          field = data.data.sku_code;
          if(vm.scan_skus.indexOf(field) == -1) {
            if ('confirmed'==data.data.status) {
              vm.add_new_sku(data.data);
              vm.scan_skus.push(field);
            } else {
              pop_msg(data.data);
            }
          } else {
            var status = true;
            for(var i = 0; i < vm.model_data.data.length; i++) {
              if(field == vm.model_data.data[i].sku_code && vm.model_data.data[i].is_new && vm.model_data.marketplace == vm.model_data.data[i].marketplace) {
                vm.model_data.data[i].return_quantity += 1;
                status = false;
                break;
              }
              if(vm.sku_mapping[field] == vm.model_data.data[i].sku_code && vm.model_data.data[i].is_new && vm.model_data.marketplace == vm.model_data.data[i].marketplace) {
                vm.model_data.data[i].return_quantity += 1;
                status = false;
                break;
              }
            }
            if (status) {
              vm.add_new_sku(data.data);
            }
          }
        });
        vm.model_data.return_sku_code = '';
      }
    }

    vm.add_new_sku = function(new_sku) {
      vm.model_data.data.push({'sku_code': new_sku.sku_code, 'sku_desc': new_sku.description, 'shipping_quantity': '', 'order_id':'',
                                'return_quantity': 1, 'damaged_quantity': '', 'track_id_enable': false,
                                'is_new': true, 'marketplace':vm.model_data.marketplace, 'sor_id': vm.model_data.sor_id})
    }

    vm.confirm_disable = false;
    vm.confirm_return = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('confirm_sales_return/', 'POST', elem, true).then(function(data){
        if(data.message) {
          pop_msg(data.data);
          vm.confirm_disable = true;
          if(data.data == 'Updated Successfully') {
            vm.reloadData();
            vm.close();
          }
        }
      });
    }

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

      vm.model_data['format_types'] = ['format1', 'format2', 'format3']

      var key_obj = {'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details'}

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
    var data = field;
    SweetAlert.swal({
        title: 'Order Id not Found',
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

      vm.remove_serials(data.splice(index, 1));
      data.splice(index, 1);
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

    vm.add_new_imei = function(data, field) {
      vm.model_data.data.push({'sku_code': data.data.sku_code, 'product_description': data.data.sku_desc,
                               'shipping_quantity': data.data.shipping_quantity, 'order_id': data.data.order_id,
                               'return_quantity': 1, 'damaged_quantity': '', 'track_id_enable': false,
                               'is_new': true, 'marketplace': '', 'return_type': '', 'sku_desc': data.data.sku_desc,
                               'invoice_number': data.data.invoice_number, 'returns_imeis': [field], 'damaged_imeis': [],
                               'damaged_imeis_reason': [], 'id': data.data.id, 'sor_id': data.data.sor_id, 'quantity': data.data.quantity});
      vm.imei_data["index"] = vm.model_data.data.length-1;
    }


    vm.return_types = ['Return to Origin(RTO)', 'Customer Initiated Return']
    vm.scan_imeis = []

    vm.imei_data = {};

    vm.scan_imei = function(event, field) {
      if ( event.keyCode == 13 && field) {
        if(vm.scan_imeis.indexOf(field) == -1) {
          vm.service.apiCall('check_return_imei/', 'GET', {imei: field}).then(function(data){
            if(data.message) {
              if ('Success'==data.data.status) {
                status = "true";
                for(var i = 0; i < vm.model_data.data.length; i++) {
                  var temp = vm.model_data.data[i]
                  if(data.data.data.sku_code == temp.sku_code && temp.is_new && data.data.data.invoice_number == temp.invoice_number && data.data.data.order_id == temp.order_id) {
                    if(vm.user_type == 'marketplace_user' && temp.quantity < (vm.model_data.data[i].return_quantity + 1)) {
                      pop_msg("Quantity Exceeding the return quantity");
                    }
                    else {
                      vm.model_data.data[i].return_quantity += 1;
                      vm.model_data.data[i].returns_imeis.push(field);
                      vm.imei_data["index"] = vm.model_data.data.length-1;
                      vm.scan_imeis.push(field);
                      //vm.return_serials(field);
                      if(vm.scan_skus.indexOf(data.data.data.sku_code) == -1){
                        vm.scan_skus.push(data.data.data.sku_code);
                      }
                    }
                    status = "false";
                    break;
                  }
                }
                if(status == "true"){
                  vm.add_new_imei(data.data, field);
                  vm.scan_imeis.push(field);
                  //vm.return_serials(field);
                  if(vm.scan_skus.indexOf(data.data.data.sku_code) == -1){
                    vm.scan_skus.push(data.data.data.sku_code);
                  }
                }
                vm.imei_data.scanning = true;

              } else {
                pop_msg(data.data.status);
              }
            }
          });
        } else {
          pop_msg("Scanned Imei exists");
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
  }

