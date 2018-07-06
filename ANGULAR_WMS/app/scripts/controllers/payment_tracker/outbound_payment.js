'use strict';

angular.module('urbanApp', ['datatables'], ['angularjs-dropdown-multiselect'])
  .controller('OutboundPaymentCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, Data) {

    var vm = this;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.user_type = Session.roles.permissions.user_type;
    vm.marketplace_user = (Session.user_profile.user_type == "marketplace_user")? true: false;
    vm.date = new Date();

    vm.selected = {};
    vm.checked_items = {};
    vm.title = "Payments";
    vm.model_data = {'customers': {'customer-1': 'customer-1','customer-2': 'customer-2','customer-3': 'customer-3'}};
    vm.bank_names = {'abc': 'abc',
                     'xyz': 'xyz',
                     'pqr': 'pqr'};

    $timeout(function () {
        $('.selectpicker').selectpicker();
    }, 500);

    vm.g_data = Data.payment_based_invoice;
    // vm.g_data.style_view = true;

    var sort_no = (vm.g_data.style_view)? 1: 0;
    vm.filters = {'datatable': 'OutboundPaymentBased', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 
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
       // .withOption('initComplete', function( settings ) {
       //   vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       // });

    vm.dtColumns = [
        DTColumnBuilder.newColumn('invoice_number').withTitle('Invoice Number'),
        DTColumnBuilder.newColumn('customer_name').withTitle('Customer Name'),
        DTColumnBuilder.newColumn('invoice_amount').withTitle('Invoice Amount'),
        DTColumnBuilder.newColumn('payment_received').withTitle('Payment Received'),
        DTColumnBuilder.newColumn('payment_receivable').withTitle('Payment Receivable'),
        DTColumnBuilder.newColumn('invoice_date').withTitle('Invoice Date'),
        DTColumnBuilder.newColumn('due_date').withTitle('Due Date'),
    ];

    var row_click_bind = 'td';

    if(vm.g_data.style_view) {
      var toggle = DTColumnBuilder.newColumn('Update').withTitle('').notSortable()

                 .withOption('width', '25px').renderWith(function(data, type, full, meta) {
                   return "<button type='submit' class='btn btn-primary pull-right' style='margin: auto;display: block;' class='invoice_data_show' ng-click='showCase.addRowData($event, "+JSON.stringify(full)+"); $event.stopPropagation()'>Mark As Paid</button>";
                 })
    }

    vm.dtColumns.push(toggle);
    vm.dtInstance = {};
    vm.poDataNotFound = function() {
      // $(elem).removeClass();
      // $(elem).addClass('fa fa-plus-square');
      Service.showNoty('Something went wrong')
    }

    vm.addRowData = function(event, data) {
      Data.invoice_data = data;
      var elem = event.target;
      var data_tr = angular.element(elem).parent().parent();
      if ($(elem).hasClass('invoice_data_show')) {
        var html = $compile("<tr class='row-expansion' style='display: none'><td colspan='13'><dt-po-data-out data='"+JSON.stringify(vm.row_data)+"' preview='showCase.preview'></dt-po-data-out></td></tr>")($scope);
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

    /*vm.service.apiCall("customer_invoice_data/", "GET", send).then(function(data) {
      if(data.message) {
        console.log(data);
      }
    });*/

    vm.multi_select_switch = function(selector) {
      var data = $(selector).val();
      if(!data) {
        data = [];
      }
      var send = data.join(",");
      vm.switches(send);
    }

    vm.switches = switches;
    function switches(value) {
      console.log(value);
      vm.model_data['sel_customers'] = [];

      if (value) {

        var sel_records = value.split(',');
        
        for (var i = 0; i < sel_records.length; i++) {
          vm.model_data.sel_customers.push({'name':sel_records[i], 'amount':100});
        }
      }
    }



    vm.check_selected = function(opt, name) {
      if(!vm.model_data[name]) {
        return false;
      } else {
        return (vm.model_data[name].indexOf(opt) > -1) ? true: false;
      }
    }

    vm.markAsPaid = function(form){
      console.log(form);
    }

    /*vm.reloadData = function () {
      $('.custom-table').DataTable().draw();
    };


    vm.close = function() {

      $state.go("app.outbound.CustomerInvoices")
    }*/
}

stockone.directive('dtPoDataOut', function() {
  return {
    restrict: 'E',
    scope: {
      po_data: '=data',
      preview: '=preview'
    },
    templateUrl: 'views/payment_tracker/update_amt_datatable.html',
    link: function(scope, element, attributes, $http){
      console.log(scope);
    }
  };
});