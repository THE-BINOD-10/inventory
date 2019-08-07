'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('OrderflowCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.service = Service;
  vm.datatable = false;

  vm.empty_data = {};
  vm.model_data = {};
  vm.isprava_permission = Session.roles.permissions.order_exceed_stock;
  vm.report_data = {};
  vm.service.get_report_data("order_flow_report").then(function(data) {
    angular.copy(data, vm.report_data);
    vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(data) {
      vm.empty_data = data.empty_data;
      angular.copy(vm.empty_data, vm.model_data);
      vm.dtOptions = data.dtOptions;
      vm.dtColumns = [
            DTColumnBuilder.newColumn('Order Id').withTitle('Central Order Id'),    
      ];
      if(!vm.isprava_permission){
        vm.dtColumns.push(DTColumnBuilder.newColumn('Main SR Number').withTitle('Main SR Number'))
      }
      vm.dtColumns.push(
            DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
            DTColumnBuilder.newColumn('SKU Description').withTitle('SKU Description'),
            DTColumnBuilder.newColumn('Customer Name').withTitle('Customer Name'))
      if(vm.isprava_permission){
        vm.dtColumns.push(
            DTColumnBuilder.newColumn('Project Name').withTitle('Project Name'),
            DTColumnBuilder.newColumn('Category').withTitle('Category'),
            DTColumnBuilder.newColumn('Price').withTitle('Price'))
      }
      if(!vm.isprava_permission){
        vm.dtColumns.push(DTColumnBuilder.newColumn('Address').withTitle('Address'),
            DTColumnBuilder.newColumn('Phone No').withTitle('Phone No'),
            DTColumnBuilder.newColumn('Email Id').withTitle('Email Id'),
            DTColumnBuilder.newColumn('Alt SKU').withTitle('Alt SKU')
          )
      }
      vm.dtColumns.push(DTColumnBuilder.newColumn('Central order status').withTitle('Central order status'),
            DTColumnBuilder.newColumn('Central Order cancellation remarks').withTitle('Central Order cancellation remarks'),
            DTColumnBuilder.newColumn('Hub location').withTitle('Hub location')
        )
      if(vm.isprava_permission){
        vm.dtColumns.push(
            DTColumnBuilder.newColumn('Order Date').withTitle('Order Date'),
            DTColumnBuilder.newColumn('Expected Date').withTitle('Expected Date')
          )
      }
      vm.dtColumns.push(DTColumnBuilder.newColumn('Hub location order status').withTitle('Hub location order status'))
      if(!vm.isprava_permission){
        vm.dtColumns.push(DTColumnBuilder.newColumn('Order cancellation remarks').withTitle('Order cancellation remarks'),
            DTColumnBuilder.newColumn('Outbound Qc params').withTitle('Outbound Qc params'),
            DTColumnBuilder.newColumn('Serial Number').withTitle('Serial Number'),
            DTColumnBuilder.newColumn('Shipment Status').withTitle('Shipment Status'),
            DTColumnBuilder.newColumn('Acknowledgement status').withTitle('Acknowledgement status'),
            DTColumnBuilder.newColumn('Receive PO status').withTitle('Receive PO status'),
            DTColumnBuilder.newColumn('PO cancellation remarks').withTitle('PO cancellation remarks'),
            DTColumnBuilder.newColumn('Inbound Qc params').withTitle('Inbound Qc params'),
            DTColumnBuilder.newColumn('SKU damage payment remarks').withTitle('SKU damage payment remarks')
          )
      }
      vm.datatable = true;
      vm.dtInstance = {};
    })
  })

  vm.print_page = "";
  vm.dtInstance = {};

  vm.empty_data = {
                    'from_date': '',
                    'to_date': '',
                    'sku_code': '',
                    'sister_warehouse' :''
                    };

  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);

}
