'use strict';

var app = angular.module('urbanApp')
app.service('Table',['$rootScope', '$compile','$q', '$http', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', Service]);

function Service($rootScope, $compile, $q, $http, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder) {

  var vm = this;

  vm.titleHtml = '<input type="checkbox" class="data-select" ng-model="showCase.selectAll" ng-change="showCase.toggleAll(showCase.selectAll, showCase.selected); $event.stopPropagation();">';

  vm.frontHtml = '<input class="data-select" type="checkbox" ng-model="showCase.selected[';
  vm.endHtml = ']" ng-change="showCase.toggleOne(showCase.selected)">';

  vm.build_colums = function(data)  {

    var columns = [];
    angular.forEach(data, function(item) {

      columns.push(DTColumnBuilder.newColumn(item).withTitle(item))
    })
    return columns;
  }

  function toggleAll (selectAll, selectedItems, event) {
    for (var id in selectedItems) {
      if (selectedItems.hasOwnProperty(id)) {
        selectedItems[id] = selectAll;
      }
    }
    vm.button_fun();
  }

  function toggleOne (selectedItems) {
    for (var id in selectedItems) {
      if (selectedItems.hasOwnProperty(id)) {
        if(!selectedItems[id]) {
          vm.selectAll = false;
          vm.button_fun();
          return;
        }
      }
    }
    vm.selectAll = true;
    vm.button_fun();
  }

  vm.button_fun = function() {

    var enable = true
    for (var id in vm.selected) {
      if(vm.selected[id]) {
        vm.bt_disable = false
        enable = false
        break;
      }
    }
    if (enable) {
      vm.bt_disable = true;
    }
  } 

  vm.datatable = {
                     titleHtml: vm.titleHtml,
                     frontHtml: vm.frontHtml,
                     endHtml: vm.endHtml,
                     toggleAll: vm.toggleAll,
                     toggleOne: vm.toggleOne,
                     button_fun: vm.button_fun,
                 }
}
