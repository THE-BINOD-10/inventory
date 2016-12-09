'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('POPutawayCtrl',['$scope', '$http', '$state', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', '$timeout', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, Session, DTOptionsBuilder, DTColumnBuilder, $timeout, colFilters, Service) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.service = Service;
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'POPutaway'},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('order', [0, 'desc'])
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

    vm.dtColumns = [
        DTColumnBuilder.newColumn('PO Number').withTitle('PO Number'),
        DTColumnBuilder.newColumn('Order Date').withTitle('Order Date'),
        DTColumnBuilder.newColumn('Supplier ID').withTitle('Supplier ID'),
        DTColumnBuilder.newColumn('Supplier Name').withTitle('Supplier Name'),
        DTColumnBuilder.newColumn('Order Type').withTitle('Order Type')
    ];

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.service.apiCall('get_received_orders/', 'GET', {supplier_id: aData.DT_RowAttr["data-id"]}).then(function(data){
                  if(data.message) {
                    change_data(data.data);
                    $state.go('app.inbound.PutAwayConfirmation.confirmation');
                  }
                });
            });
        });
        return nRow;
    } 

    function change_data(data) {
      var dat = {};
      dat['po_number'] = data.po_number;
      dat['order_id'] = data.order_id;
      dat['data'] = []
      for (var i = 0; i < data.data.length; i++) {
        var temp = data.data[i];
        var qt = (vm.permissions.use_imei)?0:temp[3];
        dat.data.push({'wms_code': temp[0], 'pallet_number': temp[6], 'original_quantity': temp[2],
                  'id': temp[5], 'orig_loc_id': temp[4], 'sub_data': [{'loc': temp[1], 'quantity': qt}],
                  'orig_data': temp[7]}) 
      
      }
      angular.copy(dat, vm.model_data);
      console.log(dat);
      vm.get_all_locations();
    }

    vm.model_data = {}
    vm.close = close;
    function close() {

      $state.go('app.inbound.PutAwayConfirmation');
    }

    vm.submit = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('putaway_data/', 'GET', elem).then(function(data){
        if(data.message) {
          if(data.data == "Updated Successfully") {
            vm.close();
            reloadData();
          } else {
            pop_msg(data.data);
          }
        }
      }); 
    }

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
        vm.message = "";
      }, 2000);
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
        total = total + parseInt(data.sub_data[i].quantity);
      }
      if(total < data.original_quantity) {
        var clone = {};
        angular.copy(data.sub_data[index], clone);
        clone.quantity = data.original_quantity - total;
        data.sub_data.push(clone);
      }
    } else {
      data.sub_data.splice(index,1);
    }
  }

  vm.cal_quantity = cal_quantity;
  function cal_quantity(sku, data) {
    console.log(sku);
    var total = 0;
    for(var i=0; i < data.sub_data.length; i++) {
        total = total + parseInt(data.sub_data[i].quantity);
    }
    if(data.original_quantity >= total){
      console.log(sku.quantity)
    } else {
      var quantity = data.original_quantity-total;
      if(quantity < 0) {
        quantity = total - sku.quantity;
        quantity = data.original_quantity - quantity;
        sku.quantity = quantity;
      } else {
        sku.quantity = quantity;
      }
    }
  }

  vm.print = function() {
    var clone = $(".print-html:first").clone();
    $(clone).removeClass("hide");
    vm.service.print_data(clone, 'Putaway Confirmation');  
  }

  vm.get_all_locations = function(data) {

    vm.scan_data.locations = []
    vm.unique_combination = [];
    angular.forEach(vm.model_data.data, function(temp1){

      angular.forEach(temp1.sub_data, function(temp2){

        if(vm.scan_data.locations.indexOf(temp2.loc) == -1) {

          vm.scan_data.locations.push(temp2.loc);
        }
        if(vm.total_quantity(temp1.sub_data) == temp1.original_quantity) {
          vm.unique_combination.push({locaton: temp2.loc, sku: temp1.wms_code, status: true});
        } else {
          vm.unique_combination.push({locaton: temp2.loc, sku: temp1.wms_code, status: false});
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

  vm.check_comb_stat = function(v1, v2) {

    var status = false;
    angular.forEach(vm.unique_combination, function(data) {
      if(data.locaton == v1 && data.sku == v2 && !(data.status)){
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
                if(vm.total_quantity(temp.sub_data) < Number(temp.original_quantity) && add_new) {
                      var clone = {};
                      angular.copy(temp.sub_data[0], clone);
                      clone.quantity = 1;
                      clone.loc = vm.model_data.scan_location;
                      temp.sub_data.push(clone);
                      vm.scan_data.locations.push(vm.model_data.scan_location);
                      vm.scan_data.suggested_sku.push(field);
                      vm.model_data.scan_sku = "";
                      vm.scan_data.loc_new = false;
                      vm.get_all_locations();
                      add_new = false;
                } else {
                  //alert("Reserved Quantity Equal to Picked Quantity.");
                  vm.model_data.scan_sku = "";
                }
              }
            })
        } else {
          if(vm.check_comb_stat(vm.model_data.scan_location, field)) {
            vm.incrs_qnty(field);
          } else {
            alert("Reserved Quantity Equal to Picked Quantity.");
          }
          vm.model_data.scan_sku = "";
        }
      }
    })
  }

  vm.status = true;
  vm.incrs_qnty = function(data) {

    var dict = {};
    vm.status = true;
    var location = vm.model_data.scan_location;
    vm.alert_status = false;
    angular.forEach(vm.model_data.data, function(temp){
      if(temp.wms_code == data) {
        if (vm.total_quantity(temp.sub_data) == Number(temp.original_quantity)) {
          //alert("Reserved Quantity Equal to Picked Quantity.");
          //vm.get_all_locations();
          //return;
           vm.alert_status = true;
        } else {
          angular.forEach(temp.sub_data, function(temp1){
            if(temp1.loc == location) {
              if(vm.status) {
                if(vm.is_total(temp)) {
                  if(temp1["stock"] && (temp1["stock"] <= Number(temp1.quantity)+1)) {
                    alert("Insufficient Stock");
                  } else {
                    temp1.quantity = Number(temp1.quantity)+1;
                    vm.alert_status = false;
                    vm.get_all_locations();
                    vm.status = false;
                  }
                  vm.status = false;
                  if(vm.total_quantity(temp.sub_data) == Number(temp.original_quantity)) {
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
      }
    })
    /*if(vm.alert_status) {
      alert("Reserved Quantity Equal to Picked Quantity");
      vm.alert_status = false;
      vm.model_data.scan_sku;
    }*/
  }
  
  vm.change_suggested = function(data) {

    if(vm.scan_data.suggested_sku[vm.scan_data.suggest_sku+1]){
      vm.scan_data.suggest_sku += 1;
    }
  }

  vm.is_total = function(data) {
    var total = 0
    angular.forEach(data.sub_data, function(temp){
      total = total + Number(temp.quantity);
    });
    if (Number(data.original_quantity) > total) {
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
      total = total + Number(temp.quantity);
    });
    return total;
  }
}

