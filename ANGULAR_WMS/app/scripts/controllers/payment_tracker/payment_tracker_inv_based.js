FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('PaymentTrackerInvBasedCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.self_life_ratio = Number(vm.permissions.shelf_life_ratio) || 0;
    vm.industry_type = Session.user_profile.industry_type;

    //process type;
    vm.po_qc = true;
    vm.po_qc = (vm.permissions.receive_process == "receipt-qc")? true: false;
    vm.g_data = Data.receive_po;

    var sort_no = (vm.g_data.style_view)? 1: 0;
    vm.filters = {'datatable': 'PaymentTrackerInvBased', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 
    				'search4': '', 'search5': ''};
    // vm.filters = {'datatable': 'ReceivePO', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': '', 'search5': '',
    //               'search6': '', 'search7': '', 'search8': '', 'search9': '', 'search10': '', 'style_view': vm.g_data.style_view};
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
       .withOption('order', [sort_no, 'desc'])
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withOption('createdRow', function(row, data, dataIndex) {
            $compile(angular.element(row).contents())($scope);
        })
        .withOption('headerCallback', function(header) {
            if (!vm.headerCompiled) {
                vm.headerCompiled = true;
                $compile(angular.element(header).contents())($scope);
            }
        })
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    vm.dtColumns = [
        DTColumnBuilder.newColumn('invoice_date').withTitle('Invoice Date'),
        DTColumnBuilder.newColumn('invoice_number').withTitle('Invoice Number'),
        DTColumnBuilder.newColumn('customer_name').withTitle('Customer Name'),
        DTColumnBuilder.newColumn('invoice_amount').withTitle('Invoice Amount'),
        DTColumnBuilder.newColumn('payment_received').withTitle('Payment Received'),
        DTColumnBuilder.newColumn('payment_receivable').withTitle('Payment Receivable'),
    ];

    var row_click_bind = 'td';
    
    // vm.dtColumns.unshift(toggle);
    vm.dtInstance = {};
    vm.poDataNotFound = function() {
      $(elem).removeClass();
      $(elem).addClass('fa fa-plus-square');
      Service.showNoty('Something went wrong')
    }

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $(row_click_bind, nRow).unbind('click');
        $(row_click_bind, nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.service.apiCall('get_invoice_payment_tracker/', 'GET', aData).then(function(data){
                  if(data.message) {
                    vm.serial_numbers = [];
                    angular.copy(data.data, vm.model_data);
                    vm.title = "Invoice Based Payment";
                    vm.update = true;

                    $state.go('app.PaymentTrackerInvBased.Inv_Details');
                    $timeout(function () {
                      $(".customer_status").val(vm.model_data.status);
                    }, 500);
                  }
                });
            });
        });
        return nRow;
    }

    vm.filter_enable = true;
    vm.print_enable = false;
    vm.update = false;
    vm.model_data = {};

    vm.change_amount = function(data) {

	  if(Number(data.amount) > data.receivable) {
	    data.amount = data.receivable;
	  }
	}

	vm.order_update = function(event){

	  var temp = event.target;
	  var parent = angular.element(temp).parents(".order-edit");
	  angular.element(parent).find(".order-update").addClass("hide");
	  angular.element(parent).find(".order-save").removeClass("hide");
	}

	vm.order_save = function(event, index, order){

    var temp = event.target;
    var parent = angular.element(temp).parents(".order-edit");
    var value = $(parent).find("input").val();
    if(value) {
      var data = {order_id: order.order_id, amount: value}
      vm.service.apiCall("update_payment_status/", "GET", data).then(function(data){
        if(data.message) {

          $(parent).find("input").val("");
          angular.element(parent).find(".order-update").removeClass("hide");
          angular.element(parent).find(".order-save").addClass("hide");

          order.receivable = Number(order.receivable) - Number(value);
          order.received = Number(order.received) + Number(value);
          // customer.payment_receivable = Number(customer.payment_receivable) - Number(value);
          // customer.payment_received = Number(customer.payment_received) + Number(value);
          // vm.payment_data.total_payment_receivable = Number(vm.payment_data.total_payment_receivable) - Number(value);
          // vm.payment_data.total_payment_received = Number(vm.payment_data.total_payment_received) + Number(value);
          if(order.inv_amount == order.received) {
            vm.model_data.data.splice(index, 1);
          }
          // if (customer.payment_received == customer.invoice_amount) {
          //   vm.payment_data.payments.splice(index2, 1);
          // }
        }
      })
    }
  }

    vm.close = close;
    function close() {
      vm.model_data = {};
      $state.go('app.PaymentTrackerInvBased');
    }

}

})();