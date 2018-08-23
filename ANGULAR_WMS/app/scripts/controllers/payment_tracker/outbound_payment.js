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
    vm.model_data = {'payment':'', 'balance':'', 'date':'', 'update_tds':'', 'bank_name':'', 'mode_of_pay':'', 'neft_cheque':''};
    vm.bank_names = {'abc': 'abc',
                     'xyz': 'xyz',
                     'pqr': 'pqr'};

    vm.mode_of_pay = ['NEFT', 'CHEQUE'];

    $timeout(function () {
        $('.selectpicker').selectpicker();
    }, 500);

    vm.g_data = Data.payment_based_invoice;
    // vm.g_data.style_view = true;

    var sort_no = (vm.g_data.style_view)? 1: 0;
    vm.filters = {'datatable': 'PaymentTrackerInvBased', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 
            'search4': '', 'search5': ''};

    vm.dtOptions = DTOptionsBuilder.newOptions()

    localStorage.setItem("mark_paid", "{}");
    vm.dtColumns = [
        DTColumnBuilder.newColumn(null).withTitle('').notSortable()
                 .withOption('width', '25px').renderWith(function(data, type, full, meta) {
                   var paid = JSON.parse(localStorage.getItem("mark_paid"));
                   if (Object.keys(paid).indexOf(data.invoice_number) === -1){
                    var btn = "<button type='submit' class='btn btn-primary pull-right paid_mode'" +
                              "style='margin: auto;display: block;'" +
                              "ng-click='showCase.calDtRowAmount($event, "+JSON.stringify(full)+"); $event.stopPropagation()'" +
                              ">Mark As Paid</button>";
                   } else {
                    var btn = "<button type='submit' class='btn btn-danger pull-right un_paid_mode'" +
                              "style='margin: auto;display: block;'" +
                              "ng-click='showCase.calDtRowAmount($event, "+JSON.stringify(full)+"); $event.stopPropagation()'" +
                              ">Mark As Unpaid</button>";
                   }

                   return btn
                 }),
        DTColumnBuilder.newColumn('invoice_number').withTitle('Invoice Number'),
        DTColumnBuilder.newColumn('customer_name').withTitle('Customer Name'),
        DTColumnBuilder.newColumn('invoice_amount').withTitle('Invoice Amount'),
        DTColumnBuilder.newColumn('payment_received').withTitle('Payment Received').renderWith(function(data, type, full, meta) {
            var paid = JSON.parse(localStorage.getItem("mark_paid"));
            if(paid[full.invoice_number]){
                return String(Number(data) + paid[full.invoice_number]);
            } else {
                return data;
            }
        }),
        DTColumnBuilder.newColumn('payment_receivable').withTitle('Payment Receivable').renderWith(function(data, type, full, meta) {
            var paid = JSON.parse(localStorage.getItem("mark_paid"));
            if(paid[full.invoice_number]){
                return String(Number(data) - paid[full.invoice_number]);
            } else {
                return data;
            }
        }),
        DTColumnBuilder.newColumn('invoice_date').withTitle('Invoice Date'),
        DTColumnBuilder.newColumn('due_date').withTitle('Due Date'),
    ];

    var row_click_bind = 'td';

    
    if(vm.g_data.style_view) {
      var toggle = DTColumnBuilder.newColumn(null).withTitle('').notSortable()
                 .withOption('width', '25px').renderWith(function(data, type, full, meta) {
                   return "<span style='color: #2ECC71;text-decoration: underline;cursor: pointer;' class='invoice_data_show' ng-click='showCase.addRowData($event, "+JSON.stringify(full)+"); $event.stopPropagation()'>Update</span>";
                 })
    }
    vm.dtColumns.push(toggle);
    
    vm.dtInstance = {};
    vm.poDataNotFound = function() {
      // $(elem).removeClass();
      // $(elem).addClass('fa fa-plus-square');
      Service.showNoty('Something went wrong')
    }

    vm.change_payment = function(payment){
      
      if (vm.model_data.update_tds) {

        vm.model_data.balance = payment - vm.model_data.update_tds;
      } else {

        vm.model_data.balance = payment;
      }

      if (vm.dt_rows_changed) {

        var total_amt = 0;
        
        angular.forEach(vm.dt_rows_changed, function(row){

          row.enter_amount = Number(payment);
          row.balance = Number(payment) - Number(row.amount);
          total_amt += Number(row.amount);
        });

        vm.model_data.balance = Number(payment) - Number(total_amt);
      }

      vm.bkp_balance = vm.model_data.balance;
    }

    vm.bkp_tds = 0;
    vm.dt_rows_changed = [];
    vm.calDtRowAmount = function(event, data){

      if (vm.model_data.payment) {
        var elem = event.target;
        if ($(elem).hasClass('paid_mode')) {

          if (vm.model_data.balance == 0){
            Service.showNoty('Balance is low');
          } else {
            if (!vm.model_data.balance) {
              vm.model_data.balance = Number(vm.model_data.payment);
            }
            data.amount = Math.min(Number(data.payment_receivable), Number(vm.model_data.balance));
            data.payment_received = Number(data.payment_received) + data.amount;
            data.enter_amount = Number(vm.model_data.payment);
            data.bank_name = vm.model_data.bank_name;
            data.balance = Number(vm.model_data.balance) - data.amount;
            data.date = vm.model_data.date;
            data.mode_of_pay = vm.model_data.mode_of_pay;
            data.neft_cheque = vm.model_data.neft_cheque;
            data.update_tds = vm.model_data.update_tds;
            vm.model_data.balance = data.balance;

            vm.bkp_balance = vm.model_data.balance;
            if (vm.model_data.update_tds) {

              vm.bkp_tds = vm.model_data.update_tds;
            }

            vm.dt_rows_changed.push(data);
            var mark_paid = JSON.parse(localStorage.getItem("mark_paid"));
            mark_paid[data.invoice_number] = data.amount;
            localStorage.setItem("mark_paid", JSON.stringify(mark_paid));

            $(elem).removeClass();
            $(elem).text('Mark As Unpaid');
            $(elem).addClass('btn btn-danger pull-right un_paid_mode');
            vm.reloadData();
          }
        } else {

          var mark_paid = JSON.parse(localStorage.getItem("mark_paid"));
          for (var i = 0; i < vm.dt_rows_changed.length; i++) {
            if (data.invoice_number == vm.dt_rows_changed[i]['invoice_number']) {

              vm.model_data.balance = Number(vm.model_data.balance) + vm.dt_rows_changed[i]['amount'];
              vm.bkp_balance = vm.model_data.balance;
              if (vm.model_data.update_tds) {

                vm.bkp_tds = vm.model_data.update_tds;
              }
              vm.dt_rows_changed.splice(i,1);
              delete mark_paid[data.invoice_number];
              localStorage.setItem("mark_paid", JSON.stringify(mark_paid));
              break;
            }
          }

          $(elem).removeClass();
          $(elem).text('Mark As Paid');
          $(elem).addClass('btn btn-primary pull-right paid_mode');
          vm.reloadData();
        }
      } else {

        vm.service.showNoty('Please enter payment amount first');
      }
    }

    vm.sendChangedData = function(){

      if (!vm.model_data.balance) {

        angular.forEach(vm.dt_rows_changed, function(row){

          row.bank_name = vm.model_data.bank_name;
          row.date = vm.model_data.date;
          row.mode_of_pay = vm.model_data.mode_of_pay;
          row.neft_cheque = vm.model_data.neft_cheque;
          row.update_tds = vm.model_data.update_tds;
          row.neft_cheque = vm.model_data.neft_cheque;  
        });

        var elem = {'data': vm.dt_rows_changed};

        vm.service.apiCall('update_payment_status/', 'POST', elem).then(function(data){
          if(data.message) {
            vm.service.showNoty(data.data.message);
            $state.go($state.current, {}, {reload: true});
          }
        });
      } else {

        vm.service.showNoty('Balance should be "Zero"'); 
      }
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

    vm.service.apiCall("get_customer_list/").then(function(data) {
      if(data.message) {
        console.log(data);
        vm.model_data['customers_info'] = data.data.data;
      }
    });

    vm.outbound_payment_dt = function(cust_ids){
      vm.filters['customer_ids'] = cust_ids;
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
       //.withOption('rowCallback', rowCallback)uncomment for popup
       // .withOption('initComplete', function( settings ) {
       //   vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       // });
    }

    vm.multi_select_switch = function(selector) {
      var data = $(selector).val();
      if(!data) {
        data = [];
      } else {
        vm.customer_ids = [];
        for (var i = 0; i < data.length; i++) {
          vm.customer_ids.push(angular.fromJson(data[i]).customer_id);
        }
      }
      var send = data.join(" ,");
      vm.switches(send);
    }

    vm.switches = switches;
    function switches(value) {
      console.log(value);
      vm.model_data['sel_customers'] = [];

      if (value) {

        var sel_records = value.split(' ,');
        
        for (var i = 0; i < sel_records.length; i++) {
          vm.model_data.sel_customers.push(angular.fromJson(sel_records[i]));
        }
        vm.outbound_payment_dt(vm.customer_ids.join(" ,"));
      }
    }

    vm.tdsValidation = function(tds_value, balance){

      if (vm.bkp_tds) {

        vm.model_data.balance = vm.model_data.balance + (vm.bkp_tds - tds_value);
        vm.bkp_tds = tds_value;
        vm.bkp_balance = vm.model_data.balance;
      } else {

        if (tds_value > vm.bkp_balance) {

          vm.service.showNoty('You can reduce only '+vm.bkp_balance+' rupees');
          vm.model_data.update_tds = vm.bkp_balance;
          vm.model_data.balance = 0;
        } else {

          vm.model_data.balance = (vm.bkp_balance - tds_value);
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

    vm.reloadData = function () {
      $('.custom-table').DataTable().draw();
    };


    vm.close = function() {

      $state.go("app.PaymentTrackerInvBased")
    }
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
