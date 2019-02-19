'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ReceiveJOCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', 'Data', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, Data, $modal) {
    var vm = this;
    vm.service = Service;
    vm.g_data = Data.receive_jo;
    vm.permissions = Session.roles.permissions;
    vm.sku_view = vm.g_data.sku_view;
    vm.table_name = (vm.g_data.sku_view)? 'ReceiveJOSKU' : 'ReceiveJO';
    vm.filters = {'datatable': vm.table_name};
    vm.tb_data = {};
    vm.po_qc = true;
    vm.po_qc = (vm.permissions.receive_process == "receipt-qc")? true: false;
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

  vm.serial_numbers = [];
  vm.serial_numbers_obj = {};
  vm.check_imei_exists = function(event, data1, index, innerIndex) {
    event.stopPropagation();
    if (event.keyCode == 13 && data1.imei_number.length > 0) {
            data1.imei_number = data1.imei_number.toUpperCase();
            if(vm.permissions.barcode_generate_opt != "sku_serial") {
              vm.service.apiCall('check_imei_exists/', 'GET',{imei: data1.imei_number, sku_code: data1.wms_code}).then(function(data){
                if(data.message) {
                  if (data.data == "") {
                    // data1.imei_number = data.data.data.label;
                    let skuWiseQtyTotal = 0;
                    // let tempUniqueDict = {};
                    angular.forEach(data1.sub_data, function(row){
                      skuWiseQtyTotal += Number(row.received_quantity);
                    });
                    // tempUniqueDict dict checking purpose only don't use anyware
                    if (data1.product_quantity > skuWiseQtyTotal) {
                      if (data1.sub_data[innerIndex].accept_imei && !data1.sub_data[innerIndex].tempUniqueDict[data1.imei_number]) {
                        data1.sub_data[innerIndex].received_quantity = Number(data1.sub_data[innerIndex].received_quantity) + 1;
                        data1.sub_data[innerIndex].accept_imei.push(data1.imei_number);
                        data1.sub_data[innerIndex].tempUniqueDict[data1.imei_number] = data1.imei_number;
                      } else {
                        if (data1.sub_data[innerIndex].tempUniqueDict && data1.sub_data[innerIndex].tempUniqueDict[data1.imei_number]) {
                          Service.showNoty("Scanned serial number already exist");
                        } else if (!data1.sub_data[innerIndex].tempUniqueDict) {
                          data1.sub_data[innerIndex]['accept_imei'] = [];
                          data1.sub_data[innerIndex]['tempUniqueDict'] = {};
                          data1.sub_data[innerIndex].tempUniqueDict[data1.imei_number] = data1.imei_number;
                          data1.sub_data[innerIndex].accept_imei.push(data1.imei_number);
                          data1.sub_data[innerIndex].received_quantity = 1;
                        }
                      }

                      // var sku_code = data.data.data.sku_code;
                      // if (data1.wms_code != sku_code) {
                      //   Service.showNoty("Scanned label belongs to "+sku_code);
                        data1.imei_number = "";
                      //   return false;
                      // }
                    } else {
                      Service.showNoty("No Quantity Available");
                    }

                    // vm.serial_numbers.push(data1.imei_number);
                    // sku.received_quantity = Number(sku.received_quantity) + 1;
                    // data1.imei_number = "";
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
                    let skuWiseQtyTotal = 0;
                    // let tempUniqueDict = {};
                    angular.forEach(data1.sub_data, function(row){
                      skuWiseQtyTotal += Number(row.received_quantity);
                    });
                    // tempUniqueDict dict checking purpose only don't use anyware
                    if (data1.product_quantity > skuWiseQtyTotal) {
                      if (data1.sub_data[innerIndex].accept_imei && !data1.sub_data[innerIndex].tempUniqueDict[data1.imei_number]) {
                        data1.sub_data[innerIndex].received_quantity = Number(data1.sub_data[innerIndex].received_quantity) + 1;
                        data1.sub_data[innerIndex].accept_imei.push(data1.imei_number);
                        data1.sub_data[innerIndex].tempUniqueDict[data1.imei_number] = data1.imei_number;
                      } else {
                        if (data1.sub_data[innerIndex].tempUniqueDict && data1.sub_data[innerIndex].tempUniqueDict[data1.imei_number]) {
                          Service.showNoty("Scanned serial number already exist");
                        } else if (!data1.sub_data[innerIndex].tempUniqueDict) {
                          data1.sub_data[innerIndex]['accept_imei'] = [];
                          data1.sub_data[innerIndex]['tempUniqueDict'] = {};
                          data1.sub_data[innerIndex].tempUniqueDict[data1.imei_number] = data1.imei_number;
                          data1.sub_data[innerIndex].accept_imei.push(data1.imei_number);
                          data1.sub_data[innerIndex].received_quantity = 1;
                        }
                      }

                      var sku_code = data.data.data.sku_code;
                      if (data1.wms_code != sku_code) {
                        Service.showNoty("Scanned label belongs to "+sku_code);
                        data1.imei_number = "";
                        return false;
                      }
                    } else {
                      Service.showNoty("No Quantity Available");
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
                  $('#'+index+'_'+innerIndex+'_imei').trigger('focus').val('');
                }
                data1["disable"] = false;
              })
            }
      //     }
      //   })
      // }
    }
  }

  vm.gen_barcode = function() {
    vm.barcode_title = 'Barcode Generation';
    vm.model_data['barcodes'] = [];

    vm.model_data['format_types'] = [];
    var key_obj = {};//{'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details', 'Bulk Barcode': 'Details'};
    vm.service.apiCall('get_format_types/').then(function(data){
      $.each(data['data']['data'], function(ke, val){
        vm.model_data['format_types'].push(ke);
      });
      key_obj = data['data']['data'];
    });
    Data.receive_jo_barcodes = true;
    var elem = angular.element($('form'));
    elem = elem[0];
    elem = $(elem).serializeArray();
    var list = [];
    var dict = {};
    $.each(elem, function(num, key){
      if(!dict.hasOwnProperty(key['name'])){
        dict[key['name']] = key['value'];
      }else{
        list.push(dict);
        dict = {}
          dict[key['name']] = key['value'];
      }
    });
    dict['quantity'] = dict['jo_quantity'];
    dict['po_id'] = dict.job_code;
    list.push(dict);
    vm.model_data['barcodes'] = list;
    vm.model_data['po_id'] = vm.model_data.job_code;
    vm.model_data.have_data = true;
    vm.model_data['custom_confg_flag'] = true;
    //$state.go('app.inbound.RevceivePo.barcode');
    var modalInstance = $modal.open({
      templateUrl: 'views/outbound/toggle/barcodes.html',
      controller: 'Barcodes',
      controllerAs: 'pop',
      size: 'lg',
      backdrop: 'static',
      keyboard: false,
      windowClass: 'z-2021',
      resolve: {
        items: function () {
          return vm.model_data;
        }
      }
    });

    modalInstance.result.then(function (selectedItem) {
      console.log(selectedItem);
    });
  }

  vm.barcode = function() {

    vm.barcode_title = 'Barcode Generation';

    vm.model_data['barcodes'] = [];

    angular.forEach(vm.model_data.data, function(barcode_data){

      var quant = barcode_data[0].value;

      var sku_det = barcode_data[0].wms_code;

      vm.model_data['barcodes'].push({'sku_code': sku_det, 'quantity': quant})

    })

    var modalInstance = $modal.open({
      templateUrl: 'views/outbound/toggle/barcodes.html',
      controller: 'Barcodes',
      controllerAs: 'pop',
      size: 'lg',
      backdrop: 'static',
      keyboard: false,
      resolve: {
        items: function () {
          console.log(model_data);
          return model_data;
        }
      }
    });

    modalInstance.result.then(function (selectedItem) {
    });
    //$state.go('app.inbound.RevceivePo.barcode');
  }

  // Qc Work
  /*vm.imei_list = [];
  vm.model_data1 = {};
  vm.po_qc_imei_scan = function(data1, index) {

    //vm.service.apiCall('check_imei_exists/', 'GET',{imei: data1.imei_number}).then(function(data){
    //  if(data.message) {
    //    if (data.data == "") {

          vm.current_index = index;
          // vm.model_data1["sku_data"] = data1.sku_details[0].fields;
          vm.imei_list.push(data1.imei_number);
          vm.accept_qc(data1, data1.imei_number);
          qc_details();
          data1.imei_number = "";
          vm.current_sku = "";
    //    } else {
    //      Service.showNoty(data.data);
    //    }
    //    data1.imei_number = "";
    //  }
    //})
  }

  vm.accept_qc = function(data, field) {

    vm.enable_button = false;
    // var sku = vm.model_data.data[vm.current_index][0];
    var sku = vm.model_data.data[vm.current_index];
    // sku.accepted_quantity = Number(sku.accepted_quantity) + 1;
    // sku.value = Number(sku.accepted_quantity) + Number(sku.rejected_quantity);

    sku["accept_imei"].push(field);
    // vm.model_data.data[vm.current_index][0] = sku
    vm.model_data.data[vm.current_index] = sku

    // fb.accept_serial(sku, field);
    vm.serial_scan = "";
  }

  vm.qc_details = qc_details;
  function qc_details() {

    $state.go('app.inbound.RevceivePo.qc_detail');
    $timeout(function() {
      if(vm.permissions.grn_scan_option == "serial_scan") {
        focus('focusIMEI');
      }
    }, 2000);
  }

  // FUN.scan_sku = vm.scan_sku;

  vm.po_imei_scan = function(data1, field) {

    if(data1["imei_list"].indexOf(field) != -1) {

      Service.showNoty("IMEI Already Scanned");
      return false;
    }
    data1.value = parseInt(data1.value)+1;
    vm.serial_numbers.push(field);
    data1["imei_list"].push(field);
    fb.change_serial(data1, field);
    vm.current_sku = "";
    data1.imei_number = "";
    if(vm.permissions.grn_scan_option == "sku_serial_scan") {
      $('textarea[name="scan_sku"]').trigger('focus').val('');
    }
  }
*/
  vm.changeStage = function(record, outerIndex, innerIndex) {
    if (record.stage == (record.stages_list[record.stages_list.length-1]) && vm.permissions.use_imei) {
      if (!record.stageStatus) {
        record.received_quantity = 0;
        record['stageStatus'] = true;
        $timeout( function(){
           $('#'+outerIndex+'_'+innerIndex+'_imei').trigger('focus').val('');
       }, 400 );
      }
      // if (record.received_quantity && record.stageStatus) {
      //   vm.confirmSwal2(record);
      // }
    } else {
      if (record.received_quantity && record.stageStatus) {
        vm.confirmSwal2(record);
        $('#'+outerIndex+'_'+innerIndex+'_imei').trigger('focus').val('');
      } else {
        record['stageStatus'] = false;
      }
    }
  }

  vm.confirmSwal2 = function (record) {
    swal2({
      title: '',
      text: 'Your received quantity will lose',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      confirmButtonText: 'Yes',
      cancelButtonText: 'No',
      confirmButtonClass: 'btn btn-danger',
      cancelButtonClass: 'btn btn-default'
    }).then(function (result) {
      $scope.$apply(function(){
        record.received_quantity = 0;
        record['stageStatus'] = false;
        record.accept_imei = [];
        record.tempUniqueDict = {};
      })
    }).catch(function (result){
      $scope.$apply(function(){
        record.stage = record.stages_list[record.stages_list.length-1];
        record['stageStatus'] = true;
      })
    });
  }

  vm.checkRecQty = function (record) {
    if (!record.stages_list.length) {
      record.received_quantity = 0;
    }
  }

/*
  vm.showOldQty = false;
  vm.goBack = function() {
    vm.showOldQty = true;
    $state.go('app.inbound.ReceiveJO.ReceiveJobOrder');
  }
*/
}
