'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('StockTransferOrders',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service',  '$q', 'Data', '$modal', '$log', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, Data, $modal, $log) {
    var vm = this;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;

    /*vm.g_data = {};
    angular.copy(Data.other_view, vm.g_data);

    if(Session.user_profile.user_type != "marketplace_user") {

      vm.g_data.views.pop(1);
    } else if(Session.user_profile.user_type == "marketplace_user") {

      vm.g_data.views = ["CustomerOrderView", "SellerOrderView"];
      if (vm.g_data.views.indexOf(vm.g_data.view) == -1) {

        vm.g_data.view = "SellerOrderView";
      }
    }*/

   

    vm.changeDtFields = function(flag){

      if (flag) {

       vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'AltStockTransferOrders'},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('order', [1, 'desc'])
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
            DTColumnBuilder.newColumn('Warehouse Name').withTitle('Warehouse Name'),
            DTColumnBuilder.newColumn('Stock Transfer ID').withTitle('Stock Transfer ID'),
            DTColumnBuilder.newColumn('Creation Date').withTitle('Creation Date'),
        ];
      } else {

        vm.dtOptions = DTOptionsBuilder.newOptions()
       .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'StockTransferOrders'},
              xhrFields: {
                withCredentials: true
              }
           })
       .withDataProp('data')
       .withOption('order', [1, 'desc'])
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
            DTColumnBuilder.newColumn('Warehouse Name').withTitle('Warehouse Name'),
            DTColumnBuilder.newColumn('Stock Transfer ID').withTitle('Stock Transfer ID'),
            DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
            DTColumnBuilder.newColumn('Quantity').withTitle('Quantity')
        ];
      }
    }

    vm.changeDtFields(false);    

    /*vm.dtColumns = [
        DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
                if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                  vm.selected = {};
                }
                vm.selected[meta.row] = vm.selectAll;
                return vm.service.frontHtml + meta.row + vm.service.endHtml;
            }).notSortable(),
        DTColumnBuilder.newColumn('Warehouse Name').withTitle('Warehouse Name'),
        DTColumnBuilder.newColumn('Stock Transfer ID').withTitle('Stock Transfer ID'),
        DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('Quantity').withTitle('Quantity')
    ];*/

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

    /*function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
            });
        });
        return nRow;
    }*/ 

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {

    vm.ord_status = '';

    $('td:not(td:first)', nRow).unbind('click');
    $('td:not(td:first)', nRow).bind('click', function() {
      // if ((vm.g_data.view == 'CustomerOrderView') || (vm.g_data.view == 'OrderView') || (vm.g_data.view == 'SellerOrderView')) {

        $scope.$apply(function() {

        console.log(aData);
          $state.go('app.outbound.ViewOrders.StockTransferAltView');

         //vm.market_place = aData['Market Place'];
          var data = {};
          var url = "get_view_order_details/";
          if ((vm.g_data.view == 'CustomerOrderView') || (vm.g_data.view == 'OrderView')) {
            data = {id: $(aData[""]).attr('name'),order_id: aData["Order ID"]}
          } else if (vm.g_data.view == 'SellerOrderView') {
            data = {id: $(aData[""]).attr('name'), sor_id: aData['SOR ID'], uor_id: aData['UOR ID']}
            url = "get_seller_order_details/"
          }
          vm.service.apiCall(url, "GET", data).then(function(data){

            var all_order_details = data.data.data_dict[0].ord_data;
            vm.ord_status = data.data.data_dict[0].status;
            vm.invoice_type = data.data.data_dict[0].invoice_type;
            vm.display_status_none = (vm.ord_status=="")?true:false;

            vm.model_data = {}
            var empty_data = {data: []}
            angular.copy(empty_data, vm.model_data);

            if (vm.g_data.view == 'CustomerOrderView'){
              vm.input_status = false;
            } else {
              vm.input_status = true;
            }

            if(vm.g_data.view == 'SellerOrderView') {
              vm.model_data["sor_id"] = aData['SOR ID'];
            }
            vm.order_input_status = false;

            vm.model_data["central_remarks"]= data.data.data_dict[0].central_remarks;
            vm.model_data["all_status"] = data.data.data_dict[0].all_status;
            vm.model_data["seller_data"] = data.data.data_dict[0].seller_details;
            vm.model_data["tax_type"] = data.data.data_dict[0].tax_type;
            vm.model_data["invoice_types"] = data.data.data_dict[0].invoice_types;
            if (data.data.data_dict[0].ord_data[0].payment_status) {
              vm.model_data["payment_status"] = data.data.data_dict[0].ord_data[0].payment_status;
            }
            var index = 0;
            angular.forEach(all_order_details, function(value, key){

            vm.customer_id = value.cust_id;
            vm.customer_name = value.cust_name;
            vm.phone = value.phone;
            vm.email = value.email;
            vm.address = value.address;
            vm.city = value.city;
            vm.state = value.state;
            vm.order_id_code = value.order_id_code;
            vm.pin = value.pin;
            vm.product_title = value.product_title;
            vm.quantity = value.quantity;
            vm.shipment_date = value.shipment_date;
            vm.remarks = value.remarks;
            vm.cust_data = value.cus_data;
            vm.item_code = value.item_code;
            vm.order_id = value.order_id;
            vm.market_place = value.market_place;
            vm.unit_price = value.unit_price;
            vm.sgst = value.sgst_tax;
            vm.cgst = value.cgst_tax;
            vm.igst = value.igst_tax;
            vm.taxes = value.taxes;
            vm.order_charges = value.order_charges;
            vm.client_name = value.client_name;
            if (!vm.client_name) {
              vm.show_client_details = false;
            }
            // if (value.discount_percentage <= 99.99) {
              vm.discount_per = value.discount_percentage;
            // }

            var image_url = value.image_url;
            vm.img_url = vm.service.check_image_url(image_url);
            /*var custom_data = value.customization_data;
            vm.market_place = value.market_place;
            if (custom_data.length === 0){

              vm.customization_data = '';
            }
            else {

              var img_url = custom_data[0][3];
              vm.img_url = vm.service.check_image_url(img_url)
            }*/

              var record = vm.model_data.data.push({item_code: vm.item_code, product_title: vm.product_title, quantity: vm.quantity,
              image_url: vm.img_url, remarks: vm.remarks, unit_price: vm.unit_price, taxes: vm.taxes,
              discount_per: vm.discount_per, sgst:vm.sgst, cgst:vm.cgst, igst:vm.igst, default_status: true, sku_status: value.sku_status})
              var record = vm.model_data.data[index]
              vm.changeInvoiceAmt(record);
              index++;
          });
        });
       })
     // }
     })
   }

    vm.close = close;
    function close() {
      $state.go('app.outbound.ViewOrders');
    }

    vm.back_button = function() {
      vm.reloadData();
      $state.go('app.outbound.ViewOrders')
    }

    vm.model_data = {};
    vm.generate_data = [];
    vm.generate_picklist = generate_picklist;
    function generate_picklist() {
      for(var key in vm.selected){
        console.log(vm.selected[key]);
        if(vm.selected[key]) {
          vm.generate_data.push(vm.dtInstance.DataTable.context[0].aoData[key]._aData);
        }
      }
      if(vm.generate_data.length > 0) {
        console.log(vm.generate_data);
        var data = {};
        for(var i=0;i<vm.generate_data.length;i++) {
          data[vm.generate_data[i]['Stock Transfer ID']+":"+vm.generate_data[i]['SKU Code']]= vm.generate_data[i].DT_RowAttr.id;
        }
        vm.service.apiCall('st_generate_picklist/', 'POST', data, true).then(function(data){
          if(data.message) {
            angular.copy(data.data, vm.model_data);
            for(var i=0; i<vm.model_data.data.length; i++){
                    vm.model_data.data[i]['sub_data'] = [];
                    var value = (vm.permissions.use_imei)? 0: vm.model_data.data[i].picked_quantity;
                    vm.model_data.data[i]['sub_data'].push({zone: vm.model_data.data[i].zone,
                                                         location: vm.model_data.data[i].location,
                                                         orig_location: vm.model_data.data[i].location,
                                                         picked_quantity: value});
                  }
            $state.go('app.outbound.ViewOrders.Picklist');
            reloadData();
          }
        });
        vm.generate_data = [];
      }
    }

    vm.serial_scan = function(event, scan, data, record) {
      if ( event.keyCode == 13) {
        var id = data.id;
        var total = 0;
        for(var i=0; i < data.sub_data.length; i++) {
          total = total + parseInt(data.sub_data[i].picked_quantity);
        }
        var scan_data = scan.split("\n");
        var length = scan_data.length;
        var elem = {};
        elem[id]= scan_data[length-1]
        if(total < data.reserved_quantity) {
          vm.service.apiCall('check_imei/', 'GET', elem).then(function(data){
            if(data.message) {
              if(data.data == "") {
                record.picked_quantity = parseInt(record.picked_quantity) + 1;
              } else {
                pop_msg(data.data);
                scan_data.splice(length-1,1);
                record.scan = scan_data.join('\n');
                record.scan = record.scan+"\n";
              }
            }
          });
        } else {
          scan_data.splice(length-1,1);
          record.scan = scan_data.join('\n');
          record.scan = record.scan+"\n";
          pop_msg("picked already equal to reserved quantity");
        }
      }
    }

    vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

  vm.print_excel = print_excel;
  function print_excel(id)  {
    vm.service.apiCall('print_picklist_excel/','GET',{data_id: id}).then(function(data){
      if(data.message) {
        window.location = Session.host+data.data.slice(3);
      }
    })
  }

  vm.print_pdf = print_pdf;
  function print_pdf(id) {
    vm.service.apiCall('print_picklist/','GET',{data_id: id}).then(function(data){
      if(data.message) {
        vm.service.print_data(data.data);
      }
    })
  }

  vm.update_data = update_data;
  function update_data(index, data, last) {
    console.log(data);
    if (last) {
      var total = 0;
      for(var i=0; i < data.sub_data.length; i++) {
        total = total + parseInt(data.sub_data[i].picked_quantity);
      }
      if(total < data.reserved_quantity) {
        var clone = {};
        angular.copy(data.sub_data[index], clone);
        clone.picked_quantity = data.reserved_quantity - total;
        data.sub_data.push(clone);
      }
    } else {
      data.sub_data.splice(index,1);
    }
  }

  vm.cal_quantity = cal_quantity;
  function cal_quantity(record, data, check) {
    console.log(record);
    var total = 0;
    for(var i=0; i < data.sub_data.length; i++) {
        total = total + parseInt(data.sub_data[i].picked_quantity);
    }
    if(data.reserved_quantity >= total){
      console.log(record.picked_quantity)
    } else {
      var quantity = data.reserved_quantity-total;
      if(quantity < 0) {
        quantity = total - parseInt(record.picked_quantity);
        quantity = data.reserved_quantity - quantity;
        record.picked_quantity = quantity;
      } else {
        record.picked_quantity = quantity;
      }
    }
  }

    vm.picklist_confirmation = picklist_confirmation;
    function picklist_confirmation() {
      var elem = angular.element($('form:visible'));
      elem = $(elem).serializeArray();
      vm.service.apiCall('picklist_confirmation/', 'POST', elem, true).then(function(data){
        if(data.message) {
          if(data.data == "Picklist Confirmed") {
            $state.go('app.outbound.ViewOrders');
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
      reloadData();
    }

  vm.add_stock_transfer = function() {
    $state.go("app.outbound.ViewOrders.CreateTransfer");
  }

  vm.insert_order_data = function(data) {
    if (data.$valid) {
      vm.bt_disable = true;
      console.log(form);
      var elem = angular.element($('form'));
      elem = elem[1];
      elem = $(elem).serializeArray();
      vm.service.apiCall('create_stock_transfer/', 'POST', elem).then(function(data){
        if(data.message) {
          if("Confirmed Successfully" == data.data) {
            vm.reloadData();
            vm.close();
          }
          pop_msg(data.data);
        }
      })
    } else {
      pop_msg("Fill Required Fields");
    }
  }

  /* raise po */
  vm.backorder_po = function() {
	var data = [];
	data.push({name: 'table_name', value: 'stock_transfer_order'})
    for(var key in vm.selected) {
        if(vm.selected[key]) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]._aData
          data.push({name: 'stock_transfer_id', value: temp['Stock Transfer ID'] })
		  data.push({name: 'sku_code', value: temp['SKU Code'] })
		  data.push({name: 'id', value: temp['DT_RowAttr']['id'] })
        }
    }
    var send_data  = {data: data}
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
    //$state.go("app.outbound.ViewOrders.PO", {data: JSON.stringify(data)});
  }

  vm.raise_jo = function() {
	var data = [];
    data.push({name: 'table_name', value: 'stock_transfer_order'})
    for(var key in vm.selected) {
        if(vm.selected[key]) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]._aData
          data.push({name: 'stock_transfer_id', value: temp['Stock Transfer ID'] })
          data.push({name: 'sku_code', value: temp['SKU Code'] })
          data.push({name: 'id', value: temp['DT_RowAttr']['id'] })
        }
    }
    var send_data = {data: data}
    var modalInstance = $modal.open({
      templateUrl: 'views/outbound/toggle/back/backorder_jo.html',
      controller: 'BackorderJOPOP',
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
  }
}
