'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SalesReturnReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
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
       .withPaginationType('full_numbers');

    vm.dtColumns = [
        DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('Order ID').withTitle('Order ID'),
        DTColumnBuilder.newColumn('Customer ID').withTitle('Customer ID'),
        DTColumnBuilder.newColumn('Return Date').withTitle('Return Date'),
        DTColumnBuilder.newColumn('Quantity').withTitle('Quantity'),
        DTColumnBuilder.newColumn('Market Place').withTitle('Market Place'),
        DTColumnBuilder.newColumn('Status').withTitle('Status').renderWith(function(data, type, full, meta) {
                          var status = 'Active';
                          var color = '#70cf32';
                          if (data != status) {
                            status = 'Inactive';
                            color = '#d96557';
                          }
                          return '<span style="padding: 1px 6px 3px;border-radius: 10px;background: #f4f4f5;">'+'<i class="fa fa-circle" style="color:'+color+';display: inline-block;"></i>'+'<p style="display: inline-block;margin: 0px;padding-left: 5px;">'+status+'</p>'+'</span>'
                        }).withOption('width', '80px')
    ];

  vm.dtInstance = {};

  vm.empty_data = {
                    'sku_code': '',
                    'wms_code': '',
                    'order_id': '',
                    'customer_id': '',
                    'creation_date': '',
                    'marketplace': ''
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

