'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('MoveInventoryCtrl',['$scope', '$http', '$state', '$compile', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', 'focus', '$timeout', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, focus, $timeout) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              xhrFields: {
                withCredentials: true
              },
              data: {'datatable': 'MoveInventory', 'special_key':'move'}
           })
       .withDataProp('data')
       .withOption('drawCallback', function(settings) {
         vm.service.make_selected(settings, vm.selected);
       })
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
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
        .withOption('rowCallback', rowCallback);

    vm.dtColumns = [
        DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
              if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                  vm.selected = {};
                }
              vm.selected[meta.row] = vm.selectAll;
              vm.seleted_rows.push(full);
              return vm.service.frontHtml + meta.row + vm.service.endHtml;
            }),
        DTColumnBuilder.newColumn('Source Location').withTitle('Source Location'),
        DTColumnBuilder.newColumn('WMS Code').withTitle('WMS Code'),
        DTColumnBuilder.newColumn('Description').withTitle('Description'),
        DTColumnBuilder.newColumn('Destination Location').withTitle('Destination Location'),
        DTColumnBuilder.newColumn('Move Quantity').withTitle('Move Quantity')
    ];

    vm.dtInstance = {};

    vm.reloadData = reloadData;
    function reloadData() {
      vm.dtInstance.DataTable.draw();
      vm.bt_disable = true;
    }

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    vm.seleted_rows = []
    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        if(vm.filter_enable){
          vm.filter_enable = false;
          vm.apply_filters.add_search_boxes();
        }
        return nRow;
    }

    vm.generate_data = []
    vm.confirm_move = confirm_move;
    function confirm_move() {
      for(var key in vm.selected){
        console.log(vm.selected[key]);
        if(vm.selected[key]) {
          vm.generate_data.push(vm.dtInstance.DataTable.context[0].aoData[Number(key)]["_aData"]);
        }
      }
      if(vm.generate_data.length > 0) {
        console.log("call");
        vm.generate_filter_en = false;
        var data = '';
        for(var i=0; i< vm.generate_data.length; i++) {
          data += $(vm.generate_data[i][""]).attr("name")+"="+$(vm.generate_data[i][""]).attr("value")+"&";
        }
        vm.service.apiCall('confirm_move_inventory/?'+data.slice(0,-1)).then(function(data){
          if(data.message) {
            colFilters.showNoty(data.data);
            reloadData();
            vm.bt_disable = true;
          }
        });
        vm.generate_data = [];
      }
    }
    vm.add = add;
    function add() {
      angular.copy(vm.empty_data, vm.model_data);
      $state.go('app.stockLocator.MoveInventory.Inventory');
    }

    vm.close = close;
    function close() {
      vm.model_imei = {};
      $state.go('app.stockLocator.MoveInventory');
    }

    vm.message = "";
    vm.empty_data = {
                      'wms_code':'',
                      'source_loc': '',
                      'dest_loc': '',
                      'quantity': ''
                    }
    vm.model_data = {};
    angular.copy(vm.empty_data, vm.model_data);

    vm.submit =submit;
    function submit(data) {
      if(data.$valid) {
        var elem = angular.element($('form'));
        elem = elem[0];
        elem = $(elem).serializeArray();
        vm.service.apiCall('insert_move_inventory/', 'GET', elem, true).then(function(data){
          if(data.message) {
            if (data.data == "Added Successfully") {
              vm.close()
              angular.extend(vm.model_data, vm.empty_data);
            } else {
              Service.showNoty(data.data, 'warning');
            }
          }
        });
      }
    }

    vm.move_imei = function() {

      $state.go("app.stockLocator.MoveInventory.IMEI");
    }

    vm.model_imei = {};
    vm.scan_imei = function(event, field) {
      if ( event.keyCode == 13 && field) {

        vm.service.apiCall('get_imei_details/', 'GET', {imei:field}, true).then(function(data){

          if(!data.data.result) {
            vm.model_imei = data.data.data;
            vm.model_imei["display_details"]= true;
            if(vm.model_imei.status = "accepted") {

              vm.model_imei["show_options"] = true;
              focus('reason');
            }
            $timeout(function(){$scope.$apply()},200);
          } else {

            vm.model_imei = {}
            colFilters.showNoty(data.data.data);
          }
        })
        vm.imei="";
      }
    }

    vm.submit_imei = function(data){

      if(data.$valid) {

        var send = $("form:visible").serializeArray();
        vm.service.apiCall("change_imei_status/", 'POST', send, true).then(function(data){

          if(data.message) {
            colFilters.showNoty(data.data.message);
            vm.model_imei = {};
            focus('focusIMEI');
          }
          console.log(data);
        })
      }
    }
  }

