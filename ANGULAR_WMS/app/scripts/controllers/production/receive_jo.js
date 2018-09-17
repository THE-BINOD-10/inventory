'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ReceiveJOCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, Data) {
    var vm = this;
    vm.service = Service;
    vm.g_data = Data.receive_jo;
    vm.permissions = Session.roles.permissions;
    vm.sku_view = vm.g_data.sku_view;
    vm.table_name = (vm.g_data.sku_view)? 'ReceiveJOSKU' : 'ReceiveJO';
    vm.filters = {'datatable': vm.table_name};
    vm.tb_data = {};
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: vm.filters,
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
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

    vm.dtColumns = vm.service.build_colums(vm.g_data.tb_headers[vm.table_name]);

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
              var data = {};
              if (vm.sku_view) {
                data['job_id'] = aData.DT_RowAttr['data-id'];
              } else {
                data['data_id'] = aData.DT_RowAttr['data-id'];
              }
              vm.service.apiCall('confirmed_jo_data/', 'GET', data).then(function(data){
                if(data.message) {
                  angular.copy(data.data, vm.model_data);
                  var skus_list = [];
                  vm.final_data = {};
                  angular.forEach(vm.model_data.data, function(record){
                    if (skus_list.indexOf(record.wms_code) == -1){
                        skus_list.push(record.wms_code);
                        vm.final_data[record.wms_code] = {quantity: 0, sku_desc: record.sku_desc}
                        }
                  });
                  vm.total_data = {quantity: 0};
                  for (var i=0; i<skus_list.length; i++){
                    var sku_one = skus_list[i];
                    angular.forEach(vm.model_data.data, function(record){
                      if (record.wms_code == sku_one){
                        vm.final_data[sku_one].quantity += record.product_quantity;
                      }
                    });
                  }
                  angular.forEach(vm.final_data, function(value, key){
                    vm.total_data.quantity += value.quantity;
                  });
		  vm.order_ids_list = data.data.order_ids.toString();
                  $state.go('app.production.ReveiveJO.ReceiveJobOrder');
                }
              });
            });
        });
        return nRow;
    }

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
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

      vm.print_enable = false;
      $state.go('app.production.ReveiveJO');
    } 

    vm.html = "";
    vm.print_enable = false;
    vm.submit = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('confirm_jo_grn/', 'POST', elem, true).then(function(data){
        if(data.message) {
          vm.reloadData();
          if (data.data["status"]) {
            pop_msg(data.data.status);
            change_pallet_ids(data.data.data);
          } else {
            vm.html = $(data.data)[2];
            var html = $(vm.html).closest("form").clone();
            angular.element(".modal-body").html($(html).find(".modal-body > .form-group"));
            vm.print_enable = true;
          }
        }
      });
    }

    function change_pallet_ids(data) {

      angular.forEach(vm.model_data.data, function(record){

        if(data[record.id]) {
          angular.forEach(record.sub_data, function(item, index) {

            item["pallet_id"] = data[record.id][index][1]["pallet_id"];
            item["status_track_id"] = data[record.id][index][3];
          });
        }
      });
      console.log(vm.model_data, data); 
    }

    vm.save = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('save_receive_jo/', 'POST', elem, true).then(function(data){
        if(data.message) {
          if (data.data == 'Saved Successfully') {
            vm.close();
            vm.reloadData();
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

  vm.update_data = update_data;
  function update_data(index, data, last) {
    console.log(data);
    if (last) {
      var total = 0;
      for(var i=0; i < data.sub_data.length; i++) {
        total = total + Number(data.sub_data[i].received_quantity);
      }
      if(total < data.product_quantity) {
        var clone = {};
        angular.copy(data.sub_data[index], clone);
        clone.received_quantity = data.product_quantity - total;
        clone.received_quantity = clone.received_quantity.toFixed(2);
        clone.pallet_id = "";
        //clone.status_track_id = "";
        data.sub_data.push(clone);
      }
    } else {
      data.sub_data.splice(index,1);
    }
  }

    vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

  vm.cal_quantity = cal_quantity;
  function cal_quantity(record, data) {
    console.log(record);
    var total = 0;
    for(var i=0; i < data.sub_data.length; i++) {
        total = total + Number(data.sub_data[i].received_quantity);
    }
    if(data.product_quantity >= total){
      console.log(record.received_quantity)
    } else {
      var quantity = data.product_quantity-total;
      if(quantity < 0) {
        quantity = total - Number(record.received_quantity);
        quantity = data.product_quantity - quantity;
        record.received_quantity = quantity;
      } else {
        record.received_quantity = quantity;
      }
    }
  } 

  vm.print = print;
  function print() {
    vm.service.print_data(vm.html);
  }

  vm.change_sku_view = function(){

    Data.receive_jo.sku_view = vm.sku_view;
    $state.go($state.current, {}, {reload: true});    
  }

  // vm.serial_numbers = [];
  vm.check_imei_exists = function(event, data1, index) {
    event.stopPropagation();
    if (event.keyCode == 13 && data1.imei_number.length > 0) {
      //if(vm.imei_list.indexOf(data1.imei_number) > -1) {

      //  Service.showNoty("IMEI Already Scanned");

      /*if (vm.fb.poData.serials.indexOf(data1.imei_number) != -1){

        Service.showNoty("Serial Number already Exist");
        data1.imei_number = "";
        if(vm.permissions.grn_scan_option == "sku_serial_scan") {
          $('textarea[name="scan_sku"]').trigger('focus').val('');
        }
      } else {

        data1["disable"] = true;
        fb.check_imei(data1.imei_number).then(function(resp) {
          if (resp.status) {
            Service.showNoty("Serial Number already Exist in other PO: "+resp.data.po);
            data1.imei_number = "";
            //if(vm.permissions.barcode_generate_opt != "sku_serial") { 
            //  $('textarea[name="scan_sku"]').trigger('focus').val('');
            //}
            if(vm.permissions.grn_scan_option == "sku_serial_scan") {
              $('textarea[name="scan_sku"]').trigger('focus').val('');
            }
            data1["disable"] = false;
          } else {*/
            if(vm.permissions.barcode_generate_opt != "sku_serial") {
              vm.service.apiCall('check_imei_exists/', 'GET',{imei: data1.imei_number, sku_code: data1.wms_code}).then(function(data){
                if(data.message) {
                  if (data.data == "") {
                    // if(vm.po_qc) {
                    //   vm.po_qc_imei_scan(data1, index)
                    // } else {
                    //   vm.po_imei_scan(data1, data1.imei_number)
                    // }
                  } else {
                    Service.showNoty(data.data);
                    data1.imei_number = "";
                  }
                }
                data1["disable"] = false;
              })
            } else {
              vm.service.apiCall('check_generated_label/', 'GET',{'label': data1.imei_number, 'order_id': vm.model_data.job_code}).then(function(data){
                if(data.message) {
                  if(data.data.message == 'Success') {
                    data1.imei_number = data.data.data.label;
                    var sku_code = data.data.data.sku_code;
                    if (data1.wms_code != sku_code) {
                      Service.showNoty("Scanned label belongs to "+sku_code);
                      data1.imei_number = "";
                      return false;
                    }
                    // if(vm.po_qc) {
                    //   vm.po_qc_imei_scan(data1, index)
                    // } else {
                    //   vm.po_imei_scan(data1, data1.imei_number)
                    // }
                  } else {
                     Service.showNoty(data.data.message);
                     data1.imei_number = "";
                  }
                }
                data1["disable"] = false;
              })
            }
      //     }
      //   })
      // }
    }
  }

}

