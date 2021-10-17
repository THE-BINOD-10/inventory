FUN = {};

;(function() {

'use strict';

var stockone = angular.module('urbanApp', ['datatables'])
stockone.controller('MaterialPlanningCtrl',['$scope', '$http', '$state', '$timeout', '$rootScope', '$location', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'SweetAlert', 'focus', '$modal', '$compile', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, $rootScope, $location, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, SweetAlert, focus, $modal, $compile, Data) {
    var vm = this;
    var location_href = $rootScope.$location_href;
    var url_params = location_href.split('?');
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

    vm.filters = {'datatable': 'MaterialPlanning', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': '', 'search5': '',
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

    var columns = ['MRP Run Id', 'Plant Code', 'Plant Name', 'Department', 'SKU Code', 'SKU Description', 'SKU Category', 'Purchase UOM', 'Average Daily Consumption Qty', 'Average Plant Daily Consumption Qty', 'Lead Time Qty',
                   'Min Days Qty', 'Max Days Qty', 'Dept Stock Qty', 'Allocated Plant Stock Qty', 'Pending PR Qty', 'Pending PO Qty', 'Total Stock Qty', 'Suggested Qty',
                   'Supplier Id', 'Suggested Value'];
    vm.dtColumns = vm.service.build_colums(columns);
    vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
                .renderWith(function(data, type, full, meta) {
                  if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                    vm.selected = {};
                  }
                  vm.selected[meta.row] = false;
                  return vm.service.frontHtml + meta.row + vm.service.endHtml;
                }))
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
    vm.create_pr = create_pr;
    function create_pr() {
      var data_ids = [];
      var formData = new FormData();
      var plant_code = '';
      var dept = ''
      var plant_check = false;
      var non_zero_qty = false;
      angular.forEach(vm.selected, function(value, key){
        if(value) {
          var table_data = vm.dtInstance.DataTable.context[0].aoData[key];
          var row_plant = table_data._aData['Plant Code'];
          var row_dept = table_data._aData['Department'];
          if(!plant_code){
            plant_code = row_plant;
          }
          if(!dept){
            dept = row_dept;
          }
          var sugg_qty = vm.dtInstance.DataTable.context[0].aoData[key]._aData['Suggested Qty'];
          if(sugg_qty != ''){
            sugg_qty = parseFloat(sugg_qty);
            formData.append('id', vm.dtInstance.DataTable.context[0].aoData[key]._aData.DT_RowId);
            formData.append('suggested_qty', sugg_qty);
            formData.append('capacity', vm.dtInstance.DataTable.context[0].aoData[key]._aData['System Stock Qty']);
            formData.append('avg_consumption_qty', vm.dtInstance.DataTable.context[0].aoData[key]._aData['Average Daily Consumption Qty']);
            formData.append('openpr_qty', vm.dtInstance.DataTable.context[0].aoData[key]._aData['Pending PR Qty']);
            formData.append('openpo_qty', vm.dtInstance.DataTable.context[0].aoData[key]._aData['Pending PO Qty']);
            non_zero_qty = true;
          }
          if(plant_code != row_plant || dept != row_dept){
            plant_check = true;
          }
        }
      });
      if(plant_check) {
        vm.service.showNoty('Please Select one plant and department only');
        return false;
      }
      if(!non_zero_qty && !vm.selectAll) {
        vm.service.showNoty('Suggested Quantity is zero for all selected lines');
        return false;
      }
      //formData.append('select_all', vm.selectAll);
      formData.append('select_all', false);
      angular.forEach(vm.model_data.filters, function(value, key){
        formData.append(key, value);
      });
      var url = "prepare_material_planning_pr_data/"
      $rootScope.process = true;
      $.ajax({url: Session.url + url,
            data: formData,
            method: 'POST',
            processData : false,
            contentType : false,
            xhrFields: {
                withCredentials: true
            },
            'success': function(response) {
              response = JSON.parse(response);
              if(!response.data_list){
                vm.service.showNoty('Suggested Quantity is zero for all selected lines');
                return false;
              }
              $rootScope.$current_raise_pr = JSON.stringify(response);
              $rootScope.process = false;
              $state.go('app.inbound.RaisePr');
            }});
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


    vm.model_data['filters'] = {'datatable': 'MaterialPlanning'};
    $timeout(function() {
    if(url_params.length > 1 && url_params[1].length > 0){
      var params_list = url_params[1].split('&')
      angular.forEach(params_list, function(param_dat){
        var param_temp = param_dat.split('=')
        vm.model_data['filters'][param_temp[0]] = param_temp[1];
      })
      vm.saveFilters(vm.model_data['filters']);
      vm.service.generate_report(vm.dtInstance, vm.model_data.filters);
    }
    }, 1000);
    vm.reset_filters = function(){

      vm.model_data['filters'] = {};
      vm.model_data.filters['datatable'] = 'MaterialPlanning';
    }


    vm.empty_filter_fields = function(){


      if (Data.rtv_filters) {

        vm.model_data['filters'] = Data.mp_filters;
      } else {

        vm.model_data['filters'] = {};
        vm.model_data.filters['sku_code'] = '';
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

  vm.category_list = [];
  vm.service.apiCall('get_sku_category_list/',).then(function(data){
    if(data.message){
      vm.category_list = data.data.category_list;
    }
  })

  vm.generate_mrp_data = function() {
    vm.service.alert_msg("Generate MRP").then(function(msg) {
      if(msg == "true"){
        var filters_data = vm.model_data.filters;
        vm.service.apiCall('generate_material_planning/', 'POST', filters_data).then(function(data){
          vm.service.showNoty(data.data);
          vm.service.refresh(vm.dtInstance);
        });
      }
    });

  }

  vm.send_mrp_output = function() {
    vm.service.alert_msg("Send MRP Output Mail").then(function(msg) {
      if(msg == "true"){
        var filters_data = vm.model_data.filters;
        vm.service.apiCall('send_material_planning_mail/', 'POST', filters_data).then(function(data){
          vm.service.showNoty(data.data);
        });
      }
    });

  }
  vm.show_formula = function () {
      var modalInstance = $modal.open({
        templateUrl: 'views/inbound/material_planning/show_formula.html',
        controller: 'ShowFormulaCtrl',
        controllerAs: 'showCase',
        size: 'lg',
        backdrop: 'static',
        keyboard: false,
      });
      modalInstance.result.then(function (selectedItem) {
        if (selectedItem) {
          console.log('');
        }
      });
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

angular.module('urbanApp').controller('ShowFormulaCtrl', function ($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance) {
  var vm = this;
  vm.user_type = Session.roles.permissions.user_type;
  vm.service = Service;
  vm.close = function () {
    $modalInstance.close();
  };
});