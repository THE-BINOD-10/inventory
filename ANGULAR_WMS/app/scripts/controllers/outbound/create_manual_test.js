'use strict';

function CreateManualTest($scope, $http, $q, $state, Session, colFilters, Service) {

  $scope.msg = "start";
  var vm = this;
  vm.service = Service;
  vm.current_user = {[$scope.user.userName]: $scope.user.user_profile.state};
  vm.tax_cg_sg = false;
  vm.igst_enable = false;
  vm.dest_sellers_list = [];
  vm.model_data = {};
  vm.industry_type = Session.user_profile.industry_type;
  vm.user_type = Session.user_profile.user_type;
  vm.wh_type_list = ['Store', 'Department'];
  vm.wh_type = 'Department';
  var rows_data = {test_code: "", test_desc: "",
   sub_data: [{wms_code: "", order_quantity: "", price: "", capacity:0, uom: ""}]}
  var empty_data = {data: [rows_data], warehouse: ""};
  angular.copy(empty_data, vm.model_data);
  vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

  vm.add_new_row = function(){
      var temp_row = {};
      angular.copy(rows_data, temp_row);
      vm.model_data.data.push(temp_row);
  }

  vm.remove_test_row = function(index){
      var temp_row = {};
      angular.copy(rows_data, temp_row);
      vm.model_data.data.splice(index,1);
  }

  vm.update_data = update_data;
  function update_data(index, data, last) {
    console.log(data);
    if (last) {
      data.sub_data.push({wms_code: "", order_quantity: "", price: "", capacity:0, uom: ""});
    } else {
      data.sub_data.splice(index,1);
    }
  }

  vm.warehouse_dict = {};
  var wh_filter = {'warehouse_type': 'STORE'};
  vm.service.apiCall('get_warehouses_list/', 'GET',wh_filter).then(function(data){
    if(data.message) {
      vm.warehouse_dict = data.data.warehouse_mapping;
      vm.warehouse_list_states = data.data.states;
    }
  });

  vm.get_warehouse_department_list = get_warehouse_department_list;
  function get_warehouse_department_list() {
    var wh_data = {};
    vm.department_list = [];
    wh_data['warehouse'] = vm.model_data.plant;
    wh_data['warehouse_type'] = 'DEPT';
    vm.service.apiCall("get_company_warehouses/", "GET", wh_data).then(function(data) {
      if(data.message) {
        vm.department_list = data.data.warehouse_list;
      }
    });
  }

  vm.get_sku_details = function(data, selected) {
    if(!vm.model_data.warehouse){
      data.wms_code = '';
      if(vm.wh_type == 'Store'){
        colFilters.showNoty("Please select Store first");
      }
      else {
        colFilters.showNoty("Please select Department first");
      }
      return
    }
    data.wms_code = selected.wms_code;
    data.description = selected.sku_desc;
    data.uom = selected.measurement_unit;
    if(!vm.batch_mandatory){
      vm.update_availabe_stock(data);
    }
  }

  function check_exist(sku_data, index) {

    var d = $q.defer();
    for(var i = 0; i < vm.model_data.data.length; i++) {

      if(vm.model_data.data[i].$$hashKey != sku_data.$$hashKey && vm.model_data.data[i].test_code == sku_data.product_code) {

        d.resolve(false);
        vm.model_data.data.splice(index, 1);
        alert("It is already exist in index");
        break;
      } else if( i+1 == vm.model_data.data.length) {
        d.resolve(true);
      }
    }
    return d.promise;
  }

  vm.get_product_data = function(item, sku_data, index) {
    if(!vm.model_data.warehouse){
      colFilters.showNoty("Please select Department First");
      sku_data.test_code = '';
      return
    }
    console.log(vm.model_data);
    check_exist(sku_data, index).then(function(data){
      if(data) {
        var elem = $.param({'sku_code': item});
        vm.service.apiCall('get_material_codes/','POST', {'sku_code': item}).then(function(data){
          if(data.message) {
            if(data.data != "No Data Found") {
              sku_data.sub_data = [];
              sku_data.test_desc = data.data.product.description;
              sku_data.test_code = data.data.product.sku_code;
              sku_data.test_quantity = 1;
              angular.forEach(data.data.materials, function(material){
                var temp_sub = {};
                temp_sub.wms_code = material.material_code;
                temp_sub.sku_quantity = material.material_quantity;
                temp_sub.description = material.material_desc;
                temp_sub.uom = material.measurement_type;
                sku_data.sub_data.push(temp_sub);
              });

              //vm.change_quantity(sku_data);
            } else {
              sku_data.data = [{"material_code": "", "material_quantity": '', "id": ''}];
            }
          }
        });
      }
    });
  }

    vm.bt_disable = false;
  vm.insert_test_data = function(data) {
    if (data.$valid) {
      vm.bt_disable = true;
      var elem = angular.element($('form'));
      elem = $(elem).serializeArray();
      vm.service.apiCall('create_manual_test/', 'POST', elem).then(function(data){
        if(data.message) {
          if("Confirmed Successfully" == data.data) {
            angular.copy(empty_data, vm.model_data);
          }
          colFilters.showNoty(data.data);
          vm.bt_disable = false;
        }
      })
    } else {
      colFilters.showNoty("Fill Required Fields");
    }
  }

  vm.get_sku_data = function(record, item, index) {
    var found = false;
    angular.forEach(vm.model_data.data[index].sub_data, function(sku_data){
      if(item.wms_code==sku_data.wms_code){
        found = true;
      }
    });
    if(!found){
      record.wms_code = item.wms_code;
      record.description = item.sku_desc;
      record.sku_quantity = 1;
      record.uom = item.cuom;
    }
    else{
      colFilters.showNoty("SKU Code already in List");
      record.wms_code = "";
    }
  }

}

angular
  .module('urbanApp')
  .controller('CreateManualTest', ['$scope', '$http', '$q', '$state', 'Session', 'colFilters', 'Service', CreateManualTest]);
