'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('CustomOrders',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', 'Data', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, Data) {

  var vm = this;
  vm.service = Service;
  vm.g_data = Data.custom_orders;
  vm.permissions = Session.roles.permissions;

    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.dtOptions = DTOptionsBuilder.newOptions()
      .withOption('ajax', {
              url: Session.url+'results_data/',
              type: 'POST',
              data: {'datatable': 'CustomOrders'},
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
      .withOption('rowCallback', rowCallback)
      .withOption('initComplete', function( settings ) {
         console.log("completed")
       });

    vm.dtColumns = vm.service.build_colums(vm.g_data.tb_headers);
    vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
      .renderWith(function(data, type, full, meta) {
        if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
          vm.selected = {};
        }
        vm.selected[meta.row] = vm.selectAll;
        return vm.service.frontHtml + meta.row + vm.service.endHtml;
      }))

  vm.change_datatable = function() {

    vm.dtInstance._renderer.options.ajax.data['datatable'] = vm.g_data.view;
    var temp = {};
    temp = vm.service.build_colums(vm.g_data.tb_headers);
    temp.unshift(DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
      .renderWith(function(data, type, full, meta) {
        if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
          vm.selected = {};
        }
        vm.selected[meta.row] = vm.selectAll;
        return vm.service.frontHtml + meta.row + vm.service.endHtml;
      }))
    vm.dtColumns = temp;
  }

  vm.dtInstance = {};

  vm.reloadData = reloadData;

  function reloadData () {

    $('.custom-table').DataTable().draw();
  };

  vm.render = function() {
    vm.dtInstance._renderer.rerender();
  }

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        $('td', nRow).unbind('click');
        $('td', nRow).bind('click', function() {
            $scope.$apply(function() {
                console.log(aData);
                vm.service.apiCall("get_view_order_details/", "GET", {id: $(aData[""]).attr('name'),order_id: aData["Order ID"]}).then(function(data){
                  var all_order_details = data.data.data_dict[0].ord_data;
            vm.ord_status = data.data.data_dict[0].status;

            vm.model_data = {}
            var empty_data = {data: []}
            angular.copy(empty_data, vm.model_data);

            vm.input_status = false;
            vm.order_input_status = false;

            vm.model_data["embroidery_vendor"] = data.data.data_dict[0].embroidery_vendor;
            vm.model_data["print_vendor"] = data.data.data_dict[0].print_vendor;
            vm.model_data["production_unit"] = data.data.data_dict[0].production_unit;
            vm.model_data["central_remarks"]= data.data.data_dict[0].central_remarks;
            vm.model_data["all_status"] = data.data.data_dict[0].all_status;
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
              vm.invoice_amount = value.invoice_amount;
              vm.shipment_date = value.shipment_date;
              vm.remarks = value.remarks;
              vm.cust_data = value.cus_data;
              vm.item_code = value.item_code;
              vm.order_id = value.order_id;
              vm.market_place = value.market_place;

              var image_url = value.image_url;
              vm.img_url = vm.service.check_image_url(image_url);
              console.log(vm.model_data);
              vm.model_data.data.push({item_code: vm.item_code, product_title: vm.product_title, quantity: vm.quantity, 
              invoice_amount: vm.invoice_amount, image_url: vm.img_url, remarks: vm.remarks, default_status: true})
            });
                $state.go('app.outbound.ViewOrders.CustomOrderDetails'); 
                })
            });
        });
        return nRow;
    }

    vm.model_data = {};

    vm.generate_data = [];
    vm.generate_picklist = function() {
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
          data[vm.generate_data[i]["data_value"]]= vm.generate_data[i]['Total Quantity'];
        }
        vm.service.apiCall(vm.g_data.generate_picklist_urls[vm.g_data.view], 'POST', data).then(function(data){
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
            vm.pop_msg(vm.model_data.stock_status);
            vm.reloadData();
          }
        });
        vm.generate_data = [];
      }
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

  vm.pdf_data = {};
    vm.picklist_confirmation = picklist_confirmation;
    function picklist_confirmation() {
      var elem = angular.element($('form:visible'));
      elem = $(elem).serializeArray();
      vm.service.apiCall('picklist_confirmation/', 'POST', elem).then(function(data){
        if(data.message) {
          if(data.data == "Picklist Confirmed") {
            $state.go('app.outbound.ViewOrders');
          } else if (data.data.status == 'invoice') {

              angular.copy(data.data.data, vm.pdf_data);
              $state.go('app.outbound.ViewOrders.GenerateInvoice');
          } else {
            pop_msg(data.data);
          }
        }
      });
    }

  vm.confirm_disable = false;
  vm.close = close;
    function close() {
      $state.go('app.outbound.ViewOrders');
      vm.message = "";
      vm.confirm_disable = false;
    }

  vm.message = "";
  vm.pop_msg =  function(msg) {
    vm.message = msg;
    $timeout(function () {
      vm.message = "";
    }, 3000);
  }

  vm.back_button = function() {
    vm.reloadData();
    $state.go('app.outbound.ViewOrders')
  }

  vm.status_type = ["Cleared", "Blocked"];
  vm.selected_status = '';

  vm.send_order_data = function(form) {
    var elem = angular.element($('form'));
    //elem = elem[0];
    //elem = $(elem).serializeArray();
    elem = $("form:visible").serializeArray();
    if (elem[0].value == '? string: ?'){
        elem[0].value = ''; 
    }   
    elem.push({name: 'order id', value: vm.order_id}, {name: 'customer_id', value: vm.customer_id}, 
              {name: 'customer_name', value: vm.customer_name},
              {name: 'phone', value: vm.phone}, {name: 'email', value: vm.email}, {name: 'address', value: vm.address},
              {name: 'shipment_date', value: vm.shipment_date}, {name: 'market_place', value: vm.market_place})
    vm.service.apiCall('update_order_data/', 'GET', elem).then(function(data){
        console.log(data);
        vm.reloadData();
        colFilters.showNoty('Saved sucessfully');
    })  
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

  vm.vendors = {}
  vm.service.apiCall("get_vendors_list/").then(function(data) {

    if(data.message)  {
      vm.vendors = data.data.data;
    }
  })
}
