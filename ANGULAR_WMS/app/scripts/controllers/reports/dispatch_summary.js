'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('DispatchSummaryCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, Data) {

    var vm = this;
    vm.service = Service;
    vm.service.print_enable = false;

    vm.g_data = Data.dispatch_summary_report;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'get_dispatch_filter/',
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

    /*vm.dtColumns = [
        DTColumnBuilder.newColumn('Order ID').withTitle('Order ID'),
        DTColumnBuilder.newColumn('WMS Code').withTitle('WMS Code'),
        DTColumnBuilder.newColumn('Description').withTitle('Description'),
        DTColumnBuilder.newColumn('Location').withTitle('Location'),
        DTColumnBuilder.newColumn('Quantity').withTitle('Quantity'),
        DTColumnBuilder.newColumn('Picked Quantity').withTitle('Picked Quantity'),
        DTColumnBuilder.newColumn('Date').withTitle('Date'),
        DTColumnBuilder.newColumn('Time').withTitle('Time')
    ];*/

    vm.dtColumns = vm.service.build_colums(vm.g_data.tb_headers[vm.g_data.view]);

   vm.dtInstance = {};

   vm.empty_data = {
                    'from_date': '',
                    'to_date': '',
                    'wms_code': '',
                    'sku_code': '',
                    'order_id': '',
                    'imei_number': ''
                    };

   vm.model_data = {};
   angular.copy(vm.empty_data, vm.model_data);

  vm.change_datatable = function() {
    Data.dispatch_summary_report.view = (vm.g_data.alternate_view)? 'serialView': 'normalView';
    $state.go($state.current, {}, {reload: true});
  }

  }

