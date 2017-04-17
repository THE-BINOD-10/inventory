'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ReceivePOCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert) {
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
      fb.generate = false;
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
      vm.model_data.data.push([{"wms_code":"", "po_quantity":"", "receive_quantity":"", "price":"", "dis": false, "order_id": vm.model_data.data[0][0].order_id, is_new: true, "unit": ""}]);
      //vm.new_sku = true
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
      vm.service.apiCall('confirm_grn/', 'GET', elem, true).then(function(data){
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
                  $('input[value="'+vm.field+'"]').parents('tr').find("input[name='imei']").trigger('focus');
                }
              }
              if (vm.sku_list_1.indexOf(field) == -1){
                pop_msg(field+" Does Not Exist");
              }
              }
              else {
                vm.sku_list_1 = [];
                for(var i=0; i<vm.model_data.data.length; i++) {
                  vm.sku_list_1.push(vm.model_data.data[i][0]["wms_code"]);
                  if(vm.field == vm.model_data.data[i][0]["wms_code"]){
                    vm.model_data.data[i][0]["value"] = Number(vm.model_data.data[i][0]["value"]) + 1;
                    $('textarea[name="scan_sku"]').trigger('focus').val('');
                  }
                }
                if (vm.sku_list_1.indexOf(field) == -1){
                  pop_msg(field+" Does Not Exist");
                }
              }
           }
         });
        /*for(var i=0; i<vm.model_data.data.length; i++) {
          if(field == vm.model_data.data[i][0]["wms_code"]){
            //vm.model_data.data[i][0].value = vm.model_data.data[i][0].value + 1;
            //$('input[value="'+field+'"]').parents('tr').find("input[name='quantity']").trigger('focus');
            $('input[value="'+field+'"]').parents('tr').find("input[name='imei_number']").trigger('focus');
            console.log("success");
            break;
          }
        }*/
      }
    }

    vm.serial_numbers = [];
    vm.check_imei_exists = function(event, data1) {
      event.stopPropagation();
      if (event.keyCode == 13 && data1.imei_number.length > 0) {
        if (vm.serial_numbers.indexOf(data1.imei_number) != -1){
          vm.service.pop_msg("Serial Number already Exist");
          data1.imei_number = "";
          $('textarea[name="scan_sku"]').trigger('focus').val('');
        } else if (vm.fb.poData.serials.indexOf(data1.imei_number) != -1){
          vm.service.pop_msg("Serial Number already Exist");
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
              } else {
                pop_msg(data.data);
              }
              data1.imei_number = "";
            }
            $('textarea[name="scan_sku"]').trigger('focus').val('');
          });
        }
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

    //firebase integrations
    var fb = {};
    vm.fb = fb;
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
        if(fb.poData.po == delete_po["po"]) {
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
  }

