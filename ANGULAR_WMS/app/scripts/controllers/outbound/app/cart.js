'use strict';

function AppCart($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams) {

  console.log($state);
  console.log($stateParams);
  var vm = this;
  vm.service = Service;
  var empty_data = {data: [], customer_id: "", payment_received: "", order_taken_by: "", other_charges: [], shipment_time_slot: "", remarks: ""};
  vm.model_data = {};
  angular.copy(empty_data, vm.model_data);

  vm.get_customer_cart_data = function() {

    vm.service.apiCall("get_customer_cart_data").then(function(data){
      if(data.message) {

        angular.copy(data.data.data,vm.model_data.data);
        if(vm.model_data.data.length > 0) {
          vm.data_status = true;
          vm.change_remarks();
          vm.cal_total();
        }
      }
    })
  }

  vm.change_remarks = function(remark) {

    angular.forEach(vm.model_data.data, function(data){
      data['remarks'] = vm.model_data.remarks;
    })
  }

  vm.date_changed = function(){
    //$('.datepicker').hide();
    console.log(vm.model_data.shipment_date_new);
    //var date = new Date(vm.model_data.shipment_date_new);
    //vm.model_data.shipment_date = (date.getMonth() + 1) + '/' + date.getDate() + '/' +  date.getFullYear();
  }

  vm.update_customer_cart_data = function(data) {

    var send = {'sku_code': data.sku_id, 'quantity': data.quantity}
    vm.service.apiCall("update_customer_cart_data", "GET", send)
  }

  vm.delete_customer_cart_data = function(data) {

    var send = {sku_codes: ""}
    angular.forEach(data, function(record){
      send.sku_codes = send.sku_codes + record.sku_id + ","
    })
    send.sku_codes = send.sku_codes.slice(0,-1);
    vm.service.apiCall("delete_customer_cart_data", "GET", send)
  }

  vm.remove_item = function(index) {

    vm.delete_customer_cart_data([vm.model_data.data[index]]);
    vm.model_data.data.splice(index,1);
    vm.cal_total();
  }

  vm.get_customer_cart_data();

  vm.data_status = false;
  vm.insert_cool = true;
  vm.insert_order_data = function(form) {
    if (!(vm.model_data.shipment_date)) {
      vm.service.showNoty("Please Select Shipment Date", "success", "bottomRight");
    } else {
      if(vm.insert_cool && vm.data_status) {
        vm.insert_cool =false
        vm.data_status = false;
        var elem = angular.element($('form'));
        elem = elem[0];
        elem = $(elem).serializeArray();
        vm.service.apiCall('insert_order_data/', 'GET', elem).then(function(data){
          if(data.message) {
            if(data.data.indexOf("Success") != -1) {
              vm.delete_customer_cart_data(vm.model_data.data);
              angular.copy(empty_data, vm.model_data);
              angular.copy(empty_final_data, vm.final_data);
              swal({
                title: "Success!",
                text: "Your Order Has Been Placed Successfully",
                type: "success",
                showCancelButton: false,
                confirmButtonText: "OK",
                closeOnConfirm: true
                },
                function(isConfirm){
                  $state.go("user.App.Brands");
                }
              )
            }
          }
          vm.insert_cool = true
        })
      }
    }
  }

  vm.change_cart_quantity = function(data, stat) {

    if (stat) {
      data.quantity = Number(data.quantity) + 1;
      vm.change_amount(data);
    } else {
      if (Number(data.quantity)> 1) {
        data.quantity = Number(data.quantity) - 1;
        vm.change_amount(data);
      }
    }
  }

  vm.change_amount = function(data) {

    var find_data=data;
    data.quantity = Number(data.quantity);
    data.invoice_amount = Number(data.price)*data.quantity;
    data.total_amount = ((data.invoice_amount*data.tax)/100)+data.invoice_amount;
    vm.update_customer_cart_data(data);
    vm.cal_total();
  }

  var empty_final_data = {total_quantity: 0, amount: 0, tax_amount: 0, total_amount: 0}
  vm.final_data = {};
  angular.copy(empty_final_data, vm.final_data);
  vm.cal_total = function() {

    angular.copy(empty_final_data, vm.final_data)
    angular.forEach(vm.model_data.data, function(record){
      vm.final_data.total_amount += Number(record.total_amount);
      vm.final_data.total_quantity += Number(record.quantity);
      vm.final_data.amount += Number(record.invoice_amount);
    })
    vm.final_data.tax_amount = vm.final_data.total_amount - vm.final_data.amount;
    console.log(vm.final_data);
  }

  $('#shipment_date').datepicker();

  $('#shipment_date').on('focus',function(){
    $(this).trigger('blur');
  });
}

angular
  .module('urbanApp')
  .controller('AppCart', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', AppCart]);
