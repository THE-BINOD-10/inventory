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
    vm.collect_imei_data = {}
    vm.get_id = ''
    vm.record_serial_data = []
    vm.industry_type = Session.user_profile.industry_type;
    vm.user_type = Session.user_profile.user_type;
  
    function getOS() {
      var userAgent = window.navigator.userAgent,
          platform = window.navigator.platform,
          macosPlatforms = ['Macintosh', 'MacIntel', 'MacPPC', 'Mac68K'],
          windowsPlatforms = ['Win32', 'Win64', 'Windows', 'WinCE'],
          iosPlatforms = ['iPhone', 'iPad', 'iPod'],
          os = null;

      if (macosPlatforms.indexOf(platform) !== -1) {
        os = 'Mac OS';
      } else if (iosPlatforms.indexOf(platform) !== -1) {
        os = 'iOS';
      } else if (windowsPlatforms.indexOf(platform) !== -1) {
        os = 'Windows';
      } else if (/Android/.test(userAgent)) {
        os = 'Android';
      } else if (!os && /Linux/.test(platform)) {
        os = 'Linux';
      }

      return os;
    }

    vm.date_format_convert = function(utc_date){

      var os_type = getOS();

      var date = utc_date.toLocaleDateString();
      var datearray = date.split("/");

      if (os_type == 'Windows') {

        if (datearray[1] < 10 && datearray[1].length == 1) {
          datearray[1] = '0'+datearray[1];
        }

        if (datearray[0] < 10 && datearray[0].length == 1) {
          datearray[0] = '0'+datearray[0];
        }

        vm.date = datearray[0] + '/' + datearray[1] + '/' + datearray[2];
      } else {

        vm.date = datearray[1] + '/' + datearray[0] + '/' + datearray[2];
      }
    }

    vm.date_format_convert(new Date());

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
            DTColumnBuilder.newColumn('Quantity').withTitle('Quantity')
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
            DTColumnBuilder.newColumn('Creation Date').withTitle('Creation Date'),
            DTColumnBuilder.newColumn('Quantity').withTitle('Quantity')
        ];
      }
    }

    vm.changeDtFields(false);

    vm.dtInstance = {};
    vm.reloadData = reloadData;

    vm.checkDateValidation = function(){

      var from_date = new Date(vm.model_data.filters.from_date);
      var to_date = new Date(vm.model_data.filters.to_date);
      if (from_date > to_date) {

        colFilters.showNoty('Pease select proper date combination');
        vm.model_data.filters.to_date = '';
      }
    }

    function reloadData () {
        vm.dtInstance.reloadData();
    };

    vm.excel = excel;
    function excel() {
      angular.copy(vm.dtColumns,colFilters.headers);
      angular.copy(vm.dtInstance.DataTable.context[0].ajax.data, colFilters.search);
      colFilters.download_excel()
    }

    vm.filtersData = function(){

      if (!vm.model_data.filters) {

        vm.model_data['filters'] = {};
      }

      if (!(vm.model_data.filters['from_date'])) {

        vm.model_data.filters['from_date'] = vm.date;
      }
      vm.model_data.filters['order_id'] = vm.order_id;
      // vm.model_data.filters['to_date'] = '';
    }

    vm.get_order_data = function(params){

      var url = "get_stock_transfer_order_details/";

      vm.service.apiCall(url, "GET", params).then(function(data){

        vm.items_dict = data.data.data_dict;
        vm.order_id = data.data.data_dict[0].order_id;
        vm.customer_name = data.data.wh_details.name;
        vm.address = data.data.wh_details.address;
        vm.city = data.data.wh_details.city;
        vm.state = data.data.wh_details.state;
        vm.creation_date = data.data.order_date;
        vm.pin = data.data.wh_details.pincode;

        angular.forEach(vm.items_dict, function(item){

          item['default_status'] = true;
        });

        vm.filtersData();
      });
    }

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {

    vm.ord_status = '';

    $('td:not(td:first)', nRow).unbind('click');
    $('td:not(td:first)', nRow).bind('click', function() {

        $scope.$apply(function() {

          var data = {order_id: aData['Stock Transfer ID']};
          $state.go('app.outbound.ViewOrders.StockTransferAltView');

          vm.get_order_data(data);

       })
     })
   }

    vm.send_order_data = function(form) {
      // var elem = angular.element($('item_form'));
      // elem = elem[0];
      // elem = $(elem).serializeArray();
      var elem = [];

      elem.push({name: 'order_id', value: vm.order_id}, /*{name: 'customer_id', value: vm.customer_id},*/
                {name: 'customer_name', value: vm.customer_name}, {name: 'city', value: vm.city},
                {name: 'address', value: vm.address}, {name: 'state', value: vm.state}, {name: 'pincode', value: vm.pin},
                {name: 'creation_date', value: vm.creation_date});

      angular.forEach(vm.items_dict, function(item){

        elem.push({name: 'closing_stock', value: item.closing_stock},
                {name: 'consumed', value: item.consumed}, {name: 'invoice_amount', value: item.invoice_amount},
                {name: 'item_code', value: item.item_code}, {name: 'opening_stock', value: item.opening_stock},
                {name: 'product_title', value: item.product_title}, {name: 'quantity', value: item.quantity},
                {name: 'received', value: item.received}, {name: 'total_stock', value: item.total_stock},
                {name: 'unit_price', value: item.unit_price}, {name: 'adjusted', value: item.adjusted});
      });

      vm.service.apiCall('update_stock_transfer_data/', 'POST', elem).then(function(data){
        if (data.message) {

          vm.back_button();
          colFilters.showNoty('Saved sucessfully');
        }
      })
    }

    vm.delete_order_data = function(ord_id) {

      var delete_data = {};
      delete_data['order_id'] = ord_id;
      // delete_data['order_id_code'] = vm.order_id_code;

      vm.service.apiCall('stock_transfer_delete/', 'GET', delete_data).then(function(data){

          if (data.message) {

            colFilters.showNoty(data.data);
            vm.reloadData();
            $state.go('app.outbound.ViewOrders');
          }
      })
    }

   vm.update_order_details = update_order_details;
    function update_order_details(index, data, last) {
      vm.default_status = false;
      if (last) {
        if (!vm.model_data.data) {
          vm.model_data['data'] = [];
        }

        vm.model_data.data.push({item_code:'', product_title:'', quantity:0, unit_price:0, invoice_amount:0,
          opening_stock: '', order_id: vm.order_id, received: '', total_stock: '', adjusted: '', consumed: '', closing: '', new_product:true,
          default_status: false, sku_status: 1});
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

    vm.changeInvoiceAmt = function(data, flag){

      if (!data.discount_per) {

        data['discount_per'] = 0;
      }

      var total = (data.quantity * data.unit_price);
      var discount_amt = (total*data.discount_per)/100;
      var invoice_amount_dis = Number(total - discount_amt);

      /*if (flag) { // Used to execute taxes for unitprice change only
        if (data.taxes.length) {
          for (var i = 0; i < data.taxes.length; i++) {

            if (data.unit_price >= data.taxes[i].min_amt && data.unit_price <= data.taxes[i].max_amt) {
              data.igst = data.taxes[i].igst_tax;
              data.cgst = data.taxes[i].cgst_tax;
              data.sgst = data.taxes[i].sgst_tax;
              break;
            }
          }
        } else {
          data.igst = 0;
          data.cgst = 0;
          data.sgst = 0;
        }
      }*/
      // Taxes initial declaration for tempararly
      data.igst = 0;
      data.cgst = 0;
      data.sgst = 0;
      var tax = Number(data.sgst)+Number(data.cgst)+Number(data.igst);

      data.discount = discount_amt;
      data.invoice_amount = (invoice_amount_dis + (invoice_amount_dis*tax)/100);
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
      for(var key in vm.selected) {
        console.log(vm.selected[key]);
        if(vm.selected[key]) {
          vm.generate_data.push(vm.dtInstance.DataTable.context[0].aoData[key]._aData);
        }
      }
      if(vm.generate_data.length > 0) {
        console.log(vm.generate_data);
        var data = {};
        for(var i=0;i<vm.generate_data.length;i++) {
          // data[vm.generate_data[i]['Stock Transfer ID']+":"+vm.generate_data[i]['SKU Code']]= vm.generate_data[i].DT_RowAttr.id;
          data[vm.generate_data[i].DT_RowAttr.id] = vm.generate_data[i]['Stock Transfer ID'];
        }

        var url = 'st_generate_picklist/';
        if (vm.alt_view) {
          url = 'stock_transfer_generate_picklist/';
        }

        vm.service.apiCall(url, 'POST', data, true).then(function(data){
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

  vm.increament = function (record) {
      record.scan = record.scan.toUpperCase()
      record.picked_quantity = parseInt(record.picked_quantity) + 1;
      vm.record_serial_data.shift()
      if(vm.collect_imei_data.hasOwnProperty(vm.get_id)) {
        vm.collect_imei_data[vm.get_id].push(record.scan)
      } else {
        vm.collect_imei_data[vm.get_id] = []
        vm.collect_imei_data[vm.get_id].push(record.scan)
      }
      $("input[name=imei_"+vm.get_id+"]").prop('value', String(vm.collect_imei_data[vm.get_id]))
      record.scan = '';
    }

	  vm.getrecordSerialnumber = function(rowdata) {
      for(var i=0; i < vm.model_data.data.length; i++) {
        if(vm.model_data.data[i].wms_code == rowdata.wms_code) {
          if(!vm.model_data.data[i].hasOwnProperty('sku_imeis_map')) {
            return false
          }
          if (vm.model_data.data[i]['sku_imeis_map'].hasOwnProperty(vm.model_data.data[i].wms_code)) {
            angular.copy(vm.model_data.data[i]['sku_imeis_map'][vm.model_data.data[i].wms_code].sort(), vm.record_serial_data);
          }
        }
      }
      vm.record_serial_data = $.map(vm.record_serial_data, function(n,i){return n.toUpperCase();});
      return true
    }

    vm.serial_scan = function(event, scan, data, record) {
      if (event.keyCode == 13) {
        scan = scan.toUpperCase();
        var resp_data = vm.getrecordSerialnumber(data);
        if (!resp_data) {
          vm.service.showNoty("Serial Number Not Available For this SKU");
          record.scan = '';
          return false
        }

      if(vm.collect_imei_data.hasOwnProperty(data.id)) {
        if ($.inArray(scan, vm.collect_imei_data[data.id]) != -1) {
          vm.service.showNoty("Serial Number Already Scanned");
          record.scan = '';
          return false
        }
      }
        vm.get_id = data.id
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
          if(data.data.status == "Success") {
      			vm.increament(record);
		      } else {
            Service.pop_msg(data.data.status);
            record.scan = '';
          }
          });
        } else {
          scan_data.splice(length-1,1);
          record.scan = scan_data.join('\n');
          record.scan = record.scan+"\n";
          vm.service.showNoty("picked already equal to reserved quantity !");
          record.scan = '';
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
