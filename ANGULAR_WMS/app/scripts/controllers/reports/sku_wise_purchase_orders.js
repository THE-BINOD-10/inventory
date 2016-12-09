'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SKUWisePurchaseOrdersCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.service.print_enable = false;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'get_sku_purchase_filter/',
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
        DTColumnBuilder.newColumn('PO Date').withTitle('PO Date'),
        DTColumnBuilder.newColumn('Supplier').withTitle('Supplier'),
        DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('Order Quantity').withTitle('Order Quantity'),
        DTColumnBuilder.newColumn('Received Quantity').withTitle('Received Quantity'),
        DTColumnBuilder.newColumn('Rejected Quantity').withTitle('Rejected Quantity'),
        DTColumnBuilder.newColumn('Receipt Date').withTitle('Receipt Date'),
        DTColumnBuilder.newColumn('status').withTitle('Status').renderWith(function(data, type, full, meta) {
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
                    'wms_code': ''
                    };
   vm.model_data = {};
   angular.copy(vm.empty_data, vm.model_data);

  }

