'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('NetworkMaster',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'SweetAlert', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, SweetAlert, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.filters = {'datatable': 'NetworkMaster'}
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


    var columns = ["Destination Location Code", "Source Location Code", "Lead Time", "Sku Stage", "Priority"];

    vm.dtColumns = [
       DTColumnBuilder.newColumn('Destination Location Code').withTitle('Destination Location Code'),
       DTColumnBuilder.newColumn('Source Location Code').withTitle('Source Location Code'),
       DTColumnBuilder.newColumn('Lead Time').withTitle('Lead Time (In Days)'),
       DTColumnBuilder.newColumn('Sku Stage').withTitle('Sku Stage'),
       DTColumnBuilder.newColumn('Priority').withTitle('Priority'),
       DTColumnBuilder.newColumn('Price Type').withTitle('Price Type'),
       DTColumnBuilder.newColumn('Remarks').withTitle('Remarks'),
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
                var send = {destination_location_code: aData['Destination Location Code'],
                            source_location_code: aData['Source Location Code'],
                            sku_stage: aData['Sku Stage']};
                vm.service.apiCall("get_network_data/", "GET", send).then(function(data) {
                    if(data.message) {
                      if (data.data.status) {
                        angular.copy(data.data.data, vm.model_data);
                        vm.update = true;
                        vm.title = "Update Network"
                        $state.go('app.masters.NetworkMaster.Add');
                      }
                    }
                });
            });
            return nRow;
         });
    }

    var empty_data = {
                    "destination_location_code": "", "source_location_code":"", "lead_time": "", 
                    "sku_stage": "", "priority": ""
                    }

    vm.update = false;
    vm.title = "ADD Network"
    vm.model_data = {};
    vm.remarks_drop = [{name:'Freight as applicable will be charged extra.'},{name:'Charges are Inclusive of Freight.'}];
    angular.copy(empty_data, vm.model_data);

  vm.getDestLocCode = function(){
    validataionLocCode();
  }

  vm.getSourceLocCode = function(){
    validataionLocCode();
  }

  function validataionLocCode(){
    if ((vm.model_data.data.dest_location_code && vm.model_data.data.source_location_code) && vm.model_data.data.dest_location_code == vm.model_data.data.source_location_code) {

      SweetAlert.swal({
               title: '',
               text: 'Destination Location Code and Source Location Code are same please change it',
               type: 'warning',
               showCancelButton: false,
               confirmButtonColor: '#33cc66',
               confirmButtonText: 'Ok',
               closeOnConfirm: true,
             },
             function (status) {
               vm.close();
               }
             );

      vm.model_data.data.source_location_code = '';
      angular.element('#source_location_code').focus();
    }
  }

  vm.close = function() {
    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.NetworkMaster');
  }

  vm.add = function() {

    vm.title = "ADD NETWORK"
    angular.copy(empty_data, vm.model_data);
    vm.update = false;
    $state.go('app.masters.NetworkMaster.Add');
  }

  vm.send_network = function(url, data) {

    vm.service.apiCall(url, 'POST', data, true).then(function(data){
      if(data.message) {
        if (data.data == 'New Network object is created' || data.data == 'Updated Successfully')  {
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
      send[0].value = send[0].value.split(":")[0].replace(/[\s]/g, '');
      send[1].value = send[1].value.split(":")[0].replace(/[\s]/g, '');

      if ("ADD NETWORK" == vm.title) {
        vm.send_network('add_network/', send);
      } else {
        vm.send_network('update_network/', send);
      }
    } else {
      vm.service.pop_msg('Please fill required fields');
    }
  }

  vm.update_data = function(index) {

    vm.model_data.data.splice(index,1);
  }

}
