'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ReceivePOCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.filters = {'datatable': 'ReceivePO', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': '', 'search5': ''}
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: vm.filters,
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('order', [0, 'desc'])
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    var columns = ['PO Number', 'Order Date', 'Supplier ID', 'Supplier Name', 'Order Type', 'Receive Status'];
    vm.dtColumns = vm.service.build_colums(columns);

    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.service.apiCall('get_supplier_data/', 'GET', {supplier_id: aData['DT_RowId']}).then(function(data){
                  if(data.message) {
                    vm.serial_numbers = [];
                    angular.copy(data.data, vm.model_data);
                    vm.title = "Generate GRN";
                    if(aData['Order Type'] == "Vendor Receipt") {
                      $state.go('app.inbound.RevceivePo.Vendor');
                    } else {
                      $state.go('app.inbound.RevceivePo.GRN');
                    }
                  }
                });
            });
        });
        return nRow;
    }

    vm.filter_enable = true;
    vm.print_enable = false;
    vm.update = false;
    vm.model_data = {};
    vm.dis = true;

    vm.close = close;
    function close() {

      vm.model_data = {};
      vm.html = "";
      vm.print_enable = false;
      $state.go('app.inbound.RevceivePo');
    }

    vm.update_data = update_data;
    function update_data(index, data) {
      if (Session.roles.permissions['pallet_switch']) {
        if (index == data.length-1) {
          var new_dic = {};
          angular.copy(data[0], new_dic);
          new_dic.receive_quantity = 0;
          new_dic.value = "";
          new_dic.pallet_number = "";
          data.push(new_dic);
        } else {
          data.splice(index,1);
        }
      }
    }
    vm.new_sku = false
    vm.add_wms_code = add_wms_code;
    function add_wms_code() {
      vm.model_data.data.push([{"wms_code":"", "po_quantity":"", "receive_quantity":"", "price":"", "dis": false, "order_id": vm.model_data.data[0][0].order_id, is_new: true}]);
      //vm.new_sku = true
    }

    vm.submit = submit;
    function submit() {
      var data = [];
      for(var i=0; i<vm.model_data.data.length; i++)  {
         var temp = vm.model_data.data[i][0];
         data.push({name: temp.order_id, value: temp.value});
      }
      vm.service.apiCall('update_putaway/', 'GET', data).then(function(data){
        if(data.message) {
          if(data.data == 'Updated Successfully') {
            vm.close();
          } else {
            pop_msg(data.data);
          }
        }
      });
    }

    vm.html = "";
    vm.confirm_grn = function(form) {

     if(check_receive()){
      var that = vm;
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('confirm_grn/', 'GET', elem).then(function(data){
        if(data.message) {
          if(data.data.search("<div") != -1) {
            vm.html = $(data.data)[2];
            var html = $(vm.html).closest("form").clone();
            angular.element(".modal-body").html($(html).find(".modal-body"));
            vm.print_enable = true;
            vm.service.refresh(vm.dtInstance);
          } else {
            pop_msg(data)
          }
        }
      });
     }
    }

    function check_receive() {
      var status = false;
      for(var i=0; i<vm.model_data.data.length; i++)  {
        if(vm.model_data.data[i][0].value > 0) {
          status = true;
          break;
        }
      }
      if(status){
        return true;
      } else {
        pop_msg("Please Update the received quantity");
        return false;
      }
    }

    vm.close_po = close_po;
    function close_po(data) {
        var elem = angular.element($('form'));
        elem = elem[0];
        elem = $(elem).serializeArray();
        //elem.push({name: "new_sku", value: vm.new_sku});
        vm.service.apiCall('close_po/', 'GET', elem).then(function(data){
          if(data.message) {
            pop_msg(data.data)
            if(data.data == 'Updated Successfully') {
              vm.close();
              vm.service.refresh(vm.dtInstance);
            }
          }
        });
    }

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
        vm.message = "";
      }, 2000);
      vm.service.refresh(vm.dtInstance);
    }

    vm.scan_sku = function(event, field) {
      if (event.keyCode == 13 && field.length > 0) {
        console.log(field);
        for(var i=0; i<vm.model_data.data.length; i++) {
          if(field == vm.model_data.data[i][0]["wms_code"]){
            $('input[value="'+field+'"]').parents('tr').find("input[name='quantity']").trigger('focus');
            console.log("success");
            break;
          }
        }
      }
    }

    vm.serial_numbers = [];
    vm.check_imei_exists = function(event, data1) {
      event.stopPropagation();
      if (event.keyCode == 13 && data1.imei_number.length > 0) {
        if (vm.serial_numbers.indexOf(data1.imei_number) != -1){
            pop_msg("Serial Number already Exist");
        } else {
          vm.service.apiCall('check_imei_exists/', 'GET',{imei: data1.imei_number}).then(function(data){
            if(data.message) {
              if (data.data == "") {
                data1.value = parseInt(data1.value)+1;
                vm.serial_numbers.push(data1.imei_number);
              } else {
                pop_msg(data.data);
              }
              data1.imei_number = "";
            }
          });
        }
      }
    }

    vm.print_grn = function() {
      vm.service.print_data(vm.html, "Generate GRN");
    }

    vm.vendor_receive = function(data) {

      if(data.$valid) {

        var elem = angular.element($('form'));
        elem = elem[0];
        elem = $(elem).serializeArray();
        vm.service.apiCall("confirm_vendor_received/", 'GET', elem).then(function(data){

          if(data.message) {

            if(data.data == "Updated Successfully") {

              vm.service.refresh(vm.dtInstance);
              vm.close();
            } else {
              pop_msg(data.data);
            }
          }
        });
      }
    }
  }

