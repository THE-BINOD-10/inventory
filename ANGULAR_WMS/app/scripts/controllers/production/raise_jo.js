'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('RaiseJOCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.selected = {};
    vm.selectAll = false;
    vm.toggleAll = toggleAll;
    vm.toggleOne = toggleOne;
    var titleHtml = '<input type="checkbox" class="data-select" ng-model="showCase.selectAll" ng-change="showCase.toggleAll(showCase.selectAll, showCase.selected); $event.stopPropagation();">';

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'RaiseJobOrder'},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('processing', true)
       .withOption('serverSide', true)
       .withOption('createdRow', function(row, data, dataIndex) {
            $compile(angular.element(row).contents())($scope);
        })
        .withOption('headerCallback', function(header) {
            if (!vm.headerCompiled) {
                vm.headerCompiled = true;
                $compile(angular.element(header).contents())($scope);
            }
        })
       .withPaginationType('full_numbers')
       .withOption('rowCallback', rowCallback);

    vm.dtColumns = [
        DTColumnBuilder.newColumn(null).withTitle(titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
                vm.selected[full.id] = false;
                return '<input class="data-select" type="checkbox" ng-model="showCase.selected[' + data.id + ']" ng-change="showCase.toggleOne(showCase.selected);$event.stopPropagation();">';
            }).notSortable(),
        DTColumnBuilder.newColumn('JO Reference').withTitle('JO Reference'),
        DTColumnBuilder.newColumn('Creation Date').withTitle('Creation Date')
    ];

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

    function toggleAll (selectAll, selectedItems, event) {
        for (var id in selectedItems) {
            if (selectedItems.hasOwnProperty(id)) {
                selectedItems[id] = selectAll;
            }
        }
        vm.button_fun();
    }
    function toggleOne (selectedItems) {
        for (var id in selectedItems) {
            if (selectedItems.hasOwnProperty(id)) {
                if(!selectedItems[id]) {
                    vm.selectAll = false;
                    vm.button_fun();
                    return;
                }
            }
        }
        vm.selectAll = true;
        vm.button_fun();
    }

    vm.bt_disable = true;
    vm.button_fun = function() {

      var enable = true
      for (var id in vm.selected) {
        if(vm.selected[id]) {
          vm.bt_disable = false;
          enable = false;
          break;
        }
      }  
      if (enable) {
        vm.bt_disable = true;
      }
    }

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        // Unbind first in order to avoid any duplicate handler (see https://github.com/l-lin/angular-datatables/issues/87)
        $('td:not(td:first)', nRow).unbind('click');
        $('td:not(td:first)', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
                $http.get(Session.url+'generated_jo_data/?data_id='+aData.DT_RowAttr['data-id'], {withCredential: true}).success(function(data, status, headers, config) {
                  console.log(data);
                  vm.title = "Update Job Order";
                  vm.update = true;
                  angular.copy(data, vm.model_data);
                  $state.go('app.production.RaiseJO.JO');
                });
            });
        });
        return nRow;
    } 

    vm.close = close;
    function close() {
      vm.print_enable = false;
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

    vm.update_data = function(data, index, last, first) {
      console.log(data, index, last);
      if (first && !(last)) {
        if (vm.update){vm.delete_jo(data.data[index].id, data.product_code, first);}
        vm.remove_product(data);
      } else if (last) {
        data.data.push({"material_code": "", "material_quantity": '' ,'new_sku': true})
      } else {
        if (vm.update){vm.delete_jo(data.data[index].id, "", first);}
        data.data.splice(index,1);
      }
    }

    vm.delete_jo = function(id, wms_code, first) {
      var data = {'rem_id': id, 'wms_code': wms_code}
      if(first){ data["jo_reference"]=vm.model_data.jo_reference }
      var elem = $.param(data); 
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

    vm.remove_product = function (data) {
      angular.forEach(vm.model_data.results, function(item){
        if (item.$$hashKey == data.$$hashKey) {
          angular.copy(vm.empty_data.results[0], item);
        } 
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

    vm.html = "";
    vm.print_enable = false;
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

            vm.reloadData();
            if(data.search("<div") != -1) {
              vm.html = $(data)[0];
              var html = $(vm.html).closest("form").clone();
              angular.element(".modal-body").html($(html).find(".modal-body > .form-group"));
              vm.print_enable = true;
            } else {
              pop_msg(data)
            }
      });
    }

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 2000);
      reloadData();
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

    vm.print = print;
    function print() {
      colFilters.print_data(vm.html);
    }

    vm.delete_jo_group = function() {
      vm.bt_disable = true;
      var that = vm;
      var data = [];
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          data.push({value:String(vm.dtInstance.DataTable.context[0].aoData[parseInt(key)-1]._aData.DT_RowAttr['data-id']), name: 'id'});
        }
      });
      Service.apiCall('delete_jo_group/', 'POST', data).then(function(data){
        vm.bt_disable = true;
        vm.reloadData()
      })
    }

    vm.confirm_print = false;
    vm.confirm_jo_group = function() {
      vm.bt_disable = true;
      var that = vm;  
      var data = [];  
      angular.forEach(vm.selected, function(value, key) {
        if(value) {   
          data.push({value:String(vm.dtInstance.DataTable.context[0].aoData[parseInt(key)-1]._aData.DT_RowAttr['data-id']), name: 'id'});
        }             
      });             
      Service.apiCall('confirm_jo_group/', 'POST', data).then(function(data){
        vm.bt_disable = true;
        vm.reloadData();
        if (data.message) {
            data = data.data;
            vm.confirm_print = true;
            vm.print_enable = true;
            $state.go('app.production.RaiseJO.JO');
            vm.bt_disable = true;
            vm.reloadData();
            if(data.search("<div") != -1) {
              vm.html = $(data)[0];
              $timeout(function() {
                var html = $(vm.html).closest("form").clone();
                $(html).find(".modal-footer").remove();
                angular.element(".modal-body").html($(html).find(".modal-body > .form-group"));
                vm.html = $(vm.html).clone();
                vm.confirm_print = false;
              }, 1000);
            }
        }
      })              
    }
  }

