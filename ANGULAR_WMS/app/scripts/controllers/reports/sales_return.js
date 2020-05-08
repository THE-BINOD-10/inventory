(function(){

'use strict';

var app = angular.module('urbanApp', ['datatables']);

app.controller('SalesReturnReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $modal) {

  var vm = this;
  vm.service = Service;
  vm.service.print_enable = false;
  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;

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
      DTColumnBuilder.newColumn('order_id').withTitle('Order ID'),
      DTColumnBuilder.newColumn('order_date').withTitle('Order Date'),
      DTColumnBuilder.newColumn('credit_note_number').withTitle('Credit Note Number'),
      DTColumnBuilder.newColumn('credit_note_date').withTitle('Credit Note Date'),
      DTColumnBuilder.newColumn('customer_id').withTitle('Customer ID'),
      DTColumnBuilder.newColumn('customer_name').withTitle('Customer Name'),
//      DTColumnBuilder.newColumn('return_date').withTitle('Return Date'),
      DTColumnBuilder.newColumn('invoice_number').withTitle('Invoice Number'),
      DTColumnBuilder.newColumn('invoice_date').withTitle('Invoice Date'),
      DTColumnBuilder.newColumn('sku_code').withTitle('SKU Code'),
      DTColumnBuilder.newColumn('sku_desc').withTitle('SKU Description'),
//      DTColumnBuilder.newColumn('sku_category').withTitle('SKU Category'),
//      DTColumnBuilder.newColumn('sub_category').withTitle('SKU Sub Category'),
//      DTColumnBuilder.newColumn('sku_brand').withTitle('SKU Brand'),
      DTColumnBuilder.newColumn('unit_price').withTitle('Unit Price'),
      DTColumnBuilder.newColumn('tax_percent').withTitle('Tax Percentage'),
      DTColumnBuilder.newColumn('hsn_code').withTitle('HSN Code'),
      DTColumnBuilder.newColumn('marketplace').withTitle('Market Place'),
      DTColumnBuilder.newColumn('city').withTitle('City'),
      DTColumnBuilder.newColumn('quantity').withTitle('Quantity'),
      DTColumnBuilder.newColumn('credit_wo_tax_amount').withTitle('Credit Note Amount(w/o tax)'),
      DTColumnBuilder.newColumn('credit_tax_amount').withTitle('Credit Note Tax Amount'),
      DTColumnBuilder.newColumn('total_credit_note_amount').withTitle('Total Credit Note Amount'),
      DTColumnBuilder.newColumn('state').withTitle('State'),
      DTColumnBuilder.newColumn('customer_gst_no').withTitle('Customer GST Number'),
      DTColumnBuilder.newColumn('gst_number').withTitle('GST Number'),
      DTColumnBuilder.newColumn('reason').withTitle('Reason'),
      DTColumnBuilder.newColumn('status').withTitle('Status')
  ];
  if (vm.industry_type == "FMCG" && vm.user_type == "marketplace_user") {
    vm.dtColumns.splice(5, 0, DTColumnBuilder.newColumn('Manufacturer').withTitle('Manufacturer'))
    vm.dtColumns.splice(6, 0, DTColumnBuilder.newColumn('Searchable').withTitle('Searchable'))
    vm.dtColumns.splice(7, 0, DTColumnBuilder.newColumn('Bundle').withTitle('Bundle'))
  }
  if (vm.industry_type == "FMCG") {
    vm.dtColumns.push(
        DTColumnBuilder.newColumn('batch_no').withTitle('Batch No'),
        DTColumnBuilder.newColumn('mrp').withTitle('MRP'),
        DTColumnBuilder.newColumn('manufactured_date').withTitle('Manufactured Date'),
        DTColumnBuilder.newColumn('expiry_date').withTitle('Expiry Date')
      )
  }

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
                    'sku_desc': '',
                    'order_id': '',
                    'customer_id': '',
                    'creation_date': '',
                    'to_date':'',
                    'marketplace': '',
                    'sku_category': '',
                    'sub_category': '',
                    'sku_brand': '',
                    'manufacturer':'',
                    'searchable':'',
                    'bundle':'',
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
