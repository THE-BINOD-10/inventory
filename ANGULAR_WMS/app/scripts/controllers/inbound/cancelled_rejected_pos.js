'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('poCancelRejectedCtrl',['$scope', '$http', '$state', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.extra_width = { 'width': '1250px' };
    vm.selected = {};
    vm.selectAll = false;
    vm.date = new Date();
    vm.update_part = true;
    vm.is_purchase_request = true;
    vm.permissions = Session.roles.permissions;
    vm.user_profile = Session.user_profile;
    vm.industry_type = vm.user_profile.industry_type;
    vm.display_purchase_history_table = false;
    vm.warehouse_type = vm.user_profile.warehouse_type;
    vm.warehouse_level = vm.user_profile.warehouse_level;
    vm.multi_level_system = vm.user_profile.multi_level_system;
    vm.send_sku_dict = {};
    vm.cleared_data = true;
    vm.blur_focus_flag = true;
    vm.filters = {'datatable': 'RaisePendingPurchase', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'special_key': 'cancel'}
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
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('order', [0, 'desc'])
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    var columns = [ "Supplier ID", "Supplier Name", "PO Number", "PR No", "Product Category", 
                    "Category", "Total Quantity", "Total Amount",
                    "PO Created Date", "PO Delivery Date", "Store", "Department",
                     "PO Raise By",  "Validation Status", "Pending Level", "To Be Approved By",
                    "Last Updated By", "Last Updated At", "Remarks"];
    vm.dtColumns = vm.service.build_colums(columns);
    vm.dtInstance = {};
    vm.model_data = {};
    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
      $('td:not(td:first)', nRow).unbind('click');
      $('td:not(td:first)', nRow).bind('click', function() {
        $scope.$apply(function() {
          vm.extra_width = { 'width': '1250px' };
          vm.supplier_id = aData['Supplier ID'];
          var data = {requested_user: aData['Requested User'], purchase_id:aData['Purchase Id'], 
                      pending_level:aData['LevelToBeApproved']};
          // vm.dynamic_route(aData);
        });
      });
      return nRow;
    }

    vm.close = function() {
      $state.go('app.inbound.RaisePo');
    }

}

