;(function(){

'use strict';

function AppCart($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams, $modal, Data) {

  var vm = this;
  vm.service = Service;
  var empty_data = {data: [], customer_id: "", payment_received: "", order_taken_by: "", other_charges: [], shipment_time_slot: "", remarks: ""};
  vm.model_data = {};
  angular.copy(empty_data, vm.model_data);
  vm.date = new Date();
  vm.user_type = Session.roles.permissions.user_type;

  vm.get_customer_cart_data = function() {
    
    vm.place_order_loading = true; 
    vm.service.apiCall("get_customer_cart_data").then(function(data){

      if(data.message) {

        angular.copy(data.data.data,vm.model_data.data);

        if(vm.model_data.data.length > 0) {
          angular.forEach(vm.model_data.data, function(sku){

            sku['org_price'] = sku.price;
            sku.quantity = Number(sku.quantity);
            sku.invoice_amount = Number(sku.price) * sku.quantity;
            sku.total_amount = ((sku.invoice_amount*sku.tax) / 100) + sku.invoice_amount;
          });

          var unique_skus = {};

          angular.forEach(vm.model_data.data, function(sku){

            if(!unique_skus[sku.sku_id]) {

              vm.update_sku_levels(vm.model_data.data, sku);
              unique_skus[sku.sku_id] = true;
            }
          });

          vm.data_status = true;
          vm.change_remarks();
          vm.cal_total();
        }
        vm.place_order_loading = false;
      }
      vm.place_order_loading = false;
    })
  }

  vm.change_remarks = function(remark) {

    angular.forEach(vm.model_data.data, function(data){
      data['remarks'] = vm.model_data.remarks;
    })
  }

  vm.date_changed = function(){
    //$('.datepicker').hide();
    // console.log(vm.model_data.shipment_date_new);
    //var date = new Date(vm.model_data.shipment_date_new);
    //vm.model_data.shipment_date = (date.getMonth() + 1) + '/' + date.getDate() + '/' +  date.getFullYear();
  }

  vm.update_customer_cart_data = function(data) {

    var send = {'sku_code': data.sku_id, 'quantity': data.quantity, 'level': data.warehouse_level, 'price': data.price}
    vm.service.apiCall("update_customer_cart_data", "POST", send).then(function(response){

    });
  }

  vm.delete_customer_cart_data = function(data) {

    var send = {};
    send[data.sku_id] = data.warehouse_level;
    vm.service.apiCall("delete_customer_cart_data", "GET", send);
  }

  vm.remove_item = function(index) {

    var deleted_sku_id = vm.model_data.data[index].sku_id;
    vm.delete_customer_cart_data(vm.model_data.data[index]); 
    vm.model_data.data.splice(index,1);
    delete vm.sku_group_data[deleted_sku_id];

    if (vm.model_data.data) {
      
      for (var i = 0; i < vm.model_data.data.length; i++) {
        
        if(deleted_sku_id == vm.model_data.data[i].sku_id){

          vm.update_sku_levels(vm.model_data.data, vm.model_data.data[i]);
          break; 
        }
      }
    }

    vm.cal_total();
  }

  vm.get_customer_cart_data();

  vm.checkDelivarableDates = function(date1, data) {

    date1 = new Date(date1);
    var status = true;
    for(let index = 0; index < data.length; index++) {
      if (data[index].del_date) {
        let date2 = new Date(data[index].del_date);
        if(date2 > date1) {
          return "Products Will Deliver As Per Delivery Shedule";
        }
      }
    }
    return "Are You Sure";
  }

  vm.data_status = false;
  vm.insert_cool = true;
  vm.insert_order_data = function(form) {

    if (vm.user_type == 'customer') {

      if (!(vm.model_data.shipment_date)) {
      
        vm.service.showNoty("The Shipment Date is Required Please Select", "success", "bottomRight");
      } else {
        vm.order_data_insertion(form);
      }
    } else {
      if (!(vm.model_data.shipment_date) || !(vm.model_data.po_number_header) || !(vm.model_data.client_name_header)) {
        vm.service.showNoty("The Shipment Date, PO Number and Client Name are Required Please Select", "success", "bottomRight");
      } else if (!(vm.model_data.shipment_time_slot)) {
        vm.service.showNoty("Please Select Shipment Slot", "success", "bottomRight");
      } else {
        vm.order_data_insertion(form);
      }
    }
  }

  vm.order_data_insertion = function(form){

    if(vm.insert_cool && vm.data_status) {
      var msg = vm.checkDelivarableDates(vm.model_data.shipment_date, vm.model_data.data);
      swal({
        title: "Place Order!",
        text: msg,
        type: "warning",
        showCancelButton: true,
        confirmButtonText: "Sure",
        closeOnConfirm: true
        },
        function(isConfirm){
          if(isConfirm){

          vm.insert_cool =false
          vm.data_status = false;
          var elem = angular.element($('form'));
          elem = elem[0];
          elem = $(elem).serializeArray();
          vm.place_order_loading = true;
          vm.service.apiCall('insert_order_data/', 'POST', elem).then(function(data){
            if(data.message) {

              if(data.data.indexOf("Success") != -1) {
                if (vm.model_data.po_number_header) {
                  vm.uploadPO(vm.model_data.po_number_header, vm.model_data.client_name_header);
                }
                angular.copy(empty_data, vm.model_data);
                angular.copy(empty_final_data, vm.final_data);
                Data.my_orders = [];
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

            vm.place_order_loading = false;
            vm.insert_cool = true
          })

          }
        }
      )
    }
  }

  vm.get_total_sku_level_quantity = function(data, row) {
    var total_quantity = 0;

    angular.forEach(data, function(record){
          
      if (record.quantity && row.sku_id == record.sku_id) {
        
        total_quantity += Number(record.quantity);
      }
    });
    return total_quantity;
  }

  vm.sku_group_data = {};
  vm.update_sku_levels = function(data, row){

    var total_quantity = vm.get_total_sku_level_quantity(data, row);

    if(!vm.sku_group_data[row.sku_id]) {
      vm.sku_group_data[row.sku_id] = {sku_code: row.sku_id, quantity: total_quantity}
    } else {
      vm.sku_group_data[row.sku_id].quantity = total_quantity;
    }
    var count = 0;
    var amount = 0;
    var total_amount = 0;
    angular.forEach(data, function(record) {

      if (row.sku_id == record.sku_id) {
        vm.priceRangesCheck(record, total_quantity);
        count += record.quantity;
        amount += record.price;
        total_amount += record.invoice_amount;
      }
    });
    vm.sku_group_data[row.sku_id].effective_landing_price = total_amount/count;
    vm.sku_group_data[row.sku_id].total_amount = total_amount;
  }

  vm.priceRangesCheck = function(record, quantity){

    var price = record.price;
    if (record.prices) {
      
      var prices = record.prices;

      for (var priceRng = 0; priceRng < prices.length; priceRng++) {

        if(quantity >= prices[priceRng].min_unit_range && quantity <= prices[priceRng].max_unit_range) {

          price = prices[priceRng].price;
          break;
        }
      }

      if (priceRng >= prices.length ) {

        price = prices[prices.length-1].price;
      }
    }

    if (record.price != price) {

      record.price = price;
      vm.update_customer_cart_data(record);
    } else {

      record.price = price;
    }
    record.invoice_amount = Number(price) * record.quantity;
    record.total_amount = ((record.invoice_amount * record.tax) / 100) + record.invoice_amount;
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

    if (data.quantity == 0 || data.quantity == '') {
      data.quantity = 1;
      Service.showNoty("You should select minimum one item", "success", "topRight");
    } else {
      data.quantity = Number(data.quantity);
    }

    vm.update_sku_levels(vm.model_data.data, data);

    //vm.update_customer_cart_data(data);
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
  };

  $('#shipment_date').datepicker();

  $('#shipment_date').on('focus',function(){
    $(this).trigger('blur');
  });

  vm.uploadPO = function(po, name) {

    var formData = new FormData();
    var el = $("#po-upload");
    var files = el[0].files;

    if(files.length == 0){

      return false;
    }

    $.each(files, function(i, file) {
      formData.append('po_file', file);
    });

    formData.append('po_number', po);
    formData.append('customer_name', name);

    vm.uploading = true;
    $.ajax({url: Session.url+'upload_po/',
            data: formData,
            method: 'POST',
            processData : false,
            contentType : false,
            xhrFields: {
                withCredentials: true
            },
            'success': function(response) {
              if(response == 'Uploaded Successfully') {

                Service.showNoty(response);
              } else {
                Service.showNoty(response, 'warning');
              }
              vm.uploading = false;
            },
            'error': function(response) {
              console.log('fail');
              Service.showNoty('Something Went Wrong', 'warning');
              vm.uploading = false;
            }
    });
  }

  vm.place_enquiry = function() {

    if (vm.model_data.data.length == 0) {

      Service.showNoty('Please Items To Cart First');
      return false;
    }
    vm.place_order_loading = true;
    Service.apiCall("insert_enquiry_data/").then(function(data){

      if(data.message) {

        if(data.data == 'Success') {

          vm.model_data.data = [];
          Data.enquiry_orders = [];
          Service.showNoty('Successfully added');
        } else {

          Service.showNoty(data.data, 'warning');
        }
      } else {

        Service.showNoty("Something Went Wrong");
      }
      vm.place_order_loading = false;
    });
  }
}

angular
  .module('urbanApp')
    .controller('AppCart', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', '$modal', 'Data', AppCart]);
})();
