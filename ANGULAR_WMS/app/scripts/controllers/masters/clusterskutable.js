;(function(){

'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ClusterSkuMasterTable',['$rootScope', '$scope', '$http', '$compile', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($rootScope, $scope, $http, $compile, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.apply_filters = colFilters;
  vm.service = Service;
  vm.selected = {};
  vm.selectAll = false;
  vm.bt_disable = true;
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
    .withOption('createdRow', function(row, data, dataIndex) {
          $compile(angular.element(row).contents())($scope);
      })
      .withOption('headerCallback', function(header) {
          if (!vm.headerCompiled) {
              vm.headerCompiled = true;
              $compile(angular.element(header).contents())($scope);
          }
      })
    .withOption('initComplete', function( settings ) {
      vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
    });

  vm.dtColumns = [
    DTColumnBuilder.newColumn('ClusterName').withTitle('Cluster Name'),
    DTColumnBuilder.newColumn('Skuid').withTitle('SKU ID'),
    DTColumnBuilder.newColumn('Sequence').withTitle('Sequence'),
    DTColumnBuilder.newColumn('CreationDate').withTitle('Creation Date')
  ];
  vm.dtColumns.unshift(DTColumnBuilder.newColumn('check').withTitle(vm.service.titleHtml).notSortable().withOption('width', '25px')
    .renderWith(function(data, type, full, meta) {
      if(1 == vm.dtInstance.DataTable.context[0].aoData.length) {
        vm.selected = {};
      }
      vm.selected[meta.row] = vm.selectAll;
      return vm.service.frontHtml + meta.row + vm.service.endHtml;
  }))
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
      });
    });
    return nRow;
  }

  vm.delete_confirmation = function () {
    vm.generate_data = []
    vm.send_data = {}
    vm.bt_disable = true;
    for(var key in vm.selected){
      if(vm.selected[key]) {
        vm.generate_data.push(vm.dtInstance.DataTable.context[0].aoData[Number(key)]["_aData"].id);
      }
    }
    swal({
        title: "Do you want to delete" + ' ' + vm.generate_data.length + ' ' + "clusters",
        text: "Are you sure?",
        type: "warning",
        showCancelButton: true,
        confirmButtonColor: "#DD6B55",
        confirmButtonText: "Yes",
        cancelButtonText: "No",
        closeOnConfirm: false,
        closeOnCancel: true
     },
     function(isConfirm){
       if (isConfirm) {
         vm.service.apiCall('delete_cluster_sku/', 'POST', {'data':JSON.stringify(vm.generate_data)}).then(function(data){
            if(data.data == 'success') {
              if(vm.generate_data.length == 1){
                swal("Deleted!", "Cluster is deleted", "success");
                vm.dtInstance.reloadData();
                vm.bt_disable = false;
              } else {
                swal("Deleted!", "Clusters are deleted", "success");
                vm.dtInstance.reloadData();
                vm.bt_disable = false;
              }
            } else {
              swal("OOPS!", "Cluster-sku Deletion Failed", "success");
              vm.dtInstance.reloadData();
            }
         });
       }
       else {
        vm.dtInstance.reloadData();
        vm.bt_disable = true;
       }
     });
  }
  vm.close = function() {
    $state.go('app.masters.ClusterSkuMaster');
  }
  vm.root_path = function(value){
    $rootScope.type = value
    $state.go('app.masters.ImageBulkUpload')
  }
}

})();
