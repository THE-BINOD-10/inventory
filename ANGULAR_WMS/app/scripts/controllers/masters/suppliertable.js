'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SupplierMasterTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.filters = {'datatable': 'SupplierMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
        DTColumnBuilder.newColumn('id').withTitle('Supplier ID'),
        DTColumnBuilder.newColumn('name').withTitle('Name'),
        DTColumnBuilder.newColumn('address').withTitle('Address'),
        DTColumnBuilder.newColumn('phone_number').withTitle('Phone Number'),
        DTColumnBuilder.newColumn('email_id').withTitle('Email'),
        DTColumnBuilder.newColumn('Status').withTitle('Status').renderWith(function(data, type, full, meta) {
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
                console.log(aData);
                vm.model_data = {};
                angular.extend(vm.model_data, aData);
                vm.update = true;
                vm.message = "";
                vm.title = "Update Supplier";
                vm.model_data.status = vm.status_data[vm.status_data.indexOf(aData["status"])]
                $state.go('app.masters.SupplierMaster.supplier');
                $timeout(function () {
                  $(".supplier_status").val(vm.model_data.status);
                }, 500); 
            });
        });
        return nRow;
    }

    vm.filter_enable = true;

    var empty_data = {
                    "id": "",
                    "name": "",
                    "email_id": "",
                    "address": "",
                    "phone_number":"",
                    "status": ""
                    }
    vm.status_data = ["Inactive", "Active"];
    vm.status= vm.status_data[0]
    vm.title = "Update Supplier";
    vm.update = true;
    vm.message = "";
    vm.model_data = {};
    angular.copy(empty_data, vm.model_data);

  vm.close = function() {
    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.SupplierMaster');
  }

  vm.add = function() {

    vm.title = "Add Supplier";
    angular.copy(empty_data, vm.model_data);
    vm.model_data.status = vm.status_data[1];
    vm.update = false;
    vm.message = "";
    $state.go('app.masters.SupplierMaster.supplier');
  }

  vm.supplier = function(url) {

    var data = $.param(vm.model_data);
    vm.service.apiCall(url, 'POST', vm.model_data, true).then(function(data){
      if(data.message) {
        if (data.data == 'New Supplier Added' || data.data == 'Updated Successfully')  {
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
      if ("Add Supplier" == vm.title) {
        vm.supplier('insert_supplier/');
      } else {
        vm.supplier('update_supplier_values/');
      }
    } else if (!(data.phone_number.$valid)) {
      vm.service.pop_msg('Invalid phone number');
    }
    else {
      vm.service.pop_msg('Please fill required fields');
    }
  }

}
