'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CorporateMasterTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.user_type = Session.roles.permissions.user_type;

    vm.filters = {'datatable': 'CorporateMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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

    if (vm.user_type != 'central_admin') {

      vm.corporate_id = 'Project ID';
      vm.corporate_name = 'Project Name';
      vm.main_title = 'Project Master';
    } else {

      vm.corporate_id = 'Corporate ID';
      vm.corporate_name = 'Corporate Name';
      vm.main_title = 'Corporate Master';
    }

    vm.dtColumns = [
        DTColumnBuilder.newColumn('corporate_id').withTitle(vm.corporate_id),
        DTColumnBuilder.newColumn('name').withTitle(vm.corporate_name),
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
                //vm.all_taxes = ['', 'VAT', 'CST']
                vm.update = true;
                vm.title = "Update Corporate";
                vm.message ="";
                $state.go('app.masters.CorporateMaster.corporate');
                $timeout(function () {
                  $(".corporate_status").val(vm.model_data.status);
                }, 500);
            });
        });
    }

  vm.status_data = ["Inactive", "Active"];
  var empty_data = {corporate_id: "", name: "", email_id: "", address: "", phone_number: "", status: "", tax_type: "", margin: 0};
  vm.model_data = {};

  vm.base = function() {

    vm.title = "Add Corporate";
    vm.update = false;
    angular.copy(empty_data, vm.model_data);
    vm.model_data.status = vm.status_data[1];
  }
  vm.base();

  vm.close = function() {

    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.CorporateMaster');
  }

  vm.get_corporate_id = function() {

    vm.service.apiCall("get_corporate_master_id/").then(function(data){
      if(data.message) {

        vm.model_data["corporate_id"] = data.data.corporate_id;
        vm.all_taxes = data.data.tax_data;
      }
    });
  }
  vm.get_corporate_id();

  vm.add = add;
  function add() {

    vm.base();
    vm.get_corporate_id();
    vm.corporate();
    $state.go('app.masters.CorporateMaster.corporate');
  }

  vm.corporate = function(url) {
    var send = {}
    //angular.copy(vm.model_data, send)
    //if(send.login_created) {
    //    send.create_login = false;
    //}
    var send = $("form").serializeArray()
    var data = $.param(send);
    vm.service.apiCall(url, 'POST', send, true).then(function(data){
      if(data.message) {
        if(data.data == 'New Corporate Added' || data.data == 'Updated Successfully') {
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
      if ("Add Corporate" == vm.title) {
        vm.corporate('insert_corporate/');
      } else {
        vm.model_data['data-id'] = vm.model_data.DT_RowId;
        vm.corporate('update_corporate_values/');
      }
    } else if (!(data.phone_number.$valid)) {
      vm.service.pop_msg('Invalid phone number');
    } else {
      vm.service.pop_msg('Please fill required fields');
    }
  }

}

