'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('ProductionBackOrdersCtrl',['$scope', '$http', '$state', '$q', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'limitToFilter', 'colFilters', 'Service', 'Data', '$modal', '$log', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $q, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, limitToFilter, colFilters, Service, Data, $modal, $log) {
    var vm = this;
    vm.g_data = Data.back_orders_list;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.units = vm.service.units;
    //vm.filters = {'datatable': 'ProductionBackOrders', 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': '', 'special_key':'Self Produce'}
    vm.disable_save = true;
    vm.selected = {};
    vm.selectAll = false;
    vm.toggleAll = toggleAll;
    vm.toggleOne = toggleOne;
    var titleHtml = '<input type="checkbox" class="data-select" ng-model="showCase.selectAll" ng-change="showCase.toggleAll(showCase.selectAll, showCase.selected); $event.stopPropagation();">';

    vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': vm.g_data.view, 'search0':'', 'search1':'', 'search2': '', 'search3': '', 'search4': '', 'special_key':'Self Produce'},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('drawCallback', function(settings) {
         vm.service.make_selected(settings, vm.selected);
       })
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

     vm.dtColumns = vm.service.build_colums(vm.g_data.tb_headers[vm.g_data.view]);
     vm.dtColumns.splice(0,0,
        DTColumnBuilder.newColumn(null).withTitle(titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
                if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                  vm.selected = {};
                 }
                vm.selected[meta.row] = vm.selectAll;
                vm.selectedRows[meta.row] = full;
                return '<input class="data-select" type="checkbox" ng-model="showCase.selected[' + meta.row + ']" ng-change="showCase.toggleOne(showCase.selected)">';
            }).notSortable()
       )

    vm.selectedRows = {};
    vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
        vm.bt_disable = false;
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

      vm.confirm_disable = false;
      vm.print_enable = false;
      vm.message = "";
      vm.model_data = {};
      reloadData();
      $state.go("app.production.BackOrders");
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
        if(data.sub_data[index].material_code) {
          data.sub_data.push({"material_code": "", "material_quantity": '' ,'new_sku': true})
        }
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
        if(data.message) {vm.confirm_disable = true; vm.message = data.data; reloadData();

          if(data.data.search("<div") != -1) {
                vm.html = $(data.data)[0];
                var html = $(vm.html).closest("form").clone();
                angular.element(".modal-body").html($(html));
                //angular.element(".modal-body").html($(html).find(".modal-body > .form-group"));
                //angular.element(".modal-body").html($(html));
                vm.print_enable = true;
           } else {
             vm.service.pop_msg(data.data);
           }
        };
      });
    }

    vm.backorder_po = function() {
      var data = {};
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.selectedRows[parseInt(key)];
          data[temp['WMS Code']+":"+$(temp[""]).attr("name")+":"+temp['order_id']]  = temp['Procurement Quantity'];
          //data[temp['WMS Code']+":"+"Order_det"] = temp['order_id'];
        }
      });
      vm.bt_disable = true;
      var send_data  = {data: data, filter: vm.filter}
      var modalInstance = $modal.open({
      templateUrl: 'views/outbound/toggle/common_backorder_po.html',
      controller: 'BackorderPOPOP',
      controllerAs: 'pop',
      size: 'lg',
      backdrop: 'static',
      keyboard: false,
      windowClass: 'full-modal',
      resolve: {
        items: function () {
          return send_data;
        }
      }
      });

      modalInstance.result.then(function (selectedItem) {
        var data = selectedItem;
        reloadData();
      }, function () {
        $log.info('Modal dismissed at: ' + new Date());
      });
    }


    vm.backorder_rwo = function() { var data = {};
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.selectedRows[parseInt(key)];
          data[temp['WMS Code']+":"+$(temp[""]).attr("name")] = temp['Procurement Quantity'];
        }
      });
      vm.bt_disable = true;
      Service.apiCall("generate_rm_rwo_data/", "POST", data, true).then(function(data){
        if(data.message) {

          angular.copy(data.data, vm.model_data);
          angular.forEach(vm.model_data.data, function(temp){
            temp["sub_data"] = [{material_code: "", material_quantity: ""}]
          });
          $state.go("app.production.BackOrders.RWO");
        };
      });
    }

    function pop_msg(msg){
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 2000);
    }

    vm.get_product_data = function(item, sku_data, index) {
      check_exist(sku_data).then(function(data){
        if(data) {
          var elem = $.param({'sku_code': item});;
          $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
          $http({
               method: 'POST',
               url:Session.url+"get_material_codes/",
               withCredential: true,
               data: elem}).success(function(data, status, headers, config) {
                 sku_data.sub_data = data.materials;
                 sku_data.product_description = 1;
                 sku_data.description = data.product.description;
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

    vm.empty_data = {"title": "Raise Returnable Order", "data": [{"product_code": "", "sub_data": [{"material_code": "", "material_quantity": '', "id": ''}], "product_description":'', 'new_sku': true}], "vendor_name": ""}

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
  vm.confirm_rwo = function() {
      var elem = angular.element($('form:visible'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall("confirm_rwo/", "POST", elem, true).then(function(data){
      //elem = $.param(elem);
      //$http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      //$http({  
       //        method: 'POST',
       //        url:Session.url+"confirm_rwo/",
       //        withCredential: true,
       //        data: elem}).success(function(data, status, headers, config) {
       if(data.message){
            vm.reloadData();
            if(data.data.search("<div") != -1) {
              vm.html = $(data.data)[0];
              var html = $(vm.html).closest("form").clone();
              angular.element(".modal-body:visible").html($(html).find(".modal-body > .form-group"));
              vm.print_enable = true;
            } else {
              pop_msg(data.data)
            }
       }
      });
    }

    vm.print = print;
    function print() {
      colFilters.print_data(vm.html);
    }

    vm.order_types = [];
    vm.service.apiCall("get_vendor_types/").then(function(data) {
      if(data.message) {
        vm.order_types = data.data.data;
      }
    });

    vm.change_special_key = function(data) {

      //vm.filter = data;
      vm.dtInstance.DataTable.context[0].ajax.data['special_key'] = data;
      vm.reloadData();
    }

    vm.change_datatable = function() {
      Data.back_orders_list.view = (vm.g_data.toggle_switch)? 'ProductionBackOrdersAlt': 'ProductionBackOrders';
      $state.go($state.current, {}, {reload: true});
    }

    vm.print_grn = function() {

      vm.service.print_data(vm.html, "Purchase Order");
    }
  }

