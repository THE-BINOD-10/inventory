'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('TandCMaster',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.filters = {'datatable': 'SellerMarginMapping', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
        DTColumnBuilder.newColumn('seller_id').withTitle('Seller ID'),
        DTColumnBuilder.newColumn('name').withTitle('Seller Name'),
        DTColumnBuilder.newColumn('sku_code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('sku_desc').withTitle('SKU Description'),
        DTColumnBuilder.newColumn('margin').withTitle('Margin')
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
                angular.copy(aData, vm.model_data);
                vm.update = true;
                vm.title = "Update Mapping";
                vm.message ="";
                $state.go('app.masters.SellerMarginMapping.Mapping');
            });
        });
    }

  vm.items = ["dsfdsf", "sdfbshjdfs"]

  var empty_data = {seller: "", sku_code: "", margin: ""};
  vm.model_data = {};

  vm.base = function() {

    vm.title = "Add Mapping";
    vm.update = false;
    angular.copy(empty_data, vm.model_data);
  }
  vm.base();

  vm.close = function() {

    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.SellerMarginMapping');
  }

  vm.sellers = [];
  vm.get_sellers = function() {

    vm.service.apiCall("get_sellers_list/").then(function(data){
      if(data.message) {

        vm.sellers = data.data.sellers;
      }
    });
  }

  vm.add = add;
  function add() {

    vm.base();
    //vm.get_sellers();
    $state.go('app.masters.TandCMaster.Mapping');
  }

  vm.seller = function(url) {
    var send = {}
    angular.copy(vm.model_data, send)
    var data = $.param(send);
    vm.service.apiCall(url, 'POST', send).then(function(data){
      if(data.message) {
        if(data.data == 'Added Successfully' || data.data == 'Updated Successfully') {
          vm.service.refresh(vm.dtInstance);
          vm.close();
        } else {
          vm.service.pop_msg(data.data);
        }
      }
    });
  }

  vm.submit = submit;
  function submit(data) {
    if (data.$valid) {
      if ("Add Mapping" == vm.title) {
        vm.seller('insert_seller_margin/');
      } else {
        vm.seller('update_seller_margin/');
      }
    } else {
      vm.service.pop_msg('Please fill required fields');
    }
  }

}

