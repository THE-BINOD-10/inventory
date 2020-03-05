'use strict';

function CreateAllocations($scope, $filter, $http, $q, Session, colFilters, Service, $state, $window, $timeout, Data, SweetAlert) {

  $scope.msg = "start";
  var vm = this;
  vm.order_type_value = "offline";
  vm.service = Service;
  vm.g_data = Data.create_orders;
  vm.company_name = Session.user_profile.company_name;
  vm.order_exceed_stock = Boolean(Session.roles.permissions.order_exceed_stock);
  vm.permissions = Session.roles.permissions;
  vm.brand_categorization = Session.roles.permissions.brand_categorization;
  vm.model_data = {}
  vm.dispatch_data = []
  var empty_data = {data: [{sku_id: "", quantity: 0, price: 0, cgst_tax: 0, sgst_tax: 0, igst_tax: 0,
                            enable_serial: false, serials: []}],
                    customer_id: "", customer_name: "", tax_type: ""};

  angular.copy(empty_data, vm.model_data);

  function check_exist(sku_data, index) {

    for(var i = 0; i < vm.model_data.data.length; i++) {

      if((vm.model_data.data[i].sku_id == sku_data.sku_id) && (index != i)) {

        sku_data.sku_id = "";
        vm.service.showNoty("It is already exist in index");
        return false;
      }
    }
    return true;
  }


  // Fill Customer Info Code Start
  vm.get_customer_data = function(item, model, label, event) {
    vm.model_data["customer_id"] = item.customer_id;
    vm.model_data["customer_name"] = item.name;
    vm.model_data["tax_type"] = item.tax_type;
  }
  // Fill Customer Info Code Ends

  //Fill SKU Info Code Starts
  vm.get_sku_data = function(record, item, index) {

    record.sku_id = item.wms_code;
    if(!vm.model_data.blind_order && !(check_exist(record, index))){
      return false;
    }
    if(!vm.model_data.customer_name){
      record.sku_id = "";
      colFilters.showNoty("Please Select Customer First");
      return false;
    }
    angular.copy(empty_data.data[0], record);
    record.sku_id = item.wms_code;
    record["description"] = item.sku_desc;
    if(vm.permissions.use_imei && item.enable_serial_based) {
      record['enable_serial'] = true;
    }
    if(!record.enable_serial) {
      record["quantity"] = 1;
    }
    $timeout(function() {
       vm.get_sku_attributes(record, item, index);
     }, 1000);
    vm.change_tax_type();
  }
  vm.order_extra_fields = []
  vm.get_order_extra_fields = function(){
    vm.service.apiCall("get_order_extra_fields/").then(function(data){
      if(data.message) {
        vm.extra_fields = data.data.order_level_data
        if(data.data.order_level_data)
        {
          vm.exta_model ={}
          vm.order_extra_fields = data.data.order_level;
           for(var i=0 ; i< vm.order_extra_fields.length; i++)
           {
              vm.exta_model[vm.order_extra_fields[i]] = '';
           }
         }
        }
      })
    }
    vm.get_order_extra_fields();
    vm.get_extra_order_options  = function()
      {
        vm.service.apiCall("get_order_extra_options/").then(function(data){
          if(data.message) {
            vm.extra_order_options = data.data;
          }

        })
      }
      vm.get_extra_order_options();

      vm.get_sku_attributes  = function(record, item, index)
      {
        vm.service.apiCall("get_sku_attributes_data/?wms_code="+item.wms_code).then(function(data){
          if(data.message) {
           Object.assign(vm.model_data.data[index], data.data.attribute_dict)
          }

        })
      }
  //Fill SKU Info Code Ends

  //Create Allocation Code Starts
  vm.bt_disable = false;
  vm.insert_allocation_data = function(event, form) {
    if (event.keyCode != 13) {
      if (form.$valid) {
        if (vm.model_data.blind_order) {
          for (var i = 0; i < vm.model_data.data.length; i++) {
            if (vm.model_data.data[i].sku_id && (!vm.model_data.data[i].location)) {
              colFilters.showNoty("Please locations");
              return false;
              break;
            }
          }
        }
        vm.bt_disable = true;
        var elem = angular.element($('form'));
        elem = elem[0];
        elem = $(elem).serializeArray();
        vm.service.apiCall('insert_allocation_data/', 'POST', elem).then(function(data){
          if(data.message) {
            if(data.data.indexOf("Success") != -1) {
              angular.copy(empty_data, vm.model_data);
              vm.final_data = {total_quantity:0,total_amount:0};
              vm.from_custom_order = false;
            }
            colFilters.showNoty(data.data);
          }
          vm.bt_disable = false;
        })
      } else {
        colFilters.showNoty("Fill Required Fields");
      }
    }
  }
  //Create Allocation Code Ends

  // Plus or Minus Button Code Starts
  vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
  }
  // Plus or Minus Button Code Ends

  //Add New Row Code Starts
  vm.update_data = update_data;
  function update_data(index, data, last) {
    if (last && (!vm.model_data.data[index].sku_id)) {
      return false;
    }
    if (last) {
      vm.model_data.data.push({sku_id: "", quantity: "", price: 0, cgst_tax: 0, sgst_tax: 0, igst_tax: 0,
                                enable_serial: false, serials: []});
    } else {
      vm.model_data.data.splice(index,1);
    }
  }
  //Add New Row Code Ends

  //Get Customer Price API Code Starts
  vm.get_customer_sku_prices = function(sku) {

    var d = $q.defer();
    var data = {sku_codes: sku, cust_id: vm.model_data.customer_id, tax_type: vm.model_data.tax_type}
    vm.service.apiCall("get_customer_sku_prices/", "POST", data).then(function(data) {

      if(data.message) {
        d.resolve(data.data);
      }
    });
    return d.promise;
  }
  //Get Customer Price API Code Ends

  // Updating Price and Tax Code Starts
  vm.change_tax_type = function() {
    var tax_name = vm.model_data.tax_type;
    if(!(vm.model_data.tax_type)) {
      tax_name = 'DEFAULT';
      angular.forEach(vm.model_data.data, function(record) {
        if(record.sku_id) {
          record.tax = 0;
          record.sgst_tax = 0;
          record.cgst_tax = 0;
          record.igst_tax = 0;
        }
      })
    } else {

      angular.forEach(vm.model_data.data, function(record) {

        if(record.sku_id) {
          vm.get_customer_sku_prices(record.sku_id).then(function(data){
            if(data.length > 0) {
              console.log(data);
              record.price = data[0].price;
              if(tax_name == 'intra_state') {
                record.cgst_tax = data[0].cgst_tax;
                record.sgst_tax = data[0].sgst_tax;
              }
              else {
                record.igst_tax = data[0].igst_tax;
              }
            }
          })
        }
      })
    }
    //vm.cal_total();
  }
  // Updating Price and Tax Code Ends

  // Serial Based Scan Code Starts
  vm.checkAndAdd = function(scan) {

    var status = false;
    for(var i = 0; i < vm.model_data.data.length; i++) {

      if(vm.model_data.data[i].serials.indexOf(scan) > -1){
        status = true;
        break;
      }
    }
    return status;
  }

  vm.serial_scan = function(event, scan, sku_data) {
    if ( event.keyCode == 13 && scan) {
      event.preventDefault();
      sku_data.serial = "";
      if(!sku_data.sku_id) {
        vm.service.showNoty("Please Select SKU Code First");
      }
      else {
        var elem = {serial: scan, cost_check:vm.model_data.blind_order};
        vm.service.apiCall('check_imei/', 'GET', elem).then(function(data){
          if(data.message) {
            if(data.data.status == "Success") {
              if (data.data.data.sku_code != sku_data.sku_id) {
                vm.service.showNoty("IMEI Code not matching with SKU code");
              } else if(vm.checkAndAdd(scan)) {
                vm.service.showNoty("Already Scanned")
              } else {
                sku_data.serials.push(scan);
                sku_data.quantity = sku_data.serials.length;
                sku_data.invoice_amount = vm.service.multi(sku_data.quantity, sku_data.price);
                vm.cal_percentage(sku_data);
                for(var i = 0; i < vm.model_data.data.length ; i++) {
                  if (vm.model_data.data[i]["sku_id"] == data.data.data.sku_code) {
                    vm.model_data.data[i]['cost_price'] = data.data.data.cost_price;
                  }
                }
              }
            } else {
              vm.service.showNoty(data.data.status);
            }
          }
        });
      }
    }
  }
  // Serial Based Scan Code Ends

}
angular
  .module('urbanApp')
  .controller('CreateAllocations', ['$scope', '$filter','$http', '$q', 'Session', 'colFilters', 'Service', '$state', '$window', '$timeout', 'Data', 'SweetAlert', CreateAllocations]);
