'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('POPutawayCtrl',['$scope', '$http', '$state', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', '$timeout', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, Session, DTOptionsBuilder, DTColumnBuilder, $timeout, colFilters, Service) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.service = Service;
    vm.industry_type = Session.user_profile.industry_type;
    vm.extra_width = {};

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
                vm.message = "";
                vm.service.apiCall('get_received_orders/', 'GET', {supplier_id: aData.DT_RowAttr["data-id"]}).then(function(data){
                  if(data.message) {
                    
                    if(vm.industry_type == 'FMCG'){
                      vm.extra_width = {
                        'width': '1200px'
                      };
                    } else {
                      vm.extra_width = {};
                    }

                    change_data(data.data);
                    $state.go('app.inbound.PutAwayConfirmation.confirmation');
                  }
                });
            });
        });
        return nRow;
    } 

    function change_data(data) {
      //var dat = {};
      //dat['po_number'] = data.po_number;
      //dat['order_id'] = data.order_id;
      //dat['data'] = []
      //for (var i = 0; i < data.data.length; i++) {
      //  var temp = data.data[i];
      //  var qt = (vm.permissions.use_imei)?0:temp[3];
      //  dat.data.push({'wms_code': temp[0], 'pallet_number': temp[6], 'original_quantity': temp[2],
      //            'id': temp[5], 'orig_loc_id': temp[4], 'sub_data': [{'loc': temp[1], 'quantity': qt}],
      //            'unit': temp[7], 'orig_data': ''})
      //
      //}
      angular.copy(data, vm.model_data);
      vm.model_data["sku_total_quantities"] = data.sku_total_quantities;
      //if(vm.permissions.use_imei) {
      //  angular.forEach(vm.model_data.data, function(data){
      //    data.sub_data[0].quantity = 0;
      //  })
      //}
      console.log(data);
      angular.copy(vm.model_data.sku_total_quantities ,vm.remain_quantity);
      vm.count_sku_quantity();
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
      vm.service.apiCall('putaway_data/', 'POST', elem, true).then(function(data){
        if(data.message) {
          if(data.data == "Updated Successfully") {
            vm.close();
            reloadData();
          } else {
            $state.go('app.inbound.PutAwayConfirmation.confirmation');
            pop_msg(data.data);
          }
        }
      }); 
    }

    function pop_msg(msg) {
      vm.message = "";
      vm.message = msg;
     }

  vm.isLast = isLast;
  function isLast(check) {

    var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
    return cssClass
  }

  vm.update_data = update_data;
  function update_data(index, data, last) {
    console.log(data);
    var remain = vm.model_data.sku_total_quantities[data.wms_code] - vm.remain_quantity[data.wms_code]
    if (last) {
      if(!(vm.model_data.sku_total_quantities[data.wms_code] <= vm.remain_quantity[data.wms_code])){
        var total = 0;
        for(var i=0; i < data.sub_data.length; i++) {
          total = total + parseInt(data.sub_data[i].quantity);
        }
        if(total < data.original_quantity) {
          var clone = {};
          angular.copy(data.sub_data[index], clone);
          var temp = data.original_quantity - total;
          clone.quantity = (remain < temp)?remain:temp;
          //clone.quantity = data.original_quantity - total;
          data.sub_data.push(clone);
        }
      }
    } else {
      data.sub_data.splice(index,1);
    }
    vm.count_sku_quantity();
  }

  vm.cal_quantity = cal_quantity;
  function cal_quantity(sku, data) {
    console.log(sku);
    var sku_qty = sku.quantity;
    var remain = vm.model_data.sku_total_quantities[data.wms_code] - vm.remain_quantity[data.wms_code]
    var total = 0;
    for(var i=0; i < data.sub_data.length; i++) {
        total = total + parseInt(data.sub_data[i].quantity);
    }
    if(data.original_quantity >= total){
      console.log(sku.quantity);
      if(remain < 0) {
        vm.change_quantity(sku, remain, sku_qty);
      }
    } else {
      var quantity = data.original_quantity-total;
      if(quantity < 0) {
        quantity = total - sku.quantity;
        quantity = data.original_quantity - quantity;
        sku.quantity = quantity;
      } else {
        sku.quantity = quantity;
      }
      vm.change_quantity(sku, remain, sku_qty)
    }
    vm.count_sku_quantity();
  }

  vm.change_quantity = function(sku, remain, sku_qty){
    console.log(remain);
    var temp = sku.quantity;
    if(remain == 0) {
      sku.quantity = 0;
      console.log(sku.quantity);
    } else if(remain < 0) {
      sku.quantity = Number(sku_qty) + remain;
    }
    if(Number(temp) < sku.quantity) {
      sku.quantity = temp;
    }
  }

  vm.print = function() {
    var clone = $(".print-html:first").clone();
    $(clone).removeClass("hide");
    vm.service.print_data(clone, 'Putaway Confirmation');  
  }

  //scanning
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
            vm.service.apiCall("get_location_capacity/", "GET", {location: field})
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
                vm.service.apiCall("get_location_capacity/", "GET", {location: vm.model_data.scan_location, wms_code: field})
                  .then(function(data){
                  if(data.data.message == "Invalid Location"){
                    alert("Invalid Location");
                  } else if(data.data.capacity == 0) {
                    alert("Zero Capacity");
                  } else {
                    var required = vm.model_data.sku_total_quantities[field] - vm.remain_quantity[field];
                    var temp_reserve = (data.data.capacity < required)? data.data.capacity: required;
                    vm.model_data.data.push({image: "",order_id: "", original_quantity: temp_reserve, wms_code: field, sub_data:[{loc: vm.model_data.scan_location, quantity: 1, new: true}]})
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
      total = total + Number(record.quantity);
    })
    var status = false
    if(data.original_quantity > total) {
      angular.forEach(data.sub_data, function(record){
        if(record.loc == location) {
          record.quantity = Number(record.quantity) + 1;
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
          if(record1.loc == vm.model_data.scan_location) {
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

        if(record1.loc == field) {
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

        temp = temp + Number(record1.quantity);
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
          if(temp1.loc == location && temp.original_quantity > vm.get_total(temp.sub_data)) {
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
    console.log(vm.sug_sku);
  }

  vm.get_total = function(data) {
    var total = 0;
    angular.forEach(data, function(record){
      total = total + Number(record.quantity);
    })
    return total;
  }  

}

