'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('supplierSKUAttributesTable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.filters = {'datatable': 'supplierSKUAttributes', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
        DTColumnBuilder.newColumn('id').withTitle('Id'),
        DTColumnBuilder.newColumn('supplier_id').withTitle('supplier'),
        DTColumnBuilder.newColumn('attribute_type').withTitle('SKU Attribute Type'),
        DTColumnBuilder.newColumn('attribute_value').withTitle('SKU Attribute Value'),
        DTColumnBuilder.newColumn('price').withTitle('Price'),
        DTColumnBuilder.newColumn('costing_type').withTitle('Costing Type'),
        DTColumnBuilder.newColumn('markdown_percentage').withTitle('MarkDown Percentage'),
        DTColumnBuilder.newColumn('markup_percentage').withTitle('Markup Percentage'),
    ];

    vm.dtInstance = {};

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.model_data['create_login'] = false;
                angular.copy(aData, vm.model_data);
                vm.update = true;
                vm.title = "Update Supplier SKU-Attribute Mapping";
                $state.go('app.masters.sourceSKUMapping.sku_attributes');
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
  var empty_data = {supplier_id: "", attribute_type: "", attribute_value: "", price: "", costing_type: "", markdown_percentage: "", markup_percentage: ""};
  vm.model_data = {};
  angular.copy(empty_data, vm.model_data);

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
    vm.title = "Add Supplier SKU-Attribute Mapping";
    vm.update = false;
    get_suppliers();
    $state.go('app.masters.sourceSKUMapping.sku_attributes');
  }
  vm.submit = function() {
    var valid = true;
    if (!vm.model_data.supplier_id || !vm.model_data.attribute_type || !vm.model_data.attribute_value) {
      valid = false;
      vm.service.pop_msg("Please Fill * Mark Fields");
    } else if (vm.model_data.costing_type == 'Price Based' && vm.model_data.price == '') {
      valid = false;
      vm.service.pop_msg("Price  is Mandatory For Price Based");
    } else if (vm.model_data.costing_type == 'Margin Based' && vm.model_data.markdown_percentage == '') {
      valid = false;
      vm.service.pop_msg("MarkDown Percentage is Mandatory For Margin Based");
    } else if (vm.model_data.costing_type == 'Markup Based' && vm.model_data.markup_percentage == '') {
      valid = false;
      vm.service.pop_msg("Markup Percentage is Mandatory For Markup Based");
    }
    if (valid) {
      if ("Add Supplier SKU-Attribute Mapping" == vm.title) {
        vm.model_data['api_type'] = 'insert';
        vm.supplier_sku('insert_supplier_attribute/');
      } else {
        vm.model_data['api_type'] = 'update';
        vm.model_data['id'] = vm.model_data.id;
        vm.supplier_sku('insert_supplier_attribute/');
      }
    }
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
  vm.attribute_type = ['Brand', 'Category']
  vm.costing_type_list = ['Price Based', 'Margin Based','Markup Based'];
  function get_suppliers() {
    vm.service.apiCall('get_supplier_list/').then(function(data){
      if(data.message) {
        data = data.data;
        var list = [];
        angular.forEach(data.suppliers, function(d){
          list.push(d.id)
        });
        vm.supplier_list = list;
        vm.model_data.supplier_id = vm.supplier_list[0];
        vm.costing_type_list = data.costing_type;
        vm.model_data.costing_type = 'Price Based';
        vm.model_data.attribute_type = 'Brand';
      }
    });
  }

}

