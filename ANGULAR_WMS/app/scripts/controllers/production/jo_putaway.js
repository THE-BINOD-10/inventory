'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('JOPutawayCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, Data) {
    var vm = this;
    vm.service = Service;
    vm.g_data = Data.order_putaway;
    vm.permissions = Session.roles.permissions;
    vm.industry_type = Session.user_profile.industry_type;	
    vm.table_data = (vm.g_data.sku_view)?'PutawayConfirmationSKU':'PutawayConfirmation' ;
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': vm.table_data},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

    vm.dtColumns = vm.service.build_colums(vm.g_data.tb_headers[vm.table_data]);

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
              vm.service.apiCall('received_jo_data/', 'GET', {data_id: aData.DT_RowAttr['data-id']}).then(function(data){
                if(data.message) {
                  angular.copy(data.data, vm.model_data);
                  $state.go('app.production.JobOrderPutaway.JOPutaway');
                }
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

    vm.update = true;
    vm.close = close;
    function close() {

      vm.confirm_enable = false;
      $state.go('app.production.JobOrderPutaway');
    }

    vm.model_data = {};
    vm.submit = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('jo_putaway_data/', 'POST', elem, true).then(function(data){
        if(data.message) {
          if (data.data == "Updated Successfully") {
            reloadData();
            vm.close();
          } else {
            pop_msg(data.data);
          }
        }
      });
    }

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 2000);
    }

  vm.update_data = update_data;
  function update_data(index, data, last) {
    console.log(data);
    if (last) {
      var total = 0;
      for(var i=0; i < data.sub_data.length; i++) {
        total = total + Number(data.sub_data[i].putaway_quantity);
      }
      if(total < data.product_quantity) {
        var clone = {};
        angular.copy(data.sub_data[index], clone);
        clone.putaway_quantity = data.product_quantity - total;
        data.sub_data.push(clone);
      }
    } else {
      data.sub_data.splice(index,1);
    }
  }

  vm.isLast = isLast;
  function isLast(check) {

    var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
    return cssClass
  }

  vm.cal_quantity = cal_quantity;
  function cal_quantity(record, data) {
    console.log(record);
    var total = 0;
    for(var i=0; i < data.sub_data.length; i++) {
        total = total + Number(data.sub_data[i].putaway_quantity);
    }
    if(data.product_quantity >= total){
      console.log(record.putaway_quantity)
    } else {
      var quantity = data.product_quantity-total;
      if(quantity < 0) {
        quantity = total - Number(record.putaway_quantity);
        quantity = data.product_quantity - quantity;
        record.putaway_quantity = quantity;
      } else {
        record.putaway_quantity = quantity;
      }
    }
  }

  vm.print = print;
  vm.html = "";
  function print() {
    vm.html = angular.element(".putaway_print").clone();
    $(vm.html).removeClass("hide")
    vm.service.print_data(vm.html, 'Job Order Putaway');
  }

  vm.change_sku_view = function(){
    //Data.order_putaway.sku_view = (vm.g_data.sku_view)?'PutawayConfirmationSKU':'PutawayConfirmation';
    Data.order_putaway.sku_view = vm.g_data.sku_view;
    $state.go($state.current, {}, {reload: true});
  }
}
