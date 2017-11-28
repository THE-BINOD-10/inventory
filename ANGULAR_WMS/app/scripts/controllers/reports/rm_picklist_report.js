'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('RMPicklistReportCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;
  vm.service = Service;
  vm.datatable = false;

  vm.empty_data = {};
  vm.model_data = {};

  vm.report_data = {};
  vm.service.get_report_data("rm_picklist_report").then(function(data) {
    angular.copy(data, vm.report_data);
    vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(data) {
      vm.empty_data = data.empty_data;
      angular.copy(vm.empty_data, vm.model_data);
      vm.dtOptions = data.dtOptions;
      vm.dtColumns = data.dtColumns;
      vm.datatable = true;
      vm.dtInstance = {};
    })
  })

  vm.print_page = "";
  vm.dtInstance = {};

  vm.empty_data = {
                    'from_date': '',
                    'to_date': '',
                    'open_po': '',
                    'wms_code': ''
                    };

  vm.model_data = {};
  angular.copy(vm.empty_data, vm.model_data);






  vm.print_excel = print_excel;
  function print_excel(id)  {
    vm.service.apiCall('/','GET',{data_id: id}).then(function(data){
      if(data.message) {
        window.location = Session.host+data.data.slice(3);
      }
    })
  }

  vm.print_pdf = print_pdf;
  function print_pdf(id) {
    vm.service.apiCall('print_rm_picklist_report/','GET',{data_id: id}).then(function(data){
      if(data.message) {
        var picklist_number = $($.parseHTML(data.data)).find("input").val()
        if (picklist_number) {
            picklist_number = 'Picklist_'+picklist_number
        } else {
            picklist_number = Picklist
        }
        vm.service.print_data(data.data, picklist_number);
      }
    })
  }




}