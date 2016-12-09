'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('VendorMasterCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.filters = {'datatable': 'VendorMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
        DTColumnBuilder.newColumn('vendor_id').withTitle('Vendor ID'),
        DTColumnBuilder.newColumn('name').withTitle('Name'),
        DTColumnBuilder.newColumn('address').withTitle('Address'),
        DTColumnBuilder.newColumn('phone_number').withTitle('Phone Number'),
        DTColumnBuilder.newColumn('email').withTitle('Email'),
        DTColumnBuilder.newColumn('Status').withTitle('Status').renderWith(function(data, type, full, meta) {
                          return vm.service.status(full.Status);
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
                console.log(aData);
                vm.service.apiCall('get_vendor_data/', 'GET', {data_id: aData.vendor_id}).then(function(data){
                  if(data.message) {
                    angular.extend(vm.model_data, data.data);
                    vm.model_data.status = vm.status_data[vm.model_data.status];
                    vm.title="Vendor Data"
                    $state.go('app.masters.VendorMaster.Vendor');
                  }
                });
            });
        });
        return nRow;
    }

   var empty_data = {
                    "id": "",
                    "name": "",
                    "email_id": "",
                    "address": "",
                    "phone_number":"",
                    "status": ""
                    }
  vm.status_data = ["Inactive", "Active"];
  vm.model_data = {};

  vm.base = function() {

    vm.title = "Add Vendor";
    vm.update = false;
    angular.extend(empty_data, vm.model_data);
    vm.model_data.status = vm.status_data[1];
  }
  vm.base();

  vm.close = function() {

      angular.copy(empty_data, vm.model_data);
      $state.go('app.masters.VendorMaster');
  }

  vm.add = function() {

    vm.base();
    $state.go('app.masters.VendorMaster.Vendor');
  }

  vm.vendor = function(url) {
    var data = $("form:visible").serializeArray();
    vm.service.apiCall(url, 'GET', data).then(function(data){
      if(data.message) {
        if (data.data == 'New Vendor Added' || data.data == 'Updated Successfully') {
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
      if ("Add Vendor" == vm.title) {
        vm.vendor("insert_vendor/");
      } else {
        vm.vendor("update_vendor_values/");
      }
    } else if (!(data.phone_number.$valid)) {
      vm.service.pop_msg('Invalid phone number');
    }
    else {
      vm.service.pop_msg('Please fill required fields');
    }
  }

}

