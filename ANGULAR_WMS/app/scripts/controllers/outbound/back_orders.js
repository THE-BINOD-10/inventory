'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('OutboundBackOrdersCtrl',['$scope', '$http', '$state', '$q', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'limitToFilter', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $q, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, limitToFilter, colFilters, Service) {
    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.filters = {'datatable': 'OutboundBackOrders', 'search0':'', 'search1':'', 'search2': ''}
    vm.selected = {};
    vm.selectAll = false;
    vm.toggleAll = toggleAll;
    vm.toggleOne = toggleOne;
    var titleHtml = '<input type="checkbox" class="data-select" ng-model="showCase.selectAll" ng-change="showCase.toggleAll(showCase.selectAll, showCase.selected); $event.stopPropagation();">';

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

    if(Session.roles.permissions["production_switch"]) {

      vm.dtColumns = [
        DTColumnBuilder.newColumn(null).withTitle(titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
                vm.selected[meta.row] = false;
                vm.selectedRows[meta.row] = full;
                return '<input class="data-select" type="checkbox" ng-model="showCase.selected[' + meta.row + ']" ng-change="showCase.toggleOne(showCase.selected)">';
            }).notSortable(),
        DTColumnBuilder.newColumn('WMS Code').withTitle('WMS Code'),
        DTColumnBuilder.newColumn('Ordered Quantity').withTitle('Ordered Quantity'),
        DTColumnBuilder.newColumn('Stock Quantity').withTitle('Stock Quantity'),
        DTColumnBuilder.newColumn('Transit Quantity').withTitle('Transit Quantity'),
        DTColumnBuilder.newColumn('In Production Quantity').withTitle('In Production Quantity'),
        DTColumnBuilder.newColumn('Procurement Quantity').withTitle('Procurement Quantity')
      ];
    } else {

      vm.dtColumns = [
        DTColumnBuilder.newColumn(null).withTitle(titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
                vm.selected[meta.row] = false;
                vm.selectedRows[meta.row] = full;
                return '<input class="data-select" type="checkbox" ng-model="showCase.selected[' + meta.row + ']" ng-change="showCase.toggleOne(showCase.selected)">';
            }).notSortable(),
        DTColumnBuilder.newColumn('WMS Code').withTitle('WMS Code'),
        DTColumnBuilder.newColumn('Ordered Quantity').withTitle('Ordered Quantity'),
        DTColumnBuilder.newColumn('Stock Quantity').withTitle('Stock Quantity'),
        DTColumnBuilder.newColumn('Transit Quantity').withTitle('Transit Quantity'),
        DTColumnBuilder.newColumn('Procurement Quantity').withTitle('Procurement Quantity')
      ]; 
    }

    vm.selectedRows = {};
    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.bt_disable = true;
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
          vm.bt_disable = false
          enable = false
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
                });
            });
        return nRow;
    }

    vm.model_data = {};

    vm.close = close;
    function close() {

      vm.print_enable = false;
      vm.message = "";
      vm.model_data = {};
      $state.go("app.outbound.BackOrders");
    }

    vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

    vm.update_data = function(data, index, last, first) {
      console.log(data, index, last);
      if (first && !(last)) {
        vm.remove_product(data);
      } else if (last) {
        data.sub_data.push({"material_code": "", "material_quantity": '' ,'new_sku': true})
      } else {
        data.sub_data.splice(index,1);
      }
    }

    vm.remove_product = function (data) {
      angular.forEach(vm.model_data.data, function(item, index){
        if (item.$$hashKey == data.$$hashKey) {
          vm.model_data.data.splice(index,1);
        } 
      });
    }

    vm.confirm_disable = false;
    vm.confirm_po = confirm_po;
    function confirm_po() {
      var elem = $(form).serializeArray();

      Service.apiCall("confirm_back_order/", "POST", elem, true).then(function(data){
        if(data.message) {
          vm.confirm_disable = true; vm.message = data.data; reloadData();
          if(data.data.search("<div") != -1) {
                vm.html = $(data.data)[0];
                var html = $(vm.html).closest("form").clone();
                angular.element(".modal-body").html($(html));
                vm.print_enable = true;
           } else {
             vm.service.pop_msg(data.data);
           }
        };
      });
    }

    vm.process = false;
    vm.backorder_po = function() {
      var data = {};
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.selectedRows[parseInt(key)];
          data[temp['WMS Code']+":"+$(temp[""]).attr("name")] = temp['Procurement Quantity'];
        }
      });
      vm.process = true
      Service.apiCall("generate_po_data/", "POST", data).then(function(data){
        if(data.message) { 

          angular.copy(data.data, vm.model_data)
          $state.go("app.outbound.BackOrders.PO");
        };
        vm.process = false;
      });
    }

    vm.backorder_jo = function() {
      var data = {};
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.selectedRows[parseInt(key)];
          data[temp['WMS Code']+":"+$(temp[""]).attr("name")] = temp['Procurement Quantity'];
        }
      });
      vm.process = true;
      Service.apiCall("generate_jo_data/", "POST", data).then(function(data){
        if(data.message) {

          angular.copy(data.data, vm.model_data);
          angular.forEach(vm.model_data.data, function(temp){
            if(temp.sub_data.length == 0) {
              temp["sub_data"] = [{material_code: "", material_quantity: ""}];
            }
          });
          $state.go("app.outbound.BackOrders.JO");
          vm.process = false;
        };
      });
    }

    vm.create_stock_transfer = function() {
        var data = [];
        for(var key in vm.selected){
            if(vm.selected[key]) {
                var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]._aData;
                data.push({wms_code: temp['WMS Code'], order_quantity: temp['Ordered Quantity'], price: 0})
            }
        }
        Service.stock_transfer = JSON.stringify(data);
        if(data) {
          $state.go('app.outbound.BackOrders.ST');
          vm.reloadData();
        }
   }

    function pop_msg(msg){
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 2000);
    }

    vm.get_product_data = function(item, sku_data) {
      console.log(vm.model_data);
      check_exist(sku_data).then(function(data){
        if(data) {
          var elem = $.param({'sku_code': item});;
          $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
          $http({
               method: 'POST',
               url:Session.url+"get_material_codes/",
               withCredential: true,
               data: elem}).success(function(data, status, headers, config) {
                 sku_data.sub_data = data;
            console.log("success");
          });
        }
      });
    }

    vm.add_product = function () {
      var temp = {};
      angular.copy(vm.empty_data.data[0],temp);
      temp.sub_data[0]['new_sku'] = true;
      vm.model_data.data.push(temp);
    }

    vm.empty_data = {"title": "Update Job Order", "data": [{"product_code": "", "sub_data": [{"material_code": "", "material_quantity": '', "id": ''}], "product_description":'', 'new_sku': true}], "jo_reference": ""}

  function check_exist(sku_data) {

    var d = $q.defer();
    for(var i = 0; i < vm.model_data.data.length; i++) {

      if(vm.model_data.data[i].$$hashKey != sku_data.$$hashKey && vm.model_data.data[i].product_code == sku_data.product_code) {

        d.resolve(false);
        vm.model_data.data.splice(i+1, 1)
        alert("It is already exist in index");
        break;
      } else if( i+1 == vm.model_data.data.length) {
        d.resolve(true);
      }
    }
    return d.promise;
  }

  vm.html = ""
  vm.print_enable = false;
  vm.confirm_jo = function() {
      var elem = angular.element($('form:visible'));
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
              angular.element(".modal-body:visible").html($(html).find(".modal-body > .form-group"));
              vm.print_enable = true;
            } else {
              pop_msg(data)
            }
      });
    }

    vm.print = print;
    function print() {
      colFilters.print_data(vm.html);
    }

  vm.print_grn = function() {

    vm.service.print_data(vm.html, "Purchase Order");
  }

  }

