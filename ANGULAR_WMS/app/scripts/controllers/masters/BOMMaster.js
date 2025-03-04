'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('BOMMasterTable',['$scope', '$http', '$state', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.filters = {'datatable': 'BOMMaster', 'search0':'', 'search1':'', 'search2':'', 'search3':'', 'search4':'', 'search5':''}
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
        DTColumnBuilder.newColumn('Org Id').withTitle('Org Id'),
        DTColumnBuilder.newColumn('Plant Code').withTitle('Plant Code'),
        DTColumnBuilder.newColumn('Plant Name').withTitle('Plant Name'),
        DTColumnBuilder.newColumn('Department Name').withTitle('Department Name'),
        DTColumnBuilder.newColumn('Instrument Id').withTitle('Instrument Id'),
        DTColumnBuilder.newColumn('Instrument Name').withTitle('Instrument Name'), 
        DTColumnBuilder.newColumn('Test Code').withTitle('Test Code'),
        DTColumnBuilder.newColumn('Test Description').withTitle('Test Description')
    ];

    vm.dtInstance = {};

    var empty_data = {"Product_sku":"",
                      "data": [
                        {"Material_sku":"", "Material_Quantity":"", "Units":"", "BOM_ID":"", "wastage_percent":"",
                         "unit_list": []}
                      ]
                     };
    vm.model_data = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.service.apiCall('get_bom_data/', 'GET', {instrument_id : aData["Instrument Id"], org_id:aData["Org Id"], data_id: aData.DT_RowAttr["data-id"]}).then(function(data) {
                  if(data.message) {
                    vm.update = true;
                    vm.title = "Update BOM";
                    angular.copy(data.data, vm.model_data);
                    //update_units();
                    $state.go('app.masters.BOMMaster.BOM');
                  }
                });
            });
        });
        return nRow;
    };

    function update_units(){

      angular.forEach(vm.model_data.data, function(data){

        data.Units = vm.units[vm.units.indexOf(data.Units)];
      });
    }

    vm.update_data = function(index) {

      if (index == vm.model_data.data.length-1) {
        vm.model_data.data.push({"Material_sku":"", "Material_Quantity":"", "Units":"KGS", "BOM_ID":"", "wastage_percent":""});
      } else {
        if (vm.update) {
          delete_bom_data(vm.model_data.data[index].BOM_ID);
        }
        vm.model_data.data.splice(index,1);
      }
    }

    function delete_bom_data(data) {
      vm.service.apiCall('delete_bom_data/', 'GET', {data_id: data}).then(function(data){
        if(data.message) {
          pop_msg(data.data);
        }
      });
    }

    vm.units = []//["KGS", "UNITS", "METERS", "INCHES", "CMS", "REAMS", "GRAMS", "GROSS", "ML", "LITRE", "FEET", "SHEETS", "NUMBERS"];
    vm.get_uom_list = function(row_data) {
      console.log(row_data);
      var req_data = {'uom_type': 'consumption', 'sku_code': row_data.Material_sku}
      vm.service.apiCall("get_sku_uom_list/", "GET", req_data).then(function(data) {
        if(data.message) {
          row_data.unit_list = [];
          angular.forEach(data.data.data, function(uom_data){
            row_data.unit_list.push(uom_data.uom);
          });
          if(row_data.unit_list && row_data.Units== ''){
            row_data.Units = row_data.unit_list[0];
          }
        }
      });
    }

    vm.base = function() {

      vm.title = "Add BOM";
      vm.update = false;
      angular.copy(empty_data, vm.model_data);
    }
    vm.base();

    vm.close = function() {

      angular.copy(empty_data, vm.model_data);
      $state.go('app.masters.BOMMaster');
    }

    vm.add = function() {

      vm.base();
      $state.go('app.masters.BOMMaster.BOM');
    }

  vm.create_bom = function(form) {

    var send = $("form:visible").serializeArray();
    vm.service.apiCall('insert_bom_data/', 'POST', send, true).then(function(data){
      if(data.message) {
        if(data.data == 'Added Successfully') {
          vm.close();
          vm.service.refresh(vm.dtInstance);
        } else {
          vm.service.pop_msg(data.data);
        }
      }
    });
  }

  vm.submit = function(form) {
    if(form.$valid) {
      vm.create_bom(form);
    }
  }

}

