FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('POPaymentTrackerInvBasedCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.self_life_ratio = Number(vm.permissions.shelf_life_ratio) || 0;
    vm.industry_type = Session.user_profile.industry_type;
    vm.expect_date = false;
    vm.extra_width = {width: '1050px'};

    //process type;
    vm.po_qc = true;
    vm.po_qc = (vm.permissions.receive_process == "receipt-qc")? true: false;
    vm.g_data = Data.payment_based_invoice;

    var sort_no = 5;
    vm.filters = {'datatable': 'POPaymentTrackerInvBased', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 
    				'search4': '', 'search5': ''};

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
       .withOption('order', [sort_no, 'asc'])
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
        DTColumnBuilder.newColumn('invoice_number').withTitle('Invoice Number'),
        DTColumnBuilder.newColumn('supplier_name').withTitle('Supplier Name'),
        DTColumnBuilder.newColumn('invoice_amount').withTitle('Invoice Amount'),
        DTColumnBuilder.newColumn('payment_received').withTitle('Payment Received'),
        DTColumnBuilder.newColumn('payment_receivable').withTitle('Payment Receivable'),
        DTColumnBuilder.newColumn('invoicee_date').withTitle('Invoice Date'),
        DTColumnBuilder.newColumn('due_date').withTitle('Due Date'),
    ];

    var row_click_bind = 'td';
    
    if(vm.g_data.style_view) {
      var toggle = DTColumnBuilder.newColumn('Update').withTitle('').notSortable()

                 .withOption('width', '25px').renderWith(function(data, type, full, meta) {
                   return "<span style='color: #2ECC71;text-decoration: underline;cursor: pointer;' class='invoice_data_show' ng-click='showCase.addRowData($event, "+JSON.stringify(full)+"); $event.stopPropagation()'>Update</span>";
                 })
    }

    vm.dtColumns.push(toggle);
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

    vm.addRowData = function(event, data) {
      Data.invoice_data = data;
      var elem = event.target;
      var data_tr = angular.element(elem).parent().parent();
      if ($(elem).hasClass('invoice_data_show')) {
        var html = $compile("<tr class='row-expansion' style='display: none'><td colspan='13'><dt-po-data data='"+JSON.stringify(vm.row_data)+"' preview='showCase.preview'></dt-po-data></td></tr>")($scope);
        data_tr.after(html);
        data_tr.next().toggle(1000);
        
        $(elem).removeClass();
        $(elem).addClass('invoice_data_hide');
      } else {
        $(elem).removeClass('invoice_data_hide');
        $(elem).addClass('invoice_data_show');
        data_tr.next().remove();
      }
    }

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $(row_click_bind, nRow).unbind('click');
        $(row_click_bind, nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.service.apiCall('po_get_invoice_payment_tracker/', 'GET', aData).then(function(data){
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
    vm.update = false;
    vm.model_data = {};
    vm.bank_names = '';
    if (vm.permissions.bank_option_fields != '' && vm.permissions.bank_option_fields) {
            vm.bank_names = vm.permissions.bank_option_fields.split(',');
          }
    vm.payment_modes = {'cheque': 'cheque',
                        'NEFT': 'NEFT',
                        'cash':'Cash',
                        'online':'Online'};
    vm.default_bank = vm.bank_names[0];
    vm.default_mode = "cash";

  vm.invoice_update = function(form){

    var elem = angular.element($('form'));
    elem = elem[1];
    elem = $(elem).serializeArray();
    elem.push({'name':'invoice_number', 'value':Data.invoice_data.invoice_number});

    vm.service.apiCall("po_update_payment_status/", "GET", elem).then(function(data){
      if(data.message) {
        console.log(data);
        vm.reloadData();
      }
    })
  }

  vm.change_amount = function(data, flag='') {

    if (!flag) {
      if(Number(data.amount) > Number(data.receivable)) {
        data.amount = data.receivable;
        Service.showNoty('You can enter '+data.receivable+' amount only');
      }
    } else {
      if (Number(data) > Number(Data.invoice_data.payment_receivable)) {
        vm.amount = Data.invoice_data.payment_receivable;
        Service.showNoty('You can enter '+Data.invoice_data.payment_receivable+' amount only');
      }
    }
  }

	vm.order_update = function(event){

	  var temp = event.target;
	  var parent = angular.element(temp).parents(".order-edit");
	  angular.element(parent).find(".order-update").addClass("hide");
	  angular.element(parent).find(".order-save").removeClass("hide");
      $(".update_fields").removeClass("hide");
	}

	vm.order_save = function(event, index, order){

    var temp = event.target;
    var parent = angular.element(temp).parents(".order-edit");
    var value = $(parent).find("input").val();
    var row = $($(parent).parent());
    var bank = row.find("[name='bank']").val();
    var mode_of_payment = row.find("[name='mode_of_payment']").val();
    var remarks = row.find("[name='remarks']").val();
    if(value) {
      var data = {order_id: order.order_id, amount: value,
				  bank: bank, remarks: remarks,
				  mode_of_payment: mode_of_payment}
      vm.service.apiCall("po_update_payment_status/", "GET", data).then(function(data){
        if(data.message) {

          $(parent).find("input").val("");
          angular.element(parent).find(".order-update").removeClass("hide");
          angular.element(parent).find(".order-save").addClass("hide");
          $(".update_fields").addClass("hide");

          order.receivable = Number(order.receivable) - Number(value);
          order.received = Number(order.received) + Number(value);
          if(order.inv_amount == order.received) {
            vm.model_data.data.splice(index, 1);
          }
        }
      })
    }
  }

    vm.close = close;
    function close() {
      vm.model_data = {};
      $state.go('app.PaymentTrackerInvBased');
      vm.reloadData();
    }

    vm.reloadData = function () {
      $('.custom-table').DataTable().draw();
    };
}

stockone.directive('dtPoData', function() {
  return {
    restrict: 'E',
    scope: {
      po_data: '=data',
      preview: '=preview'
    },
    templateUrl: 'views/payment_tracker/po_update_amt_datatable.html',
    link: function(scope, element, attributes, $http){
      console.log(scope);
    }
  };
});
})();
