'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('RaisePurchaseOrderCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, Service) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.selected = {};
    vm.selectAll = false;

    vm.filters = {'datatable': 'RaisePO', 'search0':'', 'search1':'', 'search2': '', 'search3': ''}
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
       .withOption('rowCallback', rowCallback)
       .withOption('initComplete', function( settings ) {
         vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
       });

    var columns = ["Supplier ID", "Supplier Name", "Total Quantity", "Order Type"];
    vm.dtColumns = vm.service.build_colums(columns);
    vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
                .renderWith(function(data, type, full, meta) {
                  if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                    vm.selected = {};
                  }
                  vm.selected[meta.row] = vm.selectAll;
                  return vm.service.frontHtml + meta.row + vm.service.endHtml;
                }))

    vm.dtInstance = {};

    $scope.$on('change_filters_data', function(){
      if($("#"+vm.dtInstance.id+":visible").length != 0) {
        vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
        vm.service.refresh(vm.dtInstance);
      }
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td:not(td:first)', nRow).unbind('click');
        $('td:not(td:first)', nRow).bind('click', function() {
            $scope.$apply(function() {
                var data = {supplier_id: aData['Supplier ID'], order_type: aData['Order Type']};
                vm.service.apiCall('generated_po_data/', 'GET', data).then(function(data){
                  if (data.message) {
                    angular.copy(data.data, vm.model_data);
                    vm.model_data.suppliers = [vm.model_data.supplier_id];
                    vm.model_data.supplier_id = vm.model_data.suppliers[0];
                    vm.vendor_receipt = (vm.model_data["Order Type"] == "Vendor Receipt")? true: false;
                    vm.title = 'Update PO';
                    vm.update = true;
                    $state.go('app.inbound.RaisePo.PurchaseOrder');
                  }
                });
            });
        });
        return nRow;
    }

    vm.update = false;
    vm.title = 'Raise PO';
    vm.bt_disable = true;
    vm.vendor_receipt = false;

    var empty_data = {"supplier_id":"",
                      "po_name": "",
                      "ship_to": "",
                      "data": [
                        {'fields':{"supplier_Code":"", "order_quantity":"", 'price':'','sku': {"price":"", 'wms_code': ""}}}
                      ]
                     };

    vm.model_data = {};
    angular.copy(empty_data, vm.model_data);

    vm.close = function () {

      vm.base();
      $state.go('app.inbound.RaisePo');
    }

    vm.base = function() {
      
      vm.title = "Raise PO";
      vm.vendor_produce = false;
      vm.confirm_print = false;
      vm.update = false;
      vm.print_enable = false;
      vm.vendor_receipt = false;
      angular.copy(empty_data, vm.model_data);
    }
    vm.base();

    vm.add = function () {

      $state.go('app.inbound.RaisePo.PurchaseOrder');
    }
 
    vm.update_data = function (index) {

      if (index == vm.model_data.data.length-1) {
        if (vm.model_data.data[index]["fields"]["sku"]["wms_code"] && vm.model_data.data[index]["fields"]["order_quantity"]) {
          vm.model_data.data.push({"wms_code":"", "supplier_code":"", "order_quantity":"", "price":""});
        }
      } else {
        vm.delete_data(vm.model_data.data[index].pk);
        vm.model_data.data.splice(index,1);
      }
    }

    vm.check_sku_list = function(key, val, index) {

      for (var i=0;i < vm.model_data.data.length; i++) {
        if(vm.model_data.data[i].$$hashKey != key && val == vm.model_data.data[i].fields.sku.wms_code) {
          alert("This sku already exist in index");
          vm.model_data.data.splice(index,1);
        }
      }
    }

    vm.delete_data = function(id) {
      if(id) {
        vm.service.apiCall('delete_po/', 'GET', {id: id}).then(function(data){
          if(data.message) {
            pop_msg(data.data);
          }
        });
      }
    }

    vm.save_raise_po = function(data) {

      if (data.$valid) {
        if(vm.update) {
          vm.update_raise_po();
        } else {
          vm.add_raise_po();
        }
      }
    }

    vm.update_raise_po = function() {
      
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('validate_wms/', 'GET', elem).then(function(data){
        if(data.message){
          if(data.data == 'success') {
            vm.service.apiCall('modify_po_update/', 'GET', elem).then(function(data){
              if(data.message){
                if(data.data == 'Updated Successfully') {
                  vm.close();
                  vm.service.refresh(vm.dtInstance);
                } else {
                  pop_msg(data.data);
                }
              }
            })
          } else {
            pop_msg(data.data);
          }
        }
      });
    }

    vm.confirm = function(data) {
      if (data.$valid) {
        if(!(vm.update)) {
          vm.confirm_add_po();
        } else {
          vm.confirm_po();
        }
      }
    }

    vm.confirm_add_po = function() {

      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.common_confirm('confirm_add_po/', elem);
    }

    vm.confirm_po = function() {

      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.common_confirm('confirm_po/', elem);
    }

    vm.common_confirm = function(url, elem) {

      vm.service.apiCall('validate_wms/', 'GET', elem).then(function(data){
        if(data.message) {
          if (data.data == "success") {
            vm.raise_po(url, elem);
          } else{
            pop_msg(data.data);
          }
        }
      });
    }

    vm.raise_po = function(url, elem) {

      vm.service.alert_msg("Do want to Raise PO").then(function(msg) {
        if (msg == "true") {
          vm.service.apiCall(url, 'GET', elem).then(function(data){
            if(data.message) {
              pop_msg(data.data);
              vm.service.refresh(vm.dtInstance);
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
      });
    }

    vm.confirm_print = false;
    vm.confirm_po1 = function() {

      vm.bt_disable = true;
      var that = vm;
      var data = [];
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)];
          data.push({name: temp['_aData']["Order Type"], value :temp['_aData']['Supplier ID']});
        }
      });
      vm.service.alert_msg("Do want to Raise PO").then(function(msg) {
        if (msg == "true") {
          vm.service.apiCall('confirm_po1/', 'GET', data).then(function(data){
            if(data.message) {
              vm.confirm_print = true;
              vm.print_enable = true;
              $state.go('app.inbound.RaisePo.PurchaseOrder');
              vm.bt_disable = true;
              vm.service.refresh(vm.dtInstance);
              if(data.data.search("<div") != -1) {
                vm.html = $(data.data)[0];
                $timeout(function() {
                  var html = $(vm.html).closest("form").clone();
                  angular.element(".modal-body").html($(html).find(".modal-body > .form-group"));
                  vm.confirm_print = false;
                }, 1000);
              }
            }
          });
        }
      });
    }

   vm.delete_po_group = delete_po_group;
   function delete_po_group() {
      vm.bt_disable = true;
      var that = vm;
      var data = [];
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)];
          data.push({name: temp['_aData']["Order Type"], value:temp['_aData']['Supplier ID']});
        }
      });
      vm.service.apiCall('delete_po_group/', 'GET', data).then(function(data){
        if(data.message) {
           vm.bt_disable = true;
           vm.selectAll = false;
           vm.service.refresh(vm.dtInstance);
        }
      });
   }

    vm.get_sku_details = function(product, item) {
      product.fields.sku.wms_code = item.wms_code;
      if (typeof(vm.model_data.supplier_id) == "undefined" || vm.model_data.supplier_id.length == 0){
        return false;
      } else {
        var supplier = vm.model_data.supplier_id;
        $http.get(Session.url+'get_mapping_values/?wms_code='+product.fields.sku.wms_code+'&supplier_id='+supplier, {withCredentials : true}).success(function(data, status, headers, config) {
          product.fields.price = data.price;
          product.fields.supplier_code = data.supplier_code;
        });
      }
    }

    vm.add_raise_po = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('validate_wms/', 'GET', elem).then(function(data){
        if(data.message){
          if(data.data == 'success') {
            vm.service.apiCall('add_po/', 'GET', elem).then(function(data){
              if(data.message){
                if(data.data == 'Added Successfully') {
                  vm.close();
                  vm.service.refresh(vm.dtInstance);
                } else {
                  pop_msg(data.data);
                }
              }
            })
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

    vm.html = "";
    vm.print_enable = false;
  
    vm.print_grn = function() {

      vm.service.print_data(vm.html, "Purchase Order");
    }
  }

