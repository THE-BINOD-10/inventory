'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('WarehouseMasterTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters) {
    var vm = this;
    vm.apply_filters = colFilters;
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
        DTColumnBuilder.newColumn('City').withTitle('City')
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
    var data = $.param(vm.model_data); 
    $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
    $http({
               method: 'POST',
               url:Session.url+"update_warehouse_user/",
               withCredential: true,
               data: data}).success(function(data, status, headers, config) {
                 pop_msg(data);
                 reloadData();
    });
  }

  vm.create_warehouse = create_warehouse;
  function create_warehouse(form) {
    if (form.password.$valid && form.re_password.$valid && (form.password.$viewValue == form.re_password.$viewValue)) {
    if (!(vm.model_data)) {
      vm.model_data.phone_number = "";
    }
    var data = $.param(vm.model_data);
    $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
    $http({
               method: 'POST',
               url:Session.url+"add_warehouse_user/",
               withCredential: true,
               data: data}).success(function(data, status, headers, config) {
                 pop_msg(data);
                 reloadData();
    });
    } else {
      pop_msg("Please check password") 
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

  function pop_msg(msg) {
    vm.message = msg;
    $timeout(function () {
        vm.message = "";
    }, 2000);
  }  
}

