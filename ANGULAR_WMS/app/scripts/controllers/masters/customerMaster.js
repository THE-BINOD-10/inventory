'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CustomerMasterTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.filters = {'datatable': 'CustomerMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
        DTColumnBuilder.newColumn('customer_id').withTitle('Customer ID'),
        DTColumnBuilder.newColumn('name').withTitle('Customer Name'),
        DTColumnBuilder.newColumn('email_id').withTitle('Email'),
        DTColumnBuilder.newColumn('phone_number').withTitle('Phone Number'),
        DTColumnBuilder.newColumn('address').withTitle('Address'),
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
                vm.update = true;
                vm.title = "Update Customer";
                vm.message ="";
                $state.go('app.masters.CustomerMaster.customer');
                $timeout(function () {
                  $(".customer_status").val(vm.model_data.status);
                }, 500);
            });
        });
    }

  vm.status_data = ["Inactive", "Active"];
  var empty_data = {customer_id: "", name: "", email_id: "", address: "", phone_number: "", status: "", create_login: false};
  vm.model_data = {};

  vm.base = function() {

    vm.title = "Add Customer";
    vm.update = false;
    angular.copy(empty_data, vm.model_data);
    vm.model_data.status = vm.status_data[1];
  }
  vm.base();

  vm.close = function() {

    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.CustomerMaster');
  }

  vm.add = add;
  function add() {

    vm.base();
    $state.go('app.masters.CustomerMaster.customer');
  } 

  vm.customer = function(url) {
    var data = $.param(vm.model_data);
    vm.service.apiCall(url, 'POST', vm.model_data).then(function(data){
      if(data.message) {
        if(data.data == 'New Customer Added' || data.data == 'Updated Successfully') {
          vm.service.refresh(vm.dtInstance);
          vm.close();
        } else {
          vm.service.pop_msg(data.data);
        }
      }
    });
  }

  vm.submit = submit;
  function submit(data) {
    if (data.$valid) {
      if ("Add Customer" == vm.title) {
        vm.customer('insert_customer/');
      } else {
        vm.model_data['data-id'] = vm.model_data.DT_RowId;
        vm.customer('update_customer_values/');
      }
    } else if (!(data.phone_number.$valid)) {
      vm.service.pop_msg('Invalid phone number');
    } else {
      vm.service.pop_msg('Please fill required fields');
    }
  }

}

