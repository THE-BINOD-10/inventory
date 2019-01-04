'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SkuPackMasterTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    // vm.priceband_sync = Session.roles.permissions.priceband_sync;
    // vm.display_sku_cust_mapping = Session.roles.permissions.display_sku_cust_mapping;

    vm.filters = {'datatable': 'SKUPackMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    vm.dtColumns = [
        DTColumnBuilder.newColumn('sku').withTitle('Sku Code'),
        DTColumnBuilder.newColumn('pack_id').withTitle('Pack ID'),
        DTColumnBuilder.newColumn('pack_quantity').withTitle('Pack Quantity'),
    ];

    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                angular.copy(aData, vm.model_data);
                vm.update = true;
                vm.title = "Update SkuPack";
                vm.message ="";
                $state.go('app.masters.SkuPackMaster.skupack');
                $timeout(function () {
                  $(".customer_status").val(vm.model_data.status);
                }, 500);
            });
        });
    }

  vm.status_data = ["Inactive", "Active"];
  vm.customer_roles = ["User", "HOD", "Admin"];
  var empty_data = {sku: "", pack_id: "",pack_quantity: ""};
  vm.model_data = {};

  vm.base = function() {

    vm.title = "Add SkuPack";
    vm.update = false;
    angular.copy(empty_data, vm.model_data);
    vm.model_data.status = vm.status_data[1];
    vm.model_data.role = vm.customer_roles[0];
  }
  vm.base();

  vm.close = function() {

    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.SkuPackMaster');
  }

  vm.get_customer_id = function() {

    vm.service.apiCall("get_customer_master_id/").then(function(data){
      if(data.message) {

        vm.model_data["customer_id"] = data.data.customer_id;
        vm.all_taxes = data.data.tax_data;
        vm.model_data["price_type_list"] = data.data.price_types;
        vm.model_data["logged_in_user_type"] = data.data.logged_in_user_type;
        vm.model_data["level_2_price_type"] = data.data.level_2_price_type;
        vm.model_data["price_type"] = data.data.price_type;
      }
    });
  }
  vm.get_customer_id();

  vm.add = add;
  function add() {

    vm.base();
    // vm.get_customer_id();
    $state.go('app.masters.SkuPackMaster.skupack');
  }

  vm.skupack_insert = function(url) {
    var send = {}
    //angular.copy(vm.model_data, send)
    //if(send.login_created) {
    //    send.create_login = false;
    //}
    var send = $("form").serializeArray()
    var data = $.param(send);
    vm.service.apiCall(url, 'POST', send, true).then(function(data){
      if(data.message) {
        if(data.data == 'Added Successfully' || data.data == 'Updated Successfully') {
          vm.service.refresh(vm.dtInstance);
          vm.close();
        } else {
          vm.service.pop_msg(data.data);
        }
      }
    });
  }

  vm.submit = function(data) {

    if (data.$valid) {
      if ("Add SkuPack" == vm.title) {
        vm.skupack_insert('insert_sku_pack/');
      } else {
        vm.model_data['data-id'] = vm.model_data.DT_RowId;
        vm.skupack_insert('insert_sku_pack/');
      }
    }
  }
}
