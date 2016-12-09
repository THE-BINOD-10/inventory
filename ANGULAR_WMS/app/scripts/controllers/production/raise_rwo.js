'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('RaiseRWOCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters) {
    var vm = this;

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
        // Unbind first in order to avoid any duplicate handler (see https://github.com/l-lin/angular-datatables/issues/87)
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
                $http.get(Session.url+'generated_jo_data/?data_id='+aData.DT_RowAttr['data-id'], {withCredential: true}).success(function(data, status, headers, config) {
                  console.log(data) ;
                  angular.copy(data, vm.model_data);
                  $state.go('app.production.RaiseJO.JO');
                });
            });
        });
        return nRow;
    } 

    vm.close = close;
    function close() {
      $state.go('app.production.RaiseJO');
    }

    vm.add = add;
    function add() {
      vm.update = false;
      vm.title = "Raise Job Order";
      angular.copy(vm.empty_data, vm.model_data);
      $state.go('app.production.RaiseJO.JO');
    }

    vm.title = "Update Job Order"

    vm.print = function() {
      $state.go('app.production.RaiseJO.JobOrderPrint');
    }

    vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

    vm.empty_data = {"title": "Update Job Order", "results": [{"product_code": "", "data": [{"material_code": "", "material_quantity": '', "id": ''}], "product_description":'', 'new_sku': true}], "jo_reference": ""}

    vm.model_data = {}
    angular.copy(vm.empty_data, vm.model_data)
    vm.update = true;

    vm.change_quantity = function (data) {
      console.log(data)
    }

    vm.update_data = function(data, index, last) {
      console.log(data, index, last);
      if (last) {
        data.data.push({"material_code": "", "material_quantity": '' ,'new_sku': true})
      } else {
        vm.delete_jo(data.data[index].id, data.product_code);
        data.data.splice(index,1);
      }
    }

    vm.delete_jo = function(id, wms_code) {
      var elem = $.param({'rem_id': id, 'wms_code': wms_code}); 
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      $http({
               method: 'POST',
               url:Session.url+"delete_jo/",
               withCredential: true,
               data: elem}).success(function(data, status, headers, config) {
        pop_msg(data);
        console.log("success");
      });
    }

    vm.add_product = function () {
      var temp = {};
      angular.copy(vm.empty_data.results[0],temp);
      temp.data[0]['new_sku'] = true;
      vm.model_data.results.push(temp);
    }

    vm.submit = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      elem = $.param(elem);
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      $http({
               method: 'POST',
               url:Session.url+"save_jo/",
               withCredential: true,
               data: elem}).success(function(data, status, headers, config) {
        pop_msg(data);
        console.log("success");
      });
    }

    vm.confirm_jo = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      elem = $.param(elem);
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      $http({  
               method: 'POST',
               url:Session.url+"confirm_jo/",
               withCredential: true,
               data: elem}).success(function(data, status, headers, config) {
        pop_msg(data);
        console.log("success");
      });
    }
    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 2000);
    }

    vm.get_product_data = function(item, sku_data) {
      var elem = $.param({'sku_code': item});;
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      $http({
               method: 'POST',
               url:Session.url+"get_material_codes/",
               withCredential: true,
               data: elem}).success(function(data, status, headers, config) {
                 sku_data.data = data;
            console.log("success");
      });      
    }
  }

