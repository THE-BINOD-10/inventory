'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SupplierSKUMappingDOATable',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
  var vm = this;
  vm.apply_filters = colFilters;
  vm.service = Service;
  vm.warehouse_level = Session.user_profile.warehouse_level;
  vm.permissions = Session.roles.permissions;
  vm.warehouse_type = Session.user_profile.warehouse_type;
  vm.model_data = {};
  var empty_data = {supplier_id: "", wms_code: "", supplier_code: "", preference: "", moq: "", price: ""};
  vm.costing_type_list = ['Price Based', 'Margin Based','Markup Based'];
  vm.filters = {'datatable': 'SupplierSKUMappingDOAMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
      DTColumnBuilder.newColumn('requested_user').withTitle('Requested User'),
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
      DTColumnBuilder.newColumn('status').withTitle('Status'),
  ];
  if(vm.warehouse_level==0) {
      vm.dtColumns.push(DTColumnBuilder.newColumn('request_type').withTitle('Request Type'))
      vm.dtColumns.push(DTColumnBuilder.newColumn('warehouse').withTitle('Warehouse'))
    }

  vm.dtInstance = {};

  function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
      $('td', nRow).unbind('click');
      $('td', nRow).bind('click', function() {
          $scope.$apply(function() {
              // vm.model_data['create_login'] = false;
              var open_po_status = false;
              var current_grn_status = false;
              var master_status = false;
              var margin_perc = parseInt(aData['margin_percentage'])
              var mark_perc = parseInt(aData['markup_percentage'])
              var lead_time = parseInt(aData['lead_time'])
              aData['margin_percentage'] = margin_perc?margin_perc:0;
              aData['markup_percentage'] = mark_perc?mark_perc:0;
              aData['lead_time'] = lead_time?lead_time:0
              angular.copy(aData, vm.model_data);
              if (vm.model_data['request_type'] == 'Inbound') {
                open_po_status = true;
                current_grn_status = true;
              } else {
                master_status = true;
              }
              vm.model_data.update = [{'label': 'Master', status: master_status}, {'label': 'Open PO', status: open_po_status}, {'label': 'Current GRN', status: current_grn_status}]
              vm.update = true;
              vm.title = "Supplier SKU DOA";
              vm.is_doa = true;
              $state.go('app.masters.sourceSKUMapping.mapping');
          });
      });
      return nRow;
  }

  $scope.$on('change_filters_data', function(){
    vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
    vm.service.refresh(vm.dtInstance);
  });

  //close popup
  vm.close = function() {

    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.sourceSKUMapping');
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
       // if ("Supplier SKU DOA" == vm.title) {
       //     vm.supplier_sku('insert_mapping/');
       //    }
       //  else {
       //     vm.model_data['data-id'] = vm.model_data.DT_RowId;
       //     vm.supplier_sku('update_sku_supplier_values/');
       //  }
       if (parseInt(vm.model_data.model_id) == 0){
        vm.supplier_sku('insert_mapping/');
       } else {
        vm.model_data['data-id'] = parseInt(vm.model_data.model_id);
        vm.supplier_sku('update_sku_supplier_values/');
       }

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
}