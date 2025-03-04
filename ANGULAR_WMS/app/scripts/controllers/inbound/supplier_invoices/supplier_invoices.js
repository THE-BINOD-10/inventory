'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('SupplierInvoicesTabCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, Service, $modal) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.user_type = Session.roles.permissions.user_type;
    vm.industry_type = Session.user_profile.industry_type;

    vm.selected = {};
    vm.checked_items = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.display = false;
    vm.extra_width = {'width': '1100px'};

    var send = {'tabType': 'SupplierInvoices'};
    vm.service.apiCall("supplier_invoice_data/", "GET", send).then(function(data) {
      if(data.message) {
        vm.filters = {'datatable': 'SupplierInvoices', 'search0':'', 'search1':'', 'search2': '', 'search3': ''}
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
          .withOption('order', [5, 'desc'])
          .withOption('lengthMenu', [10, 100, 200, 300, 400, 500, 1000, 2000])
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
          .withOption('initComplete', function( settings ) {
            //vm.apply_filters.add_search_boxes("#"+vm.dtInstance.id);
          });

        var columns = data.data.headers;
        var not_sort = ['Order Quantity', 'Picked Quantity']
        vm.dtColumns = vm.service.build_colums(columns, not_sort);
        vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle('').notSortable().withOption('width', '20px')
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
        vm.display = true;
      }
    });

    vm.move_to = function (click_type) {
      var supplier_name = '';
      var status = false;
      var field_name = "";
      var data = [];
      if (vm.user_type == 'distributor') {
        data = vm.checked_ids;
      } else {
        angular.forEach(vm.selected, function(value, key) {
          if(value) {
            var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]['_aData'];
            if(!(supplier_name)) {
              supplier_name = temp['Supplier Name'];
            } else if (supplier_name != temp['Supplier Name']) {
              status = true;
            }
            field_name = temp['check_field'];
            var grn_no = temp['GRN NO'];
            if(grn_no){
              grn_no = grn_no.split('/');
            }

            if (click_type == 'cancel_inv') {
              var send_data = JSON.stringify({
                grn_no: grn_no,
                invoice_number: temp['Invoice ID'],
                seller_summary_name: supplier_name, 
                seller_summary_id: temp['id'], 
                purchase_order__order_id: temp['purchase_order__order_id'],
                receipt_number: temp['receipt_number'],
                cancel: 'true',
                warehouse_id: temp['warehouse_id']
              });
            } else {
              var send_data = JSON.stringify({
                grn_no: grn_no,
                invoice_number: temp['Invoice ID'],
                seller_summary_name: supplier_name, 
                seller_summary_id: temp['id'], 
                purchase_order__order_id: temp['purchase_order__order_id'],
                receipt_number: temp['receipt_number'],
                warehouse_id: temp['warehouse_id']
              });
            }

            data.push(send_data);
          }
        });
      }

      if(status) {
        vm.service.showNoty("Please select same "+field_name+"'s");
      } else {

        var send = data.join(",");
        send = {data: send}
        var url = 'move_to_invoice/';
        vm.bt_disable = true;
        vm.service.apiCall(url, "POST", send).then(function(data){
          if(data.message) {
            console.log(data.message);
            vm.reloadData();
          } else {
            vm.service.showNoty("Something went wrong while moving to po challan !!!");
          }
        })
      }
    };

    vm.reloadData = function () {
      $('.custom-table').DataTable().draw();
    };

    vm.pdf_data = {};

    vm.generate_invoice = function(click_type, DC='false'){

      var supplier_name = '';
      var status = false;
      var field_name = "";
      var data = [];
      var send_data = {};
      if (vm.user_type == 'distributor') {
        data = vm.checked_ids;
      } else {
        angular.forEach(vm.selected, function(value, key) {
          if(value) {
            var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]['_aData'];
            if(!(supplier_name)) {
              supplier_name = temp['Supplier Name'];
            } else if (supplier_name != temp['Supplier Name']) {
              status = true;
            }
            field_name = temp['check_field'];
            var invoice_no = temp['Invoice ID']
            var grn_no = temp['GRN NO'];
            if(grn_no){
              grn_no = grn_no.split('/');
            }

            if(supplier_name && field_name == 'Supplier Name') {
              send_data['sor_id'] = supplier_name;
            }
            if(click_type == 'edit'){
              send_data = JSON.stringify({
                grn_no: grn_no,
                invoice_number: temp['Invoice ID'],
                seller_summary_name: temp['Supplier Name'],
                seller_summary_id: temp['id'],
                purchase_order__order_id: temp['purchase_order__order_id'],
                receipt_number: temp['receipt_number'],
                data: 'true',
                edit_invoice: 'true',
                edit_poc: 'false',
                po_challan: DC,
                warehouse_id: temp['warehouse_id']
              });
            } else {
              send_data = JSON.stringify({
                grn_no: grn_no,
                invoice_number: temp['Invoice ID'],
                seller_summary_name: temp['Supplier Name'], 
                seller_summary_id: temp['id'], 
                purchase_order__order_id: temp['purchase_order__order_id'],
                receipt_number: temp['receipt_number'],
                warehouse_id: temp['warehouse_id']
              });
            }
          }
        });
      }

      if(status) {
        vm.service.showNoty("Please select same "+field_name+"'s");
      } else {

        var send = {data: send_data}
        
        vm.delivery_challan = DC;
        vm.bt_disable = true;
        vm.service.apiCall("generate_supplier_invoice/", "GET", send).then(function(data){

          if(data.message) {
            if(click_type == 'generate') {
              vm.pdf_data = data.data;
              if(typeof(vm.pdf_data) == "string" && vm.pdf_data.search("print-invoice") != -1) {
                $state.go("app.inbound.SupplierInvoice.InvoiceE");
                $timeout(function () {
                  $(".modal-body:visible").html(vm.pdf_data)
                }, 3000);
              // } else if(Session.user_profile.user_type == "marketplace_user") {
              //   $state.go("app.inbound.SupplierInvoices.InvoiceM");
              // } else if(vm.permissions.detailed_invoice) {
              //   $state.go("app.inbound.SupplierInvoices.InvoiceD");
              } else {
                $state.go("app.inbound.SupplierInvoice.InvoiceN");
              }
            } else {
              var mod_data = data.data;
              var modalInstance = $modal.open({
              templateUrl: 'views/inbound/toggle/edit_supplier_invoice.html',
              controller: 'EditInvoice',
              controllerAs: 'pop',
              size: 'lg',
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
                vm.reloadData();
              })
            }
          }
          vm.bt_disable = false;
        });
      }
    }
  vm.close = function() {
    $state.go("app.inbound.SupplierInvoice")
  };

}

