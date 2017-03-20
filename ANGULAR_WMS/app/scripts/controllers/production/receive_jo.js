'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ReceiveJOCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, Data) {
    var vm = this;
    vm.service = Service;
    vm.g_data = Data.receive_jo;
    vm.permissions = Session.roles.permissions;
    vm.sku_view = vm.g_data.sku_view;
    vm.table_name = (vm.g_data.sku_view)? 'ReceiveJOSKU' : 'ReceiveJO';
    vm.filters = {'datatable': vm.table_name};
    vm.tb_data = {};
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: vm.filters,
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

    vm.dtColumns = vm.service.build_colums(vm.g_data.tb_headers[vm.table_name]);

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
              var data = {};
              if (vm.sku_view) {
                data['job_id'] = aData.DT_RowAttr['data-id'];
              } else {
                data['data_id'] = aData.DT_RowAttr['data-id'];
              }
              vm.service.apiCall('confirmed_jo_data/', 'GET', data).then(function(data){
                if(data.message) {
                  angular.copy(data.data, vm.model_data);
                  var skus_list = [];
                  angular.forEach(vm.model_data.data, function(record){
                    if (skus_list.indexOf(record.wms_code) == -1){
                        skus_list.push(record.wms_code);
                        }
                  });
                  vm.final_data = {};
                  for (var i=0; i<skus_list.length; i++){
                    var sku_one = skus_list[i];
                    vm.final_data[sku_one] = 0;
                    angular.forEach(vm.model_data.data, function(record){
                      if (record.wms_code == sku_one){
                        vm.final_data[sku_one] = vm.final_data[sku_one] + record.product_quantity;
                      }
                    });
                  }


		  vm.order_ids_list = data.data.order_ids.toString();
                  $state.go('app.production.ReveiveJO.ReceiveJobOrder');
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

    vm.model_data = {};

    vm.close = close;
    function close() {

      vm.print_enable = false;
      $state.go('app.production.ReveiveJO');
    } 

    vm.html = "";
    vm.print_enable = false;
    vm.submit = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('confirm_jo_grn/', 'POST', elem).then(function(data){
        if(data.message) {
          vm.reloadData();
          if (data.data["status"]) {
            pop_msg(data.data.status);
            change_pallet_ids(data.data.data);
          } else {
            vm.html = $(data.data)[2];
            var html = $(vm.html).closest("form").clone();
            angular.element(".modal-body").html($(html).find(".modal-body > .form-group"));
            vm.print_enable = true;
          }
        }
      });
    }

    function change_pallet_ids(data) {

      angular.forEach(vm.model_data.data, function(record){

        if(data[record.id]) {
          angular.forEach(record.sub_data, function(item, index) {

            item["pallet_id"] = data[record.id][index][1]["pallet_id"];
            item["status_track_id"] = data[record.id][index][3];
          });
        }
      });
      console.log(vm.model_data, data); 
    }

    vm.save = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('save_receive_jo/', 'POST', elem).then(function(data){
        if(data.message) {
          if (data.data == 'Saved Successfully') {
            vm.close();
            vm.reloadData();
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
        total = total + Number(data.sub_data[i].received_quantity);
      }
      if(total < data.product_quantity) {
        var clone = {};
        angular.copy(data.sub_data[index], clone);
        clone.received_quantity = data.product_quantity - total;
        clone.received_quantity = clone.received_quantity.toFixed(2);
        clone.pallet_id = "";
        clone.status_track_id = "";
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
        total = total + Number(data.sub_data[i].received_quantity);
    }
    if(data.product_quantity >= total){
      console.log(record.received_quantity)
    } else {
      var quantity = data.product_quantity-total;
      if(quantity < 0) {
        quantity = total - Number(record.received_quantity);
        quantity = data.product_quantity - quantity;
        record.received_quantity = quantity;
      } else {
        record.received_quantity = quantity;
      }
    }
  } 

  vm.print = print;
  function print() {
    vm.service.print_data(vm.html);
  }

  vm.change_sku_view = function(){

    Data.receive_jo.sku_view = vm.sku_view;
    $state.go($state.current, {}, {reload: true});    
  }

  }

