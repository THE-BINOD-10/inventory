'use strict';

angular.module('urbanApp', ['datatables'])
  .controller('StockTransferInvoiceCtrl',['$scope', '$http', '$state', '$compile', '$timeout', 'Session','DTOptionsBuilder', 'DTColumnBuilder', 'DTColumnDefBuilder', 'colFilters', 'Service', '$modal', ServerSideProcessingCtrl]);

function ServerSideProcessingCtrl($scope, $http, $state, $compile, $timeout, Session, DTOptionsBuilder, DTColumnBuilder, DTColumnDefBuilder, colFilters, Service, $modal) {

    var vm = this;
    vm.apply_filters = colFilters;
    vm.service = Service;
    vm.permissions = Session.roles.permissions;
    vm.user_type = Session.roles.permissions.user_type;

    vm.selected = {};
    vm.selectedRows = {};
    vm.checked_items = {};
    vm.selectAll = false;
    vm.bt_disable = true;
    vm.display = false;
    var titleHtml = '<input type="checkbox" class="data-select" ng-model="showCase.selectAll" ng-change="showCase.bt_disable = showCase.toggleAll(showCase.selectAll, showCase.selected); $event.stopPropagation();">';

    vm.service.apiCall("stock_transfer_invoice_data/").then(function(data) {
        if(data.message) {
          vm.filters = {'datatable': 'StockTransferInvoice', 'search0':'', 'search1':'', 'search2': '', 'search3': ''}
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
          var row_click_bind = 'td';
          vm.dtColumns.unshift(DTColumnBuilder.newColumn(null).withTitle().notSortable().withOption('width', '20px')
                 .renderWith(function(data, type, full, meta) {
                   //vm.selected[meta.row] = vm.selectAll;
				   vm.selected[meta.row] = false;
                   vm.selectedRows[meta.row] = full;
                   var titleHtml = '<input type="checkbox" class="data-select" ng-model="showCase.selected['+meta.row+']" ng-change="showCase.toggleOnes(showCase.selected);$event.stopPropagation();"/>'
				   return titleHtml
                 }).notSortable())
          row_click_bind = 'td:not(td:first)';
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

    vm.checked_ids = [];
    vm.checkedItem = function(data, index){
      if (vm.checked_items[index]) {
        delete vm.checked_items[index];
      } else {
        vm.checked_items[index] = data;
        vm.checked_ids.push(vm.checked_items[index].id);
      }
      // vm.checked_items[index] = data;
      console.log(data)
    }

    vm.generateInvoice = function(){
      console.log("Checked Items::", vm.checked_items);
      var data = [];
      angular.forEach(vm.checked_items, function(row){
        data.push(row['id']);
      });
      var ids = data.join("<<>>");
      var send = {seller_summary_id: ids};
      vm.service.apiCall("generate_customer_invoice/", "GET", send).then(function(data){

        if (data.message) {
          console.log(data);
          if(data.message) {
          vm.pdf_data = data.data;
          if(typeof(vm.pdf_data) == "string" && vm.pdf_data.search("print-invoice") != -1) {
            $state.go("app.outbound.CustomerInvoices.InvoiceE");
            $timeout(function () {
              $(".modal-body:visible").html(vm.pdf_data)
            }, 3000);
          } else if(Session.user_profile.user_type == "marketplace_user") {
            $state.go("app.outbound.CustomerInvoices.InvoiceM");
          } else if(vm.permissions.detailed_invoice) {
            $state.go("app.outbound.CustomerInvoices.InvoiceD");
          } else {
            $state.go("app.outbound.CustomerInvoices.InvoiceN");
          }
          }
          vm.service.showNoty("Invoice generated");
        }
      });
    }

    vm.addRowData = function(event, data) {
      vm.checked_items = {};
      console.log(data);
      var elem = event.target;
      if (!$(elem).hasClass('fa')) {
        return false;
      }
      var data_tr = angular.element(elem).parent().parent();
      var all_tr = angular.element(elem).parent().parent().siblings();

      for (var i = 0; i < all_tr.length; i++) {

        if (all_tr[i].cells[0].children[0].className == 'fa fa-minus-square') {

          all_tr[i].cells[0].children[0].className = 'fa fa-plus-square'
          all_tr[i].nextSibling.remove();
        }
      }

      if ($(elem).hasClass('fa-plus-square')) {
        $(elem).removeClass('fa-plus-square');
        $(elem).removeClass();
        $(elem).addClass('glyphicon glyphicon-refresh glyphicon-refresh-animate');
        Service.apiCall('get_invoice_details/?gen_id='+data['Gen Order Id']+'&customer_id='+data['Customer ID']).then(function(resp){
          if (resp.message){

            if(resp.data.status) {
              // var html = $compile("<tr class='row-expansion' style='display: none'><td colspan='11'><dt-po-data data='"+JSON.stringify(resp.data.data_dict)+"'></dt-po-data></td></tr>")($scope);
              var html = $compile("<tr class='row-expansion' style='display: none'><td colspan='11'><generic-customer-invoice-data data='"+JSON.stringify(resp.data.data_dict)+"'></generic-customer-invoice-data></td></tr>")($scope);
              data_tr.after(html)
              data_tr.next().toggle(1000);
              $(elem).removeClass();
              $(elem).addClass('fa fa-minus-square');
            } else {
              vm.poDataNotFound();
            }
          } else {
            vm.poDataNotFound();
          }
        })
      } else {
        $(elem).removeClass('fa-minus-square');
        $(elem).addClass('fa-plus-square');
        data_tr.next().remove();
      }
    }

    vm.close = function() {
    if(vm.permissions.customer_dc){
       $state.go("app.outbound.CustomerInvoices")
    } else{
        $state.go("app.outbound.CustomerInvoicesMain")
    }
    }

    vm.edit_invoice = function() {

      var data = [];
      angular.forEach(vm.selected, function(value, key) {
        if(value) {
          var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]['_aData'];
          data.push(temp['id']);
        }
      });
      var ids = data.join("<<>>");
      var send = {seller_summary_id: ids, data: true};
      vm.service.apiCall("generate_customer_invoice/", "GET", send).then(function(data){

        if (data.message) {
        var mod_data = data.data;
        var modalInstance = $modal.open({
          templateUrl: 'views/outbound/toggle/edit_invoice.html',
          controller: 'EditInvoice',
          controllerAs: 'pop',
          size: 'md',
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
        })
        }
      })
    }

    vm.delivery_challan = false;
	vm.toggleAlls = toggleAlls;
    function toggleAlls (selectAll, selectedItems, event) {
        for (var id in selectedItems) {
            if (selectedItems.hasOwnProperty(id)) {
                selectedItems[id] = selectAll;
            }
        }
        vm.button_fun();
    }

    vm.toggleOnes = toggleOnes;
    function toggleOnes (selectedItems) {
        for (var id in selectedItems) {
            if (selectedItems.hasOwnProperty(id)) {
                if(!selectedItems[id]) {
                    vm.selectAll = false;
                    vm.button_fun();
                    return;
                }
            }
        }
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

    vm.pdf_data = {};
    vm.generate_invoice = function(click_type, DC=false) {
      var po_number = '';
      var status = false;
      var field_name = "";
      var checkbox_valid = []
      var inv_check = []
      var data_dict = {}
  	  var key = 0
      var flag = 1
  	  angular.forEach(vm.selected, function(obj, idx) {
    		if (obj) {
    		  var temp = vm.dtInstance.DataTable.context[0].aoData[parseInt(idx)]['_aData']['Stock Transfer ID'];
    		  var invoice = vm.dtInstance.DataTable.context[0].aoData[parseInt(idx)]['_aData']['Invoice Number'];
    		  var pick_number = vm.dtInstance.DataTable.context[0].aoData[parseInt(idx)]['_aData']['pick_number'];
    		  if(checkbox_valid.length < 1){
    		      checkbox_valid.push(temp)
    		      inv_check.push(invoice)
    		      data_dict['order_id'] =temp
                  data_dict['pick_number'] = [pick_number]
    		  } else {
    		      if(checkbox_valid.indexOf(temp) == -1 || inv_check.indexOf(invoice) == -1){
    		          vm.service.showNoty("Please select only one Order or Invoice ");
                      flag = 0
    			     return false;
    		      } else {
                      data_dict['pick_number'].push(pick_number)
    		      }
    		  }
    		}
  	  });
      if (!flag) {
        return false;
      }
//  	  var selected_row = vm.dtInstance.DataTable.context[0].aoData[parseInt(key)]['_aData'];
//  	  var send = {};
//  	  send['order_id'] = selected_row['Stock Transfer ID'];
//  	  send['warehouse_name'] = selected_row['Warehouse Name'];
//  	  send['picklist_number'] = selected_row['Picklist Number'];
//  	  send['picked_qty'] = selected_row['Picklist Quantity'];
//  	  send['stock_transfer_datetime'] = selected_row['Stock Transfer Date&Time'];
//  	  send['total_amount'] = selected_row['Total Amount'];
//  	  send['invoice_date'] = selected_row['Invoice Date'];
//  	  send['order_date'] = selected_row['Order Date'];
  	  vm.service.apiCall("generate_stock_transfer_invoice/", "POST",{'data': JSON.stringify(data_dict)}).then(function(data) {
            if(data.message) {
              if(click_type == 'generate') {
                vm.pdf_data = data.data
//                $state.go("app.outbound.CustomerInvoicesMain.StockTransferInvoiceGen");
                $state.go("app.outbound.CustomerInvoices.StockTransferInvoiceE");
                $timeout(function () {
                  $(".modal-body:visible").html(vm.pdf_data)
                }, 3000);
              }
            }
            vm.bt_disable = false;
        });
      }
      vm.inv_height = 1358; //total invoice height
      vm.inv_details = 292; //invoice details height
      vm.inv_footer = 95;   //invoice footer height
      vm.inv_totals = 127;  //invoice totals height
      vm.inv_header = 47;   //invoice tables headers height
      vm.inv_product = 47;  //invoice products cell height
      vm.inv_summary = 47;  //invoice summary headers height
      vm.inv_total = 27;    //total display height
      vm.render_data = []
    }

function EditInvoice($scope, $http, $state, $timeout, Session, colFilters, Service, $stateParams, $modalInstance, items) {

  var vm = this;
  vm.service = Service;
  vm.permissions = Session.roles.permissions;
  vm.priceband_sync = Session.roles.permissions.priceband_sync;

  vm.model_data = items;
  vm.model_data.temp_sequence_number = vm.model_data.sequence_number;

  vm.model_data.default_charge = function(){

    if (vm.model_data.order_charges.length == 1) {

      vm.model_data.flag = true;
    }
  }

  vm.cal_total = function(extra_charges){
    extra_charges.charge_tax_value = (Number(extra_charges.charge_amount) * Number(extra_charges.tax_percent))/100
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

    $('[name="invoice_date"]').datepicker("setDate", new Date(vm.model_data.inv_date) );
  },1000);
  vm.ok = function () {

    $modalInstance.close("close");
  };

  vm.process = false;
  vm.save = function(form) {

    if (vm.permissions.increment_invoice && vm.model_data.sequence_number && form.invoice_number.$invalid) {

      Service.showNoty("Please Fill Invoice Number");
      return false;
    } else if (!form.$valid) {

      Service.showNoty("Please Fill the Mandatory Fields");
      return false;
    }
    vm.process = true;
    var data = $("form:visible").serializeArray()
    Service.apiCall("update_invoice/", "POST", data).then(function(data) {

      if(data.message) {

        if(data.data.msg == 'success') {

          Service.showNoty("Updated Successfully");
          $modalInstance.close("saved");
        } else {

          Service.showNoty(data.data.msg);
        }
      } else {

        Service.showNoty("Update fail");
      }
      vm.process = false;
    })
  }


  vm.changeUnitPrice = function(data) {

    data.base_price = data.quantity * Number(data.unit_price);
    data.discount = (data.base_price/100)*Number(data.discount_percentage);
    data.amt = data.base_price - data.discount;
    var taxes = {cgst_amt: 'cgst_tax', sgst_amt: 'sgst_tax', igst_amt: 'igst_tax', utgst_amt: 'utgst_tax'};
    data.total_tax_amount = 0;

    angular.forEach(taxes, function(tax_name, tax_amount){

      if (data.taxes[tax_name] > 0){

        data.taxes[tax_amount] = (data.amt/100)*data.taxes[tax_name];
      } else {

        data.taxes[tax_amount] = 0;
      }
       data.total_tax_amount += data.taxes[tax_amount];
    })
    data.invoice_amount = (data.amt + data.total_tax_amount);
  }
}
stockone = angular.module('urbanApp');

stockone.controller('EditInvoice', ['$scope', '$http', '$state', '$timeout', 'Session', 'colFilters', 'Service', '$stateParams', '$modalInstance', 'items', EditInvoice]);

stockone.directive('genericCustomerInvoiceData', function() {
  return {
    restrict: 'E',
    scope: {
      invoice_data: '=data',
    },
    templateUrl: 'views/outbound/toggle/invoice_data_html.html',
    link: function(scope, element, attributes, $http, Service){
      console.log(scope);
    }
  };
});
