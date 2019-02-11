'use strict';

var app = angular.module('urbanApp', ['datatables'])
app.controller('TaxMaster',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$modal', '$log', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $modal, $log) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.filters = {'datatable': 'TaxMaster'}
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
        DTColumnBuilder.newColumn('Product Type').withTitle('Product Type'),
        DTColumnBuilder.newColumn('Creation Date').withTitle('Creation Date').notSortable()
       ]

    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
              vm.service.apiCall("get_tax_data/", "GET",{product_type: aData['Product Type']}).then(function(data) {
                if(data.message) {
                  if (data.data.status) {
                    angular.copy(data.data.data, vm.model_data);
                    vm.model_data.update = true;
                    vm.model_data.title = "Update Tax";
                    vm.open('lg', vm.model_data);
                  }
                }
              });
            });
        });
        return nRow;
    }

    var empty_data = {
                       product_type: "",
                       data: [{tax_type: "intra_state", min_amt: "", max_amt: "", sgst_tax: "", cgst_tax: "", igst_tax: "", cess_tax:"", apmc_tax: "", new_tax: true}]
                     }
    vm.update = false;
    vm.title = "Add Tax"
    vm.model_data = {};
    angular.copy(empty_data, vm.model_data);

  vm.close = function() {
    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.TaxMaster');
  }

  vm.add = function() {

    angular.copy(empty_data, vm.model_data);
    vm.model_data.title = "Add Tax";
    vm.model_data.update = false;
    vm.open('lg', vm.model_data);
  }

  vm.send_pricing = function(url, data) {

    vm.service.apiCall(url, 'POST', data, true).then(function(data){
      if(data.message) {
        if (data.data == 'New Tax Added' || data.data == 'Updated Successfully')  {
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
      var send = $(data.$name).serializeArray();
      if ("ADD PRICING" == vm.title) {
        vm.send_pricing('add_tax/', send);
      } else {
        vm.send_pricing('update_tax/', send);
      }
    } else {
      vm.service.pop_msg('Please fill required fields');
    }
  }

  vm.open = function (size, data) {

    var modalInstance = $modal.open({
      templateUrl: 'views/masters/toggles/tax_update.html',
      controller: 'TaxPOPCtrl',
      controllerAs: 'pop',
      size: size,
      backdrop: 'static',
      keyboard: false,
      resolve: {
        items: function () {
          return data;
        }
      }
    });

    modalInstance.result.then(function (selectedItem) {
       var data = selectedItem;
       vm.service.refresh(vm.dtInstance);
    }, function () {
      $log.info('Modal dismissed at: ' + new Date());
    });
  }
}

app.controller('TaxPOPCtrl', function ($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {

  $scope.title = 'Some title';
  var vm = this;
  vm.permissions = Session.roles.permissions;
  vm.model_data = items;
  console.log(vm.model_data);

  vm.ok = function (msg) {
    $modalInstance.close(msg);
  };

  vm.add = function() {
    vm.model_data.data.push({tax_type: "intra_state", min_amt: "", max_amt: "", sgst_tax: "", cgst_tax: "", igst_tax: "", cess_tax: "", apmc_tax: "", new_tax: true})
  }

  vm.update_data = function(index) {

    vm.model_data.data.splice(index,1);
  }

  Service.apiCall("get_customer_master_id/").then(function(data){
    if(data.message) {

      vm.taxes = data.data.tax_data;
    }
  });

  vm.submit = function(form) {

    if(form.$valid) {

      Service.apiCall("add_or_update_tax/", "POST", {data: JSON.stringify(vm.model_data)}).then(function(data){

        console.log(data.data);
        if (data.data == "success") {
          vm.ok(data.data);
        } else {

          Service.showNoty(data.data);
        }
      })
      console.log(form);
    }
  }

  vm.checkRange = function(amt, index, data, name) {

    if (!amt){
      return false;
    }

    if (name == 'min_amt' && data[index].max_amt) {

      if (Number(data[index].min_amt) >= Number(data[index].max_amt)) {

        data[index][name] = "";
        Service.showNoty("Min Amount Should Be lesser Than Mix Amount")
        return false;
      }
    } else if(name == 'max_amt' && data[index].min_amt) {

      if (Number(data[index].min_amt) >= Number(data[index].max_amt)) {

        data[index][name] = "";
        Service.showNoty("Max Amount Should Be Greater Than Min Amount");
        return false;
      }
    }
    for (var i = 0; i < data.length; i++) {

      var temp = data[i];
      if(i != index && data[index].tax_type == temp.tax_type) {

        if (Number(temp.min_amt) <= Number(amt) && Number(amt)  <=Number(temp.max_amt)) {

          data[index][name] = "";
          Service.showNoty("Range Already Exist");
        } else if (Number(temp.min_amt) < Number(amt) && Number(amt)  < Number(temp.max_amt)) {

          data[index][name] = "";
          Service.showNoty("Range Already Exist");
        } else if(Number(data[index].min_amt) <= Number(temp.min_amt) && Number(data[index].max_amt) >= Number(temp.min_amt)) {

          data[index][name] = "";
          Service.showNoty("Range Already Exist");
        }
      }
    }
  }

  vm.taxTypeChange = function(data) {

    data.sgst_tax = "";
    data.cgst_tax = "";
    data.igst_tax = "";
    data.max_amt = "";
    data.min_amt = "";
  }
});
