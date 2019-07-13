'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('QualityCheckCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.industry_type = Session.user_profile.industry_type;
    vm.extra_width = {};
    vm.qc_invoice_data = {}
    vm.quantity_focused = false;

    vm.filters = {'datatable': 'QualityCheck', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': ''}
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
       .withOption('order', [1, 'desc'])
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

    var columns = ['Purchase Order ID', 'Supplier ID', 'Supplier Name', 'Order Type', 'Total Quantity']
    vm.dtColumns = vm.service.build_colums(columns);

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.reloadData();
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.service.apiCall('quality_check_data/', 'GET', {order_id: aData.DT_RowId}).then(function(data){
                  if(data.message) {
                    vm.qc_invoice_data = {}
                    vm.qc_invoice_data = aData
                    if(vm.industry_type == 'FMCG'){
                      vm.extra_width = {
                        'width': '1200px'
                      };
                    } else {
                      vm.extra_width = {};
                    }
                    angular.copy(data.data, vm.model_data);
                    vm.model_data.updated_skus = {};
                    angular.forEach(vm.model_data.data ,function(record){

                      record["accept_imei"] = [];
                      record["reject_imei"] = [];

                      if (vm.model_data.updated_skus[record.wms_code]) {

                        vm.model_data.updated_skus[record.wms_code].quantity = Number(vm.model_data.updated_skus[record.wms_code].quantity) + Number(record.quantity)
                      } else {

                        vm.model_data.updated_skus[record.wms_code] = record;
                      }
                    });
                    if(vm.permissions.use_imei) {
                      fb.push_po(vm.model_data);
                    }
                    $state.go('app.inbound.QualityCheck.qc');
                    vm.bt_enable = false;
                    vm.confirm_btn = false;
                  }
                });
            });
        });
        if(vm.filter_enable){
          vm.filter_enable = false;
          vm.apply_filters.add_search_boxes();
        }
        return nRow;
    }

    vm.filter_enable = true;
    vm.bt_enable = false;
    var empty_data ={};
    vm.model_data = {};
    angular.copy(empty_data, vm.model_data);

    vm.close = close;
    function close() {

      angular.copy(empty_data, vm.model_data);
      vm.imei_list = [];
      if(vm.permissions.use_imei) {
        $timeout(function() {
          fb.stop_fb();
        }, 1000);
      }
      $state.go('app.inbound.QualityCheck');
    }

    vm.qc_close = qc_close;
    function qc_close() {

      $state.go('app.inbound.QualityCheck.qc');
    }

    vm.qc_details = qc_details;
    function qc_details() {
      $state.go('app.inbound.QualityCheck.qc_detail');
    }

    vm.get_current_weight = function(event, data, index) {
      if(vm.permissions.weight_integration_name.length > 0) {
        vm.service.apiCall('get_current_weight/', 'GET',{}).then(function(res_data){
          if(res_data.message){
            if(res_data.data.status && res_data.data.is_updated){
              if(res_data.data.weight >data.data[index].quantity)
              {
                vm.service.showNoty('Weighed Quantity is Greater than QC Qunatity '+data.data[index].quantity);
              }
              else
              {
               data.data[index].accepted_quantity = res_data.data.weight;
              }
            }
            if (data.data[index].accepted_quantity){
              data.data[index].rejected_quantity = data.data[index].quantity - data.data[index].accepted_quantity
            }
            else{
              data.data[index].rejected_quantity = 0
            }
            if(vm.quantity_focused) {
              setTimeout(function(){ vm.get_current_weight(event, data, index, parent_index); }, 1000);
            }
          }
        });
      }
    }

    vm.getSku = function (field) {
      vm.service.apiCall('create_orders_check_ean/', 'GET', {'ean': field}).then(function(data) {
        if(data.message) {
  		    if(data.data.sku) {
            return data.data.sku;
          } else {
            return field;
          }
        }
      })
    }

    vm.scan_sku = function(event, field) {
      if ( event.keyCode == 13 && field.length > 0) {
        console.log(field);

        vm.service.apiCall('create_orders_check_ean/', 'GET', {'ean': field}).then(function(data) {
          if(data.message) {
    		    if(data.data.sku) {
              field = data.data.sku;
            }
          }
          var data = [{name: field, value: vm.model_data.po_reference}];
          vm.service.apiCall('check_wms_qc/', 'POST', data).then(function(data){
            if(data.message) {
              if ('WMS Code not found'==data.data) {
                 pop_msg(data.data);
              } else {

                for(var i=0;vm.model_data.data.length; i++) {
                  if(vm.model_data.data[i].wms_code == data.data.sku_data['SKU Code']) {

                    vm.model_data.data[i].acc_qty = false;
                    vm.current_index = i;
                    var temp = Number(vm.model_data.data[i].accepted_quantity) + 1;
                    if (Number(vm.model_data.data[i].accepted_quantity) < Number(vm.model_data.data[i].quantity)) {

                      vm.model_data.data[i].accepted_quantity = Number(vm.model_data.data[i].accepted_quantity) + 1;
                    }

                    if (Number(vm.model_data.data[i].quantity) == Number(vm.model_data.data[i].accepted_quantity)) {

                      vm.model_data.data[i].acc_qty = true;
                    }

                    if (temp > Number(vm.model_data.data[i].accepted_quantity)) {

                      vm.model_data.data[i].acc_qty = true;
                      vm.service.showNoty("You don't have quantity in "+vm.model_data.data[i].wms_code+" SKU");
                    }

                    break;
                  }
                }
                vm.model_data1 = data.data;
                qc_details();
              }
            }
          });
        });
        vm.scan = '';
      }
    }

    vm.checkQty = function(sku){

      if (Number(sku.accepted_quantity) > Number(sku.quantity)) {

        sku.accepted_quantity = sku.quantity;
        vm.service.showNoty("You will enter only <b>"+sku.quantity+"</b> quantity");
      }
      if (Number(sku.accepted_quantity)){
        sku.rejected_quantity = sku.quantity - sku.accepted_quantity
      }
      else{
        sku.rejected_quantity = 0
      }
    }

    vm.imei_sku = "";
    vm.imei_list = [];
    vm.wait_imei = "";
    vm.scan_imei = function(event, field) {
      if ( event.keyCode == 13 && field.length > 0) {
        field = field.toUpperCase();
        if(vm.imei_list.indexOf(field) == -1) {
          var data = {imei: field, order_id: vm.model_data.order_id};
          vm.service.apiCall('check_imei_qc/', 'GET', data).then(function(data){
            if(data.message) {
              console.log(data.data)
              if ($state.$current.name == 'app.inbound.QualityCheck.qc_detail' && data.data.status == "") {
                /*if (vm.model_data1.sku_data['SKU Code'] == data.data.sku_data['SKU Code']) {
                  vm.imei_list.push(field);
                  vm.accept_qc(field);
                } else {
                  vm.update_details(vm.current_details, false);
                  generate_details_data(data.data.sku_data['SKU Code']);
                  vm.model_data1 = data.data;
                  vm.imei_list.push(field);
                  vm.accept_qc(field);
                }*/
                generate_details_data(data.data.sku_data['SKU Code']).then(function(status){
                  console.log(status);
                  if(status) {
                    vm.model_data1 = data.data;
                    vm.imei_list.push(field);
                    vm.accept_qc(field);
                  }
                })
              } else if(data.data.status) {
                vm.service.showNoty(data.data.status);
              } else {

                generate_details_data(data.data.sku_data['SKU Code']).then(function(status){
                  if(status) {
                    vm.model_data1 = data.data;
                    qc_details();
                    vm.imei_list.push(field);
                    vm.accept_qc(field);
                  }
                });
              }
            }
          })
        } else {
          vm.service.showNoty("IMEI already scanned");
        }
        vm.serial_scan = "";
        vm.imei_number = "";
      }
    }

    vm.current_index = "";
    function generate_details_data(field) {
      var d = $q.defer();
      if(vm.current_index == "") {

        d.resolve(change_current_index(field))
      } else {

        if(vm.model_data.data[vm.current_index].wms_code == field) {

          var sku = vm.model_data.data[vm.current_index];
          if(sku.quantity == (Number(sku.accepted_quantity) + Number(sku.rejected_quantity))) {

            d.resolve(change_current_index(field))
          } else {

            d.resolve(true);
          }
        } else {

          d.resolve(change_current_index(field))
        }
      }
      return d.promise;
    }

    function change_current_index(field) {

      var status = false;
      var sku_status = false;
      for(var i = 0; i < vm.model_data.data.length; i++) {

        if(vm.model_data.data[i].wms_code == field) {

          sku_status = true;
          var sku = vm.model_data.data[i];
          if(sku.quantity > (Number(sku.accepted_quantity) + Number(sku.rejected_quantity))) {
            vm.current_index = i;
            status = true;
            break;
          }
        }
      }
      if(sku_status && (!status)) {

        vm.service.showNoty(field+" SKU quantity equal to accepted quantity");
        return false;
      } else if(!status) {

        vm.service.showNoty("Entered Imei Number Not Matched With Any SKU's");
        return false;
      } else {
        return true;
      }
    }

   vm.update_details = function(data, state) {
     $state.go('app.inbound.QualityCheck.qc');
   }

    vm.model_data1 = {};
    vm.current_details = {};

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 2000);
    }
    vm.print_enable = false;

    vm.confirm = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      //var qc_scan = JSON.stringify(vm.qc_scan);
      //elem.push({name:'qc_scan', value: qc_scan})
      elem.push({name:'headers', value: JSON.stringify(vm.qc_invoice_data)})
      vm.service.apiCall('confirm_quality_check/', 'POST', elem, true).then(function(data){
        if(data.message) {
          if (data.data == "Updated Successfully") {
            reloadData();
            fb.generate = true;
            if(vm.permissions.use_imei) {
              fb.generate = true;
              //fb.stop_listening(fb.poData);
              fb.remove_po(fb.poData["id"]);
            }
          }
          else if (data.data.search("<div") != -1){
            vm.pdf_data = data.data;
            $state.go("app.inbound.QualityCheck.qc_print");
            $timeout(function () {
              $(".modal-body:visible").html(vm.pdf_data)
              }, 3000);
          }
            else {
            pop_msg(data.data);
          }
        }
      });

    }



    vm.print_grn = function() {
      vm.service.print_data(vm.html, "Quality Check");
    }

    vm.confirm_btn = false;
    vm.reason_show = false;
    vm.enable_button = true;
    vm.show_serial = true;;

    vm.accept_qc = function(field, status_imei) {

      if(!status_imei) {
        vm.enable_button = false;
      }
      var sku = vm.model_data.data[vm.current_index];
      sku.accepted_quantity = Number(sku.accepted_quantity) + 1;

      if(!(sku["accept_imei"])) {
        sku["accept_imei"] = [];
      }
      sku["accept_imei"].push(field+"<<>>"+sku.id+"<<>>");
      vm.model_data.data[vm.current_index] = sku

      if(vm.permissions.use_imei) {
        fb.accept_serial(sku, field+"<<>>"+sku.id+"<<>>");
      }
    }

    vm.reject_qc = function(imei) {

      vm.reason_show = false;
      var sku = vm.model_data.data[vm.current_index];
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
      var imei = field+"<<>>"+sku.id+"<<>>"+vm.selected;
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
        field = field.toUpperCase();
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
                 var serial1 = vm.model_data.data[index1][from_data][index2];
                 vm.model_data.data[index1][from_data].splice(index2, 1);
                 var from = "rejected";
                 var to = "accepted";
                 vm.model_data.data[index1].rejected_quantity -= 1;
                 var serial2 = serial1.split("<<>>");
                 serial2 = serial2[0]+"<<>>"+serial2[1]
                 fb.remove_add_serial(vm.model_data.data[index1], serial1, serial2, from, to)
             });
      }, 100);

      } else {
              vm.model_data1.reasons = {};
              angular.forEach(vm.model_data1.options, function(reason){
                vm.model_data1.reasons[reason] = reason;
              })
$timeout(function() {
swal2({
  title: '',
  text: 'Accepted. Move to Reject State?',
  input: 'select',
  inputOptions: vm.model_data1.reasons,
  inputPlaceholder: 'Select Reason',
  showCancelButton: true,
}).then(function (result) {

                 var serial1 = vm.model_data.data[index1][from_data][index2];
                 vm.model_data.data[index1][from_data].splice(index2, 1);
                 var to = "rejected";
                 var from = "accepted";
                 vm.model_data.data[index1].accepted_quantity -= 1;
                 var serial2 = serial1.split("<<>>");
                 serial2 = serial2[0]+"<<>>"+serial2[1]+"<<>>"+result;
                 fb.remove_add_serial(vm.model_data.data[index1], serial1, serial2, from, to)

})
},100);
      }

    }

    vm.status_move_imei = function(field) {

      for(var i = 0; i < vm.model_data.data.length; i++) {

        var data = vm.model_data.data[i];
        var reject = vm.status_ac_rj(field, data.reject_imei);
        var accept = vm.status_ac_rj(field, data.accept_imei);
        if(reject != -1) {

          vm.status_imei_here(i, reject, "reject_imei", field);
          break;
        } else if(accept != -1) {

          vm.status_imei_here(i, accept, "accept_imei", field);
          break;
        }
      }
    }

    //firebase integrations
    var fb = {};
    //var fb_empty = {poData: {serials: []}, generate: false, add_new: false}
    vm.fb = fb;
    //angular.copy(fb_empty, fb);
    fb["poData"] = {serials: []};
    fb["generate"] = false;
    fb["add_new"] = false;

    fb["exists"] = function(data) {
      var d = $q.defer();
      firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/").orderByChild("po").equalTo(data.po_reference).once("value", function(snapshot) {
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
        var name = sku.wms_code+"<<>>"+ sku.location+ "<<>>" + sku.id;
        po[name] = {};
        po[name]["wms_code"] = sku.wms_code;
        po[name]["accepted"] = "";
        po[name]["rejected"] = "";
      })
      console.log(po);
      firebase.database().ref("/QualityCheck/"+Session.parent.userId).push(po).then(function(data){

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
      //vm.imei_list = Object.values(vm.fb.poData['serials']);
      angular.forEach(vm.model_data.data, function(data){
        var name= data.wms_code+"<<>>"+ data.location+ "<<>>" + data.id;
        if(vm.fb.poData[name]) {
          if(!vm.fb.poData[name]['accepted']){vm.fb.poData[name]['accepted'] = {}}
          if(!vm.fb.poData[name]['rejected']){vm.fb.poData[name]['rejected'] = {}}
          data.accepted_quantity = Object.keys(vm.fb.poData[name]['accepted']).length;
          data.rejected_quantity = Object.keys(vm.fb.poData[name]['rejected']).length;
          data.accept_imei =  Object.values(vm.fb.poData[name]['accepted']);
          data.reject_imei =  Object.values(vm.fb.poData[name]['rejected']);
          $timeout(function() {$scope.$apply();}, 500);
        }
      })
      fb.add_new = true;

      /*firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+vm.fb.poData.id+"/").on("child_changed", function(sku) {

        if(sku.V.path.o[3] == "serials") {
          vm.fb.poData['serials'] = Object.values(sku.val());
          vm.imei_list = vm.fb.poData['serials'];
        }
      })*/
    }

    fb["recent_accept"] = "";
    fb["accept_serial"] = function(data, serial) {

      var name= data.wms_code+"<<>>"+ data.location+ "<<>>" + data.id;
      firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ name +"/accepted/").push(serial).then(function(snapshot){

        fb["recent_accept"] = snapshot.path.o[5];
      });
      firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+vm.fb.poData.id+"/serials/").push(serial.split("<<>>")[0]);
    }

    fb["reject_serial"] = function(data, serial) {

      var name= data.wms_code+"<<>>"+ data.location+ "<<>>" + data.id;
      if(fb.recent_accept) {
        firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ name +"/accepted/"+fb.recent_accept).once("value", function(snapshot) {
          snapshot.ref.remove();
        })
      }
      firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ name +"/rejected/").push(serial);
      firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+vm.fb.poData.id+"/serials/").push(serial.split("<<>>")[0]);
    }

    fb["remove_add_serial"] = function(data, serial1, serial2, remove_from, add_to) {

      var name= data.wms_code+"<<>>"+ data.location+ "<<>>" + data.id;
      firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ name +"/"+remove_from+"/").once("value", function(snapshot) {
        if(snapshot.val()) {
          var status = true;
          angular.forEach(snapshot.val(), function(value,key) {
            if(serial1 == value && status) {
              status = false;
              firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ name +"/"+remove_from+"/"+key).once("value", function(snapshot) {
                snapshot.ref.remove();
              })
            }
          })
        }
      })
      firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ name +"/"+add_to+"/").push(serial2);
    }

    fb["delete_accept_serial"] = function() {

      angular.forEach(vm.fb.poData, function(value, key) {
        firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+key + "/accepted/").on("child_removed", function(snapshot) {
          if(snapshot.V.path.o[4] == "accepted") {

            if(vm.model_data['data']) {
              var sku_data = snapshot.V.path.o[3].split("<<>>");
              for(var i=0; i < vm.model_data.data.length; i++) {

                var sku = vm.model_data.data[i];
                if(sku.wms_code == sku_data[0] && sku.location == sku_data[1] && sku.id == sku_data[2]) {

                  var imei = snapshot.val();
                  var index = sku.accept_imei.indexOf(imei);
                  if(index != -1) {
                    vm.model_data.data[i].accept_imei.splice(index, 1);
                    vm.model_data.data[i].accepted_quantity -= 1;
                    $timeout(function() {$scope.$apply();}, 500);
                  };
                  break;
                }
              }
            }
          }
        })
        firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+key + "/rejected/").on("child_removed", function(snapshot) {
          if(snapshot.V.path.o[4] == "rejected") {

            if(vm.model_data['data']) {
              var sku_data = snapshot.V.path.o[3].split("<<>>");
              for(var i=0; i < vm.model_data.data.length; i++) {

                var sku = vm.model_data.data[i];
                if(sku.wms_code == sku_data[0] && sku.location == sku_data[1] && sku.id == sku_data[2]) {

                  var imei = snapshot.val();
                  var index = sku.reject_imei.indexOf(imei);
                  if(index != -1) {
                    vm.model_data.data[i].reject_imei.splice(index, 1);
                    vm.model_data.data[i].rejected_quantity -= 1;
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
        firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ key + "/rejected/" ).on("child_added", function(snapshot) {
          if(snapshot.V.path.o[4] == "rejected" && fb.add_new) {

            var sku_data = snapshot.V.path.o[3].split("<<>>");
            for(var i=0; i < vm.model_data.data.length; i++) {

              var sku = vm.model_data.data[i];
              if(sku.wms_code == sku_data[0] && sku.location == sku_data[1] && sku.id == sku_data[2]) {

                var imei = snapshot.val();
                var index = sku.reject_imei.indexOf(imei);
                if(index == -1) {
                  vm.model_data.data[i].reject_imei.push(imei);
                  vm.model_data.data[i].rejected_quantity += 1;
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
        firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+vm.fb.poData.id+"/"+ key + "/accepted/" ).on("child_added", function(snapshot) {
          if(snapshot.V.path.o[4] == "accepted" && fb.add_new) {

            var sku_data = snapshot.V.path.o[3].split("<<>>");
            for(var i=0; i < vm.model_data.data.length; i++) {

              var sku = vm.model_data.data[i];
              if(sku.wms_code == sku_data[0] && sku.location == sku_data[1] && sku.id == sku_data[2]) {

                var imei = snapshot.val();
                var index = sku.accept_imei.indexOf(imei);
                if(index == -1) {
                  vm.model_data.data[i].accept_imei.push(imei);
                  vm.model_data.data[i].accepted_quantity += 1;
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

      firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/").on("child_removed", function(po) {

        var delete_po = po.val();
        if(fb.poData.po == delete_po["po"] && vm.model_data.po_reference == delete_po["po"]) {
          fb.poData = {};
          if (!(fb.generate)) {

             fb.stop_listening(delete_po["po"]);
             SweetAlert.swal({
               title: '',
               text: 'QC confirmed Successfully',
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
        firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+po).once("value", function(data){
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
      fb.stop_listening(fb.poData);
    }

    fb["stop_listening"] = function(po) {

      var data = po;
      firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+data.id).off();
      firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/").off();

      angular.forEach(data, function(value, key) {
        firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+data.id+"/"+key + "/").off();
        firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+data.id+"/"+ key + "/rejected/" ).off();
        firebase.database().ref("/QualityCheck/"+Session.parent.userId+"/"+data.id+"/"+ key + "/accepted/" ).off();
      })
    }

    fb["stop_fb"] = function() {

      fb.stop_listening(fb.poData);
      fb["poData"] = {serials: []};
      fb["generate"] = false;
      fb["add_new"] = false;
    }
  }
