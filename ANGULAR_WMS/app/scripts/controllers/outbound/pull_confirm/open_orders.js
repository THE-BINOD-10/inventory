'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('OpenOrders',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;

    vm.permissions = Session.roles.permissions;
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
       .withOption('rowCallback', rowCallback);

    vm.dtColumns = [
        DTColumnBuilder.newColumn('picklist_id').withTitle('Picklist ID'),
        DTColumnBuilder.newColumn('customer').withTitle('Customer / Marketplace').notSortable(),
         DTColumnBuilder.newColumn('picklist_note').withTitle('Picklist Note'),
        DTColumnBuilder.newColumn('reserved_quantity').withTitle('Reserved Quantity').notSortable(),
        DTColumnBuilder.newColumn('date').withTitle('Date')
    ];

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
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
              });
            });
        });
        return nRow;
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
        vm.service.apiCall('picklist_confirmation/', 'POST', elem).then(function(data){
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
        vm.service.apiCall('picklist_delete/','GET',{key: 'process', picklist_id: pick_id}).then(function(data){
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
           vm.service.apiCall('picklist_delete/','GET', {key: 'delete', picklist_id: pick_id}).then(function(data){
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
      angular.forEach(data.sub_data, function(record){
        if(record.location == location) {
          record.picked_quantity = Number(record.picked_quantity) + 1;
          vm.count_sku_quantity();
          status = true;
          return status;
        }
      })
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
          vm.invoice_edit = false;
        }
      })
      console.log("edit");
    }
}
