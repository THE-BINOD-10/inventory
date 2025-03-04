'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('VehicleMasterTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$modal',ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $modal) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.priceband_sync = Session.roles.permissions.priceband_sync;
    vm.display_sku_cust_mapping = Session.roles.permissions.display_sku_cust_mapping;

    vm.filters = {'datatable': 'VehicleMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
        DTColumnBuilder.newColumn('customer_id').withTitle('Vehicle ID'),
        DTColumnBuilder.newColumn('name').withTitle('Vehicle Number'),
        DTColumnBuilder.newColumn('customer_type').withTitle('Type'),
        DTColumnBuilder.newColumn('city').withTitle('City'),
        DTColumnBuilder.newColumn('status').withTitle('Status').renderWith(function(data, type, full, meta) {
                        return vm.service.status(full.status);
                        }).withOption('width', '80px')
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
                vm.model_data['create_login'] = false;
                angular.copy(aData, vm.model_data);
                //vm.all_taxes = ['', 'VAT', 'CST']
                vm.update = true;
                vm.title = "Update Vehicle";
                vm.message ="";
                vm.service.apiCall('get_user_attributes_list', 'GET', {attr_model: 'customer'}).then(function(data){
                  vm.model_data.attributes = data.data.data;
                  angular.forEach(vm.model_data.attributes, function(attr_dat){
                  if(vm.model_data.customer_attributes[attr_dat.attribute_name])
                  {
                    attr_dat.attribute_value = vm.model_data.customer_attributes[attr_dat.attribute_name];
                  }
                  });
                });
                $state.go('app.masters.VehicleMaster.vehicle');
                $timeout(function () {
                  $(".customer_status").val(vm.model_data.status);
                }, 500);
            });
        });
    }

  vm.status_data = ["Inactive", "Active"];
  vm.customer_roles = ["User", "HOD", "Admin"];
  var empty_data = {customer_id: "", name: "", email_id: "", address: "", phone_number: "", status: "", create_login: false,
                    login_created: false, tax_type: "", margin: 0, customer_roles: ""};
  vm.model_data = {};

  vm.base = function() {

    vm.title = "Add Vehicle";
    vm.update = false;
    angular.copy(empty_data, vm.model_data);
    vm.model_data.status = vm.status_data[1];
    vm.model_data.role = vm.customer_roles[0];
  }
  vm.base();

  vm.close = function() {

    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.VehicleMaster');
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
    vm.get_customer_id();
    vm.service.apiCall('get_user_attributes_list', 'GET', {attr_model: 'customer'}).then(function(data){
      vm.model_data.attributes = data.data.data;
    });
    $state.go('app.masters.VehicleMaster.vehicle');
  }

  vm.customer = function(url) {
    var send = {}
    //angular.copy(vm.model_data, send)
    //if(send.login_created) {
    //    send.create_login = false;
    //}
    var send = $("form").serializeArray()
    var data = $.param(send);
    vm.service.apiCall(url, 'POST', send, true).then(function(data){
      if(data.message) {
        if(data.data == 'New Customer Added' || data.data == 'Updated Successfully') {
          vm.service.refresh(vm.dtInstance);
          vm.close();
        } else {
          vm.service.pop_msg(data.data.replace('Customer', 'Vehicle'));
        }
      }
    });
  }

  vm.submit = submit;
  function submit(data) {
    if (data.$valid) {
//      if (vm.model_data.tax_type) {
        if ("Add Vehicle" == vm.title) {
          vm.customer('insert_customer/');
        } else {
          vm.model_data['data-id'] = vm.model_data.DT_RowId;
          vm.customer('update_customer_values/');
        }
//      } else {
//        vm.service.pop_msg('Please select tax type');
//      }
    } else if (!(data.phone_number.$valid)) {
      vm.service.pop_msg('Invalid phone number');
    } else {
      vm.service.pop_msg('Please fill required fields');
    }
  }

  vm.addAttributes = function() {
    var send_data = {}
    angular.copy(vm.attr_model_data, send_data);
    var modalInstance = $modal.open({
      templateUrl: 'views/masters/toggles/attributes.html',
      controller: 'AttributesPOP',
      controllerAs: 'pop',
      size: 'lg',
      backdrop: 'static',
      keyboard: false,
      //windowClass: 'full-modal',
      resolve: {
        items: function () {
          return send_data;
        }
      }
    });

    modalInstance.result.then(function (result_dat) {
      vm.model_data.attributes = result_dat;
    });
  }

//    vm.service.apiCall('get_user_attributes_list', 'GET', {attr_model: 'customer'}).then(function(data){
//      vm.attributes = data.data.data;
//    });


}

