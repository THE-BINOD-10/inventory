'use strict';

var apps1 = angular.module('urbanApp', ['datatables']);
apps1.controller('VendorStockTransferCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.selected = {};
    vm.generate_data = [];
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.permissions = Session.roles.permissions;
    vm.industry_type = Session.user_profile.industry_type;
    vm.user_type = Session.user_profile.user_type;
    console.log(vm.permissions)
    console.log(vm.industry_type)
    console.log(vm.user_type)
    console.log(vm.permissions.production_switch)
    if (vm.permissions.production_switch == 'true') {
      vm.tabheader = 'Vendor Stock Transfer'
    }else {
      vm.tabheader = ''
    }
    console.log(vm.tabheader)
}
