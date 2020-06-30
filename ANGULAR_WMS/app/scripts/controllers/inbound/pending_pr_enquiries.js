'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PendingPREnquiriesCtrl',['$scope', '$http', '$state', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.extra_width = { 'width': '1250px' };

    vm.filters = {'datatable': 'PendingPREnquiries', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
        // DTColumnBuilder.newColumn('Supplier ID').withTitle('Supplier ID'),
        // DTColumnBuilder.newColumn('Supplier Name').withTitle('Supplier Name'),
        DTColumnBuilder.newColumn('Purchase Number').withTitle('PR Number'),
        DTColumnBuilder.newColumn('Product Category').withTitle('Product Category'),
        DTColumnBuilder.newColumn('Enquiry From').withTitle('Enquiry From'),
        DTColumnBuilder.newColumn('Enquiry To').withTitle('Enquiry To'),
        DTColumnBuilder.newColumn('Enquiry Text').withTitle('Enquiry Text'),
        DTColumnBuilder.newColumn('Response').withTitle('Response'),
        DTColumnBuilder.newColumn('Status').withTitle('Status')
    ];

    vm.dtInstance = {};
    vm.model_data = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.service.apiCall('get_pending_enquiry/', 'GET', {data_id: aData.id}).then(function(data) {
                  if(data.message) {
                    vm.update = true;
                    vm.title = "Reply Enquiry";
                    angular.copy(data.data, vm.model_data);
                    vm.model_data.purchase_number = aData["Purchase Number"];
                    $state.go('app.inbound.RaisePr.submitResponseToEnquiry');
                  }
                });
            });
        });
        return nRow;
    };

    vm.submit_enquiry = function(data_id, response){
      var elem = {'data_id': data_id, 'response': response}
      vm.service.apiCall('submit_pending_enquiry/', 'POST', elem, true).then(function(data){
        if(data.message){
          if(data.data == 'Submitted Successfully') {
            vm.close();
            vm.service.refresh(vm.dtInstance);
          } else {
            vm.service.showNoty(data.data);
          }
        }
      })
    }
    vm.close = function() {
      $state.go('app.inbound.RaisePr');
    }
}

