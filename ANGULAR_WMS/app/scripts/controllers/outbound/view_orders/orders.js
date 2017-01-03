'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('Orders',['$scope', '$http', '$state', '$compile', '$timeout', 'Session', 'DTOptionsBuilder', 'DTColumnBuilder', 'colFilters', 'Service', '$q', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, colFilters, Service, $q) {
    var vm = this;
    $state.go($state.current, {}, {reload: true});
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.apply_filters = colFilters;
    vm.selected = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.special_key = {market_places: "", customer_id: ""}
  if (Session.roles.permissions.batch_switch) {
    vm.filters = {'datatable': 'ViewOrdersB', 'search0':'', 'search1':'', 'search2': '', 'special_key': JSON.stringify(vm.special_key)}
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
       .withOption('lengthMenu', [100, 200, 300, 400, 500])
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

    vm.dtColumns = [
        DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
                if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                  vm.selected = {};
                }
                vm.selected[meta.row] = vm.selectAll;
                vm.seleted_rows.push(full);
                return vm.service.frontHtml + meta.row + vm.service.endHtml;
            }).notSortable(),
        DTColumnBuilder.newColumn('sku_code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('title').withTitle('Title'),
        DTColumnBuilder.newColumn('total_quantity').withTitle('Total Quantity')
    ];
  } else {

    vm.filters = {'datatable': 'ViewOrders', 'search0':'', 'search1':'', 'search2': '' , 'search3': '' , 'search4': '' , 'special_key': JSON.stringify(vm.special_key)}
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
       .withOption('lengthMenu', [100, 200, 300, 400, 500])
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

    vm.dtColumns = [
        DTColumnBuilder.newColumn(null).withTitle(vm.service.titleHtml).notSortable().withOption('width', '20px')
            .renderWith(function(data, type, full, meta) {
                if( 1 == vm.dtInstance.DataTable.context[0].aoData.length) {
                  vm.selected = {};
                }
                vm.selected[meta.row] = vm.selectAll;
                vm.seleted_rows.push(full);
                return vm.service.frontHtml + meta.row + vm.service.endHtml;
            }).notSortable(),
        DTColumnBuilder.newColumn('Order ID').withTitle('Order ID'),
        DTColumnBuilder.newColumn('SKU Code').withTitle('SKU Code'),
        DTColumnBuilder.newColumn('Title').withTitle('Title'),
        DTColumnBuilder.newColumn('Product Quantity').withTitle('Product Quantity'),
        DTColumnBuilder.newColumn('Shipment Date').withTitle('Shipment Date'),
        DTColumnBuilder.newColumn('Marketplace').withTitle('Marketplace')
    ];

   function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {

     $('td:not(td:first)', nRow).unbind('click');
     $('td:not(td:first)', nRow).bind('click', function() {
       
       $scope.$apply(function() {
	
	 console.log(aData);
         $state.go('app.outbound.ViewOrders.OrderDetails'); 
	 vm.service.apiCall("get_view_order_details/", "GET", {order_id: $(aData[""]).attr('name')}).then(function(data){
	  
	   vm.customer_id = data.data.data_dict[0].cust_id;
	   vm.customer_name = data.data.data_dict[0].cust_name;
	   vm.phone = data.data.data_dict[0].phone;
	   vm.email = data.data.data_dict[0].email;
	   vm.address = data.data.data_dict[0].address;
	   vm.city = data.data.data_dict[0].city;
	   vm.state = data.data.data_dict[0].state;
	   vm.pin = data.data.data_dict[0].pin;
	   vm.product_title = data.data.data_dict[0].product_title;
	   vm.quantity = data.data.data_dict[0].quantity;
	   vm.invoice_amount = data.data.data_dict[0].invoice_amount;
	   vm.shipment_date = data.data.data_dict[0].shipment_date;
	   vm.remarks = data.data.data_dict[0].remarks;
	   vm.cust_data = data.data.data_dict[0].cus_data;
	   vm.item_code = data.data.data_dict[0].item_code;
	   vm.order_id = data.data.data_dict[0].order_id;
	   var image_url = data.data.data_dict[0].image_url;
	   vm.img_url = vm.service.check_image_url(image_url);
	   var custom_data = data.data.data_dict[0].customization_data;
	   if (custom_data.length === 0){

	     vm.customization_data = '';
	   }
	   else {
	
	     var img_url = custom_data[0][3];
	     vm.img_url = vm.service.check_image_url(img_url)	
	   }
	 });
       })
     })
   }

  }
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

    $scope.$on('change_filters_data', function(){
      vm.dtInstance.DataTable.context[0].ajax.data[colFilters.label] = colFilters.value;
      vm.reloadData();
    });

    function rowCallback(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
        /*if(vm.filter_enable){
          vm.filter_enable = false;
          vm.apply_filters.add_search_boxes();
        }*/
        return nRow;
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
    }

    vm.generate = generate;
    function generate() {
      if(vm.permissions.batch_switch){
        batch_generate_picklist();
      } else {
        generate_picklist();
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
        vm.service.print_data(data.data);
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
      for(var key in vm.selected){
        if(vm.selected[key]) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]._aData
          data.push({name: 'id', value: $(temp[""]).attr("name")})
        }
      }
      Service.apiCall("generate_order_jo_data/", "POST", data).then(function(data){
        if(data.message) {

          angular.copy(data.data, vm.model_data);
          angular.forEach(vm.model_data.data, function(temp){
            if(temp.sub_data.length == 0) {
              temp["sub_data"] = [{material_code: "", material_quantity: ""}];
            }
          });
          $state.go("app.outbound.ViewOrders.JO");
        };
      });
      data = [];
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

  /* raise po */
  vm.backorder_po = function() {
      var data = [];
      for(var key in vm.selected){
        if(vm.selected[key]) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]._aData
          data.push({name: 'id', value: $(temp[""]).attr("name")})
        }
      }
      Service.apiCall("generate_order_po_data/", "POST", data).then(function(data){
        if(data.message) {

          angular.copy(data.data, vm.model_data)
          $state.go("app.outbound.ViewOrders.PO");
        };
      });
  }

  vm.confirm_po = function() {
      var elem = $(form).serializeArray();

      Service.apiCall("confirm_back_order/", "POST", elem).then(function(data){
        if(data.message) {vm.confirm_disable = true; vm.message = data.data; reloadData();};
      });
    }

  vm.raise_stock_transfer = function() {

    var data = []
    for(var key in vm.selected){
      if(vm.selected[key]) {
        var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]._aData
        data.push({wms_code: temp['SKU Code'], order_quantity: 1, price: 0})
      }
    }
    Service.stock_transfer = JSON.stringify(data)
    $state.go('app.outbound.ViewOrders.ST')
  }

  }

