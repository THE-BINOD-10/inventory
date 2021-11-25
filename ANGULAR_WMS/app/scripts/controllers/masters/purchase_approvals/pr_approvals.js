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
    vm.default_current_level = 0;
    vm.ranges_current_level = 0;
    vm.ranges_count = 0;
    vm.approved_current_level = 0;
    vm.roles_type_name = 'pr';
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
                  vm.default_current_level = vm.model_data.default_level_data.length - 1;
                  vm.ranges_current_level = vm.model_data.ranges_level_data.length - 1;
                  vm.approved_current_level = vm.model_data.approved_level_data.length - 1;
                  vm.title = "Update Purchase Approval";
                  $state.go('app.masters.PurchaseApproval.updateApproval');
                  $timeout(function(){$('.selectpicker-ranges').selectpicker();}, 1000);
                  $timeout(function(){$('.selectpicker-default').selectpicker();}, 1000);
                  $timeout(function(){$('.selectpicker-approved').selectpicker();}, 1000);
//                  angular.forEach(vm.model_data.default_level_data, function(level_dat, level_index){
//                    $timeout(function(){$('#default-'+vm.roles_type_name+'roles-'+level_index).selectpicker()}, 100);
//                  });
//                  angular.forEach(vm.model_data.ranges_level_data, function(level_dat, level_index){
//                    $timeout(function(){$('#ranges-'+vm.roles_type_name+'roles-'+level_index).selectpicker()}, 100);
//                  });
//                  angular.forEach(vm.model_data.approved_level_data, function(level_dat, level_index){
//                    $timeout(function(){$('#approved-'+vm.roles_type_name+'roles-'+level_index).selectpicker()}, 100);
//                  });
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
  var empty_data = {name: '', product_category: '', sku_category: '', plant: '', department_type: '', zone : '',
  default_level_data: [{level: 'level0', roles: '', data_id: '' , display_emails: false, emails: ''}],
   ranges_level_data: [{min_Amt: 0, max_Amt: 0, range_no: 0, 'range_levels': [{level: 'level0', roles: '', emails: '',  data_id: '', level_no: 0}] }],
  approved_level_data: [{level: 'level0', roles: '', data_id: ''}]};
  vm.model_data = {};
  angular.copy(empty_data, vm.model_data);


  //close popup
  vm.close = function() {
    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.PurchaseApproval');
    vm.default_current_level = 0;
    vm.ranges_current_level = 0;
    vm.approved_current_level = 0;
    vm.category_list = [];
  }

  vm.add = function() {

    vm.title = "Add PR Approval";
    angular.copy(empty_data, vm.model_data);
    vm.update = false;
    vm.get_company_warehouses();
    vm.default_current_level = 0;
    vm.ranges_current_level = 0;
    vm.approved_current_level = 0;
    vm.all_purchase_approval_data_api();
    vm.getProdMaxValue(vm.model_data);
    $state.go('app.masters.PurchaseApproval.updateApproval');
    $timeout(function(){$('.selectpicker-ranges').selectpicker();}, 1000);
    $timeout(function(){$('.selectpicker-default').selectpicker();}, 1000);
    $timeout(function(){$('.selectpicker-approved').selectpicker();}, 1000);
    $timeout(function(){$('.selectpicker-plants').selectpicker();}, 1000);
  }

  vm.submit = function(data) {
    var valid = true;
    if (data.$valid) {
      if(valid)
      {
        var email_req = false;
        angular.forEach(vm.model_data.default_level_data, function(record, index){
          record.emails = $(".bootstrap-tagsinput .emails").eq(index).val();
          if(record.roles.indexOf("Specify User") != -1 && !record.emails){
            email_req = true;
          }
        });
        if(email_req){
          vm.service.showNoty("Email is Mandatory");
          return
        }
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

  vm.update_data = function(index, approval_type, data_id) {
    if(vm.model_data[approval_type+'_level_data'].length > 1) {
      if(data_id) {
        vm.service.apiCall('delete_pr_config/', 'POST', {'data_id': data_id, 'type': 'actual_pr_save'}).then(function(data){
          if(data.message) {
            if(data.data == "Deleted Successfully") {
              vm.service.refresh(vm.dtInstance);
            } else {
              vm.service.pop_msg(data.data);
            }
          }
        });
      }
      vm.model_data[approval_type+'_level_data'].splice(index,1);
      vm[approval_type+'_current_level'] -= 1;
    }
  }

  vm.addDefaultLevel = function() {
    var new_level = (vm.default_current_level + 1);
    vm.model_data.default_level_data.push({level: 'level' + new_level, roles: '', data_id: ''})
    $('#default-'+vm.roles_type_name+'roles-'+new_level).val();
    $timeout(function(){$('.selectpicker-default').selectpicker();}, 2);
    vm.default_current_level += 1;
  }

  vm.addRangesLevel = function(range_data, level_dat) {
    var new_level = level_dat.level_no + 1;
    range_data.range_levels.push({level: 'level' + new_level, roles: '', emails: '', data_id: '', level_no: new_level})
    $timeout(function(){$('.selectpicker-ranges').selectpicker();}, 2);
  }

  vm.addRangesAmts = function() {
    var new_range = (vm.ranges_count + 1);
    vm.model_data.ranges_level_data.push({min_Amt: 0, max_Amt: 0, range_no: new_range, 'range_levels': [{level: 'level0', roles: '', emails: '', data_id: '', level_no: 0}]})
    $timeout(function(){$('.selectpicker-ranges').selectpicker();}, 10);
    vm.ranges_count += 1;
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
  vm.get_sku_category_list = function() {
    vm.category_list = [];
    vm.model_data.sku_category = '';
    var cat_data = {'product_category': vm.model_data.product_category};
    vm.service.apiCall('get_sku_category_list/', 'GET', cat_data).then(function(data){
      if(data.message) {
        vm.category_list = data.data.category_list;
      }
    });
  }

  vm.roles_list = [];
  function get_roles_list() {
    vm.service.apiCall("get_company_roles_list/", "GET").then(function(data) {
      if(data.message) {
        vm.roles_list = data.data.roles_list;
      }
    });
  }
  get_roles_list();

  vm.emails_list = {};
  function get_emails() {
    vm.service.apiCall("get_emails_list/", "GET").then(function(data) {
      if(data.message) {
        vm.emails_list = data.data.emails;
      }
    });
  }
  get_emails();

  vm.check_selected = function(data, role){
    var selected_val = false;
    for(var ind=0; ind<data.roles.length; ind++) {
      if(data.roles[ind] == role) {
        selected_val = true;
        break;
      }
    }
    return selected_val;
  }

  vm.updateRoles = function(level_dat, email){
    level_dat['roles'] = [vm.emails_list[email]]
  }

  vm.check_for_mail = function(data, row_index){
    if(data.roles.indexOf("Specify User") != -1){
      if(data.roles.length > 1){
        vm.service.showNoty("Can't select other roles if Specify User is selected");
        data.roles.pop("Specify User");
        $('.selectpicker-default').eq(row_index).find("[value="+"'Specify User']").prop('selected', false);
        $('.selectpicker-default').selectpicker("refresh");
        data.display_emails = false;
      }
      else {
       data.display_emails = true;
      }
    }
    else {
      data.emails = "";
      $(".bootstrap-tagsinput .emails").eq(row_index).val()
      data.display_emails = false;
    }
  }

  vm.delete_range_levels_data = function(index, range_data, level_dat) {
    if(level_dat.data_id) {
      vm.service.apiCall('delete_pr_config/', 'POST', {'data_id': level_dat.data_id, 'type': 'actual_pr_save'}).then(function(data){
        if(data.message) {
          if(data.data == "Deleted Successfully") {
            vm.service.refresh(vm.dtInstance);
          } else {
            vm.service.pop_msg(data.data);
          }
        }
      });
    }
    if(index != 0) {
      range_data.range_levels.splice(index,1);
    }
    if(index == 0 && range_data.range_no != 0){
        vm.model_data.ranges_level_data.splice(-1);
    }
  }

  vm.download_excel_extra_info = function(headers, search){
    var data = {};
    angular.forEach(headers, function(value, key) {
      if(value.mData) {
        data[value.mData] = value.sTitle;
      }
    });
    angular.extend(data, search);
    data['search[value]'] = $(".dataTables_filter").find("input").val();
    //data = $.param(data);
    vm.service.apiCall('download_pr_doa_staff_excel/', 'POST', data).then(function(res_data){
      if(res_data.message){
        location.href = res_data.data;
      }
    });
  }

}
