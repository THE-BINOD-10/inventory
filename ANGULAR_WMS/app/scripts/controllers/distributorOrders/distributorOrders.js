'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('distirbutorOrdersTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', 'Data', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service,  Data, $modal) {
    var vm = this;
    vm.cancelPoDisable = false;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.user_type = Session.roles.permissions.user_type;
    vm.filters = {'datatable': 'DistributorOrdersData', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
       .withOption('rowCallback', rowCallback);
    vm.dtColumns = [
        DTColumnBuilder.newColumn('distributor').withTitle('Distributor'),
        DTColumnBuilder.newColumn('order_id').withTitle('Order ID'),
        DTColumnBuilder.newColumn('emizaids').withTitle('Emiza Order IDs'),
        DTColumnBuilder.newColumn('uploaded_date').withTitle('Date'),
        DTColumnBuilder.newColumn('tot_qty').withTitle('Order Qty')
    ];
    vm.dtInstance = {};
    vm.reloadData = reloadData;

    vm.customer_name=true;

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.reloadData();
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
                vm.model_data = {};
                vm.update = true;
                vm.message = "";
                vm.title = "Order Detail";
                var sendData = {gen_ord_id:aData.order_id, distributor:aData.dist_cust_id};

                vm.service.apiCall("get_distributor_order/", "POST", sendData, true).then(function(data) {
                  if(data.message) {
                    angular.copy(data.data, vm.model_data);
                    $state.go('app.distributorOrders.IndividualOrder');
                  }
                });
            });
        });
        if(vm.filter_enable){
          vm.filter_enable = false;
          vm.apply_filters.add_search_boxes();
        }
        return nRow;
    }

    vm.filter_enable = true;

    vm.close = close;
    function close() {

      vm.model_data = {};
//      angular.extend(vm.model_data, empty_data);
      $state.go('app.distributorOrders');
    }

    vm.sm_cancel_distributorOrder = function(gen_ord_id, dist_cust_id) {
    event.stopPropagation();
    vm.service.alert_msg("Do you want to cancel Order").then(function(msg) {
      vm.cancelPoDisable = true;
      var sendData = {gen_ord_id:gen_ord_id, distributor:dist_cust_id};
      if (msg == "true") {
        Service.apiCall("sm_cancel_distributor_order/", "POST", sendData, true).then(function(data) {
          if(data.message) {
            if(data.data == 'Success') {
              Service.showNoty('Successfully Cancelled the Order');
              vm.cancelPoDisable = false;
              vm.close();
              reloadData();
            } else {
              Service.showNoty(data.data, 'warning');
              vm.cancelPoDisable = false;
            }
          } else {
            Service.showNoty('Something Went Wrong', 'warning');
            vm.cancelPoDisable = false;
          }
        });
      } else {
        vm.cancelPoDisable = false;
      }
    });
  }

}
