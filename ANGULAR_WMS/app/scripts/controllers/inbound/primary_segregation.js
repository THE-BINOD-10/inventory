FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('PrimarySegregationCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.industry_type = Session.user_profile.industry_type;
    if(vm.industry_type == 'FMCG'){
      vm.extra_width = {
        'width': '1350px'
      }
    }

    vm.filters = {'datatable': 'PrimarySegregation', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': '', 'search5': '',
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

    var columns = ['PO Number', 'Order Date', 'Supplier ID', 'Supplier Name', 'Order Type'];
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
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.service.apiCall('get_po_segregation_data/', 'GET', {order_id: aData['DT_RowId']}).then(function(data){
                  if(data.message) {
                    vm.serial_numbers = [];
                    angular.copy(data.data, vm.model_data);
                    vm.title = "Primary Segregation";
                    $state.go('app.inbound.PrimarySegregation.AddSegregation');
                  }
                });
            });
        });
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

    vm.update_data = update_data;
    function update_data(index, data) {
      if (Session.roles.permissions['pallet_switch']) {
        if (index == data.length-1) {
          var new_dic = {};
          angular.copy(data[0], new_dic);
          new_dic.receive_quantity = 0;
          new_dic.value = "";
          new_dic.pallet_number = "";
          data.push(new_dic);
        } else {
          data.splice(index,1);
        }
      }
    }
    vm.new_sku = false
    vm.add_wms_code = add_wms_code;
    function add_wms_code() {
      vm.model_data.data.push([{"wms_code":"", "po_quantity":"", "receive_quantity":"", "price":"", "dis": false,
                                "order_id": vm.model_data.data[0][0].order_id, is_new: true, "unit": "",
                                "sku_details": [{"fields": {"load_unit_handle": ""}}]}]);
      //vm.new_sku = true
    }
    vm.get_sku_details = function(data, selected) {

      data.sku_details[0].fields.load_unit_handle = selected.load_unit_handle;
      data.wms_code = selected.wms_code;
      $timeout(function() {$scope.$apply();}, 1000);
    }

    vm.html = "";
    vm.confirm_segregation = function(form) {

     if(check_receive()){
      var that = vm;
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      var url = "confirm_primary_segregation/"
      vm.service.apiCall(url, 'POST', elem, true).then(function(data){
        if(data.message) {
          if(data.data == "Updated Successfully") {
            vm.service.refresh(vm.dtInstance);
            vm.close();
          } else {
            pop_msg(data.data);
          }
        }
      });
     }
    }

    function check_receive() {
      var status = false;
      for(var i=0; i<vm.model_data.data.length; i++)  {
        if(vm.model_data.data[i][0].sellable > 0 || vm.model_data.data[i][0].non_sellable > 0) {
          status = true;
          break;
        }
      }
      if(status){
        return true;
      } else {
        pop_msg("Please Update the received quantity");
        return false;
      }
    }

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
        vm.message = "";
      }, 2000);
      vm.service.refresh(vm.dtInstance);
    }

    vm.receive_quantity_change = function(data) {

      if(isNaN(data.sellable)){
        data.sellable = 0;
      }
      else {
        data.sellable = Number(data.sellable);
      }
      if(Number(data.quantity) < Number(data.sellable)) {
          data.sellable = data.quantity;
      }
      data.non_sellable = Number(data.quantity) - Number(data.sellable)
    }

  //GRN Pop Data
  vm.grn_details = {po_reference: 'PO Reference', supplier_id: 'Supplier ID', supplier_name: 'Supplier Name',
                    order_date: 'Order Date'}
  vm.grn_details_keys = Object.keys(vm.grn_details);

  vm.change_datatable = function() {
      Data.receive_po.style_view = vm.g_data.style_view;
      $state.go($state.current, {}, {reload: true});
  }
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
