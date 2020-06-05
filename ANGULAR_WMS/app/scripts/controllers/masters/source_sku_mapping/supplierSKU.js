'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SupplierSKUMappingTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.warehouse_level = Session.user_profile.warehouse_level;
    vm.permissions = Session.roles.permissions;
    vm.warehouse_type = Session.user_profile.warehouse_type;
    vm.filters = {'datatable': 'SupplierSKUMappingMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
        DTColumnBuilder.newColumn('supplier_id').withTitle('Supplier ID'),
        DTColumnBuilder.newColumn('wms_code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('supplier_code').withTitle("Supplier's SKU Code"),
        DTColumnBuilder.newColumn('costing_type').withTitle("Costing Type"),
        DTColumnBuilder.newColumn('price').withTitle("Price"),
        DTColumnBuilder.newColumn('margin_percentage').withTitle("Margin Percentage"),
        DTColumnBuilder.newColumn('markup_percentage').withTitle("Mark Up Percentage"),
        DTColumnBuilder.newColumn('mrp').withTitle('MRP'),
        DTColumnBuilder.newColumn('preference').withTitle('Priority'),
        DTColumnBuilder.newColumn('moq').withTitle('MOQ'),
        DTColumnBuilder.newColumn('lead_time').withTitle('Lead Time'),
    ];
    if(vm.warehouse_level==0) {
      vm.dtColumns.push(DTColumnBuilder.newColumn('warehouse').withTitle('Warehouse'))
    }

    vm.dtInstance = {};

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.model_data['create_login'] = false;
                angular.copy(aData, vm.model_data);
                vm.update = true;
                vm.title = "Update Supplier SKU";
                $state.go('app.masters.sourceSKUMapping.mapping');
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
  var empty_data = {supplier_id: "", wms_code: "", supplier_code: "", preference: "", moq: "", price: ""};
  vm.model_data = {};
  angular.copy(empty_data, vm.model_data);

  vm.readonly_permission = function(){
      if(!vm.permissions.change_skusupplier){
        $(':input').attr('readonly','readonly');
      }
    }

  //close popup
  vm.close = function() {

    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.sourceSKUMapping');
  }

  // open popup for new supplier sku mapping
  vm.get_sku_mrp = function(wms_code){
    vm.service.apiCall('get_sku_mrp/','POST' ,{'wms_code':JSON.stringify(wms_code)}).then(function(data){
      if(data.message)
      {
        vm.model_data.mrp = data.data['mrp'];
      }

    })
  }
  vm.add = function() {

    vm.title = "Add Supplier SKU Mapping";
    angular.copy(empty_data, vm.model_data);
    vm.update = false;
    get_suppliers();
    get_warehouses();
    $state.go('app.masters.sourceSKUMapping.mapping');
  }

  vm.submit = function(data) {
    var valid = true;
    if (data.$valid) {
      if(data.costing_type.$modelValue == 'Price Based')
      {
        if(data.price.$viewValue == '')
        {
           valid = false
           vm.service.pop_msg("Price  is Mandatory For Price Based");

        }
       else {
              if (Number(data.price.$viewValue) > Number(data.mrp.$viewValue) )
              {
                  valid = false
                  vm.service.pop_msg("Cost price Should be Less than or Equal to MRP");
              }
         }
      }
      if (data.costing_type.$modelValue == 'Margin Based' &&  data.margin_percentage.$viewValue == '') {
         valid = false
         vm.service.pop_msg("MarkDown Percentage is Mandatory For Margin Based")
      }
      if (data.costing_type.$modelValue == 'Markup Based' && data.markup_percentage.$viewValue == ''){
        valid = false
        vm.service.pop_msg("Markup Percentage is Mandatory For Markup Based")

       }
      if(valid)
      {
       delete(vm.model_data.mrp)
       if ("Add Supplier SKU Mapping" == vm.title) {
           vm.supplier_sku('insert_mapping/');
          }
        else {
           vm.model_data['data-id'] = vm.model_data.DT_RowId;
           vm.supplier_sku('update_sku_supplier_values/');
        }
      }
    }
  }

  vm.send_supplier_doa = function() {
    vm.service.apiCall('send_supplier_doa/', 'POST', vm.model_data, true).then(function(data){
      if(data.message) {
        if(data.data == "Added Successfully") {
          vm.service.refresh(vm.dtInstance);
          vm.close();
        } else {
          vm.service.pop_msg(data.data);
        }
      }
    });
  }
  // add or update supplier sku mapping
  vm.supplier_sku = function(url) {
    vm.service.apiCall(url, 'POST', vm.model_data, true).then(function(data){
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

  // Get all supplier list
  vm.supplier_list = [];
  vm.costing_type_list = ['Price Based', 'Margin Based','Markup Based'];
  function get_suppliers() {
    vm.service.apiCall('get_supplier_list/').then(function(data){
      if(data.message) {
        data = data.data;
        var list = [];
//        angular.forEach(data.suppliers, function(d){
//          list.push(d.supplier_id)
//        });
        vm.supplier_list = list;
        vm.model_data.supplier_id = vm.supplier_list[0];
        vm.costing_type_list = data.costing_type;
        vm.model_data.costing_type = 'Price Based';
      }
    });
  }

  // Get all warehouse list
  vm.warehouse_list = [];
  function get_warehouses() {
    vm.service.apiCall('get_warehouse_list/').then(function(data){
      if(data.message) {
        data = data.data;
        var list = [];
        angular.forEach(data.warehouses, function(d){
          list.push({"id": d.warehouse_id, "name": d.warehouse_name})
        });
        vm.warehouse_list = list;
      }
    });
  }

}
