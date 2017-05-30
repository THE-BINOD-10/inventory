'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ReceivePOCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.service = Service;

    //process type;
    vm.po_qc = true;
    vm.po_qc = (vm.permissions.receive_process == "receipt-qc")? true: false;

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
                    if(vm.permissions.use_imei) {
                      fb.push_po(vm.model_data);
                    }
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
      if(vm.permissions.use_imei) {
        fb.stop_fb();
        vm.imei_list = [];
      }
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
      vm.model_data.data.push([{"wms_code":"", "po_quantity":"", "receive_quantity":"", "price":"", "dis": false,
                                "order_id": vm.model_data.data[0][0].order_id, is_new: true, "unit": "",
                                "sku_details": [{"fields": {"load_unit_handle": ""}}]}]);
      //vm.new_sku = true
    }
    vm.get_sku_details = function(data, selected) {

      data.sku_details[0].fields.load_unit_handle = selected.load_unit_handle;
      data.wms_code = selected.wms_code;
      $timeout(function() {$scope.$apply();}, 1000);
    }

    vm.submit = submit;
    function submit() {
      var data = [];
      for(var i=0; i<vm.model_data.data.length; i++)  {
         var temp = vm.model_data.data[i][0];
         data.push({name: temp.order_id, value: temp.value});
      }
      vm.service.apiCall('update_putaway/', 'GET', data, true).then(function(data){
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
      var url = "confirm_grn/"
      if(vm.po_qc) {
        url = "confirm_receive_qc/"
      }
      vm.service.apiCall(url, 'POST', elem, true).then(function(data){
        if(data.message) {
          if(data.data.search("<div") != -1) {
            vm.html = $(data.data)[2];
            var html = $(vm.html).closest("form").clone();
            angular.element(".modal-body").html($(html).find(".modal-body"));
            vm.print_enable = true;
            vm.service.refresh(vm.dtInstance);
            if(vm.permissions.use_imei) {
              fb.generate = true;
              fb.remove_po(fb.poData["id"]);
            }
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
        vm.service.apiCall('close_po/', 'GET', elem, true).then(function(data){
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

    vm.receive_quantity_change = function(data) {

      if(Session.user_profile.user_type == "marketplace_user") {
        if(Number(data.po_quantity) < Number(data.value)) {
          data.value = data.po_quantity;
        }
      }
    }

    vm.scan_sku = function(event, field) {
      if (event.keyCode == 13 && field.length > 0) {
        console.log(field);
        vm.service.apiCall('check_sku/', 'GET',{'sku_code': field}).then(function(data){
          if(data.message) {
            vm.field = data.data.sku_code;

            if (vm.permissions.use_imei) {
              vm.sku_list_1 = [];
              for(var i=0; i<vm.model_data.data.length; i++) {
                vm.sku_list_1.push(vm.model_data.data[i][0]["wms_code"]);
                if(vm.field == vm.model_data.data[i][0]["wms_code"]){
                  $("input[attr-name='imei_"+vm.field+"']").trigger('focus');
                }
              }
              if (vm.sku_list_1.indexOf(vm.field) == -1){
                Service.showNoty(field+" Does Not Exist");
              }
              vm.model_data.scan_sku = "";
            } else {
              vm.sku_list_1 = [];
              for(var i=0; i<vm.model_data.data.length; i++) {
                vm.sku_list_1.push(vm.model_data.data[i][0]["wms_code"]);
                if(vm.field == vm.model_data.data[i][0]["wms_code"]){
                  if(vm.model_data.data[i][0].value < vm.model_data.data[i][0].po_quantity) {
                    vm.model_data.data[i][0]["value"] = Number(vm.model_data.data[i][0]["value"]) + 1;
                  } else {
                     Service.showNoty("Received Quantity Equal To PO Quantity");
                  }
                  $('textarea[name="scan_sku"]').trigger('focus').val('');
                }
              }
              if (vm.sku_list_1.indexOf(field) == -1){
                Service.showNoty(field+" Does Not Exist");
              }
            }
          }
        });
      }
    }

    vm.po_imei_scan = function(data1) {

      if (vm.serial_numbers.indexOf(data1.imei_number) != -1){
          Service.showNoty("Serial Number already Exist");
          data1.imei_number = "";
          $('textarea[name="scan_sku"]').trigger('focus').val('');
        } else if (vm.fb.poData.serials.indexOf(data1.imei_number) != -1){
          Service.showNoty("Serial Number already Exist");
          data1.imei_number = "";
          $('textarea[name="scan_sku"]').trigger('focus').val('');
        } else {
          vm.service.apiCall('check_imei_exists/', 'GET',{imei: data1.imei_number}).then(function(data){
            if(data.message) {
              if (data.data == "") {
                data1.value = parseInt(data1.value)+1;
                vm.serial_numbers.push(data1.imei_number);
                data1["imei_list"].push(data1.imei_number);
                fb.change_serial(data1, data1.imei_number);
                $('textarea[name="scan_sku"]').trigger('focus').val('');
              } else {
                Service.showNoty(data.data);
              }
              data1.imei_number = "";
            }
          });
        }
    }

    vm.qc_details = qc_details;
    function qc_details() {

      $state.go('app.inbound.RevceivePo.qc_detail');
    }

    vm.goBack = function() {

      $state.go('app.inbound.RevceivePo.GRN');
    }

    vm.imei_list = [];
    vm.model_data1 = {};
    vm.po_qc_imei_scan = function(data1, index) {

      vm.service.apiCall('check_imei_exists/', 'GET',{imei: data1.imei_number}).then(function(data){
        if(data.message) {
          if (data.data == "") {

            vm.current_index = index;
            vm.model_data1["sku_data"] = data1.sku_details[0].fields;
            vm.imei_list.push(data1.imei_number);
            vm.accept_qc(data1, data1.imei_number);
            qc_details();
          } else {
            Service.showNoty(data.data);
          }
          data1.imei_number = "";
        }
      })
    }

    vm.from_qc_scan = function(event, field) {

      event.stopPropagation();
      if (event.keyCode == 13 && field.length > 0) {

        if(vm.imei_list.indexOf(field) > -1) {

          Service.showNoty("IMEI Already Scanned");
        } else if(vm.model_data.data[vm.current_index][0].po_quantity == vm.model_data.data[vm.current_index][0].value) {

          Service.showNoty("PO quanity already equal to Receive Quantity for with SKU Code");
        } else {
          vm.service.apiCall('check_imei_exists/', 'GET',{imei: field}).then(function(data){
            if(data.message) {
              if (data.data == "") {
                vm.imei_list.push(field);
                vm.accept_qc(vm.model_data.data[vm.current_index], field);
              } else {
                Service.showNoty(data.data);
              }
            }
          })
          console.log(vm.current_index);
        }
      }
    }

    vm.serial_numbers = [];
    vm.check_imei_exists = function(event, data1, index) {
      event.stopPropagation();
      if (event.keyCode == 13 && data1.imei_number.length > 0) {
        if(vm.imei_list.indexOf(data1.imei_number) > -1) {

          Service.showNoty("IMEI Already Scanned");
        } else {
          if(vm.po_qc) {
            vm.po_qc_imei_scan(data1, index)
          } else {
            vm.po_imei_scan(data1)
          }
        }
      }
    }

    vm.change_sku_scan = function(event, sku) {

      if (event.keyCode == 13 && sku.length > 0) {
        event.stopPropagation();
        var status = true;
        for(var i = 0; i < vm.model_data.data.length; i++) {

          var data = vm.model_data.data[i][0];
          if(data.wms_code == sku) {

            vm.enable_button = true;
            vm.reason_show = false;
            vm.current_index = i;
            status = false;
            break;
          }
        }
        if(status) {

          Service.showNoty("SKU Not Found");
        }
        vm.change_sku = "";
      }
    }

    vm.print_grn = function() {
      vm.service.print_data(vm.html, "Generate GRN");
    }


    vm.barcode = function() {

      vm.barcode_title = 'Barcode Generation';

      vm.model_data['barcodes'] = [];

      angular.forEach(vm.model_data.data, function(barcode_data){

        var quant = barcode_data[0].value;

        var sku_det = barcode_data[0].wms_code;

        vm.model_data['barcodes'].push({'sku_code': sku_det, 'quantity': quant})

      })

      vm.model_data['format_types'] = ['format1', 'format2', 'format3']

      var key_obj = {'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details'}

      $state.go('app.inbound.RevceivePo.barcode');
    }

    vm.gen_barcode = function() {
      vm.barcode_title = 'Barcode Generation';
      vm.model_data['barcodes'] = [];

      angular.forEach(vm.model_data.data, function(barcode_data){
        var quant = barcode_data[0].value;
        var sku_det = barcode_data[0].wms_code;
        /*var list_of_sku = barcode_data[0].serial_number.split(',');

        angular.forEach(list_of_sku, function(serial) {
          console.log(vm.sku_det);
          var serial_number = vm.sku_det+'/00'+serial;
          vm.model_data['barcodes'].push({'sku_code': serial_number, 'quantity': 1})
        })*/
       vm.model_data['barcodes'].push({'sku_code': sku_det, 'quantity': quant})

      })

      vm.model_data['format_types'] = ['format1', 'format2', 'format3']
      var key_obj = {'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details'}
      $state.go('app.inbound.RevceivePo.barcode');
    }

    vm.vendor_receive = function(data) {

      if(data.$valid) {

        var elem = angular.element($('form'));
        elem = elem[0];
        elem = $(elem).serializeArray();
        vm.service.apiCall("confirm_vendor_received/", 'GET', elem, true).then(function(data){

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

    //firebase integrations
    var fb = {};
    vm.fb = fb;

  function po_fb_functions() {

    fb["poData"] = {serials: []};
    fb["generate"] = false;

    fb["exists"] = function(data) {
      var d = $q.defer();
      firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/").orderByChild("po").equalTo(data.po_reference).once("value", function(snapshot) {
        if(snapshot.val()) {
          var po = {}
          angular.forEach(snapshot.val(), function(data,v){
            po = data;
            po['id'] = v;
          })
          d.resolve({status: true, data: po});
        } else {
          d.resolve({status: false});
        }
      });
      return d.promise;
    }

    fb["push"] = function(data){
      var po = {};
      po["po"] = data.po_reference;
      po["serials"] = "";
      angular.forEach(data.data, function(sku){
        po[sku[0].wms_code] = {};
        po[sku[0].wms_code]["quantity"] = sku[0].value;
        po[sku[0].wms_code]["wms_code"] = sku[0].wms_code;
        po[sku[0].wms_code]["serials"] = "";
      })
      console.log(po);
      firebase.database().ref("/GenerateGRN/"+Session.parent.userId).push(po).then(function(data){
        console.log(data);
        fb.poData = po;
        fb.poData['id'] = data.path.o[2];
        console.log(fb.poData);
        fb.po_change_event();
        fb.po_generate_event();
      })
    }

    fb["push_po"] = function(data) {

      fb.exists(data).then(function(po){

        console.log(po);
        if(!po.status) {
          fb.push(data);
        } else {
          fb.poData = po.data;
          fb.change_po_data(fb.poData);
          fb.po_change_event();
          fb.po_generate_event();
        }
      })
    }

    fb["change_serial"] = function(data, serial) {

      console.log(data.wms_code, serial);
      firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ data.wms_code +"/serials/").push(serial);
      firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/"+vm.fb.poData.id+"/serials/").push(serial);
    }

    fb["change_po_data"] = function(data) {

      vm.fb.poData['serials'] = Object.values(vm.fb.poData['serials']);
      angular.forEach(vm.model_data.data, function(data){
        if(vm.fb.poData[data[0].wms_code]) {
          data[0].value = Object.keys(vm.fb.poData[data[0].wms_code]['serials']).length;
          data[0]['imei_list'] =  Object.values(vm.fb.poData[data[0].wms_code]['serials']);
        }
      })
    }

    fb["po_change_event"] = function() {

        firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/"+vm.fb.poData.id+"/").on("child_changed", function(sku) {
          console.log(sku.val());
          var response = sku.val();
          if(response["wms_code"]){

            for(var i=0; i < vm.model_data.data.length; i++) {

              if(response.wms_code == vm.model_data.data[i][0]['wms_code']) {
                vm.model_data.data[i][0]['value'] = Object.keys(response.serials).length;
                vm.model_data.data[i][0]['imei_list'] = Object.values(response.serials);
                vm.fb.poData[response.wms_code]['serials'] = Object.values(response.serials);
                $timeout(function() {
                  $scope.$apply();
                }, 500);
                break;
              }
            }
          } else {

            vm.fb.poData.serials = Object.values(response);
          }
        });
    }

    fb["po_generate_event"] = function() {

      firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/").on("child_removed", function(po) {

        var delete_po = po.val();
        if(fb.poData.po == delete_po["po"] && vm.model_data.po_reference == delete_po["po"]) {
          fb.poData = {};
          if (!(fb.generate)) {

             SweetAlert.swal({
               title: '',
               text: 'Generated GRN Successfully',
               type: 'success',
               showCancelButton: false,
               confirmButtonColor: '#33cc66',
               confirmButtonText: 'Ok',
               closeOnConfirm: true,
             },
             function (status) {
               vm.close();
               }
             );
            //vm.close();
          }
        }
        console.log(po);
      })
    }

    fb["remove_po"] = function(po) {

      if(po) {
        firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/"+po).once("value", function(data){
          data.ref.remove()
            .then(function() {
              console.log("Remove succeeded.")
            })
            .catch(function(error) {
              console.log("Remove failed: " + error.message)
            });
          console.log(data.ref.remove())
        })
      }
    }

    fb["stop_listening"] = function(po) {

      var data = po;

      firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/"+data.id+"/").off();
      firebase.database().ref("/GenerateGRN/"+Session.parent.userId+"/").off();
    }

    fb["stop_fb"] = function() {

      fb.stop_listening(fb.poData);
      fb["poData"] = {serials: []};
      fb["generate"] = false;
    }
  }


  function po_qc_fb_functions() {

    fb["poData"] = {serials: []};
    fb["generate"] = false;
    fb["add_new"] = false;

    fb["exists"] = function(data) {
      var d = $q.defer();
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/").orderByChild("po").equalTo(data.po_reference).once("value", function(snapshot) {
        if(snapshot.val()) {
          var po = {}
          angular.forEach(snapshot.val(), function(data,v){
            po = data;
            po['id'] = v;
          })
          d.resolve({status: true, data: po});
        } else {
          d.resolve({status: false});
        }
      });
      return d.promise;
    }

    fb["push"] = function(data){
      var po = {};
      po["po"] = data.po_reference;
      po["serials"] = "";
      angular.forEach(data.data, function(sku){
        var name = sku[0].wms_code;
        po[name] = {};
        po[name]["wms_code"] = sku[0].wms_code;
        po[name]["accepted"] = "";
        po[name]["rejected"] = "";
      })
      console.log(po);
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId).push(po).then(function(data){

        fb.poData = po;
        fb.poData['id'] = data.path.o[2];
        fb.delete_accept_serial(fb.poData);
        fb.added_reject_serial(fb.poData);
        fb.added_accept_serial(fb.poData);
        fb.qc_confirm_event();
        fb.change_po_data(fb.poData);
      })
    }

    fb["push_po"] = function(data) {
      angular.forEach(data.data, function(record){

        record[0]["accepted_quantity"] = 0;
        record[0]["rejected_quantity"] = 0;
        record[0]["accept_imei"] = [];
        record[0]["reject_imei"] = [];
      });
      fb.exists(data).then(function(po){

        console.log(po);
        if(!po.status) {
          fb.push(data);
        } else {
          fb.poData = po.data;
          fb.delete_accept_serial(fb.poData);
          fb.added_reject_serial(fb.poData);
          fb.added_accept_serial(fb.poData);
          fb.qc_confirm_event();
          fb.change_po_data(fb.poData);
        }
      })
    }

    fb["add_new"] = false;
    fb["change_po_data"] = function(data) {

      vm.fb.poData['serials'] = Object.values(vm.fb.poData['serials']);
      vm.imei_list = vm.fb.poData['serials'];
      angular.forEach(vm.model_data.data, function(data){
        var name= data[0].wms_code;
        if(vm.fb.poData[name]) {
          if(!vm.fb.poData[name]['accepted']){vm.fb.poData[name]['accepted'] = {}}
          if(!vm.fb.poData[name]['rejected']){vm.fb.poData[name]['rejected'] = {}}
          data[0].accepted_quantity = Object.keys(vm.fb.poData[name]['accepted']).length;
          data[0].rejected_quantity = Object.keys(vm.fb.poData[name]['rejected']).length;
          data[0].accept_imei =  Object.values(vm.fb.poData[name]['accepted']);
          data[0].reject_imei =  Object.values(vm.fb.poData[name]['rejected']);
          data[0].value = data[0].accepted_quantity + data[0].rejected_quantity;
          $timeout(function() {$scope.$apply();}, 500);
        }
      })
      fb.add_new = true;

    }

    fb["recent_accept"] = "";
    fb["accept_serial"] = function(data, serial) {

      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ data.wms_code +"/accepted/").push(serial).then(function(snapshot){

        fb["recent_accept"] = snapshot.path.o[5];
      });
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/serials/").push(serial);
    }

    fb["reject_serial"] = function(data, serial) {

      var name= data.wms_code;
      if(fb.recent_accept) {
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ name +"/accepted/"+fb.recent_accept).once("value", function(snapshot) {
          snapshot.ref.remove();
        })
      }
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ name +"/rejected/").push(serial);
      //firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/serials/").push(serial);
    }

    fb["remove_add_serial"] = function(data, serial1, serial2, remove_from, add_to) {

      var name= data.wms_code;
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ name +"/"+remove_from+"/").once("value", function(snapshot) {
        if(snapshot.val()) {
          var status = true;
          angular.forEach(snapshot.val(), function(value,key) {
            if(serial1 == value && status) {
              status = false;
              firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ name +"/"+remove_from+"/"+key).once("value", function(snapshot) {
                snapshot.ref.remove();
              })
            }
          })
        }
      })
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ name +"/"+add_to+"/").push(serial2);
    }

    fb["delete_accept_serial"] = function() {

      angular.forEach(vm.fb.poData, function(value, key) {
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+key + "/accepted/").on("child_removed", function(snapshot) {
          if(snapshot.V.path.o[4] == "accepted") {

            if(vm.model_data['data']) {
              var sku_data = snapshot.V.path.o[3];
              for(var i=0; i < vm.model_data.data.length; i++) {

                var sku = vm.model_data.data[i][0];
                if(sku.wms_code == sku_data) {

                  var imei = snapshot.val();
                  var index = sku.accept_imei.indexOf(imei);
                  if(index != -1) {
                    vm.model_data.data[i][0].accept_imei.splice(index, 1);
                    vm.model_data.data[i][0].accepted_quantity -= 1;
                    vm.model_data.data[i][0].value = vm.model_data.data[i][0].accepted_quantity + vm.model_data.data[i][0].rejected_quantity;
                    $timeout(function() {$scope.$apply();}, 500);
                  };
                  break;
                }
              }
            }
          }
        })
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+key + "/rejected/").on("child_removed", function(snapshot) {
          if(snapshot.V.path.o[4] == "rejected") {

            if(vm.model_data['data']) {
              var sku_data = snapshot.V.path.o[3];
              for(var i=0; i < vm.model_data.data.length; i++) {

                var sku = vm.model_data.data[i][0];
                if(sku.wms_code == sku_data) {

                  var imei = snapshot.val();
                  var index = sku.reject_imei.indexOf(imei);
                  if(index != -1) {
                    vm.model_data.data[i][0].reject_imei.splice(index, 1);
                    vm.model_data.data[i][0].rejected_quantity -= 1;
                    vm.model_data.data[i][0].value = vm.model_data.data[i][0].accepted_quantity + vm.model_data.data[i][0].rejected_quantity;
                    $timeout(function() {$scope.$apply();}, 500);
                  };
                  break;
                }
              }
            }
          }
        })
      })
    }

    fb["added_reject_serial"] = function() {

      angular.forEach(vm.fb.poData, function(value, key) {
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ key + "/rejected/" ).on("child_added", function(snapshot) {
          if(snapshot.V.path.o[4] == "rejected" && fb.add_new) {

            var sku_data = snapshot.V.path.o[3];
            for(var i=0; i < vm.model_data.data.length; i++) {

              var sku = vm.model_data.data[i][0];
              if(sku.wms_code == sku_data) {

                var imei = snapshot.val();
                var index = sku.reject_imei.indexOf(imei);
                if(index == -1) {
                  vm.model_data.data[i][0].reject_imei.push(imei);
                  vm.model_data.data[i][0].rejected_quantity += 1;
                  vm.model_data.data[i][0].value = vm.model_data.data[i][0].accepted_quantity + vm.model_data.data[i][0].rejected_quantity;
                  $timeout(function() {$scope.$apply();}, 500);
                }
                break;
              }
            }
          }
        })
      })
    }

    fb["added_accept_serial"] = function() {

      angular.forEach(vm.fb.poData, function(value, key) {
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ key + "/accepted/" ).on("child_added", function(snapshot) {
          if(snapshot.V.path.o[4] == "accepted" && fb.add_new) {

            var sku_data = snapshot.V.path.o[3];
            for(var i=0; i < vm.model_data.data.length; i++) {

              var sku = vm.model_data.data[i][0];
              if(sku.wms_code == sku_data) {

                var imei = snapshot.val();
                var index = sku.accept_imei.indexOf(imei);
                if(index == -1) {
                  vm.model_data.data[i][0].accept_imei.push(imei);
                  vm.model_data.data[i][0].accepted_quantity += 1;
                  vm.model_data.data[i][0].value = vm.model_data.data[i][0].accepted_quantity + vm.model_data.data[i][0].rejected_quantity;
                  $timeout(function() {$scope.$apply();}, 500);
                }
                break;
              }
            }
          }
        })
      })
    }

    fb["qc_confirm_event"] = function() {

      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/").on("child_removed", function(po) {

        var delete_po = po.val();
        if(fb.poData.po == delete_po["po"] && vm.model_data.po_reference == delete_po["po"]) {
          fb.poData = {};
          if (!(fb.generate)) {

             fb.stop_listening(delete_po["po"]);
             SweetAlert.swal({
               title: '',
               text: 'Receiv+QC confirmed Successfully',
               type: 'success',
               showCancelButton: false,
               confirmButtonColor: '#33cc66',
               confirmButtonText: 'Ok',
               closeOnConfirm: true,
             },
             function (status) {
               vm.close();
               }
             );
            //vm.close();
          }
        }
        console.log(po);
      })
    }

    fb["remove_po"] = function(po) {

      if(po) {
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+po).once("value", function(data){
          data.ref.remove()
            .then(function() {
              console.log("Remove succeeded.")
            })
            .catch(function(error) {
              console.log("Remove failed: " + error.message)
            });
          console.log(data.ref.remove())
        })
      }
    }

    fb["stop_listening"] = function(po) {

      var data = po;
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+data.id).off();
      firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/").off();

      angular.forEach(data, function(value, key) {
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+data.id+"/"+key + "/").off();
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+data.id+"/"+ key + "/rejected/" ).off();
        firebase.database().ref("/ReceiveQC/"+Session.parent.userId+"/"+data.id+"/"+ key + "/accepted/" ).off();
      })
    }

    fb["stop_fb"] = function() {

      fb.stop_listening(fb.poData);
      fb["poData"] = {serials: []};
      fb["generate"] = false;
      fb["add_new"] = false;
    }
  }

  if(vm.po_qc) {
    po_qc_fb_functions();
  } else {
    po_fb_functions();
  }

  vm.accept_qc = function(data, field) {

      vm.enable_button = false;
      var sku = vm.model_data.data[vm.current_index][0];
      sku.accepted_quantity = Number(sku.accepted_quantity) + 1;
      sku.value = Number(sku.value) + 1;

      sku["accept_imei"].push(field);
      vm.model_data.data[vm.current_index][0] = sku

      fb.accept_serial(sku, field);
      vm.serial_scan = "";
    }

    vm.selected = "";
    vm.reject_qc = function(imei) {

      vm.reason_show = false;
      var sku = vm.model_data.data[vm.current_index][0];
      var field = "";
      if(!imei) {

        sku.accepted_quantity = Number(sku.accepted_quantity) - 1;
        var index = sku["accept_imei"].length-1;
        var field = sku["accept_imei"][index].split("<<>>")[0];
        sku["accept_imei"].splice(index,1);
      } else {
        field = imei;
      }
      sku.rejected_quantity = Number(sku.rejected_quantity) + 1;

      if(!(sku["reject_imei"])) {
        sku["reject_imei"] = [];
      }
      var imei = field+"<<>>"+vm.selected;
      sku["reject_imei"].push(imei);

      if(vm.permissions.use_imei) {
        fb.reject_serial(sku, imei);
      }

      vm.selected="";
      focus('focusIMEI');
    }

    vm.status_imei = "";
    vm.status_scan_imei = function(event, field) {
      if ( event.keyCode == 13 && field.length > 0) {
        vm.enable_button = true;
        vm.reason_show = false;
        var data = {imei: field, order_id: vm.model_data.order_id};
        if(vm.imei_list.indexOf(field) != -1) {
          vm.status_move_imei(field);
        } else {
          vm.service.apiCall('check_imei_qc/', 'GET', data).then(function(data){
            if(data.data.status == "") {

              vm.service.showNoty("Yet to scan IMEI")
            } else {

              vm.service.showNoty(data.data.status);
            }
          })
        }
        vm.status_imei = "";
      }
    }

    vm.status_move_imei = function(field) {

      for(var i = 0; i < vm.model_data.data.length; i++) {

        var data = vm.model_data.data[i][0];
        var reject = vm.status_ac_rj(field, data.reject_imei);
        var accept = vm.status_ac_rj(field, data.accept_imei);
        if(reject != -1) {

          vm.status_imei_here(i, reject, "reject_imei", field);
          vm.current_index = i;
          vm.model_data1["sku_data"] = data.sku_details[0].fields;
          break;
        } else if(accept != -1) {

          vm.current_index = i;
          vm.model_data1["sku_data"] = data.sku_details[0].fields;
          vm.status_imei_here(i, accept, "accept_imei", field);
          break;
        }
      }
    }

    vm.status_imei_here = function(index1, index2, from_data, field) {

      var msg = "Accepted. Move to Reject State?"
      if(from_data == "reject_imei") {
        msg = "Rejected. Move to Accept State?"


        $timeout(function() {
          swal2({
            title: '',
            text: 'Rejected. Move to Accept State?',
            showCancelButton: true,
          }).then(function (result) {
            var serial1 = vm.model_data.data[index1][0][from_data][index2];
            vm.model_data.data[index1][0][from_data].splice(index2, 1);
            var from = "rejected";
            var to = "accepted";
            vm.model_data.data[index1][0].rejected_quantity -= 1;
            var serial2 = serial1.split("<<>>");
            serial2 = serial2[0]
            fb.remove_add_serial(vm.model_data.data[index1][0], serial1, serial2, from, to)
           });
         }, 100);

      } else {
        vm.model_data.reasons = {};
        angular.forEach(vm.model_data.options, function(reason){
          vm.model_data.reasons[reason] = reason;
        })
        $timeout(function() {
          swal2({
            title: '',
            text: 'Accepted. Move to Reject State?',
            input: 'select',
            inputOptions: vm.model_data.reasons,
            inputPlaceholder: 'Select Reason',
            showCancelButton: true,
          }).then(function (result) {
            var serial1 = vm.model_data.data[index1][0][from_data][index2];
            vm.model_data.data[index1][0][from_data].splice(index2, 1);
            var to = "rejected";
            var from = "accepted";
            vm.model_data.data[index1][0].accepted_quantity -= 1;
            var serial2 = serial1.split("<<>>");
            serial2 = serial2[0]+"<<>>"+result;
            fb.remove_add_serial(vm.model_data.data[index1][0], serial1, serial2, from, to)
          })
        },100);
      }
    }

    vm.status_ac_rj = function(field, data){

      var index = -1;
      for(var i = 0; i < data.length; i++) {

        if(field == data[i].split("<<>>")[0]) {

          index = i;
          break;
        }
      }
      return index;
    }
}
