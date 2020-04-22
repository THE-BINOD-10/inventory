'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('RaiseStockTransferCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.apply_filters = colFilters;
    vm.permissions = Session.roles.permissions;
    vm.industry_type = Session.user_profile.industry_type;
    vm.user_type = Session.user_profile.user_type;

    vm.filters = {'datatable': 'RaiseST', 'search0':'', 'search1':''};
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
    var columns = ['Warehouse Name', 'Total Quantity']
    vm.dtColumns = vm.service.build_colums(columns);

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        // Unbind first in order to avoid any duplicate handler (see https://github.com/l-lin/angular-datatables/issues/87)
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                $http.get(Session.url+'update_raised_st?warehouse_name='+aData['Warehouse Name']).success(function(data, status, headers, config) {
                  console.log(data);
                  vm.update = true;
                  vm.get_sellers_list(true);
                  vm.title = "Update Stock Transfer";
                  angular.copy(data, vm.model_data);
                  vm.changeDestSeller();
                  $state.go('app.inbound.RaisePo.StockTransfer');
                });
            });
        });
        return nRow;
    } 

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    $scope.$on('change_filters_data', function(){
      if($("#"+vm.dtInstance.id+":visible").length != 0) {
        vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
        vm.reloadData();
      }
    });

    vm.update = true;
    vm.status_data = ["Active","Inactive"];
    vm.status= vm.status_data[0];
    var empty_data = {"Supplier_ID":"",
                      "POName": "",
                      "ShipTo": "",
                      "warehouse_name": "",
                      "source_seller_id": "",
                      "dest_seller_id": "",
                      "data": [
                        {"WMS_Code":"", "Supplier_Code":"", "Quantity":"", "Price":""}
                      ]
                     };
    vm.model_data = {};
    angular.copy(empty_data, vm.model_data);

    vm.get_sellers_list = get_sellers_list;
    function get_sellers_list(is_update) {
      vm.sellers_list = [];
      vm.service.apiCall('get_sellers_list/').then(function(data){
      if(data.message) {
        vm.sellers_list = data.data.sellers;
        if(vm.sellers_list && !is_update) {
          vm.model_data.source_seller_id = vm.sellers_list[0].id;
        }
      }
    });
    }

    vm.close = close;
    function close() {

      vm.model_data = {};
      angular.copy(empty_data, vm.model_data);
      $state.go('app.inbound.RaisePo');
    }
    vm.add = add;
    function add() {

      $http.get(Session.url+'raise_st_toggle/').success(function(data, status, headers, config) {
        vm.model_data['warehouse_list'] = data.user_list;
      });
      vm.get_sellers_list();
      vm.title = "Raise Stock Transfer";
      vm.model_data = {};
      angular.copy(empty_data, vm.model_data);
      vm.update = false;
      $state.go('app.inbound.RaisePo.StockTransfer');
    } 
    vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }
    vm.update_data = update_data;
    function update_data(index) {

      if (index == vm.model_data.data.length-1) {
        vm.model_data.data.push({"wms_code":"", "quantity":"", "price":""});
      } else {
        vm.delete_st(vm.model_data.data[index]);
        vm.model_data.data.splice(index,1);
      }
    }

    vm.save_stock = save_stock;
    function save_stock(data) {
      if (data.$valid) {
        var elem = angular.element($('form'));
        elem = elem[1];
        elem = $(elem).serializeArray();
        vm.service.apiCall('save_st/', 'POST', elem, true).then(function(data){
          if(data.message){
            if(data.data == 'Added Successfully') {
              vm.close();
              vm.reloadData();
            } else {
              pop_msg(data.data);
            }
          }
        });
      }
    }

    vm.confirm_stock = confirm_stock;
    function confirm_stock(data) {

     if (data.$valid) {
      var elem = angular.element($('form'));
      elem = elem[1];
      elem = $(elem).serializeArray();
      vm.service.apiCall('confirm_st/', 'POST', elem, true).then(function(data){
        if(data.message){
          if(data.data == 'Confirmed Successfully') {
            vm.close();
            vm.reloadData();
          } else {
            pop_msg(data.data);
          }
        }
      });
     }
    }

    vm.delete_st = delete_st;
    function delete_st(data){
      console.log(data);
      if(typeof(data.id) == "number") {
        $http.get(Session.url+"delete_st/?data_id="+data.id, {withCredential: true}).success(function(data){
          pop_msg(data);
        })
      }
    }

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 2000);
      reloadData();
    }

    vm.changeDestSeller = function() {
      vm.dest_sellers_list = [];
      var temp_data = {warehouse: vm.model_data.warehouse_name}
      vm.service.apiCall("get_sellers_list/", "GET", temp_data).then(function(data){
      if(data.message) {
        vm.dest_sellers_list = data.data.sellers;
        if(vm.dest_sellers_list) {
          vm.model_data.dest_seller_id = vm.sellers_list[0].id;
        }
      }
    });
  }


  vm.get_sku_data = function(record, item, index) {
    record.wms_code = item.wms_code;
    var get_data = {sku_codes: record.wms_code}
    vm.service.apiCall("get_customer_sku_prices/", "POST", get_data).then(function(data) {
      if(data.message) {
        data = data.data;
        if(data.length > 0) {
          data = data[0]
          record.mrp = data.mrp;
          if(!(record.order_quantity)) {
            record.order_quantity = 1
          }
          if(!(record.price)) {
            record.price = data.mrp;
          }
        }
      }
    });
  }

}




//        if(data.length > 0) {

//      }