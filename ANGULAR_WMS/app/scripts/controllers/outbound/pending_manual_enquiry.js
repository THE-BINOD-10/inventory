;(function(){

'use strict';

var stockone = angular.module('urbanApp', ['datatables']);

stockone.controller('PendingManualEnquiryCtrl',['$scope', '$http', '$state', '$compile', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', '$modal', PendingManualEnquiryCtrl]);

function PendingManualEnquiryCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, Service, $modal) {

  var vm = this;
  vm.apply_filters = colFilters;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  vm.tb_data = {};
  vm.filters = {'datatable': 'ManualEnquiryOrders', 'special_key': 'pending_approval', 'search0':'', 'search1':'', 'search2': '', 'search3': ''}
  vm.dtOptions = DTOptionsBuilder.newOptions()
    .withOption('ajax', {
        url: Session.url+'results_data/',
        type: 'POST',
        data: vm.filters,
        xhrFields: {
          withCredentials: true
        },
        complete: function(jqXHR, textStatus) {
          $scope.$apply(function(){
            angular.copy(JSON.parse(jqXHR.responseText), vm.tb_data)
          })
        }
    })
    .withDataProp('data')
    .withOption('processing', true)
    .withOption('serverSide', true)
    .withOption('rowCallback', rowCallback)
    .withOption('order', [0, 'desc'])
    .withPaginationType('full_numbers')
    .withOption('initComplete', function( settings ) {
      //vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
    });
    
  vm.dtColumns = vm.service.build_colums(['Enquiry ID', 'Customer Name', 'Sub Distributor', 'Style Name', 'Customization Type', 'Date']);
  vm.dtInstance = {};

  $scope.$on('change_filters_data', function(){
    if($("#"+vm.dtInstance.id+":visible").length != 0) {
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    }
  });

  function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
    $('td', nRow).unbind('click');
    $('td', nRow).bind('click', function() {
      $scope.$apply(function() {
        vm.enquiryDetails(aData);
      });
    });
  }

  vm.enquiryDetails = function(data) {

    var mod_data = {enquiry_id: data['ID'], user_id: data['User ID'],
                    customization_type: data['Customization Type'], from: 'pending_approval'};
    var modalInstance = $modal.open({
      templateUrl: 'views/outbound/toggle/approve_manual_order.html',
      controller: 'ManualOrderDetails',
      controllerAs: 'order',
      size: 'lg',
      backdrop: 'static',
      keyboard: false,
      resolve: {
        items: function () {
          return mod_data;
        }
      }
    });
    modalInstance.result.then(function (selectedItem) {
      var data = selectedItem;
      $('.custom-table').DataTable().ajax.reload();
    })
  }
}

})();
