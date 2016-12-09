'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('RaiseRWOCtrl',['$scope', '$http', '$state', '$q', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $q, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, service) {

    var vm = this;
    vm.service = service;

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'RaiseRWO'},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

    vm.dtColumns = [
        DTColumnBuilder.newColumn('RWO Reference').withTitle('RWO Reference'),
        DTColumnBuilder.newColumn('Vendor ID').withTitle('Vendor ID'),
        DTColumnBuilder.newColumn('Vendor Name').withTitle('Vendor Name'),
        DTColumnBuilder.newColumn('Creation Date').withTitle('Creation Date')
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
                console.log(aData);
                vm.service.apiCall('saved_rwo_data/', 'GET', {data_id: aData.DT_RowAttr['data-id']}).then(function(data){
                  if(data.message) {
                    vm.update = true;
                    angular.copy(data.data, vm.model_data);
                    $state.go('app.production.RaiseJO.RWO');
                  }
                });
            });
        });
        return nRow;
    } 

    vm.update = false;
    vm.close = close;
    function close() {
      vm.confirm_disable = false;
      vm.html = "";
      vm.print_enable = false;
      vm.update = false;
      angular.copy(vm.empty_data, vm.model_data);
      $state.go('app.production.RaiseJO');
    }

    vm.add = add;
    function add() {
      vm.update = false;
      vm.title = "Raise Job Order";
      angular.copy(vm.empty_data, vm.model_data);
      $state.go('app.production.RaiseJO.RWO');
    }

    vm.title = "Update Job Order"

    vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

    vm.empty_data = {"title": "Raise Returnable Order", "data": [{"product_code": "", "sub_data": [{"material_code": "", "material_quantity": '', "id": ''}], "product_description":'', 'new_sku': true}], "jo_reference": ""}

    vm.model_data = {}
    angular.copy(vm.empty_data, vm.model_data)
    vm.update = true;

    vm.change_quantity = function (data) {
      console.log(data)
    }

    vm.update_data = function(data, index, last, first) {
      if (first && !(last)) {
        if (vm.update){vm.delete_jo(data.sub_data[index].id, data.product_code, first);}
        vm.remove_product(data);
      } else if (last) {
        if(data.sub_data[index]["material_code"]) {
          data.sub_data.push({"material_code": "", "material_quantity": '' ,'new_sku': true})
        }
      } else {
        if (vm.update &&  !(data.sub_data[index].new_sku)){vm.delete_jo(data.sub_data[index].id, "", first);}
        data.sub_data.splice(index,1);
      }
    }

    vm.delete_jo = function(id, wms_code, first) {
      var data = {'rem_id': id, 'wms_code': wms_code};
      if(first){ data["jo_reference"]=vm.model_data.jo_reference}
      vm.service.apiCall('delete_jo/', 'POST', data).then(function(data){
        if(data.message) {
          pop_msg(data.data);
        }
      });
    }

    vm.remove_product = function (data) {
      angular.forEach(vm.model_data.data, function(item){
        if (item.$$hashKey == data.$$hashKey) {
          angular.copy(vm.empty_data.data[0], item);
        } 
      });
    }

    vm.add_product = function () {
      var temp = {};
      angular.copy(vm.empty_data.data[0],temp);
      temp.sub_data[0]['new_sku'] = true;
      vm.model_data.data.push(temp);
    }

    vm.submit = function() {
      var elem = angular.element($('form'));
      elem = elem[1];
      elem = $(elem).serializeArray();
      vm.service.apiCall('save_rwo/', 'POST', elem).then(function(data){
        if(data.message) {
          pop_msg(data.data);
          if(data.data == "Added Successfully") {
            vm.confirm_disable = true;
            reloadData();
            vm.close();
          }
        }
      });
    }

    vm.html = "";
    vm.print_enable = false
    vm.confirm_disable = false
    vm.confirm_rwo = function() {
      var elem = angular.element($('form'));
      elem = elem[1];
      elem = $(elem).serializeArray();
      vm.service.apiCall('confirm_rwo/', 'POST', elem).then(function(data){
        if(data.message) {
          if(data.data.search("<div") != -1) {
            vm.html = $(data.data)[0];
            var html = $(vm.html).closest("form").clone();
            angular.element(".modal-body:visible").html($(html).find(".modal-body > .form-group"));
            vm.print_enable = true;
            vm.reloadData();
          } else {
            pop_msg(data.data)
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

    vm.get_product_data = function(item, sku_data) {

      check_exist(sku_data).then(function(data){
        if(data) {
          var elem = $.param({'sku_code': item});
          vm.service.apiCall('get_material_codes/', 'POST', {'sku_code': item}).then(function(data){
            if(data.message) {
              sku_data.sub_data = data.data;
            }
          });
        }
      });
    }

    service.apiCall("generate_rm_rwo_data/", "GET").then(function(data){

      if(data.message) {
        vm.empty_data["vendors"] = data.data.vendors;
      }
    })

  function check_exist(sku_data) {

    var d = $q.defer();
    for(var i = 0; i < vm.model_data.data.length; i++) {

      if(vm.model_data.data[i].$$hashKey != sku_data.$$hashKey && vm.model_data.data[i].product_code == sku_data.product_code) {

        d.resolve(false);
        vm.model_data.data.splice(vm.model_data.data.length-1, 1)
        alert("It is already exist in index");
        break;
      } else if( i+1 == vm.model_data.data.length) {
        d.resolve(true);
      }
    }
    return d.promise;
  }

    vm.print = print;
    function print() {
      vm.service.print_data(vm.html, 'Returnable Work Order');
    }
  }

