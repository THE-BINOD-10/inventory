'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('Orders',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', 'Data', '$modal', '$log', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q, Data, $modal, $log) {
    var vm = this;
    //$state.go($state.current, {}, {reload: true});
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.show_client_details = vm.permissions.create_order_po;
    vm.apply_filters = colFilters;
    vm.default_status = true;
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.merge_invoice = false;
    vm.scroll_data = true;
    vm.special_key = {market_places: "", customer_id: ""}
    vm.picklist_display_address = vm.permissions.picklist_display_address;
    vm.payment_status = ['To Pay', 'VPP', 'Paid'];
    vm.project_name = "";

    vm.update_order_details = update_order_details;
    function update_order_details(index, data, last) {
      vm.default_status = false;
      if (last) {
        vm.model_data.data.push({item_code:'', product_title:'', quantity:0, unit_price:0, discount_price:0, tax:0, invoice_amount:0, remarks:'', order_status:'', new_product:true, default_status: false, sku_status: 1});
      } else {
        var data_to_delete = {};
        data_to_delete['order_id'] = vm.order_id;
        data_to_delete['item_code'] = data.item_code;
        data_to_delete['order_id_code'] = vm.order_id_code;

        if (data.new_product) {
          vm.model_data.data.splice(index,1);
        } else {
          vm.service.apiCall('delete_order_data/', 'GET', data_to_delete).then(function(data){

            if (data.message){
                vm.model_data.data.splice(index,1);
            }
          });
        }
      }
    }

    vm.order_charges = [];

    vm.default_charge = function() {
      if (vm.order_charges.length == 1) {
        vm.flag = true;
      }
    }

    vm.delete_charge = function(id) {
      if (id) {
        vm.service.apiCall("delete_order_charges?id="+id, "GET").then(function(data){
          if(data.message){
            Service.showNoty(data.data.message);
          }
        });
      }
    }

    vm.save_order_charges = function(order_id, $event) {
      var data_params = {};
      data_params['order_id'] = order_id;
      data_params['order_charges'] = JSON.stringify(vm.order_charges);
      angular.forEach(vm.order_charges, function(obj) {
        if($.isEmptyObject(obj['charge_name'])) {
          colFilters.showNoty('Charge Name cannot be Empty');
          $event.preventDefault();
        }
        if($.isEmptyObject(String(obj['charge_amount']))) {
          colFilters.showNoty('Charge Amount cannot be Empty');
          $event.preventDefault();
        }
      })
      vm.service.apiCall('add_order_charges/', 'POST', data_params).then(function(data) {
        vm.reloadData();
        colFilters.showNoty('Saved sucessfully');
      })
    }

    vm.g_data = {};
    angular.copy(Data.other_view, vm.g_data);

    if(Session.user_profile.user_type != "marketplace_user") {

      vm.g_data.views.pop(1);
    } else if(Session.user_profile.user_type == "marketplace_user") {

      vm.g_data.views = ["CustomerOrderView", "SellerOrderView"];
      if (vm.g_data.views.indexOf(vm.g_data.view) == -1) {

        vm.g_data.view = "SellerOrderView";
      }
    }

    vm.pop_buttons = false;
    if (["OrderView", "CustomerOrderView"].indexOf(vm.g_data.view) != -1) {
      vm.pop_buttons = true;
    }

    vm.filters = {'datatable': vm.g_data.view, 'search0':'', 'search1':'', 'search2': '', 'special_key': JSON.stringify(vm.special_key)}
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
       .withOption('order', [0, 'asc'])
       .withOption('lengthMenu', [100, 200, 300, 400, 500, 1000, 2000])
       .withOption('pageLength', 100)
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

    vm.dtColumns = vm.service.build_colums2(vm.g_data.tb_headers[vm.g_data.view]);
    vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
      .renderWith(function(data, type, full, meta) {
        if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
          vm.selected = {};
        }
        vm.selected[meta.row] = vm.selectAll;
        return vm.service.frontHtml + meta.row + vm.service.endHtml;
      }))


   vm.dtInstance = {};
    vm.reloadData = reloadData;

    function reloadData () {
        vm.dtInstance.reloadData();
    };

   vm.status_type = ["Cleared", "Blocked"];
   vm.selected_status = '';

   vm.isLast = isLast;
    function isLast(check) {

      var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
      return cssClass
    }

  vm.send_order_data = function(form) {
    var elem = angular.element($('form'));
    elem = elem[0];
    elem = $(elem).serializeArray();
    if (elem[0].value == '? string: ?'){
        elem[0].value = '';
    }
    elem.push({name: 'order_id', value: vm.order_id}, {name: 'customer_id', value: vm.customer_id},
              {name: 'customer_name', value: vm.customer_name},
              {name: 'phone', value: vm.phone}, {name: 'email', value: vm.email}, {name: 'address', value: vm.address},
              {name: 'shipment_date', value: vm.shipment_date}, {name: 'market_place', value: vm.market_place})
    vm.service.apiCall('update_order_data/', 'POST', elem).then(function(data){
        console.log(data);
        vm.reloadData();
        colFilters.showNoty('Saved sucessfully');
    })
  }

  vm.back_button = function() {
    vm.reloadData();
    $state.go('app.outbound.ViewOrders')
  }

  vm.delete_order_data = function(ord_id) {

      var delete_data = {};
      delete_data['order_id'] = ord_id;
      delete_data['order_id_code'] = vm.order_id_code;

      vm.service.apiCall('order_delete/', 'GET', delete_data).then(function(data){
          if (data.message) {
            colFilters.showNoty(data.data);
            vm.reloadData();
            $state.go('app.outbound.ViewOrders');
          }
          })
  }

  vm.get_sku_data = function(record, item){

    var sku = item.wms_code;
    var value_exested = false;

    for (var i = 0; i < vm.model_data.data.length; i++) {
      if (sku === vm.model_data.data[i].item_code){
        value_exested = true;
        break;
      }
    }

    if(value_exested){

      record.item_code = '';
      record.product_title = '';
      record.quantity = 0;
      record.unit_price = 0;

      vm.service.showNoty(item.sku_desc+" is already existed. Please try it another one.", "success", "topRight");
    } else {
      record.item_code = sku;
      record.product_title = item.sku_desc;

      var data = {sku_codes: sku, cust_id: vm.model_data.customer_id, tax_type: vm.model_data.tax_type}

      vm.service.apiCall("get_customer_sku_prices/", "POST", data).then(function(data) {
        if(data.message) {
          if(data.data.length == 1) {

            if(!(record.quantity)) {
              record.quantity = 1;
            }
            record.unit_price = data.data[0].price;
            record.default_status = false;
            record.discount_per = 0;
            record.invoice_amount = record.quantity * record.unit_price;
            record.remarks = "";
            record.taxes = data.data[0].taxes;

            if (data.data[0].taxes.length) {
              for (var i = 0; i < data.data[0].taxes.length; i++) {

                if(data.data[0].price >= data.data[0].taxes[i].min_amt && data.data[0].price <= data.data[0].taxes[i].max_amt) {
                  record.igst = data.data[0].taxes[i].igst_tax;
                  record.cgst = data.data[0].taxes[i].cgst_tax;
                  record.sgst = data.data[0].taxes[i].sgst_tax;
                  record.cess = data.data[0].taxes[i].cess_tax;
                  break;
                }
              }
            } else {
              record.igst = 0;
              record.cgst = 0;
              record.sgst = 0;
              record.cess = 0;
            }
          }
        }
      });
    }
  }

  function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {

    vm.ord_status = '';

    $('td:not(td:first)', nRow).unbind('click');
    $('td:not(td:first)', nRow).bind('click', function() {
      if ((vm.g_data.view == 'CustomerOrderView') || (vm.g_data.view == 'OrderView') || (vm.g_data.view == 'SellerOrderView')) {

        $scope.$apply(function() {

	      console.log(aData);
          $state.go('app.outbound.ViewOrders.OrderDetails');

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
            vm.courier_name = data.data.data_dict[0].courier_name;
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
            vm.project_name = value.project_name
	          vm.market_place = value.market_place;
            vm.unit_price = value.unit_price;
            vm.sgst = value.sgst_tax;
            vm.cgst = value.cgst_tax;
            vm.igst = value.igst_tax;
            vm.cess = value.cess_tax;
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
              discount_per: vm.discount_per, sgst:vm.sgst, cgst:vm.cgst, igst:vm.igst, cess:vm.cess,default_status: true, sku_status: value.sku_status})
              var record = vm.model_data.data[index]
              vm.changeInvoiceAmt(record);
              index++;
	        });
	      });
       })
     }
     })
   }

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.reloadData();
    });

    vm.changeInvoiceAmt = function(data, flag){

      var total = (data.quantity * data.unit_price);
      var discount_amt = (total*data.discount_per)/100;
      var invoice_amount_dis = Number(total - discount_amt);

      if (flag) { // Used to execute taxes for unitprice change only
        if (data.taxes.length) {
          for (var i = 0; i < data.taxes.length; i++) {

            if (data.unit_price >= data.taxes[i].min_amt && data.unit_price <= data.taxes[i].max_amt) {
              data.igst = data.taxes[i].igst_tax;
              data.cgst = data.taxes[i].cgst_tax;
              data.sgst = data.taxes[i].sgst_tax;
              data.cess = data.taxes[i].cess_tax;
              break;
            }
          }
        } else {
          data.igst = 0;
          data.cgst = 0;
          data.sgst = 0;
          data.cess = 0;
        }
      }

      var tax = Number(data.sgst)+Number(data.cgst)+Number(data.igst) + Number(data.cess);

      data.discount = discount_amt;
      data.invoice_amount = (invoice_amount_dis + (invoice_amount_dis*tax)/100);
    }

    vm.model_data = {};
    vm.filter_enable = true;
    vm.market_filters = [];
    vm.market_filter = "";

    vm.close = close;
    function close() {
      $state.go('app.outbound.ViewOrders');
      vm.message = "";
      vm.confirm_disable = false;
      vm.merge_invoice = false;
      vm.print_enable = false;
      vm.reloadData();
    }

    vm.generate = generate;
    function generate() {
      vm.bt_disable = true;
      for(var key in vm.selected){
        console.log(vm.selected[key]);
        if(vm.selected[key]) {
          vm.generate_data.push(vm.dtInstance.DataTable.context[0].aoData[key]._aData);
        }
      }
      if(vm.generate_data.length > 0) {
        console.log(vm.generate_data);
        var data = {};
        if(vm.g_data.view == 'OrderView') {

          for(var i=0;i<vm.generate_data.length;i++) {
            data[$(vm.generate_data[i][""]).attr("name")]= vm.generate_data[i]['SKU Code'];
          }
          data["ship_reference"] = vm.ship_reference;
        } else if(vm.g_data.view == 'SKUView') {

          for(var i=0;i<vm.generate_data.length;i++) {
            data[vm.generate_data[i].data_value]= vm.generate_data[i]['Total Quantity'];
          }
        } else if(vm.g_data.view == 'CustomerOrderView' || vm.g_data.view == 'CustomerCategoryView' || vm.g_data.view == 'SellerOrderView'){
          for(var i=0;i<vm.generate_data.length;i++) {
            data[vm.generate_data[i]["data_value"]]= vm.generate_data[i]['Total Quantity'];
          }
        }
        data['filters'] = vm.dtInstance.DataTable.context[0].ajax.data['special_key'];
        data['enable_damaged_stock'] = vm.enable_damaged_stock;

        var mod_data = {data: data};
        mod_data['url'] = vm.g_data.generate_picklist_urls[vm.g_data.view];
        mod_data['method'] = "POST";
        mod_data['page'] = "ViewOrders";

        $scope.open = function (size) {

          var modalInstance = $modal.open({
            templateUrl: 'views/outbound/toggle/common_picklist.html',
            controller: 'Picklist',
            controllerAs: 'pop',
            size: size,
            backdrop: 'static',
            keyboard: false,
            resolve: {
              items: function () {
                return mod_data;
              }
            }
          });

          modalInstance.result.then(function (selectedItem) {
            var data = selectedItem;
            reloadData();
            if (data.message == 'invoice') {
              angular.copy(data.data, vm.pdf_data);
              if (Session.user_profile['user_type'] == 'marketplace_user') {
                $state.go('app.outbound.ViewOrders.InvoiceM');
              } else if (vm.pdf_data.detailed_invoice) {
                $state.go('app.outbound.ViewOrders.DetailGenerateInvoice');
              } else {
                $state.go('app.outbound.ViewOrders.GenerateInvoice');
              }
            } else if (data.message == 'html') {
              $state.go("app.outbound.ViewOrders.InvoiceE");
              $timeout(function () {
                $(".modal-body:visible").html(data.data)
              }, 3000);
            }
          }, function () {
          $log.info('Modal dismissed at: ' + new Date());
          });
        };
        $scope.open('lg');
        vm.generate_data = [];
      } else {

        vm.bt_disable = false;
      }
    }

    vm.model_transfer = {};
    vm.transfer = transfer;
    function transfer() {
      vm.model_transfer = {};
      if(vm.permissions.batch_switch){
        batch_transfer_order();
      } else {
        get_transfer_data();
      }
    }

    vm.title = "Update Job Order"

    vm.print = function() {
      $state.go('app.production.RaiseJO.JobOrderPrint');
    }

    vm.seleted_rows = []
    vm.generate_data = []

    vm.batch_generate_picklist = batch_generate_picklist;
    function batch_generate_picklist() {
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
          data[vm.generate_data[i].data_value]= vm.generate_data[i].total_quantity;
        }
        vm.service.apiCall('batch_generate_picklist/', 'POST', data).then(function(data){
          if(data.message) {
            angular.copy(data.data, vm.model_data);
            for(var i=0; i<vm.model_data.data.length; i++){
                    vm.model_data.data[i]['sub_data'] = [];
                    var value = (vm.permissions.use_imei)? 0: vm.model_data.data[i].picked_quantity;
                    vm.model_data.data[i]['sub_data'].push({zone: vm.model_data.data[i].zone,
                                                         location: vm.model_data.data[i].location,
                                                         orig_location: vm.model_data.data[i].location,
                                                         picked_quantity: value, scan: ""});
                  }
            $state.go('app.outbound.ViewOrders.Picklist');
            reloadData();
            pop_msg(data.data.stock_status);
          }
        });
        vm.generate_data = [];
      }
    }

    vm.ship_reference = "";
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
          data[$(vm.generate_data[i][""]).attr("name")]= vm.generate_data[i]['SKU Code'];
        }
        data["ship_reference"] = vm.ship_reference;
        data["enable_damaged_stock"] = vm.enable_damaged_stock;
        vm.service.apiCall('generate_picklist/', 'POST', data).then(function(data){
          if(data.message) {
            angular.copy(data.data, vm.model_data);
            for(var i=0; i<vm.model_data.data.length; i++){
                    vm.model_data.data[i]['sub_data'] = [];
                    var value = (vm.permissions.use_imei)? 0: vm.model_data.data[i].picked_quantity;
                    vm.model_data.data[i]['sub_data'].push({zone: vm.model_data.data[i].zone,
                                                         location: vm.model_data.data[i].location,
                                                         orig_location: vm.model_data.data[i].location,
                                                         picked_quantity: value, scan: ""});
                  }
            $state.go('app.outbound.ViewOrders.Picklist');
            reloadData();
          }
        });
        vm.generate_data = [];
      }
    }


    vm.pdf_data = {};
    vm.picklist_confirmation = picklist_confirmation;
    function picklist_confirmation() {
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('picklist_confirmation/', 'POST', elem, true).then(function(data){
        if(data.message) {
          if(data.data == "Picklist Confirmed") {
            $state.go('app.outbound.ViewOrders');
          } else if (data.data.status == 'invoice') {

            angular.copy(data.data.data, vm.pdf_data);
            if (vm.pdf_data.detailed_invoice) {
              $state.go('app.outbound.ViewOrders.DetailGenerateInvoice');
            } else {
              $state.go('app.outbound.ViewOrders.GenerateInvoice');
            }
          } else {
            pop_msg(data.data);
          }
        }
      });
    }

    function get_transfer_data(){
      var data = {};
      var length = vm.seleted_rows.length/2;
      var rows = vm.seleted_rows.slice(0, length)
      angular.forEach(vm.selected, function(key, value){
        if(key) {
          console.log(value);
          var row = rows[parseInt(value)];
          data[$(row[""]).attr("name")] = row["Marketplace"];
        }
      })
      vm.service.apiCall('transfer_order/', 'POST', data).then(function(data){
        if(data.message) {
          if(data.data == "No Users Found") {
            console.log("fail")
          } else {
            angular.copy(data.data, vm.model_transfer)
            $state.go('app.outbound.ViewOrders.Transfer');
          }
        }
      });
    }

    function batch_transfer_order() {
      var data = {};
      var length = vm.seleted_rows.length/2;
      var rows = vm.seleted_rows.slice(0, length)
      angular.forEach(vm.selected, function(key, value){
        if(key) {
          console.log(value);
          var row = rows[parseInt(value)];
          data[row.sku_code] = row.total_quantity;
        }
      })
      vm.service.apiCall('batch_transfer_order/', 'POST', data).then(function(data){
        if(data.message) {
          if(data.data == "No Users Found") {
            console.log("fail");
          } else {
            angular.copy(data.data, vm.model_transfer);
            $state.go('app.outbound.ViewOrders.Transfer');
          }
        }
      });
    }

    vm.confirm_transfer = function() {
      console.log(vm.model_transfer  );
      var data = {};
      for(var i=0; i<vm.model_transfer.data.length; i++) {
        if(vm.model_transfer.data[i].option) {
          data[vm.model_transfer.data[i].id] = vm.model_transfer.data[i].option
        }
      }
      vm.service.apiCall('confirm_transfer/', 'POST', data).then(function(data){
        if(data.message) {
          pop_msg(data.data);
        }
      })
    }

    function pop_msg(msg) {
      vm.message = msg;
      $timeout(function () {
          vm.message = "";
      }, 3000);
      reloadData();
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

  vm.update_data = function(data, index, last, first) {
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
          vm.model_data.data.splice(index, 1);
        }
      });
  }
  vm.update_data_order = function(index, data, last) {
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
  function cal_quantity(record, data) {
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
        var picklist_number = $($.parseHTML(data.data)).find("input").val()
        if (picklist_number) {
            picklist_number = 'Picklist_'+picklist_number
        } else {
            picklist_number = Picklist
        }
        vm.service.print_data(data.data, picklist_number);
      }
    })
  }

  vm.change_customer = function(data) {

    if (data) {
      vm.special_key.customer_id = data;
      vm.dtInstance.DataTable.context[0].ajax.data['special_key'] = JSON.stringify(vm.special_key);
      vm.reloadData();
    }
  }

  vm.market_list = [];
  vm.service.apiCall('get_marketplaces_list/').then(function(data){
    if(data.message) {
      vm.market_list = data.data.marketplaces;
      $timeout(function () {
        $('.selectpicker').selectpicker();
        $(".bootstrap-select").change(function(){
            var data = $(".selectpicker").val();
            var send = "";
            if (data) {
              for(var i = 0; i < data.length; i++) {
                send += data[i].slice(1)+",";
              }
            }
            vm.special_key.market_places = send.slice(0,-1);
            vm.dtInstance.DataTable.context[0].ajax.data['special_key'] = JSON.stringify(vm.special_key);
            vm.reloadData();
        })
      }, 1000);
    }
  });

  vm.address_change = function(switch_value) {
    vm.service.apiCall("switches/?picklist_display_address="+String(switch_value)).then(function(data) {
        if(data.message) {
            Service.showNoty(data.data);
        }
    });
    vm.picklist_display_address = switch_value;
    Session.roles.permissions['picklist_display_address'] = switch_value;
  }

  /*vm.change_enable_damaged_stock = function(switch_value) {
    vm.service.apiCall("switches/?enable_damaged_stock="+String(switch_value)).then(function(data) {
      if(data.message) {
        Service.showNoty(data.data);
      }
    });
    vm.enable_damaged_stock = switch_value;
    Session.roles.permissions['enable_damaged_stock'] = switch_value;
  }*/

  vm.add_order = function() {
    $state.go("app.outbound.ViewOrders.CreateOrder");
  }

  vm.insert_order_data = function(data) {
    if (data.$valid) {
      vm.bt_disable = true;
      console.log(form);
      var elem = angular.element($('form'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      vm.service.apiCall('insert_order_data/', 'GET', elem).then(function(data){
        if(data.message) {
          if("Success" == data.data) {
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

  /* Raise JO */

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

  vm.raise_jo = function() {
    var data = [];
    data.push({name: 'table_name', value: 'orders_table'})
    if (vm.g_data.view == 'OrderView') {
      for(var key in vm.selected){
        if(vm.selected[key]) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]._aData
          data.push({name: 'id', value: $(temp[""]).attr("name")})
        }
      }
    } else {
      for(var key in vm.selected){
        if(vm.selected[key]) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]._aData
          data.push({name: 'order_id', value: temp['data_value']})
        }
      }
    }

    var send_data  = {data: data}
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

  vm.html = ""
  vm.print_enable = false;
  vm.confirm_jo = function() {
      var elem = angular.element($('form:visible'));
      elem = elem[0];
      elem = $(elem).serializeArray();
      //elem = $.param(elem);
      $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
      Service.apiCall("confirm_jo/", "POST", elem, true).then(function(data){
        if(data.message) {
      //$http({
      //         method: 'POST',
      //         url:Session.url+"confirm_jo/",
      //         withCredential: true,
      //         data: elem}).success(function(data, status, headers, config) {

            vm.reloadData();
            if(data.data.search("<div") != -1) {
              vm.html = $(data.data)[0];
              var html = $(vm.html).closest("form").clone();
              angular.element(".modal-body:visible").html($(html).find(".modal-body > .form-group"));
              vm.print_enable = true;
            } else {
              pop_msg(data)
            }
        }
      });
  }

  vm.print = print;
  function print() {
      colFilters.print_data(vm.html);
  }
  /* raise po */
  vm.backorder_po = function() {
    var data = [];
    if (vm.g_data.view == 'OrderView') {
      for(var key in vm.selected){
        if(vm.selected[key]) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]._aData
          data.push({name: 'id', value: $(temp[""]).attr("name")})
        }
      }
    } else {
      for(var key in vm.selected){
        if(vm.selected[key]) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]._aData
          data.push({name: 'order_id', value: temp['data_value']})
        }
      }
    }
	data.push({name: 'table_name', value: 'orders_table'})
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

  vm.print_enable = false;
  vm.confirm_po = function() {
      var elem = $(form).serializeArray();

      Service.apiCall("confirm_back_order/", "POST", elem, true).then(function(data){
        if(data.message) {
          vm.confirm_disable = true; vm.message = data.data; reloadData();

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

  vm.raise_stock_transfer = function() {
    var data = {};
    var url = '';
    if (vm.g_data.view == 'OrderView') {
      for(var key in vm.selected){
        if(vm.selected[key]) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]._aData
          if (data[temp['SKU Code']]) {
            data[temp['SKU Code']].order_quantity += temp['Product Quantity'];
          } else {
            data[temp['SKU Code']] = {wms_code: temp['SKU Code'], order_quantity: temp['Product Quantity'], price: 0}
          }
        }
      }
      data = Object.values(data);
    } else {
      data = [];
      for(var key in vm.selected){
        if(vm.selected[key]) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]._aData
          data.push(temp['data_value'])
        }
      }
      url = 'get_stock_transfer_details/';
      data = {order_id: data.join(',')};
    }

    var send_data  = {data: data, url: url}
    var modalInstance = $modal.open({
      templateUrl: 'views/outbound/toggle/create_stock_transfer.html',
      controller: 'StockTransferPOP',
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
    //Service.stock_transfer = JSON.stringify(data)
    //$state.go('app.outbound.ViewOrders.ST', {data: Service.stock_transfer})
    //$state.go('app.outbound.ViewOrders.ST', )
  }

  vm.change_datatable = function() {
    Data.other_view.view =  vm.g_data.view;
    $state.go($state.current, {}, {reload: true});
  }

  // Edit invoice
    vm.invoice_edit = false;
    vm.save_invoice_data = function(data) {

      var send = $(data.$name+":visible").serializeArray();
      vm.service.apiCall("edit_invoice/","POST",send).then(function(data){
        if(data.message) {
          vm.invoice_edit = false;
        }
      })
      console.log("edit");
    }

  vm.print_grn = function() {

    vm.service.print_data(vm.html, "Purchase Order");
  }

  }
