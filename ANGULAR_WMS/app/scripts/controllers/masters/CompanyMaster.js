'use strict';

angular.module('urbanApp', ['datatables', 'ngAnimate', 'ui.bootstrap'])
  .controller('CompanyMasterTable',['$scope', '$http', '$state', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', '$log', 'colFilters' , 'Service', '$rootScope', '$modal',ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, $log, colFilters, Service, $rootScope, $modal) {
    var vm = this;
    vm.service = Service;
    vm.apply_filters = colFilters;

    vm.filters = {'datatable': 'CompanyMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
        DTColumnBuilder.newColumn('id').withTitle('Company ID'),
        DTColumnBuilder.newColumn('company_name').withTitle('Company Name'),
        DTColumnBuilder.newColumn('email_id').withTitle('Email ID'),
        DTColumnBuilder.newColumn('phone_number').withTitle('Phone Number')
    ];

    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });
    var empty_data = {"id":"", "company_name":"", 
                      "email_id":"", "phone_number":"", "logo":"",
                      "city":"", "state":"", "country":"", "pincode":"", "gstin_number":"",
                      "cin_number":"", "pan_number":"", "address":""};
    vm.model_data = {};
    angular.copy(empty_data, vm.model_data);

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                angular.copy(aData, vm.model_data);
                vm.model_data.logo = vm.service.check_image_url(vm.model_data.logo);
                vm.update = true;
                vm.title = "Update Company";
                $state.go("app.masters.CompanyMaster.Company");
            });
        });
        return nRow;
    }

    vm.base = function() {

      vm.title = "Add Company";
      vm.update = false;
      angular.copy(empty_data, vm.model_data);
      vm.service.apiCall("get_company_master_id/").then(function(data){
      if(data.message) {

        vm.model_data["id"] = data.data.id;
      }
    });
    }
    vm.base();

    vm.close = function() {

      angular.copy(empty_data, vm.model_data);
      $state.go('app.masters.CompanyMaster');
    }

    vm.add = function() {

      vm.base();
      $state.go('app.masters.CompanyMaster.Company');
    }

  vm.company = function(url) {
    var elem = angular.element($('form'));
    elem = elem[0];
    elem = $(elem).serializeArray();
    var formData = new FormData()
    var files = $("#update_company").find('[name="files"]')[0].files;
    $.each(files, function(i, file) {
        formData.append('files-' + i, file);
    });
    $.each(elem, function(i, val) {
        formData.append(val.name, val.value);
    });
    $rootScope.process = true;
    $.ajax({url: Session.url+url,
            data: formData,
            method: 'POST',
            processData : false,
            contentType : false,
            xhrFields: {
                withCredentials: true
            },
            'success': function(response) {
              if(response.indexOf("Success") > -1) {
                vm.service.refresh(vm.dtInstance);
                vm.close();
              } else {
                vm.service.pop_msg(response);
              }
              $rootScope.process = false;
            }});
    }
  vm.get_company_id = function() {

    vm.service.apiCall("get_company_master_id/").then(function(data){
      if(data.message) {

        vm.model_data["id"] = data.data.id;
      }
    });
  }
  vm.get_company_id();

  vm.submit = function(data) {

    if (data.$valid) {
      if ("Add Company" == vm.title) {
        vm.company('insert_company_master/');
      } else {
        vm.model_data['data-id'] = vm.model_data.DT_RowId;
        vm.company('update_company_master/');
      }
    }
  }

}

