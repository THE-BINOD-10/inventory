'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('StaffMasterTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.department_type_readonly = true;
    vm.filters = {'datatable': 'StaffMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':''}
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
       .withOption('order', [1, 'asc'])
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    vm.dtColumns = [
        DTColumnBuilder.newColumn('staff_code').withTitle('Staff Code'),
        DTColumnBuilder.newColumn('name').withTitle('Staff Name'),
        DTColumnBuilder.newColumn('company').withTitle('Subsidary'),
        DTColumnBuilder.newColumn('warehouse_names').withTitle('Plant'),
        DTColumnBuilder.newColumn('department').withTitle('Department'),
        DTColumnBuilder.newColumn('department_type').withTitle('Department Type'),
        DTColumnBuilder.newColumn('position').withTitle('Position'),
        DTColumnBuilder.newColumn('email_id').withTitle('Email'),
        DTColumnBuilder.newColumn('reportingto_email_id').withTitle('Reporting To'),
        DTColumnBuilder.newColumn('phone_number').withTitle('Phone Number'),
        DTColumnBuilder.newColumn('status').withTitle('Status').renderWith(function(data, type, full, meta) {
                        return vm.service.status(full.status);
                        }).withOption('width', '80px'),
        DTColumnBuilder.newColumn('group_keys').withTitle('Groups'),
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
                vm.title = "Update Staff";
                vm.message ="";
                vm.model_data.warehouse = vm.model_data.warehouse.split(',');
                $state.go('app.masters.StaffMaster.Staff');


                $timeout(function(){
                  $('.selectpicker-groups').val(vm.model_data.groups);
                  $('.selectpicker-groups').selectpicker();
                }, 500);
                $timeout(function () {
                  $(".customer_status").val(vm.model_data.status);
                }, 500);
            });
        });
    }

  vm.status_data = ["Inactive", "Active"];
  var empty_data = {name: "", email_id: "", phone_number: "", status: "", margin: 0, company_id: '',
                    plant: [], department_id: '', department_type: [], postion: '', warehouse: []};
  vm.model_data = {};

  vm.base = function() {

    vm.title = "Add Staff";
    vm.update = false;
    angular.copy(empty_data, vm.model_data);
    vm.model_data.status = vm.status_data[1];
  }
  vm.base();

  vm.close = function() {

    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.StaffMaster');
    vm.warehouse_list = [];
    vm.department_type_readonly = true;
  }

  vm.add = add;
  function add() {

    vm.base();
    $state.go('app.masters.StaffMaster.Staff');
    $timeout(function(){$('.selectpicker-groups').selectpicker();}, 1000);
    $timeout(function(){$('.selectpicker-plants').selectpicker();}, 500);
    $timeout(function(){$('.selectpicker-depts').selectpicker();}, 500);
  }

  vm.customer = function(url) {

    var send = {}
    var send = $("form").serializeArray();
    if(vm.model_data.warehouse){ send.push({name: 'plant', value: vm.model_data.warehouse.join(',')}); }
    else {send.push({name: 'plant', value: ""});}
    if(vm.model_data.department_type_list){ send.push({name: 'department_type', value: vm.model_data.department_type_list.join(',')}); }
    else {send.push({name: 'department_type', value: ""});}
    vm.service.apiCall(url, 'POST', send, true).then(function(data){
      if(data.message) {
        if(data.data == 'New Staff Added' || data.data == 'Updated Successfully') {
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
      if ("Add Staff" == vm.title) {
        vm.customer('insert_staff/');
      } else {
        vm.model_data['data-id'] = vm.model_data.DT_RowId;
        vm.customer('update_staff_values/');
      }
    } else if (!(data.phone_number.$valid)) {
      vm.service.pop_msg('Invalid phone number');
    } else {
      vm.service.pop_msg('Please fill required fields');
    }
  }

  vm.company_list = [];
  function get_company_list() {
    vm.service.apiCall("get_company_list/", "GET").then(function(data) {
      if(data.message) {
        vm.company_list = data.data.company_list;
      }
    });
  }
  get_company_list();

  vm.warehouse_list = [];
  vm.get_company_warehouse_list = get_company_warehouse_list;
  function get_company_warehouse_list() {
    var wh_data = {};
    wh_data['company_id'] = vm.model_data.company_id;
    wh_data['warehouse_type'] = 'STORE,SUB_STORE';
    vm.service.apiCall("get_company_warehouses/", "GET", wh_data).then(function(data) {
      if(data.message) {
        vm.warehouse_list = data.data.warehouse_list;
        $('.selectpicker-plants').selectpicker('deselectAll');
        $timeout(function(){$('.selectpicker-plants').selectpicker('refresh');}, 500);
        $('.selectpicker-depts').selectpicker('deselectAll');
        $timeout(function(){$('.selectpicker-depts').selectpicker('refresh');}, 500);
      }
    });
  }

  vm.department_list = [];
  vm.get_warehouse_department_list = get_warehouse_department_list;
  function get_warehouse_department_list() {
    var wh_data = {};
    wh_data['company_id'] = vm.model_data.company_id;
    wh_data['warehouse'] = vm.model_data.warehouse.join(',');
    wh_data['warehouse_type'] = 'DEPT';
    if(vm.model_data.warehouse.length > 1){
      vm.department_type_readonly = false;
    }
    else {
      vm.department_type_readonly = true;
    }
    vm.service.apiCall("get_company_warehouses/", "GET", wh_data).then(function(data) {
      if(data.message) {
        vm.department_list = data.data.warehouse_list;
      }
    });
  }

  vm.department_type_list = [];
  vm.service.apiCall('get_department_list/').then(function(data){
    if(data.message) {
      vm.department_type_list = data.data.department_list;
    }
  });

  vm.roles_list = [];
  function get_roles_list() {
    vm.service.apiCall("get_company_roles_list/", "GET").then(function(data) {
      if(data.message) {
        vm.roles_list = data.data.roles_list;
      }
    });
  }
  get_roles_list();

  vm.update_department_type = function() {
    angular.forEach(vm.department_list, function(dept){
      console.log(dept);
      if(dept.username == vm.model_data.department){
        vm.model_data.department_type = dept.stockone_code;
      }
    });
  }

  vm.groups_list = [];
  function get_groups_list() {
    vm.service.apiCall("get_user_groups_list/", "GET").then(function(data) {
      if(data.message) {
        vm.groups_list = data.data.groups;
      }
    });
  }
  get_groups_list();

  vm.check_selected_val = function(check_data, group){
    var selected_val = false;
    for(var ind=0; ind<check_data.length; ind++) {
      console.log(check_data[ind], group)
      if(check_data[ind] == group) {
        selected_val = true;
        break;
      }
    }
    return selected_val;
  }

}

