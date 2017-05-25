'use strict';

angular.module('urbanApp', ['angularjs-dropdown-multiselect'])
  .controller('TallyConfigCtrl',['$scope', '$http', '$state', '$compile', 'Session' , 'Auth', '$timeout', 'Service', 'SweetAlert', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, Auth, $timeout, Service, SweetAlert) {
  var vm = this;
  vm.service = Service;
  vm.model_data = {};
  //vm.model_data['ledger_cust_mapping'] = [{'product': '', 'state': '', 'ledger': ''}];
  //vm.model_data['vat_calculation'] = [{'percentage': '5.5', 'ledger': 'VAT@5.5'}, {'percentage': '6', 'ledger': 'VAT@6.0'}];
  //vm.model_data['customer'] = [{'customer': 'All Customers', 'group': 'Sundry Debtors', 'ledger': 'All Customers'}];
  //vm.model_data['supplier'] = [{'customer': 'All Suppliers', 'group': 'Sundry Debtors', 'ledger': 'All Suppliers'}];
  //vm.model_data['price'] = '30';

  vm.submit = function(data){
    console.log(vm.model_data);
    var send = $("form:visible").serializeArray();
    if(data.$valid) {
      vm.service.apiCall("save_tally_data/" , "POST", send).then(function(data){

        if(data.message) {

          vm.service.showNoty(data.data.message);
        }
      })
    }
  }

  vm.service.apiCall("get_tally_data/").then(function(data){

    vm.data = data.data.data;
  });

  vm.empty = { basic: { machine_details: "", port: "", path: "", company_name: "", bill_wise: false, no_config: false},
               item: { stock_group: "", stock_category: ""},
               customer: [],
               vendor: [],
               sales_ledger_map: [{product_group: "", state: "", name: ""}],
               sales_vat: [{vat_percentage: "", name: ""}],
               purchase_ledger_map: [{product_group: "", state: "", name: ""}],
               purchase_vat: [{vat_percentage: "", name: ""}]
             }
  angular.copy(vm.empty, vm.model_data);

  vm.remove = function(data, index, name) {

    if (data[index].id) {
      vm.service.apiCall("delete_tally_data/?"+name+"="+data[index].id).then(function(resp){

        if(resp.message) {

          data.splice(index,1);
          vm.service.showNoty("Deleted Successfully");
        }
      })
    } else {

      data.splice(index,1);
    }
  }

  vm.checkStateGroup = function(data, index) {

    var current_data = data[index];
    for(var i = 0; i < data.length; i++) {

      if(index != i) {

        if(data[i].product_group == current_data.product_group && data[i].state == current_data.state) {

          //alert("This combination already existed");
          SweetAlert.swal({
               title: '',
               text: 'This combination already existed',
               type: 'warning',
               showCancelButton: false,
               confirmButtonColor: '#33cc66',
               confirmButtonText: 'Ok',
               closeOnConfirm: true,
             },
             function (status) {
               data.splice(index, 1);
             }
          );
          break;
        }
      }
    }
  }

  vm.checkPercentageLedger = function(data, index) {

    var current_data = data[index];
    for(var i = 0; i < data.length; i++) {

      if(index != i) {

        if(data[i].ledger_name == current_data.ledger_name) {

          SweetAlert.swal({
               title: '',
               text: 'Ledger name already existed',
               type: 'warning',
               showCancelButton: false,
               confirmButtonColor: '#33cc66',
               confirmButtonText: 'Ok',
               closeOnConfirm: true,
             },
             function (status) {
               data.splice(index, 1);
             }
          );
          break;
        }
      }
    }
  }

  vm.display = function(data){console.log(data)};
}
