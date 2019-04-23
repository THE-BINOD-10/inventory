;(function(){

'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ClusterSkuMasterTable',['$rootScope', '$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($rootScope, $scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.apply_filters = colFilters;
  vm.service = Service;

  vm.filters = {'datatable': 'ClusterMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
    DTColumnBuilder.newColumn('ClusterName').withTitle('Cluster Name'),
    DTColumnBuilder.newColumn('Skuid').withTitle('SKU ID'),
    DTColumnBuilder.newColumn('Sequence').withTitle('Sequence'),
    DTColumnBuilder.newColumn('CreationDate').withTitle('Creation Date')
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
        vm.model_data = {};
        angular.extend(vm.model_data, aData);
        vm.update = true;
        vm.message = "";
        vm.title = "Update Cluster";
        // $state.go('app.masters.SupplierMaster.supplier');
      });
    });
    return nRow;
  }

  vm.filter_enable = true;

  var empty_data = {id: "", name: "", email_id: "", address: "", phone_number: "", status: "Active",
                    create_login: false, login_created: false};
  vm.status_data = ["Inactive", "Active"];
  vm.title = "Add Supplier";
  vm.update = false;
  vm.message = "";
  vm.model_data = {};
  angular.copy(empty_data, vm.model_data);

  vm.close = function() {
    $state.go('app.masters.ClusterSkuMaster');
  }
  vm.root_path = function(value){
    $rootScope.type = value
    $state.go('app.masters.ImageBulkUpload')
  }
}

})();
