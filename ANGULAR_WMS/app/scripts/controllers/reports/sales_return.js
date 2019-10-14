(function(){

'use strict';

var app = angular.module('urbanApp', ['datatables']);

app.controller('SalesReturnReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $modal) {

  var vm = this;
  vm.service = Service;
  vm.service.print_enable = false;

  vm.dtOptions = DTOptionsBuilder.newOptions()
     .withOption('ajax', {
            url: Session.url+'get_sales_return_filter/',
            type: 'GET',
            data: vm.model_data,
            xhrFields: {
              withCredentials: true
            },
            data: vm.model_data
         })
     .withDataProp('data')
     .withOption('processing', true)
     .withOption('serverSide', true)
     .withPaginationType('full_numbers')
     .withOption('rowCallback', rowCallback);

  vm.dtColumns = [
      DTColumnBuilder.newColumn('sku_code').withTitle('SKU Code'),
      DTColumnBuilder.newColumn('sku_category').withTitle('SKU Category'),
      DTColumnBuilder.newColumn('sub_category').withTitle('SKU Sub Category'),
      DTColumnBuilder.newColumn('sku_brand').withTitle('SKU Brand'),
      DTColumnBuilder.newColumn('order_id').withTitle('Order ID'),
      DTColumnBuilder.newColumn('customer_id').withTitle('Customer ID'),
      DTColumnBuilder.newColumn('return_date').withTitle('Return Date'),
      DTColumnBuilder.newColumn('quantity').withTitle('Quantity'),
      DTColumnBuilder.newColumn('marketplace').withTitle('Market Place')
  ];

  vm.dtInstance = {};

  function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
    $('td', nRow).unbind('click');
    $('td', nRow).bind('click', function() {
      $scope.$apply(function() {
         console.log(aData);

         var modalInstance = $modal.open({
            templateUrl: 'views/reports/toggles/sales_return_details.html',
            controller: 'SalesReturnDetails',
            controllerAs: '$ctrl',
            size: 'lg',
            backdrop: 'static',
            keyboard: false,
            resolve: {
              items: function () {
                return aData;
              }
            }
          });
      });
    })
  }

  vm.empty_data = {
                    'sku_code': '',
                    'wms_code': '',
                    'order_id': '',
                    'customer_id': '',
                    'creation_date': '',
                    'to_date':'',
                    'marketplace': '',
                    'sku_category': '',
                    'sub_category': '',
                    'sku_brand': ''
                    };

  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);

  vm.marketplace_list = [];
  vm.service.apiCall("get_marketplaces_list/").then(function(data){

    if(data.message) {

      vm.marketplace_list = data.data.marketplaces;
    }
  })

}

app.controller('SalesReturnDetails', function($scope, Service, $modalInstance, items){

  console.log(items);
  var vm = this;
  vm.modal_data = items;

  vm.ok = function (msg) {
    $modalInstance.close(vm.status_data);
  };
})

})();
