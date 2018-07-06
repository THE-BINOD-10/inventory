'use strict';

angular.module('urbanApp', ['datatables'], ['angularjs-dropdown-multiselect'])
  .controller('OutboundPaymentCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, Service, $modal) {

    var vm = this;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.user_type = Session.roles.permissions.user_type;
    vm.marketplace_user = (Session.user_profile.user_type == "marketplace_user")? true: false;
    vm.date = new Date();

    vm.selected = {};
    vm.checked_items = {};
    vm.title = "Payments";
    vm.model_data = {'customers': {'customer-1': 'customer-1','customer-2': 'customer-2','customer-3': 'customer-3'},
                     'banks': ['SBI','Andhra Bank','ICICI','YES']};

    $timeout(function () {
        $('.selectpicker').selectpicker();
    }, 500);

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
