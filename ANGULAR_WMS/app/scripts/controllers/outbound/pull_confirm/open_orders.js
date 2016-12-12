'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('OpenOrders',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;

    vm.permissions = Session.roles.permissions;
    vm.service = Service;
    vm.special_key = {status: 'open'};
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'OpenOrders', 'special_key':JSON.stringify(vm.special_key)},
              xhrFields: {
                withCredentials: true
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
        DTColumnBuilder.newColumn('picklist_note').withTitle('Picklist Note'),
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
                    var value = (vm.permissions.use_imei == "true")? 0: vm.model_data.data[i].picked_quantity;
                    var temp = {zone: vm.model_data.data[i].zone,
                                location: vm.model_data.data[i].location,
                                orig_location: vm.model_data.data[i].location,
                                picked_quantity: value}
                    if(vm.permissions.use_imei) {
                      temp["picked_quantity"] = 0;
                    }
                    vm.model_data.data[i]['sub_data'].push(temp);
                  }
                  vm.get_all_locations();
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

              angular.copy(data.data.data, vm.pdf_data);
              $state.go('app.outbound.PullConfirmation.GenerateInvoice');
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
        vm.service.print_data(data.data);
      }
    })
  }

    vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

  vm.update_data = update_data;
  function update_data(index, data, last) {
    console.log(data);
    if (last) {
      var total = 0;
      for(var i=0; i < data.sub_data.length; i++) {
        total = total + Number(data.sub_data[i].picked_quantity);
      }
      if(total < data.reserved_quantity) {
        var clone = {};
        angular.copy(data.sub_data[index], clone);
        clone.picked_quantity = data.reserved_quantity - total;
        data.sub_data.push(clone);
      }
    } else {
      data.sub_data.splice(index,1);
    }
  }

  vm.cal_quantity = cal_quantity;
  function cal_quantity(record, data) {
    console.log(record);
    var total = 0;
    for(var i=0; i < data.sub_data.length; i++) {
        total = total + Number(data.sub_data[i].picked_quantity);
    }
    if(data.reserved_quantity >= total){
      console.log(record.picked_quantity)
    } else {
      var quantity = data.reserved_quantity-total;
      if(quantity < 0) {
        quantity = total - Number(record.picked_quantity);
        quantity = data.reserved_quantity - quantity;
        record.picked_quantity = quantity;
      } else {
        record.picked_quantity = quantity;
      }
    }
  } 

  vm.get_all_locations = function(data) {

    vm.scan_data.locations = []
    vm.unique_combination = [];
    angular.forEach(vm.model_data.data, function(temp1){

      angular.forEach(temp1.sub_data, function(temp2){

        if(vm.scan_data.locations.indexOf(temp2.location) == -1) {

          vm.scan_data.locations.push(temp2.location);
        }
        if(vm.total_quantity(temp1.sub_data) == temp1.reserved_quantity) {
          vm.unique_combination.push({locaton: temp2.location, sku: temp1.wms_code, status: true});
        } else {
          vm.unique_combination.push({locaton: temp2.location, sku: temp1.wms_code, status: false});
        }
      })
    });
    vm.get_sug();
  }

  vm.check_comb = function(v1, v2) {

    var status = false;
    angular.forEach(vm.unique_combination, function(data) {
      if(data.locaton == v1 && data.sku == v2){
        status = true;
        return status;
      }
    })
    return status;
  }

  vm.sug_sku = "";
  vm.sug_loc = "";

  vm.get_sug = function() {

    var status = true;
    vm.sug_sku = "";
    angular.forEach(vm.unique_combination, function(data){

      if(vm.model_data.scan_location) {

        if(data.status == false && status && vm.model_data.scan_location == data.locaton) {

          vm.sug_sku = data.sku;
          vm.sug_loc = data.locaton;
          status = false;
          return;
        }
      } else if(data.status == false && status) {
        vm.sug_sku = data.sku;
        vm.sug_loc = data.locaton;
        status = false;
        return;
      }
    });
  }

  vm.unique_combination = [];
  vm.scan_data = { suggested_sku: [""], suggest_sku: 0 , locations:[], loc_new: false};

  vm.check_location = function(event, field) {

    vm.service.scan(event, field).then(function(data){
      if(data) {
          if(vm.scan_data.locations.indexOf(field) == -1) {
            vm.service.apiCall("get_stock_location_quantity/", "GET", {location: field, wms_code: vm.model_data.scan_sku})
            .then(function(data){
              if(data.data.message == "Invalid Location"){
                alert("Invalid Location");
                vm.model_data.scan_location = "";
                return;
              } else {
                vm.scan_data.loc_new = true;
                vm.scan_data.suggested_sku = [];
                vm.scan_data.suggest_sku = 0;
                $("textarea[attr-name='sku']").focus();
                angular.forEach(vm.model_data.data, function(temp){

                  angular.forEach(temp.sub_data, function(temp1){
                    if(vm.scan_data.suggested_sku.indexOf(temp.wms_code) == -1) {
                        vm.scan_data.suggested_sku.push(temp.wms_code);
                    }
                  })
                })
                vm.get_sug();
              }
            })  
          } else {
            
            vm.scan_data.suggested_sku = [];
            vm.scan_data.suggest_sku = 0;
            angular.forEach(vm.model_data.data, function(temp){
  
              angular.forEach(temp.sub_data, function(temp1){
                  if(vm.scan_data.suggested_sku.indexOf(temp.wms_code) == -1) {
                    vm.scan_data.suggested_sku.push(temp.wms_code);
                  }
              })
            })
            vm.get_sug();
            $("textarea[attr-name='sku']").focus();
          }
      }
    })
  }

  vm.check_sku = function(event, field) {

    var field = field;
    vm.service.scan(event, field).then(function(data){
      if(data) {
        if(!(vm.model_data.scan_location)) {
          alert("Please Scan Location First");
          $("textarea[attr-name='location']").focus();
          vm.model_data.scan_sku = "";
          return;
        } else if(vm.scan_data.suggested_sku.indexOf(field) == -1) {
          alert("Invalid SKU");
          vm.model_data.scan_sku = "";
        } else if(!(vm.check_comb(vm.model_data.scan_location, field))) {
          
          var add_new = true;
            angular.forEach(vm.model_data.data, function(temp){
              if(temp.wms_code == field) {
                if(vm.total_quantity(temp.sub_data) < Number(temp.reserved_quantity) && add_new) {
                  vm.service.apiCall("get_stock_location_quantity/", "GET", {location: vm.model_data.scan_location, wms_code: vm.model_data.scan_sku})
                  .then(function(data){
                    if(data.data.message == "Success" && data.data.stock > 0) {
                      var clone = {};
                      angular.copy(temp.sub_data[0], clone);
                      clone.picked_quantity = 1;
                      clone.location = vm.model_data.scan_location;
                      clone["stock"] = data.data.stock;
                      temp.sub_data.push(clone);
                      vm.scan_data.locations.push(vm.model_data.scan_location);
                      vm.scan_data.suggested_sku.push(field);
                      vm.model_data.scan_sku = "";
                      vm.scan_data.loc_new = false;
                      vm.get_all_locations();
                    } else {
                      alert("No Stock");
                      vm.model_data.scan_sku = "";
                    }
                  })
                  add_new = false;
                } else {
                  alert("Reserved Quantity Equal to Picked Quantity.");
                  vm.model_data.scan_sku = "";
                }
              }
            })
        } else {
          vm.incrs_qnty(field);
          vm.model_data.scan_sku = "";
        }
      }
    })
  }

  vm.status = true;
  vm.incrs_qnty = function(data) {

    var dict = {};
    vm.status = true;
    vm.open = true;
    var location = vm.model_data.scan_location;
    vm.alert_status = false;
    angular.forEach(vm.model_data.data, function(temp){
      if((temp.wms_code == data) && (vm.model_data.order_status == 'batch_open')) {
        if (vm.total_quantity(temp.sub_data) == Number(temp.reserved_quantity)) {
          alert("Reserved Quantity Equal to Picked Quantity.");
          vm.get_all_locations();
          return;
        } else {
          angular.forEach(temp.sub_data, function(temp1){
            if(temp1.location == location) {
              if(vm.status) {
                if(vm.is_total(temp)) {
                  if(temp1["stock"] && (temp1["stock"] <= Number(temp1.picked_quantity)+1)) {
                    alert("Insufficient Stock");
                  } else {
                    temp1.picked_quantity = Number(temp1.picked_quantity)+1; 
                    vm.get_all_locations();
                  }
                  vm.status = false;
                  if(vm.total_quantity(temp.sub_data) == Number(temp.reserved_quantity)) {
                    vm.get_all_locations();
                  }
                  return true;
                } else {
                  vm.model_data.scan_sku = "";
                  alert("Reserved Quantity Equal to Picked Quantity.");
                }
              }
            }
          })
        }
      } else {

        if(temp.wms_code == data) {
          angular.forEach(temp.sub_data, function(temp1){
            if(temp1.location == location) {
              if(vm.open) {
                if(vm.is_total(temp)) {
                  if(temp1["stock"] && (temp1["stock"] <= Number(temp1.picked_quantity)+1)) {
                    alert("Insufficient Stock");
                    
                  } else if(vm.open) {
                    temp1.picked_quantity = Number(temp1.picked_quantity)+1;
                    vm.open = false;
                    vm.alert_status = false;
                  } else {
                    vm.alert_status = true;
                  }
                  if(vm.total_quantity(temp.sub_data) == Number(temp.reserved_quantity)) {
                    vm.change_suggested(temp);
                  }
                } else {
                  vm.alert_status = true;
                }
              }
            }
          })
        }
      }
    })
    if(vm.alert_status) {
      alert("Reserved Quantity Equal to Picked Quantity");
      vm.alert_status = false;
      vm.model_data.scan_sku;
    } 
  }

  vm.change_suggested = function(data) {

    if(vm.scan_data.suggested_sku[vm.scan_data.suggest_sku+1]){
      vm.scan_data.suggest_sku += 1;
    }
  }

  vm.is_total = function(data) {
    var total = 0
    angular.forEach(data.sub_data, function(temp){
      total = total + Number(temp.picked_quantity);
    });
    if (Number(data.reserved_quantity) > total) {
      return true;
    } else {
      vm.status = false;
      vm.change_suggested(data);
      return false;
    }
  }

  vm.total_quantity = function(data) {

    var total = 0
    angular.forEach(data, function(temp){
      total = total + Number(temp.picked_quantity);
    });
    return total;
  }
}
