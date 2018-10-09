'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('RawMaterialPicklistCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'printer', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session , printer, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, Data) {
    var vm = this;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.vendor_produce = false;
    vm.g_data = Data.confirm_orders;
    vm.tb_data = {};

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': vm.g_data.view},
              xhrFields: {
                withCredentials: true
              },
              complete: function(jqXHR, textStatus) {
                $scope.$apply(function(){
                  angular.copy(JSON.parse(jqXHR.responseText), vm.tb_data)
                })
              }
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

    vm.dtColumns = vm.service.build_colums(vm.g_data.tb_headers[vm.g_data.view]);

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
              var elem = {};
              if (aData.DT_RowAttr.hasOwnProperty('data-id')) {
                elem = {'data_id': aData.DT_RowAttr['data-id']}
              } else {
                elem =  {'id': aData.DT_RowAttr['id']}
              }
              vm.service.apiCall('view_confirmed_jo/', 'POST', elem).then(function(data){
                if(data.message) {
                  vm.vendor_produce = (aData["Order Type"] == "Vendor Produce") ? true : false;
		  vm.order_ids_list = data.data.order_ids.toString();
                  angular.copy(data.data, vm.model_data);
                  vm.model_data.jo_reference = aData['Job Code']
                  $state.go('app.production.RMPicklist.ConfirmedJO');
                }
              });
            });
        });
        return nRow;
    }

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        $('.custom-table').DataTable().draw();
    };

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    vm.close = close;
    function close() {

      vm.vendor_produce = false;
      vm.print_enable = false;
      $state.go('app.production.RMPicklist');
    }

    vm.model_data = {}
    vm.update = true;

    vm.generate = function(url) {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall(url, 'POST', elem, true).then(function(data){
        if(data.message) {
          if(data.data == "Success") {
            vm.close();
            reloadData();
          } else {
            pop_msg(data.data);
          }
        }
      });
    }

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 2000);
    }

    vm.change_datatable = function() {
      Data.confirm_orders.view = (vm.g_data.sku_view)? 'RawMaterialPicklistSKU': 'RawMaterialPicklist';
      $state.go($state.current, {}, {reload: true});
    }
  }
