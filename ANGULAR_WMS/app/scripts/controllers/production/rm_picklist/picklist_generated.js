'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PicklistGeneratedCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'printer', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, printer, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.tb_data = {};
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'PickelistGenerated'},
              xhrFields: {
                withCredentials: true
              },
              complete: function(jqXHR, textStatus) {
                $scope.$apply(function(){
                  angular.copy(JSON.parse(jqXHR.responseText), vm.tb_data)
                })
              }
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

    vm.dtColumns = [
        DTColumnBuilder.newColumn('Job Code').withTitle('Job Code'),
        DTColumnBuilder.newColumn('Creation Date').withTitle('Creation Date'),
        DTColumnBuilder.newColumn('Order Type').withTitle('Order Type'),
        DTColumnBuilder.newColumn('Quantity').withTitle('Quantity')
    ];

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
              var elem = {'data_id': aData.DT_RowAttr['data-id']};
              vm.service.apiCall('view_rm_picklist/', 'POST', elem).then(function(data){
                if(data.message) {
                  angular.copy(data.data, vm.model_data);
                  change_model_data();
                  $state.go('app.production.RMPicklist.RawMaterialPicklist');
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

    vm.model_data = {}
    vm.update = true;

    vm.close = close;
    function close() {

      vm.confirm_disable = false;
      $state.go('app.production.RMPicklist');
    }

    vm.print = print;
    function print() {
      Service.apiCall("print_rm_picklist/", "GET", {data_id: vm.model_data.job_code}).then(function(resp) {
        if(resp.message) {
          vm.service.print_data($(resp.data), 'Raw Material Picklist');
        }
      })
    }

    vm.confirm_disable = false;
    vm.submit = function() {
      var elem = angular.element($('form'));
      elem = elem[1];
      elem = $(elem).serializeArray();
      vm.service.apiCall('rm_picklist_confirmation/', 'POST', elem).then(function(data){
        if(data.message) {
          reloadData();
          if(data.data == "Picklist Confirmed") {
            vm.close();
            reloadData();
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

    vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

    function change_model_data() {

      angular.forEach(vm.model_data.data, function(item){
        item["sub_data"] = [{zone: item.zone, location: item.location, picked_quantity: item.picked_quantity}]
      })
      console.log(vm.model_data);
    }

  vm.cal_quantity = cal_quantity;
  function cal_quantity(record, data) {
    console.log(record);
    var total = 0;
    for(var i=0; i < data.sub_data.length; i++) {
        total = total + Number(data.sub_data[i].picked_quantity);
    }
    if(data.reserved_quantity >= total){
      console.log(record.picked_quantity)
    } else {
      var quantity = data.reserved_quantity-total;
      if(quantity < 0) {
        quantity = total - Number(record.picked_quantity);
        quantity = data.reserved_quantity - quantity;
        record.picked_quantity = quantity;
      } else {
        record.picked_quantity = quantity;
      }
    }
  }

  vm.update_data = update_data;
  function update_data(index, data, last) {
    console.log(data);
    if (last) {
      var total = 0;
      for(var i=0; i < data.sub_data.length; i++) {
        total = total + Number(data.sub_data[i].picked_quantity);
      }
      if(total < data.reserved_quantity) {
        var clone = {};
        angular.copy(data.sub_data[index], clone);
        clone.picked_quantity = data.reserved_quantity - total;
        data.sub_data.push(clone);
      }
    } else {
      data.sub_data.splice(index,1);
    }
  }

  vm.process = false;
  vm.update_stock = function() {

    vm.process = true;
    var elem = angular.element($('form'));
    elem = elem[1];
    elem = $(elem).serializeArray();
    vm.service.apiCall('update_rm_picklist/', 'POST', elem).then(function(data){
      if(data.message) {
        angular.copy(data.data, vm.model_data);
        change_model_data();
      }
      vm.process = false;
    })
  }

  }

