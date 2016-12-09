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
                    vm.model_data.data[i]['sub_data'].push({zone: vm.model_data.data[i].zone,
                                                         location: vm.model_data.data[i].location,
                                                         orig_location: vm.model_data.data[i].location,
                                                         picked_quantity: value});
                  }
                  $state.go('app.outbound.PullConfirmation.Open');
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
      $state.go('app.outbound.PullConfirmation');
    }

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

  vm.scan_data = { suggested_sku: [""], suggest_sku: 0 , locations:[]};

  vm.check_location = function(event, field) {

    vm.service.scan(event, field).then(function(data){
      if(data) {
        if (!(vm.model_data.scan_sku)) {
          vm.scan_data.suggested_sku = [];
          vm.scan_data.suggest_sku = 0;
          angular.forEach(vm.model_data.data, function(temp){
  
            angular.forEach(temp.sub_data, function(temp1){
              if(temp1.location == field) {
                if(vm.scan_data.suggested_sku.indexOf(temp.wms_code) == -1) {
                  vm.scan_data.suggested_sku.push(temp.wms_code);
                }
              }
            })
          })
        } else {
          if(vm.scan_data.locations.indexOf(field) == -1) {
            angular.forEach(vm.model_data.data, function(temp){
              if(temp.wms_code == vm.model_data.scan_sku) {
                var clone = {};
                angular.copy(temp.sub_data[0], clone);
                clone.picked_quantity = 1;
                clone.location = field;
                temp.sub_data.push(clone);
                vm.scan_data.locations.push(field);
                return;
              }
            })  
          } else {
            vm.incrs_qnty(vm.model_data.scan_sku); 
          }
        }
        if(vm.model_data.scan_sku) {
          vm.model_data.scan_location = "";
        }
      }
    })
  }

  vm.check_sku = function(event, field) {

    var field = field;
    vm.service.scan(event, field).then(function(data){
      if(data) {
        if ((vm.scan_data.suggested_sku.indexOf(field) == -1) && vm.model_data.scan_location) {
          alert("Invalid SKU");
        } else if(!(vm.model_data.scan_location)) {

          var sku_list = [];
          angular.forEach(vm.model_data.data, function(temp){
            if(sku_list.indexOf(temp.wms_code) == -1) {
               sku_list.push(temp.wms_code)
            }
          })
          if(sku_list.indexOf(field) == -1) {
            alert("Invalid SKU")
            vm.model_data.scan_sku = "";
          } else {
            vm.scan_data.locations = [];
            angular.forEach(vm.model_data.data, function(temp){
              if(temp.wms_code == field) {
                if (vm.total_quantity(temp.sub_data) == Number(temp.reserved_quantity)) {
                  alert("Reserved Quantity Equal to Picked Quantity.");
                } else {
                  angular.forEach(temp.sub_data, function(temp1){
                  if(vm.scan_data.locations.indexOf(temp1.location) == -1) {
                    vm.scan_data.locations.push(temp1.location);
                    }
                  })
                }
                return;
              }
            })
          }
        } else {
          vm.incrs_qnty(field);
        }
        if(vm.model_data.scan_location) {
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
    angular.forEach(vm.model_data.data, function(temp){
      if(temp.wms_code == data) {
        if (vm.total_quantity(temp.sub_data) == Number(temp.reserved_quantity)) {
          alert("Reserved Quantity Equal to Picked Quantity.");
          return;
        } else {
          angular.forEach(temp.sub_data, function(temp1){
            if(temp1.location == location) {
              if(vm.status) {
                if(vm.is_total(temp)) {
                  temp1.picked_quantity = Number(temp1.picked_quantity)+1;
                  vm.status = false;
                  if(vm.total_quantity(temp.sub_data) == Number(temp.reserved_quantity)) {
                    vm.change_suggested();
                  }
                  return true;
                }
              }
            }
          })
        }
      }
    }) 
  }

  vm.change_suggested = function() {

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
      vm.change_suggested();
      alert("Reserved Quantity Equal to Picked Quantity.");
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
