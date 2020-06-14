'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PRApprovalTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.warehouse_level = Session.user_profile.warehouse_level;
    vm.permissions = Session.roles.permissions;
    vm.warehouse_type = Session.user_profile.warehouse_type;
    vm.current_level = 0;
    vm.filters = {'datatable': 'PRApprovalTable', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':'',
                    'special_key': 'PR'}
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
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    vm.dtColumns = [
        DTColumnBuilder.newColumn('name').withTitle('Config Name'),
        DTColumnBuilder.newColumn('product_category').withTitle("Product Category"),
        DTColumnBuilder.newColumn('plant').withTitle("Plant"),
        DTColumnBuilder.newColumn('department_type').withTitle("Department Type"),
        DTColumnBuilder.newColumn('min_Amt').withTitle("Min Amount"),
        DTColumnBuilder.newColumn('max_Amt').withTitle("Max Amount"),
    ];

    vm.dtInstance = {};

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
              var wh_data = {'name': aData['name'], 'purchase_type': 'PR'};
              vm.service.apiCall('get_purchase_config_data/', "GET", wh_data).then(function(data){
                if(data.message) {
                  //vm.warehouse_list = data.data.warehouse_list;
                  //angular.copy(aData, vm.model_data);
                  angular.copy(data.data.data, vm.model_data);
                  vm.update = true;
                  vm.current_level = vm.model_data.level_data.length - 1;
                  vm.title = "Update Purchase Approval";
                  $state.go('app.masters.PurchaseApproval.updateApproval');
                }
              });
            });
        });
        return nRow;
    }

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

  /**************************************/
  vm.update = false;
  var empty_data = {name: '', product_category: '', sku_category: '', plant: '', department_type: '', min_Amt: '', max_Amt: '',
  level_data: [{level: 'level0', roles: ''}]};
  vm.model_data = {};
  angular.copy(empty_data, vm.model_data);


  //close popup
  vm.close = function() {
    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.PurchaseApproval');
    vm.current_level = 0;
  }

  vm.add = function() {

    vm.title = "Add PR Approval";
    angular.copy(empty_data, vm.model_data);
    vm.update = false;
    vm.get_company_warehouses();
    vm.current_level = 0;
    vm.all_purchase_approval_data_api();
    vm.getProdMaxValue(vm.model_data);
    $state.go('app.masters.PurchaseApproval.updateApproval');
  }

  vm.submit = function(data) {
    var valid = true;
    if (data.$valid) {
      if(valid)
      {
        angular.forEach(vm.model_data.level_data, function(level_dat, level_index){
          vm.model_data.level_data[level_index]['roles'] = $('.roles-'+level_index).val()
        });
        vm.service.apiCall('add_update_pr_config/', 'POST', {'data':JSON.stringify(vm.model_data), 'type': 'actual_pr_save'}).then(function(data){
          if(data.message) {
            if(data.data == "Updated Successfully" || data.data == "Added Successfully") {
              vm.service.refresh(vm.dtInstance);
              vm.close();
            } else {
              vm.service.pop_msg(data.data);
            }
          }
        });
      }
    }
  }

  vm.warehouse_list = [];
  vm.get_company_warehouses = function() {
  var wh_data = {};
  wh_data['warehouse_type'] = 'STORE,SUB_STORE';
  vm.service.apiCall('get_company_warehouses/', "GET", wh_data).then(function(data){
    if(data.message) {
      vm.warehouse_list = data.data.warehouse_list;
      }
    });
  }

  vm.department_list = [];
  vm.service.apiCall('get_department_list/').then(function(data){
    if(data.message) {
      vm.department_list = data.data.department_list;
    }
  });

  vm.product_category_list = [];
  vm.service.apiCall('get_product_categories_list/').then(function(data){
    if(data.message) {
      vm.product_category_list = data.data.product_categories;
    }
  });

  vm.update_data = function(index) {
    if(vm.model_data.level_data.length > 1) {
      vm.model_data.level_data.splice(index,1);
      vm.current_level -= 1;
    }
  }

  vm.addLevel = function() {
    vm.model_data.level_data.push({level: 'level' + (vm.current_level + 1), roles: ''})
    vm.current_level += 1;
  }

  vm.delete_config = function() {
    vm.service.apiCall('delete_pr_config/', 'POST', {'data':JSON.stringify(vm.model_data), 'type': 'actual_pr_save'}).then(function(data){
      if(data.message) {
        if(data.data == "Deleted Successfully") {
          vm.service.refresh(vm.dtInstance);
          vm.close();
        } else {
          vm.service.pop_msg(data.data);
        }
      }
    });
  }

  vm.all_purchase_approval_data = [];
  vm.all_purchase_approval_data_api = function() {
    vm.service.apiCall('all_purchase_approval_config_data/').then(function(data){
      if(data.message) {
        vm.all_purchase_approval_data = data.data.config_data;
      }
    });
  }

  vm.getProdMaxValue = function(configData){
    var maxAmtsList = [];
    var maxVal = 0;
    var prConfigData = vm.all_purchase_approval_data['actual_pr_approvals_conf_data'] //vm.model_data['total_actual_pr_config_ranges'];
    angular.forEach(prConfigData, function(record, index){
      if(record.product_category == configData.product_category && record.plant == configData.plant &&
            record.department_type == configData.department_type && record.sku_category == configData.sku_category){
        maxAmtsList.push(record.max_Amt);
      }
    });
    if (maxAmtsList.length > 0){
      maxVal = Math.max(maxAmtsList);
    } else{
      maxVal = 0
    }
    if (maxVal){
      configData.min_Amt = maxVal + 1;
    } else {
      configData.min_Amt = 0;
    }

  }

  vm.category_list = [];
  vm.service.apiCall('get_sku_category_list/').then(function(data){
    if(data.message) {
      vm.category_list = data.data.category_list;
    }
  });

}
