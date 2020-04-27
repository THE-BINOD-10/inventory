'use strict';

function Picklist($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, $modal, items, $rootScope) {

  var vm = this;
  vm.state_data = items;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  vm.user_type=Session.user_profile.user_type;
  vm.model_data = {};
  vm.record_serial_data = [];
  vm.record_serial_dict= {}
  vm.record_qcitems_data = [];
  vm.status_data = {message:"cancel", data:{}}
  vm.qty_validation = {};
  vm.serial_number_scanned = ''
  $rootScope.collect_imei_details = {}
  vm.collect_imei_details = $rootScope.collect_imei_details
  vm.passed_serial_number = {}
  vm.failed_serial_number = {}
  vm.collect_imei_data = {};
  vm.industry_type = Session.user_profile.industry_type;
  vm.get_id = '';
  vm.decimal_limit = (vm.permissions.decimal_limit)?Number(vm.permissions.decimal_limit):1;
  vm.quantity_focused = false;

  vm.getPoData = function(data){
    Service.apiCall(data.url, data.method, data.data, true).then(function(data){
      if(data.message) {
         angular.copy(data.data, vm.model_data);
         for(var i=0; i<vm.model_data.data.length; i++){
                    vm.model_data.data[i]['sub_data'] = [];
                    var value = (vm.permissions.scan_picklist_option != 'scan_none')? 0: vm.model_data.data[i].picked_quantity;
                    if(Session.user_profile.user_type == "marketplace_user") {
                      value = vm.model_data.data[i].picked_quantity;
                    }
                    vm.model_data.data[i]['sub_data'].push({zone: vm.model_data.data[i].zone,
                                                         location: vm.model_data.data[i].location,
                                                         orig_location: vm.model_data.data[i].location,
                                                         picked_quantity: value, scan: "", pallet_code:  vm.model_data.data[i].pallet_code,
                                                         capacity: vm.model_data.data[i].picked_quantity,
                                                         passed_serial_number: [],
                                                         failed_serial_number:[],
                                                         labels: [], last_pallet_code:vm.model_data.data[i].pallet_code,
                                                         last_location: vm.model_data.data[i].location});
         }

         //if(vm.state_data.page != "PullConfirmation") {

         //  view_orders();
         //} else {
           pull_confirmation();
           angular.copy(vm.model_data.sku_total_quantities ,vm.remain_quantity);
           vm.count_sku_quantity();
         //}
         vm.bt_disable = false;
         Service.pop_msg(data.data.stock_status);
       };
    });
  }

  vm.ok = function (msg) {
    if (msg) {
      vm.status_data.message = msg
    }
    $modalInstance.close(vm.status_data);
  };

  function update_decimal_val(field) {

    var temp_pick_qty = field.toString();
    if(temp_pick_qty.indexOf('.') != -1 ) {
      var temp_pick_qty = String(field).split('.');
      if(temp_pick_qty[1].length > vm.decimal_limit) {
        field = temp_pick_qty[0]+"."+temp_pick_qty[1].slice(0,vm.decimal_limit);
      }
    }
    return field;
  }



  vm.getPoData(vm.state_data);

  vm.get_current_weight = function(event, data, index, parent_index) {
    if(vm.permissions.weight_integration_name.length > 0) {
      vm.service.apiCall('get_current_weight/', 'GET',{}).then(function(res_data){
        if(res_data.message){
          if(res_data.data.status && res_data.data.is_updated){
            if(data[parent_index].reserved_quantity < res_data.data.weight)
             {
              vm.service.showNoty("Picked quntity is Greater Than Reserved Quantity");
              }
          else
          {
              data[parent_index]["sub_data"][index].picked_quantity = res_data.data.weight;
            }
          }
          if(vm.quantity_focused) {
            setTimeout(function(){ vm.get_current_weight(event, data, index, parent_index); }, 1000);
          }
        }
      });
    }
  }

  vm.check_sku_match = function(field){

    var exist = false;
    angular.forEach(vm.model_data.data, function(record){

      if(record.wms_code == field) {
        exist = true;
        return exist;
      }
    });
    return exist;
  }
/*
function view_orders() {

  vm.cal_quantity = cal_quantity;
  function cal_quantity(record, data) {

    console.log(record);

    if(!record.picked_quantity) {

      return false;
    }

    if (record.pallet_code && Number(record.picked_quantity) > record.capacity) {

      record.picked_quantity = record.capacity;
    }

    var total = 0;
    for(var i=0; i < data.sub_data.length; i++) {
        total = total + parseInt(data.sub_data[i].picked_quantity);
    }
    if(data.reserved_quantity >= total){
      console.log(record.picked_quantity)
    } else {
      var quantity = data.reserved_quantity-total;
      if(quantity < 0) {
        quantity = total - parseInt(record.picked_quantity);
        quantity = data.reserved_quantity - quantity;
        record.picked_quantity = quantity;
      } else {
        record.picked_quantity = quantity;
      }
    }
  }

  vm.update_data = function(index, data, last) {
    console.log(data);
    if (last) {
      var total = 0;
      for(var i=0; i < data.sub_data.length; i++) {
        total = total + parseInt(data.sub_data[i].picked_quantity);
      }
      if(total < data.reserved_quantity) {
        var clone = {};
        angular.copy(data.sub_data[index], clone);
        clone.picked_quantity = data.reserved_quantity - total;
        clone.scan = "";
        clone.pallet_code = "";
        data.sub_data.push(clone);
      }
    } else {
      data.sub_data.splice(index,1);
    }
  }

}
*/

    vm.getrecordSerialnumber = function(rowdata) {
      var record_serial_data = []
      vm.temp_imei_list = []
      for(var i=0; i < vm.model_data.data.length; i++) {
        if(vm.model_data.data[i].wms_code == rowdata.wms_code) {
          if(!vm.model_data.data[i].hasOwnProperty('sku_imeis_map')) {
            return false;
          }
          if(vm.model_data.data[i]['sku_imeis_map'].hasOwnProperty(vm.model_data.data[i].wms_code)) {
            angular.copy(vm.model_data.data[i]['sku_imeis_map'][vm.model_data.data[i].wms_code].sort(), record_serial_data);
            record_serial_data = [...new Set(record_serial_data)]
            vm.temp_imei_list = vm.remove_duplicate_imei_numbers(vm.model_data.data[i], record_serial_data)
            if(vm.temp_imei_list.length != 0){
              record_serial_data = vm.get_array_difference(record_serial_data, vm.temp_imei_list)
              vm.record_serial_dict[vm.model_data.data[i].wms_code] = record_serial_data
            } else {
              vm.record_serial_dict[vm.model_data.data[i].wms_code] = record_serial_data
            }
          }
          if(!vm.record_serial_dict.hasOwnProperty(vm.model_data.data[i].wms_code)) {
            vm.service.showNoty("No Serial Number Present");
            return false;
          }
          if(vm.model_data.data.length == i+1){
            vm.temp_imei_list = []
          }
        }
      }
      return true;
    }

    vm.myFunction = function(rowdata, record) {
      var record_serial_data = []
      vm.temp_imei_list = []
      for(var i=0; i < vm.model_data.data.length; i++) {
        if(vm.model_data.data[i].wms_code == rowdata.wms_code) {
          if(angular.copy(vm.model_data.data[i]['sku_imeis_map']).hasOwnProperty(vm.model_data.data[i].wms_code)) {
            angular.copy(vm.model_data.data[i]['sku_imeis_map'][vm.model_data.data[i].wms_code].sort(), record_serial_data);
            record_serial_data = [...new Set(record_serial_data)]
            vm.temp_imei_list = vm.remove_duplicate_imei_numbers(vm.model_data.data[i], record_serial_data)
            if(vm.temp_imei_list.length != 0){
              record_serial_data = vm.get_array_difference(record_serial_data, vm.temp_imei_list)
              vm.record_serial_dict[vm.model_data.data[i].wms_code] = record_serial_data
              vm.record_serial_data = $.map(vm.record_serial_data, function(n,i){return n.toUpperCase();});
            }else {
              vm.record_serial_dict[vm.model_data.data[i].wms_code] = record_serial_data
              vm.record_serial_data = $.map(vm.record_serial_data, function(n,i){return n.toUpperCase();});
            }
          }
          if(!vm.record_serial_dict.hasOwnProperty(vm.model_data.data[i].wms_code)) {
            vm.service.showNoty("No Serial Number Present");
            return false;
          }
          if(vm.model_data.data.length == i+1){
            vm.temp_imei_list = []
          }
        }
      }
    }
  vm.remove_duplicate_imei_numbers = function(rowdata, imei_list){
    if(rowdata.sub_data[0].passed_serial_number.length != 0){
      vm.temp_imei_list = (vm.temp_imei_list).concat(rowdata.sub_data[0].passed_serial_number)
    }
    if(rowdata.sub_data[0].failed_serial_number.length != 0){
      vm.temp_imei_list = (vm.temp_imei_list).concat(rowdata.sub_data[0].failed_serial_number)
    }
    return vm.temp_imei_list
  }
  vm.get_array_difference =function(arr1, arr2){
    return arr1.concat(arr2).filter(function (val) {
      if (!(arr1.includes(val) && arr2.includes(val)))
        return val;
    })
  }
  vm.serial_scan = function(event, scan, data, record) {
      if (event.keyCode == 13) {
        scan = scan.toUpperCase();
        record.scan = record.scan.toUpperCase();
        var resp_data = vm.getrecordSerialnumber(data);
        if (!resp_data) {
          vm.service.showNoty("Serial Number Not Available For this SKU");
          record.scan = '';
          return false
        }
		if(vm.collect_imei_data.hasOwnProperty(data.id)) {
			if ($.inArray(scan, vm.collect_imei_data[data.id]) != -1) {
				vm.service.showNoty("Serial Number Already Scanned");
				record.scan = '';
				return false
			}
		}
        vm.get_id = data.id
        var id = data.id;
        var total = 0;
        for(var i=0; i < data.sub_data.length; i++) {
          total = total + parseInt(data.sub_data[i].picked_quantity);
        }
        var scan_data = scan.split("\n");
        var length = scan_data.length;
        var elem = {};
        elem[id]= scan_data[length-1]
        if (!vm.permissions.dispatch_qc_check) {
          var resp_data = vm.getrecordSerialnumber(data);
          if (!resp_data) {
            vm.service.showNoty("Serial number not available for this SKU");
            record.scan = '';
            return false
          }
          if(vm.collect_imei_data.hasOwnProperty(data.id)) {
            if ($.inArray(scan, vm.collect_imei_data[data.id]) != -1) {
              vm.service.showNoty("Serial number already scanned");
              record.scan = '';
              return false
            }
          }
        } else {
          vm.serial_number_scanned = elem[id];
        }
        if(total < data.reserved_quantity) {
          vm.service.apiCall('check_imei/', 'GET', elem).then(function(data){
            if(data.data.status == "Success") {
              if(data.data.data.sku_code == record.wms_code) {
                if (vm.permissions.dispatch_qc_check) {
                  if(vm.record_serial_dict[data.data.data.sku_code].indexOf(scan_data[length-1]) > -1 || vm.permissions.allow_rejected_serials) {
                    if(!vm.permissions.allow_rejected_serials)
                    {
                     vm.picklist_qcitems(vm.model_data, record);
                    }
                    else{
                      vm.non_qc_increament(record);
                    }
                  } else {
                    vm.service.showNoty("Please Enter the Correct Serial Number !");
                    record.scan = '';
                  }
                } else {
                  vm.non_qc_increament(record);
                }
              } else {
                Service.pop_msg(data.data.status);
                scan_data.splice(length-1,1);
                record.scan = scan_data.join('\n');
                record.scan = record.scan+"\n";
                record.scan = '';
              }
            } else {
              Service.pop_msg(data.data.status);
              record.scan = '';
            }
          });
        } else {
          scan_data.splice(length-1,1);
          record.scan = scan_data.join('\n');
          record.scan = record.scan+"\n";
          vm.service.showNoty("picked already equal to reserved quantity !");
          record.scan = '';
        }
      }
    }

    vm.non_qc_increament = function (record) {
      record.scan = record.scan.toUpperCase()
      record.picked_quantity = parseInt(record.picked_quantity) + 1;
      vm.record_serial_data.shift()
      if(vm.collect_imei_data.hasOwnProperty(vm.get_id)) {
        vm.collect_imei_data[vm.get_id].push(record.scan)
      } else {
        vm.collect_imei_data[vm.get_id] = []
        vm.collect_imei_data[vm.get_id].push(record.scan)
      }
      $("input[name=imei_"+vm.get_id+"]").prop('value', String(vm.collect_imei_data[vm.get_id]))
      record.scan = '';
    }

    vm.qc_increament = function (record, result) {
      if (result == "pass") {
        record.picked_quantity = parseInt(record.picked_quantity) + 1;
        for(var i=0; i < vm.model_data.data.length; i++) {
          if (vm.model_data.data[i]['sku_imeis_map'].hasOwnProperty(record.wms_code)) {
            for( var j = 0; j < vm.model_data.data[i]['sku_imeis_map'][record.wms_code].length; j++){
              if ( vm.model_data.data[i]['sku_imeis_map'][record.wms_code][j] == record.scan) {
                vm.model_data.data[i]['sku_imeis_map'][record.wms_code].splice(j, 1);
                for (var k = 0; k < vm.record_serial_dict[record.wms_code].length; k++) {
                  if (vm.record_serial_dict[record.wms_code][k] == record.scan){
                    vm.record_serial_dict[record.wms_code].splice(k, 1);
                  }
                }
              }
            }
          }
        }
        if (vm.passed_serial_number.hasOwnProperty(record.wms_code)) {
          if(!vm.passed_serial_number[record.wms_code].includes(record.wms_code)) {
            vm.passed_serial_number[record.wms_code].push(record.scan)
            record.passed_serial_number.push(record.scan)
          }
        } else {
          vm.passed_serial_number[record.wms_code] = [record.scan]
          record.passed_serial_number.push(record.scan)
        }
        record.scan = '';
      } else {
        for(var i=0; i < vm.model_data.data.length; i++) {
          if (vm.model_data.data[i]['sku_imeis_map'].hasOwnProperty(record.wms_code)) {
            for( var j = 0; j < vm.model_data.data[i]['sku_imeis_map'][record.wms_code].length; j++){
              if ( vm.model_data.data[i]['sku_imeis_map'][record.wms_code][j] == record.scan) {
                vm.model_data.data[i]['sku_imeis_map'][record.wms_code].splice(j, 1);
                for (var k = 0; k < vm.record_serial_dict[record.wms_code].length; k++) {
                  if (vm.record_serial_dict[record.wms_code][k] == record.scan){
                    vm.record_serial_dict[record.wms_code].splice(k, 1);
                  }
                }
              }
            }
          }
        }
        if (vm.failed_serial_number.hasOwnProperty(record.wms_code)) {
          if(!vm.failed_serial_number[record.wms_code].includes(record.wms_code)) {
            vm.failed_serial_number[record.wms_code].push(record.scan)
            record.failed_serial_number.push(record.scan)
          }
        } else {
          vm.failed_serial_number[record.wms_code] = [record.scan]
          record.failed_serial_number.push(record.scan)
        }
        record.scan = '';
      }
    }

    vm.picklist_qcitems = function(items, val) {
    var mod_data =  vm.state_data
    vm.state_data['serial_number_scanned'] = vm.serial_number_scanned
    angular.copy(vm.model_data["qc_items"].sort(), vm.record_qcitems_data);
    var modalInstance = $modal.open({
      templateUrl: 'views/outbound/toggle/qcitems.html',
      controller: 'picklist_qcitems',
      controllerAs: 'pop',
      size: 'lg',
      backdrop: 'static',
      keyboard: false,
      resolve: {
        items: function () {
          return mod_data;
        }
      }
    });

    modalInstance.result.then(function (selectedItem) {
      if (selectedItem != 'close') {
        if ($.isEmptyObject(selectedItem)) {
          selectedItem = vm.state_data['collect_imei_details'][vm.state_data['serial_number_scanned']][1]
        }
        vm.qc_increament(val, selectedItem);
      } else {
        val.scan = ''
      }
    });
  }

    vm.isLast = isLast;
    function isLast(check) {
      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

  vm.print_excel = print_excel;
  function print_excel(id)  {
    vm.service.apiCall('print_picklist_excel/','GET',{data_id: id, 'display_order_id' : vm.display_order_id}).then(function(data){
      if(data.message) {
        window.location = Session.host+data.data.slice(3);
      }
    })
  }

  vm.print_pdf = print_pdf;
  function print_pdf(id) {
    vm.service.apiCall('print_picklist/','GET',{data_id: id, 'display_order_id' : vm.display_order_id}).then(function(data){
      if(data.message) {
        var picklist_number = $($.parseHTML(data.data)).find("input").val()
        if (picklist_number) {
            picklist_number = 'Picklist_'+picklist_number
        } else {
            picklist_number = Picklist
        }
        vm.service.print_data(data.data, picklist_number);
      }
    })
  }

    vm.pdf_data = {};
    vm.picklist_confirmation = picklist_confirmation;
    function picklist_confirmation() {
      vm.bt_disable = true;
      var elem_dict = {}
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      if (vm.permissions.dispatch_qc_check) {
        if (vm.state_data.hasOwnProperty("collect_imei_details")) {
          elem_dict = {'name':'imei_qc_details', 'value': JSON.stringify(vm.state_data.collect_imei_details)}
          elem.push(elem_dict)
        }
        if (!$.isEmptyObject(vm.passed_serial_number)) {
          elem_dict = {'name':'passed_serial_number', 'value': JSON.stringify(vm.passed_serial_number)}
          elem.push(elem_dict)
        }
        if (!$.isEmptyObject(vm.failed_serial_number)) {
          elem_dict = {'name':'failed_serial_number', 'value': JSON.stringify(vm.failed_serial_number)}
          elem.push(elem_dict)
        }
      }
      vm.service.apiCall('picklist_confirmation/', 'POST', elem, true).then(function(data) {
        if(data.message) {
          vm.qty_validation = {};
          if(data.data == "Picklist Confirmed") {
            vm.ok("done");
          } else if (data.data == 'Insufficient Stock in given location with batch number') {
            Service.showNoty(data.data);
            vm.ok('')
          } else if (data.data == 'Expiry batch number not Allowed'){
            Service.showNoty(data.data);
          } else if (typeof(data.data) == "string" && data.data.indexOf("print-invoice")) {
            vm.ok("html");
            vm.status_data.data = data.data;
          } else if (data.data.status == 'invoice') {

            vm.status_data.data = data.data.data;
            vm.ok("invoice");
          } else {

            if (!data.data.status) {
              vm.validate_skus = {};

              for (var i = 0; i < data.data.sku_codes.length; i++) {

                angular.forEach(data.data.sku_codes[i], function(value, key){

                  var temp_combo = {};
                  for(var j = 0; j < value.length; j++){

                    if (!temp_combo[value[j]]) {
                      temp_combo[value[j]] = value[j];
                    }
                  }

                  if(!vm.validate_skus[key]){

                    vm.validate_skus[key] = temp_combo;
                  }
                });
              }
              vm.qty_validation = {borderColor:'#ce402f'};
              vm.bt_disable = false;
            }
            // Service.pop_msg(data.data);
            Service.pop_msg(data.data.message);
          }
        }
      });
    }


function pull_confirmation() {

  vm.sku_scan = function(event, field) {

    var field = field;
    vm.service.scan(event, field).then(function(data){
      if(data) {
        var sku_brand = vm.model_data.data[0].sku_brand;
        vm.service.apiCall('check_sku/', 'GET',{'sku_code': field, 'sku_brand': sku_brand}).then(function(data){
          if(data.message) {
            if(typeof(data.data) == 'string') {
              alert(data.data);
              vm.model_data.scan_sku = "";
              return false;
            }
            field = data.data.sku_code;
            vm.model_data.scan_sku = field;

            if(vm.check_sku_match(field)) {
              if(vm.model_data.sku_total_quantities[field] <= vm.remain_quantity[field]) {
                alert("Reservered quantity equal to picked quantity");
                vm.model_data.scan_sku = "";
              } else {
                vm.incr_qty();
              }
            } else {
              alert("Invalid SKU");
              vm.model_data.scan_sku = "";
            }
          }
        })
      }
    });
  }



  //scan location and sku feature

  vm.update_data = update_data;
  function update_data(index, data, last) {
    console.log(data);
    var remain = vm.model_data.sku_total_quantities[data.wms_code] - vm.remain_quantity[data.wms_code];
    if (last) {
      if(!(vm.model_data.sku_total_quantities[data.wms_code] <= vm.remain_quantity[data.wms_code])){
        var total = 0;
        for(var i=0; i < data.sub_data.length; i++) {
          total = total + Number(data.sub_data[i].picked_quantity);
        }
        if(total && total < data.reserved_quantity) {
          var clone = {};
          angular.copy(data.sub_data[index], clone);
          var temp = data.reserved_quantity - total;
          temp = update_decimal_val(temp);
          clone.picked_quantity = (remain < temp)?remain:temp;
          //clone.picked_quantity = data.reserved_quantity - total;
          clone.picked_quantity = 0;
          clone.scan = "";
          clone.pallet_code = "";
          clone.location = "";
          if (vm.permissions.scan_picklist_option == 'scan_label') {
            clone.labels = [];
            clone.picked_quantity = 0;
            clone.capacity = 0;
          }
          data.sub_data.push(clone);
        } else if (total == data.reserved_quantity) {
          vm.service.showNoty("Please compare with Received and Picked Quantity");
        } else {
          vm.service.showNoty("Please pick the existing sku quantity first. If you want change another location");
        }
      }
    } else {
      data.sub_data.splice(index,1);
    }
    vm.count_sku_quantity();
  }

  vm.get_sku_details = function(record, item, index) {
    record.manufactured_date = item.manufactured_date
    record.mrp = item.mrp
    record.expiry_date = item.expiry_date
  }

  vm.cal_quantity = cal_quantity;
  function cal_quantity(record, data) {

    console.log(record);

    if (record.pallet_code && Number(record.picked_quantity) > record.capacity) {

      vm.remain_quantity[data.wms_code] = (vm.remain_quantity[data.wms_code] - Number(record.picked_quantity))  + record.capacity;
      record.picked_quantity = record.capacity;
    }

    var sku_qty = record.picked_quantity;
    var remain = vm.model_data.sku_total_quantities[data.wms_code] - vm.remain_quantity[data.wms_code]
    var total = 0;
    for(var i=0; i < data.sub_data.length; i++) {
        total = total + Number(data.sub_data[i].picked_quantity);
    }
    if(data.reserved_quantity >= total){
      console.log(record.picked_quantity);
      if(remain < 0) {
        vm.change_quantity(record, remain, sku_qty);
      }
    } else {
      var quantity = data.reserved_quantity-total;
      if(quantity < 0) {
        quantity = total - Number(record.picked_quantity);
        quantity = data.reserved_quantity - quantity;
        record.picked_quantity = quantity;
      } else {
        record.picked_quantity = quantity;
      }
      vm.change_quantity(record, remain, sku_qty)
    }
    vm.count_sku_quantity();
  }

  vm.change_quantity = function(sku, remain, sku_qty){
    console.log(vm);
    console.log(remain);
    var temp = sku.picked_quantity;
    if(remain == 0) {
      sku.picked_quantity = 0;
      console.log(sku.quantity);
    } else if(remain < 0) {
      sku.picked_quantity = Number(sku_qty) + remain;
    }
    if(Number(temp) < sku.picked_quantity) {
      sku.picked_quantity = temp;
    }
    sku.picked_quantity = update_decimal_val(sku.picked_quantity);
//    var temp_pick_qty = String(sku.picked_quantity).split('.');
//    if(temp_pick_qty[1].length > vm.decimal_limit) {
//      sku.picked_quantity = temp_pick_qty[0]+"."+temp_pick_qty[1].slice(0,vm.decimal_limit);
//    }
  }

  vm.check_location = function(event, field) {

    var field = field;
    vm.service.scan(event, field).then(function(data){
      if(data) {
          if(vm.check_match(field)) {
            console.log(field);
            $("textarea[attr-name='sku']").focus();
            vm.suggest_sku();
          } else {
            vm.service.apiCall("get_stock_location_quantity/", "GET", {location: field})
            .then(function(data){
              if(data.data.message == "Invalid Location"){
                alert("Invalid Location");
                vm.model_data.scan_location = "";
              } else {
                $("textarea[attr-name='sku']").focus();
                vm.suggest_sku();
              }
            })
          }
      }
    })
  }

  vm.current_data = [];
  vm.check_sku = function(event, field) {

    /*if(vm.state_data.page != "PullConfirmation") {
      return false;
    }*/

    var field = field;
    vm.service.scan(event, field).then(function(data){
      if(data) {
        if(vm.model_data.scan_location) {
          var sku_brand = vm.model_data.data[0].sku_brand;
          vm.service.apiCall('check_sku/', 'GET',{'sku_code': field, 'sku_brand': sku_brand}).then(function(data){
            if(data.message) {
              if(typeof(data.data) == 'string') {
                alert(data.data);
                vm.model_data.scan_sku = "";
                return false;
              }
              field = data.data.sku_code;
              vm.model_data.scan_sku = field;

              if(vm.check_sku_match(field)) {
                if(vm.model_data.sku_total_quantities[field] <= vm.remain_quantity[field]) {
                  alert("Reservered quantity equal to picked quantity")
                  vm.model_data.scan_sku = "";
                  return false;
                } else {
                  if (vm.check_comb()) {
                    vm.incr_qty();
                  } else {
                    vm.service.apiCall("get_stock_location_quantity/", "GET", {location: vm.model_data.scan_location, wms_code: field})
                    .then(function(data){
                      if(data.data.message == "Invalid Location"){
                        alert("Invalid Location");
                        vm.model_data.scan_sku = "";
                        return false;
                      } else if(data.data.stock == 0) {
                        alert("Zero Stock");
                        vm.model_data.scan_sku = "";
                        return false;
                      } else {
                        var required = vm.model_data.sku_total_quantities[field] - vm.remain_quantity[field];
                        var temp_reserve = (data.data.stock < required)? data.data.stock: required;
                        vm.model_data.data.push({image: "",order_id: "", reserved_quantity: temp_reserve, wms_code: field, sub_data:[{location: vm.model_data.scan_location, picked_quantity: 1, new: true}]})
                        vm.count_sku_quantity();
                        vm.model_data.scan_sku = "";
                      }
                    })
                  }
                }
              } else {
                alert("Invalid SKU");
                vm.model_data.scan_sku = "";
                return false;
              }
            }
          })
        } else {
          alert("Please Enter location first");
          vm.model_data.scan_sku = "";
          $("textarea[attr-name='location']").focus();
        }
      }
    });
  }

  vm.incr_qty = function() {
    var sku = vm.model_data.scan_sku;
    var location = vm.model_data.scan_location;
    var status = false;
    for(var i=0; i < vm.model_data.data.length; i++) {

      if(vm.model_data.data[i].wms_code == sku) {
        if(vm.increase(vm.model_data.data[i])) {
          status = false;
          break;
        } else {
          status = true;
        }
      }
    }
    if(status) {
      alert("Reserved quantity equal to picked quantity");
      vm.model_data.scan_sku = "";
    }
  }

  vm.increase = function(data) {

    var sku = vm.model_data.scan_sku;
    var location = vm.model_data.scan_location;
    var total = 0;
    angular.forEach(data.sub_data, function(record){
      total = total + Number(record.picked_quantity);
    })
    var status = false
    if(data.reserved_quantity > total) {
      for(var i = 0; i < data.sub_data.length; i++) {

        if(data.sub_data[i].location == location || vm.permissions.scan_picklist_option == 'scan_sku') {

          data.sub_data[i].picked_quantity = Number(data.sub_data[i].picked_quantity) + 1;
          vm.model_data.scan_sku = "";
          status = true;
          vm.count_sku_quantity();
          break;
        }
      }
    }
    vm.model_data.scan_sku = "";
    return status;
  }

  vm.check_comb = function() {

    var exist = false;
    angular.forEach(vm.model_data.data, function(record){

      if(record.wms_code == vm.model_data.scan_sku) {
        angular.forEach(record.sub_data, function(record1){
          if(record1.location == vm.model_data.scan_location) {
            exist = true;
            return exist;
          }
        });
      }
    });
    return exist;
  }

  vm.check_match = function(field){

    var exist = false;
    angular.forEach(vm.model_data.data, function(record){

      angular.forEach(record.sub_data, function(record1){

        if(record1.location == field) {
          exist = true;
          return exist;
        }
      });
    });
    return exist;
  }

  vm.remain_quantity = {}
  vm.count_sku_quantity = function() {

    angular.forEach(vm.remain_quantity, function(value, key) {

      vm.remain_quantity[key] = 0;
    })
    angular.forEach(vm.model_data.data, function(record){
      var temp = 0;
      angular.forEach(record.sub_data, function(record1){

        temp = temp + Number(record1.picked_quantity);
      })
      vm.remain_quantity[record.wms_code] = temp + vm.remain_quantity[record.wms_code];
    })
    vm.suggest_sku();
  }

  vm.sug_sku = "";
  vm.suggest_sku = function() {
    var location = vm.model_data.scan_location;
    var status = false;
    for(var i = 0 ; i < vm.model_data.data.length ; i++) {
      var temp = vm.model_data.data[i];
      if(vm.model_data.sku_total_quantities[temp.wms_code] > vm.remain_quantity[temp.wms_code]){
        for(var j = 0 ; j < temp.sub_data.length ; j++) {
          var temp1 = temp.sub_data[j];
          if(temp1.location == location && temp.reserved_quantity > vm.get_total(temp.sub_data)) {
            vm.sug_sku = temp.wms_code;
            status = true;
            break;
          } else {
            vm.sug_sku = "";
          }
        }
      } else {
        vm.sug_sku = "";
      }
      if(status) {
        break;
      }
    }
  }

  vm.get_total = function(data) {
    var total = 0;
    angular.forEach(data, function(record){
      total = total + Number(record.picked_quantity);
    })
    return total;
  }
}

   vm.cancel_picklist = function(pick_id) {
    swal({
      title: "Do you want to process these orders later!",
      text: "Are you sure?",
      type: "warning",
      showCancelButton: true,
      confirmButtonColor: "#DD6B55",
      confirmButtonText: "Yes",
      cancelButtonText: "No",
      closeOnConfirm: true,
      closeOnCancel: false
    },
    function(isConfirm){
      if (isConfirm) {
        vm.service.apiCall('picklist_delete/','GET',{key: 'process', picklist_id: pick_id}, true).then(function(data){
          if (data.message) {
             vm.ok("done");
          }
        });
      }
    else {
      swal({
          title: "Do you want to delete this Picklist!",
          text: "Are you sure?",
          type: "warning",
          showCancelButton: true,
          confirmButtonColor: "#DD6B55",
          confirmButtonText: "Yes",
          cancelButtonText: "No",
          closeOnConfirm: false,
          closeOnCancel: true
       },
       function(isConfirm){
         if (isConfirm) {
           vm.service.apiCall('picklist_delete/','GET', {key: 'delete', picklist_id: pick_id}, true).then(function(data){
                swal("", data.data, "success");
           });
           vm.ok("done");
         }
         else {
           vm.ok("done");
         }
       });
    }
   });
  }

  /*
  vm.update_picklist = function(pick_id) {

    vm.service.apiCall('update_picklist_loc/','GET',{picklist_id: pick_id}, true).then(function(data){
      if (data.message) {
        vm.getPoData(vm.state_data);
      }
    });
  }
  */
  vm.deliveryChallan = function(){
    vm.bt_disable = true;
    let formdata = angular.element($('form'));
    formdata = formdata[0];
    formdata = $(formdata).serializeArray();
    vm.service.apiCall('generate_picklist_dc/', 'POST', formdata, true).then(function(data){
      if(data.message) {
        vm.pdf_data = data.data;
        vm.DeliveryChallanPopup(vm.pdf_data)
      }
      vm.bt_disable = false;
    });
  }
  vm.DeliveryChallanPopup = function(pdfdata) {
    var mod_data = pdfdata
    var modalInstance = $modal.open({
      templateUrl: 'views/outbound/toggle/empty_dc_invoice.html',
      controller: 'deliveryChallanPopUP',
      controllerAs: 'pop',
      size: 'lg',
      backdrop: 'static',
      keyboard: false,
      resolve: {
        items: function () {
          return mod_data;
        }
      }
    });
  }
  vm.update_picklist = function(pick_id) {
    vm.service.apiCall('update_picklist_loc/','GET',{picklist_id: pick_id}, true).then(function(data){
      if (data.message) {
        vm.service.apiCall('view_picklist/', 'GET' , {data_id: pick_id}, true).then(function(data){
                if(data.message) {
                  angular.copy(data.data, vm.model_data);
                  for(var i=0; i<vm.model_data.data.length; i++){
                    vm.model_data.data[i]['sub_data'] = [];
                    var value = (vm.permissions.scan_picklist_option != 'scan_none')? 0: vm.model_data.data[i].picked_quantity;
                    var temp = {zone: vm.model_data.data[i].zone,
                                location: vm.model_data.data[i].location,
                                orig_location: vm.model_data.data[i].location,
                                passed_serial_number: [],failed_serial_number:[],
                                picked_quantity: value, new: false}
                    if(Session.user_profile.user_type == "marketplace_user") {
                      temp["picked_quantity"] = vm.model_data.data[i].picked_quantity;
                    }
                    vm.model_data.data[i]['sub_data'].push(temp);
                  }
                  angular.copy(vm.model_data.sku_total_quantities ,vm.remain_quantity);
                  vm.count_sku_quantity();
                }
        });
      }
    });
  }


  //pallet feature

  vm.checkPallet = function(index, sku_data) {

    var status = false;
    for(var i = 0; i < sku_data.sub_data.length; i++) {

      if(sku_data.sub_data[i].pallet_code.toLowerCase() == sku_data.sub_data[index].pallet_code.toLowerCase() && i != index) {

        status = true;
        break;
      }
    }
    return status;
  }

  vm.checkCapacity = function(index, sku_data, from, element) {

    console.log(vm.model_data);
    element.preventDefault();
    var row_data = sku_data.sub_data[index];
    if (row_data.last_location == row_data.location && row_data.last_pallet_code == row_data.pallet_code) {
       return false;
    } else {
      row_data.last_location = row_data.location;
      row_data.last_pallet_code = row_data.pallet_code;
      if(row_data.labels.length > 0) {
        row_data.labels = [];
        row_data.picked_quantity = 0;
        vm.service.showNoty("Labels cleared")
      }
    }
    if (from == "location") {

      if(row_data.location == 'NO STOCK') {

        return false;
      } else if(!row_data.location) {

        vm.service.showNoty("Please Fill Location");
        row_data.picked_quantity = 0;
        return false;
      }
    } else if (from == "pallet_code"){
      if (!row_data.location) {

        vm.service.showNoty("Please Fill Location");
        row_data.picked_quantity = 0;
        return false;
      } else if (!row_data.pallet_code) {

        vm.service.showNoty("Please Fill Pallet Code");
        row_data.picked_quantity = 0;
        return false;
      } else if(vm.checkPallet(index, sku_data) && row_data.pallet_code) {

        row_data.pallet_code = "";
        vm.service.showNoty("Already Pallet Code Exist");
        return false;
      }
    }

    var send = {sku_code: sku_data.wms_code, location: row_data.location, pallet_code: row_data.pallet_code}

    vm.service.apiCall("get_sku_stock_check/", "GET", send).then(function(data){

      if(data.message) {

        if(data.data.status == 0) {

          vm.service.showNoty(data.data.message);

          if(data.data.message== "Invalid Location") {

            row_data.location = "";
            angular.element(element.target).focus();
          } else if (data.data.message == "Invalid Location and Pallet code Combination") {

            row_data.pallet_code = "";
            angular.element(element.target).focus();
          }
          row_data.picked_quantity = 0;
          row_data.labels = [];
        } else {

          var data = data.data.data;
          data = Object.values(data)[0];
          row_data["capacity"] = Number(data.total_quantity);

          if(Number(row_data.picked_quantity) > Number(data.total_quantity)) {

            row_data.picked_quantity = Number(data.total_quantity);
          } else {

            if (vm.permissions.scan_picklist_option == 'scan_sku_location' || vm.permissions.scan_picklist_option == 'scan_sku') {
              var total = 0;
              row_data.picked_quantity = 0;
              angular.forEach(sku_data.sub_data, function(record) {

                total += Number(record.picked_quantity);
              })

              if (sku_data.reserved_quantity > total) {

                row_data.picked_quantity = sku_data.reserved_quantity - total;
              } else {

                row_data.picked_quantity = 0;
              }

              if (row_data.picked_quantity > row_data.capacity) {

                row_data.picked_quantity = row_data.capacity;
              }
            } else {
              row_data.picked_quantity = 0;
            }
          }
        }
      }
    })
  }

  vm.print_barcodes = function(picklist_id) {

    var mod_data = {id: picklist_id}
    var modalInstance = $modal.open({
      templateUrl: 'views/outbound/toggle/barcodes.html',
      controller: 'Barcodes',
      controllerAs: 'pop',
      size: 'lg',
      backdrop: 'static',
      keyboard: false,
      resolve: {
        items: function () {
          return mod_data;
        }
      }
    });

    modalInstance.result.then(function (selectedItem) {
      console.log(selectedItem);
    });
  }

  vm.label_scan = function(event, field) {

    var field = field;
    vm.service.scan(event, field).then(function(data){
      if(data) {
        vm.model_data.scan_label = "";
        var send = {label: field, picklist_number: vm.model_data.picklist_id};
        vm.service.apiCall('check_labels/', 'GET', send).then(function(data){
          if(data.message) {
            if (data.data.message != "Success") {
              vm.service.showNoty(data.data.message);
              return false;
            }
            var sku_code = data.data.data.sku_code;
            var order_id = data.data.data.order_id;

            if(vm.count_sku_quantity[sku_code] >= vm.model_data.sku_total_quantities[sku_code]) {
              vm.service.showNoty("Picked Quantity Already Equal to Reserved Quantity");
              return false;
            }
            var p1 = null;
            var p2 = null;
            for(var i=0; i<vm.model_data.data.length; i++) {
              for(var j=0; j<vm.model_data.data[i].sub_data.length; j++) {
                var temp = vm.model_data.data[i];
                var temp_sub = vm.model_data.data[i].sub_data[j];
                if(temp_sub.labels.indexOf(field) > -1) {
                  vm.service.showNoty("Label Already Scanned");
                  return false;
                }
                if (p1 != null) {
                  continue;
                }
                if(vm.model_data.order_status == 'open') {
                  if(temp.wms_code == sku_code && temp.order_no == order_id) {
                    if(temp_sub.capacity <= Number(temp_sub.picked_quantity)) {
                      p1 = null; p2 = null;
                    } else if(Number(temp.reserved_quantity) > Number(temp_sub.picked_quantity)) {
                      p1 = i; p2 = j;
                    }
                  }
                } else {
                  if(temp.wms_code == sku_code) {
                    if(temp_sub.capacity <= Number(temp_sub.picked_quantity)) {
                      p1 = null; p2 = null;
                    } else if(Number(temp.reserved_quantity) > Number(temp_sub.picked_quantity)) {
                      p1 = i; p2 = j;
                    }
                  }
                }
              }
            }
            if (p1 != null) {
              vm.model_data.data[p1].sub_data[p2].labels.push(field);
              vm.model_data.data[p1].sub_data[p2].picked_quantity = Number(vm.model_data.data[p1].sub_data[p2].picked_quantity) + 1;
              vm.count_sku_quantity();
            }
          }
        })
      }
    });
  }

}

angular
  .module('urbanApp')
  .controller('Picklist', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', '$modal', 'items', '$rootScope', Picklist]);

/*
function Barcodes($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {

  var vm = this;
  vm.service = Service;

  var url_get = "get_order_labels/";
  vm.model_data = {};

  vm.getPoData = function(data){

    var send = {picklist_number: data.id}
    Service.apiCall(url_get, "GET", send, true).then(function(data){
      if(data.message) {
        angular.copy(data.data.data, vm.model_data.barcodes)
        if (data.data.data.length == 0) {

          Service.showNoty("No labels are there")
        }
      };
    });
  }

  vm.getPoData(items);

  vm.barcode_title = 'Barcode Generation';

  vm.model_data['format_types'] = ['format1', 'format2', 'format3']

  var key_obj = {'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details'}

  vm.model_data['barcodes'] = [{'sku_code':'', 'quantity':''}];

  vm.ok = function (msg) {
    $modalInstance.close(vm.status_data);
  };

  vm.generate_barcodes = function(form) {
    if(form.$valid) {
      var elem = $("form[name='barcodes']").serializeArray();
      vm.service.apiCall('generate_barcodes/', 'POST', elem, true).then(function(data){
        if(data.message) {
          console.log(data);
          var href_url = data.data;

          var downloadpdf = $('<a id="downloadpdf" target="_blank" href='+href_url+' >');
          $('body').append(downloadpdf);
          document.getElementById("downloadpdf").click();
          $("#downloadpdf").remove();
        }
      })
    }
  }
}

angular
  .module('urbanApp')
  .controller('Barcodes', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', Barcodes]);*/
  function picklist_qcitems($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $q, $modalInstance, items, $rootScope) {

  var vm = this;
  vm.state_data = items;
  vm.service = Service;
  vm.input_types = ['Input', 'Number', 'Textarea'];
  vm.empty_data = {'id': '', 'attribute_name': '', 'attribute_type': 'Input'}
  vm.model_data = {};
  vm.record_qcitems_data = [];
  vm.sku_details = {};
  vm.pop_data = {};
  vm.status_data = "";
  vm.status_data = [];
  vm.getPoData = function(data){
    Service.apiCall(data.url, data.method, data.data, true).then(function(data){
      if(data.message) {
        angular.copy(data.data, vm.model_data);
        for(var i=0; i < vm.model_data["qc_items"].length; i++) {
          var keyvalue = vm.model_data["qc_items"][i];
          var key = vm.model_data["qc_items"][i].replace(/[" "]/g, '_').toLowerCase();
          vm.record_qcitems_data.push({[key] : vm.model_data["qc_items"][i]})
          vm.sku_details[vm.model_data["qc_items"][i]] = {'status': true, 'comment': ""}
        }
      }
    });
  }
  vm.getPoData(vm.state_data);
  vm.qcitemstatus = function (keys, values){
    for(var i=0; i < Object.keys(vm.sku_details).length; i++) {
      if(Object.keys(vm.sku_details)[i] == values) {
        if(vm.sku_details[values].status == true) {
          vm.sku_details[values].status = false
        } else {
          vm.sku_details[values].status = true
        }
      }
    }
    console.log(vm.sku_details[values].status);
    console.log(vm.sku_details);
  }
  vm.passdata = function() {
    vm.checkboxes = false;
    vm.totalData("pass");
  }
  vm.canceldata = function(keys){
    vm.checkboxes = true;
    if(keys == 'true') {
      vm.totalData("fail");
    } else {
      vm.totalData("");
    }
  }
  vm.totalData = function(key){
    if(key == "pass") {
      vm.sku_details['validation_status'] = {'status': key}
    } else {
      vm.sku_details['validation_status'] = {'status': key}
    }
  }

  vm.totalData("")

  vm.submitData = function() {
    var submit_data = []
    var validation_status = ''
    angular.forEach(vm.sku_details, function(key, obj) {
      var dict = {}
      if (String(obj) == "validation_status") {
        validation_status = String(key['status'])
      } else {
        dict[String(obj)] = [String(key['comment']), String(key['status'])]
        submit_data.push(dict)
      }
    })
    if (!validation_status) {
      vm.service.showNoty("Choose Pass/Fail");
      return false;
    }
    var elem = {
      'sku_details':JSON.stringify(submit_data),
      'imei_number':vm.state_data.serial_number_scanned,
      'validation_status':validation_status
    }
    $rootScope.collect_imei_details[vm.state_data.serial_number_scanned] = [JSON.stringify(submit_data), validation_status]
    vm.state_data.collect_imei_details = $rootScope.collect_imei_details
    vm.service.showNoty("success");
    $modalInstance.close(vm.status_data);
  }

  vm.ok = function (msg) {
    $modalInstance.close('close');
  };
}

angular
  .module('urbanApp')
  .controller('picklist_qcitems', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$q', '$modalInstance', 'items', '$rootScope', picklist_qcitems]);

function deliveryChallanPopUP($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $q, $modalInstance, items) {

  var vm = this;
  vm.service = Service;
  vm.pdf_data = items
  console.log($modalInstance)
  vm.permissions = Session.roles.permissions;
    $timeout(function () {
      $("#dc_pdf").html(vm.pdf_data)
    },500);
  vm.ok = function (msg) {
    $modalInstance.close(vm.status_data);
  };
}

angular
  .module('urbanApp')
  .controller('deliveryChallanPopUP', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$q', '$modalInstance', 'items', deliveryChallanPopUP]);
