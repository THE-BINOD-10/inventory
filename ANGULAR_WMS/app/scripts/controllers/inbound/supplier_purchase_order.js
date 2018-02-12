FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('SupplierPOCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.filters = {'datatable': 'ReceivePO', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': '', 'search5': '',
                  'search6': '', 'search7': '', 'search8': '', 'style_view': true}
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
       .withOption('order', [1, 'desc'])
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
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    var columns = ['PO No', 'Customer Name', 'Order Date', 'Total Qty', 'Receivable Qty', 'Received Qty',
                   'Supplier ID/Name', 'Expected Date', 'Remarks', 'Order Type', 'Receive Status'];
    vm.dtColumns = vm.service.build_colums(columns);

    var row_click_bind = 'td';
    var toggle = DTColumnBuilder.newColumn('PO No').withTitle(' ').notSortable()
                 .withOption('width', '25px').renderWith(function(data, type, full, meta) {
                   return "<i ng-click='showCase.addRowData($event, "+JSON.stringify(full)+")' class='fa fa-plus-square'></i>";
                 })
    row_click_bind = 'td:not(td:first)';
    vm.dtColumns.unshift(toggle);

    vm.dtInstance = {};
    vm.poDataNotFound = function() {
      $(elem).removeClass();
      $(elem).addClass('fa fa-plus-square');
      Service.showNoty('Something went wrong')
    }
    vm.addRowData = function(event, data) {
      console.log(data);
      var elem = event.target;
      if (!$(elem).hasClass('fa')) {
        return false;
      }
      var data_tr = angular.element(elem).parent().parent();
      if ($(elem).hasClass('fa-plus-square')) {
        $(elem).removeClass('fa-plus-square');
        $(elem).removeClass();
        $(elem).addClass('glyphicon glyphicon-refresh glyphicon-refresh-animate');
        var po_number = data['PO No'].split("_")[1];
        Service.apiCall('get_receive_po_style_view/?order_id='+po_number).then(function(resp){
          if (resp.message){

            if(resp.data.status) {
              var html = $compile("<tr class='row-expansion' style='display: none'><td colspan='13'><dt-supplier-po-data data='"+JSON.stringify(resp.data.data_dict)+"' send='showCase.send' po='"+po_number+"'></dt-supplier-po-data></td></tr>")($scope);
              data_tr.after(html)
              data_tr.next().toggle(1000);
              $(elem).removeClass();
              $(elem).addClass('fa fa-minus-square');
            } else {
              vm.poDataNotFound();
            }
          } else {
            vm.poDataNotFound();
          }
        })
      } else {
        $(elem).removeClass('fa-minus-square');
        $(elem).addClass('fa-plus-square');
        data_tr.next().remove();
      }
    }

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

  vm.send = function(form, po) {

    var d = $q.defer();
    var data = $("form[data-attr='"+po+"']").serializeArray();
    Service.apiCall('save_supplier_po/', 'POST', data).then(function(resp) {

      if(resp.message) {

        console.log(resp.data);
        Service.showNoty(resp.data);
        if(resp.data == 'Success') {
          Service.refresh(vm.dtInstance);
        }
        d.resolve('Update Successfully');
      } else {
        d.resolve('something went wrong');
      }
    });
    console.log(form);
    return d.promise;
  }
}

stockone.directive('dtSupplierPoData', function() {
  return {
    restrict: 'E',
    scope: {
      po_data: '=data',
      send: '=send',
      po: '=po'
    },
    templateUrl: 'views/inbound/toggle/supplier_po_data_html.html',
    link: function(scope, element, attributes, $http){
      scope.date = new Date();
      scope.send_data = function(form, po) {
        scope.disable = true;
        scope.send(form, po).then(function(data){
          console.log(data);
          scope.disable = false;
        });
      }
    }
  };
});

})();
