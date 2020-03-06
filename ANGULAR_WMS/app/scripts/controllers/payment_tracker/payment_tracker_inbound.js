FUN = {};

;(function() {
'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
  stockone.controller('PaymentTrackerInbound',['$scope', '$http', '$state', 'Session', 'Service','$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, Session, Service, $q, SweetAlert, focus, $modal, $compile,Data) {

  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  
  var empty_data = { payments: [],
                     total_invoice_amount: "", total_payment_receivable: "", total_payment_received: ""
                   }

  vm.payment_data = {};
  angular.copy(empty_data, vm.payment_data);

  vm.model_data = {search:"All",filters: ["All", "Order Created", "Partially Invoiced", "Invoiced"]}

  vm.searching = function(data) {
    console.log(data);
  }

  vm.get_payment_tracker_data = function() {
    angular.copy(empty_data, vm.payment_data);
    vm.service.apiCall("invoice_payment_tracker/","GET", {filter: vm.model_data.search}).then(function(data){

      if(data.message) {

        angular.copy(data.data, vm.payment_data);
        vm.payment_data.payments = data.data.data;
      }
    })
  }
  vm.get_payment_tracker_data();

  vm.get_customer_orders = function(payment) {

   console.log(payment) ;
    if(!(payment["data"])) {
      var send = {id:payment.supplier_id, name:payment.supplier_name}
      vm.service.apiCall("supplier_invoice_data/", "GET", send).then(function(data){
  
        if(data.message) {
          payment["data"] = data.data.data;
          angular.forEach(payment["data"], function(datum, key){
            datum['show'] = false;
          })
        }
      })
    }
  }
  vm.display_acord = function (record) {
    if (record['show']) {
      record['show'] = false;
    } else {
      record['show'] = true;
    }
  }
  vm.invoice_update = function(form, data){

    var elem = angular.element($('form'));
    elem = elem[0];
    elem = $(elem).serializeArray();
    elem.push({'name':'invoice_number', 'value':data.invoice_number});

    vm.service.apiCall("po_update_payment_status/", "GET", elem).then(function(data){
      if(data.message) {
        console.log(data);
        Service.showNoty('Payment saved!');
        vm.get_payment_tracker_data();
      }
    })
  }
  vm.loadjs = function () {
      vm.PaymentTrackerInbound_enable = true;
    }

  vm.order_update = function(event){

    var temp = event.target;
    var parent = angular.element(temp).parents(".order-edit");
    angular.element(parent).find(".order_update").addClass("hide");
    angular.element(parent).find(".order-save").removeClass("hide");
  }
  vm.addRowData = function(event, data) {
      Data.invoice_data = data;
      var elem = event.target;
      var data_tr = angular.element(elem).parent().parent();
      if ($(elem).hasClass('order_update_show')) {
        var html = $compile("<tr class='row-expansion' style='display: none'><td colspan='12'><dt-po-data-out data='"+JSON.stringify(vm.row_data)+"' preview='showCase.preview'></dt-po-data-out></td></tr>")($scope);
        data_tr.after(html);
        data_tr.next().toggle(1000);
        
        $(elem).removeClass();
        $(elem).addClass('order_update_hide');
      } else {
        $(elem).removeClass('order_update_hide');
        $(elem).addClass('order_update_show');
        data_tr.next().remove();
      }
    }
  vm.bank_names = ''
  if (vm.permissions.bank_option_fields){
    vm.bank_names=vm.permissions.bank_option_fields.split(',');
  }
  // vm.bank_names = {'abc': 'abc',
  //                  'xyz': 'xyz',
  //                  'pqr': 'pqr'};
  vm.payment_modes = {'cheque': 'Cheque',
                      'NEFT': 'NEFT',
                      'online': 'Online',
                      'cash': 'Cash'};
  vm.default_bank = vm.bank_names[0];
  vm.default_mode = "";

  vm.change_amount = function(data, flag='') {

    if (!flag) {
      if(Number(data.amount) > Number(data.receivable)) {
        data.amount = data.receivable;
        Service.showNoty('You can enter '+data.receivable+' amount only');
      }
    } else {
      if (Number(data) > Number(Data.invoice_data.receivable)) {
        vm.amount = Data.invoice_data.receivable;
        Service.showNoty('You can enter '+Data.invoice_data.receivable+' amount only');
      }
    }
  }
}
  stockone.directive('dtPoDataOut', function() {
  return {
    restrict: 'E',
    scope: {
      po_data: '=data',
      preview: '=preview'
    },
    templateUrl: 'views/payment_tracker/update_alternative_amt_datatable.html',
    link: function(scope, element, attributes, $http){
      console.log(scope);
    }
  };
});
})();
