'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ViewManualTestCtrl',['$scope', '$http', '$state', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', '$timeout', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, Session, DTOptionsBuilder, DTColumnBuilder, $timeout, colFilters, Service) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.service = Service;
    vm.industry_type = Session.user_profile.industry_type;
    vm.extra_width = {};
    vm.wh_type = 'Department';
    var rows_data = {test_code: "", test_desc: "",
    sub_data: [{wms_code: "", order_quantity: "", price: "", capacity:0, uom: ""}]}
    var empty_data = {data: [rows_data], warehouse: ""};
    angular.copy(empty_data, vm.model_data);

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'ViewManualTest'},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('order', [0, 'desc'])
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

    vm.dtColumns = [
        DTColumnBuilder.newColumn('Created Date').withTitle('Created Date'),
        DTColumnBuilder.newColumn('Requested User').withTitle('Requested User'),
        DTColumnBuilder.newColumn('Store').withTitle('Store'),
        DTColumnBuilder.newColumn('Department').withTitle('Department'),
        DTColumnBuilder.newColumn('Test Quantity').withTitle('Test Quantity'),
        DTColumnBuilder.newColumn('Status').withTitle('Status'),
    ];

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.message = "";
                var data_to_send ={
                  'id': aData.DT_RowAttr["data-id"],
                }
                vm.service.apiCall('get_manual_test_approval_pending/', 'GET', data_to_send).then(function(data){
                  if(data.message) {
                    
                    if(vm.industry_type == 'FMCG'){
                      vm.extra_width = {
                        'width': '1200px'
                      };
                    } else {
                      vm.extra_width = {};
                    }
                    angular.copy(data.data.data, vm.model_data);
                    vm.model_data.action_buttons = false;
                    if(aData['Status'] == 'Rejected'){
                      vm.model_data.action_buttons = true;
                    }
                    $state.go('app.outbound.CreateManualTest.confirmation');
                  }
                });
            });
        });
        return nRow;
    }

    vm.model_data = {}
    vm.close = close;
    function close() {
      vm.update = false;
      $state.go('app.outbound.CreateManualTest');
    }

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

    function pop_msg(msg) {
      vm.message = "";
      vm.message = msg;
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
    var elem = angular.element($('form#confirm_manual_test'));
    elem = $(elem).serializeArray();
      vm.bt_disable = true;
      vm.service.apiCall('create_manual_test/', 'POST', elem).then(function(data){
        if(data.message) {
          if("Confirmed Successfully" == data.data) {
            angular.copy(empty_data, vm.model_data);
            vm.close()
          }
          colFilters.showNoty(data.data);
          vm.bt_disable = false;
          reloadData();
        }
      })
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

  vm.reject_adjustment = reject_adjustment;
    function reject_adjustment(data) {
      if(data.$valid) {
        var elem = angular.element($('form#confirm_manual_test'));
        elem = elem[0];
        elem = $(elem).serializeArray();
        vm.service.apiCall('reject_inventory_adjustment/', 'POST', elem, true).then(function(data){
          if(data.message) {
            if (data.data == "Updated Successfully") {
              angular.extend(vm.model_data, vm.empty_data);
              reloadData();
              vm.close();
            } else {
              pop_msg(data.data);
            }
          }
        });
      }
  }

}

