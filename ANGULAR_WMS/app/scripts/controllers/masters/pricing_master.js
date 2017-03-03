'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PricingMaster',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.filters = {'datatable': 'PricingMaster'}
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

    var columns = ["SKU Code", "SKU Description", "Selling Price Type", "Price", "Discount"];
    vm.dtColumns = vm.service.build_colums(columns);

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
                angular.copy(empty_data, vm.model_data);
                vm.model_data.sku_code = aData['SKU Code'];
                vm.model_data.selling_price_type = aData['Selling Price Type'];
                vm.model_data.price = aData['Price'];
                vm.model_data.discount = aData['Discount'];
                vm.update = true;
                vm.title = "Update Pricing"
                $state.go('app.masters.PricingMaster.Add');
            });
        });
        return nRow;
    }

    var empty_data = {
                    "sku_code": "","selling_price_type":"", "price": "", "discount": ""
                    }
    vm.update = false;
    vm.title = "ADD PRICING"
    vm.model_data = {};
    angular.copy(empty_data, vm.model_data);

  vm.close = function() {
    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.PricingMaster');
  }

  vm.add = function() {

    vm.title = "ADD PRICING"
    angular.copy(empty_data, vm.model_data);
    vm.update = false;
    $state.go('app.masters.PricingMaster.Add');
  }

  vm.send_pricing = function(url, data) {

    vm.service.apiCall(url, 'POST', data).then(function(data){
      if(data.message) {
        if (data.data == 'New Pricing Added' || data.data == 'Updated Successfully')  {
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
        vm.send_pricing('add_pricing/', send);
      } else {
        vm.send_pricing('update_pricing/', send);
      }
    } else {
      vm.service.pop_msg('Please fill required fields');
    }
  }

}
