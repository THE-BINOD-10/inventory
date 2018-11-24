'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('WarehouseMasterTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.filters = {'datatable': 'WarehouseMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
       .withOption('rowCallback', rowCallback);
    vm.dtColumns = [
        DTColumnBuilder.newColumn('Username').withTitle('Username'),
        DTColumnBuilder.newColumn('Name').withTitle('Name'),
        DTColumnBuilder.newColumn('Email').withTitle('Email'),
        DTColumnBuilder.newColumn('City').withTitle('City'),
        DTColumnBuilder.newColumn('Type').withTitle('Type'),
        DTColumnBuilder.newColumn('Level').withTitle('Level'),
        DTColumnBuilder.newColumn('Min Order Value').withTitle('Min Order Value'),
        DTColumnBuilder.newColumn('Zone').withTitle('Zone')
    ];

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    var empty_data = {"username":"","first_name":"", "last_name":"", "phone_number":"", "email":"",
                      "country":"", "state":"", "city":"", "address":"", "pin_code":""}

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
            vm.customer_name=false;
            $scope.$apply(function() {
                console.log(aData);
                vm.model_data = {};
                vm.update = true;
                vm.message = "";
                vm.title = "Update Warehouse";
                //vm.status = (aData["Status"] == "Active") ? vm.status_data[0] : vm.status_data[1];
                $http.get(Session.url+'get_warehouse_user_data/?username='+aData.Username).success(function(data, status, headers, config) {
                   console.log(data)
                   angular.extend(vm.model_data, data.data);
                   vm.model_data.phone_number = parseInt(vm.model_data.phone_number);
                   vm.customer_name = (vm.model_data.customer_name)? true: false;
                   $state.go('app.masters.WarehouseMaster.Warehouse');
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

    vm.close = close;
    function close() {

      vm.model_data = {};
      vm.customer_name = false;
      angular.extend(vm.model_data, empty_data);
      $state.go('app.masters.WarehouseMaster');
    }
    vm.add = add;
    function add() {

      vm.title = "Add Warehouse";
      vm.message = "";
      vm.model_data = {};
      angular.extend(vm.model_data, empty_data);
      vm.update = false;
      $state.go('app.masters.WarehouseMaster.Warehouse');
    }

  vm.update_warehouse = update_warehouse;
  function update_warehouse() {
    vm.service.apiCall("update_warehouse_user/", "POST", vm.model_data, true).then(function(data) {
      if(data.message) {
        if(data.data == "Updated Successfully") {
          vm.close();
          reloadData();
        }
        vm.service.pop_msg(data.data);
      }
    });
  }
  vm.change_warehouse_password = change_warehouse_password;
  function change_warehouse_password(){
    vm.service.apiCall("change_warehouse_password/", "POST",{'new_password':vm.model_data.new_password,'user_name':vm.model_data.username}).then(function(data) {
      // if(data.message)
      // {
      //   vm.service.pop_msg(data.data);
      // }
      vm.service.pop_msg(data.data);
  });
  }

  vm.create_warehouse = create_warehouse;
  function create_warehouse(form) {
    if (form.password.$valid && form.re_password.$valid && (form.password.$viewValue == form.re_password.$viewValue)) {
      if (!(vm.model_data)) {
        vm.model_data.phone_number = "";
      }
      vm.service.apiCall("add_warehouse_user/", "POST", vm.model_data, true).then(function(data) {
        if(data.message) {
          if(data.data == "Added Successfully") {
            vm.close();
            reloadData();
          }
          vm.service.pop_msg(data.data);
        }
      });
    } else {
      vm.service.pop_msg("Please check password");
    }
  }

  vm.submit = submit;
  function submit(form) {
    if(form.username.$valid && form.first_name.$valid) {

      if ("Add Warehouse" == vm.title) {
        create_warehouse(form);
      } else {
        update_warehouse();
      }
    }
  }

  vm.changed = function(evt){
    if (vm.customer_name == true) {
      vm.customer_name = false;
    } else {
      vm.customer_name = true;
    }
  }
}
