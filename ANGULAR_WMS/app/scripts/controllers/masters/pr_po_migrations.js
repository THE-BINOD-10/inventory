;(function(){

'use strict';

var app = angular.module('urbanApp', [''])
app.controller('PRPOMigrations',['$scope', 'Session', 'Service', '$modal', PRPOMigrations]);

function PRPOMigrations($scope, Session, Service, $modal) {

  var vm = this;
  vm.edit_form = false;
  vm.model_data = {};
  vm.model_data['response'] = '';
  vm.model_pr_po_data = {};
  vm.host = Session.host;
  vm.service = Service;
  vm.process = false;
  vm.emptyData = function () {
    vm.model_data = {}
    vm.model_data.source_staff = '';
    vm.model_data.dest_staff = '';
    vm.model_data['response'] = '';
    vm.display_inputs = false;
    vm.confirm_btn_final = false;
  }
  vm.emptyData();
  vm.search_staff_pr_pos = function() {
    if (vm.model_data.source_staff.includes(':') && vm.model_data.source_staff.split(':').length == 2) {
      Service.apiCall('get_staff_pr_po_data/', 'POST', vm.model_data).then(function(data){
        if(data.message) {
          if (typeof(data.data)=='string') {
            Service.showNoty('Invalid Source Staff Email !');
          } else {
            vm.model_data['response'] = {};
            angular.copy(data.data.data, vm.model_data.response);
            if (Object.keys(vm.model_data.response.PR).length > 0 || Object.keys(vm.model_data.response.PO).length > 0) {
              vm.display_inputs = true;
            }
          }
        } else {
          vm.emptyData();
          Service.showNoty('Something Went Wrong, Contact Admin');
        }
      });
    } else {
      Service.showNoty('Invalid Source Staff Email !');
    }
  }

  vm.empty_check_data = function() {
    if (vm.model_data.source_staff == vm.model_data.dest_staff) {
      vm.emptyData();
      Service.showNoty('Source Staff EmailId & Destination Email ID should not match');
    }
  }

  vm.migrate_staff_pr_pos = function() {
    if (vm.model_data.source_staff && vm.model_data.dest_staff) {
      var send_dict = {
        'source': vm.model_data.source_staff,
        'dest': vm.model_data.dest_staff,
        'PO_IDS': JSON.stringify(vm.model_data.response.PO_IDS),
        'PR_IDS': JSON.stringify(vm.model_data.response.PR_IDS),
        'PR_PO_IDS': JSON.stringify(vm.model_data.response.PR_PO_IDS)
      }
      vm.confirm_btn_final = true;
      swal2({
        title: "Migrating All PR & PO's",
        text: vm.model_data.source_staff + ' to ' + vm.model_data.dest_staff,
        imageUrl: 'images/default_loader.gif',
        imageWidth: 150,
        imageHeight: 150,
        imageAlt: 'Custom image',
        showConfirmButton:false,
        allowOutsideClick: false,
      })
      Service.apiCall('migrate_staff_user_pr_pos/', 'POST', send_dict).then(function(data){
        if(data.message) {
          if (data.data == 'Success') {
            swal2.close();
            vm.emptyData();
            Service.showNoty(data.data);
          } else {
            swal2.close();
            vm.confirm_btn_final = false;
            Service.showNoty(data.data);
          }
        } else {
          vm.emptyData();
          swal2.close();
          Service.showNoty('Something Went Wrong, Contact Admin');
        }
      });
    } else {
      swal2.close();
      vm.confirm_btn_final = false;
      Service.showNoty('Please Enter Source & Destination Staff Emails');
    }
  }
}

})();
