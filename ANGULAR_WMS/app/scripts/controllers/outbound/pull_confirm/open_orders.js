'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('OpenOrders',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $modal) {
    var vm = this;

    vm.picklist_order = {};
    vm.permissions = Session.roles.permissions;
    vm.industry_type = Session.user_profile.industry_type;
    vm.user_type=Session.user_profile.user_type;
    vm.show_client_details = vm.permissions.create_order_po;
    vm.service = Service;
    vm.merge_invoice = false;
    vm.special_key = {status: 'open'};
    vm.tb_data = {};
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'OpenOrders', 'special_key':JSON.stringify(vm.special_key)},
              xhrFields: {
                withCredentials: true
              },
              complete: function(jqXHR, textStatus) {
                $scope.$apply(function(){
                  angular.copy(JSON.parse(jqXHR.responseText), vm.tb_data)
                })
              }
           })
       .withDataProp('data')
       .withOption('order', [1, 'desc'])
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback)
       .withOption('createdRow', function(row, data, dataIndex) {
            $compile(angular.element(row).contents())($scope);
        });

    vm.dtColumns = [
        DTColumnBuilder.newColumn('picklist_id').withTitle('Picklist ID'),
        DTColumnBuilder.newColumn('customer').withTitle('Customer / Marketplace').notSortable(),
        DTColumnBuilder.newColumn('picklist_note').withTitle('Picklist Note'),
        DTColumnBuilder.newColumn('reserved_quantity').withTitle('Reserved Quantity').notSortable(),
        DTColumnBuilder.newColumn('shipment_date').withTitle('Exp Delivery Date'),
        DTColumnBuilder.newColumn('date').withTitle('Date'),
        DTColumnBuilder.newColumn('id').withTitle('').notSortable().withOption('width', '35px').renderWith(actionsHtml)
    ];

    vm.order_charges = [];

    vm.default_charge = function() {
      if (vm.order_charges.length == 1) {
        vm.flag = true;
      }
    }

    vm.delete_charge = function(id) {
      if (id) {
        vm.service.apiCall("delete_order_charges?id="+id, "GET").then(function(data){
          if(data.message){
            Service.showNoty(data.data.message);
          }
        });
      }
    }

    vm.save_order_charges = function(order_id, $event) {
      var data_params = {};
      data_params['order_id'] = order_id;
      data_params['order_charges'] = JSON.stringify(vm.order_charges);
      angular.forEach(vm.order_charges, function(obj) {
        if($.isEmptyObject(obj['charge_name'])) {
          colFilters.showNoty('Charge Name cannot be Empty');
          $event.preventDefault();
        }
        if($.isEmptyObject(String(obj['charge_amount']))) {
          colFilters.showNoty('Charge Amount cannot be Empty');
          $event.preventDefault();
        }
      })
      vm.service.apiCall('add_order_charges/', 'POST', data_params).then(function(data) {
        vm.reloadData();
        colFilters.showNoty('Saved sucessfully');
      })
    }

    function actionsHtml(data, type, full, meta) {

      if (full.picklist_note == 'Auto-generated Picklist') {

        vm.picklist_order[full.id] = full;

        return '<a href="" style="text-decoration: underline; color: #33cc66; " ng-click="showCase.show_order_details(showCase.picklist_order['+ full.id +'], showCase.size)">' +
               '   Details' +
               '</a>';
      } else {
        return '';
      }
    }

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td:not(td:last)', nRow).unbind('click');
        $('td:not(td:last)', nRow).bind('click', function() {
            $scope.$apply(function() {

  var data = {data_id: aData.DT_RowAttr["data-id"]};

  var mod_data = {data: data};
  mod_data['url'] = "view_picklist/";
  mod_data['method'] = "GET";
  mod_data['page'] = "PullConfirmation";

  $scope.open = function (size) {

    var modalInstance = $modal.open({
      templateUrl: 'views/outbound/toggle/common_picklist.html',
      controller: 'Picklist',
      controllerAs: 'pop',
      size: size,
      backdrop: 'static',
      keyboard: false,
      resolve: {
        items: function () {
          return mod_data;
        }
      }
    });

    modalInstance.result.then(function (selectedItem) {
       var data = selectedItem;
       reloadData();
       if (data.message == 'invoice') {

         //angular.copy(data.data, vm.pdf_data);
         vm.pdf_data = data.data;
         if (Session.user_profile['user_type'] == 'marketplace_user') {
           $state.go('app.outbound.PullConfirmation.InvoiceM');
         } else if (vm.pdf_data.detailed_invoice) {
           $state.go('app.outbound.PullConfirmation.DetailGenerateInvoice');
         } else {
           $state.go('app.outbound.PullConfirmation.GenerateInvoice');
         }
       } else if (data.message == 'html') {
         $state.go("app.outbound.PullConfirmation.InvoiceE");
         $timeout(function () {
           $(".modal-body:visible").html(data.data)
         }, 3000);
       }

    }, function () {
      $log.info('Modal dismissed at: ' + new Date());
    });
  };
  $scope.open('lg');
                /*
              vm.service.apiCall('view_picklist/', 'GET' , {data_id: aData.DT_RowAttr["data-id"]}).then(function(data){
                if(data.message) {
                  angular.copy(data.data, vm.model_data);
                  for(var i=0; i<vm.model_data.data.length; i++){
                    vm.model_data.data[i]['sub_data'] = [];
                    var value = (vm.permissions.use_imei)? 0: vm.model_data.data[i].picked_quantity;
                    var temp = {zone: vm.model_data.data[i].zone,
                                location: vm.model_data.data[i].location,
                                orig_location: vm.model_data.data[i].location,
                                picked_quantity: value, new: false}
                    if(Session.user_profile.user_type == "marketplace_user") {
                      temp["picked_quantity"] = vm.model_data.data[i].picked_quantity;
                    }
                    vm.model_data.data[i]['sub_data'].push(temp);
                  }
                  angular.copy(vm.model_data.sku_total_quantities ,vm.remain_quantity);
                  vm.count_sku_quantity();
                  $state.go('app.outbound.PullConfirmation.Open');
                  $timeout(function () {
                    $("textarea[attr-name='location']").focus();
                  }, 1000);
                }
              });*/
            });
        });
        return nRow;
    } 

    vm.show_order_details = function(data){

      if (data.picklist_note == 'Auto-generated Picklist') {

        $state.go('app.outbound.PullConfirmation.OrderDetails');

        var params = {id: data.od_id, order_id: data.od_order_id};

        vm.service.apiCall('get_view_order_details/', "GET", params).then(function(data){

          var all_order_details = data.data.data_dict[0].ord_data;
          vm.ord_status = data.data.data_dict[0].status;

          vm.model_data = {}
          var empty_data = {data: []}
          angular.copy(empty_data, vm.model_data);

          vm.input_status = true;

          vm.order_input_status = false;

          vm.model_data["central_remarks"]= data.data.data_dict[0].central_remarks;
          vm.model_data["all_status"] = data.data.data_dict[0].all_status;
          vm.model_data["seller_data"] = data.data.data_dict[0].seller_details;
          angular.forEach(all_order_details, function(value, key){

          vm.customer_id = value.cust_id;
          vm.customer_name = value.cust_name;
          vm.phone = value.phone;
          vm.email = value.email;
          vm.address = value.address;
          vm.city = value.city;
          vm.state = value.state;
          vm.order_id_code = value.order_id_code;
          vm.pin = value.pin;
          vm.product_title = value.product_title;
          vm.quantity = value.quantity;
          vm.invoice_amount = value.invoice_amount;
          vm.shipment_date = value.shipment_date;
          vm.remarks = value.remarks;
          vm.cust_data = value.cus_data;
          vm.item_code = value.item_code;
          vm.order_id = value.order_id;
          vm.market_place = value.market_place;
          vm.order_charges = value.order_charges;
          vm.client_name = value.client_name;
          if (!vm.client_name) {
            vm.show_client_details = false;
          }
          var image_url = value.image_url;
          vm.img_url = vm.service.check_image_url(image_url);
          /*var custom_data = value.customization_data;
          vm.market_place = value.market_place;
          if (custom_data.length === 0){

            vm.customization_data = '';
          }
          else {

            var img_url = custom_data[0][3];
            vm.img_url = vm.service.check_image_url(img_url)
          }*/
            console.log(vm.model_data);
            vm.model_data.data.push({item_code: vm.item_code, product_title: vm.product_title, quantity: vm.quantity, unit_price: value.unit_price,
            invoice_amount: vm.invoice_amount, image_url: vm.img_url, remarks: vm.remarks, default_status: true, sku_status: true})
          });
        });
      }
    }

    vm.back_button = function() {
      vm.reloadData();
      $state.go('app.outbound.PullConfirmation')
    }

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        $('.custom-table').DataTable().draw();
    };

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    vm.model_data = {};

    vm.close = close;
    function close() {
      vm.scan_data = { suggested_sku: [""], suggest_sku: 0 , locations:[]};
      vm.unique_combination = [];
      vm.sug_loc = "";
      vm.sug_sku = "";
      vm.merge_invoice = false;
      $state.go('app.outbound.PullConfirmation');
    }

    vm.pdf_data = {};
    vm.picklist_confirmation = picklist_confirmation;
    function picklist_confirmation() {
      var elem = angular.element($('form'));
        elem = elem[0];
        elem = $(elem).serializeArray();
        vm.service.apiCall('picklist_confirmation/', 'POST', elem, true).then(function(data){
          if(data.message) {
            if(data.data == "Picklist Confirmed") {
              reloadData();
              vm.close();
            } else if (data.data.status == 'invoice') {

              reloadData();
              angular.copy(data.data.data, vm.pdf_data);
              if (vm.pdf_data.detailed_invoice) {
                $state.go('app.outbound.PullConfirmation.DetailGenerateInvoice');
              } else {
                $state.go('app.outbound.PullConfirmation.GenerateInvoice');
              }
            } else {
              pop_msg(data.data);
            }
          }
        });
    }

    vm.serial_scan = function(event, scan, data, record) {
      if ( event.keyCode == 13) {
        var id = data.id;
        var total = 0;
        for(var i=0; i < data.sub_data.length; i++) {
          total = total + Number(data.sub_data[i].picked_quantity);
        }
        scan = scan.toUpperCase();
        var scan_data = scan.split("\n");
        var length = scan_data.length;
        var elem = {};
        elem[id]= scan_data[length-1]
        if(total < data.reserved_quantity) {
          vm.service.apiCall('check_imei/', 'GET', elem).then(function(data){
            if(data.message) {
              if(data.data == "") {
                record.picked_quantity = Number(record.picked_quantity) + 1;
              } else {
                pop_msg(data.data);
                scan_data.splice(length-1,1);
                record.scan = scan_data.join('\n');
                record.scan = record.scan+"\n";
              }
            }
          });
        } else {
          scan_data.splice(length-1,1);
          record.scan = scan_data.join('\n');
          record.scan = record.scan+"\n";
          pop_msg("picked already equal to reserved quantity");
        }
      }
    }
  
  function pop_msg(msg) {
    vm.message = msg;
    $timeout(function () {
        vm.message = "";
    }, 2000);
    reloadData();
  }

  vm.print_excel = print_excel;
  function print_excel(id)  {
    vm.service.apiCall('print_picklist_excel/','GET',{data_id: id}).then(function(data){
      if(data.message) {
        window.location = Session.host+data.data.slice(3);
      }
    })
  }

  vm.print_pdf = print_pdf;
  function print_pdf(id) {
    vm.service.apiCall('print_picklist/','GET',{data_id: id}).then(function(data){
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
            $state.go('app.outbound.PullConfirmation');
            reloadData();
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
                swal("Deleted!", "picklist is deleted", "success");
           });
           $state.go('app.outbound.PullConfirmation');
           reloadData();
         }
         else {
           $state.go('app.outbound.PullConfirmation');
           reloadData();
         }
       });
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
                    var value = (vm.permissions.use_imei)? 0: vm.model_data.data[i].picked_quantity;
                    var temp = {zone: vm.model_data.data[i].zone,
                                location: vm.model_data.data[i].location,
                                orig_location: vm.model_data.data[i].location,
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

    vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

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
        if(total < data.reserved_quantity) {
          var clone = {};
          angular.copy(data.sub_data[index], clone);
          var temp = data.reserved_quantity - total;
          clone.picked_quantity = (remain < temp)?remain:temp;
          //clone.picked_quantity = data.reserved_quantity - total;
          data.sub_data.push(clone);
        }
      }
    } else {
      data.sub_data.splice(index,1);
    }
    vm.count_sku_quantity();
  }

  vm.cal_quantity = cal_quantity;
  function cal_quantity(record, data) {
    console.log(record);
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
  }

  vm.check_location = function(event, field) {

    var field = field;
    vm.service.scan(event, field).then(function(data){
      if(data) {
        vm.service.scan(event, field).then(function(data){
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
        });
      }
    }) 
  }

  vm.current_data = [];
  vm.check_sku = function(event, field) {

    var field = field;
    vm.service.scan(event, field).then(function(data){
      if(data) {
        if(vm.model_data.scan_location) {
          if(vm.check_sku_match(field)) {
            if(vm.model_data.sku_total_quantities[field] <= vm.remain_quantity[field]) {
              alert("Reservered quantity equal to picked quantity")
            } else {
              if (vm.check_comb()) {
                vm.incr_qty();
              } else {
                vm.service.apiCall("get_stock_location_quantity/", "GET", {location: vm.model_data.scan_location, wms_code: field})
                  .then(function(data){
                  if(data.data.message == "Invalid Location"){
                    alert("Invalid Location");
                  } else if(data.data.stock == 0) {
                    alert("Zero Stock");
                  } else {
                    var required = vm.model_data.sku_total_quantities[field] - vm.remain_quantity[field];
                    var temp_reserve = (data.data.stock < required)? data.data.stock: required;
                    vm.model_data.data.push({image: "",order_id: "", reserved_quantity: temp_reserve, wms_code: field, sub_data:[{location: vm.model_data.scan_location, picked_quantity: 1, new: true}]})
                    vm.count_sku_quantity();
                  }
                })
              }
            }
          } else {
            alert("Invalid SKU");
          }
          vm.model_data.scan_sku = "";
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
      //angular.forEach(data.sub_data, function(record){
      //  if(record.location == location || true) {
      //    record.picked_quantity = Number(record.picked_quantity) + 1;
      //    vm.count_sku_quantity();
      //    status = true;
      //    return status;
      //  }
      //})
    }
    return status;
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

  // Edit invoice
    vm.invoice_edit = false;
    vm.save_invoice_data = function(data) {

      var send = $(data.$name+":visible").serializeArray();
      vm.service.apiCall("edit_invoice/","POST",send).then(function(data){
        if(data.message) {
          vm.pdf_data.invoice_date =  vm.pdf_data.inv_date;
          vm.invoice_edit = false;
          vm.service.showNoty("Updated Successfully");
        }
      })
      console.log("edit");
    }

  vm.sku_scan = function(event, field) {

    var field = field;
    vm.service.scan(event, field).then(function(data){
      if(data) {
        vm.service.apiCall('check_sku/', 'GET',{'sku_code': field}).then(function(data){
          if(data.message) {
            field = data.data.sku_code;

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
}
