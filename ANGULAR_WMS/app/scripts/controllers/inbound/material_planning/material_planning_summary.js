FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('MaterialPlanningSummaryCtrl',['$scope', '$http', '$state', '$timeout', '$rootScope', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, $rootScope, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.industry_type = Session.user_profile.industry_type;
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = false;
    vm.zones_list = ['Central', 'East', 'GRL', 'Mumbai', 'NACO', 'North', 'Overseas', 'South', 'West'];
    if(vm.industry_type == 'FMCG'){
      vm.extra_width = {
        'width': '1350px'
      }
    }

    vm.filters = {'datatable': 'MaterialPlanningSummary', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': '', 'search5': '',
                  'search6': '', 'search7': '', 'search8': '', 'search9': '', 'search10': ''};
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
         $scope.$apply(function() {vm.bt_disable = true;vm.selectAll = false;});
       })
       .withOption('order', [0, 'desc'])
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

    var columns = ['MRP Run Id', 'Zone', 'State', 'Plant', 'Department', 'Count of SKUs', 'Value of MRP Generated'];
    vm.dtColumns = vm.service.build_colums(columns);
    //var toggle = DTColumnBuilder.newColumn('PO No').withTitle(' ').notSortable().notVisible();
    //vm.dtColumns.unshift(toggle);
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
        Service.apiCall('get_receive_po_style_view/?order_id='+data['PO No'].split("_")[1]).then(function(resp){
          if (resp.message){

            if(resp.data.status) {
              var html = $compile("<tr class='row-expansion' style='display: none'><td colspan='13'><dt-po-data data='"+JSON.stringify(resp.data)+"' preview='showCase.preview'></dt-po-data></td></tr>")($scope);
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

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        /*$('td:not(td:first)', nRow).bind('click', function() {
            $scope.$apply(function() {
                var data_to_send = {
                  'order_id': aData['DT_RowId'],
                  'prefix': aData['prefix']
                }
                vm.service.apiCall('get_po_segregation_data/', 'GET', data_to_send).then(function(data){
                  if(data.message) {
                    vm.serial_numbers = [];
                    angular.copy(data.data, vm.model_data);
                    vm.title = "Primary Segregation";
                    $state.go('app.inbound.PrimarySegregation.AddSegregation');
                  }
                });
            });
        });*/
        return nRow;
    }

    vm.filter_enable = true;
    vm.print_enable = false;
    vm.update = false;
    vm.model_data = {};
    vm.dis = true;

    vm.close = close;
    function close() {

      vm.model_data = {};
      vm.html = "";
      vm.print_enable = false;
      $state.go('app.inbound.PrimarySegregation');
    }

    vm.get_sku_details = function(data, selected) {

      data.sku_details[0].fields.load_unit_handle = selected.load_unit_handle;
      data.wms_code = selected.wms_code;
      $timeout(function() {$scope.$apply();}, 1000);
    }


    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
        vm.message = "";
      }, 2000);
      vm.service.refresh(vm.dtInstance);
    }

    vm.model_data['filters'] = {'datatable': 'MaterialPlanningSummary'};
    vm.reset_filters = function(){

      vm.model_data['filters'] = {};
      vm.model_data.filters['datatable'] = 'MaterialPlanningSummary';
    }


    vm.empty_filter_fields = function(){


      if (Data.rtv_filters) {

        vm.model_data['filters'] = Data.mp_filters;
      } else {

        vm.model_data['filters'] = {};
        vm.model_data.filters['plant_code'] = '';
        vm.model_data.filters['plant_name'] = '';
        vm.model_data.filters['zone_code'] = '';
        vm.model_data.filters['datatable'] = 'MaterialPlanning';
      }
    }

    vm.saveFilters = function(filters){
      Data.mp_filters = filters;
    }

  vm.department_type_list = [];
  vm.service.apiCall('get_department_list/').then(function(data){
    if(data.message) {
      vm.department_type_list = data.data.department_list;
    }
  });



}

stockone.directive('dtPoData', function() {
  return {
    restrict: 'E',
    scope: {
      po_data: '=data',
      preview: '=preview'
    },
    templateUrl: 'views/inbound/toggle/po_data_html.html',
    link: function(scope, element, attributes, $http){
      console.log(scope);
    }
  };
});

})();
