'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SalesReturnsCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'SweetAlert', 'COLORS', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, SweetAlert, COLORS, Service) {
    var vm = this;
    vm.service = Service;
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

      vm.confirm_disable = false;
      $state.go('app.inbound.SalesReturns');
    }

    vm.scan_pop = scan_pop;
    function scan_pop() {
      vm.model_data = {data:[]};
      $state.go('app.inbound.SalesReturns.ScanReturns'); 
    }

    vm.model_data = {'data':[]}

    vm.scan_track = function(event, field) {
      if ( event.keyCode == 13 && field.length > 0) {
        vm.service.apiCall('check_returns/', 'GET', {order_id: field}).then(function(data){
          if(data.message) {
            if ('Order Id is invalid' == data.data) {
              check_data(field);
            } else if (field+' is already confirmed' == data.data){
              pop_msg(data.data);
            } else {  
              vm.model_data.data.push(data.data)
            }
          }
          vm.model_data.scan_order_id = "";
        });
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

    vm.scan_sku = function(event, field) {
      if ( event.keyCode == 13 && field.length > 0) {
        vm.service.apiCall('check_sku/', 'GET', {sku_code: field}).then(function(data){
          if(data.message) {
            if ('confirmed'==data.data) {
              vm.add_new_sku(field);
            } else {
              pop_msg(data.data);
            }
          }
          field = '';
        });
        vm.model_data.return_sku_code = '';
      }
    }

    vm.add_new_sku = function(field) {
      var i = 0
      for(; i < vm.model_data.data.length; i++) {
        if(field == vm.model_data.data[i].sku_code) {
          vm.model_data.data[i].return_quantity += 1;
          break;
        }
      }
      if (i >= vm.model_data.data.length || vm.model_data.data.length == 0) {
        vm.model_data.data.push([{'sku_code': field, 'product_description':'', 'shipping_quantity': '', 'order_id':'',
                                           'return_quantity': 1, 'damaged_quantity': '', 'track_id_enable': false, 'is_new': true}])
      }
    }

    vm.confirm_disable = false;
    vm.confirm_return = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('confirm_sales_return/', 'GET', elem).then(function(data){
        if(data.message) {
          pop_msg(data.data);
          vm.confirm_disable = true;
          if(data.data == 'Updated Successfully') {
            vm.close();
          }
        }
      }); 
    }

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
  }

