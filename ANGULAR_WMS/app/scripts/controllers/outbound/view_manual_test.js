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
                    angular.copy(data.data, vm.model_data);
                    vm.model_data.plant_name = data.data.plant_name;
                    vm.model_data.warehouse_name = data.data.warehouse_name;
                    vm.model_data.warehouse = data.data.warehouse;
                    $state.go('app.outbound.CreateManualTest.confirmation');
                  }
                });
            });
        });
        return nRow;
    } 

    function change_data(data, warehouse_id) {
      //var dat = {};
      //dat['po_number'] = data.po_number;
      //dat['order_id'] = data.order_id;
      //dat['data'] = []
      //for (var i = 0; i < data.data.length; i++) {
      //  var temp = data.data[i];
      //  var qt = (vm.permissions.use_imei)?0:temp[3];
      //  dat.data.push({'wms_code': temp[0], 'pallet_number': temp[6], 'original_quantity': temp[2],
      //            'id': temp[5], 'orig_loc_id': temp[4], 'sub_data': [{'loc': temp[1], 'quantity': qt}],
      //            'unit': temp[7], 'orig_data': ''})
      //
      //}
      angular.copy(data, vm.model_data);
      vm.model_data.warehouse_id = warehouse_id;
      vm.model_data["sku_total_quantities"] = data.sku_total_quantities;
      //if(vm.permissions.use_imei) {
      //  angular.forEach(vm.model_data.data, function(data){
      //    data.sub_data[0].quantity = 0;
      //  })
      //}
      console.log(data);
      angular.copy(vm.model_data.sku_total_quantities ,vm.remain_quantity);
      vm.count_sku_quantity();
    }

    vm.model_data = {}
    vm.close = close;
    function close() {
      vm.update = false;
      $state.go('app.outbound.CreateManualTest');
    }

    vm.submit = function() {
      var elem = angular.element($('form'));
      vm.model_data.data.forEach(function(item){
           item.wrong_sku = false;
       });
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('putaway_data/', 'POST', elem, true).then(function(data){
        if(data.message) {
          if(data.data == "Updated Successfully") {
            vm.close();
            reloadData();
          } else {
            $state.go('app.inbound.PutAwayConfirmation.confirmation');
            vm.model_data.data.forEach(function(item){
              if (data.data.wrong_skus.indexOf(item.wms_code) != -1) {
                    item.wrong_sku = true;
              }
             });
            pop_msg(data.data.status);
          }
        }
      }); 
    }

    function pop_msg(msg) {
      vm.message = "";
      vm.message = msg;
     }

  vm.isLast = isLast;
  function isLast(check) {

    var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
    return cssClass
  }

  vm.update_data = update_data;
  function update_data(index, data, last) {
    console.log(data);
    var remain = vm.model_data.sku_total_quantities[data.wms_code] - vm.remain_quantity[data.wms_code]
    if (last) {
      if(!(vm.model_data.sku_total_quantities[data.wms_code] <= vm.remain_quantity[data.wms_code])){
        var total = 0;
        for(var i=0; i < data.sub_data.length; i++) {
          total = total + parseInt(data.sub_data[i].quantity);
        }
        if(total < data.original_quantity) {
          var clone = {};
          angular.copy(data.sub_data[index], clone);
          var temp = data.original_quantity - total;
          clone.quantity = (remain < temp)?remain:temp;
          //clone.quantity = data.original_quantity - total;
          data.sub_data.push(clone);
        }
      }
    } else {
      data.sub_data.splice(index,1);
    }
    vm.count_sku_quantity();
  }

}

