'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('OrderSyncIssuesTable',['$scope', '$http', '$state', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

  function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, Service) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.selected = {};
    vm.selectAll = false;
    vm.enable_button = false;
    vm.filters = {'datatable': 'OrderSyncTable', 'search0':'', 'search1':'', 'search2': '', 'search3': ''}

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
       .withOption('drawCallback', function(settings) {
         vm.service.make_selected(settings, vm.selected);
       })
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
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.model_data = {}
               var sync_id = aData.DT_RowId;
                vm.service.apiCall('order_sync_data_detail/', 'GET', { sync_id : aData.DT_RowId }).then(function(data) {
                  if(data.message) {
                    vm.update = true;
                    vm.title = "Modify Orders Sync Issues";
                    angular.copy(data.data, vm.model_data);
                    vm.model_data['sync_id'] = sync_id;
                    $scope.sku_name = vm.model_data['sku_code'];
                    vm.model_data['sku_code'] = '';
                    $state.go('app.OrdersSyncIssues.ModifyIssues');
                  }
                });
            });
        });
        return nRow;
    };

    var columns = ["Order ID", "SKU Code", "Reason", "Created Date"];
    vm.dtColumns = vm.service.build_colums(columns);
    vm.dtInstance = {};

    function reloadData () {
        vm.bt_disable = true;
        vm.dtInstance.reloadData();
    };

    vm.bt_disable = true;
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

   vm.confirm_orders = function(datas) {
     if(vm.model_data.sku_code) {
        var data = {};
        data = vm.model_data
        Service.apiCall("confirm_order_sync_data/", "POST", data).then(function(data){
          if(data.data.resp) {
            vm.service.showNoty(data.data.resp_message, 'success', 'topRight');
            pop_msg(data.data.resp_message);
            vm.close();
          } else {
            vm.service.showNoty(data.data.resp_message, 'error', 'topRight');
            pop_msg(data.data.resp_message);
          }
          reloadData();
        });
     }
   }

   vm.close = close;
   function close() {
      vm.model_data = {};
      vm.html = "";
      $state.go('app.OrdersSyncIssues');
   }

   vm.pop_msg = pop_msg;
   function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 2000);
   }

   vm.delete_order = function delete_order() {
     var data = {}
     data['sync_id'] = vm.model_data.sync_id
     vm.service.apiCall('delete_order_sync_data/', 'POST', data).then(function(data) {
        if(data.data.resp) {
            vm.service.showNoty(data.data.resp_message, 'success', 'topRight');
            pop_msg(data.data.resp_message);
            vm.close();
          } else {
            vm.service.showNoty(data.data.resp_message, 'error', 'topRight');
            pop_msg(data.data.resp_message);
        }
        reloadData();
     })
   }

  }
