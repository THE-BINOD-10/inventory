'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('PicklistGeneratedCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'printer', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session, printer, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.customertype = Session.user_profile.industry_type
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
    vm.submit = function(form) {

      if(form.$valid) {
      var elem = angular.element($('form'));
      elem = elem[1];
      elem = $(elem).serializeArray();
      vm.service.apiCall('rm_picklist_confirmation/', 'POST', elem, true).then(function(data){
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
        var dict = {zone: item.zone, location: item.location, picked_quantity: item.picked_quantity, pallet_code: item.pallet_code, capacity: item.picked_quantity};
        if (item.pallet_code) {
          dict["pallet_visible"] = true;
        }
        item["sub_data"] = []
        item.sub_data.push(dict);
      })
      console.log(vm.model_data);
    }

  vm.cal_quantity = cal_quantity;
  function cal_quantity(record, data) {
    console.log(record);

    if(!record.picked_quantity) {

      return false;
    }

    if (Number(record.picked_quantity) > record.capacity) {

      record.picked_quantity = record.capacity;
    }

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
        clone.pallet_code = "";
        clone.picked_quantity = 0;
        //clone.picked_quantity = data.reserved_quantity - total;
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

  vm.checkPallet = function(index, sku_data) {

    var status = false;
    for(var i = 0; i < sku_data.sub_data.length; i++) {

      if(sku_data.sub_data[i].pallet_code.toLowerCase() == sku_data.sub_data[index].pallet_code.toLowerCase() && i != index) {

        status = true;
        break;
      }
    }
    return status;
  }

  vm.checkCapacity = function(index, sku_data, from, element) {

    console.log(vm.model_data);
    var row_data = sku_data.sub_data[index];
    element.preventDefault();
    if (from == "location") {

      if(!row_data.location) {

        vm.service.showNoty("Please Fill Location");
        row_data.picked_quantity = 0;
        return false;
      }
    } else if (from == "pallet_code"){
      if (!row_data.location) {

        vm.service.showNoty("Please Fill Location");
        row_data.picked_quantity = 0;
        return false;
      } else if (!row_data.pallet_code) {

        vm.service.showNoty("Please Fill Pallet Code");
        row_data.picked_quantity = 0;
        return false;
      }
    }

    if(vm.checkPallet(index, sku_data)) {

      row_data.pallet_code = "";
      vm.service.showNoty("Already Pallet Code Exist");
      return false;
    }

    var send = {sku_code: sku_data.wms_code, location: row_data.location, pallet_code: row_data.pallet_code}

    vm.service.apiCall("get_sku_stock_check/", "GET", send).then(function(data){

      if(data.message) {

        if(data.data.status == 0) {

          vm.service.showNoty(data.data.message);

          if(data.data.message== "Invalid Location") {

            row_data.location = "";
            angular.element(element.target).focus();
          } else if (data.data.message == "Invalid Location and Pallet code Combination") {

            row_data.pallet_code = "";
            angular.element(element.target).focus();
          }
          row_data.picked_quantity = 0;
        } else {

          var data = data.data.data;
          data = Object.values(data)[0];
          row_data["capacity"] = Number(data.total_quantity);

          if(Number(row_data.picked_quantity) > Number(data.total_quantity)) {

            row_data.picked_quantity = Number(data.total_quantity);
          } else {

            var total = 0;
            row_data.picked_quantity = 0;
            angular.forEach(sku_data.sub_data, function(record) {

              total += Number(record.picked_quantity);
            })

            if (sku_data.reserved_quantity > total) {

              row_data.picked_quantity = sku_data.reserved_quantity - total;
            } else {

              row_data.picked_quantity = 0;
            }

            if (row_data.picked_quantity > row_data.capacity) {

              row_data.picked_quantity = row_data.capacity;
            }
          }
        }
      }
    })
  }

  vm.serial_numbers = [];
  vm.check_imei_exists = function(event, data1, index, innerIndex) {
    event.stopPropagation();
    if (event.keyCode == 13 && data1.imei_number.length > 0) {
      // if(vm.permissions.barcode_generate_opt != "sku_serial") {
      var temp_dict = {'is_rm_picklist': true}
      temp_dict[data1.id] = data1.imei_number
      vm.service.apiCall('check_imei/', 'GET', temp_dict).then(function(data){
        if(data.message) {
          if (!data.data.status && data1.wms_code == data.data.data.sku_code) {
            // data1.received_quantity = Number(sku.received_quantity) + 1;
            // data1.imei_number = data.data.data.label;
            let skuWiseQtyTotal = 0;
            angular.forEach(data1.sub_data, function(row){
              skuWiseQtyTotal += Number(row.picked_quantity);
            });
            // tempUniqueDict dict checking purpose only don't use anyware
            if (data1.reserved_quantity > skuWiseQtyTotal) {
              if (data1.sub_data[innerIndex].accept_imei && !data1.sub_data[innerIndex].tempUniqueDict[data1.imei_number]) {
                data1.sub_data[innerIndex].picked_quantity = Number(data1.sub_data[innerIndex].picked_quantity) + 1;
                data1.sub_data[innerIndex].accept_imei.push(data1.imei_number);
                data1.sub_data[innerIndex].tempUniqueDict[data1.imei_number] = data1.imei_number;
                data1.imei_number = "";
              } else {
                if (data1.sub_data[innerIndex].tempUniqueDict && data1.sub_data[innerIndex].tempUniqueDict[data1.imei_number]) {
                  Service.showNoty("Scanned serial number already exist");
                  data1.imei_number = "";
                } else if (!data1.sub_data[innerIndex].tempUniqueDict) {
                  data1.sub_data[innerIndex]['accept_imei'] = [];
                  data1.sub_data[innerIndex]['tempUniqueDict'] = {};
                  data1.sub_data[innerIndex].tempUniqueDict[data1.imei_number] = data1.imei_number;
                  data1.sub_data[innerIndex].accept_imei.push(data1.imei_number);
                  data1.sub_data[innerIndex].picked_quantity = 1;
                  data1.imei_number = "";
                }
              }
              var sku_code = data.data.data.sku_code;
              if (data1.wms_code != sku_code) {
                Service.showNoty("Scanned label belongs to "+sku_code);
                data1.imei_number = "";
                return false;
              }
            } else {
              Service.showNoty("No Quantity Available");
            }
          } else {
            Service.showNoty(data.data.status);
            data1.imei_number = "";
          }
          vm.reloadData();
        }
        data1["disable"] = false;
      })
    }
  }

  }
