'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('QualityCheckCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.service = Service;
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
                    angular.copy(data.data, vm.model_data);
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

    vm.scan_sku = function(event, field) {
      if ( event.keyCode == 13 && field.length > 0) {
        console.log(field);
        var data = [{name: field, value: vm.model_data.po_reference}];
        vm.service.apiCall('check_wms_qc/', 'POST', data).then(function(data){
          if(data.message) {
            if ('WMS Code not found'==data.data) {
               pop_msg(data.data);
            } else {
              generate_details_data(field);
              vm.model_data1 = data.data;
              qc_details();
            }
          }
        });
        vm.scan = '';
      }
    }
 
    function generate_details_data(field) {
      for(var i=0;vm.model_data.data.length; i++) {
        if(vm.model_data.data[i].wms_code == field) {
          vm.current_details = {};
          angular.copy(vm.model_data.data[i],vm.current_details);
          break;
        }
      }
    }

   vm.update_details = function(data) {
     for(var i=0;vm.model_data.data.length; i++) {
        if(vm.model_data.data[i].wms_code == data.wms_code) {
          vm.model_data.data[i] = data;
          $state.go('app.inbound.QualityCheck.qc');
          break;
        }
      }
   }

    vm.model_data1 = {};
    vm.current_details = {};

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 2000);
    }

    vm.confirm = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      var qc_scan = JSON.stringify(vm.qc_scan);
      elem.push({name:'qc_scan', value: qc_scan})
      vm.service.apiCall('confirm_quality_check/', 'POST', elem).then(function(data){
        if(data.message) {
          if (data.data == "Updated Successfully") {
            reloadData();
            vm.close();
          } else {
            pop_msg(data.data);
          }
        }
      });  
    }

    vm.confirm_btn = false;
    vm.reason_show = false;
    vm.enable_button = true;
    vm.show_serial = true;;
    vm.scan_serial = function(event, field, id) {
      if ( event.keyCode == 13 && field.length > 0) {
        var data = [{name:'serial',value:field},{name:'id', value:id}]
        vm.service.apiCall('check_serial_exists/', 'POST', data).then(function(data){
          if(data.message) {
            if(data.data == "") {
              vm.enable_button = false;
            } else {
              pop_msg(data.data);
              vm.serial_scan = "";
            }
          }
        });
      }
    }

    vm.qc_scan = [];
    vm.add_qc_scan = function(type, sku, id, reason) {
      vm.qc_scan.push({type:sku+"<<>>"+id+"<<>>"+reason});
      vm.serial_scan = "";
      console.log(vm.qc_scan);
    }

    vm.accept_qc = function() {

      vm.add_qc_scan('accept',vm.serial_scan, vm.model_data1.data_dict[0].id, '');
      vm.current_details.accepted_quantity = parseInt(vm.current_details.accepted_quantity)+1;
      vm.enable_button = true;
      vm.show_serial = (vm.current_details.quantity == vm.current_details.accepted_quantity + vm.current_details.rejected_quantity)? false : true;
    }

    vm.reject_qc = function() {

      vm.add_qc_scan('accept',vm.serial_scan, vm.model_data1.data_dict[0].id, vm.selected);
      vm.reason_show = false;
      vm.current_details.rejected_quantity = parseInt(vm.current_details.rejected_quantity)+1;
      vm.show_serial = (vm.current_details.quantity == vm.current_details.accepted_quantity + vm.current_details.rejected_quantity)? false : true;
    }
  }

