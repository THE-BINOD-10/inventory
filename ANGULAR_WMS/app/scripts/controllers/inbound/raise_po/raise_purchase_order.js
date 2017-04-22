'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('RaisePurchaseOrderCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, Service) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;

    vm.selected = {};
    vm.selectAll = false;

    vm.update_part = true;

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
         $scope.$apply(function() {vm.bt_disable = true;vm.selectAll = false;});
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
                  vm.selected[meta.row] = false;
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
          vm.supplier_id = aData['Supplier ID'];
          var data = {supplier_id: aData['Supplier ID'], order_type: aData['Order Type']};
          vm.service.apiCall('generated_po_data/', 'GET', data).then(function(data){
            if (data.message) {
              //angular.copy(data.data, vm.model_data);
              var receipt_types = ['Buy & Sell', 'Purchase Order'];
              vm.update_part = false;
              var empty_data = {"supplier_id":vm.supplier_id,
                      "po_name": "",
                      "ship_to": "",
                      "receipt_type": receipt_types[data.data.receipt_type],
                      "seller_types": [],
                      "total_price": 0,
                      "tax": "",
                      "sub_total": "",
                      "data": data.data.data,
              };
              vm.model_data = {};
              angular.copy(empty_data, vm.model_data);

              angular.forEach(vm.model_data.data, function(one_row){
               vm.model_data.total_price = vm.model_data.total_price + (one_row.fields.order_quantity * one_row.fields.price);
              });

              vm.model_data.sub_total = ((vm.model_data.total_price / 100) * vm.model_data.tax) + vm.model_data.total_price;

              vm.get_total = function(price, index) {
                vm.model_data.data[index].fields.row_price = Number(vm.model_data.data[index].fields.order_quantity) * Number(vm.model_data.data[index].fields.price);
                vm.model_data.total_price = 0;

                angular.forEach(vm.model_data.data, function(one_row){
                  vm.model_data.total_price = Number(vm.model_data.total_price) + (Number(one_row.fields.order_quantity) * Number(one_row.fields.price));
                });
                vm.model_data.sub_total = ((vm.model_data.total_price / 100) * vm.model_data.tax) + vm.model_data.total_price;
              }

              vm.service.apiCall('get_sellers_list/', 'GET').then(function(data){
                if (data.message) {
                  var seller_data = data.data.sellers;
                  vm.model_data.tax = data.data.tax;

                  angular.forEach(seller_data, function(seller_single){
                    vm.model_data.seller_types.push(seller_single.id + ':' + seller_single.name);
                  });

                  vm.default_status = (Session.user_profile.user_type == 'marketplace_user')? true : false;

                  vm.seller_change = function(type) {

                    vm.selected_seller = type;
                    vm.default_status = false;
                    vm.model_data.data[vm.model_data.data.length - 1].fields.dedicated_seller = vm.selected_seller;
                  }
                }
              });

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
                      "receipt_types": ['Buy & Sell', 'Purchase Order'],
                      "seller_types": [],
                      "total_price": 0,
                      "tax": "",
                      "sub_total": "",
                      "data": [
                        {'fields':{"supplier_Code":"", "ean_number":"", "order_quantity":"", 'price':'', "measurement_unit":"", 
                                   "dedicated_seller": "", "row_price": 0, 'sku': {"price":"", 'wms_code': ""}}}
                      ]
                     };

    vm.model_data = {};
    angular.copy(empty_data, vm.model_data);

    vm.close = function () {

      vm.base();
      $state.go('app.inbound.RaisePo');
    }

    vm.b_close = vm.close;
    /*vm.b_close = function () {
      $state.go('app.inbound.RaisePo.PurchaseOrder');
    }*/

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

      vm.service.apiCall('get_sellers_list/', 'GET').then(function(data){
        if (data.message) {
          var seller_data = data.data.sellers;
          vm.model_data.tax = data.data.tax;

          angular.forEach(seller_data, function(seller_single){
              vm.model_data.seller_types.push(seller_single.id + ':' + seller_single.name);
          });

          vm.default_status = (Session.user_profile.user_type == 'marketplace_user') ? true: false;

          vm.seller_change = function(type) {

            vm.selected_seller = type;
            vm.default_status = false;
            vm.model_data.data[vm.model_data.data.length - 1].fields.dedicated_seller = vm.selected_seller;
          }

          $state.go('app.inbound.RaisePo.PurchaseOrder');
        }

      });

    }
    vm.get_total = function(price, index) {
      vm.model_data.data[index].fields.row_price = (Number(vm.model_data.data[index].fields.order_quantity) * Number(vm.model_data.data[index].fields.price));
      vm.model_data.total_price = 0;

      angular.forEach(vm.model_data.data, function(one_row){
        vm.model_data.total_price = vm.model_data.total_price + Number(one_row.fields.row_price);
      });

      vm.model_data.sub_total = ((vm.model_data.total_price / 100) * vm.model_data.tax) + vm.model_data.total_price;
    }
 
    vm.update_data = function (index) {

      if (index == vm.model_data.data.length-1) {
        if (vm.model_data.data[index]["fields"]["sku"]["wms_code"] && vm.model_data.data[index]["fields"]["order_quantity"]) {
          vm.model_data.data.push({"wms_code":"", "ean_number": "", "supplier_code":"", "order_quantity":"", "price":"", 
                                   "measurement_unit": "", "fields": {"dedicated_seller": vm.selected_seller, "order_quantity": "",
                                                                      "row_price": 0}});
        }
      } else {
        if(vm.model_data.data[index].seller_po_id){
             vm.delete_data('seller_po_id', vm.model_data.data[index].seller_po_id, index);
            }
        else {
        vm.delete_data('id', vm.model_data.data[index].pk, index);
        }
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

    vm.delete_data = function(key, id, index) {
      if(id) {
        var del_data = {}
        del_data[key] = id;
        vm.service.apiCall('delete_po/', 'GET', del_data).then(function(data){
          if(data.message) {
      vm.model_data.data[index].fields.row_price = (vm.model_data.data[index].fields.order_quantity * Number(vm.model_data.data[index].fields.price))
;
      vm.model_data.total_price = 0;

      angular.forEach(vm.model_data.data, function(one_row){
        vm.model_data.total_price = vm.model_data.total_price + (one_row.fields.order_quantity * one_row.fields.price);
      });
            vm.service.pop_msg(data.data);
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

    vm.barcode = function() {

      vm.barcode_title = 'Barcode Generation';

      vm.model_data['barcodes'] = [];

      angular.forEach(vm.model_data.data, function(barcode_data){

        var quant = barcode_data.fields.order_quantity;

       var sku_det = barcode_data.fields.sku.wms_code;

        if (barcode_data.fields.ean_number) {

            sku_det = barcode_data.fields.ean_number;
        }

        vm.model_data['barcodes'].push({'sku_code': sku_det, 'quantity': quant})

      })

      console.log(vm.barcode_print_data);

      vm.model_data['format_types'] = ['format1', 'format2', 'format3']

      var key_obj = {'format1': 'SKUCode', 'format2': 'Details', 'format3': 'Details'}

      $state.go('app.inbound.RaisePo.barcode');
    }

    vm.update_raise_po = function() {
      
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('validate_wms/', 'GET', elem, true).then(function(data){
        if(data.message){
          if(data.data == 'success') {
            vm.service.apiCall('modify_po_update/', 'GET', elem, true).then(function(data){
              if(data.message){
                if(data.data == 'Updated Successfully') {
                  vm.close();
                  vm.service.refresh(vm.dtInstance);
                } else {
                  vm.service.pop_msg(data.data);
                }
              }
            })
          } else {
            vm.service.pop_msg(data.data);
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

      vm.service.apiCall('validate_wms/', 'GET', elem, true).then(function(data){
        if(data.message) {
          if (data.data == "success") {
            vm.raise_po(url, elem);
          } else{
            vm.service.pop_msg(data.data);
          }
        }
      });
    }

    vm.raise_po = function(url, elem) {

      vm.service.alert_msg("Do want to Raise PO").then(function(msg) {
        if (msg == "true") {
          vm.service.apiCall(url, 'GET', elem).then(function(data){
            if(data.message) {
              vm.service.pop_msg(data.data);
              vm.service.refresh(vm.dtInstance);
              if(data.data.search("<div") != -1) {
                vm.html = $(data.data)[0];
                var html = $(vm.html).closest("form").clone();
                angular.element(".modal-body").html($(html).find(".modal-body > .form-group"));
                vm.print_enable = true;
              } else {
                vm.service.pop_msg(data.data);
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
          var temp = vm.dtInstance.DataTable.context[0].aoData[Number(key)];
          data.push({name: temp['_aData']["Order Type"], value :temp['_aData']['Supplier ID']});
        }
      });
      vm.service.alert_msg("Do want to Raise PO").then(function(msg) {
        if (msg == "true") {
          vm.service.apiCall('confirm_po1/', 'GET', data, true).then(function(data){
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
        } else {

          vm.bt_disable = false;
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
          var temp = vm.dtInstance.DataTable.context[0].aoData[Number(key)];
          data.push({name: temp['_aData']["Order Type"], value:temp['_aData']['Supplier ID']});
        }
      });
      vm.service.apiCall('delete_po_group/', 'GET', data, true).then(function(data){
        if(data.message) {
           vm.bt_disable = true;
           vm.selectAll = false;
           vm.service.refresh(vm.dtInstance);
        }
      });
   }

    vm.get_sku_details = function(product, item, index) {
      product.fields.sku.wms_code = item.wms_code;
      product.fields.measurement_unit = item.measurement_unit;
      product.fields.order_quantity = 1;
      product.fields.price = "";
      product.fields.description = item.sku_desc;
      if (typeof(vm.model_data.supplier_id) == "undefined" || vm.model_data.supplier_id.length == 0){
        return false;
      } else {
        var supplier = vm.model_data.supplier_id;
        $http.get(Session.url+'get_mapping_values/?wms_code='+product.fields.sku.wms_code+'&supplier_id='+supplier, {withCredentials : true}).success(function(data, status, headers, config) {
          if(Object.values(data).length) {
            product.fields.price = data.price;
            product.fields.supplier_code = data.supplier_code;
            product.fields.ean_number = data.ean_number;

            vm.model_data.data[index].fields.row_price = (vm.model_data.data[index].fields.order_quantity * Number(vm.model_data.data[index].fields.price));
            vm.model_data.total_price = 0;

            angular.forEach(vm.model_data.data, function(one_row){
              vm.model_data.total_price = vm.model_data.total_price + (one_row.fields.order_quantity * one_row.fields.price);
            });
          }
          vm.model_data.sub_total = ((vm.model_data.total_price / 100) * vm.model_data.tax) + vm.model_data.total_price;
        });
      }
    }

    vm.key_event = function(product, item) {
       if (typeof(vm.model_data.supplier_id) == "undefined" || vm.model_data.supplier_id.length == 0){
         return false;
       } else {
         var supplier = vm.model_data.supplier_id;
         $http.get(Session.url+'get_mapping_values/?wms_code='+product.fields.sku.wms_code+'&supplier_id='+supplier, {withCredentials : true}).success(function(data, status, headers, config) {
           if(Object.values(data).length){
             product.fields.price = data.price;
             product.fields.supplier_code = data.supplier_code;
             product.fields.sku.wms_code = data.sku;
             product.fields.ean_number = data.ean_number;
           }
         });
       }
    }

    vm.add_raise_po = function() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('validate_wms/', 'GET', elem, true).then(function(data){
        if(data.message){
          if(data.data == 'success') {
            vm.service.apiCall('add_po/', 'GET', elem, true).then(function(data){
              if(data.message){
                if(data.data == 'Added Successfully') {
                  vm.close();
                  vm.service.refresh(vm.dtInstance);
                } else {
                  vm.service.pop_msg(data.data);
                }
              }
            })
          } else {
            vm.service.pop_msg(data.data);
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

