'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('RawMaterialPicklistCtrl',['$scope', '$http', '$state', '$timeout', 'Session', 'printer', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $timeout, Session , printer, DTOptionsBuilder, DTColumnBuilder, colFilters) {
    var vm = this;
    vm.permissions = Session.roles.permissions;
    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'RawMaterialPicklist'},
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
        DTColumnBuilder.newColumn('Job Code').withTitle('Job Code'),
        DTColumnBuilder.newColumn('Creation Date').withTitle('Creation Date')
    ];

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        // Unbind first in order to avoid any duplicate handler (see https://github.com/l-lin/angular-datatables/issues/87)
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
              var elem = $.param({'data_id': aData.DT_RowAttr['data-id']});;
              $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
              $http({
               method: 'POST',
               url:Session.url+"view_confirmed_jo/",
               withCredential: true,
               data: elem}).success(function(data, status, headers, config) {
                console.log(data) ;
                angular.copy(data, vm.model_data);
                $state.go('app.production.RMPicklist.ConfirmedJO');
              });
            });
        });
        return nRow;
    } 

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        $('.custom-table').DataTable().draw();
    };

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    vm.close = close;
    function close() {

      vm.print_enable = false;
      vm.disable_generate = false;
      $state.go('app.production.RMPicklist');
    }

   vm.empty_data = {"title": "Update Job Order", "results": [{"product_code": "", "data": [{"material_code": "", "material_quantity": '', "id": ''}], "product_description":'', 'new_sku': true}], "jo_reference": ""}

    vm.model_data = {}
    angular.copy(vm.empty_data, vm.model_data)
    vm.update = true; 

    vm.print = print;
    function print() {
      printer.print('/views/production/print/view_raw_picklist.html' ,{'data': 'data'});
    }

    vm.disable_generate = false;
    vm.generate = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      elem = $.param(elem);
              $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
              $http({
               method: 'POST',
               url:Session.url+"jo_generate_picklist/",
               withCredential: true,
               data: elem}).success(function(data, status, headers, config) {
              if(data == "Success") { vm.disable_generate = true; }
              pop_msg(data);
              reloadData();
              });
    }

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 2000);
    } 
  }