function EditInvoice($scope, $http, $q, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {

  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  vm.priceband_sync = Session.roles.permissions.priceband_sync;
  vm.date = new Date();

  vm.model_data = items;
  
  vm.model_data.supplier_id = vm.model_data.supplier_details.id;
  vm.model_data['order_charges'] = [];
  vm.model_data.temp_sequence_number = vm.model_data.sequence_number;

  var empty_data = {data: [{sku_code: "", title: "", unit_price: "", quantity: "", base_price: "",
              discount: "", amt: "", invoice_amount: "", discount_percentage: "",
              discount: "", price: "", tax: "", total_amount: "",
                            location: "", serials: [], serial: "", capacity: 0
                          }],
                    customer_id: "", payment_received: "", order_taken_by: "", other_charges: [],  shipment_time_slot: "",
                    tax_type: "", blind_order: false, mode_of_transport: ""};

  vm.fields = Session.roles.permissions["order_headers"];
  vm.model_data.default_charge = function(){

    if (vm.model_data.order_charges.length == 1) {

      vm.model_data.flag = true;
    }
  }

  vm.delete_charge = function(id){

    if (id) {

      vm.service.apiCall("delete_order_charges?id="+id, "GET").then(function(data){

        if(data.message){

          Service.showNoty(data.data.message);
        }
      });
    }
  }

  $timeout(function() {

    $('[name="inv_date"]').datepicker("setDate", new Date(vm.model_data.inv_date) );
  },1000);
  vm.ok = function () {

    $modalInstance.close("close");
  };

  vm.process = false;
  vm.save = function(form_data) {

    if (vm.permissions.increment_invoice && vm.model_data.invoice_date && form_data.invoice_no.$invalid) {

      Service.showNoty("Please Fill Invoice Number");
      return false;
    } else if (!form_data.$valid) {

      Service.showNoty("Please Fill the Mandatory Fields");
      return false;
    }

    var update_edit_invoice_data = {};
    update_edit_invoice_data.form_data = {
      'invoice_no': form_data.invoice_no.$modelValue,
      'invoice_date': form_data.invoice_date.$modelValue,
      'address': form_data.address.$modelValue,
      'order_id': form_data.order_id.$modelValue,
      'supplier_id': form_data.supplier_id.$modelValue,
    };

    angular.forEach(vm.removed_data, function(data){
      vm.model_data.data.push(data);
    });
    update_edit_invoice_data.data = JSON.stringify(vm.model_data.data);
    update_edit_invoice_data.order_charges = JSON.stringify(vm.model_data.order_charges);

    vm.process = true;
    // var data = $("form").serializeArray()
    Service.apiCall("update_po_invoice/", "POST", update_edit_invoice_data).then(function(data) {

      if(data.message) {

        if(data.data.message == 'success') {

          Service.showNoty("Updated Successfully");
          $modalInstance.close("saved");
        } else {

          Service.showNoty(data.data.message);
        }
      } else {

        Service.showNoty("Update fail");
      }
      vm.process = false;
    })
  }

  vm.changeUnitPrice = function(data) {

    data.base_price = data.quantity * Number(data.unit_price);
    // data.discount = (data.base_price/100)*Number(data.discount_percentage);
    // data.amt = data.base_price - data.discount;
    var taxes = {cgst_amt: 'cgst_tax', sgst_amt: 'sgst_tax', igst_amt: 'igst_tax', utgst_amt: 'utgst_tax'};
    data.tax = 0;

    angular.forEach(taxes, function(tax_name, tax_amount){

      if (data.taxes[tax_name] > 0){

        data.taxes[tax_amount] = (data.base_price/100)*data.taxes[tax_name];
      } else {

        data.taxes[tax_amount] = 0;
      }
       data.tax += data.taxes[tax_amount];
    })
    data.invoice_amount = (data.base_price + data.tax);
  }

  angular.forEach(vm.model_data.data, function(sku){
    vm.changeUnitPrice(sku);
  });

  vm.isLast = isLast;
  function isLast(check) {

    var cssClass = check ? "fa fa-plus-square-o" : "fa fa-minus-square-o";
    return cssClass
  }

  vm.removed_data = [];
  vm.update_data = update_data;
  function update_data(index, data, last) {
    
    if (last && (!vm.model_data.data[index].sku_code)) {
      return false;
    }
    if (last) {
    var temp = vm.model_data.data[0];
    // temp.amt = temp.base_price = temp.discount = temp.id = temp.invoice_amount = temp.sku_code = temp.sku_size = temp.tax = temp.title = temp.unit_price = "";
    var empty_data = {
      'amt':0, 'base_price':"0.00", 'discount':0, 'discount_percentage':0, 'hsn_code':"", 'id':"", 'imeis':[], 'invoice_amount':"",
      'mrp_price':"", 'order_id':"", 'quantity':0, 'shipment_date':"", 'sku_category':"", 'sku_class':"", 'sku_code':"",
      'sku_size':"", 'tax':"0.00", 'tax_type':"", 'title':"", 'unit_price':"0.00", 'vat':0 }

    empty_data["order_id"] = temp["order_id"];
    empty_data["shipment_date"] = temp["shipment_date"];
    empty_data["new_sku"] = true;
    empty_data["taxes"] = temp["taxes"];
    vm.model_data.data.push(empty_data);
    } else {
    var del_sku = vm.model_data.data[index];
      // if(!del_sku.new_sku) {
      //   Service.apiCall("remove_sku/", "POST", del_sku).then(function(data) {
      //     console.log(data);
      //   });
      // }

      vm.model_data.data[index].quantity = 0;
      vm.removed_data.push(vm.model_data.data[index]);
      vm.model_data.data.splice(index,1);
      vm.cal_total();
    }
  }

  vm.change_quantity = function(data) {

    var flag = false;
    if(data.priceRanges && data.priceRanges.length > 0) {

      for(var skuRec = 0; skuRec < data.priceRanges.length; skuRec++){
    
        if(data.quantity >= data.priceRanges[skuRec].min_unit_range && data.quantity <= data.priceRanges[skuRec].max_unit_range){
    
          data.unit_price = data.priceRanges[skuRec].price;
          flag = true;
        }
      }

      if (!flag) {
    
        data.unit_price = data.priceRanges[data.priceRanges.length-1].price;
      }
    }

    data.base_price = vm.service.multi(data.quantity, data.unit_price);
    // vm.cal_percentage(data);
    vm.vm.changeUnitPrice(data);
  }

  vm.get_customer_sku_prices = function(sku) {

    var d = $q.defer();
    var tax_dict = {0:"intra_state", 1:"inter_state", 2:"default"};
    var data = {sku_codes: sku, cust_id: vm.model_data.customer_id, tax_type: tax_dict[vm.model_data.tax_type]}
    vm.service.apiCall("get_customer_sku_prices/", "POST", data).then(function(data) {

      if(data.message) {
        d.resolve(data.data);
      }
    });
    return d.promise;
  }

  vm.get_tax_value = function(data) {

    var tax_perc = 0;
    // data.sgst_tax = 0;
    // data.cgst_tax = 0;
    // data.igst_tax = 0;
    // data.taxes = {"cgst_amt": "", "cgst_tax": 0, "sgst_amt": "", "sgst_tax": 0, "igst_amt": "", "igst_tax": 0};
    if (data.taxes_data) {
      for(var i = 0; i < data.taxes_data.length; i++) {

        if(data.unit_price <= data.taxes_data[i].max_amt && data.unit_price >= data.taxes_data[i].min_amt) {

          if(vm.model_data.tax_type == "0") {//intra_state

            tax_perc = data.taxes_data[i].sgst_tax + data.taxes_data[i].cgst_tax;
            data.sgst_tax = data.taxes_data[i].sgst_tax;
            data.cgst_tax = data.taxes_data[i].cgst_tax;
            data.taxes.sgst_tax = data.sgst_tax;
            data.taxes.cgst_tax = data.cgst_tax;
          } else if (vm.model_data.tax_type == "1") {//inter_state

            data.igst_tax = data.taxes_data[i].igst_tax;
            tax_perc = data.taxes_data[i].igst_tax;
            data.taxes.igst_tax = data.igst_tax;
          }
          data.taxes.cgst_amt = (data.amt * data.cgst_tax)/100;
          data.taxes.sgst_amt = (data.amt * data.sgst_tax)/100;
          data.taxes.igst_amt = (data.amt * data.igst_tax)/ 100;
          break;
        }
      }
    }
    /*tax_perc = data.taxes.sgst_tax + data.taxes.cgst_tax + data.taxes.igst_tax;
    data.taxes.sgst_amt = (data.unit_price * data.taxes.sgst_tax / 100) * data.quantity;
    data.taxes.cgst_amt = (data.unit_price * data.taxes.cgst_tax / 100) * data.quantity;
    data.taxes.igst_amt = (data.unit_price * data.taxes.igst_tax / 100) * data.quantity;*/
    data.tax = tax_perc;
    return tax_perc;
  }

  vm.final_data = {total_quantity:0,total_amount:0}
  vm.cal_total = function() {

    vm.final_data.total_quantity = 0;
    vm.final_data.total_amount = 0;
    angular.forEach(vm.model_data.data, function(record){
      vm.final_data.total_amount += Number(record.total_amount);
      vm.final_data.total_quantity += Number(record.quantity);
    })
    if(vm.model_data.other_charges) {
      angular.forEach(vm.model_data.other_charges, function(record){
        if(record.amount){
          vm.final_data.total_amount += Number(record.amount);
        }
      })
    }
  }

  vm.discountChange = function(data) {

    vm.cal_percentage(data, false); 
  }

  vm.discountPercentageChange = function(data, status) {

    if(vm.fields.indexOf('Discount Percentage') != -1) {
      return false;
    }
    if(!data.discount_percentage) {
      data.discount_percentage = "";
    }
    var temp_perc = Number(data.discount_percentage);
    data.discount = (Number(data.invoice_amount)*temp_perc)/100;
  }


  vm.cal_percentage = function(data, no_total) {

    vm.discountPercentageChange(data, false);
    data.amt = data.base_price - data.discount;
    vm.get_tax_value(data);
    var per = Number(data.tax);
    data.invoice_amount = ((Number(data.base_price - Number(data.discount))/100)*per)+(Number(data.base_price)-Number(data.discount));

    if(!no_total) {
      vm.cal_total();
    }
  }

  function check_exist(sku_data, index) {

    for(var i = 0; i < vm.model_data.data.length; i++) {

      if((vm.model_data.data[i].sku_code == sku_data.sku_code) && (index != i)) {

        sku_data.sku_code = "";
        vm.service.showNoty("It is already exist in index");
        return false;
      }
    }
    return true;
  }

  vm.get_sku_data = function(record, item, index) {

    record.sku_code = item.wms_code;
  record["title"] = item.sku_desc;
  //record.unit_price = item.
    if(!vm.model_data.blind_order && !(check_exist(record, index))){
      return false;
    }
    //angular.copy(empty_data.data[0], record);
    record.sku_code = item.wms_code;
    record["title"] = item.sku_desc;

    vm.get_customer_sku_prices(item.wms_code).then(function(data){
      if(data.length > 0) {
        data = data[0]
        record["unit_price"] = data.price;
        //record["description"] = data.sku_desc;
        if (! vm.model_data.blind_order) {
          if(!(record.quantity)) {
            record.quantity = 1
          }
        }
        record["taxes_data"] = data.taxes;
    record["base_price"] = Number(record.unit_price)*Number(record.quantity);
    record["discount"] = data.discount;
    record["amt"] = record["base_price"] - record["discount"];
        //record.invoice_amount = Number(record.price)*Number(record.quantity);
        record["priceRanges"] = data.price_bands_map;
        vm.cal_percentage(record);
      }
    })
  }

}
stockone = angular.module('urbanApp');

stockone.controller('EditInvoice', ['$scope', '$http', '$q', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', EditInvoice]);

// stockone.directive('genericCustomerInvoiceData', function() {
//   return {
//     restrict: 'E',
//     scope: {
//       invoice_data: '=data',
//     },
//     templateUrl: 'views/outbound/toggle/invoice_data_html.html',
//     link: function(scope, element, attributes, $http, Service){
//       console.log(scope);
//     }
//   };
// });
