'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PricingMaster',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.reloadData = function() {
    vm.filters = {'datatable': 'PricingMaster'}
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
       var columns = ["SKU Code", "SKU Description", "Selling Price Type", "Price"];
       vm.dtColumns = vm.service.build_colums(columns);

    }
    vm.reloadData();

    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.service.refresh(vm.dtInstance);
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                var send = {sku_code: aData['SKU Code'], price_type: aData['Selling Price Type']};
                vm.service.apiCall("get_pricetype_data/", "GET", send).then(function(data) {
                    if(data.message) {
                      if (data.data.status) {
                        angular.copy(data.data.data, vm.model_data);
                        vm.update = true;
                        vm.title = "Update Pricing"
                        $state.go('app.masters.PricingMaster.Add');
                      }
                    }
                });
            });
            return nRow;
         });
    }

    var empty_data = {
                    "sku_code": "","selling_price_type":"",
                    "data": [{"min_amount": "", "max_amount": "", "price": "", "discount": ""}]
                    }
    vm.update = false;
    vm.title = "ADD PRICING"
    vm.model_data = {};
    angular.copy(empty_data, vm.model_data);

  vm.close = function() {
    angular.copy(empty_data, vm.model_data);
    $state.go('app.masters.PricingMaster');
  }

  vm.add = function() {

    vm.title = "ADD PRICING"
    angular.copy(empty_data, vm.model_data);
    vm.update = false;
    $state.go('app.masters.PricingMaster.Add');
  }


  vm.send_pricing = function(url, data) {

    vm.service.apiCall(url, 'POST', data, true).then(function(data){
      if(data.message) {
        if (data.data == 'New Pricing Added' || data.data == 'Updated Successfully')  {
          vm.service.refresh(vm.dtInstance);
          vm.close();
        } else {
          vm.service.pop_msg(data.data);
        }
      }
    });
  }

  vm.submit = function(data) {
    if (data.$valid) {
      var send = $(data.$name).serializeArray();
      if ("ADD PRICING" == vm.title) {
        vm.send_pricing('add_pricing/', send);
      } else {
        vm.send_pricing('update_pricing/', send);
      }
    } else {
      vm.service.pop_msg('Please fill required fields');
    }
  }

  vm.checkRange = function(amt, index, data, name) {

    if (!amt){
      return false;
    }

    if(!data[index].min_unit_range && data[index].max_unit_range){
      Service.showNoty("Fill The Min Unit Range First");
    }

    if (name == 'min_amount' && data[index].max_amount) {

      if (Number(data[index].min_amount) >= Number(data[index].max_amount)) {

        data[index][name] = "";
        Service.showNoty("Min Amount Should Be lesser Than Mix Amount")
        return false;
      }
    } else if(name == 'max_amount' && data[index].min_amount) {

      if (Number(data[index].min_amount) > Number(data[index].max_amount)) {

        data[index][name] = "";
        Service.showNoty("Max Amount Should Be Greater Than Min Amount");
        return false;
      }
    }
    for (var i = 0; i < data.length; i++) {

      var temp = data[i];
      if(i != index) {
        if (Number(temp.min_unit_range) <= Number(amt) && Number(amt) <= Number(temp.max_unit_range)) {
          vm.clearFields(data, index);
          break;
        } else if (Number(temp.min_unit_range) < Number(amt) && Number(amt) < Number(temp.max_unit_range)) {
          vm.clearFields(data, index);
          break;
        } else if(Number(data[index].min_unit_range) <= Number(temp.min_unit_range) && Number(data[index].max_unit_range) >= Number(temp.min_amount)) {
          if (Number(data[index].min_unit_range) > Number(temp.min_unit_range) && Number(data[index].max_unit_range) > Number(temp.min_unit_range)) {
            vm.clearFields(data, index);
            break;
          }
        }
      }
    }
  }

 vm.reports = {}
 vm.report_data = {};
 vm.empty_data ={};
  vm.toggle_price_master = function() {
    var send = {};
    if(!vm.toggle_brand){
        vm.reloadData();
    } else {
    var name = 'brand_price_master';
    vm.service.apiCall("get_report_data/", "GET", {report_name: name}).then(function(data) {
    	if (data.message) {
    	  if ($.isEmptyObject(data.data.data)) {
    		  vm.datatable = false;
    		  vm.dtInstance = {};
    	  } else {
      	  vm.reports[name] = data.data.data.excel_name;
      	  angular.copy(data.data.data, vm.report_data)
          vm.service.get_report_dt(vm.empty_data, vm.report_data).then(function(datam) {
            vm.empty_data = datam.empty_data;
            angular.copy(vm.empty_data, vm.filters_dt_data)
            vm.dtOptions = datam.dtOptions;
            vm.dtColumns = datam.dtColumns;
            vm.datatable = true;
            vm.dtInstance = {};
          })
        }
    	}
  	})
    }
  }
  vm.clearFields = function(data, index){
    data[index][name] = "";
    data[index].min_unit_range = '';
    data[index].max_unit_range = '';
    Service.showNoty("Range Already Exist");
  }

  vm.update_data = function(index) {

    vm.model_data.data.splice(index,1);
  }

  vm.add_data = function() {
    vm.model_data.data.push({"min_amount": "", "max_amount": "", "price": "", "discount": ""})
  }
}
