'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ReceiveJOCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', 'Data', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, Data, $modal) {
    var vm = this;
    vm.service = Service;
    vm.g_data = Data.receive_jo;
    vm.permissions = Session.roles.permissions;
    vm.selectAll = false;
    vm.rwo_view  = false;
    vm.selected = {};
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
       .withOption('rowCallback', rowCallback)
       .withOption('drawCallback', function(settings) {
         vm.service.make_selected(settings, vm.selected);
       })


    vm.dtColumns = vm.service.build_colums(vm.g_data.tb_headers[vm.table_name]);
    vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
      .renderWith(function(data, type, full, meta) {
        if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
          vm.selected = {};
        }
        vm.selected[meta.row] = vm.selectAll;
        return vm.service.frontHtml + meta.row + vm.service.endHtml;
    }))
    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
      $('td:not(td:first)', nRow).unbind('click');
      $('td:not(td:first)', nRow).bind('click', function()  {
            $scope.$apply(function() {
              if (vm.selected[iDisplayIndex]) {
                vm.selected[iDisplayIndex] = false;
              } else {
                vm.selected[iDisplayIndex] = true;
              }
              vm.bt_disable = vm.service.toggleOne(vm.selectAll, vm.selected, vm.bt_disable);
              vm.selectAll = vm.service.select_all(vm.selectAll, vm.selected);
              var data = {};
              if (vm.sku_view) {
                data['job_id'] = aData.DT_RowAttr['data-id'];
              } else {
                data['data_id'] = aData.DT_RowAttr['data-id'];
              }
             if(vm.rwo_view){
               var elem = {};
               vm.send_data ={}
               if (aData.DT_RowAttr.hasOwnProperty('data-id')) {
                 elem = {'data_id': aData.DT_RowAttr['data-id']}
               } else {
                 elem =  {'id': aData.DT_RowAttr['id'],'rwo':true}
               }

               vm.service.apiCall('rwo_data/', 'POST',elem).then(function(data){
                 if(data.message) {
                   angular.copy(data.data, vm.send_data);
                   vm.send_data['job_creation_date'] = aData["Creation Date"]
                   vm.send_data['job_code'] = aData["Job Code"]
                   vm.scanned_return_serials =[];
                   vm.scanned_replaced_serials =[];
                   $state.go('app.production.ReveiveJO.Rm');
                 }
               });
            }
             else{
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
            }
            });
        });
        return nRow;
    }

    vm.dtInstance = {};
    vm.reloadData = reloadData;
    vm.scanned_return_serials =[];
    vm.scanned_replaced_serials = [];

    function reloadData () {
        vm.dtInstance.reloadData();
    };
    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }
    vm.scan_return__serial = function(event,serial_number){
      event.stopPropagation();

      if (event.keyCode == 13 )
      {
        if (vm.scanned_return_serials.indexOf(serial_number) === -1 )
        {
         vm.service.apiCall('check_return_imei_scan/', 'GET', {'serial_number':serial_number}).then(function(data){
           if (data.data.data)
             {
                for(var i =0 ;i< vm.send_data.data.length;i++)
                {
                  if (vm.send_data.data[i].wms_code ==  data.data.data)
                  {
                    if(vm.send_data.data[i].picked_quantity>0)
                    {
                      vm.send_data.data[i].picked_quantity-=1
                      vm.send_data.data[i].return_quantity +=1
                      vm.scanned_return_serials.push(serial_number);
                      vm.send_data.scan_return_serial ='';
                    }
                  }
                }
               }
            else{
              Service.showNoty("Invalid Imei Number");
            }

          });
      }
      else {
        {
          Service.showNoty("Serial Already Scanned");
        }
      }
    }

  }
    vm.scan_replace_serial = function(event ,value){
      event.stopPropagation();
      var replace_dict = {}
      if (event.keyCode == 13) {
        if (vm.scanned_replaced_serials.indexOf(value.replace_serial) == -1 )
        {
        vm.service.apiCall('check__replace_imei_exists/', 'GET',{imei: value.replace_serial, sku_code: value.wms_code}).then(function(data){
          if(data.message) {
            if (data.data.status == "Success") {
              if(vm.scanned_return_serials.length > 0 && value.return_quantity > value.replacement_quntity)
              {
                replace_dict['po_id']= data.data.po_id;
               replace_dict['serial_number'] = value.replace_serial;
               replace_dict['sku_id'] = value.sku_id;
              vm.scanned_replaced_serials.push(replace_dict);
              value.picked_quantity+=1;
              value.replacement_quntity+=1;
              focus('focusSKU');
              value.replace_serial = "";
              }
              else{
                Service.showNoty("Unable to Replace Please Check");
              }
            } else {
              Service.showNoty(data.data.status);
            }
          }
        })
      }
      else {
          Service.showNoty("Imei number already scanned");
      }
    }
  }

    vm.model_data = {};

    vm.close = close;
    function close() {

      vm.print_enable = false;
      $state.go('app.production.ReveiveJO');
    }
    vm.scanned_return_serials = [];
    vm.scanned_replaced_serials = [];
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
    vm.save_replace = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.save_repalced_serials();
      vm.service.apiCall('save_replaced_locations/', 'POST', elem, true).then(function(data){
        if(data.message) {
          if (data.data == 'Added Successfully') {
            vm.close();
            vm.reloadData();
          } else {
            pop_msg(data.data);
          }
        }
      });
    }
    vm.save_repalced_serials = function()
    {
      vm.service.apiCall('save_replaced_serials/', 'POST',{'returned_serials':vm.scanned_return_serials ,'replacement_serials':JSON.stringify(vm.scanned_replaced_serials)} ).then(function(data){
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
  vm.add = function () {
      vm.bt_disable = true;
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.selectedRows[parseInt(key)];
          data[temp['WMS Code']+":"+$(temp[""]).attr("name")] = temp['Procurement Quantity'];
        }
      });
      var send_data  = {data: data}
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


}
