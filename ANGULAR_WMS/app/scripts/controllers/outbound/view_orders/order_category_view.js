'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('OrderCategoryView',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, Data) {

  var vm = this;
  vm.service = Service;
  vm.g_data = Data.other_view;
  vm.permissions = Session.roles.permissions;

    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.dtOptions = DTOptionsBuilder.newOptions()
      .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'OrderCategoryView'},
              xhrFields: {
                withCredentials: true
              }
           })
      .withDataProp('data')
      .withOption('order', [1, 'desc'])
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
         console.log("completed")
       });

    vm.dtColumns = vm.service.build_colums(vm.g_data.tb_headers['OrderCategoryView']);
    vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
      .renderWith(function(data, type, full, meta) {
        if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
          vm.selected = {};
        }
        vm.selected[meta.row] = vm.selectAll;
        return vm.service.frontHtml + meta.row + vm.service.endHtml;
      }))

  vm.change_datatable = function() {

    vm.dtInstance._renderer.options.ajax.data['datatable'] = vm.g_data.view;
    var temp = {};
    temp = vm.service.build_colums(vm.g_data.tb_headers[vm.g_data.view]);
    temp.unshift(DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
      .renderWith(function(data, type, full, meta) {
        if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
          vm.selected = {};
        }
        vm.selected[meta.row] = vm.selectAll;
        return vm.service.frontHtml + meta.row + vm.service.endHtml;
      }))
    vm.dtColumns = temp;
  }

  vm.dtInstance = {};

  vm.reloadData = reloadData;

  function reloadData () {

    $('.custom-table').DataTable().draw();
  };

  vm.render = function() {
    vm.dtInstance._renderer.rerender();
  }

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
            });
        });
        return nRow;
    } 

    vm.model_data = {};

    vm.generate_data = [];
    vm.generate_picklist = function() {
      for(var key in vm.selected){
        console.log(vm.selected[key]);
        if(vm.selected[key]) {
          vm.generate_data.push(vm.dtInstance.DataTable.context[0].aoData[key]._aData);
        }
      }
      if(vm.generate_data.length > 0) {
        console.log(vm.generate_data);
        var data = {};
        for(var i=0;i<vm.generate_data.length;i++) {
          data[vm.generate_data[i]["data_value"]]= vm.generate_data[i]['Total Quantity'];
        }
        vm.service.apiCall(vm.g_data.generate_picklist_urls[vm.g_data.view], 'POST', data).then(function(data){
          if(data.message) {
            angular.copy(data.data, vm.model_data);
            for(var i=0; i<vm.model_data.data.length; i++){
                    vm.model_data.data[i]['sub_data'] = [];
                    var value = (vm.permissions.use_imei)? 0: vm.model_data.data[i].picked_quantity;
                    vm.model_data.data[i]['sub_data'].push({zone: vm.model_data.data[i].zone,
                                                         location: vm.model_data.data[i].location,
                                                         orig_location: vm.model_data.data[i].location,
                                                         picked_quantity: value, scan: ""});
                  }
            $state.go('app.outbound.ViewOrders.Picklist');
            vm.reloadData();
          }
        });
        vm.generate_data = [];
      }
    }

  vm.print_excel = print_excel;
  function print_excel(id)  {
    vm.service.apiCall('print_picklist_excel/','GET',{data_id: id}).then(function(data){
      if(data.message) {
        window.location = Session.host+data.data.slice(3);
      }
    })
  }

  vm.print_pdf = print_pdf;
  function print_pdf(id) {
    vm.service.apiCall('print_picklist/','GET',{data_id: id}).then(function(data){
      if(data.message) {
        vm.service.print_data(data.data);
      }
    })
  }

  vm.pdf_data = {};
    vm.picklist_confirmation = picklist_confirmation;
    function picklist_confirmation() {
      var elem = angular.element($('form:visible'));
      elem = $(elem).serializeArray();
      vm.service.apiCall('picklist_confirmation/', 'POST', elem).then(function(data){
        if(data.message) {
          if(data.data == "Picklist Confirmed") {
            $state.go('app.outbound.ViewOrders');
          } else if (data.data.status == 'invoice') {

              angular.copy(data.data.data, vm.pdf_data);
              $state.go('app.outbound.ViewOrders.GenerateInvoice');
          } else {
            pop_msg(data.data);
          }
        }
      });
    }

  vm.confirm_disable = false;
  vm.close = close;
    function close() {
      $state.go('app.outbound.ViewOrders');
      vm.message = "";
      vm.confirm_disable = false;
    }
}
