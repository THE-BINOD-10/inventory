'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('RaiseJOCtrl',['$scope', '$http', '$state', '$q', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $q, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service) {
    var vm = this;
    vm.service = Service;
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.vendor_produce = false;
    vm.units = vm.service.units;
    vm.button_status = false;

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

    vm.dtColumns = [
        DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
                if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                  vm.selected = {};
                }
                vm.selected[meta.row] = vm.selectAll;
                return vm.service.frontHtml + meta.row + vm.service.endHtml;
            }).notSortable(),
        DTColumnBuilder.newColumn('JO Reference').withTitle('JO Reference'),
        DTColumnBuilder.newColumn('Creation Date').withTitle('Creation Date'),
        DTColumnBuilder.newColumn('Order Type').withTitle('Order Type')
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

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td:not(td:first)', nRow).unbind('click');
        $('td:not(td:first)', nRow).bind('click', function() {
            $scope.$apply(function() {
                vm.service.apiCall('generated_jo_data/', 'GET', {data_id: aData.DT_RowAttr['data-id']}).then(function(data){
                  if(data.message) {
                    vm.title = "Update Job Order";
                    vm.update = true;
                    angular.copy(data.data, vm.model_data);
                    vm.vendor_produce = (aData["Order Type"] == "Vendor Produce") ? true: false;
                    $state.go('app.production.RaiseJO.JO');
                  }
                });
            });
        });
        return nRow;
    } 

    vm.close = close;
    function close() {
      vm.button_status = false;
      vm.print_enable = false;
      vm.vendor_produce = false;
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

      var qty = data.product_description;
      angular.forEach(data.data, function(material){
        var temp = Number(material.material_quantity) * Number(data.product_description);
        temp = String(temp);
        if(temp.indexOf("e") != -1) {
          temp = "0";
        } else {
          material.temp_qty = vm.service.decimal(temp, 1);
        }
      })
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
      vm.service.apiCall('delete_jo/', 'POST', data).then(function(data){
        if(data.message) {
          pop_msg(data.data);
        }
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

    vm.submit = function(data) {
     if(data.$valid) {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('save_jo/', 'POST', elem, true).then(function(data){
        if(data.message) {
          pop_msg(data.data);
          if(data.data == 'Added Successfully') {
            vm.close();
          }
        }
      });
     }
    }

    vm.html = "";
    vm.print_enable = false;
    vm.confirm_jo = function(data) {
     vm.button_status = true;
     if(data.$valid) {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('confirm_jo/', 'POST', elem, true).then(function(data){
        if(data.message) {
          vm.reloadData();
          if(data.data.search("<div") != -1) {
            vm.html = $(data.data)[0];
            var html = $(vm.html).closest("form").clone();
            angular.element(".modal-body").html($(html).find(".modal-body > .form-group"));
            vm.print_enable = true;
          } else {
            pop_msg(data.data)
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
      reloadData();
    }

  function check_exist(sku_data, index) {

    var d = $q.defer();
    for(var i = 0; i < vm.model_data.results.length; i++) {

      if(vm.model_data.results[i].$$hashKey != sku_data.$$hashKey && vm.model_data.results[i].product_code == sku_data.product_code) {

        d.resolve(false);
        vm.model_data.results.splice(index, 1);
        alert("It is already exist in index");
        break;
      } else if( i+1 == vm.model_data.results.length) {
        d.resolve(true);
      }
    }
    return d.promise;
  }

    vm.get_product_data = function(item, sku_data, index) {
      console.log(vm.model_data);
      check_exist(sku_data, index).then(function(data){
        if(data) {
          var elem = $.param({'sku_code': item});
          vm.service.apiCall('get_material_codes/','POST', {'sku_code': item}).then(function(data){
            if(data.message) {
              if(data.data != "No Data Found") {
                sku_data.data = data.data;
              } else {
                sku_data.data = [{"material_code": "", "material_quantity": '', "id": ''}];
              }
            }
          });
        }
      });
    }

    vm.print = print;
    function print() {
      vm.service.print_data(vm.html, 'Job Order');
    }

    vm.delete_jo_group = function() {
      vm.bt_disable = true;
      var that = vm;
      var data = [];
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]._aData;
          data.push({value:String(temp.DT_RowAttr['data-id']), name: temp["Order Type"]});
        }
      });
      vm.service.apiCall('delete_jo_group/', 'POST', data).then(function(data){
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
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]._aData;
          data.push({value:String(temp.DT_RowAttr['data-id']), name: temp["Order Type"]});
        }             
      });             
      vm.service.apiCall('confirm_jo_group/', 'POST', data).then(function(data){
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

