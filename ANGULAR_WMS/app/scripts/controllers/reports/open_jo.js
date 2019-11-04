'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('OpenJOCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {

  var vm = this;

  vm.service = Service;
  vm.datatable = false;
  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;


  vm.empty_data = {}
  vm.model_data = {};

  vm.report_data = {};
  vm.service.get_report_data("open_jo_report").then(function(data){

    angular.copy(data, vm.report_data);
    vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(data){

      vm.empty_data = data.empty_data;
      angular.copy(vm.empty_data, vm.model_data);
      vm.dtOptions = data.dtOptions;
      vm.dtColumns = data.dtColumns;
      vm.datatable = true;
      vm.dtInstance = {};
    })
  })

  }
