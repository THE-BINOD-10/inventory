;(function(){

'use strict';

function AppCart($scope, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Auth, $stateParams, $modal, Data) {

  var vm = this;
  vm.service = Service;
  var empty_data = {data: [], customer_id: "", payment_received: "", order_taken_by: "", other_charges: [], shipment_time_slot: "", remarks: ""};
  vm.model_data = {};
  angular.copy(empty_data, vm.model_data);
  vm.date = new Date();
  vm.permissions = Session.roles.permissions;
  vm.user_type = vm.permissions.user_type;
  vm.central_order_mgmt = vm.permissions.central_order_mgmt;
  vm.order_exceed_stock = vm.permissions.order_exceed_stock;
  vm.deliver_address = ['Distributor Address'];
  vm.checked_address = vm.deliver_address[0];
  vm.shipment_addr = 'default';
  vm.manual_shipment_addr = false;
  vm.default_shipment_addr = true;
  vm.client_logo = Session.parent.logo;
  vm.api_url = Session.host;
  vm.is_portal_lite = Session.roles.permissions.is_portal_lite;

  vm.unique_levels = {};
  vm.sel_styles = {};
  vm.get_customer_cart_data = function() {

    vm.place_order_loading = true;
    vm.service.apiCall("get_customer_cart_data/").then(function(data){

      if(data.message) {

        angular.copy(data.data.data,vm.model_data.data);

        vm.model_data.invoice_type = data.data.invoice_types[0]
        if(vm.model_data.data.length > 0) {
          vm.unique_levels = {};
          angular.forEach(vm.model_data.data, function(sku){

            sku['org_price'] = sku.price;
            sku['sku_remarks'] = sku.remarks;
            sku.quantity = Number(sku.quantity);
            sku.invoice_amount = Number(sku.price) * sku.quantity;
            sku.total_amount = ((sku.invoice_amount*sku.tax) / 100) + sku.invoice_amount;
            if (!vm.unique_levels[sku.warehouse_level]) {
              vm.unique_levels[sku.warehouse_level] = sku.level_name;
            }

            vm.quantity_valid(sku);
          });
          vm.corporates = data.data.reseller_corporates;
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

  vm.add_quantities = function(sku){
    if (sku.quantity > sku.avail_stock) {
      sku.quantity = sku.avail_stock;
    }

    if(vm.sel_styles[sku.sku_style]){
      vm.sel_styles[sku.sku_style] += Number(sku.quantity);
    } else {
      vm.sel_styles[sku.sku_style] = Number(sku.quantity);
    }
  }

  vm.quantity_valid = function(row){
    if (row.quantity > row.avail_stock) {

      row.quantity = row.avail_stock;
      vm.service.showNoty("You can add "+row.avail_stock+" items only", "success", "topRight");
    }
  }

  /*vm.change_remarks = function(remark) {

    angular.forEach(vm.model_data.data, function(data){
      if(!data['sku_remarks']){
        data['remarks'] = vm.model_data.remarks;
      } else {
        data['remarks'] = data['sku_remarks'];
      }
    })
  }*/
  vm.change_sku_remarks = function(data) {

    data['remarks'] = data['sku_remarks'];
  }

  vm.date_changed = function(){
    //$('.datepicker').hide();
    // console.log(vm.model_data.shipment_date_new);
    //var date = new Date(vm.model_data.shipment_date_new);
    //vm.model_data.shipment_date = (date.getMonth() + 1) + '/' + date.getDate() + '/' +  date.getFullYear();
  }

vm.update_cartdata_for_approval = function() {
    var send = {}
    vm.service.apiCall("update_orders_for_approval/", "POST", send).then(function(response){
        if(response.message) {
          if(response.data.message == "success") {
            Data.my_orders = [];
            swal({
              title: "Success!",
              text: "Your Order Has Been Sent for Approval",
              type: "success",
              showCancelButton: false,
              confirmButtonText: "OK",
              closeOnConfirm: true
              },
              function(isConfirm){
                $state.go("user.App.Brands");
              }
            )
          } else {
            vm.insert_cool = true;
            vm.data_status = true;
            vm.service.showNoty(response.data, "danger", "bottomRight");
          }
        }
    });
  }

  vm.update_customer_cart_data = function(data) {

    if (vm.order_exceed_stock){
      if (data.available_stock < data.quantity){
        data.quantity = 1;//data.available_stock;
        vm.service.showNoty("Order quantity can't exceed available stock.");
      }
    }
    var send = {'sku_code': data.sku_id, 'quantity': data.quantity, 'level': data.warehouse_level,
                'price': data.price, 'remarks': data.remarks}
    vm.service.apiCall("update_customer_cart_data/", "POST", send).then(function(response){

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
    vm.unique_levels = {}

    if (vm.model_data.data) {

      for (var i = 0; i < vm.model_data.data.length; i++) {

        vm.update_sku_levels(vm.model_data.data, vm.model_data.data[i]);
        break;
      }

      angular.forEach(vm.model_data.data, function(sku){
      if (!vm.unique_levels[sku.warehouse_level]) {
          vm.unique_levels[sku.warehouse_level] = sku.level_name;
        }
      })
    }

    vm.cal_total();
  }

  vm.get_customer_cart_data();

  vm.checkDelivarableDates = function(date1, data) {

    date1 = new Date(date1);
    var status = true;
    for(let index = 0; index < data.length; index++) {
      if (data[index].del_date) {
        let temp = data[index].del_date.split("/");
        let date2 = new Date(temp[1]+"/"+temp[0]+"/"+temp[2]);
        if(date2 > date1) {
          return "Delivery is scheduled to be later than the expected date entered. Click on 'Cancel' to modify date or 'Confirm' to place order";
        }
      }
    }
    return "Are You Sure";
  }

  vm.data_status = false;
  vm.insert_cool = true;
  vm.insert_order_data = function(data_dict) {

    if (vm.user_type == 'reseller') {

      if (!(vm.model_data.shipment_date) || !(vm.model_data.po_number_header) || !(vm.model_data.client_name_header) || !($("#po-upload")[0].files.length)) {
        vm.service.showNoty("The Shipment Date, PO Number, Client Name and Uploaded PO's are Required Please Select", "success", "bottomRight");
      } else if (!(vm.model_data.shipment_time_slot)) {
        vm.service.showNoty("Please Select Shipment Slot", "success", "bottomRight");
      } else {
        vm.order_data_insertion(data_dict);
      }
    }else if(data_dict && data_dict.is_central_order){
      if (!(vm.model_data.client_name_header)){
        vm.service.showNoty("Project Name is mandatory")
      } else if (!(vm.model_data.shipment_date)) {
        vm.service.showNoty("The Shipment Date is Required. Please Select", "success", "bottomRight");
      } else {
        vm.order_data_insertion(data_dict);
      }
    }else {
      if (!(vm.model_data.shipment_date)) {

        vm.service.showNoty("The Shipment Date is Required. Please Select", "success", "bottomRight");
      } else {
        vm.order_data_insertion(data_dict);
      }
    }
  }

  vm.order_data_insertion = function(data_dict){

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
          if(data_dict && data_dict.is_sample){
            elem.push({'name': 'is_sample', 'value': true})
          }
          if(data_dict && data_dict.is_central_order){
            elem.push({'name': 'is_central_order', 'value': true})
          }
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
              } else {
                vm.insert_cool = true;
                vm.data_status = true;
                vm.service.showNoty(data.data);
              }
            } else {
              vm.insert_cool = true;
              vm.data_status = true;
              vm.service.showNoty(data.data);
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

    var total_price = 0;
    vm.sel_styles = {};
    angular.forEach(data, function(record){
      vm.add_quantities(record);
    });

    angular.forEach(data, function(record) {

      if (vm.sel_styles[record.sku_style]) {

        vm.priceRangesCheck(record, Number(vm.sel_styles[record.sku_style]));
      }

      if(vm.sku_group_data[record.sku_id] && vm.sku_group_data[record.sku_id][record.level_name] != record.level_name) {

        vm.sku_group_data[record.sku_id].quantity += record.quantity;
        vm.sku_group_data[record.sku_id].add_sku_total_price += (record.price * record.quantity);
      } else {

        vm.sku_group_data[record.sku_id] = {'sku_code': record.sku_id, 'quantity': record.quantity};
        vm.sku_group_data[record.sku_id][record.level_name] = record.level_name;
        vm.sku_group_data[record.sku_id].add_sku_total_price = (record.price * record.quantity);
      }

      vm.sku_group_data[record.sku_id].sku_style = record.sku_style;
    });

    var style_prices = {}
    angular.forEach(vm.sku_group_data, function(record) {
      if(style_prices[record.sku_style]) {
        style_prices[record.sku_style]['quantity'] += record.quantity;
        style_prices[record.sku_style]['total_price'] += record.add_sku_total_price;
      }
      else {
        style_prices[record.sku_style] = {}
        style_prices[record.sku_style]['quantity'] = record.quantity;
        style_prices[record.sku_style]['total_price'] = record.add_sku_total_price;
      }

      vm.sku_group_data[record.sku_code].effective_landing_price = style_prices[record.sku_style]['total_price']/style_prices[record.sku_style]['quantity'];
      vm.sku_group_data[record.sku_code].total_amount = style_prices[record.sku_style]['total_price']
    });
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
      //vm.update_customer_cart_data(record);
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
      vm.quantity_valid(data);
    }

    vm.update_sku_levels(vm.model_data.data, data);

    vm.update_customer_cart_data(data);
    vm.cal_total();
  }

  vm.change_remarks = function(data) {
    if(data){
      angular.forEach(vm.model_data.data, function(data){
        if(!data['sku_remarks']){
          data['remarks'] = vm.model_data.remarks;
        } else {
          data['remarks'] = data['sku_remarks'];
      }
    })
      vm.update_customer_cart_data(data);
    }
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
    if (vm.user_type == 'reseller') {

      if (!vm.model_data.client_name_header) {

        vm.service.showNoty("The Customer Name is Required Please Select", "success", "bottomRight");
      } else {
        if (vm.unique_levels['0'] || vm.unique_levels['2']) {
          Service.showNoty("Enquiry Order can't be placed to <b>L0 & L2</b> levels, Please remove them");
          return false;
        } else {
          if (vm.model_data.data.length == 0) {

            Service.showNoty('Please Items To Cart First');
            return false;
          }
          vm.place_order_loading = true;
          var send = {'name': vm.model_data.client_name_header};
          Service.apiCall("insert_enquiry_data/", "POST", send).then(function(data){

            if(data.message) {

              if(data.data == 'Success') {

                vm.model_data.data = [];
                Data.enquiry_orders = [];
                Service.showNoty('Successfully added');
                $state.go("user.App.Brands");
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
    }
  }

  vm.upload_file_name = "";
  $scope.$on("fileSelected", function (event, args) {
    $scope.$apply(function () {
      vm.upload_file_name = args.file.name;
    });
  });

  vm.selectShipmentAddr = function (shipment_type) {
    if (shipment_type === 'manual') {
      vm.manual_shipment_addr = true;
      vm.default_shipment_addr = false;
    } else {
      vm.default_shipment_addr = true;
      vm.manual_shipment_addr = false;
    }
  }
}

angular
  .module('urbanApp')
    .controller('AppCart', ['$scope', '$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Auth', '$stateParams', '$modal', 'Data', AppCart]);
})();
